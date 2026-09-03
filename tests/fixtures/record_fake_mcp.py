"""Launch the real recorder around a deterministic fake child, only for regression tests."""

import asyncio
import sys
from pathlib import Path

from framework.ai.mcp_recorder import Recorder, run_recorder

root = Path(sys.argv[1])
origin = sys.argv[2]
identity = {
    "package": "@playwright/mcp",
    "configured_version": "0.0.80",
    "resolved_version": "0.0.80",
    "entrypoint_digest": "0" * 64,
}
command = [sys.executable, str(Path(__file__).with_name("fake_mcp_server.py"))]
asyncio.run(run_recorder(Recorder(root, origin, command, identity)))
