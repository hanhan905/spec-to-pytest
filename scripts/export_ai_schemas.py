"""Export JSON Schemas from the canonical Pydantic contracts."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from framework.ai.contracts import RunManifest, StepInfoStore, TestPlan

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "mana" / "schemas"


def main() -> None:
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    contracts: dict[str, type[BaseModel]] = {
        "test_plan.schema.json": TestPlan,
        "step_info.schema.json": StepInfoStore,
        "run_manifest.schema.json": RunManifest,
    }
    for filename, contract in contracts.items():
        output = SCHEMA_DIR / filename
        output.write_text(
            json.dumps(contract.model_json_schema(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(output.relative_to(ROOT))


if __name__ == "__main__":
    main()
