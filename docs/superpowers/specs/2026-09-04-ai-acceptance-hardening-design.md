# AI acceptance hardening — design 2.1

> Historical design: its custom MCP-recorder section was superseded by the approved
> [direct Playwright MCP design](2026-09-04-mcp-release-hardening-design.md). The structured
> execution, repair, request and review controls remain applicable.

Date: 2026-09-04

Status: written specification approved by the maintainer on 2026-09-04.
This document is not an implementation or acceptance claim.

## 1. Purpose and observed failure modes

This change strengthens the local spec-to-pytest workbench after its first supplied
TRAE session. The existing run recorded 15 planned cases, 25 data rows, six complete
attempts and two repair rounds. Independent reconciliation confirmed 15 passing
cases in the final attempt and intact recorded evidence. That establishes execution
facts, not every claim about the workflow that produced them.

The review found four concrete gaps:

1. A configured MCP package version was presented as an observed tool-server identity.
   The supplied session used browser tools through a host integration without evidence
   tying those calls to the configured project MCP process.
2. CONTENT-014 required a particular error-detail meaning in its plan, but its test
   checked only that the detail was nonempty. Frozen assertion text did not detect
   this initial mismatch between intention and implementation.
3. CONTENT-015 retained an assertion's syntax by rebinding its page variable to a new
   request wrapper. The request still tested a real revoked cookie, but the mechanism
   demonstrates why identical assertion syntax cannot establish unchanged semantics.
4. Six attempts were recorded; the claim that three were host-generated duplicates
   had no caller-level evidence. Execution count and cause must be distinguished.

These examples become small synthetic regression fixtures. Do not copy the private
conversation, raw browser state, real process environments or entire run into Git.

## 2. Scope and approved choices

Keep the practice application, business rules, two-role TRAE workflow, Python
Playwright framework, Pytest execution and Allure collection. The new work is a
bounded acceptance layer, provenance recorder and stricter repair policy.

The selected approach is layered gates with machine evidence and restricted repairs.
Prompt-only changes were rejected because they cannot enforce the boundary. Replacing
Python tests with a full testing language was rejected as disproportionate for v0.1.

Preserve automatic generation and batch execution after a scenario is supplied.
Host permissions, login and usage limits remain in force. Public-example review is
separate from execution and must not introduce a required human pause before every
test. The workbench never writes its own maintainer approval.

Out of scope: changes to business behavior, another AI host, cloud hosting, parallel
workers, a new model runtime, automatic license selection, GitHub publication, social
posts or an OS security sandbox. Do not edit SECURITY.md under this specification.

This document supersedes the original v0.1 design only for new-run acceptance,
provenance, request identity and automatic repair rules described below.

## 3. Compatibility and evidence ownership

- Existing run directories, generated sources associated with those runs, manifests,
  receipts, repairs and recordings remain byte-for-byte unchanged.
- Do not add new fields, regenerate summaries, replay into an old run or backfill
  missing evidence. New findings belong in separate review output or documentation.
- New runs carry explicit `schema_version: 2.1` and `acceptance_policy: 2.1` metadata.
  Readers support legacy 2.0 and new 2.1 explicitly; unknown versions are rejected.
  Unversioned legacy run metadata is recognized only through its consistent recorded
  2.0 plan and manifest, never silently promoted to the new policy.
- A legacy inspection reads its recorded result and checks its stored evidence without
  executing its source or treating today's source tree as the historical environment.
  It labels new-policy acceptance `unverified`; this is not a retroactive failed test.
- Continuing an old run through the new runner is rejected with instructions to create
  a linked new run. A read-only legacy inspection never rewrites the old manifest.
- Historical replay creates a new run with a replay source label. It cannot acquire a
  fresh-generation claim merely by being processed by a newer runner.

Before implementation, record aggregate hashes for the reviewed legacy run and its
generated directory. Recheck them after tests and before committing. New unit tests
use temporary roots; integration tests create fresh runs only.

