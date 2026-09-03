"""Conservative change guards, not a sandbox for arbitrary generated Python."""

import ast
import hashlib
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_files(root: Path) -> list[Path]:
    paths = [
        root / name for name in ("pyproject.toml", "uv.lock", "AGENTS.md", ".gitignore", "Makefile")
    ]
    for folder in (
        "framework",
        "practice_app",
        "scripts",
        "tests",
        "mana",
        "config",
        "examples",
        "integrations",
        ".agents",
    ):
        paths.extend(
            path
            for path in (root / folder).rglob("*")
            if path.is_file()
            and not {"__pycache__", "node_modules", ".git", ".venv"}.intersection(
                path.relative_to(root).parts
            )
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
        if validate_generated_path(root, path)
    }


def validate_generated_path(root: Path, path: Path) -> bool:
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Generated files must be real files inside this workspace")
    return True


def application_fingerprint(root: Path) -> str:
    rows = [
        f"{path.relative_to(root).as_posix()}:{digest(path)}"
        for path in source_files(root)
        if path.is_relative_to(root / "practice_app")
    ]
    return hashlib.sha256("\n".join(rows).encode()).hexdigest()


def assertion_signatures(root: Path, run_id: str) -> dict[str, list[str] | None]:
    result: dict[str, list[str] | None] = {}
    for path in sorted((root / "tests/generated" / run_id).rglob("*.py")):
        validate_generated_path(root, path)
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
            if (
                isinstance(node, ast.Assert)
                or (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr.startswith(("to_", "not_to_"))
                )
                or (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "verify"
                )
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


def require_repair_budget(rounds: int, kind: str | None, note: str | None) -> None:
    if (
        rounds >= 3
        or rounds < 0
        or kind not in {"locator", "synchronisation", "data", "syntax"}
        or not note
        or not note.strip()
    ):
        raise ValueError("Changed generated code requires a documented repair within three rounds")
