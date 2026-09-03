"""A bounded stdio recorder for the pinned local Playwright MCP subprocess."""

from __future__ import annotations

import asyncio
import json
import signal
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from filelock import FileLock

from framework.ai.mcp_evidence import MAX_MESSAGE, Segment
from framework.ai.paths import contained_path
from framework.runtime.service import parse_local_url

MANAGEMENT = [
    {
        "name": "evidence_begin_run",
        "description": "Bind this project MCP recorder to a prepared run",
        "inputSchema": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}, "nonce": {"type": "string"}},
            "required": ["run_id", "nonce"],
            "additionalProperties": False,
        },
    },
    {
        "name": "evidence_end_run",
        "description": "Close the isolated browser and seal this run's evidence",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "evidence_status",
        "description": "Read observed package/server identity and active binding",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]


def parse_message(line: bytes) -> dict[str, Any]:
    if len(line) > MAX_MESSAGE or not line.endswith(b"\n"):
        raise ValueError("Invalid or oversized MCP frame")
    value = json.loads(line)
    if not isinstance(value, dict) or value.get("jsonrpc") != "2.0":
        raise ValueError("Expected a JSON-RPC object")
    if "id" in value and type(value["id"]) not in {int, str}:
        raise ValueError("MCP request IDs must be strings or integers")
    if "id" not in value and not str(value.get("method", "")).startswith("notifications/"):
        raise ValueError("Only protocol notifications may omit request IDs")
    return value