## 4. Separate execution from workflow acceptance

Keep `quality_gate` as the execution-only result derived from collection, phase
events, JUnit, process completion and artifact integrity. Its values remain
`passed`, `failed` and `blocked`; Pytest failures must never be rewritten by a review.

Add a separately versioned assessment containing `workflow_gate`:

| State | Meaning |
|---|---|
| `verified` | Required workflow evidence and structural checks are complete, and the maintainer reviewed expectation alignment |
| `unverified` | Evidence or semantic review is absent; no contradictory fact has been established |
| `rejected` | Evidence contradicts the claim, a required check is bypassed, or integrity validation fails |
| `not_applicable` | Baseline, synthetic fixture or historical replay makes no fresh AI workflow claim |

Each assessment records policy version, source claim, evidence basis, specific reasons
and hashes of the inputs it assesses. It references a specific final attempt, never
an inferred newest file. Later review creates a new assessment revision, not an edit
to execution evidence. Changing any referenced input invalidates that review.

The report always shows both gates. A green execution result with an unverified
workflow must not become a single green AI-acceptance badge. A structurally complete
run can automatically finish with semantic review pending.

`run_local` retains execution exit codes 0/1/2. A separate acceptance command returns
0 only for `verified`, 1 for `rejected`, and 2 for `unverified` or an inapplicable
fresh-AI claim. A release check must use this command, not just the Pytest exit code.

Public summary export includes both gates and their policy/evidence level without raw
evidence. Promotion additionally requires explicit maintainer approval of the example
and privacy/source review. Neither gate approves a license or publication action.

## 5. Project MCP recorder

### 5.1 Mechanism and identity

Add a project-owned stdio adapter in front of the version-pinned Playwright MCP
process. The adapter forwards protocol traffic without changing browser results and
records the traffic it actually observes. It does not infer tool origin from names.

MCP stdio uses newline-delimited UTF-8 JSON-RPC, with protocol traffic on stdout and
diagnostics on stderr. Preserve those stream boundaries and request/response IDs.
See the [MCP stdio specification](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports).

Capture initialization, negotiated protocol version, client information, returned
server information, tool listing and correlated tool requests/responses. Initialization
exchanges implementation information; its server version is not automatically the
npm package version. See the [MCP lifecycle specification](https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle).

Record these as distinct fields:

- configured package and version;
- resolved package version and entrypoint digest, when verified from the launched package;
- server-reported name/version and negotiated protocol version;
- recorder session ID, version and start/end state.

Launch only the maintenance-configured executable and package entrypoint, never a
command received from page text or a tool argument. If package identity cannot be
resolved, record it as unavailable; a configured version must not fill that gap.
A configured/resolved package mismatch rejects the package claim. Different npm and
server-reported version strings are not inherently a mismatch; preserve both values.

### 5.2 Binding evidence to a run

The adapter adds three namespaced management tools: `evidence_begin_run`,
`evidence_end_run` and `evidence_status`. The underlying server's tool names and
schemas are preserved; a name collision prevents recording from starting.

Begin accepts only a prepared 2.1 run ID and its generated correlation nonce, not
an arbitrary output directory. It checks the run's exact loopback exploration origin
and application identity. One recorder session has at most one active run; a second
binding is rejected. Close the previous isolated browser context before beginning
another run so that browser state cannot silently cross run boundaries.

Before a run is bound, initialization and tool discovery are allowed but browser
actions are rejected. After binding, browser requests and responses receive the run,
session, sequence and JSON-RPC request IDs. End seals the evidence segment only when
outstanding requests are resolved; an interrupted segment remains visibly incomplete.

A verified MCP claim requires a complete bound segment with the actual expected
server identity, a local navigation, a page observation, a successful scenario action
and a subsequent observation. Failed calls remain in the segment. These requirements
establish an observed interaction path, not complete scenario or assertion coverage.

