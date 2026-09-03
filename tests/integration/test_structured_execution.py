"""A deterministic authored contract fixture, not a newly AI-generated scenario."""

import argparse
import json
import socket
from datetime import UTC, datetime
from pathlib import Path

from framework.ai.bindings import contract_errors
from framework.ai.contracts import ExpectedResult, PlannedCase, PlannedCheck
from framework.ai.contracts import TestPlan as Plan
from framework.ai.integrity import digest
from framework.ai.runs import create_run, write_json
from scripts.run_local import execute

ROOT = Path(__file__).resolve().parents[2]


def test_structured_ui_check_data_trace_and_cached_execution() -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        origin = f"http://127.0.0.1:{probe.getsockname()[1]}"
    run = create_run("structured-fixture", ROOT / "reports/runs")
    target = ROOT / "tests/generated" / run.name
    target.mkdir(parents=True)
    (target / "test_publish.py").write_text("""import pytest
from framework.ai.checks import verify
from framework.data.content import post_data
from framework.pages.publish_page import PublishPage

@pytest.mark.case_id("STRUCTURED_001")
def test_publish(authenticated_page, settings):
    post = post_data("BASE_001")
    publish = PublishPage(authenticated_page, settings.base_url).open().fill(post).publish()
    verify("CHECK_SUCCESS", publish.success)
""")
    plan = Plan(
        schema_version="2.1",
        run_id=run.name,
        scenario_id="structured-fixture",
        generated_at=datetime.now(UTC),
        source="synthetic",
        cases=[
            PlannedCase(
                scenario_id="structured-fixture",
                case_id="STRUCTURED_001",
                title="Contract helper fixture",
                rule_ids=["POST-01"],
                data_ids=["BASE_001"],
                steps=["Publish a synthetic post"],
                expected_results=["The publish success message is visible"],
                expectations=[
                    ExpectedResult(
                        expectation_id="EXPECT_SUCCESS",
                        text="The publish success message is visible",
                        check_ids=["CHECK_SUCCESS"],
                    )
                ],
                checks=[
                    PlannedCheck(
                        check_id="CHECK_SUCCESS",
                        subject="publish.status",
                        operator="equals",
                        expected="内容发布成功！",
                        rule_ids=["POST-01"],
                    )
                ],
            )
        ],
    )
    write_json(run / "candidate-plan.json", plan.model_dump(mode="json"))
    args = argparse.Namespace(
        run_dir=run,
        base_url=origin,
        plan=run / "candidate-plan.json",
        data=None,
        bug_mode="healthy",
        timeout=60,
        repair_kind=None,
        repair_note=None,
        request_id="one-logical-request",
        parent_request_ref=None,
        request_reason=None,
    )
    selection = [target.relative_to(ROOT).as_posix(), "--browser", "chromium", "-q"]
    assert execute(args, selection) == 0
    metadata = json.loads((run / "run.json").read_text())
    assert metadata["attempts"] == ["0001"]
    attempt = run / "attempts/0001"
    events = [json.loads(line) for line in (attempt / "events.jsonl").read_text().splitlines()]
    bindings = json.loads((run / "check-bindings.json").read_text())
    collection = json.loads((attempt / "collection.json").read_text())
    mapping = {item["case_id"]: item["nodeid"] for item in collection["items"]}
    assert contract_errors(plan, events, bindings, mapping) == []
    receipt_hash = digest(attempt / "receipt.json")
    assert execute(args, selection) == 0
    assert json.loads((run / "run.json").read_text())["attempts"] == ["0001"]
    original = (attempt / "pytest.log").read_bytes()
    try:
        (attempt / "pytest.log").write_bytes(original + b"synthetic tamper")
        assert execute(args, selection) == 2
    finally:
        (attempt / "pytest.log").write_bytes(original)
    assert digest(attempt / "receipt.json") == receipt_hash
