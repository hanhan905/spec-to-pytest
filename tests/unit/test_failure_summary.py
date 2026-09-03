from framework.ai.failure_summary import summarise_failure


def test_timeout_is_classified_as_synchronisation() -> None:
    summary = summarise_failure("Timeout 5000ms exceeded")
    assert summary.category == "synchronisation"


def test_connection_refused_is_classified_as_environment() -> None:
    summary = summarise_failure("Page.goto: net::ERR_CONNECTION_REFUSED")
    assert summary.category == "environment"


def test_permission_failure_is_not_healed_as_a_locator() -> None:
    summary = summarise_failure("HTTP 403 permission denied")
    assert summary.category == "security"
    assert "Preserve the assertion" in summary.next_action
