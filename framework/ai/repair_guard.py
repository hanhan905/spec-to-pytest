"""Full-source guard with a deliberately small action-leaf allowlist, not a sandbox."""

import ast
import re
from pathlib import Path

from framework.ai.integrity import validate_generated_path

SELECTORS = {"name", "label", "test_id", "css"}


def signature(source: str, *, category: str) -> str:
    tree = ast.parse(source)
    original = list(ast.walk(tree))
    parents = {child: parent for parent in original for child in ast.iter_child_nodes(parent)}
    imported = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "framework.ai"
        and any(alias.name == "actions" and alias.asname is None for alias in node.names)
        for node in tree.body
    )
    ids: set[str] = set()
    for node in original:
        if isinstance(node, ast.Name) and node.id == "actions" and isinstance(node.ctx, ast.Store):
            raise ValueError("Action module cannot be rebound")
        if isinstance(node, ast.ExceptHandler):
            raise ValueError("Generated tests cannot hide exceptions")
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "actions"
        ):
            continue
        if not imported or node.func.attr not in {"click", "fill", "wait_visible"}:
            raise ValueError("Unregistered action API")
        if not isinstance(parents[node], ast.Expr) or len(node.args) < 2:
            raise ValueError("Action calls must be standalone statements")
        key = node.args[1]
        if not (
            isinstance(key, ast.Constant)
            and isinstance(key.value, str)
            and re.fullmatch(r"[A-Z][A-Z0-9_-]{0,95}", key.value)
        ):
            raise ValueError("Action needs a literal registration ID")
        if key.value in ids:
            raise ValueError("Duplicate action registration")
        ids.add(key.value)
        if any(kw.arg is None for kw in node.keywords):
            raise ValueError("Action options cannot be expanded dynamically")
        strategy = [kw.arg for kw in node.keywords if kw.arg in {"role", "label", "test_id", "css"}]
        if len(strategy) != 1:
            raise ValueError("Action needs one explicit locator strategy")
        for kw in node.keywords:
            if kw.arg == "timeout":
                if not (
                    isinstance(kw.value, ast.Constant)
                    and type(kw.value.value) is int
                    and 100 <= kw.value.value <= 30_000
                ):
                    raise ValueError("Repair timeout must be bounded")
                if category == "synchronisation":
                    kw.value = ast.Constant(value="<registered-timeout>")
            if kw.arg in SELECTORS:
                if not (
                    isinstance(kw.value, ast.Constant)
                    and isinstance(kw.value.value, str)
                    and 0 < len(kw.value.value) <= 1024
                ):
                    raise ValueError("Action selector must be a bounded literal")
                if category == "locator" and node.func.attr != "wait_visible":
                    kw.value = ast.Constant(value="<registered-action-selector>")
    return ast.dump(tree, include_attributes=False)


def guard_snapshot(root: Path, run_id: str) -> dict[str, dict[str, str]]:
    result = {}
    for path in sorted((root / "tests/generated" / run_id).rglob("*.py")):
        validate_generated_path(root, path)
        result[path.relative_to(root).as_posix()] = {
            category: signature(path.read_text(), category=category)
            for category in ("locator", "synchronisation")
        }
    return result


def validate_repair(
    previous: dict[str, dict[str, str]],
    current: dict[str, dict[str, str]],
    kind: str | None,
    rounds: int,
) -> None:
    if kind not in {"locator", "synchronisation"} or rounds >= 3:
        raise ValueError("Only three registered locator/wait repairs are allowed")
    if previous.keys() != current.keys() or any(
        previous[name][kind] != current[name][kind] for name in previous
    ):
        raise ValueError("Repair changed frozen source outside registered action leaves")
