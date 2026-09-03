"""Promote local exploration knowledge only with linked, checked execution evidence."""

from __future__ import annotations

import json
import re
from pathlib import Path

from filelock import FileLock

from framework.ai.contracts import RunManifest, StepInfoRecord, StepInfoStore
from framework.ai.paths import contained_path


def merge_verified_steps(
    run_dir: Path,
    candidates: StepInfoStore,
    manifest: RunManifest,
    fingerprint: str,
    store_path: Path,
) -> StepInfoStore:
    if manifest.quality_gate != "passed" or manifest.integrity_errors:
        raise ValueError("Only a verified passing run can promote knowledge")
    passed = {result.case_id for result in manifest.results if result.status == "passed"}
    for record in candidates.records:
        if (
            record.source_run_id != manifest.run_id
            or record.source_case_id not in passed
            or record.app_fingerprint != fingerprint
        ):
            raise ValueError("Step provenance does not match the passing run")
        for relative in record.evidence_paths:
            contained_path(run_dir, relative)
        payload = record.model_dump_json()
        if re.search(
            r"password|passwd|authorization|cookie|api[_-]?key|secret|token|credential|密码|令牌",
            payload,
            re.IGNORECASE,
        ):
            raise ValueError("Credentials and sensitive fields do not belong in reusable knowledge")
    store_path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(store_path.with_suffix(".lock"), timeout=0):
        store = (
            StepInfoStore.model_validate_json(store_path.read_text())
            if store_path.exists()
            else StepInfoStore()
        )

        def key(record: StepInfoRecord) -> str:
            payload = record.model_dump()
            return json.dumps(
                {
                    name: payload[name]
                    for name in (
                        "action",
                        "selector",
                        "locator_strategy",
                        "app_fingerprint",
                        "parameters",
                    )
                },
                sort_keys=True,
            )

        existing = {key(record) for record in store.records}
        for record in candidates.records:
            if key(record) not in existing:
                store.records.append(record)
                existing.add(key(record))
        temporary = store_path.with_suffix(".tmp")
        temporary.write_text(store.model_dump_json(indent=2) + "\n", encoding="utf-8")
        temporary.replace(store_path)
        return store
