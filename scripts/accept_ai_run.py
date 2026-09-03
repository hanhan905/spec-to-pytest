"""Read-only by default; a zero exit means reviewed AI-workflow acceptance, not just green tests."""

import argparse
import json
import sys
from pathlib import Path

from framework.ai.acceptance import assess, save_assessment
from scripts.finalise_ai_run import finalise

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()
    run = args.run_dir.resolve()
    if not run.is_relative_to(ROOT / "reports/runs"):
        raise SystemExit("Run must belong to this workspace")
    try:
        manifest = finalise(run, write_output=False)
        review = args.review.resolve() if args.review else None
        assessment = assess(run, manifest, review_path=review)
        if args.save:
            metadata = json.loads((run / "run.json").read_text())
            if metadata.get("acceptance_policy") != "2.1":
                raise ValueError("Legacy runs cannot be modified")
            save_assessment(run, assessment)
        print(assessment.model_dump_json(indent=2))
    except (ValueError, OSError, TypeError, KeyError):
        print("Acceptance blocked: invalid or incomplete evidence", file=sys.stderr)
        raise SystemExit(2) from None
    raise SystemExit(
        {"verified": 0, "rejected": 1, "unverified": 2, "not_applicable": 2}[
            assessment.workflow_gate
        ]
    )


if __name__ == "__main__":
    main()
