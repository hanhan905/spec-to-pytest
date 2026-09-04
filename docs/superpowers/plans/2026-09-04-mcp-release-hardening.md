# Direct Playwright MCP release — implementation plan

The maintainer approved the revised direct-MCP design on 2026-09-04. The writing-plans skill is
unavailable in this environment; this explicit plan is the fallback.

## Work packages

- [ ] Remove the custom MCP recorder, sealed segment implementation, launcher, probe, fake peers,
  recorder-only tests, and Make targets.
- [ ] Remove recorder-specific assessment requirements while retaining execution, delegation, host
  capture, and maintainer semantic-review gates.
- [ ] Simplify TRAE configuration to the exact pinned official Playwright MCP server with isolated
  browser state, loopback configuration, ignored scratch output, and bounded output retention.
- [ ] Update English/Chinese setup, architecture, security, prompt, status, version, and provenance
  documentation so exploration is never described as independently verified evidence.
- [ ] Add the maintainer-approved MIT license and update release metadata.
- [ ] Update focused tests for the simplified acceptance semantics and direct configuration.
- [ ] Run one independent read-only bypass/regression review of the candidate diff and resolve only
  confirmed issues within this scope.
- [ ] Verify diff/syntax first, then unit/API tests, lint/format/types, baseline browser tests, direct
  MCP package/configuration, secret/history scan, and tracked-file inventory.
- [ ] Commit reviewed tracked changes. Do not clean local evidence, create/push a remote, or change
  GitHub visibility during implementation.

## Completion rule

The earlier recorder findings are resolved by removing that security boundary entirely, not by
claiming the unrestricted official MCP is safe. The project remains a local synthetic workbench;
Pytest artifacts decide test outcomes, while host and semantic review decide workflow claims.
