# Direct Playwright MCP release — implementation plan

The maintainer approved the revised direct-MCP design on 2026-09-04. The writing-plans skill is
unavailable in this environment; this explicit plan is the fallback.

## Work packages

- [x] Remove the custom MCP recorder, sealed segment implementation, launcher, probe, fake peers,
  recorder-only tests, and Make targets.
- [x] Remove recorder-specific assessment requirements while retaining execution, delegation, host
  capture, and maintainer semantic-review gates.
- [x] Simplify TRAE configuration to the exact pinned official Playwright MCP server with isolated
  browser state, loopback configuration, ignored scratch output, and bounded output retention.
- [x] Update English/Chinese setup, architecture, security, prompt, status, version, and provenance
  documentation so exploration is never described as independently verified evidence.
- [x] Add the maintainer-approved MIT license and update release metadata.
- [x] Update focused tests for the simplified acceptance semantics and direct configuration.
- [x] Attempt an independent read-only bypass/regression review. The reviewer hit its usage limit,
  so the maintainer agent performed the required separate-pass review and fixed the stale local TRAE
  configuration and lock-bypassing `npx` invocation it identified.
- [x] Verify diff/syntax first, then unit/API tests, lint/format/types, baseline browser tests, direct
  MCP package/configuration, secret/history scan, and tracked-file inventory.
- [x] Commit reviewed tracked changes. Do not clean local evidence, create/push a remote, or change
  GitHub visibility during implementation.

## Completion rule

The earlier recorder findings are resolved by removing that security boundary entirely, not by
claiming the unrestricted official MCP is safe. The project remains a local synthetic workbench;
Pytest artifacts decide test outcomes, while host and semantic review decide workflow claims.

The final dependency audit also found that the project's Starlette `<1` ceiling retained a vulnerable
release. The ceiling was replaced with a `>=1.3.1,<2` security range, the lock resolved Starlette
1.6.0 plus its `httpx2` TestClient transport, and the full local regression suite passed afterward.
