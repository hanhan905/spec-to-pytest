# MCP Release Hardening Design

Status: approved by the maintainer on 2026-09-04

## Purpose

Harden the Playwright MCP integration before publishing `spec-to-pytest` as a public portfolio
project. Preserve access to the complete upstream Playwright MCP tool set for deliberate local
exploration while ensuring that only constrained, attributable interactions can become verified AI
workflow evidence.

This work also adds the maintainer-approved MIT license. It does not publish the repository, delete
local evidence, approve an AI run, or turn this local workbench into a general-purpose execution
sandbox.

## Security invariants

1. A server-advertised tool is not authorized merely because it appears in `tools/list`.
2. Verified evidence may contain only project-approved browser interactions against the exact bound
   loopback application origin and application instance.
3. A successful request URL is insufficient proof of browser location. The recorder must verify the
   resulting page URL reported by the pinned Playwright MCP response.
4. Full upstream MCP functionality remains available only through a separate, explicitly unverified
   exploration configuration. It cannot create project verification receipts.
5. One recorder segment has finite message, event, byte, duration, pending-request, and request-ID
   memory bounds.
6. Any failed identity, origin, protocol, or resource check fails closed and remains visible in the
   evidence record where recording is still possible.

## Two operating modes

### Verified recording mode

The existing project recorder remains the policy 2.1 acceptance entrypoint and the default documented
TRAE workflow. It exposes the three project management tools plus an explicit safe tool allowlist:

- `browser_navigate`
- `browser_snapshot`
- `browser_click`
- `browser_type`
- `browser_fill_form`
- `browser_select_option`
- `browser_press_key`
- `browser_close`

The recorder filters `tools/list` before returning it to the host and rejects every non-allowlisted
`tools/call`, even when the child server advertised that name. In particular, code evaluation,
arbitrary Playwright execution, storage-state manipulation, file upload/drop, tab creation, PDF,
screenshot filenames, network export, and other filename-bearing tools are unavailable in verified
mode.

The child catalog is still retained in recorder metadata for audit purposes. The exposed catalog and
the authorized set are recorded separately so an assessor can prove which boundary was in force.

### Unrestricted exploration mode

The existing direct Playwright MCP template remains available for deliberate local exploration and
debugging. It bypasses the project recorder, exposes the upstream server's complete configured tool
catalog, and has no `evidence_begin_run` or `evidence_end_run` tools.

Artifacts from this mode are scratch output only. The acceptance inspector cannot treat them as
project MCP evidence. Documentation must call this mode `unverified` and explain that tools such as
`browser_run_code_unsafe`, `browser_evaluate`, and file operations execute with the local user's
authority.

This separation preserves upstream functionality without weakening the verified evidence boundary.

## Application-instance binding

`scripts.configure_trae --recorded` probes the configured loopback origin's `/health` endpoint before
writing its ignored proposal. It accepts only the expected application and captures these exact
fields in the recorder launch arguments:

- `application_id=spec-to-pytest`
- application `version`
- `instance_id`
- `bug_mode`

The recorder compares all four values when a run calls `evidence_begin_run`. A changed or restarted
exploration application therefore requires a newly generated local proposal and TRAE MCP reload.
These values are not secrets, and the proposal remains ignored because it is machine- and
session-specific.

The verified segment stores both the expected identity and the observed health response. The
inspector requires them to match in addition to its existing package, entrypoint, run nonce, receipt,
and origin checks.

## Resulting-origin verification

The pinned Playwright MCP version returns a `### Page` section with `Page URL` for the approved
navigation and interaction tools. For every successful non-close tool response in verified mode, the
recorder extracts all reported page URLs and requires:

- at least one parseable `Page URL`;
- every reported URL to use the exact bound scheme, host, and port; and
- no contradictory page URL across returned content blocks.

The check occurs before the response is accepted as successful evidence. A missing, malformed, or
foreign resulting URL terminates the verified segment with an explicit error and stops the child MCP
process, which also closes its isolated browser. `browser_close` is exempt because its successful
response represents browser teardown rather than a live page.

