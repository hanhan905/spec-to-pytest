# AI acceptance hardening — implementation plan

The maintainer approved the written 2.1 design on 2026-09-04. Implement in an isolated
checkout, synchronize only reviewed tracked changes, commit locally and do not push.
The writing-plans skill is unavailable in this environment; this explicit plan is
the fallback. The original learning projects and legacy run artifacts are read-only.

## Work packages

- [x] Contracts: explicit 2.0/2.1 readers, structured expectations/checks, mappings,
  run policy and a separate workflow assessment. Add invalid-input regressions.
- [x] Execution checks: frozen comparison helpers, phase-bound check/data events,
  mapping reconciliation and fail-closed assessment. Add green-but-missing-check cases.
- [x] Repairs: registered action helpers and full-source guards; reject wrappers,
  rebinding, imports, check-locator edits and unbounded waits. Retain rejected patches.
- [x] Requests: request/invocation/attempt identities, durable reservations,
  idempotent results with receipt revalidation, interruption and contention regressions.
- [x] MCP: pinned local runtime, stdio recorder with run binding and sealed receipts,
  identity separation, fake-server regressions and a real local MCP probe.
- [x] Acceptance: host evidence and explicit maintainer reviews bound to artifact
  hashes; automatic execution never manufactures review approval; safe public export.
- [x] Compatibility: read-only old-run inspection; new replay runs have honest labels;
  no legacy manifest rewrites or old-run continuation. Test preserved artifact hashes.
- [x] Documentation: coordinator/generator/data Skill, English/Chinese setup,
  schema exports, acceptance status and clear limits; preserve existing MCP config.
- [x] Verify: lint, format, types, contracts, baseline, candidate replay, known defect,
  positive/negative repair flows, MCP smoke and publication-source scans.
- [x] Synchronize exact tracked changes, verify the real project, recheck legacy hashes
  and commit locally. A fresh user-driven TRAE run remains a separate acceptance gate.

## Legacy preservation checkpoint

The reviewed run contained 1,999 files and its generated directory contained 30 files.
Aggregate digests are retained privately in the task record, not as a claim that the
run satisfies policy 2.1. Tests must not import or mutate those directories.

## Completion rule

Check each item only after its evidence exists. Do not equate a fake-server test or
standalone MCP probe with real host delegation. If a required external capability
cannot be verified, retain the unverified state and report the exact remaining gate.
