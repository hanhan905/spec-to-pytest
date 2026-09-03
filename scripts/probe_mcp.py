"""Standalone recorded MCP smoke; explicitly not TRAE or fresh AI acceptance."""

import json
import re
import select
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any

from framework.ai.mcp_evidence import MAX_MESSAGE, inspect_mcp
from framework.ai.runs import create_run, write_json
from framework.runtime.service import OwnedApp

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        origin = f"http://127.0.0.1:{probe.getsockname()[1]}"
    run = create_run("recorded-mcp-probe", ROOT / "reports/runs", exploration_origin=origin)
    metadata = json.loads((run / "run.json").read_text())
    with (
        OwnedApp(origin, run / "probe-app-data", run / "probe-app.log", "healthy"),
        (run / "recorder-stderr.log").open("xb") as log,
    ):
        process = subprocess.Popen(
            [sys.executable, "-m", "scripts.mcp_recorder", "--origin", origin, "--headless"],
            cwd=ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=log,
        )
        sequence = 0

        def rpc(method: str, params: dict[str, Any]) -> dict[str, Any]:
            nonlocal sequence
            sequence += 1
            assert process.stdin and process.stdout
            process.stdin.write(
                json.dumps(
                    {"jsonrpc": "2.0", "id": sequence, "method": method, "params": params}
                ).encode()
                + b"\n"
            )
            process.stdin.flush()
            while True:
                if not select.select([process.stdout], [], [], 30)[0]:
                    raise RuntimeError("MCP probe response timed out")
                reply = json.loads(process.stdout.readline(MAX_MESSAGE + 1))
                if reply.get("id") == sequence:
                    if "error" in reply or reply.get("result", {}).get("isError"):
                        raise RuntimeError("MCP probe tool failed; inspect private recorder log")
                    return dict(reply["result"])

        def tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
            return rpc("tools/call", {"name": name, "arguments": arguments})

        def texts(result: dict[str, Any]) -> str:
            return "\n".join(
                item.get("text", "")
                for item in result.get("content", [])
                if item.get("type") == "text"
            )

        try:
            rpc(
                "initialize",
                {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "spec-to-pytest-standalone-probe", "version": "2.1"},
                },
            )
            assert process.stdin
            process.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
            process.stdin.flush()
            tools = rpc("tools/list", {})["tools"]
            tool("evidence_begin_run", {"run_id": run.name, "nonce": metadata["correlation_nonce"]})
            tool("browser_navigate", {"url": origin + "/login"})
            snapshot = texts(tool("browser_snapshot", {}))
            match = re.search(r'textbox "用户名"[^\n]*\[ref=([^\]]+)\]', snapshot)
            if not match:
                raise RuntimeError("Username field was not observed in the live snapshot")
            tool(
                "browser_type",
                {"target": match.group(1), "text": "admin", "element": "synthetic demo username"},
            )
            observed = texts(tool("browser_snapshot", {}))
            if "admin" not in observed:
                raise RuntimeError("Typed synthetic username was not observed")
            tool("evidence_end_run", {})
            status = json.loads(texts(tool("evidence_status", {})))
            gate, reasons = inspect_mcp(run)
            result = {
                "standalone_mcp_probe": gate,
                "reasons": reasons,
                "tool_count": len(tools),
                "fresh_ai_generation": False,
                "trae_host_acceptance": False,
                "identity": status["identity"],
                "handshake": status["handshake"],
            }
            write_json(run / "probe-check.json", result, exclusive=True)
            print(
                json.dumps(
                    {
                        "run_dir": str(run),
                        "standalone_mcp_probe": gate,
                        "tool_count": len(tools),
                        "identity": status["identity"],
                        "serverInfo": status["handshake"]["serverInfo"],
                        "trae_host_acceptance": False,
                    },
                    ensure_ascii=False,
                )
            )
            if gate != "verified":
                raise SystemExit(2)
        finally:
            if process.stdin:
                process.stdin.close()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=10)
            if process.stdout:
                process.stdout.close()


if __name__ == "__main__":
    main()
