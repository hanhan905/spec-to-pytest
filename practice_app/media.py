"""Bounded decoding and metadata-free image storage, never client-selected paths."""

import re
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
FORMATS = {"image/png": "PNG", "image/jpeg": "JPEG"}


class MediaStore:
    def __init__(self, data_dir: Path) -> None:
        self.root = (data_dir / "media").resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, name: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{32}\.(png|jpg)", name):
            raise ValueError("invalid media identifier")
        path = self.root / name
        if path.is_symlink() or path.resolve().parent != self.root:
            raise ValueError("media path escapes instance")
        return path

    async def store(self, upload: UploadFile) -> str:
        expected = FORMATS.get(upload.content_type or "")
        if expected is None:
            raise HTTPException(422, "Only PNG and JPG images are supported")
        payload = await upload.read(MAX_IMAGE_BYTES + 1)
        if len(payload) > MAX_IMAGE_BYTES:
            raise HTTPException(422, "Image must not exceed 2 MB")
        try:
            with Image.open(BytesIO(payload), formats=["PNG", "JPEG"]) as candidate:
                if candidate.format != expected:
                    raise ValueError("Image content does not match its declared type")
                if candidate.width * candidate.height > MAX_IMAGE_PIXELS:
                    raise ValueError("Image must not exceed 20 megapixels")
                candidate.verify()
            with Image.open(BytesIO(payload)) as decoded:
                mode = "RGBA" if expected == "PNG" else "RGB"
                pixels = decoded.convert(mode)
                clean = Image.frombytes(mode, pixels.size, pixels.tobytes())
                output = BytesIO()
                clean.save(output, format=expected)
        except (
            OSError,
            ValueError,
            UnidentifiedImageError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ) as error:
            raise HTTPException(422, "Invalid or unsafe image content") from error
        name = f"{uuid4().hex}.{'png' if expected == 'PNG' else 'jpg'}"
        with self.path(name).open("xb") as target:
            target.write(output.getvalue())
        return name

    def remove(self, name: str) -> None:
        self.path(name).unlink(missing_ok=True)
