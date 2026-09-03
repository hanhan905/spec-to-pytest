"""Run preparation and on-disk summaries with explicit ownership."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from framework.ai.contracts import RunManifest


def write_json(path: Path, payload: Any, *, exclusive: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x" if exclusive else "w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def create_run(scenario_id: str, reports_root: Path) -> Path:
    scenario = re.sub(r"[^A-Za-z0-9_-]", "-", scenario_id).strip("-")[:60] or "scenario"
    run_id = f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{scenario}-{uuid4().hex[:8]}"
    run_dir = reports_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    write_json(
        run_dir / "run.json",
        {
            "run_id": run_id,
            "scenario_id": scenario,
            "created_at": datetime.now(UTC).isoformat(),
            "attempts": [],
            "repairs": [],
        },
        exclusive=True,
    )
    return run_dir


def write_summary(run_dir: Path, manifest: RunManifest) -> None:
    write_json(run_dir / "manifest.json", manifest.model_dump(mode="json"))
    lines = [
        f"# Run {manifest.run_id}",
        "",
        f"Quality gate: **{manifest.quality_gate}**",
        "",
        "Counts refer to unique planned cases, not attempts.",
        "",
        "| Case | Result | Reason |",
        "|---|---|---|",
    ]
    lines.extend(
        f"| {item.case_id} | {item.status.value} | {item.final_reason.replace('|', '/')} |"
        for item in manifest.results
    )
    lines.extend(
        [
            "",
            "## Evidence integrity",
            "",
            *(manifest.integrity_errors or ["Checks passed."]),
            "",
            "Raw browser evidence is local-only and must be reviewed before sharing.",
        ]
    )
    (run_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
