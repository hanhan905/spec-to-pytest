"""Run preparation and on-disk summaries with explicit ownership."""

from __future__ import annotations

import json
import platform
import re
import secrets
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any
from uuid import uuid4

from framework.ai.contracts import RunManifest
from framework.ai.integrity import application_fingerprint, protected_hashes


def write_json(path: Path, payload: Any, *, exclusive: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x" if exclusive else "w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def create_run(
    scenario_id: str,
    reports_root: Path,
    *,
    exploration_origin: str = "http://127.0.0.1:8000",
    parent_run_id: str | None = None,
) -> Path:
    from framework.runtime.service import parse_local_url

    exploration_origin, _ = parse_local_url(exploration_origin)
    if parent_run_id is not None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", parent_run_id):
            raise ValueError("Invalid parent run identifier")
        if not (reports_root / parent_run_id / "run.json").is_file():
            raise ValueError("Parent run does not exist")
    scenario = re.sub(r"[^A-Za-z0-9_-]", "-", scenario_id).strip("-")[:60] or "scenario"
    run_id = f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{scenario}-{uuid4().hex[:8]}"
    run_dir = reports_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    project = Path(__file__).resolve().parents[2]
    versions: dict[str, str] = {}
    for name in (
        "pytest",
        "playwright",
        "pytest-playwright",
        "allure-pytest",
        "fastapi",
        "starlette",
        "pillow",
    ):
        try:
            versions[name] = version(name)
        except PackageNotFoundError:
            versions[name] = "not_installed"
    write_json(
        run_dir / "run.json",
        {
            "schema_version": "2.1",
            "acceptance_policy": "2.1",
            "run_id": run_id,
            "scenario_id": scenario,
            "parent_run_id": parent_run_id,
            "created_at": datetime.now(UTC).isoformat(),
            "attempts": [],
            "repairs": [],
            "correlation_nonce": secrets.token_hex(32),
            "exploration_origin": exploration_origin,
            "protected_hashes": protected_hashes(project),
            "application_fingerprint": application_fingerprint(project),
            "environment": {
                "python": platform.python_version(),
                "platform": platform.system(),
                "architecture": platform.machine(),
                "packages": versions,
            },
        },
        exclusive=True,
    )
    return run_dir


def write_summary(run_dir: Path, manifest: RunManifest) -> None:
    from framework.ai.acceptance import assess, save_assessment

    assessment = assess(run_dir, manifest)
    assessment_path = save_assessment(run_dir, assessment)
    write_json(run_dir / "manifest.json", manifest.model_dump(mode="json"))
    lines = [
        f"# Run {manifest.run_id}",
        "",
        f"Execution gate: **{manifest.quality_gate}**",
        f"AI workflow gate: **{assessment.workflow_gate}**",
        f"Assessment: `{assessment_path.relative_to(run_dir).as_posix()}`",
        f"Declared workflow source: `{manifest.source}`",
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
            "",
            "## Workflow acceptance",
            "",
            *(assessment.reasons or ["Evidence and maintainer review verified."]),
        ]
    )
    (run_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
