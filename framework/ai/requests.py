"""Durable logical request reservations; correlation is not caller attestation."""

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from framework.ai.integrity import digest, generated_hashes, protected_hashes
from framework.ai.runs import write_json


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def fingerprint(root: Path, run: Path, args: Any, pytest_args: list[str]) -> str:
    payload = {
        "run": run.name,
        "plan": digest(args.plan) if args.plan else None,
        "data": digest(args.data) if args.data else None,
        "generated": generated_hashes(root, run.name),
        "protected": protected_hashes(root),
        "base_url": args.base_url,
        "bug_mode": args.bug_mode,
        "selection": pytest_args,
        "repair_kind": args.repair_kind,
        "timeout": args.timeout,
    }
    value = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(value.encode()).hexdigest()


@dataclass(frozen=True)
class Reservation:
    request_id: str
    invocation_id: str
    fingerprint: str
    path: Path
    cached_exit: int | None = None


def reserve(
    run: Path, request_id: str, value: str, *, parent_ref: str | None, reason: str | None
) -> Reservation:
    folder = run / "requests"
    folder.mkdir(exist_ok=True)
    path = folder / f"{request_id}.json"
    if path.exists():
        record = json.loads(path.read_text())
        if record.get("fingerprint") != value:
            raise ValueError("Request ID was already used with different inputs")
        state = record.get("state")
        if state == "completed":
            return Reservation(request_id, uuid4().hex, value, path, int(record["exit_code"]))
        if state in {"rejected", "interrupted"}:
            return Reservation(request_id, uuid4().hex, value, path, 2)
        raise RuntimeError("Logical request is already in progress")
    siblings = [json.loads(item.read_text()) for item in folder.glob("*.json")]
    if any(item.get("state") in {"running", "interrupted"} for item in siblings):
        raise ValueError("Uncertain prior execution requires a linked new run")
    if any(item.get("fingerprint") == value for item in siblings) and not reason:
        raise ValueError("An intentional repeat needs a reason and a new request ID")
    if parent_ref:
        pieces = parent_ref.split("/")
        if len(pieces) != 2:
            raise ValueError("Parent request reference must be run_id/request_id")
        parent = run.parent / pieces[0] / "requests" / f"{pieces[1]}.json"
        if not parent.is_file() or not parent.resolve().is_relative_to(run.parent.resolve()):
            raise ValueError("Parent request evidence does not exist")
        parent_run = json.loads((run.parent / pieces[0] / "run.json").read_text())
        parent_request = json.loads(parent.read_text())
        if (
            parent_run.get("run_id") != pieces[0]
            or parent_request.get("request_id") != pieces[1]
            or parent_request.get("state") not in {"completed", "rejected", "interrupted"}
        ):
            raise ValueError("Parent request evidence is inconsistent")
    record = {
        "schema_version": "2.1",
        "request_id": request_id,
        "fingerprint": value,
        "state": "running",
        "created_at": utc_now(),
        "parent_request_ref": parent_ref,
        "reason": reason,
        "invocations": [],
    }
    invocation_id = uuid4().hex
    record["invocations"].append(
        {
            "invocation_id": invocation_id,
            "started_at": utc_now(),
            "pid": os.getpid(),
            "parent_pid": os.getppid(),
        }
    )
    write_json(path, record, exclusive=True)
    return Reservation(request_id, invocation_id, value, path)


def finish(
    reservation: Reservation,
    state: Literal["completed", "rejected", "interrupted"],
    *,
    exit_code: int,
    attempt_id: str | None = None,
) -> None:
    record = json.loads(reservation.path.read_text())
    if record.get("state") != "running" or record.get("fingerprint") != reservation.fingerprint:
        raise ValueError("Request reservation changed during execution")
    invocation = record["invocations"][-1]
    if invocation.get("invocation_id") != reservation.invocation_id:
        raise ValueError("Invocation identity changed")
    invocation.update({"finished_at": utc_now(), "exit_code": exit_code})
    record.update(
        {"state": state, "exit_code": exit_code, "attempt_id": attempt_id, "finished_at": utc_now()}
    )
    write_json(reservation.path, record)


def invocation_result(
    run: Path, reservation: Reservation, *, code: int, state: str, attempt_id: str | None = None
) -> None:
    write_json(
        run / "invocations" / f"{reservation.invocation_id}.result.json",
        {
            "invocation_id": reservation.invocation_id,
            "request_id": reservation.request_id,
            "finished_at": utc_now(),
            "state": state,
            "exit_code": code,
            "attempt_id": attempt_id,
        },
        exclusive=True,
    )
