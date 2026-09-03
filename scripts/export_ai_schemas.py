"""Export JSON Schemas from the canonical Pydantic contracts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic import BaseModel

from framework.ai.acceptance import WorkflowAssessment
from framework.ai.contracts import DelegationDeclaration, RunManifest, StepInfoStore, TestPlan

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "mana" / "schemas"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    contracts: dict[str, type[BaseModel]] = {
        "test_plan.schema.json": TestPlan,
        "step_info.schema.json": StepInfoStore,
        "run_manifest.schema.json": RunManifest,
        "workflow_assessment.schema.json": WorkflowAssessment,
        "delegation_declaration.schema.json": DelegationDeclaration,
    }
    for filename, contract in contracts.items():
        output = SCHEMA_DIR / filename
        expected = json.dumps(contract.model_json_schema(), ensure_ascii=False, indent=2) + "\n"
        if args.check:
            if not output.exists() or output.read_text(encoding="utf-8") != expected:
                raise SystemExit(f"Stale schema: {output.name}")
        else:
            output.write_text(expected, encoding="utf-8")
        print(output.relative_to(ROOT))


if __name__ == "__main__":
    main()
