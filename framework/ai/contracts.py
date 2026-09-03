"""Versioned generation contracts. Schema validity alone is not execution proof."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")]
CaseId = Annotated[str, Field(pattern=r"^[A-Z0-9][A-Z0-9_-]{0,95}$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CaseStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class DataReference(StrictModel):
    data_id: CaseId
    field: Literal["title", "content", "tags", "comment", "expected_valid"]


class PlannedCheck(StrictModel):
    check_id: CaseId
    subject: str = Field(min_length=1, max_length=300)
    operator: Literal[
        "equals",
        "contains",
        "ordered_equals",
        "count",
        "visible",
        "url_equals",
        "attribute_equals",
        "property_equals",
    ]
    expected: JsonValue = None
    expected_ref: DataReference | None = None
    rule_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def valid_operand(self) -> PlannedCheck:
        if self.expected_ref is None and "expected" not in self.model_fields_set:
            raise ValueError("Exactly one expected operand or data reference is required")
        if self.expected_ref is not None and self.expected is not None:
            raise ValueError("Exactly one expected operand or data reference is required")
        if self.expected_ref is not None:
            if self.operator not in {"equals", "contains", "url_equals"}:
                raise ValueError("Data references are string operands")
            return self
        value = self.expected
        if self.operator in {"contains", "url_equals"} and not isinstance(value, str):
            raise ValueError("This comparison requires a string operand")
        if self.operator == "visible" and type(value) is not bool:
            raise ValueError("Visibility requires a boolean")
        if self.operator == "count" and (type(value) is not int or value < 0):
            raise ValueError("Count requires a non-negative integer")
        if self.operator == "ordered_equals" and not isinstance(value, list):
            raise ValueError("Ordered comparison requires a list")
        if self.operator in {"attribute_equals", "property_equals"} and (
            not isinstance(value, dict)
            or set(value) != {"name", "value"}
            or not isinstance(value["name"], str)
            or not value["name"]
        ):
            raise ValueError("Property comparison requires name and value")
        return self


class ExpectedResult(StrictModel):
    expectation_id: CaseId
    text: str = Field(min_length=1)
    check_ids: list[CaseId] = Field(min_length=1)


class DeclaredPhase(StrictModel):
    role: Literal["playwright-test-generator", "ai-test-data-expander"]
    phase: Literal["plan", "data", "generate-and-execute"]
    correlation_id: Identifier
    host_role_identifier: str = Field(min_length=1)
    host_call_id: str = "not_exposed_by_host"
    parent_call_id: str = "not_exposed_by_host"
    input_artifacts: dict[str, Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]] = Field(
        min_length=1
    )
    output_artifacts: dict[str, Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]] = Field(
        min_length=1
    )


class DelegationDeclaration(StrictModel):
    schema_version: Literal["2.1"] = "2.1"
    run_id: Identifier
    evidence_kind: Literal["agent_statement"] = "agent_statement"
    calls: list[DeclaredPhase] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def ordered_phases(self) -> DelegationDeclaration:
        phases = [(item.role, item.phase) for item in self.calls]
        if phases != [
            ("playwright-test-generator", "plan"),
            ("ai-test-data-expander", "data"),
            ("playwright-test-generator", "generate-and-execute"),
        ]:
            raise ValueError("Declaration requires the three ordered coordinator phases")
        if len({item.correlation_id for item in self.calls}) != 3:
            raise ValueError("Phase correlation IDs must be unique")
        return self


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
    expectations: list[ExpectedResult] = Field(default_factory=list)
    checks: list[PlannedCheck] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_reasons(self) -> PlannedCase:
        if not self.rule_ids and not self.exploratory_reason:
            raise ValueError("rule_ids or exploratory_reason is required")
        if not self.automation_candidate and not self.unsupported_reason:
            raise ValueError("unsupported_reason is required")
        if len(self.data_ids) != len(set(self.data_ids)):
            raise ValueError("duplicate data references")
        if self.expectations or self.checks:
            if [item.text for item in self.expectations] != self.expected_results:
                raise ValueError("Expectations must preserve every natural-language result")
            referenced = [key for item in self.expectations for key in item.check_ids]
            ids = [check.check_id for check in self.checks]
            if len(set(ids)) != len(ids) or sorted(referenced) != sorted(ids):
                raise ValueError("Every check must map to exactly one expectation")
            if len({item.expectation_id for item in self.expectations}) != len(self.expectations):
                raise ValueError("Expectation IDs must be unique")
            if any(not set(check.rule_ids).issubset(self.rule_ids) for check in self.checks):
                raise ValueError("Check rules must belong to the case")
            if any(not check.rule_ids for check in self.checks) and not self.exploratory_reason:
                raise ValueError("A check needs a rule basis or the case's exploratory reason")
            if any(
                check.expected_ref and check.expected_ref.data_id not in self.data_ids
                for check in self.checks
            ):
                raise ValueError("Check operand refers to undeclared case data")
        return self


class TestPlan(StrictModel):
    schema_version: Literal["2.0", "2.1"] = "2.0"
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
        check_ids = [check.check_id for case in self.cases for check in case.checks]
        expectation_ids = [item.expectation_id for case in self.cases for item in case.expectations]
        if len(set(check_ids)) != len(check_ids) or len(set(expectation_ids)) != len(
            expectation_ids
        ):
            raise ValueError("Check and expectation IDs must be globally unique")
        if self.schema_version == "2.0" and any(case.checks for case in self.cases):
            raise ValueError("Structured checks require schema 2.1")
        if self.source.startswith("trae_"):
            if len(self.cases) > 15:
                raise ValueError("AI plans have at most 15 cases")
            if len(self.cases) < 8 and not self.reduced_scope_reason:
                raise ValueError("small AI plans require reduced_scope_reason")
            if not {"host_version", "model", "mcp_version"}.issubset(self.provenance):
                raise ValueError("AI plan requires recorded host/model/MCP provenance")
            if self.schema_version == "2.1" and any(
                not case.checks for case in self.cases if case.automation_candidate
            ):
                raise ValueError("Every generated case requires structured checks")
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
    schema_version: Literal["2.0", "2.1"] = "2.0"
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
