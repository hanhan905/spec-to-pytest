"""Allocate a new run; this does not claim anything has been generated or executed."""

import argparse
from pathlib import Path

from framework.ai.runs import create_run

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario_id")
    parser.add_argument("--origin", default="http://127.0.0.1:8000")
    parser.add_argument("--parent-run")
    args = parser.parse_args()
    print(
        create_run(
            args.scenario_id,
            ROOT / "reports/runs",
            exploration_origin=args.origin,
            parent_run_id=args.parent_run,
        )
    )


if __name__ == "__main__":
    main()
