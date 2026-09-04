import json
import sys
from pathlib import Path

import pytest

from scripts import configure_trae


def test_direct_template_is_pinned_full_mcp_with_bounded_scratch_output() -> None:
    root = Path(__file__).resolve().parents[2]
    server = json.loads((root / "integrations/trae/mcp.example.json").read_text())["mcpServers"][
        "playwright"
    ]

    assert server["command"] == "node"
    assert server["args"][0] == "integrations/trae/node_modules/@playwright/mcp/cli.js"
    assert "--isolated" in server["args"]
    assert server["args"][server["args"].index("--output-max-size") + 1] == "16777216"
    assert not any("recorder" in value for value in server["args"])


def test_configure_trae_writes_ignored_direct_server_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = tmp_path / "integrations/trae/node_modules/@playwright/mcp/package.json"
    package.parent.mkdir(parents=True)
    package.write_text(json.dumps({"name": "@playwright/mcp", "version": "0.0.80"}))
    package.with_name("cli.js").write_text("// fixture")
    template = tmp_path / "integrations/trae/mcp.example.json"
    template.parent.mkdir(parents=True, exist_ok=True)
    template.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "playwright": {
                        "command": "node",
                        "args": [
                            "integrations/trae/node_modules/@playwright/mcp/cli.js",
                            "--output-dir",
                            "reports/mcp",
                            "--output-max-size",
                            "16777216",
                            "--allowed-origins",
                            "http://127.0.0.1:8000",
                        ],
                    }
                }
            }
        )
    )
    monkeypatch.setattr(configure_trae, "ROOT", tmp_path)
    monkeypatch.setattr(configure_trae.shutil, "which", lambda _: "/usr/local/bin/node")
    monkeypatch.setattr(sys, "argv", ["configure_trae", "--origin", "http://127.0.0.1:8765"])

    configure_trae.main()

    server = json.loads((tmp_path / ".trae/mcp.json").read_text())["mcpServers"]["playwright"]
    assert server["command"] == "/usr/local/bin/node"
    assert server["args"][0] == str(package.with_name("cli.js"))
    assert server["args"][server["args"].index("--allowed-origins") + 1] == (
        "http://127.0.0.1:8765"
    )
    assert "evidence_begin_run" not in json.dumps(server)
