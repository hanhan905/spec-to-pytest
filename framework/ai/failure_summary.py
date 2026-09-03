"""Offline failure classification that can later feed a local LLM adapter."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FailureSummary:
    category: str
    likely_cause: str
    next_action: str


def summarise_failure(message: str) -> FailureSummary:
    lowered = message.lower()
    if "connection refused" in lowered or "err_connection_refused" in lowered:
        return FailureSummary(
            "environment",
            "The local practice application is not reachable.",
            "Start the local app and re-run without changing the test or business assertion.",
        )
    if "timeout" in lowered:
        return FailureSummary(
            "synchronisation",
            "The expected UI or network condition did not become ready in time.",
            "Inspect the trace and replace fixed waits with a user-visible condition.",
        )
    if "strict mode violation" in lowered:
        return FailureSummary(
            "locator",
            "The locator matched more than one element.",
            "Use role, accessible name, label, or a scoped component locator.",
        )
    if "401" in lowered or "403" in lowered or "permission" in lowered:
        return FailureSummary(
            "security",
            "Authentication or authorisation did not match the expected access rule.",
            "Preserve the assertion and inspect the session, role, and API response.",
        )
    if "500" in lowered or "crash" in lowered:
        return FailureSummary(
            "service",
            "A dependent service returned an internal error.",
            "Inspect the captured request and service log before changing the UI test.",
        )
    if "unsupported" in lowered or "schema" in lowered:
        return FailureSummary(
            "spec",
            "The generated case or asset does not match the supported contract.",
            "Mark unsupported cases explicitly or repair the generated structure.",
        )
    return FailureSummary(
        "assertion",
        "Observed behaviour differed from the expected business outcome.",
        "Compare the assertion, screenshot, page source, and recent network responses.",
    )
