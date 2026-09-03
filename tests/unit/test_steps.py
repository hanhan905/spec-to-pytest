from datetime import UTC, datetime
from pathlib import Path

import pytest

from framework.ai.contracts import (
    CaseRunResult,
    CaseStatus,
    RunManifest,
    StepInfoRecord,
    StepInfoStore,
)
from framework.ai.integrity import require_repair_budget
from framework.ai.steps import merge_verified_steps
from scripts.export_public_summary import public_summary


def passing_manifest() -> RunManifest:
    return RunManifest(
        run_id="fixture",
        scenario_id="fixture",
        completed=True,
        final_attempt="0001",
        finished_at=datetime.now(UTC),
        quality_gate="passed",
        planned_count=1,
        counts={status: int(status == CaseStatus.PASSED) for status in CaseStatus},
        integrity_errors=[],
        results=[CaseRunResult(case_id="CASE_001", status="passed", final_reason="synthetic test")],
    )


def candidate() -> StepInfoRecord:
    return StepInfoRecord(
        description="Search synthetic data",
        action="fill",
        mcp_tool="browser_fill_form",
        locator_strategy="label",
        selector="Search",
        parameters={"value": "synthetic"},
        success_state="Results appear",
        verified_at=datetime.now(UTC),
        source_run_id="fixture",
        source_case_id="CASE_001",
        app_version="test",
        app_fingerprint="a" * 64,
        evidence_paths=["snapshot.txt"],
    )


def test_only_matching_passed_steps_are_promoted_and_deduplicated(tmp_path: Path) -> None:
    (tmp_path / "snapshot.txt").write_text("Synthetic MCP observation fixture")
    path = tmp_path / "knowledge/steps.json"
    candidates = StepInfoStore(records=[candidate()])
    assert (
        len(merge_verified_steps(tmp_path, candidates, passing_manifest(), "a" * 64, path).records)
        == 1
    )
    assert (
        len(merge_verified_steps(tmp_path, candidates, passing_manifest(), "a" * 64, path).records)
        == 1
    )


@pytest.mark.parametrize(
    "change",
    ["failed-run", "wrong-case", "wrong-fingerprint", "missing-evidence", "sensitive-data"],
)
def test_invalid_step_provenance_never_updates_the_store(tmp_path: Path, change: str) -> None:
    (tmp_path / "snapshot.txt").write_text("Synthetic observation")
    manifest, record = passing_manifest(), candidate()
    if change == "failed-run":
        manifest.quality_gate = "failed"
    elif change == "wrong-case":
        record.source_case_id = "MISSING"
    elif change == "wrong-fingerprint":
        record.app_fingerprint = "b" * 64
    elif change == "missing-evidence":
        record.evidence_paths = ["missing.txt"]
    else:
        record.parameters = {"password": "synthetic-do-not-store"}
    path = tmp_path / "knowledge/steps.json"
    with pytest.raises(ValueError):
        merge_verified_steps(tmp_path, StepInfoStore(records=[record]), manifest, "a" * 64, path)
    assert not path.exists()


@pytest.mark.parametrize(
    "rounds,kind,note",
    [
        (3, "locator", "fourth round"),
        (-1, "locator", "bad"),
        (1, "assertion", "not allowed"),
        (1, "syntax", " "),
    ],
)
def test_repair_budget_and_classification_are_checked(rounds: int, kind: str, note: str) -> None:
    with pytest.raises(ValueError, match="three rounds"):
        require_repair_budget(rounds, kind, note)


def test_first_three_repair_rounds_are_permitted() -> None:
    for completed_rounds in range(3):
        require_repair_budget(completed_rounds, "locator", "synthetic regression fixture")


def test_public_export_never_includes_raw_reasons_paths_or_run_identifiers() -> None:
    manifest = passing_manifest()
    manifest.results[0].final_reason = "synthetic private detail"
    manifest.results[0].evidence_paths = ["private-trace.zip"]
    exported = public_summary(manifest)
    assert set(exported) == {
        "run_ref",
        "quality_gate",
        "source",
        "planned_count",
        "counts",
        "integrity_error_count",
    }
    assert "synthetic private detail" not in str(exported)
    assert "private-trace.zip" not in str(exported)
    assert manifest.run_id != exported["run_ref"]
