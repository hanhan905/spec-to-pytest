import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from framework.ai.acceptance import assess, record_review
from framework.ai.contracts import CaseRunResult, CaseStatus, RunManifest
from framework.ai.integrity import digest
from scripts.export_public_summary import public_summary
from scripts.finalise_ai_run import finalise


def fixture_run(tmp_path: Path) -> tuple[Path, RunManifest]:
    run = tmp_path / "run"
    attempt = run / "attempts/0001"
    attempt.mkdir(parents=True)
    plan = {
        "schema_version": "2.1",
        "run_id": "run",
        "scenario_id": "fixture",
        "generated_at": datetime.now(UTC).isoformat(),
        "source": "trae_orchestrated",
        "reduced_scope_reason": "One synthetic assessment fixture",
        "provenance": {
            "host_version": "synthetic",
            "model": "synthetic",
            "mcp_version": "synthetic",
        },
        "cases": [
            {
                "scenario_id": "fixture",
                "case_id": "CASE_001",
                "title": "Type detail",
                "rule_ids": ["MEDIA-01"],
                "steps": ["Read error detail"],
                "expected_results": ["Contains PNG"],
                "expectations": [
                    {
                        "expectation_id": "EXPECT_001",
                        "text": "Contains PNG",
                        "check_ids": ["CHECK_001"],
                    }
                ],
                "checks": [
                    {
                        "check_id": "CHECK_001",
                        "subject": "response.detail",
                        "operator": "contains",
                        "expected": "PNG",
                        "rule_ids": ["MEDIA-01"],
                    }
                ],
            }
        ],
    }
    (run / "plan.json").write_text(json.dumps(plan))
    (run / "data.csv").write_text("synthetic fixture data\n")
    (run / "run.json").write_text(
        json.dumps(
            {
                "schema_version": "2.1",
                "acceptance_policy": "2.1",
                "run_id": "run",
                "correlation_nonce": "fixture",
                "exploration_origin": "http://127.0.0.1:8000",
            }
        )
    )
    binding = {"case_id": "CASE_001", "check_id": "CHECK_001", "nodeid": "test.py::test_case"}
    (run / "check-bindings.json").write_text(json.dumps([binding]))
    (attempt / "collection.json").write_text(json.dumps({"items": [binding], "errors": []}))
    event = {
        **binding,
        "kind": "check",
        "phase": "call",
        "operator": "contains",
        "outcome": "passed",
    }
    (attempt / "events.jsonl").write_text(json.dumps(event) + "\n")
    (attempt / "receipt.json").write_text(
        json.dumps({"events.jsonl": digest(attempt / "events.jsonl")})
    )
    (run / "candidate-delegations.json").write_text(
        json.dumps(
            {
                "schema_version": "2.1",
                "run_id": "run",
                "evidence_kind": "agent_statement",
                "calls": [
                    {
                        "role": role,
                        "phase": phase,
                        "correlation_id": f"synthetic-{index}",
                        "host_role_identifier": role,
                        "input_artifacts": {"plan.json": digest(run / "plan.json")},
                        "output_artifacts": {"data.csv": digest(run / "data.csv")},
                    }
                    for index, (role, phase) in enumerate(
                        [
                            ("playwright-test-generator", "plan"),
                            ("ai-test-data-expander", "data"),
                            ("playwright-test-generator", "generate-and-execute"),
                        ]
                    )
                ],
            }
        )
    )
    manifest = RunManifest(
        schema_version="2.1",
        run_id="run",
        scenario_id="fixture",
        source="trae_orchestrated",
        completed=True,
        final_attempt="0001",
        finished_at=datetime.now(UTC),
        quality_gate="passed",
        planned_count=1,
        counts={
            CaseStatus.PASSED: 1,
            CaseStatus.FAILED: 0,
            CaseStatus.SKIPPED: 0,
            CaseStatus.BLOCKED: 0,
        },
        integrity_errors=[],
        results=[
            CaseRunResult(
                case_id="CASE_001",
                nodeid="test.py::test_case",
                status=CaseStatus.PASSED,
                final_reason="synthetic",
            )
        ],
    )
    return run, manifest


def test_green_execution_without_review_is_unverified(tmp_path: Path) -> None:
    run, manifest = fixture_run(tmp_path)
    (run / "agent-declarations.json").write_text('{"all_agents_called": true}')
    result = assess(run, manifest)
    assert result.execution_gate == "passed"
    assert result.workflow_gate == "unverified"
    assert "reviewed_host_delegation_evidence_required" in result.reasons
    assert result.evidence_basis["mcp_exploration"] == "host_review_only"
    assert public_summary(manifest, result)["workflow_gate"] == "unverified"


