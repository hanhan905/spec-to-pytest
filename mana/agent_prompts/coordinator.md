# TRAE built-in Agent: local testing coordinator

Use this instruction with the built-in Agent. The two custom roles do not need to call each other.
Operate only on this project and its separate local exploration/test instances.

1. Read AGENTS.md, business rules and the requested scenario. Create a run with
   `uv run --frozen python -m scripts.prepare_ai_run content_lifecycle`; use its run.json identifiers.
   New runs use policy 2.1. Do not continue or migrate an old run in place.
2. Call `playwright-test-generator` in **plan** phase. It returns a validated `candidate-plan.json`.
3. Call `ai-test-data-expander` with that plan and the base CSV. It returns validated `candidate-data.csv`.
4. Call `playwright-test-generator` in **generate-and-execute** phase with both artifact paths.
5. Return the actual manifest/summary paths, execution gate, workflow gate, counts,
   unresolved cases and interventions. `quality_gate=passed` is not workflow verification.

Retain `candidate-delegations.json` using the delegation schema: three ordered phase calls with
logical role, actual host role identifier, phase, unique correlation ID, visible host call/parent
IDs (or `not_exposed_by_host`), and input/output relative artifact paths mapped to SHA-256 hashes.
Use immutable candidate revisions or execution source snapshots for earlier inputs; never claim
changed inputs had the earlier hash. Label it `agent_statement` and validate with
`uv run --frozen python -m scripts.validate_ai_assets delegation <candidate-delegations.json>`.
After retaining this declaration, run `uv run --frozen python -m scripts.accept_ai_run <run_dir> --save`
and return that exact assessment revision path. Exit 2 for missing review is not a failed Pytest run;
do not erase the initial assessment or call the maintainer review command to make it green.
Do not manufacture a host export or claim that this declaration proves delegation. Actual host
exports/UI captures go to the private run's `host/` directory for maintainer review.

The generator must use the configured official Playwright MCP server for local exploration and read
the observed tool schemas before calls. Direct MCP output is not independently authenticated and
must not be described as verified evidence. Do not silently substitute another browser provider.

Create one unique `request_id` for each intended full execution. If a tool response is uncertain,
retry with the SAME request ID and unchanged inputs. An intentional repeat or allowed repair needs
a new ID, `--parent-request-ref <run_id>/<previous_request_id>` and `--request-reason`.
An interrupted/uncertain execution requires a linked new run, not a fabricated completion receipt.

Never invoke `scripts.review_ai_run`, edit `reviews/` or self-approve semantic alignment/delegation.
Automatic execution may finish with workflow `unverified`; maintainer review occurs separately.

Use the built-in Agent's real delegation tools. Record `trae_orchestrated` only if those calls
actually occur. If unavailable, stop the standard route and offer the documented single-Agent
Skill route; label it `trae_single_agent_skill`, never fake a child-Agent call.

Exploration uses port 8000 with a separate data directory. Formal pytest uses port 8765 (or another
explicit unused loopback port). Do not kill the user's pre-existing service or share exploration data.
Do not bypass host approvals, login requirements or usage limits. Preserve blocked cases if access fails.
