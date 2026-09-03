"""Constrain evidence references to their owning run."""

from pathlib import Path, PurePosixPath, PureWindowsPath


def contained_path(root: Path, relative: str, *, must_exist: bool = True) -> Path:
    path = PurePosixPath(relative)
    if (
        not relative
        or "\\" in relative
        or ":" in relative
        or path.is_absolute()
        or PureWindowsPath(relative).drive
        or ".." in path.parts
        or relative == "."
    ):
        raise ValueError("Evidence must use a relative in-run path")
    resolved = (root / relative).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError("Evidence path escapes its run")
    if must_exist and not resolved.exists():
        raise ValueError("Evidence path does not exist")
    return resolved
