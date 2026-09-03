"""Join frozen intentions to independent process, pytest event and JUnit evidence."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from xml.etree import ElementTree

from framework.ai.contracts import CaseRunResult, CaseStatus, RunManifest, TestPlan
from framework.ai.paths import contained_path


def load_evidence(root: Path, name: str, errors: list[str]) -> Any:
    try:
        return json.loads(contained_path(root, name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        errors.append(f"invalid_or_missing_{name}")
        return {}


def reconcile(
    run_dir: Path, attempt_id: str, *, integrity_errors: list[str] | None = None
) -> RunManifest:
    plan = TestPlan.model_validate_json(contained_path(run_dir, "plan.json").read_text())
    errors = list(integrity_errors or [])
    attempt = contained_path(run_dir, f"attempts/{attempt_id}")
    collection = load_evidence(attempt, "collection.json", errors)
    process = load_evidence(attempt, "process.json", errors)
    if not isinstance(collection, dict) or not isinstance(process, dict):
        errors.append("invalid_evidence_structure")
        collection, process = {}, {}
    items = collection.get("items", [])
    if not isinstance(items, list) or any(
        not isinstance(item, dict)
        or not isinstance(item.get("nodeid"), str)
        or not isinstance(item.get("case_id"), str)
        for item in items
    ):
        errors.append("invalid_collection_items")
        items = []
    if collection.get("errors"):
        errors.append("collection_mapping_error")
    mapping = {item["case_id"]: item["nodeid"] for item in items}
    if len(mapping) != len(items) or len({item["nodeid"] for item in items}) != len(items):
        errors.append("duplicate_case_or_nodeid")
    expected = {case.case_id for case in plan.cases if case.automation_candidate}
    if set(mapping) != expected:
        errors.append("planned_and_collected_cases_differ")
    if not items:
        errors.append("zero_collection")
    try:
        events = [
            json.loads(line)
            for line in contained_path(attempt, "events.jsonl").read_text().splitlines()
            if line
        ]
        if any(not isinstance(event, dict) for event in events):
            raise ValueError("invalid event")
    except (OSError, ValueError):
        errors.append("invalid_or_missing_events")
        events = []
    starts = [event for event in events if event.get("kind") == "session_start"]
    finishes = [event for event in events if event.get("kind") == "session_finish"]
    if len(starts) != 1 or len(finishes) != 1:
        errors.append("incomplete_session_events")
    elif events[0].get("kind") != "session_start" or events[-1].get("kind") != "session_finish":
        errors.append("event_sequence_invalid")
    if plan.schema_version == "2.1" and (
        not process.get("request_id")
        or not process.get("invocation_id")
        or len(starts) != 1
        or starts[0].get("request_id") != process.get("request_id")
        or starts[0].get("invocation_id") != process.get("invocation_id")
    ):
        errors.append("request_invocation_identity_mismatch")
    if (
        type(process.get("exit_code")) is not int
        or process.get("exit_code") not in (0, 1)
        or process.get("completed") is not True
        or process.get("full_suite") is not True
    ):
        errors.append("process_not_a_completed_acceptance_run")
    if finishes and (
        finishes[-1].get("exitstatus") != process.get("exit_code")
        or finishes[-1].get("collected") != len(items)
    ):
        errors.append("process_session_mismatch")
    reports: dict[str, dict[str, dict[str, Any]]] = {}
    for event in events:
        if event.get("kind") != "report":
            continue
        case_id, nodeid, phase = event.get("case_id"), event.get("nodeid"), event.get("phase")
        if (
            not isinstance(case_id, str)
            or not isinstance(phase, str)
            or not isinstance(event.get("outcome"), str)
            or case_id not in mapping
            or mapping.get(case_id) != nodeid
            or phase not in {"setup", "call", "teardown"}
            or event.get("outcome") not in {"passed", "failed", "skipped"}
        ):
            errors.append("unmapped_or_invalid_report")
            continue
        if phase in reports.setdefault(case_id, {}):
            errors.append("duplicate_phase_report")
        reports[case_id][phase] = event
        if event.get("wasxfail") or event.get("outcome") == "skipped":
            errors.append("unexpected_skip_or_xfail")

    junit: dict[str, str] = {}
    try:
        root = ElementTree.parse(contained_path(attempt, "junit.xml")).getroot()
        if root.tag not in {"testsuites", "testsuite"}:
            raise ValueError("invalid JUnit root")
        for suite in root.iter("testsuite"):
            entries = suite.findall("testcase")
            if int(suite.get("tests", "-1")) != len(entries):
                errors.append("junit_declared_count_mismatch")
            for attribute, child in (
                ("failures", "failure"),
                ("errors", "error"),
                ("skipped", "skipped"),
            ):
                if int(suite.get(attribute, "-1")) != sum(
                    entry.find(child) is not None for entry in entries
                ):
                    errors.append("junit_declared_count_mismatch")
        for testcase in root.iter("testcase"):
            property_rows = testcase.findall("./properties/property")
            properties = {prop.get("name"): prop.get("value") for prop in property_rows}
            if any(
                sum(prop.get("name") == key for prop in property_rows) != 1
                for key in ("case_id", "nodeid")
            ):
                errors.append("ambiguous_junit_properties")
            junit_case = properties.get("case_id")
            if (
                not junit_case
                or junit_case in junit
                or mapping.get(junit_case) != properties.get("nodeid")
            ):
                errors.append("invalid_or_duplicate_junit_mapping")
                continue
            junit[junit_case] = (
                "error"
                if testcase.find("error") is not None
                else "failed"
                if testcase.find("failure") is not None
                else "skipped"
                if testcase.find("skipped") is not None
                else "passed"
            )
        if set(junit) != expected:
            errors.append("junit_case_set_mismatch")
    except (OSError, ValueError, ElementTree.ParseError):
        errors.append("invalid_or_missing_junit")

    results: list[CaseRunResult] = []
    for case in plan.cases:
        status, reason = CaseStatus.BLOCKED, "incomplete_execution_evidence"
        failure_phase: Any = "mapping"
        if not case.automation_candidate:
            status, reason, failure_phase = (
                CaseStatus.SKIPPED,
                case.unsupported_reason or "unsupported",
                None,
            )
        else:
            stages = reports.get(case.case_id, {})
            outcomes = {phase: event["outcome"] for phase, event in stages.items()}
            expected_sequence = (
                ["setup", "call", "teardown"]
                if outcomes.get("setup") == "passed"
                else ["setup", "teardown"]
            )
            if list(stages) != expected_sequence:
                errors.append(f"invalid_phase_sequence:{case.case_id}")
            raw = (
                "error"
                if any(outcomes.get(phase) == "failed" for phase in ("setup", "teardown"))
                else "failed"
                if outcomes.get("call") == "failed"
                else "skipped"
                if "skipped" in outcomes.values()
                else "passed"
            )
            if junit.get(case.case_id) != raw:
                errors.append(f"junit_event_mismatch:{case.case_id}")
            if outcomes.get("setup") == "failed":
                status, reason, failure_phase = CaseStatus.BLOCKED, "setup_failed", "setup"
            elif outcomes.get("teardown") == "failed":
                status, reason, failure_phase = CaseStatus.FAILED, "teardown_failed", "teardown"
            elif outcomes.get("call") == "failed":
                status, reason, failure_phase = CaseStatus.FAILED, "test_failed", "call"
            elif outcomes == {"setup": "passed", "call": "passed", "teardown": "passed"}:
                status, reason, failure_phase = (
                    CaseStatus.PASSED,
                    "all_execution_phases_passed",
                    None,
                )
            if (
                "setup" not in outcomes
                or "teardown" not in outcomes
                or (outcomes.get("setup") == "passed" and "call" not in outcomes)
            ):
                errors.append(f"missing_execution_phase:{case.case_id}")
        evidence = [
            f"attempts/{attempt_id}/{name}"
            for name in ("collection.json", "events.jsonl", "junit.xml", "process.json")
            if (attempt / name).is_file()
        ]
        media_events = reports.get(case.case_id, {}).values()
        media_expected = any(event.get("media_expected") for event in media_events)
        media_paths: list[str] = []
        for event in media_events:
            relative = event.get("artifact_dir")
            if relative is not None:
                try:
                    if not isinstance(relative, str):
                        raise ValueError("invalid artifact directory")
                    directory = contained_path(attempt, relative, must_exist=False)
                    for file in directory.rglob("*") if directory.is_dir() else []:
                        if file.is_file():
                            value = file.relative_to(run_dir).as_posix()
                            contained_path(run_dir, value)
                            media_paths.append(value)
                except ValueError:
                    errors.append(f"unsafe_artifact_path:{case.case_id}")
        evidence.extend(sorted(set(media_paths)))
        missing_media = [
            label
            for label, suffix in (("screenshot", ".png"), ("trace", ".zip"), ("video", ".webm"))
            if not any(path.endswith(suffix) for path in media_paths)
        ]
        unavailable = (
            "Not retained: " + ", ".join(missing_media)
            if media_expected
            and missing_media
            and status in {CaseStatus.FAILED, CaseStatus.BLOCKED}
            else None
        )
        results.append(
            CaseRunResult(
                case_id=case.case_id,
                nodeid=mapping.get(case.case_id),
                status=status,
                final_reason=reason,
                failure_phase=failure_phase,
                evidence_paths=evidence,
                artifact_unavailable_reason=unavailable,
            )
        )
    if process.get("exit_code") == 0 and any(
        result.status != CaseStatus.PASSED for result in results if result.nodeid
    ):
        errors.append("exit_code_hides_unsuccessful_case")
    if process.get("exit_code") == 1 and not any(
        result.status in {CaseStatus.FAILED, CaseStatus.BLOCKED} for result in results
    ):
        errors.append("nonzero_exit_without_failure")
    if errors:
        for result in results:
            if result.status == CaseStatus.PASSED:
                result.status, result.final_reason = CaseStatus.BLOCKED, "evidence_integrity_failed"
    counts = {status: sum(result.status == status for result in results) for status in CaseStatus}
    required_skipped = any(
        case.required and result.status == CaseStatus.SKIPPED
        for case, result in zip(plan.cases, results, strict=True)
    )
    gate: Literal["passed", "failed", "blocked"] = (
        "blocked"
        if errors or counts[CaseStatus.BLOCKED]
        else "failed"
        if counts[CaseStatus.FAILED] or required_skipped
        else "passed"
    )
    return RunManifest(
        schema_version=plan.schema_version,
        run_id=plan.run_id,
        scenario_id=plan.scenario_id,
        source=plan.source,
        completed=True,
        final_attempt=attempt_id,
        finished_at=datetime.now(UTC),
        quality_gate=gate,
        planned_count=len(plan.cases),
        counts=counts,
        integrity_errors=sorted(set(errors)),
        results=results,
    )
