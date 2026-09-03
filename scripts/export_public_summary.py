"""Export only an explicit non-identifying aggregate allowlist, never raw browser artifacts."""

import hashlib
import json
from pathlib import Path

from framework.ai.contracts import RunManifest
from framework.ai.runs import write_json
from scripts.finalise_ai_run import finalise

ROOT = Path(__file__).resolve().parents[1]


def public_summary(manifest: RunManifest) -> dict[str, object]:
    return {
        "run_ref": hashlib.sha256(manifest.run_id.encode()).hexdigest()[:12],
        "quality_gate": manifest.quality_gate,
        "source": manifest.source,
        "planned_count": manifest.planned_count,
        "counts": dict(manifest.counts),
        "integrity_error_count": len(manifest.integrity_errors),
    }


def main() -> None:
    output = ROOT / "reports/public"
    output.mkdir(parents=True, exist_ok=True)
    count = 0
    for path in sorted((ROOT / "reports/runs").glob("*/manifest.json")):
        manifest = finalise(path.parent, write_output=False)
        value = public_summary(manifest)
        write_json(output / f"{value['run_ref']}.json", value)
        count += 1
    print(json.dumps({"aggregate_summaries_exported": count, "raw_artifacts_exported": False}))


if __name__ == "__main__":
    main()
