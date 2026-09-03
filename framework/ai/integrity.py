"""Conservative change guards, not a sandbox for arbitrary generated Python."""

import ast
import hashlib
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_files(root: Path) -> list[Path]:
    paths = [root / "pyproject.toml", root / "uv.lock", root / "AGENTS.md"]
    for folder in ("framework", "practice_app", "scripts", "tests", "mana", "config"):
        paths.extend(
            path
            for path in (root / folder).rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix in {".py", ".json", ".csv", ".md", ".js", ".css", ".html"}
        )
    existing = sorted(path for path in paths if path.is_file())
    if any(
        path.is_symlink() or not path.resolve().is_relative_to(root.resolve()) for path in existing
    ):
        raise ValueError("Source snapshots cannot follow links outside the workspace")
    return existing


def protected_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): digest(path)
        for path in source_files(root)
        if not path.is_relative_to(root / "tests/generated")
    }


def generated_hashes(root: Path, run_id: str) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): digest(path)
        for path in sorted((root / "tests/generated" / run_id).rglob("*.py"))
    }


def assertion_signatures(root: Path, run_id: str) -> dict[str, list[str] | None]:
    result: dict[str, list[str] | None] = {}
    for path in sorted((root / "tests/generated" / run_id).rglob("*.py")):
        name = path.relative_to(root).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            result[name] = None
            continue
        assertions: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                raise ValueError("Generated tests cannot catch and hide test exceptions")
            if isinstance(node, ast.Attribute) and node.attr in {"skip", "skipif", "xfail"}:
                raise ValueError("Generated tests cannot introduce skip or xfail")
            if (
                isinstance(node, ast.ImportFrom)
                and node.module == "pytest"
                and any(alias.name in {"skip", "xfail"} for alias in node.names)
            ):
                raise ValueError("Generated tests cannot import skip or xfail")
            if isinstance(node, ast.Assert) or (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr.startswith(("to_", "not_to_"))
            ):
                assertions.append(ast.dump(node, include_attributes=False))
        result[name] = sorted(assertions)
        if path.name.startswith("test_") and not assertions:
            raise ValueError("Generated test files must contain explicit outcome assertions")
    return result


def check_assertions(
    previous: dict[str, list[str] | None], current: dict[str, list[str] | None]
) -> None:
    for path, signature in previous.items():
        if path not in current or (signature is not None and current[path] != signature):
            raise ValueError("Frozen assertions changed or a generated file was removed")
