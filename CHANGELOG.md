# Changelog

## Unreleased

- Policy 2.1: separate execution and workflow gates, frozen structured comparisons,
  check/data events and explicit maintainer review bound to evidence hashes.
- Direct, version-pinned Playwright MCP exploration with explicit local-workbench safety limits.
- Starlette upgraded to 1.6.0 after the release dependency audit identified advisories below 1.3.1.
- Idempotent logical requests, per-invocation records and read-only legacy inspection.
- Restricted registered action repairs; wrapper/rebinding and unrelated source changes are rejected.

- Independent local workbench with locked Python dependencies.
- SQLite content persistence, real bounded PNG/JPEG uploads and opaque sessions.
- Owned loopback service lifecycle and per-run/per-attempt artifacts.
- Version-2 plans, explicit case mapping and reconciliation of pytest, JUnit and process evidence.
- Conservative repair guards; historical candidate replay labelled separately from new AI generation.
- Pinned TRAE MCP template and data-only Skill.

Public preview is live. A tagged v0.1 still requires maintainer review of the candidate example and
the latest TRAE workflow evidence.
