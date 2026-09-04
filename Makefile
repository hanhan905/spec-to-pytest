.PHONY: help setup check baseline replay bug-demo report integration mcp-setup

help:
	@echo "setup: frozen Python dependencies and Chromium download"
	@echo "check: lint, formatting, types and unit/contract tests"
	@echo "baseline: owned local app, API/UI regression and checked evidence"
	@echo "replay: verify historical candidates; not a new AI generation or maintainer approval"
	@echo "bug-demo: check expected failure while retaining the inner failed report"
	@echo "report: optional Allure CLI view of the most recently summarized run"
	@echo "integration: structured-check, request-cache and bounded-repair regression"
	@echo "mcp-setup: install the locked optional Node runtime"
	@echo "Set AUTO_BASE_URL=http://127.0.0.1:8765 if port 8000 is occupied."

setup:
	uv sync --frozen --extra test --extra dev
	uv run --frozen playwright install chromium

check:
	uv run --frozen ruff check framework practice_app scripts tests examples
	uv run --frozen ruff format --check framework practice_app scripts tests examples
	uv run --frozen mypy framework practice_app scripts
	uv run --frozen python -m scripts.check_docs
	uv run --frozen python -m scripts.export_ai_schemas --check
	uv run --frozen pytest tests/unit -q

baseline:
	uv run --frozen python -m scripts.run_local --browser chromium -q

replay:
	uv run --frozen python -m scripts.replay --candidate

bug-demo:
	uv run --frozen python -m scripts.bug_demo

report:
	uv run --frozen python -m scripts.report

integration:
	uv run --frozen pytest tests/integration -q

mcp-setup:
	npm ci --prefix integrations/trae --ignore-scripts
