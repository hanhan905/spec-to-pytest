# Observed tool versions

Local observation, 2026-09-03, macOS arm64:

| Component | Observed version | Verification |
|---|---|---|
| Python | 3.14.7 | Frozen environment and local tests |
| Python, clean clone | 3.12.14 | New environment: quality, 92 units/contracts, 14 baseline, 13 replay checks passed |
| Python Playwright | 1.62.0 | Real Chromium baseline |
| Pytest | 9.1.1 | Unit tests and recorded subprocesses |
| FastAPI / Starlette | 0.141.1 / 0.52.1 | App and TestClient checks |
| AnyIO | 4.14.2 | Locked TestClient compatibility |
| Pillow | 12.3.0 | Decode, metadata, size and persistence |
| Node.js | 24.11.1 | Standalone MCP probe |
| @playwright/mcp | 0.0.80 | CLI, stdio, tool list, local navigation and snapshot |
| MCP serverInfo | 1.63.0-alpha-2026-08-31 | Reported server version, distinct from npm wrapper |
| Allure CLI | 2.45.0 | Installed; rendering checked separately |
| Gitleaks | 8.30.1 | Official binary SHA-256 checked before scanning |

The MCP probe exposed 24 tools and accessed only the isolated local login page, without personal
browser state. This was **not a TRAE-host run**. The pinned release supports `--codegen python`;
earlier search snippets with a smaller options list were not authoritative for the installed release.

Linux and hosted CI remain targets until their jobs run. Python 3.12.14 was additionally verified on
macOS in a clean clone. Windows, Firefox and WebKit are not verified. Python Playwright and the MCP
server are distinct components; their versions can differ.

Policy 2.1 recorder observation (2026-09-04): the actual installed package remained
0.0.80, the server reported `1.63.0-alpha-2026-08-31`, and the adapter exposed 27 tools
(24 underlying tools plus 3 evidence-management tools). A fresh local navigate,
snapshot, username entry, follow-up snapshot and sealed close passed. The pinned
`browser_type` schema requires `target`; an initial probe using `ref` failed and was
retained. This is a standalone recorded probe, **not** new TRAE-host acceptance.

Sources: [Playwright MCP](https://github.com/microsoft/playwright-mcp),
[TRAE Agent](https://docs.trae.cn/ide_built-in-agent),
[TRAE Skills](https://docs.trae.cn/ide_skills), [Gitleaks](https://github.com/gitleaks/gitleaks).
