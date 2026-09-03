"""Structural plan/source/runtime correspondence. Semantic review remains explicit."""

import ast
from collections import Counter
from pathlib import Path
from typing import Any

from framework.ai.contracts import TestPlan


def source_bindings(root: Path, run_id: str, plan: TestPlan) -> list[dict[str, str]]:
    expected = {check.check_id: case.case_id for case in plan.cases for check in case.checks}
    if not expected:
        return []
    bindings: list[dict[str, str]] = []
    for path in sorted((root / "tests/generated" / run_id).rglob("test_*.py")):
        tree = ast.parse(path.read_text())
        imported = any(
            isinstance(node, ast.ImportFrom)
            and node.module == "framework.ai.checks"
            and any(a.name == "verify" and a.asname is None for a in node.names)
            for node in tree.body
        )
        if any(
            isinstance(node, ast.Name) and node.id == "verify" and isinstance(node.ctx, ast.Store)
            for node in ast.walk(tree)
        ):
            raise ValueError("Frozen check helper cannot be rebound")
        for function in tree.body:
            if not isinstance(function, ast.FunctionDef) or not function.name.startswith("test_"):
                continue
            cases = [
                d.args[0].value
                for d in function.decorator_list
                if isinstance(d, ast.Call)
                and isinstance(d.func, ast.Attribute)
                and d.func.attr == "case_id"
                and len(d.args) == 1
                and isinstance(d.args[0], ast.Constant)
                and isinstance(d.args[0].value, str)
            ]
            if len(cases) != 1:
                raise ValueError("Structured checks require one literal case marker")
            for node in ast.walk(function):
                if not (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "verify"
                ):
                    continue
                if (
                    not imported
                    or len(node.args) != 2
                    or node.keywords
                    or not (
                        isinstance(node.args[0], ast.Constant)
                        and isinstance(node.args[0].value, str)
                    )
                ):
                    raise ValueError("Use verify(literal_check_id, observation) without overrides")
                check_id = node.args[0].value
                if expected.get(check_id) != cases[0]:
                    raise ValueError("Check belongs to another case or is undeclared")
                bindings.append(
                    {
                        "check_id": check_id,
                        "case_id": cases[0],
                        "nodeid": f"{path.relative_to(root).as_posix()}::{function.name}",
                    }
                )
    if Counter(row["check_id"] for row in bindings) != Counter(expected.keys()):
        raise ValueError("Every required check needs exactly one source binding")
    return bindings


def contract_errors(
    plan: TestPlan,
    events: list[dict[str, Any]],
    bindings: list[dict[str, str]],
    mapping: dict[str, str],
) -> list[str]:
    errors: list[str] = []
    expected = {c.check_id: (case.case_id, c.operator) for case in plan.cases for c in case.checks}
    if not expected:
        return ["missing_structured_checks"] if plan.source.startswith("trae_") else []
    if Counter(row.get("check_id") for row in bindings) != Counter(expected.keys()):
        errors.append("source_check_binding_mismatch")
    for row in bindings:
        observed = mapping.get(row.get("case_id", ""), "")
        source_node = row.get("nodeid", "")
        # pytest-playwright adds the selected browser parameter; collection still
        # enforces exactly one concrete node for each case.
        if not source_node or not (
            observed == source_node
            or (observed.startswith(source_node + "[") and observed.endswith("]"))
        ):
            errors.append("source_node_binding_mismatch")
    checks = [event for event in events if event.get("kind") == "check"]
    if Counter(e.get("check_id") for e in checks) != Counter(expected.keys()):
        errors.append("missing_or_duplicate_check_events")
    for event in checks:
        if (
            expected.get(str(event.get("check_id", "")))
            != (event.get("case_id"), event.get("operator"))
            or event.get("phase") != "call"
            or mapping.get(event.get("case_id", "")) != event.get("nodeid")
        ):
            errors.append("invalid_check_event_mapping")
        if event.get("outcome") != "passed":
            errors.append("unsuccessful_required_check")
    reads = [event for event in events if event.get("kind") == "data_read"]
    for case in plan.cases:
        actual = {
            e.get("data_id")
            for e in reads
            if e.get("case_id") == case.case_id and e.get("phase") == "call"
        }
        if actual != set(case.data_ids):
            errors.append("declared_observed_data_mismatch")
    for event in reads:
        if (
            event.get("phase") != "call"
            or event.get("case_id") not in mapping
            or mapping.get(event.get("case_id", "")) != event.get("nodeid")
        ):
            errors.append("invalid_data_event_mapping")
    return sorted(set(errors))
