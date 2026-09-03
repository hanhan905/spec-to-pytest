import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from framework.ai.contracts import PlannedCase
from framework.ai.contracts import TestPlan as PlanContract
from framework.ai.reconcile import reconcile


def run_case(tmp_path: Path, body: str, extra: str = "") -> Path:
    test = tmp_path / "test_fixture.py"
    test.write_text(
        "import pytest\n" + extra + "\n@pytest.mark.case_id('CASE_001')\n" + body, encoding="utf-8"
    )
    run = tmp_path / "run"
    attempt = run / "attempts" / "0001"
    attempt.mkdir(parents=True)
    plan = PlanContract(
        run_id="synthetic-run",
        scenario_id="synthetic",
        source="synthetic",
        generated_at=datetime.now(UTC),
        cases=[
            PlannedCase(
                scenario_id="synthetic",
                case_id="CASE_001",
                title="Real pytest subprocess fixture",
                rule_ids=["FIXTURE-01"],
                steps=["execute"],
                expected_results=["the chosen fixture assertion"],
            )
        ],
    )
    (run / "plan.json").write_text(plan.model_dump_json(), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(test),
            "--confcutdir",
            str(tmp_path),
            "--rootdir",
            str(tmp_path),
            "-p",
            "framework.plugins.execution",
            "--require-case-ids",
            "--execution-dir",
            str(attempt),
            f"--junitxml={attempt / 'junit.xml'}",
            "-q",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    (attempt / "pytest.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    (attempt / "process.json").write_text(
        json.dumps({"exit_code": result.returncode, "completed": True, "full_suite": True}),
        encoding="utf-8",
    )
    return run


def test_pass_requires_real_matching_pytest_and_junit(tmp_path: Path) -> None:
    run = run_case(tmp_path, "def test_fixture():\n    assert 1 == 1\n")
    result = reconcile(run, "0001")
    assert result.integrity_errors == [], (result, (run / "attempts/0001/pytest.log").read_text())
    assert result.quality_gate == "passed"
    assert result.counts["passed"] == 1


def test_real_assertion_failure_stays_failed(tmp_path: Path) -> None:
    result = reconcile(run_case(tmp_path, "def test_fixture():\n    assert 1 == 2\n"), "0001")
    assert result.quality_gate == "failed"
    assert result.results[0].status == "failed"
    assert result.results[0].failure_phase == "call"


def test_teardown_error_cannot_be_hidden_by_passing_assertions(tmp_path: Path) -> None:
    extra = (
        "@pytest.fixture\ndef bad_cleanup():\n    yield\n    raise RuntimeError('cleanup failed')\n"
    )
    result = reconcile(
        run_case(tmp_path, "def test_fixture(bad_cleanup):\n    assert True\n", extra), "0001"
    )
    assert result.quality_gate != "passed"
    assert result.results[0].failure_phase == "teardown"


def test_setup_failure_is_explicitly_blocked(tmp_path: Path) -> None:
    extra = "@pytest.fixture\ndef unavailable():\n    raise RuntimeError('browser unavailable')\n"
    result = reconcile(
        run_case(tmp_path, "def test_fixture(unavailable):\n    assert True\n", extra), "0001"
    )
    assert result.quality_gate == "blocked"
    assert result.results[0].failure_phase == "setup"


@pytest.mark.parametrize("body", ["pytest.skip('hide')", "pytest.xfail('hide')"])
def test_skip_and_xfail_cannot_hide_a_planned_case(tmp_path: Path, body: str) -> None:
    result = reconcile(run_case(tmp_path, f"def test_fixture():\n    {body}\n"), "0001")
    assert result.quality_gate == "blocked"
    assert "unexpected_skip_or_xfail" in result.integrity_errors


@pytest.mark.parametrize(
    "mutation",
    [
        "missing-junit",
        "bad-xml",
        "missing-finish",
        "exit-mismatch",
        "empty-collection",
        "duplicate-collection",
        "missing-phase",
        "extra-node",
        "wrong-junit-count",
    ],
)
def test_corrupted_or_incomplete_evidence_never_turns_green(tmp_path: Path, mutation: str) -> None:
    run = run_case(tmp_path, "def test_fixture():\n    assert True\n")
    attempt = run / "attempts/0001"
    if mutation == "missing-junit":
        (attempt / "junit.xml").unlink()
    elif mutation == "bad-xml":
        (attempt / "junit.xml").write_text("<broken")
    elif mutation == "wrong-junit-count":
        path = attempt / "junit.xml"
        path.write_text(path.read_text().replace('tests="1"', 'tests="0"'))
    elif mutation == "exit-mismatch":
        (attempt / "process.json").write_text(
            json.dumps({"exit_code": 1, "completed": True, "full_suite": True})
        )
    elif mutation in {"empty-collection", "duplicate-collection", "extra-node"}:
        path = attempt / "collection.json"
        data = json.loads(path.read_text())
        if mutation == "empty-collection":
            data["items"] = []
        elif mutation == "duplicate-collection":
            data["items"].append(data["items"][0].copy())
        else:
            data["items"].append({"case_id": "EXTRA", "nodeid": "test_extra.py::test_extra"})
        path.write_text(json.dumps(data))
    else:
        path = attempt / "events.jsonl"
        events = [json.loads(line) for line in path.read_text().splitlines()]
        if mutation == "missing-finish":
            events = [event for event in events if event["kind"] != "session_finish"]
        else:
            events = [event for event in events if event.get("phase") != "teardown"]
        path.write_text("\n".join(json.dumps(event) for event in events) + "\n")
    result = reconcile(run, "0001")
    assert result.quality_gate == "blocked"
    assert result.integrity_errors