Host-native browser tools that bypass the adapter do not qualify as recorder evidence.
They may be used only through an explicitly labelled alternative route; they cannot
silently satisfy the project-Playwright-MCP claim.

### 5.3 Failure handling, privacy and limits

Use bounded message buffers and a documented 16 MiB per-message recording limit.
Oversized/malformed messages, recorder write failures, unmatched responses, unfinished
requests or child-process failures cannot yield complete evidence. Fail the recorded
session clearly rather than truncate it and call it verified. Notifications remain
distinct from responses; termination stops only the child owned by this adapter.

Raw protocol payloads, snapshots and screenshots are private run artifacts. Summary
records retain tool names, timing, outcome and payload references/hashes, not full
arguments or response bodies. Do not log environment variables, cookies, credentials
or authorization headers in public metadata. Raw payloads still require review.

Hashes and local recording are audit aids, not remote attestation. The trusted local
operator can modify files or processes; this design does not defend against that actor.
Origin restrictions also do not sandbox arbitrary generated Python or every redirect.

Configuration changes are opt-in: produce a proposed local MCP configuration and
instructions to restart/reload it. Never overwrite an existing `.trae/mcp.json` or
modify the user's old-project Agent definitions automatically.

## 6. TRAE delegation evidence

The coordinator still invokes generator/plan, expander/data, then
generator/generate-and-execute. TRAE documents built-in Agent delegation to configured
custom roles, but this does not promise a particular export API. See the
[official Agent configuration](https://docs.trae.cn/ide_built-in-agent).

Keep declared role calls separate from their evidence. Each record contains role,
phase, local correlation ID, input/output artifact hashes, host call/parent IDs when
exposed, evidence reference and capture kind. Capture kinds distinguish a host export,
a UI capture reviewed by the maintainer and an Agent's own statement.

Only a reviewed host export or UI capture can substantiate a delegation claim. A
well-formed JSON file written by an Agent, or a nonce echoed by it, is not independent
proof. Hidden host IDs and model versions stay `not_exposed_by_host`.

Without suitable host evidence, execution can finish but `trae_orchestrated` remains
an unverified claim. The recorder can prove MCP traffic but not which custom Agent
requested it. Do not add an invented host hook, read unrelated conversations or
relabel a single-Agent Skill run as dual-Agent orchestration.

## 7. Expected-result contracts and data mapping

### 7.1 Plan-time structure

New generated plans give each expected result a stable `expectation_id`, its natural
language meaning and one or more structured check IDs. A check declares its subject,
comparison operator, expected value or frozen data-field reference, and rule basis.
Operators are explicit: equality, containment, ordered equality, count, visibility,
URL equality and attribute/property equality. Truthiness is not a substitute for
equality or containment. No arbitrary Python expression is evaluated from the plan.

The planner must not invent an exact error string when the rule only requires a
rejection. A justified exploratory expectation must be labelled. If a conflict is
found before freezing, revise and revalidate the candidate plan, preserving a revision
record. After freezing, expectation changes require a linked new run.

The planner may reserve new data IDs for the expander to fulfil. It must not force
all cases to reference only a baseline row. Before freezing, every reference must
resolve in the expanded CSV and each case lists the rows it actually needs.

### 7.2 Test binding and runtime checks

Bind every check to its planned case and concrete test node. Generated tests invoke
maintenance-owned check helpers using the check ID and observed value/locator. The
helper loads the comparison and expected operand from frozen inputs, performs the
real check and writes a phase-bound event. Python code cannot override the expected
operand or downgrade the operator through the helper interface.

All required checks must execute successfully in the final full attempt. Missing,
duplicate, undeclared, cross-case or setup-only check events prevent contract acceptance.
Conditional expectations must be explicitly planned rather than silently omitted.
Additional diagnostic assertions do not count toward the required check set.
Failed helper checks raise real test failures as well as recording failed check events.
An unsuccessful check event cannot be hidden by a subsequently passing test phase.

The data loader records per-case data IDs during the call phase. The finalizer checks
them against declared references; unmapped or unused declared rows are reported.
Such a declared/observed mapping mismatch rejects structural contract acceptance.
Extra CSV rows are retained but not counted as executed coverage.

For CONTENT-014, a contract requiring a type-related message cannot be fulfilled by
`bool(detail)`. It must run the declared comparison, fail on a mismatch or remain
rejected for a missing required check even if the Python test itself passed.

### 7.3 Honest semantic boundary

Structural checks cannot prove that an arbitrary observation is honest or that a
natural-language expectation was correctly translated. Generated code can still choose
the wrong subject or compare fabricated values. A maintainer must review the rule,
structured contract and observation source before workflow acceptance becomes verified
and before a sample is promoted. A model-written review is advisory, not approval.

Do not describe check IDs, AST hashes or passing helper calls as general semantic
verification. The automatic gate makes omissions and comparison substitutions visible;
the explicit review closes the remaining interpretation gap.

## 8. Restricted repairs after the first attempt

Freeze the plan, checks, data, generated imports, classes, helper definitions, statement
structure, assertion/check calls and observation derivations before execution.
Pre-execution parsing and validation failures are generation failures and are recorded
as such; they do not create a fictitious Pytest attempt.

After freezing, allow at most three repair rounds and only two categories:

- `locator`: literal selector/accessible-name changes in explicitly registered,
  allowlisted action-locator nodes;
- `synchronisation`: bounded timeout values on registered existing waits/actions,
  without adding, deleting or changing a wait's success condition.

Timeout replacements are integer milliseconds from 100 through 30,000 inclusive;
zero, negative and unbounded waits are rejected. Existing overall run timeouts remain.

Compare the full parsed source before and after while allowing only the registered
leaf values. Preserve registration IDs and operation types. Selectors used by a check
or to derive its observed value are not auto-repairable. Shared aliases, unresolved
data flow or any edit that cannot be proven to fit the narrow syntax rule is rejected.

Do not allow imports, new wrappers/classes, variable rebinding, changed API clients,
new/deleted statements, control flow, exception handling, skip/xfail, data edits or
operator/expected-value changes. For new 2.1 runs, `syntax` and `data` are not accepted
post-freeze repair categories. An API property mistake requires a corrected new run,
not an adapter introduced to keep an old assertion string unchanged.

Retain every proposed patch, its classification, decision, input hashes and reason,
including rejected proposals. A rejected patch is not accepted as a new source baseline.
Any accepted repair reruns the complete plan with a new logical request ID and attempt.
This is conservative automation, not proof of semantic equivalence for arbitrary code.

## 9. Request identity and repeat execution

Separate four identifiers: run, logical execution request, actual runner invocation
and Pytest attempt. The coordinator creates a `request_id` once per intended full
execution and reuses it if the tool response is uncertain. A repair or an intentional
repeat creates a new request ID linked to the prior request and records its reason.

Under the existing serial lock, persist a request reservation before starting an app
or Pytest. Each runner process generates its own `invocation_id` and local audit entry.
The reservation fingerprints frozen inputs, generated source, target origin, bug mode
and effective selection; it must not depend on a model's claimed process identity.

- Same request ID and same fingerprint, completed: return the recorded outcome and
  original attempt reference after rechecking its receipts; do not launch another app
  or create another attempt. Corrupted cached evidence returns blocked, not success.
- Same ID with a different fingerprint: reject the conflict.
- Same ID still running: report in progress without executing it again.
- Same ID interrupted or outcome uncertain: retain that state, do not silently retry;
  an explicit retry creates a linked new run and request that reference it. Do not
  manufacture a complete receipt for the interrupted attempt to allow continuation.
- A different ID with the same inputs is a separate requested run, not automatic proof
  of a host bug. Record the relationship without guessing its cause.

Log local timestamps, PID/parent PID, request/invocation/attempt IDs and sanitized
command shape. Do not capture the process environment. IDs establish correlation,
not the true external caller unless independent host evidence supplies that link.

## 10. Components and integration boundaries

| Component | Responsibility |
|---|---|
| Versioned contracts and validators | New plan/check/binding, provenance, assessment and request schemas; explicit legacy readers |
| MCP adapter and local configuration helper | Record actual child-server traffic and run bindings; preserve existing config |
| Check helpers and execution plugin | Execute frozen comparisons and collect check/data events without model verdicts |
| Repair validator | Full-source comparison with a narrow registered-leaf allowlist |
| Runner and request ledger | Reserve requests, own processes and retain idempotent execution records |
| Finalizer and acceptance assessor | Keep execution facts separate from workflow claims and review revisions |
| TRAE prompts and guides | Phase contracts, actual evidence, correct `csv` validator command and honest fallback labels |
| Reports and public exporter | Show both gates, source basis and limitations; export aggregate allowlists only |

Keep new responsibilities in focused modules rather than expanding `run_local.py`
into a host controller. No application feature work is required. Update English and
Chinese instructions, exported schemas and the acceptance checkpoint consistently.
Correct the stale SECURITY.md status in documentation; do not rewrite its policy.

## 11. Acceptance tests and handoff

Required deterministic regressions:

1. Config-only MCP identity, absent handshake, wrong server and missing run binding
   cannot verify a project-MCP claim. Package and server versions remain distinct.
2. Recorder tests cover real request/response pairing, notifications, errors, duplicate
   IDs, interrupted segments, oversize messages and child cleanup using a fake server.
3. A real pinned Playwright MCP probe through the recorder reaches the local app and
   retains a correlated action sequence. This probe is not a TRAE-host acceptance run.
4. An Agent-written delegation statement cannot stand in for a host capture; absent
   host details remain unknown and prior-run artifacts cannot satisfy the new run.
5. Required error-detail equality/containment cannot pass through a nonempty-string
   check. Missing, duplicate and cross-case check/data mappings are detected.
6. The wrapper/rebinding technique from CONTENT-015 is rejected. Legitimate registered
   action-locator changes pass; changed check locators, data, imports and API paths fail.
7. Full-suite execution follows every permitted repair; rejected patches and all
   earlier failures remain inspectable. The fourth repair is rejected.
8. Concurrent and repeated same-ID requests create at most one app/attempt. Conflicting
   inputs, process interruption and explicit retry links produce distinct honest states.
9. A passing Pytest run with an unverified workflow cannot pass the AI acceptance
   command or be displayed/exported as fully verified. Semantic review is hash-bound.
10. Legacy inspection is read-only, cannot promote old results, and remains usable
    after current source changes. Legacy run/source aggregate hashes remain unchanged.
11. Ruff, types, schemas, documentation links, units/contracts, baseline, historical
    replay and known-defect demonstration continue to pass under their correct meanings.
12. Public aggregate fixtures omit credentials, raw payloads, private paths, hostnames,
    process identifiers and unnecessary personal information.

After local implementation checks, a fresh user-driven TRAE run is still necessary.
Inspect real custom-role calls, recorder identity, generated check mappings, execution
and review state. Do not reuse the previous green run as proof of the new design.
GitHub-hosted CI, license/source approval and publication remain separate release gates.

## 12. Design workflow checkpoint

- [x] Inspect project context, original design, current contracts and reviewed run evidence.
- [x] Assess visual questions: none; no visual companion is needed for this backend policy change.
- [x] Clarify legacy evidence handling: preserve old runs and sources without mutation.
- [x] Compare prompt-only, layered-gate and full-language approaches.
- [x] Obtain approval for the layered-gate design and restricted automatic repairs.
- [x] Write the concrete specification and self-review scope, consistency and ambiguity.
- [x] Obtain maintainer review of this written specification.
- [ ] Produce the implementation plan, then implement and validate within the approved scope.

Only local commits are authorized. No remote repository, push or public example
promotion is performed as part of this design-document checkpoint.
