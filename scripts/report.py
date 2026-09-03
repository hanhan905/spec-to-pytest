"""Generate a new local Allure view without overwriting any execution attempt."""

import argparse
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

from framework.ai.paths import contained_path
from scripts.finalise_ai_run import finalise

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "run_dir", nargs="?", type=Path, help="Defaults to the most recently summarized run"
    )
    args = parser.parse_args()
    if args.run_dir:
        run = args.run_dir.resolve()
    else:
        manifests = list((ROOT / "reports/runs").glob("*/manifest.json"))
        if not manifests:
            raise SystemExit("No summarized run exists; run the baseline first.")
        run = max(manifests, key=lambda item: item.stat().st_mtime).parent
    if not run.is_relative_to(ROOT / "reports/runs"):
        raise SystemExit("Reports must belong to this workspace.")
    command = shutil.which("allure")
    if command is None:
        raise SystemExit(
            "Optional Allure CLI is not installed. JSON/JUnit results remain available."
        )
    manifest = finalise(run, write_output=False)
    if manifest.integrity_errors:
        raise SystemExit(
            "Evidence is stale or incomplete; inspect raw artifacts before rendering a report."
        )
    inputs = contained_path(run, f"attempts/{manifest.final_attempt}/allure-results")
    output = ROOT / "reports/views" / run.name / f"allure-{uuid4().hex[:8]}"
    subprocess.run([command, "generate", str(inputs), "-o", str(output)], check=True)
    print(output)


if __name__ == "__main__":
    main()
