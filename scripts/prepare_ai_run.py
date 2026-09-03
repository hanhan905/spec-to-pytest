"""Allocate a new run; this does not claim anything has been generated or executed."""

import argparse
from pathlib import Path

from framework.ai.runs import create_run

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario_id")
    args = parser.parse_args()
    print(create_run(args.scenario_id, ROOT / "reports/runs"))


if __name__ == "__main__":
    main()
