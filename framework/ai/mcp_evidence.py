"""Sealed local MCP segments. Hashes detect changes, not a malicious local operator."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from framework.ai.integrity import digest
from framework.ai.paths import contained_path
from framework.ai.runs import write_json

PINNED_VERSION = "0.0.80"
MAX_MESSAGE = 16 * 1024 * 1024


def now() -> str:
    return datetime.now(UTC).isoformat()


class Segment:
    def __init__(
        self,
        run: Path,
        session_id: str,
        *,
        identity: dict[str, Any],
        handshake: dict[str, Any],
        health: dict[str, Any],
        nonce: str,
    ) -> None:
        self.root = run / "exploration/mcp" / session_id
        self.root.mkdir(parents=True, exist_ok=False)
        self.sequence = 0
        self.closed = False
        self.metadata = {
            "schema_version": "2.1",
            "run_id": run.name,
            "session_id": session_id,
            "started_at": now(),
            "completed": False,
            "identity": identity,
            "handshake": handshake,
            "health": health,
            "nonce_hash": hashlib.sha256(nonce.encode()).hexdigest(),
            "errors": [],
        }
        write_json(self.root / "segment.json", self.metadata, exclusive=True)
        (self.root / "events.jsonl").touch(exist_ok=False)

    def record(
        self, direction: str, message: dict[str, Any], *, tool: str | None, internal: bool = False
    ) -> None:
        if self.closed:
            raise ValueError("Cannot append to a sealed MCP segment")
        self.sequence += 1
        raw = json.dumps(message, ensure_ascii=False).encode()
        if len(raw) > MAX_MESSAGE or self.sequence > 10_000:
            raise ValueError("MCP recording exceeded its bounded size")
        relative = f"payloads/{self.sequence:06d}.json"
        write_json(self.root / relative, message, exclusive=True)
        event = {
            "sequence": self.sequence,
            "at": now(),
            "direction": direction,
            "request_id": message.get("id"),
            "tool": tool,
            "internal": internal,
            "payload_path": relative,
            "payload_hash": digest(self.root / relative),
        }
        if direction == "response":
            result = message.get("result", {})
            event["outcome"] = (
                "failed"
                if "error" in message or (isinstance(result, dict) and result.get("isError"))
                else "passed"
            )
        with (self.root / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")

    def seal(self, *, error: str | None = None) -> None:
        if self.closed:
            return
        self.metadata.update(
            {
                "completed": error is None,
                "finished_at": now(),
                "event_count": self.sequence,
                "errors": [error] if error else [],
            }
        )
        write_json(self.root / "segment.json", self.metadata)
        files = {
            p.relative_to(self.root).as_posix(): digest(p)
            for p in sorted(self.root.rglob("*"))
            if p.is_file()
        }
        write_json(self.root / "receipt.json", files, exclusive=True)
        self.closed = True


def inspect_mcp(run: Path) -> tuple[str, list[str]]:
    segments = sorted((run / "exploration/mcp").glob("*/segment.json"))
    if not segments:
        return "unverified", ["project_mcp_recording_missing"]
    reasons: list[str] = []
    pending = False
    try:
        metadata = json.loads(contained_path(run, "run.json").read_text())
        for path in segments:
            root = contained_path(run, path.parent.relative_to(run).as_posix())
            info = json.loads(contained_path(root, "segment.json").read_text())
            receipt = json.loads(contained_path(root, "receipt.json").read_text())
            actual = {
                p.relative_to(root).as_posix()
                for p in root.rglob("*")
                if p.is_file() and p.name != "receipt.json"
            }
            if set(receipt) != actual or any(
                digest(contained_path(root, name)) != value for name, value in receipt.items()
            ):
                raise ValueError("MCP receipt mismatch")
            if (
                info.get("run_id") != run.name
                or info.get("nonce_hash")
                != hashlib.sha256(str(metadata.get("correlation_nonce", "")).encode()).hexdigest()
            ):
                raise ValueError("MCP run binding mismatch")
            identity = info.get("identity", {})
            if (
                identity.get("package") != "@playwright/mcp"
                or identity.get("configured_version") != PINNED_VERSION
                or identity.get("resolved_version") != PINNED_VERSION
                or not re.fullmatch(r"[a-f0-9]{64}", identity.get("entrypoint_digest", ""))
            ):
                raise ValueError("MCP package identity mismatch")
            handshake = info.get("handshake", {})
            if (
                handshake.get("serverInfo", {}).get("name") != "Playwright"
                or not handshake.get("protocolVersion")
                or not handshake.get("serverInfo", {}).get("version")
            ):
                raise ValueError("MCP observed handshake missing")
            if info.get("health", {}).get("application_id") != "spec-to-pytest":
                raise ValueError("MCP application identity mismatch")
            tool_catalog = {tool["name"] for tool in handshake.get("serverTools", [])}
            if not tool_catalog:
                raise ValueError("Observed MCP tool catalog missing")
            if not info.get("completed"):
                pending = True
                reasons.append("project_mcp_segment_incomplete")
            events = [json.loads(line) for line in (root / "events.jsonl").read_text().splitlines()]
            if len(events) != info.get("event_count") or [e["sequence"] for e in events] != list(
                range(1, len(events) + 1)
            ):
                raise ValueError("MCP event sequence invalid")
            requests: dict[str, dict[str, Any]] = {}
            successful = []
            for event in events:
                raw = json.loads(contained_path(root, event["payload_path"]).read_text())
                if digest(contained_path(root, event["payload_path"])) != event["payload_hash"]:
                    raise ValueError("MCP payload mismatch")
                key = json.dumps(event["request_id"])
                if raw.get("id") != event["request_id"]:
                    raise ValueError("MCP response ID mismatch")
                if event["direction"] == "request":
                    if event["tool"] not in tool_catalog:
                        raise ValueError("Called tool was not in the observed server catalog")
                    if (
                        raw.get("method") != "tools/call"
                        or raw.get("params", {}).get("name") != event["tool"]
                    ):
                        raise ValueError("MCP tool identity differs from request")
                    url = raw.get("params", {}).get("arguments", {}).get("url")
                    if url is not None:
                        from urllib.parse import urlsplit

                        parsed = urlsplit(url)
                        if f"{parsed.scheme}://{parsed.netloc}" != metadata.get(
                            "exploration_origin"
                        ):
                            raise ValueError("MCP navigation origin differs from its binding")
                    if key in requests:
                        raise ValueError("Duplicate MCP request")
                    requests[key] = event
                elif event["direction"] == "response":
                    prior = requests.pop(key, None)
                    if prior is None or prior["tool"] != event["tool"]:
                        raise ValueError("Unmatched MCP response")
                    failed = "error" in raw or bool(raw.get("result", {}).get("isError"))
                    if event["outcome"] != ("failed" if failed else "passed"):
                        raise ValueError("MCP outcome contradicts payload")
                    if not failed and not event["internal"]:
                        successful.append(event["tool"])
            if requests:
                pending = True
                reasons.append("project_mcp_requests_unfinished")
            stage = 0
            actions = {
                "browser_click",
                "browser_type",
                "browser_fill_form",
                "browser_select_option",
                "browser_press_key",
            }
            for tool in successful:
                if stage == 0 and tool == "browser_navigate":
                    stage = 1
                elif stage == 1 and tool == "browser_snapshot":
                    stage = 2
                elif stage == 2 and tool in actions:
                    stage = 3
                elif stage == 3 and tool == "browser_snapshot":
                    stage = 4
            if stage != 4:
                pending = True
                reasons.append("project_mcp_observation_action_sequence_missing")
    except (ValueError, OSError, TypeError, KeyError, AttributeError):
        return "rejected", ["invalid_project_mcp_evidence"]
    return ("unverified", sorted(set(reasons))) if pending else ("verified", [])
