from pathlib import Path

import pytest

from framework.ai.requests import finish, reserve


def test_completed_request_is_cached_and_identity_conflicts_are_rejected(tmp_path: Path) -> None:
    first = reserve(tmp_path, "request_1", "abc", parent_ref=None, reason=None)
    finish(first, "completed", exit_code=0, attempt_id="0001")
    second = reserve(tmp_path, "request_1", "abc", parent_ref=None, reason=None)
    assert second.cached_exit == 0
    assert first.invocation_id != second.invocation_id
    assert len(list((tmp_path / "requests").glob("*.json"))) == 1
    with pytest.raises(ValueError, match="different inputs"):
        reserve(tmp_path, "request_1", "def", parent_ref=None, reason=None)


def test_running_or_interrupted_request_never_starts_again(tmp_path: Path) -> None:
    first = reserve(tmp_path, "request_1", "abc", parent_ref=None, reason=None)
    with pytest.raises(RuntimeError, match="in progress"):
        reserve(tmp_path, "request_1", "abc", parent_ref=None, reason=None)
    finish(first, "interrupted", exit_code=2)
    assert reserve(tmp_path, "request_1", "abc", parent_ref=None, reason=None).cached_exit == 2
    with pytest.raises(ValueError, match="linked new run"):
        reserve(tmp_path, "request_2", "abc", parent_ref=None, reason="retry")


def test_repeat_requires_explicit_reason(tmp_path: Path) -> None:
    first = reserve(tmp_path, "request_1", "abc", parent_ref=None, reason=None)
    finish(first, "completed", exit_code=1)
    with pytest.raises(ValueError, match="intentional repeat"):
        reserve(tmp_path, "request_2", "abc", parent_ref=None, reason=None)
    assert (
        reserve(
            tmp_path, "request_2", "abc", parent_ref=None, reason="Documented repeat"
        ).cached_exit
        is None
    )
