"""Replay a reviewed snapshot with honest source labels; never simulate an AI generation."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

from framework.ai.contracts import TestPlan
from framework.ai.integrity import digest
from framework.ai.runs import create_run, write_json
from scripts.run_local import execute

ROOT = Path(__file__).resolve().parents[1]


def replay(
    *,
    candidate: bool,
    base_url: str,
    case_ids: list[str] | None = None,
    bug_mode: str = "healthy",
    reverse: bool = False,
) -> tuple[int, Path]:
    bundle = ROOT / "examples" / ("candidates" if candidate else "approved") / "content_lifecycle"
    index = json.loads((bundle / "bundle.json").read_text())
    for relative, expected in index["files"].items():
        path = bundle / relative
        if (
            path.is_symlink()
            or not path.resolve().is_relative_to(bundle.resolve())
            or digest(path) != expected
        ):
            raise ValueError("Replay snapshot changed; review it again before running")
    plan = TestPlan.model_validate_json((bundle / "plan.json").read_text())
    if not candidate and index.get("review_status") != "maintainer_approved":
        raise ValueError("This snapshot has not been approved by its maintainer")
    chosen = set(case_ids or [case.case_id for case in plan.cases])
    if not chosen or not chosen.issubset({case.case_id for case in plan.cases}):
        raise ValueError("Unknown or empty replay selection")
    run_dir = create_run(plan.scenario_id, ROOT / "reports/runs")
    plan = plan.model_copy(
        update={
            "schema_version": "2.1",
            "run_id": run_dir.name,
            "source": "candidate_replay" if candidate else "approved_replay",
            "cases": [case for case in plan.cases if case.case_id in chosen],
            "provenance": {
                **plan.provenance,
                "bundle_sha256": digest(bundle / "bundle.json"),
                "selection": ",".join(sorted(chosen)),
            },
        }
    )
    write_json(run_dir / "candidate-plan.json", plan.model_dump(mode="json"), exclusive=True)
    target = ROOT / "tests/generated" / run_dir.name
    target.mkdir(parents=True, exist_ok=False)
    for relative in index["files"]:
        if relative.startswith("tests/test_") and any(
            relative.endswith(f"_{case}.py") for case in chosen
        ):
            shutil.copyfile(bundle / relative, target / Path(relative).name)
    args = argparse.Namespace(
        base_url=base_url,
        run_dir=run_dir,
        plan=run_dir / "candidate-plan.json",
        data=bundle / "data.csv",
        bug_mode=bug_mode,
        timeout=180,
        repair_kind=None,
        repair_note=None,
    )
    pytest_args = [target.relative_to(ROOT).as_posix(), "--browser", "chromium", "-q"]
    if reverse:
        pytest_args.append("--reverse-order")
    return execute(args, pytest_args), run_dir


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--candidate",
        action="store_true",
        help="Explicitly run the port awaiting maintainer approval",
    )
    parser.add_argument(
        "--base-url", default=os.environ.get("AUTO_BASE_URL", "http://127.0.0.1:8000")
    )
    parser.add_argument("--case", action="append")
    parser.add_argument("--bug-mode", choices=["healthy", "comment_counter"], default="healthy")
    parser.add_argument("--reverse-order", action="store_true")
    args = parser.parse_args()
    code, _ = replay(
        candidate=args.candidate,
        base_url=args.base_url,
        case_ids=args.case,
        bug_mode=args.bug_mode,
        reverse=args.reverse_order,
    )
    raise SystemExit(code)


if __name__ == "__main__":
    main()
