# TRAE built-in Agent: local testing coordinator

Use this instruction with the built-in Agent. The two custom roles do not need to call each other.
Operate only on this project and its separate local exploration/test instances.

1. Read AGENTS.md, business rules and the requested scenario. Create a run with
   `uv run --frozen python -m scripts.prepare_ai_run content_lifecycle`; use its run.json identifiers.
2. Call `playwright-test-generator` in **plan** phase. It returns a validated `candidate-plan.json`.
3. Call `ai-test-data-expander` with that plan and the base CSV. It returns validated `candidate-data.csv`.
4. Call `playwright-test-generator` in **generate-and-execute** phase with both artifact paths.
5. Return the actual manifest/summary paths, counts, unresolved cases and interventions.

Use the built-in Agent's real delegation tools. Record `trae_orchestrated` only if those calls
actually occur. If unavailable, stop the standard route and offer the documented single-Agent
Skill route; label it `trae_single_agent_skill`, never fake a child-Agent call.

Exploration uses port 8000 with a separate data directory. Formal pytest uses port 8765 (or another
explicit unused loopback port). Do not kill the user's pre-existing service or share exploration data.
Do not bypass host approvals, login requirements or usage limits. Preserve blocked cases if access fails.
