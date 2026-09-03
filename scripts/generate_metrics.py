"""Generate a compact JSON metrics file from a JUnit result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from framework.metrics.result_metrics import metrics_from_junit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("junit", type=Path)
    parser.add_argument("--output", type=Path, default=Path("reports/metrics/latest.json"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    metrics = metrics_from_junit(args.junit)
    args.output.write_text(json.dumps(metrics.as_dict(), indent=2), encoding="utf-8")
    print(json.dumps(metrics.as_dict(), ensure_ascii=False))


if __name__ == "__main__":
    main()
