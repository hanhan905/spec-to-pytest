"""Separate an execution result from evidence-backed, explicitly reviewed AI claims."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import Field

from framework.ai.bindings import contract_errors
from framework.ai.contracts import (
    DelegationDeclaration,
    Identifier,
    RunManifest,
    StrictModel,
    TestPlan,
)
from framework.ai.integrity import digest
from framework.ai.paths import contained_path
from framework.ai.runs import write_json

ROLES = [
    "playwright-test-generator:plan",
    "ai-test-data-expander:data",
    "playwright-test-generator:generate-and-execute",
]


class WorkflowAssessment(StrictModel):
    schema_version: Literal["2.1"] = "2.1"
    acceptance_policy: Literal["2.1"] = "2.1"
    assessment_id: Identifier
    run_id: Identifier
    final_attempt: Identifier
    assessed_at: datetime
    execution_gate: Literal["passed", "failed", "blocked"]
    workflow_gate: Literal["verified", "unverified", "rejected", "not_applicable"]
    reasons: list[str] = Field(default_factory=list)
    evidence_basis: dict[str, str] = Field(default_factory=dict)
    reviewed_artifacts: dict[str, str] = Field(default_factory=dict)
    review_id: str | None = None


def artifact_basis(run: Path, manifest: RunManifest) -> dict[str, str]:
    paths = [
        "candidate-delegations.json",
        "run.json",
        "plan.json",
        "data.csv",
        "check-bindings.json",
        f"attempts/{manifest.final_attempt}/receipt.json",
    ]
    paths.extend(
        p.relative_to(run).as_posix()
        for p in sorted((run / "exploration/mcp").glob("*/receipt.json"))
    )
    return {name: digest(contained_path(run, name)) for name in paths if (run / name).is_file()}


def assess(
    run: Path, manifest: RunManifest, *, review_path: Path | None = None
) -> WorkflowAssessment:
    metadata = json.loads(contained_path(run, "run.json").read_text())
    result = WorkflowAssessment(
        assessment_id=uuid4().hex,
        run_id=manifest.run_id,
        final_attempt=manifest.final_attempt,
        assessed_at=datetime.now(UTC),
        execution_gate=manifest.quality_gate,
        workflow_gate="unverified",
    )
    if metadata.get("acceptance_policy") != "2.1":
        result.reasons = ["legacy_run_not_assessed_under_policy_2_1"]
        return result
    if not manifest.source.startswith("trae_"):
        result.workflow_gate = "not_applicable"
        result.reasons = ["source_does_not_claim_fresh_ai_generation"]
        return result
    rejected = list(manifest.integrity_errors)
    pending: list[str] = []
    if manifest.source == "trae_orchestrated":
        declaration_path = run / "candidate-delegations.json"
        if not declaration_path.exists():
            pending.append("phase_artifact_declaration_missing")
        else:
            try:
                declaration = DelegationDeclaration.model_validate_json(
                    declaration_path.read_text()
                )
                if declaration.run_id != manifest.run_id:
                    raise ValueError("Declaration belongs to another run")
                for call in declaration.calls:
                    for name, expected in [
                        *call.input_artifacts.items(),
                        *call.output_artifacts.items(),
                    ]:
                        if digest(contained_path(run, name)) != expected:
                            raise ValueError("Declared phase artifact changed")
                result.evidence_basis["phase_mapping"] = "agent_statement_not_independent_proof"
            except (ValueError, OSError, TypeError, KeyError):
                rejected.append("invalid_or_stale_phase_declaration")
    try:
        plan = TestPlan.model_validate_json(contained_path(run, "plan.json").read_text())
        events = [
            json.loads(line)
            for line in contained_path(run, f"attempts/{manifest.final_attempt}/events.jsonl")
            .read_text()
            .splitlines()
            if line
        ]
        collection = json.loads(
            contained_path(run, f"attempts/{manifest.final_attempt}/collection.json").read_text()
        )
        bindings = json.loads(contained_path(run, "check-bindings.json").read_text())
        mapping = {item["case_id"]: item["nodeid"] for item in collection["items"]}
        rejected.extend(contract_errors(plan, events, bindings, mapping))
        result.reviewed_artifacts = artifact_basis(run, manifest)
    except (ValueError, OSError, KeyError, TypeError):
        rejected.append("invalid_contract_evidence")
    from framework.ai.mcp_evidence import inspect_mcp

    mcp_state, mcp_reasons = inspect_mcp(run)
    result.evidence_basis["mcp"] = mcp_state
    (rejected if mcp_state == "rejected" else pending).extend(mcp_reasons)
    if review_path is None:
        pending.append("maintainer_semantic_review_required")
        if manifest.source == "trae_orchestrated":
            pending.append("reviewed_host_delegation_evidence_required")
    else:
        try:
            resolved = contained_path(run, review_path.relative_to(run).as_posix())
            if not resolved.relative_to(run).as_posix().startswith("reviews/"):
                raise ValueError("Expected a maintainer review record, not a candidate declaration")
            review = json.loads(resolved.read_text())
            if review.get("schema_version") != "2.1" or review.get("run_id") != manifest.run_id:
                raise ValueError("Review identity mismatch")
            if review.get("artifact_basis") != result.reviewed_artifacts:
                raise ValueError("Reviewed artifacts have changed")
            if review.get("final_attempt") != manifest.final_attempt:
                raise ValueError("Review belongs to another attempt")
            result.review_id = resolved.relative_to(run).as_posix()
            if (
                review.get("semantic_alignment") == "approved"
                and review.get("maintainer_confirmed") is True
            ):
                result.evidence_basis["semantic_alignment"] = "maintainer_reviewed"
            elif review.get("semantic_alignment") == "rejected":
                rejected.append("maintainer_rejected_expectation_alignment")
            else:
                pending.append("maintainer_semantic_review_required")
            if manifest.source == "trae_orchestrated":
                captures = review.get("host_captures", {})
                if (
                    review.get("delegated_phases") != ROLES
                    or not captures
                    or review.get("capture_kind") not in {"host_export", "ui_capture"}
                    or review.get("maintainer_confirmed") is not True
                ):
                    pending.append("reviewed_host_delegation_evidence_required")
                else:
                    for name, expected in captures.items():
                        if (
                            not name.startswith("host/")
                            or digest(contained_path(run, name)) != expected
                        ):
                            raise ValueError("Host capture changed or is outside host evidence")
                    result.evidence_basis["delegation"] = "maintainer_reviewed_host_capture"
            else:
                result.evidence_basis["delegation"] = "single_agent_skill_route_no_delegation_claim"
        except (ValueError, OSError, KeyError, TypeError):
            rejected.append("invalid_or_stale_maintainer_review")
    if manifest.quality_gate != "passed":
        rejected.append("execution_gate_not_passed")
    result.reasons = sorted(set(rejected + pending))
    result.workflow_gate = "rejected" if rejected else "unverified" if pending else "verified"
    return result


def save_assessment(run: Path, assessment: WorkflowAssessment) -> Path:
    path = run / "assessments" / f"{assessment.assessment_id}.json"
    write_json(path, assessment.model_dump(mode="json"), exclusive=True)
    return path


def record_review(
    run: Path,
    manifest: RunManifest,
    *,
    semantic_alignment: str,
    captures: list[str],
    capture_kind: str,
    delegation_reviewed: bool,
) -> Path:
    metadata = json.loads(contained_path(run, "run.json").read_text())
    if metadata.get("acceptance_policy") != "2.1":
        raise ValueError("Legacy runs cannot receive a new-policy approval")
    if semantic_alignment not in {"approved", "rejected"}:
        raise ValueError("Explicit semantic review result required")
    evidence = {}
    for name in captures:
        if not name.startswith("host/"):
            raise ValueError("Host captures must be imported into the private run/host directory")
        evidence[name] = digest(contained_path(run, name))
    if delegation_reviewed and (not evidence or capture_kind not in {"host_export", "ui_capture"}):
        raise ValueError("Delegation review needs an actual host capture")
    review_id = uuid4().hex
    path = run / "reviews" / f"{review_id}.json"
    write_json(
        path,
        {
            "schema_version": "2.1",
            "run_id": manifest.run_id,
            "final_attempt": manifest.final_attempt,
            "created_at": datetime.now(UTC).isoformat(),
            "maintainer_confirmed": True,
            "semantic_alignment": semantic_alignment,
            "artifact_basis": artifact_basis(run, manifest),
            "host_captures": evidence,
            "capture_kind": capture_kind,
            "delegated_phases": ROLES if delegation_reviewed else [],
        },
        exclusive=True,
    )
    return path
