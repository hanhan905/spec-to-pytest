import pytest

from framework.ai.repair_guard import signature, validate_repair

SOURCE = """from framework.ai import actions
def test_case(page):
    actions.click(page, "SUBMIT", role="button", name="Wrong", timeout=5000)
    response = page.request.get("http://127.0.0.1:8765/api/posts")
    assert response.status == 401
"""


def snapshot(source: str) -> dict[str, dict[str, str]]:
    return {
        "test_case.py": {
            kind: signature(source, category=kind) for kind in ("locator", "synchronisation")
        }
    }


def test_registered_selector_and_timeout_repairs_are_allowed() -> None:
    validate_repair(
        snapshot(SOURCE), snapshot(SOURCE.replace('name="Wrong"', 'name="登录"')), "locator", 0
    )
    validate_repair(
        snapshot(SOURCE),
        snapshot(SOURCE.replace("timeout=5000", "timeout=6000")),
        "synchronisation",
        1,
    )


@pytest.mark.parametrize(
    "change",
    [
        'response = type("Result", (), {"status": 401})()',
        "page = object()",
        "import httpx",
        "assert True",
    ],
)
def test_unchanged_assertion_does_not_allow_surrounding_semantics_to_change(change: str) -> None:
    changed = SOURCE.replace(
        "    assert response.status", f"    {change}\n    assert response.status"
    )
    with pytest.raises(ValueError, match="frozen source"):
        validate_repair(snapshot(SOURCE), snapshot(changed), "locator", 0)


def test_api_path_condition_and_nonregistered_locator_are_frozen() -> None:
    for changed in (
        SOURCE.replace("/api/posts", "/api/other"),
        SOURCE.replace("== 401", "!= 401"),
        SOURCE.replace('role="button"', 'role="link"'),
    ):
        with pytest.raises(ValueError):
            validate_repair(snapshot(SOURCE), snapshot(changed), "locator", 0)
    normal = "def test_case(page):\n    page.get_by_label('Wrong').click()\n    assert True\n"
    with pytest.raises(ValueError):
        validate_repair(snapshot(normal), snapshot(normal.replace("Wrong", "Right")), "locator", 0)


@pytest.mark.parametrize("timeout", ["0", "-1", "30001", "True", "float('inf')"])
def test_timeout_limits(timeout: str) -> None:
    with pytest.raises(ValueError):
        snapshot(SOURCE.replace("timeout=5000", f"timeout={timeout}"))


def test_fourth_round_and_api_repair_categories_are_rejected() -> None:
    for kind, count in [("locator", 3), ("syntax", 0), ("data", 0)]:
        with pytest.raises(ValueError):
            validate_repair(snapshot(SOURCE), snapshot(SOURCE), kind, count)


def test_action_results_cannot_be_used_as_observations() -> None:
    with pytest.raises(ValueError, match="standalone"):
        snapshot(SOURCE.replace("    actions.click", "    result = actions.click"))
