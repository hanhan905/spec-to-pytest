"""Rebuild a summary from pytest/JUnit facts, never from an agent's result text."""

import argparse
import json
from pathlib import Path

from framework.ai.contracts import RunManifest
from framework.ai.integrity import digest, protected_hashes
from framework.ai.paths import contained_path
from framework.ai.reconcile import reconcile
from framework.ai.runs import write_summary

ROOT = Path(__file__).resolve().parents[1]


def finalise(run_dir: Path) -> RunManifest:
    metadata = json.loads(contained_path(run_dir, "run.json").read_text())
    attempts = metadata["attempts"]
    if not attempts:
        raise ValueError("No execution attempt exists")
    errors: list[str] = []
    if metadata.get("protected_hashes") != protected_hashes(ROOT):
        errors.append("protected_inputs_changed")
    if metadata.get("plan_hash") != digest(contained_path(run_dir, "plan.json")):
        errors.append("frozen_plan_changed")
    if metadata.get("data_hash") != digest(contained_path(run_dir, "data.csv")):
        errors.append("frozen_data_changed")
    for attempt_id in attempts:
        try:
            receipt = json.loads(
                contained_path(run_dir, f"attempts/{attempt_id}/receipt.json").read_text()
            )
            for name, expected in receipt.items():
                if digest(contained_path(run_dir, f"attempts/{attempt_id}/{name}")) != expected:
                    errors.append("attempt_evidence_changed")
        except (ValueError, OSError):
            errors.append("missing_attempt_evidence")
    result = reconcile(run_dir, attempts[-1], integrity_errors=errors)
    for case in result.results:
        case.repair_attempts = sum(
            case.case_id in repair["case_ids"] for repair in metadata["repairs"]
        )
    write_summary(run_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    result = finalise(args.run_dir.resolve())
    print(json.dumps({"quality_gate": result.quality_gate, "counts": result.counts}))
    raise SystemExit({"passed": 0, "failed": 1, "blocked": 2}[result.quality_gate])


if __name__ == "__main__":
    main()
