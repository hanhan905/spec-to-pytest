import asyncio
import json
import os
import select
import subprocess
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from framework.ai.mcp_evidence import MAX_MESSAGE, inspect_mcp
from framework.ai.mcp_recorder import Recorder, parse_message

ROOT = Path(__file__).resolve().parents[2]


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        body = b'{"application_id":"spec-to-pytest","instance_id":"synthetic-health"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: Any) -> None:
        pass


@contextmanager
def recorded_peer(tmp: Path) -> Iterator[tuple[Path, str, Any]]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    run = tmp / "reports/runs/run"
    run.mkdir(parents=True)
    (run / "run.json").write_text(
        json.dumps(
            {
                "schema_version": "2.1",
                "acceptance_policy": "2.1",
                "run_id": "run",
                "correlation_nonce": "synthetic-nonce",
                "exploration_origin": origin,
            }
        )
    )
    process = subprocess.Popen(
        [sys.executable, str(ROOT / "tests/fixtures/record_fake_mcp.py"), str(tmp), origin],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    sequence = 0

    def rpc(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        nonlocal sequence
        sequence += 1
        assert process.stdin and process.stdout
        process.stdin.write(
            json.dumps(
                {"jsonrpc": "2.0", "id": sequence, "method": method, "params": params or {}}
            ).encode()
            + b"\n"
        )
        process.stdin.flush()
        assert select.select([process.stdout], [], [], 10)[0], "Recorder response timed out"
        reply = json.loads(process.stdout.readline())
        assert reply["id"] == sequence
        return reply

    try:
        rpc(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "synthetic-client", "version": "1"},
            },
        )
        assert process.stdin
        process.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
        process.stdin.flush()
        listed = rpc("tools/list")["result"]["tools"]
        assert "evidence_begin_run" in [tool["name"] for tool in listed]
        yield run, origin, rpc
    finally:
        if process.stdin and not process.stdin.closed:
            process.stdin.close()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=10)
        if process.stdout:
            process.stdout.close()
        if process.stderr:
            process.stderr.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_real_stdio_forwarding_binding_and_sealed_receipt(tmp_path: Path) -> None:
    with recorded_peer(tmp_path) as (run, origin, rpc):
        assert "error" in rpc("tools/call", {"name": "browser_snapshot"})
        rejected = rpc(
            "tools/call",
            {"name": "evidence_begin_run", "arguments": {"run_id": "run", "nonce": "wrong"}},
        )
        assert rejected["result"]["isError"]
        begun = rpc(
            "tools/call",
            {
                "name": "evidence_begin_run",
                "arguments": {"run_id": "run", "nonce": "synthetic-nonce"},
            },
        )
        assert not begun["result"].get("isError")
        for name, arguments in [
            ("browser_navigate", {"url": origin + "/login"}),
            ("browser_snapshot", {}),
            ("browser_click", {"ref": "fixture"}),
            ("browser_snapshot", {}),
        ]:
            rpc("tools/call", {"name": name, "arguments": arguments})
        ended = rpc("tools/call", {"name": "evidence_end_run", "arguments": {}})
        assert not ended["result"].get("isError")
        assert inspect_mcp(run) == ("verified", [])
    assert inspect_mcp(run) == ("verified", [])


def test_interrupted_segment_cannot_be_verified(tmp_path: Path) -> None:
    with recorded_peer(tmp_path) as (run, _, rpc):
        rpc(
            "tools/call",
            {
                "name": "evidence_begin_run",
                "arguments": {"run_id": "run", "nonce": "synthetic-nonce"},
            },
        )
        rpc("tools/call", {"name": "browser_snapshot"})
    assert inspect_mcp(run)[0] != "verified"


def test_wrong_origin_is_rejected_before_forwarding_and_retained(tmp_path: Path) -> None:
    with recorded_peer(tmp_path) as (run, _, rpc):
        rpc(
            "tools/call",
            {
                "name": "evidence_begin_run",
                "arguments": {"run_id": "run", "nonce": "synthetic-nonce"},
            },
        )
        reply = rpc(
            "tools/call",
            {"name": "browser_navigate", "arguments": {"url": "https://example.invalid/"}},
        )
        assert "error" in reply
        rpc("tools/call", {"name": "evidence_end_run", "arguments": {}})
        assert inspect_mcp(run)[0] == "rejected"
        events = next((run / "exploration/mcp").glob("*/events.jsonl")).read_text()
        assert '"outcome": "failed"' in events


@pytest.mark.parametrize(
    "data",
    [
        b"[]\n",
        b"{}\n",
        b'{"jsonrpc":"2.0","id":true}\n',
        b'{"jsonrpc":"2.0","method":"tools/call"}\n',
        b"no-newline",
    ],
)
def test_protocol_frames_are_validated(data: bytes) -> None:
    with pytest.raises(ValueError):
        parse_message(data)


def test_oversize_frame_is_not_truncated_into_evidence() -> None:
    with pytest.raises(ValueError):
        parse_message(b"x" * (MAX_MESSAGE + 1) + b"\n")


def test_duplicate_ids_and_unmatched_responses_are_rejected(tmp_path: Path) -> None:
    async def check() -> None:
        recorder = Recorder(tmp_path, "http://127.0.0.1:8000", [], {})

        async def forward(message: dict[str, Any]) -> None:
            pass

        recorder.forward = forward
        await recorder.client_message(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        )
        with pytest.raises(ValueError, match="Duplicate"):
            await recorder.client_message({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        with pytest.raises(ValueError, match="Unmatched"):
            await recorder.server_message({"jsonrpc": "2.0", "id": 999, "result": {}})

    asyncio.run(check())
