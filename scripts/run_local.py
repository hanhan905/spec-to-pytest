"""Execute an isolated baseline or planned generated suite and retain every attempt."""

from __future__ import annotations

import argparse
import csv
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from filelock import FileLock, Timeout

from framework.ai.acceptance import assess
from framework.ai.bindings import source_bindings
from framework.ai.contracts import PlannedCase, TestPlan
from framework.ai.integrity import (
    assertion_signatures,
    digest,
    generated_hashes,
    protected_hashes,
    require_repair_budget,
    source_files,
)
from framework.ai.repair_guard import guard_snapshot, validate_repair
from framework.ai.requests import fingerprint, finish, invocation_result, reserve, utc_now
from framework.ai.runs import create_run, write_json
from framework.runtime.service import OwnedApp, assert_serial, parse_local_url
from scripts.finalise_ai_run import finalise
from scripts.validate_ai_assets import validate_csv

ROOT = Path(__file__).resolve().parents[1]


def execute(args: argparse.Namespace, pytest_args: list[str]) -> int:
    run = args.run_dir.resolve() if args.run_dir else create_run("baseline", ROOT / "reports/runs")
    if not run.is_relative_to(ROOT / "reports/runs") or run.is_symlink():
        raise ValueError("Run must belong to this workspace")
    metadata = json.loads((run / "run.json").read_text())
    if metadata.get("schema_version") != "2.1" or metadata.get("acceptance_policy") != "2.1":
        raise ValueError("Legacy runs are read-only; create a linked new run")
    if metadata.get("run_id") != run.name:
        raise ValueError("Run identity mismatch")
    args.run_dir = run
    requested = getattr(args, "request_id", None)
    try:
        claim = json.loads(args.plan.read_text()).get("source", "") if args.plan else ""
    except (ValueError, AttributeError):
        claim = ""
    if claim.startswith("trae_") and not requested:
        raise ValueError("AI execution requires a stable --request-id")
    request_id = requested or uuid4().hex
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", request_id):
        raise ValueError("Invalid logical request identifier")
    parent = getattr(args, "parent_request_ref", None)
    reason = getattr(args, "request_reason", None)
    if parent and not re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9_-]+", parent):
        raise ValueError("Invalid parent request reference")
    (ROOT / ".local").mkdir(exist_ok=True)
    try:
        with FileLock(ROOT / ".local/request-ledger.lock", timeout=0):
            value = fingerprint(ROOT, run, args, pytest_args)
            reservation = reserve(run, request_id, value, parent_ref=parent, reason=reason)
            args.request_id, args.invocation_id = request_id, reservation.invocation_id
            invocation = {
                "schema_version": "2.1",
                "request_id": request_id,
                "invocation_id": reservation.invocation_id,
                "started_at": utc_now(),
                "pid": os.getpid(),
                "parent_pid": os.getppid(),
                "cached": reservation.cached_exit is not None,
            }
            write_json(
                run / "invocations" / f"{reservation.invocation_id}.json",
                invocation,
                exclusive=True,
            )
            if reservation.cached_exit is not None:
                code = reservation.cached_exit
                if code != 2:
                    try:
                        cached = finalise(run, write_output=False)
                        if cached.integrity_errors:
                            code = 2
                    except (ValueError, OSError, TypeError, KeyError):
                        code = 2
                cached_record = json.loads(reservation.path.read_text())
                invocation_result(
                    run,
                    reservation,
                    code=code,
                    state="cached",
                    attempt_id=cached_record.get("attempt_id"),
                )
                print(
                    json.dumps(
                        {
                            "request_id": request_id,
                            "cached": True,
                            "exit_code": code,
                            "attempt_id": cached_record.get("attempt_id"),
                        }
                    )
                )
                return code
            try:
                code = _execute_once(args, pytest_args)
            except (ValueError, OSError, KeyError, TypeError, SyntaxError):
                finish(reservation, "rejected", exit_code=2)
                invocation_result(run, reservation, code=2, state="rejected")
                raise
            except BaseException:
                finish(reservation, "interrupted", exit_code=2)
                invocation_result(run, reservation, code=2, state="interrupted")
                raise
            attempts = json.loads((run / "run.json").read_text())["attempts"]
            process = (
                json.loads((run / "attempts" / attempts[-1] / "process.json").read_text())
                if attempts
                else {}
            )
            finish(
                reservation,
                "completed" if process.get("completed") else "interrupted",
                exit_code=code,
                attempt_id=attempts[-1] if attempts else None,
            )
            invocation_result(
                run,
                reservation,
                code=code,
                state="completed" if process.get("completed") else "interrupted",
                attempt_id=attempts[-1] if attempts else None,
            )
            return code
    except Timeout:
        print(json.dumps({"request_id": request_id, "state": "in_progress_or_workbench_busy"}))
        return 2


