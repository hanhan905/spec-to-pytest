"""Create local-only MCP config from a portable, version-pinned template."""

import argparse
import json
import shutil
import sys
from pathlib import Path

from framework.runtime.service import parse_local_url

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--origin", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--recorded", action="store_true", help="Propose the policy 2.1 recorder config"
    )
    args = parser.parse_args()
    origin, _ = parse_local_url(args.origin)
    destination = ROOT / ".trae/mcp.json"
    if args.recorded:
        destination = ROOT / ".trae/mcp.recorded.proposed.json"
        if destination.exists():
            raise SystemExit("Recorder proposal already exists; inspect it instead of overwriting")
        template = {
            "mcpServers": {
                "playwright": {
                    "command": sys.executable,
                    "args": [str(ROOT / "scripts/mcp_recorder.py"), "--origin", origin],
                    "env": {"PYTHONPATH": str(ROOT)},
                }
            }
        }
        destination.parent.mkdir(exist_ok=True)
        with destination.open("x", encoding="utf-8") as stream:
            json.dump(template, stream, indent=2)
            stream.write("\n")
        print(
            "Created ignored .trae/mcp.recorded.proposed.json; review and merge in TRAE. "
            "Existing config unchanged."
        )
        return
    if destination.exists():
        raise SystemExit(
            "Local MCP config already exists; merge settings manually instead of overwriting it."
        )
    command = shutil.which("npx")
    if command is None:
        raise SystemExit("Node.js and npx are required only for the optional TRAE integration.")
    template = json.loads((ROOT / "integrations/trae/mcp.example.json").read_text())
    server = template["mcpServers"]["playwright"]
    server["command"] = command
    flags = server["args"]
    flags[flags.index("--output-dir") + 1] = str(ROOT / "reports/mcp")
    flags[flags.index("--allowed-origins") + 1] = origin
    destination.parent.mkdir(exist_ok=True)
    with destination.open("x", encoding="utf-8") as stream:
        json.dump(template, stream, indent=2)
        stream.write("\n")
    print("Created ignored local .trae/mcp.json. Enable project MCP and .agents skills in TRAE.")


if __name__ == "__main__":
    main()
