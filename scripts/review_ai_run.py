"""Maintainer-only review record; never part of automatic generation or execution."""

import argparse
from pathlib import Path

from framework.ai.acceptance import record_review
from scripts.finalise_ai_run import finalise

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--semantic-alignment", choices=["approved", "rejected"], required=True)
    parser.add_argument("--host-evidence", action="append", default=[])
    parser.add_argument(
        "--capture-kind", choices=["host_export", "ui_capture"], default="ui_capture"
    )
    parser.add_argument("--delegation-reviewed", action="store_true")
    parser.add_argument("--confirm-maintainer-review", action="store_true")
    args = parser.parse_args()
    if not args.confirm_maintainer_review:
        raise SystemExit(
            "A maintainer must explicitly review the contracts and evidence; "
            "agents must not self-approve"
        )
    run = args.run_dir.resolve()
    if not run.is_relative_to(ROOT / "reports/runs"):
        raise SystemExit("Run must belong to this workspace")
    manifest = finalise(run, write_output=False)
    print(
        record_review(
            run,
            manifest,
            semantic_alignment=args.semantic_alignment,
            captures=args.host_evidence,
            capture_kind=args.capture_kind,
            delegation_reviewed=args.delegation_reviewed,
        )
    )


if __name__ == "__main__":
    main()