def _execute_once(args: argparse.Namespace, pytest_args: list[str]) -> int:
    assert_serial(pytest_args)
    if any(argument.startswith("--app-url") for argument in pytest_args):
        raise ValueError(
            "Use the runner's --base-url; do not override the test application's origin"
        )
    base_url, _ = parse_local_url(args.base_url)
    (ROOT / ".local").mkdir(exist_ok=True)
    with FileLock(ROOT / ".local/workbench.lock", timeout=0):
        run_dir = (
            args.run_dir.resolve()
            if args.run_dir
            else create_run("baseline", ROOT / "reports/runs")
        )
        if not run_dir.is_relative_to(ROOT / "reports/runs"):
            raise ValueError("Run directory must be owned by this workspace")
        metadata = json.loads((run_dir / "run.json").read_text())
        if (
            not isinstance(metadata, dict)
            or not isinstance(metadata.get("attempts"), list)
            or not isinstance(metadata.get("repairs"), list)
        ):
            raise ValueError("Run metadata has an invalid structure")
        if metadata["run_id"] != run_dir.name:
            raise ValueError("Run identity mismatch")
        is_generated = args.plan is not None or metadata.get("source") not in {None, "baseline"}
        run_id = metadata["run_id"]
        if not metadata["attempts"]:
            if metadata["protected_hashes"] != protected_hashes(ROOT):
                raise ValueError("Protected inputs changed since run preparation")
            metadata["assertions"] = assertion_signatures(ROOT, run_id) if is_generated else {}
            metadata["repair_guard"] = guard_snapshot(ROOT, run_id) if is_generated else {}
            metadata["generated_hashes"] = generated_hashes(ROOT, run_id)
            metadata["source"] = "baseline"
            data = args.data or ROOT / "mana/test_data/content_base.csv"
            validate_csv(data)
            shutil.copyfile(data, run_dir / "data.csv")
            metadata["data_hash"] = digest(run_dir / "data.csv")
            if args.plan:
                plan = TestPlan.model_validate_json(args.plan.read_text())
                if plan.schema_version != "2.1":
                    raise ValueError("New execution requires a 2.1 plan")
                if plan.run_id != run_id or plan.scenario_id != metadata["scenario_id"]:
                    raise ValueError("Plan and prepared run identifiers differ")
                with (run_dir / "data.csv").open(newline="", encoding="utf-8") as stream:
                    data_ids = {row["data_id"] for row in csv.DictReader(stream)}
                rule_ids = set(
                    re.findall(
                        r"^## ([A-Z]+-\d+) —",
                        (ROOT / "mana/business_rules.md").read_text(),
                        re.MULTILINE,
                    )
                )
                if any(
                    not set(case.data_ids).issubset(data_ids)
                    or not set(case.rule_ids).issubset(rule_ids)
                    for case in plan.cases
                ):
                    raise ValueError("Plan refers to missing data IDs or unknown business rules")
                write_json(
                    run_dir / "plan.json",
                    plan.model_dump(mode="json"),
                    exclusive=not (run_dir / "plan.json").exists(),
                )
                metadata["source"] = plan.source
                metadata["plan_hash"] = digest(run_dir / "plan.json")
                write_json(run_dir / "check-bindings.json", source_bindings(ROOT, run_id, plan))
                metadata["bindings_hash"] = digest(run_dir / "check-bindings.json")
        else:
            if metadata["protected_hashes"] != protected_hashes(ROOT):
                raise ValueError("Protected project files changed; create a new run")
            if metadata["plan_hash"] != digest(run_dir / "plan.json") or metadata[
                "data_hash"
            ] != digest(run_dir / "data.csv"):
                raise ValueError("Frozen inputs changed; create a new run")
            if is_generated:
                hashes = generated_hashes(ROOT, run_id)
                if hashes != metadata["generated_hashes"]:
                    try:
                        current_guard = guard_snapshot(ROOT, run_id)
                        validate_repair(
                            metadata["repair_guard"],
                            current_guard,
                            args.repair_kind,
                            len(metadata["repairs"]),
                        )
                    except (ValueError, SyntaxError) as error:
                        proposal = run_dir / "repair-proposals" / uuid4().hex
                        previous = run_dir / "attempts" / metadata["attempts"][-1] / "source"
                        patches = []
                        for name in sorted(set(hashes) | set(metadata["generated_hashes"])):
                            old, new = previous / name, ROOT / name
                            patches.extend(
                                difflib.unified_diff(
                                    old.read_text().splitlines(True) if old.exists() else [],
                                    new.read_text().splitlines(True) if new.exists() else [],
                                    fromfile=name,
                                    tofile=name,
                                )
                            )
                        write_json(
                            proposal / "decision.json",
                            {
                                "accepted": False,
                                "reason": str(error),
                                "kind": args.repair_kind,
                                "request_id": args.request_id,
                                "recorded_at": utc_now(),
                                "before": metadata["generated_hashes"],
                                "after": hashes,
                            },
                            exclusive=True,
                        )
                        (proposal / "change.patch").write_text("".join(patches))
                        raise ValueError(
                            "Repair rejected; proposal retained; create a new run"
                        ) from error
                    if not getattr(args, "parent_request_ref", None) or not getattr(
                        args, "request_reason", None
                    ):
                        raise ValueError(
                            "Repair request must link to its prior execution and reason"
                        )
                    require_repair_budget(
                        len(metadata["repairs"]), args.repair_kind, args.repair_note
                    )
                    previous = run_dir / "attempts" / metadata["attempts"][-1]
                    collection = json.loads((previous / "collection.json").read_text())["items"]
                    changed = {
                        name
                        for name in set(hashes) | set(metadata["generated_hashes"])
                        if hashes.get(name) != metadata["generated_hashes"].get(name)
                    }
                    affected = [
                        item["case_id"]
                        for item in collection
                        if item["nodeid"].split("::")[0] in changed
                    ]
                    if any(not Path(name).name.startswith("test_") for name in changed):
                        affected = [item["case_id"] for item in collection]
                    repair = {
                        "round": len(metadata["repairs"]) + 1,
                        "kind": args.repair_kind,
                        "note": args.repair_note,
                        "case_ids": affected,
                        "before": metadata["generated_hashes"],
                        "after": hashes,
                    }
                    patch: list[str] = []
                    for name in sorted(changed):
                        before = previous / "source" / name
                        after = ROOT / name
                        patch.extend(
                            difflib.unified_diff(
                                before.read_text().splitlines(keepends=True)
                                if before.exists()
                                else [],
                                after.read_text().splitlines(keepends=True)
                                if after.exists()
                                else [],
                                fromfile=name,
                                tofile=name,
                            )
                        )
                    repair_path = run_dir / "repairs" / f"{repair['round']:02d}"
                    write_json(repair_path / "repair.json", repair, exclusive=True)
                    (repair_path / "change.patch").write_text("".join(patch))
                    metadata["repairs"].append(repair)
                    metadata["repair_guard"] = current_guard
                current = assertion_signatures(ROOT, run_id)
                metadata["assertions"], metadata["generated_hashes"] = current, hashes
        attempt_id = f"{len(metadata['attempts']) + 1:04d}"
        attempt = run_dir / "attempts" / attempt_id
        attempt.mkdir(parents=True, exist_ok=False)
        metadata["attempts"].append(attempt_id)
        write_json(run_dir / "run.json", metadata)
        for source in source_files(ROOT):
            if source.is_relative_to(ROOT / "tests/generated") and not source.is_relative_to(
                ROOT / "tests/generated" / run_id
            ):
                continue
            destination = attempt / "source" / source.relative_to(ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        default_targets = (
            [f"tests/generated/{run_id}"] if is_generated else ["tests/api", "tests/ui"]
        )
        has_target = any(
            not arg.startswith("-") and (ROOT / arg.split("::")[0]).exists() for arg in pytest_args
        )
        selection = pytest_args if has_target else [*default_targets, *pytest_args]
        command = [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "framework.plugins.execution",
            *selection,
            "--execution-dir",
            str(attempt),
            f"--junitxml={attempt / 'junit.xml'}",
            f"--alluredir={attempt / 'allure-results'}",
            f"--output={attempt / 'artifacts'}",
            "--tracing=retain-on-failure",
            "--video=retain-on-failure",
            "--screenshot=only-on-failure",
        ]
        if is_generated:
            command.append("--require-case-ids")
        process: dict[str, Any] = {
            "request_id": args.request_id,
            "invocation_id": args.invocation_id,
            "completed": False,
            "full_suite": True,
            "exit_code": None,
            "started_at": datetime.now(UTC).isoformat(),
            "command": ["python", "-m", "pytest", *selection],
            "bug_mode": args.bug_mode,
        }
        try:
            with OwnedApp(
                base_url, attempt / "app-data", attempt / "app.log", args.bug_mode
            ) as service:
                env = {
                    **os.environ,
                    "AUTO_BASE_URL": base_url,
                    "AUTO_API_URL": base_url,
                    "AUTO_INSTANCE_ID": service.instance_id,
                    "AUTO_CONTROL_TOKEN": service.control_token,
                    "AUTO_RUN_DIR": str(run_dir),
                    "AUTO_REQUEST_ID": args.request_id,
                    "AUTO_INVOCATION_ID": args.invocation_id,
                }
                with (attempt / "pytest.log").open("xb") as log:
                    result = subprocess.run(
                        command,
                        cwd=ROOT,
                        env=env,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        timeout=args.timeout,
                        check=False,
                    )
                process.update(completed=True, exit_code=result.returncode)
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
            process["environment_error"] = type(error).__name__
        process["finished_at"] = datetime.now(UTC).isoformat()
        write_json(attempt / "process.json", process, exclusive=True)
        if not is_generated and not (run_dir / "plan.json").exists():
            path = attempt / "collection.json"
            rows = json.loads(path.read_text()).get("items", []) if path.exists() else []
            if not rows:
                write_json(
                    run_dir / "blocked.json",
                    {"reason": "no_baseline_collection", "attempt": attempt_id},
                    exclusive=True,
                )
                print(json.dumps({"run_dir": str(run_dir), "quality_gate": "blocked"}))
                return 2
            plan = TestPlan(
                schema_version="2.1",
                run_id=run_id,
                scenario_id=metadata["scenario_id"],
                source="baseline",
                generated_at=datetime.now(UTC),
                provenance={"plan_basis": "pytest_collection_not_requirement_coverage"},
                cases=[
                    PlannedCase(
                        scenario_id=metadata["scenario_id"],
                        case_id=item["case_id"],
                        title=item["nodeid"],
                        exploratory_reason="Deterministic baseline regression, not AI generation",
                        steps=["Run the existing baseline"],
                        expected_results=["Existing assertions pass"],
                    )
                    for item in rows
                ],
            )
            write_json(run_dir / "plan.json", plan.model_dump(mode="json"), exclusive=True)
            metadata["plan_hash"] = digest(run_dir / "plan.json")
            write_json(run_dir / "run.json", metadata)
        receipt = {
            path.relative_to(attempt).as_posix(): digest(path)
            for path in attempt.rglob("*")
            if path.is_file()
        }
        write_json(attempt / "receipt.json", receipt, exclusive=True)
        manifest = finalise(run_dir)
        assessment = assess(run_dir, manifest)
        print(
            json.dumps(
                {
                    "run_dir": str(run_dir),
                    "quality_gate": manifest.quality_gate,
                    "workflow_gate": assessment.workflow_gate,
                    "counts": manifest.counts,
                }
            )
        )
        return {"passed": 0, "failed": 1, "blocked": 2}[manifest.quality_gate]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--data", type=Path)
    parser.add_argument(
        "--base-url", default=os.environ.get("AUTO_BASE_URL", "http://127.0.0.1:8000")
    )
    parser.add_argument("--bug-mode", choices=["healthy", "comment_counter"], default="healthy")
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--repair-kind", choices=["locator", "synchronisation"])
    parser.add_argument("--repair-note")
    parser.add_argument("--request-id")
    parser.add_argument("--parent-request-ref")
    parser.add_argument("--request-reason")
    args, remaining = parser.parse_known_args()
    try:
        return execute(args, remaining)
    except (ValueError, OSError, KeyError, TypeError, SyntaxError, RuntimeError) as error:
        print(f"Execution blocked: {type(error).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
