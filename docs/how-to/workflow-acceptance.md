# Execution is not workflow verification

New runs use policy 2.1. `manifest.json` keeps the Pytest execution result;
`assessments/` holds immutable workflow-assessment revisions. Summaries show both.

| Result | Meaning |
|---|---|
| Execution `passed` / `failed` / `blocked` | Collection, phase events, JUnit, process result and receipts |
| Workflow `unverified` | MCP/host evidence or semantic review is absent |
| Workflow `rejected` | A required check is missing/unsuccessful, evidence conflicts, or review is stale/rejected |
| Workflow `verified` | Checks and recorded MCP evidence match; the maintainer reviewed semantics and claimed delegation |
| Workflow `not_applicable` | Baseline, synthetic fixture or replay makes no fresh AI claim |

`run_local` exits according to execution only. Assess the AI claim separately:

```sh
uv run --frozen python -m scripts.accept_ai_run reports/runs/RUN_ID
```

Exit codes: 0 verified, 1 rejected, 2 unverified/inapplicable/invalid evidence. The
command is read-only unless `--save` is used for a new assessment revision on a 2.1
run. Do not use a Pytest zero exit code alone as a release approval.

## Maintainer review, not Agent self-approval

Inspect planned comparisons, real observation sources, failure evidence, repairs and
the recorder segment. For a dual-Agent claim, inspect real TRAE role calls and place
the host export or UI capture inside this run's private `host/` directory. An Agent's
narrative or JSON declaration is not a host capture.
The coordinator also retains `candidate-delegations.json`: three ordered role/phase
records, correlation IDs, exposed host identifiers and input/output artifact hashes.
This structural declaration is explicitly labelled `agent_statement`; even when it
validates, independent host capture and maintainer review are still required.

Only after personally completing that review, record it:

```sh
uv run --frozen python -m scripts.review_ai_run reports/runs/RUN_ID \
  --semantic-alignment approved --host-evidence host/capture.png \
  --capture-kind ui_capture --delegation-reviewed --confirm-maintainer-review
```

Pass the printed review path to the assessor:

```sh
uv run --frozen python -m scripts.accept_ai_run reports/runs/RUN_ID \
  --review reports/runs/RUN_ID/reviews/REVIEW_ID.json --save
```

A review binds to one attempt and artifact hashes. Changed inputs, receipts, MCP
segments or captures invalidate it. Use `--semantic-alignment rejected` for a rejected
interpretation. Never edit the old review or execution result to reverse a decision.

The local operator is trusted. The confirmation flag is not authentication against a
malicious process acting as that operator. Automatic generation may not invoke the
review command or write approvals. A production approval service is out of scope.

## Requests and retries

A request ID identifies one intended full execution. A retry with the same ID and
inputs returns the earlier result after receipt verification, without another app or
attempt. Different inputs with that ID are rejected. An intentional repeat/repair
uses a new ID, parent request reference and reason:

```sh
uv run --frozen python -m scripts.run_local --run-dir reports/runs/RUN_ID \
  --plan reports/runs/RUN_ID/candidate-plan.json --data reports/runs/RUN_ID/candidate-data.csv \
  --base-url http://127.0.0.1:8765 --request-id repair-1 \
  --parent-request-ref RUN_ID/initial --request-reason "Registered locator repair" \
  --repair-kind locator --repair-note "Correct action label from the current snapshot"
```

Interrupted/uncertain execution requires a new linked run; its first request refers
to `OLD_RUN_ID/OLD_REQUEST_ID`. Preserve the old run. Local process/time correlation
does not itself prove who caused a repeat; do not automatically blame the host.

## Legacy data and public export

Old 2.0 runs and their generated code are never upgraded or continued in place.
Use `scripts.prepare_ai_run SCENARIO --parent-run OLD_RUN_ID` to link a new run without
editing an old one, including a legacy run that has no logical-request ledger.
Read-only inspection verifies historical snapshots rather than comparing them to
today's tree. New-policy acceptance is unverified. New Allure views are outside old
runs, under `reports/views/`.

Public export includes both gates and omits raw payloads, paths, host/process IDs
and review content. The automatic exporter does not infer approval merely from
finding a review file. License choice, publication and sample promotion require
separate approval.

To export one explicitly reviewed result, use `scripts.export_public_summary --run-dir
reports/runs/RUN_ID --review reports/runs/RUN_ID/reviews/REVIEW_ID.json`. The source label
is a declared route, not verification by itself; interpret it with `workflow_gate`.
