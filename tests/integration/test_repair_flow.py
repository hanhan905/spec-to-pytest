"""A synthetic repair exercise; not a fresh AI generation or an application bug."""

import argparse
import json
import socket
from datetime import UTC, datetime
from pathlib import Path

import pytest

from framework.ai.contracts import PlannedCase
from framework.ai.contracts import TestPlan as PlanContract
from framework.ai.integrity import digest
from framework.ai.runs import create_run, write_json
from scripts.finalise_ai_run import finalise
from scripts.run_local import execute

ROOT = Path(__file__).resolve().parents[2]


def test_locator_repair_keeps_original_failure_and_rejects_tampered_evidence() -> None:
    with socket.socket() as port_probe:
        port_probe.bind(("127.0.0.1", 0))
        port = port_probe.getsockname()[1]
    run = create_run("synthetic-repair", ROOT / "reports/runs")
    target = ROOT / "tests/generated" / run.name
    target.mkdir(parents=True)
    test = target / "test_locator.py"
    test.write_text(
        """import pytest
from playwright.sync_api import Page, expect

from framework.config.settings import Settings
from framework.ai import actions


@pytest.mark.case_id("REPAIR_001")
def test_login(configured_page: Page, settings: Settings) -> None:
    configured_page.goto(f"{settings.base_url}/login")
    actions.fill(configured_page, "USERNAME", "admin", label="用户名（错误定位）", timeout=300)
    configured_page.get_by_label("密码").fill("admin123")
    configured_page.get_by_role("button", name="登录").click()
    expect(configured_page).to_have_url(f"{settings.base_url}/dashboard")
    profile = configured_page.request.get(f"{settings.api_url}/api/profile")
    assert profile.json()["username"] == "admin"
""",
        encoding="utf-8",
    )
    plan = PlanContract(
        schema_version="2.1",
        run_id=run.name,
        scenario_id="synthetic-repair",
        source="synthetic",
        generated_at=datetime.now(UTC),
        provenance={"purpose": "deterministic repair regression, not AI generation"},
        cases=[
            PlannedCase(
                scenario_id="synthetic-repair",
                case_id="REPAIR_001",
                title="Login locator repair fixture",
                rule_ids=["AUTH-01"],
                steps=["Log in"],
                expected_results=["Dashboard and authenticated profile are visible"],
            )
        ],
    )
    write_json(run / "candidate-plan.json", plan.model_dump(mode="json"))
    args = argparse.Namespace(
        base_url=f"http://127.0.0.1:{port}",
        run_dir=run,
        plan=run / "candidate-plan.json",
        data=None,
        bug_mode="healthy",
        timeout=60,
        repair_kind=None,
        repair_note=None,
        request_id="initial",
        parent_request_ref=None,
        request_reason=None,
    )
    selection = [target.relative_to(ROOT).as_posix(), "--browser", "chromium", "-q"]
    assert execute(args, selection) == 1
    original = run / "attempts/0001/pytest.log"
    original_content, original_hash = original.read_bytes(), digest(original)
    first = json.loads((run / "manifest.json").read_text())
    assert first["results"][0]["status"] == "failed"

    test.write_text(test.read_text().replace("用户名（错误定位）", "用户名"))
    args.repair_kind, args.repair_note = "locator", "Correct accessible label in synthetic fixture"
    args.request_id = "repair-one"
    args.parent_request_ref = f"{run.name}/initial"
    args.request_reason = "Registered locator repair"
    assert execute(args, selection) == 0
    assert digest(original) == original_hash
    repaired = finalise(run)
    assert repaired.results[0].passed_after_repair
    assert repaired.results[0].repair_attempts == 1
    assert repaired.results[0].attempt_ids == ["0001", "0002"]
    assert (run / "repairs/01/change.patch").is_file()

    try:
        original.write_bytes(original_content + b"\nsynthetic corruption probe\n")
        tampered = finalise(run)
        assert tampered.quality_gate == "blocked"
        assert "attempt_evidence_changed" in tampered.integrity_errors
    finally:
        original.write_bytes(original_content)
    assert finalise(run).quality_gate == "passed"
    original_generated = test.read_bytes()
    try:
        test.write_text(test.read_text() + "\nclass Wrapper:\n    status_code = 200\n")
        args.request_id = "rejected-wrapper"
        args.parent_request_ref = f"{run.name}/repair-one"
        args.request_reason = "Synthetic guard rejection fixture"
        with pytest.raises(ValueError, match="Repair rejected"):
            execute(args, selection)
        proposal = next((run / "repair-proposals").glob("*/decision.json"))
        decision = json.loads(proposal.read_text())
        assert decision["accepted"] is False
        assert decision["before"] != decision["after"]
        assert "class Wrapper" in (proposal.parent / "change.patch").read_text()
        assert json.loads((run / "run.json").read_text())["attempts"] == ["0001", "0002"]
    finally:
        test.write_bytes(original_generated)
    write_json(
        run / "regression-check.json",
        {
            "initial_failure_preserved": True,
            "documented_repair_passed": True,
            "tamper_detected": True,
            "evidence_restored_to_original_hash": digest(original) == original_hash,
            "fresh_ai_generation": False,
            "rejected_wrapper_patch_retained": True,
        },
    )
