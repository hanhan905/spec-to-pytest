"""Append-only, per-attempt facts from pytest; no model-written status is consumed."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest


@dataclass
class ExecutionState:
    root: Path
    cases: dict[str, str] = field(default_factory=dict)

    def emit(self, payload: dict[str, Any]) -> None:
        with (self.root / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False) + "\n")


KEY = pytest.StashKey[ExecutionState]()


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("execution evidence")
    group.addoption("--execution-dir", default=None)
    group.addoption("--require-case-ids", action="store_true")


def pytest_sessionstart(session: pytest.Session) -> None:
    value = session.config.getoption("--execution-dir")
    if value:
        root = Path(value)
        root.mkdir(parents=True, exist_ok=True)
        (root / "events.jsonl").touch(exist_ok=False)
        state = ExecutionState(root)
        session.config.stash[KEY] = state
        state.emit({"kind": "session_start"})


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "case_id(value): explicit plan case identifier")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    state = config.stash.get(KEY, None)
    if state is None:
        return
    rows: list[dict[str, str]] = []
    errors: list[str] = []
    for item in items:
        marker = item.get_closest_marker("case_id")
        case = str(marker.args[0]) if marker and len(marker.args) == 1 else ""
        if not case:
            if config.getoption("--require-case-ids"):
                errors.append("missing_case_marker")
            case = "BASE_" + hashlib.sha256(item.nodeid.encode()).hexdigest()[:16].upper()
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{0,95}", case):
            errors.append("invalid_case_marker")
        if len(item.nodeid) > 500:
            errors.append("nodeid_too_long_use_explicit_parameter_ids")
        state.cases[item.nodeid] = case
        item.user_properties.extend([("case_id", case), ("nodeid", item.nodeid)])
        rows.append({"nodeid": item.nodeid, "case_id": case})
    if len(set(state.cases.values())) != len(items):
        errors.append("duplicate_case_marker")
    (state.root / "collection.json").write_text(
        json.dumps({"items": rows, "errors": errors}, indent=2), encoding="utf-8"
    )
    if errors:
        raise pytest.UsageError("Invalid case mapping: " + ", ".join(sorted(set(errors))))


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[None]) -> Any:
    outcome = yield
    report = outcome.get_result()
    state = item.config.stash.get(KEY, None)
    if state is None:
        return
    state.emit(
        {
            "kind": "report",
            "nodeid": item.nodeid,
            "case_id": state.cases.get(item.nodeid),
            "phase": report.when,
            "outcome": report.outcome,
            "wasxfail": bool(getattr(report, "wasxfail", False)),
            "duration": report.duration,
        }
    )


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    state = session.config.stash.get(KEY, None)
    if state:
        state.emit(
            {
                "kind": "session_finish",
                "exitstatus": int(exitstatus),
                "collected": session.testscollected,
            }
        )
