from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from framework.ai.contracts import PlannedCase, StepInfoStore
from framework.ai.contracts import TestPlan as PlanContract
from framework.ai.paths import contained_path


def example_plan() -> PlanContract:
    return PlanContract(
        run_id="fixture-run",
        scenario_id="fixture",
        generated_at=datetime.now(UTC),
        source="synthetic",
        cases=[
            PlannedCase(
                scenario_id="fixture",
                case_id="CASE_001",
                title="Synthetic case",
                rule_ids=["AUTH-01"],
                steps=["Check"],
                expected_results=["Assert the rule"],
            )
        ],
    )


def test_valid_synthetic_plan_and_empty_temporary_store() -> None:
    assert example_plan().cases[0].case_id == "CASE_001"
    assert StepInfoStore().records == []


@pytest.mark.parametrize(
    "mutation,error",
    [
        ("duplicate", "unique"),
        ("scenario", "mixed scenario"),
        ("empty", "at least 1"),
        ("unsupported", "unsupported_reason"),
    ],
)
def test_rejects_incomplete_or_ambiguous_plans(mutation: str, error: str) -> None:
    payload = example_plan().model_dump(mode="json")
    if mutation == "duplicate":
        payload["cases"].append(payload["cases"][0].copy())
    elif mutation == "scenario":
        payload["cases"][0]["scenario_id"] = "other"
    elif mutation == "empty":
        payload["cases"] = []
    else:
        payload["cases"][0]["automation_candidate"] = False
    with pytest.raises(ValidationError, match=error):
        PlanContract.model_validate(payload)


def test_ai_source_cannot_omit_scope_and_provenance() -> None:
    payload = example_plan().model_dump(mode="json")
    payload["source"] = "trae_orchestrated"
    with pytest.raises(ValidationError, match="reduced_scope_reason"):
        PlanContract.model_validate(payload)
    payload["reduced_scope_reason"] = "Only one behavior in this synthetic fixture"
    with pytest.raises(ValidationError, match="provenance"):
        PlanContract.model_validate(payload)


@pytest.mark.parametrize(
    "relative", ["../outside", "/absolute", "C:/private", "C:\\private", "", "."]
)
def test_rejects_unsafe_evidence_paths(tmp_path: Path, relative: str) -> None:
    with pytest.raises(ValueError):
        contained_path(tmp_path, relative, must_exist=False)


def test_rejects_outside_symlink_and_missing_evidence(tmp_path: Path) -> None:
    run = tmp_path / "run"
    run.mkdir()
    (run / "link").symlink_to(tmp_path)
    with pytest.raises(ValueError, match="escapes"):
        contained_path(run, "link/anything", must_exist=False)
    with pytest.raises(ValueError, match="does not exist"):
        contained_path(run, "missing.json")
