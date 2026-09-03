# Run a scenario with TRAE

A real TRAE-host acceptance run is still a release gate. The standalone MCP probe and historical
replay do not establish that host orchestration passed.

## Prepare the project

Run `make setup` and `make baseline` first. The optional AI path needs Node.js and your TRAE
account. The Python project itself does not request an LLM API key.

For policy 2.1, install the locked optional runtime and generate a recorder proposal:

```sh
npm ci --prefix integrations/trae --ignore-scripts
uv run --frozen python -m scripts.configure_trae --recorded
```

Review `.trae/mcp.recorded.proposed.json` and merge its `playwright` entry into project MCP settings,
preserving unrelated servers. The helper never overwrites `.trae/mcp.json`. Reload the server and
confirm `evidence_begin_run`, `evidence_end_run` and `evidence_status` appear alongside browser tools.
Use `.trae`, not `.trea`. The legacy direct-server template supports unrecorded exploration only;
neither that config nor host-native `browser_*` names prove the new project-MCP claim.

The adapter records installed package and server-reported versions separately. Read actual tool
schemas: pinned MCP 0.0.80 uses `target` for `browser_type`, not the old `ref` parameter.

Enable `.agents/skills` in Skills and Commands settings. A same-named skill under `.trae/skills`
takes priority; resolve ambiguity first. See [official settings](https://docs.trae.cn/ide_skills).

## Create two custom roles

| Field | Test generator | Data expander |
|---|---|---|
| Name | Playwright AI 测试生成器 | AI 测试数据增强器 |
| English identifier | playwright-test-generator | ai-test-data-expander |
| Prompt | `mana/agent_prompts/test_generator.md` | `mana/agent_prompts/data_expander.md` |
| Tools | Project files, terminal, Playwright MCP | Project files and terminal only |
| When to call | Plan, explore and generate tests for a prepared run | Expand synthetic test data for a plan |

Enable “can be called by other agents” for both roles and add them to the built-in Agent's tools.
If these identifiers already belong to your original learning project, create project-specific
identifiers and substitute them in the coordinating instruction; do not overwrite the original roles.
Confirm project rules loaded. Use `mana/agent_prompts/coordinator.md` as the coordinating instruction.
The host describes built-in Agent → custom roles, not an assumed direct custom-Agent-to-custom-Agent
call. See [official configuration](https://docs.trae.cn/ide_built-in-agent).

## Separate exploration and acceptance

Use port **8000** for MCP and **8765** for formal pytest. Do not share their data or kill an existing
service. Start a separate local exploration app:

```sh
PRACTICE_DATA_DIR=.local/exploration PRACTICE_ORIGIN=http://127.0.0.1:8000 \
  uv run --frozen uvicorn practice_app.main:app --host 127.0.0.1 --port 8000
```

Leave that terminal open while exploring; close only what you started. MCP navigates to
`http://127.0.0.1:8000/login`, never an external website or personal signed-in browser profile.
First inspect `/health`: it must identify `application_id=spec-to-pytest`, not merely return 200.
If port 8000 serves a different app, choose another explicit exploration origin and update the local
MCP configuration to match. Similar-looking pages are not proof of instance identity.

## Execute one scenario

Ask the built-in Agent to read the coordinator instruction and execute
`mana/scenarios/content_lifecycle.md`. It should create a run, delegate planning and CSV expansion,
then request exploration/generation and execution. Inspect artifacts, not just the natural-language reply.

The generator uses `scripts.run_local` with the actual run directory, candidate plan, candidate CSV
and `--base-url http://127.0.0.1:8765 --request-id <logical_request_id>`.
All paths must come from this run, never an older frozen batch.
Save exact MCP snapshots/tool outputs into the run's exploration directory; `reports/mcp` is scratch
output, not evidence automatically associated with every run. Never invent a tool transcript.

Use schema 2.1 [structured checks](check-contracts.md). Bind the recorder with `evidence_begin_run`,
using this run's ID and `correlation_nonce` from `run.json`. Retain navigate → snapshot → action →
snapshot through the recorder, then call `evidence_end_run`. It closes the isolated browser and
seals the segment under `exploration/mcp/`; incomplete segments cannot verify MCP use.

Host permissions, login or usage limits may interrupt execution. Record interventions rather than
claiming an unattended run. If delegation is unavailable, use the generator plus the data Skill and
record `trae_single_agent_skill`, not `trae_orchestrated`.

Every planned case must appear in `manifest.json`. Review failures, repair diffs, source snapshots,
JUnit, screenshots and traces. `make report` creates an optional local Allure view. Do not upload raw
browser artifacts. Record visible TRAE/model/MCP versions and use `not_exposed_by_host` for hidden
versions. Standard orchestration, fallback and historical replay are separate verification claims.

Report execution and workflow gates separately. Missing host captures or maintainer semantic review
leaves workflow `unverified`, even with all tests green. Do not ask the generator to self-approve.
See [workflow acceptance and request retries](workflow-acceptance.md).

Optional: `uv run --frozen python -m scripts.probe_mcp` runs the real pinned MCP through the recorder
against an owned local app. This is a standalone diagnostic, not TRAE delegation acceptance.
