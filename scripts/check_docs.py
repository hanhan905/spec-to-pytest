"""Check local Markdown file links without scanning environments or crawling the web."""

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    paths = [*ROOT.glob("*.md"), *(ROOT / "docs").rglob("*.md"), *(ROOT / "examples").rglob("*.md")]
    failures: list[str] = []
    for path in paths:
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if target.startswith(("https://", "http://", "mailto:", "#")):
                continue
            name = unquote(target.split("#")[0].strip("<>"))
            resolved = (path.parent / name).resolve()
            if not resolved.is_relative_to(ROOT) or not resolved.exists():
                failures.append(f"{path.relative_to(ROOT)}: invalid local target {name}")
    if failures:
        raise SystemExit("\n".join(failures))
    print(
        f"Checked local file links in {len(paths)} Markdown files; "
        "external links/anchors not fetched."
    )


if __name__ == "__main__":
    main()
