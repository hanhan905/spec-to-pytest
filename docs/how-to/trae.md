# Run a scenario with TRAE

A reviewed TRAE-host run is still a release gate. Historical replay does not establish that host
orchestration passed.

## Prepare the project

Run `make setup` and `make baseline` first. The optional AI path needs Node.js and your TRAE
account. The Python project itself does not request an LLM API key.

Install the locked optional runtime and create the ignored direct MCP configuration:

```sh
npm ci --prefix integrations/trae --ignore-scripts
uv run --frozen python -m scripts.configure_trae
```

Review `.trae/mcp.json`, preserving any unrelated servers if you merge it manually. The helper never
overwrites an existing file. Reload the server and confirm the official `browser_*` tools appear.
Use `.trae`, not `.trea`.

Read actual tool schemas: pinned MCP 0.0.80 uses `target` for `browser_type`, not the old `ref`
parameter. The server exposes powerful code and file tools; retain TRAE approvals and use only this
synthetic workspace. `--isolated`, loopback origins and output limits reduce accidental exposure but
are not a security sandbox.

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
`reports/mcp` is ignored scratch output, not independently authenticated evidence. Use schema 2.1
[structured checks](check-contracts.md). Explore with navigate → snapshot → action → snapshot, but
do not describe successful exploration as a passed test or a verified transcript.

Host permissions, login or usage limits may interrupt execution. Record interventions rather than
claiming an unattended run. If delegation is unavailable, use the generator plus the data Skill and
record `trae_single_agent_skill`, not `trae_orchestrated`.

Every planned case must appear in `manifest.json`. Review failures, repair diffs, source snapshots,
JUnit, screenshots and traces. `make report` creates an optional local Allure view. Do not upload raw
browser artifacts. Record visible TRAE/model/MCP versions and use `not_exposed_by_host` for hidden
versions. Standard orchestration, fallback and historical replay are separate verification claims.

Report execution and workflow gates separately. Missing host captures or maintainer semantic review
leaves workflow `unverified`, even with all tests green. Direct MCP output is reviewed only as part
of the host capture; do not ask the generator to self-approve. See
[workflow acceptance and request retries](workflow-acceptance.md).
