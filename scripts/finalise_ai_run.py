"""Rebuild a summary from pytest/JUnit facts, never from an agent's result text."""

import argparse
import json
import sys
from pathlib import Path

from framework.ai.contracts import RunManifest, TestPlan
from framework.ai.integrity import digest, protected_hashes
from framework.ai.paths import contained_path
from framework.ai.reconcile import reconcile
from framework.ai.runs import write_summary

ROOT = Path(__file__).resolve().parents[1]


def finalise(run_dir: Path, *, write_output: bool = True) -> RunManifest:
    metadata = json.loads(contained_path(run_dir, "run.json").read_text())
    plan = TestPlan.model_validate_json(contained_path(run_dir, "plan.json").read_text())
    policy = metadata.get("acceptance_policy")
    legacy = metadata.get("schema_version") in {None, "2.0"} and policy is None
    if legacy:
        stored = RunManifest.model_validate_json(
            contained_path(run_dir, "manifest.json").read_text()
        )
        if plan.schema_version != "2.0" or stored.schema_version != "2.0":
            raise ValueError("Inconsistent legacy evidence version")
        if write_output:
            raise ValueError("Legacy runs are read-only; inspect without writing")
    elif metadata.get("schema_version") != "2.1" or policy != "2.1" or plan.schema_version != "2.1":
        raise ValueError("Unknown or inconsistent run policy")
    attempts = metadata["attempts"]
    if not attempts:
        raise ValueError("No execution attempt exists")
    errors: list[str] = []
    if not legacy and metadata.get("protected_hashes") != protected_hashes(ROOT):
        errors.append("protected_inputs_changed")
    if metadata.get("plan_hash") != digest(contained_path(run_dir, "plan.json")):
        errors.append("frozen_plan_changed")
    if metadata.get("data_hash") != digest(contained_path(run_dir, "data.csv")):
        errors.append("frozen_data_changed")
    if metadata.get("bindings_hash") and metadata["bindings_hash"] != digest(
        contained_path(run_dir, "check-bindings.json")
    ):
        errors.append("frozen_check_bindings_changed")
    for attempt_id in attempts:
        try:
            receipt = json.loads(
                contained_path(run_dir, f"attempts/{attempt_id}/receipt.json").read_text()
            )
            for name, expected in receipt.items():
                if digest(contained_path(run_dir, f"attempts/{attempt_id}/{name}")) != expected:
                    errors.append("attempt_evidence_changed")
            if legacy:
                for name, expected in metadata.get("protected_hashes", {}).items():
                    if (
                        digest(contained_path(run_dir, f"attempts/{attempt_id}/source/{name}"))
                        != expected
                    ):
                        errors.append("legacy_source_snapshot_changed")
        except (ValueError, OSError):
            errors.append("missing_attempt_evidence")
    result = reconcile(run_dir, attempts[-1], integrity_errors=errors)
    for case in result.results:
        case.attempt_ids = list(attempts)
        case.repair_attempts = sum(
            case.case_id in repair["case_ids"] for repair in metadata["repairs"]
        )
        case.passed_after_repair = case.status == "passed" and case.repair_attempts > 0
    if write_output:
        write_summary(run_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--write", action="store_true", help="New 2.1 runs only")
    args = parser.parse_args()
    try:
        result = finalise(args.run_dir.resolve(), write_output=args.write)
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"Evidence validation blocked: {type(error).__name__}", file=sys.stderr)
        raise SystemExit(2) from None
    print(json.dumps({"quality_gate": result.quality_gate, "counts": result.counts}))
    raise SystemExit({"passed": 0, "failed": 1, "blocked": 2}[result.quality_gate])


if __name__ == "__main__":
    main()
