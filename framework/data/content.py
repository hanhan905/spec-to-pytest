"""Read frozen run data without depending on a previous agent session's directory."""

import csv
import os
from pathlib import Path

from framework.ai.contracts import DataRow
from framework.ai.event_context import current
from framework.ai.paths import contained_path
from framework.data.models import CommunityPostData


def load_row(data_id: str) -> dict[str, str]:
    root = Path(__file__).resolve().parents[2]
    value = os.environ.get("AUTO_RUN_DIR")
    if not value:
        raise ValueError("Frozen run data requires AUTO_RUN_DIR")
    run = Path(value).resolve()
    if not run.is_relative_to(root / "reports/runs"):
        raise ValueError("Run data must belong to this workspace")
    with contained_path(run, "data.csv").open(encoding="utf-8", newline="") as stream:
        rows = [DataRow.model_validate(row) for row in csv.DictReader(stream)]
    matches = [row for row in rows if row.data_id == data_id]
    if len(matches) != 1:
        raise ValueError("Data reference must identify exactly one row")
    row = matches[0]
    context = current.get()
    if context is not None:
        context.record("data_read", data_id=data_id)
    return {
        "data_id": row.data_id,
        "title": row.title,
        "content": row.content,
        "tags": row.tags,
        "comment": row.comment,
        "expected_valid": row.expected_valid,
    }


def post_data(data_id: str) -> CommunityPostData:
    row = load_row(data_id)
    return CommunityPostData(
        title=row["title"], content=row["content"], tags=row["tags"], comment=row["comment"]
    )
