"""Execute a frozen check; a test supplies the observation, never the expected operand."""

from typing import Any

from playwright.sync_api import Locator, Page, expect

from framework.ai.contracts import TestPlan
from framework.ai.event_context import current
from framework.ai.paths import contained_path
from framework.data.content import load_row


def verify(check_id: str, actual: Any) -> None:
    context = current.get()
    if context is None:
        raise RuntimeError("Structured checks require the execution plugin")
    plan = TestPlan.model_validate_json(contained_path(context.run, "plan.json").read_text())
    matches = [
        check
        for case in plan.cases
        if case.case_id == context.case_id
        for check in case.checks
        if check.check_id == check_id
    ]
    if len(matches) != 1:
        context.record("check", check_id=check_id, outcome="failed", reason="unknown_check")
        raise AssertionError("Check does not belong to the current planned case")
    check = matches[0]
    expected = (
        load_row(check.expected_ref.data_id)[check.expected_ref.field]
        if check.expected_ref
        else check.expected
    )
    outcome = "failed"
    try:
        compare(check.operator, actual, expected)
        outcome = "passed"
    finally:
        context.record("check", check_id=check_id, operator=check.operator, outcome=outcome)


def compare(operator: str, actual: Any, expected: Any) -> None:
    if isinstance(actual, Locator):
        assertion = expect(actual)
        if operator in {"equals", "ordered_equals"}:
            assertion.to_have_text(expected)
        elif operator == "contains":
            assertion.to_contain_text(expected)
        elif operator == "count":
            assertion.to_have_count(expected)
        elif operator == "visible":
            assertion.to_be_visible() if expected else assertion.to_be_hidden()
        elif operator == "attribute_equals":
            assertion.to_have_attribute(expected["name"], expected["value"])
        elif operator == "property_equals":
            assertion.to_have_js_property(expected["name"], expected["value"])
        else:
            raise ValueError("Unsupported locator comparison")
    elif operator == "url_equals" and isinstance(actual, Page):
        expect(actual).to_have_url(expected)
    elif operator in {"equals", "ordered_equals", "url_equals", "visible"}:
        if type(actual) is not type(expected) or actual != expected:
            raise AssertionError("Observed value differs from the frozen operand")
    elif operator == "contains" and isinstance(actual, str) and isinstance(expected, str):
        if expected not in actual:
            raise AssertionError("Observed text does not contain the frozen operand")
    elif operator == "count" and isinstance(actual, (list, tuple, dict, set)):
        if len(actual) != expected:
            raise AssertionError("Observed count differs from the frozen operand")
    else:
        raise ValueError("Unsupported observation type for the frozen comparison")
