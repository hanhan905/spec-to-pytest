# Contributing

The repository is being prepared for its first release. License selection, maintainer review of
historical examples and a real TRAE host acceptance run are still release gates.

## Work locally

Run `make setup`, then `make check` and `make baseline`. Use `AUTO_BASE_URL` to select an unused
loopback port; the runner deliberately refuses to reuse an existing server. Python dependencies
belong in pyproject.toml and uv.lock. Do not install or format files inside virtual environments.

Keep changes focused. Add a failing regression first, fix the behavior, then run relevant checks.
When adding a business rule, provide a stable rule ID, positive/negative tests and explicit expected
outcomes. Do not change an assertion just because a generated test is red.

## AI-assisted contributions

You are responsible for understanding generated code and verifying its assertions. Explain what was
AI-assisted, what you reviewed and what actually ran. Do not flood the project with unreviewed PRs.
Keep deterministic baseline, candidate replay and fresh TRAE generation results distinct.

## A useful pull request includes

- The problem, scope and any behavior change.
- Focused regressions and exact commands/results.
- Applicable specification/acceptance IDs and known gaps.
- Safe, synthetic evidence only; no cookies, secrets, raw traces or private paths.

Never add local MCP configuration, .env files, databases, virtual environments or reports to Git.
Tests are serial in v0.1. Parallel worker support needs an explicit isolation design and tests.
Do not add a live cloud dependency, new public deployment or paid service without discussing scope.
