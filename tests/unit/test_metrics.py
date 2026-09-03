from pathlib import Path

from framework.metrics.result_metrics import metrics_from_junit


def test_metrics_from_junit(tmp_path: Path) -> None:
    report = tmp_path / "junit.xml"
    report.write_text(
        '<testsuite tests="10" failures="2" errors="1" skipped="1" time="3.5"/>',
        encoding="utf-8",
    )
    metrics = metrics_from_junit(report)
    assert metrics.passed == 6
    assert metrics.pass_rate == 6 / 9
