# spec-to-pytest

A local-first workbench for turning test scenarios into reviewable Python Playwright tests,
with evidence checked against the original plan.

**Development status:** v0.1 is being implemented. The design is approved, but the release
acceptance checks are not yet complete. No production-readiness or AI coverage claim is made.

The deterministic baseline does not require TRAE, Node.js, an LLM account or an API key.
TRAE is the first planned generation integration; it is not the test execution engine.

- [Approved design (中文)](docs/superpowers/specs/2026-09-03-spec-to-pytest-v0.1-design.md)
- [Implementation plan](docs/superpowers/plans/2026-09-03-v0.1-implementation.md)

## Local development

```sh
uv sync --frozen --extra test --extra dev
uv run playwright install chromium
uv run pytest tests/unit
uv run ruff check .
uv run mypy framework practice_app scripts
```

Only run trusted, reviewed generated code in an isolated local workspace. This project is not
a security sandbox. Public distribution is pending source review and license selection.
