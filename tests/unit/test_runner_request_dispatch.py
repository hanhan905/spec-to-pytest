"""Dispatch tests use a fake executor; browser behavior is exercised separately."""

import argparse
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import run_local


def arguments(root: Path, request: str = "initial") -> argparse.Namespace:
    return argparse.Namespace(
        run_dir=root / "reports/runs/run",
        plan=None,
        data=None,
        base_url="http://127.0.0.1:8765",
        bug_mode="healthy",
        repair_kind=None,
        repair_note=None,
        timeout=60,
        request_id=request,
        parent_request_ref=None,
        request_reason=None,
    )


def prepare(root: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    run = root / "reports/runs/run"
    run.mkdir(parents=True)
    (run / "run.json").write_text(
        json.dumps(
            {
                "schema_version": "2.1",
                "acceptance_policy": "2.1",
                "run_id": "run",
                "attempts": [],
                "repairs": [],
            }
        )
    )
    monkeypatch.setattr(run_local, "ROOT", root)
    monkeypatch.setattr(run_local, "finalise", lambda *a, **k: SimpleNamespace(integrity_errors=[]))
    return run


def test_two_concurrent_same_id_calls_create_one_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = prepare(tmp_path, monkeypatch)
    entered, release = threading.Event(), threading.Event()
    calls = []

    def executor(args: argparse.Namespace, selection: list[str]) -> int:
        calls.append(args.invocation_id)
        entered.set()
        assert release.wait(timeout=5)
        attempt = run / "attempts/0001"
        attempt.mkdir(parents=True)
        (attempt / "process.json").write_text('{"completed":true}')
        metadata = json.loads((run / "run.json").read_text())
        metadata["attempts"] = ["0001"]
        (run / "run.json").write_text(json.dumps(metadata))
        return 0

    monkeypatch.setattr(run_local, "_execute_once", executor)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(run_local.execute, arguments(tmp_path), [])
        assert entered.wait(timeout=5)
        try:
            assert run_local.execute(arguments(tmp_path), []) == 2
        finally:
            release.set()
        assert pending.result(timeout=5) == 0
    assert run_local.execute(arguments(tmp_path), []) == 0
    assert len(calls) == 1
    assert len(list((run / "attempts").iterdir())) == 1
    assert len(list((run / "invocations").glob("*.result.json"))) == 2


def test_interruption_is_recorded_and_requires_new_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = prepare(tmp_path, monkeypatch)

    def interrupted(*args: object) -> int:
        raise KeyboardInterrupt

    monkeypatch.setattr(run_local, "_execute_once", interrupted)
    with pytest.raises(KeyboardInterrupt):
        run_local.execute(arguments(tmp_path), [])
    assert json.loads((run / "requests/initial.json").read_text())["state"] == "interrupted"
    assert run_local.execute(arguments(tmp_path), []) == 2
    with pytest.raises(ValueError, match="linked new run"):
        run_local.execute(arguments(tmp_path, "retry"), [])


def test_preflight_failure_is_recorded_without_pytest_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = prepare(tmp_path, monkeypatch)

    def invalid(*args: object) -> int:
        raise SyntaxError("synthetic generation failure")

    monkeypatch.setattr(run_local, "_execute_once", invalid)
    with pytest.raises(SyntaxError):
        run_local.execute(arguments(tmp_path), [])
    assert json.loads((run / "requests/initial.json").read_text())["state"] == "rejected"
    assert not (run / "attempts").exists()