class Recorder:
    def __init__(
        self, root: Path, origin: str, command: list[str], identity: dict[str, Any]
    ) -> None:
        self.root = root.resolve()
        self.origin, _ = parse_local_url(origin)
        self.command, self.identity = command, identity
        self.handshake: dict[str, Any] = {}
        self.client_info: dict[str, Any] = {}
        self.pending: dict[str, dict[str, Any]] = {}
        self.seen: set[str] = set()
        self.segment: Segment | None = None
        self.process: asyncio.subprocess.Process | None = None
        self.tools: set[str] = set()
        self.binding_lock = FileLock(self.root / ".local/mcp-binding.lock", timeout=0)

    def output(self, message: dict[str, Any]) -> None:
        sys.stdout.write(json.dumps(message, ensure_ascii=False) + "\n")
        sys.stdout.flush()

    async def forward(self, message: dict[str, Any]) -> None:
        assert self.process and self.process.stdin
        self.process.stdin.write(json.dumps(message, ensure_ascii=False).encode() + b"\n")
        await self.process.stdin.drain()

    def reject_call(self, message: dict[str, Any], tool: str | None, reason: str) -> None:
        reply = {
            "jsonrpc": "2.0",
            "id": message["id"],
            "error": {"code": -32602, "message": reason},
        }
        if self.segment:
            self.segment.record("request", message, tool=tool)
            self.segment.record("response", reply, tool=tool)
        self.output(reply)

    async def begin(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if self.segment or self.pending or not self.handshake or not self.tools:
            raise ValueError("Recorder is busy or not initialized")
        run = contained_path(self.root / "reports/runs", arguments["run_id"])
        if run.parent != self.root / "reports/runs":
            raise ValueError("Expected one prepared run identifier")
        metadata = json.loads(contained_path(run, "run.json").read_text())
        if (
            metadata.get("schema_version") != "2.1"
            or metadata.get("acceptance_policy") != "2.1"
            or metadata.get("correlation_nonce") != arguments["nonce"]
            or metadata.get("exploration_origin") != self.origin
        ):
            raise ValueError("Run binding or origin does not match")
        async with (
            httpx.AsyncClient(trust_env=False, timeout=5.0) as client,
            client.stream("GET", self.origin + "/health") as response,
        ):
            response.raise_for_status()
            body = bytearray()
            async for chunk in response.aiter_bytes(chunk_size=4096):
                body.extend(chunk)
                if len(body) > 65536:
                    raise ValueError("Oversized health response")
            health = json.loads(body)
        if health.get("application_id") != "spec-to-pytest":
            raise ValueError("Exploration application identity differs")
        self.binding_lock.acquire()
        try:
            self.segment = Segment(
                run,
                uuid4().hex,
                identity=self.identity,
                handshake=self.handshake,
                health=health,
                nonce=arguments["nonce"],
            )
        except BaseException:
            self.binding_lock.release()
            raise
        return {"bound_run": run.name, "session_id": self.segment.root.name}

    async def end(self) -> dict[str, Any]:
        if self.segment is None or self.pending:
            raise ValueError("No active run or requests are still outstanding")
        if "browser_close" not in self.tools:
            raise ValueError("Cannot prove isolated browser cleanup")
        message = {
            "jsonrpc": "2.0",
            "id": "recorder-" + uuid4().hex,
            "method": "tools/call",
            "params": {"name": "browser_close", "arguments": {}},
        }
        future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        key = json.dumps(message["id"])
        self.pending[key] = {
            "method": "tools/call",
            "tool": "browser_close",
            "segment": self.segment,
            "future": future,
            "internal": True,
        }
        self.segment.record("request", message, tool="browser_close", internal=True)
        await self.forward(message)
        reply = await asyncio.wait_for(future, timeout=15)
        if "error" in reply or reply.get("result", {}).get("isError"):
            raise ValueError("Isolated browser cleanup failed")
        self.segment.seal()
        path = self.segment.root.relative_to(self.root).as_posix()
        self.segment = None
        self.binding_lock.release()
        return {"sealed": True, "evidence_path": path}

    async def client_message(self, message: dict[str, Any]) -> None:
        if "method" not in message:
            await self.forward(message)
            return
        if "id" not in message:
            await self.forward(message)
            return
        key = json.dumps(message["id"])
        if key in self.seen:
            raise ValueError("Duplicate client request ID")
        self.seen.add(key)
        method = message.get("method")
        params = message.get("params", {})
        if method == "initialize":
            self.client_info = {
                "clientInfo": params.get("clientInfo"),
                "requestedProtocolVersion": params.get("protocolVersion"),
            }
        tool = params.get("name") if method == "tools/call" else None
        if tool in {item["name"] for item in MANAGEMENT}:
            body: dict[str, Any]
            try:
                if tool == "evidence_begin_run":
                    result = await self.begin(params.get("arguments", {}))
                elif tool == "evidence_end_run":
                    result = await self.end()
                else:
                    result = {
                        "identity": self.identity,
                        "handshake": self.handshake,
                        "active_run": self.segment.metadata["run_id"] if self.segment else None,
                    }
                body = {"content": [{"type": "text", "text": json.dumps(result)}]}
            except (ValueError, OSError, KeyError, TypeError, httpx.HTTPError, TimeoutError):
                body = {
                    "isError": True,
                    "content": [
                        {
                            "type": "text",
                            "text": "Recording rejected; inspect local setup and pending requests",
                        }
                    ],
                }
            self.output({"jsonrpc": "2.0", "id": message["id"], "result": body})
            return
        if method == "tools/call":
            if self.segment is None or tool not in self.tools:
                self.reject_call(message, tool, "Bind a prepared run before known browser actions")
                return
            url = params.get("arguments", {}).get("url")
            if url is not None and (
                not isinstance(url, str)
                or f"{urlsplit(url).scheme}://{urlsplit(url).netloc}" != self.origin
            ):
                self.reject_call(message, tool, "Only the bound exploration origin is allowed")
                return
        self.pending[key] = {
            "method": method,
            "tool": tool,
            "segment": self.segment if tool else None,
            "future": None,
            "internal": False,
        }
        if tool and self.segment:
            self.segment.record("request", message, tool=tool)
        await self.forward(message)

    async def server_message(self, message: dict[str, Any]) -> None:
        if "id" not in message or "method" in message:
            self.output(message)
            return
        pending = self.pending.pop(json.dumps(message["id"]), None)
        if pending is None:
            raise ValueError("Unmatched server response")
        result = message.get("result", {})
        if pending["method"] == "initialize" and isinstance(result, dict):
            self.handshake = {
                **self.client_info,
                **{
                    key: result.get(key)
                    for key in ("protocolVersion", "serverInfo", "capabilities")
                },
            }
        if pending["method"] == "tools/list" and isinstance(result, dict):
            listed = result.get("tools", [])
            self.tools.update(item["name"] for item in listed)
            catalog = {item["name"]: item for item in self.handshake.get("serverTools", [])}
            catalog.update({item["name"]: item for item in listed})
            self.handshake["serverTools"] = list(catalog.values())
            if self.tools.intersection(item["name"] for item in MANAGEMENT):
                raise ValueError("Recorder tool name collision")
            result["tools"] = [*listed, *MANAGEMENT]
        segment = pending["segment"]
        if segment:
            segment.record("response", message, tool=pending["tool"], internal=pending["internal"])
        future = pending["future"]
        if future is not None:
            if not future.done():
                future.set_result(message)
        else:
            self.output(message)

    async def serve(self) -> None:
        (self.root / ".local").mkdir(exist_ok=True)
        self.process = await asyncio.create_subprocess_exec(
            *self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=MAX_MESSAGE + 1,
            cwd=self.root,
        )
        reader = asyncio.StreamReader(limit=MAX_MESSAGE + 1)
        await asyncio.get_running_loop().connect_read_pipe(
            lambda: asyncio.StreamReaderProtocol(reader), sys.stdin.buffer
        )
        assert self.process.stdout and self.process.stderr

        async def read_loop(stream: asyncio.StreamReader, server: bool) -> None:
            while line := await stream.readline():
                message = parse_message(line)
                await (self.server_message(message) if server else self.client_message(message))

        async def diagnostics() -> None:
            assert self.process and self.process.stderr
            while data := await self.process.stderr.read(4096):
                sys.stderr.buffer.write(data)
                sys.stderr.buffer.flush()

        tasks = [
            asyncio.create_task(read_loop(reader, False)),
            asyncio.create_task(read_loop(self.process.stdout, True)),
            asyncio.create_task(diagnostics()),
        ]
        try:
            done, _ = await asyncio.wait(tasks[:2], return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                task.result()
        finally:
            if self.segment:
                self.segment.seal(error="connection_interrupted_before_evidence_end")
            self.binding_lock.release()
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            if self.process.returncode is None:
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), 5)
                except TimeoutError:
                    self.process.kill()
                    await self.process.wait()


async def run_recorder(recorder: Recorder) -> None:
    task = asyncio.current_task()
    if task is not None:
        asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, task.cancel)
    await recorder.serve()
