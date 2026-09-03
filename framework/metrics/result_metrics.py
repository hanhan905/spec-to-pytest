"""Calculate shareable run metrics from standard JUnit XML."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from xml.etree import ElementTree


@dataclass(frozen=True, slots=True)
class RunMetrics:
    tests: int
    passed: int
    failures: int
    errors: int
    skipped: int
    duration_seconds: float

    @property
    def pass_rate(self) -> float:
        executed = self.tests - self.skipped
        return self.passed / executed if executed else 0.0

    def as_dict(self) -> dict[str, int | float]:
        return {**asdict(self), "pass_rate": round(self.pass_rate, 4)}


def metrics_from_junit(path: Path) -> RunMetrics:
    root = ElementTree.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    tests = sum(int(suite.attrib.get("tests", 0)) for suite in suites)
    failures = sum(int(suite.attrib.get("failures", 0)) for suite in suites)
    errors = sum(int(suite.attrib.get("errors", 0)) for suite in suites)
    skipped = sum(int(suite.attrib.get("skipped", 0)) for suite in suites)
    duration = sum(float(suite.attrib.get("time", 0)) for suite in suites)
    return RunMetrics(
        tests=tests,
        passed=tests - failures - errors - skipped,
        failures=failures,
        errors=errors,
        skipped=skipped,
        duration_seconds=round(duration, 3),
    )