This is evidence-integrity enforcement, not a claim that `--allowed-origins` prevents every network
request. That upstream flag remains defense in depth, and the documentation continues to prohibit
production accounts, personal browser profiles, and external targets.

## Resource bounds

The current 16 MiB per-frame bound remains for compatibility with full accessibility snapshots. A
segment additionally enforces:

| Resource | Limit |
|---|---:|
| Recorded request/response events | 2,000 |
| Aggregate serialized payload bytes | 64 MiB |
| Segment lifetime | 30 minutes |
| Outstanding forwarded requests | 32 |
| Remembered completed request IDs | 4,096 |
| Child MCP scratch output | 16 MiB |

The limits are checked before writing a new payload or forwarding a new request. Exceeding a bound
fails closed; the segment records a stable reason when possible and is sealed as incomplete. Request
IDs remain unique for the active segment, while the bounded completed-ID window prevents unbounded
process memory growth. Internal cleanup calls count toward pending and byte limits.

## Error handling

- Unknown or disallowed tools return a JSON-RPC invalid-parameters error and are not forwarded.
- Identity mismatch prevents segment creation.
- Resulting-origin failure seals the active segment with a specific error and terminates the child.
- Resource exhaustion seals the segment with a specific error and terminates the child.
- A connection interruption retains the existing incomplete-evidence behavior.
- The inspector rejects tampered receipts, identity contradictions, disallowed recorded tools,
  unverified profiles, and missing or foreign resulting URLs.

Errors exposed to TRAE remain concise and do not include filesystem paths, environment values, or
health internals. Detailed reasons live in local evidence metadata.

## Implementation boundaries

Expected production changes are limited to:

- `framework/ai/mcp_recorder.py` for authorization, identity, result-origin, and pending-request
  enforcement;
- `framework/ai/mcp_evidence.py` for aggregate quotas and inspection;
- `scripts/mcp_recorder.py` for pinned identity arguments and child output limits;
- `scripts/configure_trae.py` for loopback health capture;
- the TRAE how-to and security documentation for the two modes;
- focused MCP unit fixtures/tests;
- a root MIT `LICENSE` file.

The practice application, generated tests, scenario rules, AI plans, prior run artifacts, and formal
pytest runner behavior are outside this patch unless a focused regression test proves a direct
compatibility defect.

## Verification plan

Focused regression tests will prove that:

1. A fake child advertising dangerous and safe tools exposes only the safe subset in verified mode.
2. Direct/unverified configuration still preserves the upstream tool catalog.
3. A direct call to a dangerous advertised tool is rejected without reaching the child.
4. Application version, instance, and bug-mode mismatches reject binding.
5. Normal same-origin navigate, snapshot, action, snapshot, and close evidence still verifies.
6. A foreign, malformed, missing, or contradictory resulting page URL cannot verify.
7. Aggregate bytes, events, lifetime, pending calls, and request-ID memory remain bounded.
8. Interrupted and tampered segments retain their existing rejected or unverified outcomes.

Verification then proceeds through formatting/lint, type checking, unit and API tests, baseline UI
tests, and the real pinned MCP probe. A relevant unavailable check blocks a `fixed` conclusion rather
than being silently skipped.

## Release sequence

1. Implement and validate the security patch in the current local repository.
2. Add the MIT license and update public documentation.
3. Re-run secret/history checks and inspect the final tracked-file inventory.
4. Present an exact cleanup list; delete only maintainer-approved generated reports, generated tests,
   caches, and task-owned temporary copies.
5. Create the GitHub repository in a non-public staging state, configure security reporting and run
   hosted CI.
6. Make the repository public only after local and hosted checks pass.

The latest AI candidate run remains an execution demonstration with pending semantic and host
evidence review unless a later reviewed run supersedes it. Publication must not describe that run as
fully verified.
