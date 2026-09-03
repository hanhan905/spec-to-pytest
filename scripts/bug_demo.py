"""An outer check of the expected defect; the inner run remains genuinely failed."""

import argparse
import json
import os
import sqlite3

from scripts.replay import replay


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url", default=os.environ.get("AUTO_BASE_URL", "http://127.0.0.1:8000")
    )
    args = parser.parse_args()
    code, run = replay(
        candidate=True, base_url=args.base_url, case_ids=["CONTENT_012"], bug_mode="comment_counter"
    )
    result = json.loads((run / "manifest.json").read_text())
    case = result["results"][0]
    attempt = run / "attempts" / result["final_attempt"]
    database = attempt / "app-data/content.sqlite3"
    with sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True) as connection:
        defect_rows = connection.execute(
            "SELECT p.comment_count, COUNT(c.id) FROM posts p "
            "JOIN comments c ON c.post_id=p.id GROUP BY p.id"
        ).fetchall()
    counter_defect_observed = any(count == 0 and actual > 0 for count, actual in defect_rows)
    proven = (
        counter_defect_observed
        and code == 1
        and result["quality_gate"] == "failed"
        and case["case_id"] == "CONTENT_012"
        and case["status"] == "failed"
        and case["failure_phase"] == "call"
        and bool(list((attempt / "artifacts").rglob("*.png")))
        and bool(list((attempt / "artifacts").rglob("*.zip")))
    )
    writeup = {
        "expected_defect_detected": proven,
        "inner_run_gate": result["quality_gate"],
        "note": "Outer success means the expected failure was observed, not that the app passed.",
    }
    (run / "defect-check.json").write_text(json.dumps(writeup, indent=2) + "\n")
    print(json.dumps(writeup))
    raise SystemExit(0 if proven else 1)


if __name__ == "__main__":
    main()
