.PHONY: help setup check baseline

help:
	@echo "setup: frozen Python dependencies and Chromium download"
	@echo "check: lint, formatting, types and unit/contract tests"
	@echo "baseline: owned local app, API/UI regression and checked evidence"
	@echo "Set AUTO_BASE_URL=http://127.0.0.1:8765 if port 8000 is occupied."

setup:
	uv sync --frozen --extra test --extra dev
	uv run --frozen playwright install chromium

check:
	uv run --frozen ruff check framework practice_app scripts tests
	uv run --frozen ruff format --check framework practice_app scripts tests
	uv run --frozen mypy framework practice_app scripts
	uv run --frozen pytest tests/unit -q

baseline:
	uv run --frozen python -m scripts.run_local --browser chromium -q
