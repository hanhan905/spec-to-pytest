"""Test-phase context; callers cannot choose a case ID in the check-helper API."""

from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TestContext:
    run: Path
    case_id: str
    nodeid: str
    phase: str
    emit: Callable[[dict[str, Any]], None]

    def record(self, kind: str, **values: Any) -> None:
        self.emit(
            {
                "kind": kind,
                "case_id": self.case_id,
                "nodeid": self.nodeid,
                "phase": self.phase,
                **values,
            }
        )


current: ContextVar[TestContext | None] = ContextVar("test_execution_context", default=None)
