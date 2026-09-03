"""Launch only the project's installed, version-checked Playwright MCP entrypoint."""

import argparse
import asyncio
import json
import shutil
import sys
from pathlib import Path

from framework.ai.integrity import digest
from framework.ai.mcp_evidence import PINNED_VERSION
from framework.ai.mcp_recorder import Recorder, run_recorder

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--origin", default="http://127.0.0.1:8000")
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()
    package = ROOT / "integrations/trae/node_modules/@playwright/mcp"
    node = shutil.which("node")
    if node is None or not (package / "package.json").is_file():
        raise SystemExit("Install the optional pinned runtime: npm ci --prefix integrations/trae")
    metadata = json.loads((package / "package.json").read_text())
    if metadata.get("name") != "@playwright/mcp" or metadata.get("version") != PINNED_VERSION:
        raise SystemExit("Installed MCP package differs from the pinned version")
    entry = package / "cli.js"
    if entry.is_symlink() or not entry.resolve().is_relative_to(package.resolve()):
        raise SystemExit("Unsafe MCP entrypoint")
    command = [
        node,
        str(entry),
        "--isolated",
        "--codegen",
        "python",
        "--allowed-origins",
        args.origin,
        "--block-service-workers",
        "--viewport-size",
        "1440x900",
        "--output-dir",
        str(ROOT / "reports/mcp"),
    ]
    if args.headless:
        command.append("--headless")
    identity = {
        "package": metadata["name"],
        "configured_version": PINNED_VERSION,
        "resolved_version": metadata["version"],
        "entrypoint_digest": digest(entry),
    }
    try:
        asyncio.run(run_recorder(Recorder(ROOT, args.origin, command, identity)))
    except (ValueError, OSError, KeyError, TypeError, AttributeError, asyncio.CancelledError):
        print("MCP recorder stopped; incomplete evidence is not verification", file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
