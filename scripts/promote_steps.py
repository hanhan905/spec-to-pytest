"""Validate actual run evidence before updating ignored local step knowledge."""

import argparse
import json
from pathlib import Path

from framework.ai.contracts import StepInfoStore
from framework.ai.paths import contained_path
from framework.ai.steps import merge_verified_steps
from scripts.finalise_ai_run import finalise

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    run = args.run_dir.resolve()
    if not run.is_relative_to(ROOT / "reports/runs"):
        raise ValueError("Run must belong to this workspace")
    metadata = json.loads(contained_path(run, "run.json").read_text())
    candidates = StepInfoStore.model_validate_json(
        contained_path(run, "exploration/candidate_steps.json").read_text()
    )
    store = merge_verified_steps(
        run,
        candidates,
        finalise(run),
        metadata["application_fingerprint"],
        ROOT / ".local/knowledge/step_info.json",
    )
    print(json.dumps({"verified_local_steps": len(store.records)}))


if __name__ == "__main__":
    main()
