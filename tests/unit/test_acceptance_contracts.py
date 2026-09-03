from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from framework.ai.bindings import contract_errors, source_bindings
from framework.ai.checks import verify
from framework.ai.contracts import ExpectedResult, PlannedCase, PlannedCheck
from framework.ai.contracts import TestPlan as Plan
from framework.ai.event_context import TestContext as Context
from framework.ai.event_context import current


def plan_fixture() -> Plan:
    return Plan(
        schema_version="2.1",
        run_id="run",
        scenario_id="fixture",
        generated_at=datetime.now(UTC),
        source="synthetic",
        cases=[
            PlannedCase(
                scenario_id="fixture",
                case_id="CASE_001",
                title="Type rejection",
                rule_ids=["MEDIA-01"],
                steps=["Submit unsupported media"],
                expected_results=["The message contains PNG"],
                expectations=[
                    ExpectedResult(
                        expectation_id="EXPECT_001",
                        text="The message contains PNG",
                        check_ids=["CHECK_001"],
                    )
                ],
                checks=[
                    PlannedCheck(
                        check_id="CHECK_001",
                        subject="error.detail",
                        operator="contains",
                        expected="PNG",
                        rule_ids=["MEDIA-01"],
                    )
                ],
            )
        ],
    )


def test_contract_roundtrip_and_reference_roundtrip() -> None:
    plan = plan_fixture()
    assert Plan.model_validate_json(plan.model_dump_json()) == plan
    check = PlannedCheck(
        check_id="CHECK_002",
        subject="post.title",
        operator="equals",
        expected_ref={"data_id": "ROW_001", "field": "title"},
        rule_ids=["POST-01"],
    )
    assert PlannedCheck.model_validate_json(check.model_dump_json()) == check


@pytest.mark.parametrize("mutation", ["text", "duplicate", "missing", "wrong-rule", "legacy"])
def test_incomplete_contracts_cannot_validate(mutation: str) -> None:
    value = plan_fixture().model_dump(mode="json")
    case = value["cases"][0]
    if mutation == "text":
        case["expectations"][0]["text"] = "Anything nonempty"
    elif mutation == "duplicate":
        case["expectations"][0]["check_ids"].append("CHECK_001")
    elif mutation == "missing":
        case["checks"] = []
    elif mutation == "wrong-rule":
        case["checks"][0]["rule_ids"] = ["OTHER-01"]
    else:
        value["schema_version"] = "2.0"
    with pytest.raises(ValidationError):
        Plan.model_validate(value)


def test_truthiness_cannot_replace_a_frozen_contains_check(tmp_path: Path) -> None:
    (tmp_path / "plan.json").write_text(plan_fixture().model_dump_json())
    events = []
    token = current.set(Context(tmp_path, "CASE_001", "test.py::test_case", "call", events.append))
    try:
        with pytest.raises(ValueError):
            verify("CHECK_001", True)
        with pytest.raises(AssertionError):
            verify("CHECK_001", "Invalid image")
        verify("CHECK_001", "Only PNG supported")
    finally:
        current.reset(token)
    assert [e["outcome"] for e in events] == ["failed", "failed", "passed"]


def test_source_and_runtime_mapping_are_both_required(tmp_path: Path) -> None:
    plan = plan_fixture()
    folder = tmp_path / "tests/generated/run"
    folder.mkdir(parents=True)
    source = folder / "test_case.py"
    source.write_text(
        "import pytest\nfrom framework.ai.checks import verify\n"
        '@pytest.mark.case_id("CASE_001")\ndef test_case():\n'
        '    verify("CHECK_001", "PNG")\n'
    )
    bindings = source_bindings(tmp_path, "run", plan)
    mapping = {"CASE_001": bindings[0]["nodeid"]}
    event = {
        "kind": "check",
        "case_id": "CASE_001",
        "nodeid": mapping["CASE_001"],
        "phase": "call",
        "check_id": "CHECK_001",
        "operator": "contains",
        "outcome": "passed",
    }
    assert contract_errors(plan, [event], bindings, mapping) == []
    for events in (
        [],
        [event, event],
        [{**event, "phase": "setup"}],
        [{**event, "outcome": "failed"}],
        [{**event, "operator": "equals"}],
    ):
        assert contract_errors(plan, events, bindings, mapping)
    source.write_text(source.read_text().replace('verify("CHECK_001", "PNG")', "assert True"))
    with pytest.raises(ValueError, match="exactly one"):
        source_bindings(tmp_path, "run", plan)