def test_missing_required_check_rejects_otherwise_green_run(tmp_path: Path) -> None:
    run, manifest = fixture_run(tmp_path)
    (run / "attempts/0001/events.jsonl").write_text("")
    result = assess(run, manifest)
    assert result.workflow_gate == "rejected"
    assert "missing_or_duplicate_check_events" in result.reasons


def test_explicit_review_and_host_capture_are_needed(tmp_path: Path) -> None:
    run, manifest = fixture_run(tmp_path)
    assert assess(run, manifest).workflow_gate == "unverified"
    (run / "host").mkdir()
    (run / "host/synthetic-capture.txt").write_text("Synthetic reviewed three-phase host capture")
    review = record_review(
        run,
        manifest,
        semantic_alignment="approved",
        captures=["host/synthetic-capture.txt"],
        capture_kind="host_export",
        delegation_reviewed=True,
    )
    assert assess(run, manifest, review_path=review).workflow_gate == "verified"
    (run / "data.csv").write_text("changed operand data")
    assert assess(run, manifest, review_path=review).workflow_gate == "rejected"


def test_agent_statement_cannot_be_a_reviewed_host_capture(tmp_path: Path) -> None:
    run, manifest = fixture_run(tmp_path)
    (run / "host").mkdir()
    (run / "host/claim.json").write_text('{"called": true}')
    with pytest.raises(ValueError):
        record_review(
            run,
            manifest,
            semantic_alignment="approved",
            captures=["host/claim.json"],
            capture_kind="agent_statement",
            delegation_reviewed=True,
        )


def test_legacy_inspection_does_not_compare_current_tree_or_write(tmp_path: Path) -> None:
    run, manifest = fixture_run(tmp_path)
    plan = json.loads((run / "plan.json").read_text())
    plan.update({"schema_version": "2.0", "source": "synthetic"})
    plan["cases"][0].pop("checks")
    plan["cases"][0].pop("expectations")
    (run / "plan.json").write_text(json.dumps(plan))
    manifest.schema_version, manifest.source = "2.0", "synthetic"
    (run / "manifest.json").write_text(manifest.model_dump_json())
    attempt = run / "attempts/0001"
    source = attempt / "source/framework/frozen.py"
    source.parent.mkdir(parents=True)
    source.write_text("synthetic_historical_source = True\n")
    events = [{"kind": "session_start"}]
    events.extend(
        {
            "kind": "report",
            "case_id": "CASE_001",
            "nodeid": "test.py::test_case",
            "phase": phase,
            "outcome": "passed",
        }
        for phase in ["setup", "call", "teardown"]
    )
    events.append({"kind": "session_finish", "exitstatus": 0, "collected": 1})
    (attempt / "events.jsonl").write_text("\n".join(json.dumps(e) for e in events))
    (attempt / "process.json").write_text('{"completed":true,"full_suite":true,"exit_code":0}')
    (attempt / "junit.xml").write_text(
        '<testsuite tests="1" failures="0" errors="0" skipped="0"><testcase>'
        '<properties><property name="case_id" value="CASE_001"/>'
        '<property name="nodeid" value="test.py::test_case"/>'
        "</properties></testcase></testsuite>"
    )
    (run / "run.json").write_text(
        json.dumps(
            {
                "run_id": "run",
                "attempts": ["0001"],
                "repairs": [],
                "plan_hash": digest(run / "plan.json"),
                "data_hash": digest(run / "data.csv"),
                "protected_hashes": {"framework/frozen.py": digest(source)},
            }
        )
    )
    receipt = {
        p.relative_to(attempt).as_posix(): digest(p)
        for p in attempt.rglob("*")
        if p.is_file() and p.name != "receipt.json"
    }
    (attempt / "receipt.json").write_text(json.dumps(receipt))
    before = {p.relative_to(run).as_posix(): digest(p) for p in run.rglob("*") if p.is_file()}
    result = finalise(run, write_output=False)
    assert result.quality_gate == "passed"
    assert assess(run, result).workflow_gate == "unverified"
    with pytest.raises(ValueError, match="read-only"):
        finalise(run)
    with pytest.raises(ValueError, match="Legacy"):
        record_review(
            run,
            result,
            semantic_alignment="approved",
            captures=[],
            capture_kind="ui_capture",
            delegation_reviewed=False,
        )
    assert before == {
        p.relative_to(run).as_posix(): digest(p) for p in run.rglob("*") if p.is_file()
    }
