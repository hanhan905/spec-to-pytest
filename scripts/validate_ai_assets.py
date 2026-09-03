"""Validate TRAE-produced JSON and CSV assets without calling a model."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from framework.ai.contracts import DataRow, RunManifest, StepInfoStore, TestPlan

CONTRACTS: dict[str, type[BaseModel]] = {
    "plan": TestPlan,
    "steps": StepInfoStore,
    "manifest": RunManifest,
}
CSV_FIELDS = ["data_id", "title", "content", "tags", "comment", "expected_valid"]


def validate_json(path: Path, kind: str) -> None:
    payload: Any = json.loads(path.read_text(encoding="utf-8"))
    CONTRACTS[kind].model_validate(payload)


def validate_csv(path: Path) -> None:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != CSV_FIELDS:
            raise ValueError(f"CSV fields must be exactly {CSV_FIELDS}")
        rows = list(reader)
    if not rows:
        raise ValueError("CSV must contain at least one data row")
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError("CSV rows must match the declared columns")
    case_ids = [row["data_id"] for row in rows]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("CSV data_id values must be unique")
    if any(row["expected_valid"] not in {"true", "false"} for row in rows):
        raise ValueError("expected_valid must be true or false")
    for row in rows:
        DataRow.model_validate(row)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=[*CONTRACTS, "csv"])
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    if args.kind == "csv":
        validate_csv(args.path)
    else:
        validate_json(args.path, args.kind)
    print(f"valid: {args.path}")


if __name__ == "__main__":
    main()
