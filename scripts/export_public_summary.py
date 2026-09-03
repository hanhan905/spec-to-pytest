"""Export only an explicit non-identifying aggregate allowlist, never raw browser artifacts."""

import argparse
import hashlib
import json
from pathlib import Path

from framework.ai.acceptance import WorkflowAssessment, assess
from framework.ai.contracts import RunManifest
from framework.ai.runs import write_json
from scripts.finalise_ai_run import finalise

ROOT = Path(__file__).resolve().parents[1]


def public_summary(
    manifest: RunManifest, assessment: WorkflowAssessment | None = None
) -> dict[str, object]:
    return {
        "run_ref": hashlib.sha256(manifest.run_id.encode()).hexdigest()[:12],
        "quality_gate": manifest.quality_gate,
        "workflow_gate": assessment.workflow_gate if assessment else "unverified",
        "acceptance_policy": "2.1",
        "source": manifest.source,
        "planned_count": manifest.planned_count,
        "counts": dict(manifest.counts),
        "integrity_error_count": len(manifest.integrity_errors),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--review", type=Path)
    args = parser.parse_args()
    if args.review and not args.run_dir:
        raise SystemExit("Select a run explicitly when exporting a reviewed assessment")
    if args.run_dir and not args.run_dir.resolve().is_relative_to(ROOT / "reports/runs"):
        raise SystemExit("Run must belong to this workspace")
    output = ROOT / "reports/public"
    output.mkdir(parents=True, exist_ok=True)
    count = 0
    paths = (
        [args.run_dir.resolve() / "manifest.json"]
        if args.run_dir
        else sorted((ROOT / "reports/runs").glob("*/manifest.json"))
    )
    for path in paths:
        manifest = finalise(path.parent, write_output=False)
        value = public_summary(
            manifest,
            assess(
                path.parent, manifest, review_path=args.review.resolve() if args.review else None
            ),
        )
        write_json(output / f"{value['run_ref']}.json", value)
        count += 1
    print(json.dumps({"aggregate_summaries_exported": count, "raw_artifacts_exported": False}))


if __name__ == "__main__":
    main()
