"""Versioned generation contracts. Schema validity alone is not execution proof."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")]
CaseId = Annotated[str, Field(pattern=r"^[A-Z0-9][A-Z0-9_-]{0,95}$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CaseStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class PlannedCase(StrictModel):
    scenario_id: Identifier
    case_id: CaseId
    title: str = Field(min_length=1)
    priority: Literal["P0", "P1", "P2"] = "P1"
    rule_ids: list[str] = Field(default_factory=list)
    exploratory_reason: str | None = None
    preconditions: list[str] = Field(default_factory=list)
    data_ids: list[CaseId] = Field(default_factory=list)
    steps: list[str] = Field(min_length=1)
    expected_results: list[str] = Field(min_length=1)
    automation_candidate: bool = True
    unsupported_reason: str | None = None
    required: bool = True

    @model_validator(mode="after")
    def require_reasons(self) -> PlannedCase:
        if not self.rule_ids and not self.exploratory_reason:
            raise ValueError("rule_ids or exploratory_reason is required")
        if not self.automation_candidate and not self.unsupported_reason:
            raise ValueError("unsupported_reason is required")
        if len(self.data_ids) != len(set(self.data_ids)):
            raise ValueError("duplicate data references")
        return self


class TestPlan(StrictModel):
    schema_version: Literal["2.0"] = "2.0"
    run_id: Identifier
    scenario_id: Identifier
    generated_at: datetime
    source: Literal[
        "baseline",
        "synthetic",
        "approved_replay",
        "candidate_replay",
        "trae_orchestrated",
        "trae_single_agent_skill",
    ]
    provenance: dict[str, str] = Field(default_factory=dict)
    reduced_scope_reason: str | None = None
    cases: list[PlannedCase] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def consistent_plan(self) -> TestPlan:
        ids = [case.case_id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("case_id must be unique")
        if any(case.scenario_id != self.scenario_id for case in self.cases):
            raise ValueError("mixed scenario identifiers")
        if self.source.startswith("trae_"):
            if len(self.cases) > 15:
                raise ValueError("AI plans have at most 15 cases")
            if len(self.cases) < 8 and not self.reduced_scope_reason:
                raise ValueError("small AI plans require reduced_scope_reason")
            if not {"host_version", "model", "mcp_version"}.issubset(self.provenance):
                raise ValueError("AI plan requires recorded host/model/MCP provenance")
        return self


class StepInfoRecord(StrictModel):
    description: str = Field(min_length=1)
    action: str = Field(min_length=1)
    mcp_tool: str = Field(min_length=1)
    locator_strategy: Literal["role", "label", "test_id", "css"]
    selector: str = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)
    success_state: str = Field(min_length=1)
    verified_at: datetime
    source_run_id: Identifier
    source_case_id: CaseId
    app_version: str = Field(min_length=1)
    app_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    evidence_paths: list[str] = Field(min_length=1)


class DataRow(StrictModel):
    data_id: CaseId
    title: str
    content: str
    tags: str
    comment: str
    expected_valid: Literal["true", "false"]

    @model_validator(mode="after")
    def validate_expected_legality(self) -> DataRow:
        valid = (
            1 <= len(self.title.strip()) <= 50
            and 1 <= len(self.content.strip()) <= 500
            and 1 <= len(self.comment.strip()) <= 100
        )
        if (self.expected_valid == "true") != valid:
            raise ValueError("expected_valid disagrees with lifecycle text rules")
        return self


class StepInfoStore(StrictModel):
    schema_version: Literal["2.0"] = "2.0"
    records: list[StepInfoRecord] = Field(default_factory=list)


class CaseRunResult(StrictModel):
    case_id: CaseId
    nodeid: str | None = None
    status: CaseStatus
    repair_attempts: int = Field(default=0, ge=0, le=3)
    passed_after_repair: bool = False
    attempt_ids: list[Identifier] = Field(default_factory=list)
    final_reason: str = Field(min_length=1)
    failure_phase: Literal["setup", "call", "teardown", "mapping", "environment"] | None = None
    evidence_paths: list[str] = Field(default_factory=list)
    artifact_unavailable_reason: str | None = None


class RunManifest(StrictModel):
    schema_version: Literal["2.0"] = "2.0"
    run_id: Identifier
    scenario_id: Identifier
    source: Literal[
        "baseline",
        "synthetic",
        "candidate_replay",
        "approved_replay",
        "trae_orchestrated",
        "trae_single_agent_skill",
        "unrecorded",
    ] = "unrecorded"
    completed: bool
    final_attempt: Identifier
    finished_at: datetime
    quality_gate: Literal["passed", "failed", "blocked"]
    planned_count: int = Field(ge=1)
    counts: dict[CaseStatus, int]
    integrity_errors: list[str]
    results: list[CaseRunResult] = Field(min_length=1)

    @model_validator(mode="after")
    def consistent_results(self) -> RunManifest:
        ids = [result.case_id for result in self.results]
        if len(ids) != len(set(ids)) or self.planned_count != len(ids):
            raise ValueError("results must match unique planned_count")
        actual = {
            status: sum(result.status == status for result in self.results) for status in CaseStatus
        }
        if self.counts != actual:
            raise ValueError("counts do not match results")
        if self.quality_gate == "passed" and (
            self.integrity_errors
            or actual[CaseStatus.FAILED]
            or actual[CaseStatus.BLOCKED]
            or not actual[CaseStatus.PASSED]
            or not self.completed
        ):
            raise ValueError("incomplete or unsuccessful results cannot pass the quality gate")
        return self
