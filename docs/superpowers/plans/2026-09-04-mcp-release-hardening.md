# MCP release hardening — implementation plan

The maintainer approved
`docs/superpowers/specs/2026-09-04-mcp-release-hardening-design.md` on 2026-09-04.
Implement and verify locally before cleaning artifacts or publishing. The writing-plans skill is
unavailable in this environment; this explicit plan is the fallback.

## Work packages

- [ ] Establish the patch boundary: independently trace dynamic tool authorization, application
  identity, resulting-origin evidence, aggregate resource usage, callers, and compatibility needs.
- [ ] Add verified-mode tool authorization: expose and forward only the approved safe subset while
  retaining the complete observed child catalog for audit.
- [ ] Pin the exploration application identity: capture health in the ignored recorded-TRAE proposal,
  pass it to the recorder, compare all required fields at bind time, and validate it during inspection.
- [ ] Validate successful tool results: extract the pinned MCP `Page URL`, require the exact bound
  origin for every approved non-close response, and fail closed on missing or contradictory results.
- [ ] Bound recorder resources: enforce aggregate payload bytes, event count, duration, pending
  requests, remembered IDs, and child scratch-output limits with stable failure reasons.
- [ ] Preserve unrestricted exploration: keep the direct MCP template functional and document that
  it is local, high-privilege, unrecorded, and ineligible for workflow verification.
- [ ] Add focused regressions for dangerous advertised tools, direct disallowed calls, identity
  mismatch, foreign/missing result URLs, quota exhaustion, and the legitimate recorded workflow.
- [ ] Add the maintainer-approved root MIT license and update security/TRAE/reference documentation.
- [ ] Challenge the candidate patch with one independent read-only bypass and compatibility review;
  confirm any hypothesis against source or focused execution before revising.
- [ ] Verify in order: final diff/syntax, original security triggers and alternate malicious inputs,
  legitimate focused controls, unit/API suite, lint/format/types, baseline browser suite, real pinned
  MCP probe, secret/history scan, and tracked-file inventory.
- [ ] Commit only reviewed tracked changes. Do not delete process evidence, create a remote, push,
  change GitHub visibility, or claim the AI workflow is fully verified in this implementation stage.

## Completion rule

The three findings are `fixed` only when their original triggers no longer reproduce, the ordinary
TRAE recorded flow still works, unrestricted direct exploration remains available, and all relevant
local checks pass. Any unavailable relevant check leaves the result blocked or explicitly unverified.
