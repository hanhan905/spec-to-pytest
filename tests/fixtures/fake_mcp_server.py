"""Synthetic protocol peer for recorder regression tests; not a real browser."""

import json
import sys

TOOLS = ["browser_navigate", "browser_snapshot", "browser_click", "browser_close"]
for line in sys.stdin.buffer:
    request = json.loads(line)
    if "id" not in request:
        continue
    method = request.get("method")
    if method == "initialize":
        result = {
            "protocolVersion": "2025-06-18",
            "serverInfo": {"name": "Playwright", "version": "synthetic-peer"},
            "capabilities": {"tools": {}},
        }
    elif method == "tools/list":
        result = {"tools": [{"name": name, "inputSchema": {"type": "object"}} for name in TOOLS]}
    else:
        result = {"content": [{"type": "text", "text": "synthetic fixture response"}]}
    print(json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": result}), flush=True)
