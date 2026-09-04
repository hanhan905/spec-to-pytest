# Direct Playwright MCP Release Design

Status: revised and approved by the maintainer on 2026-09-04

## Decision

Use the official, version-pinned Playwright MCP server directly from TRAE. Remove the custom MCP
recorder, its management tools, and its independent verification gate.

This project is a local AI-assisted testing workbench, not an MCP security proxy or operating-system
sandbox. Keeping the complete official MCP feature set while describing a custom recorder as a
security boundary would add complexity and create a misleading assurance claim.

## Supported workflow

```text
Scenario written by a person
        -> TRAE built-in Agent
        -> test-generator and data-expander roles
        -> official Playwright MCP explores the local practice app
        -> generated Python Playwright tests
        -> Pytest formal execution
        -> structured checks, JUnit, traces, screenshots and Allure results
```

Playwright MCP exploration helps the generator understand the rendered application and discover
working interaction steps. It is not a simulated test pass and is not independently authenticated
evidence. Formal execution artifacts produced by Pytest remain the source of truth for case results.

## MCP configuration and trust boundary

The project keeps one portable direct-server template and one helper that creates an ignored local
`.trae/mcp.json`. The configuration:

- pins `@playwright/mcp` to the reviewed project version;
- uses an isolated browser profile;
- points the browser at the configured exact loopback origin;
- blocks service workers;
- bounds scratch output retention;
- stores scratch output only under the ignored reports directory.

These flags reduce accidental exposure but are not a security sandbox. Full MCP includes powerful
features such as browser-side evaluation, arbitrary Playwright code, and file operations. Operators
must use only synthetic local data in a disposable workspace, retain TRAE permission controls, and
never connect the project MCP to personal or production accounts.

## Acceptance semantics

Remove project claims and gates that independently verify an MCP transcript. In particular:

- no `evidence_begin_run`, `evidence_end_run`, or `evidence_status` tools;
- no sealed MCP segment, recorder receipt, or recorder-specific assessment;
- no inference that an MCP operation was safe merely because it appeared in an agent summary;
- no requirement for a custom proxy to approve official MCP tools.

Workflow review still separates:

- deterministic execution results from Pytest/JUnit/structured checks;
- host delegation evidence showing the requested TRAE roles ran;
- maintainer semantic review of generated cases and assertions.

A maintainer may retain screenshots or host exports as private review material. Those files are not
automatically public and must not contain credentials or personal browser state.

## Removed components

- `framework/ai/mcp_recorder.py`
- `framework/ai/mcp_evidence.py`
- `scripts/mcp_recorder.py`
- `scripts/probe_mcp.py`
- recorder-specific fake servers and regression tests
- recorder configuration generation and recorder-specific documentation

Historical ignored run artifacts are not migrated. Git history retains the removed implementation
for audit and learning purposes.

## Retained components

- the official Playwright MCP configuration and version lock;
- TRAE built-in/custom-agent instructions;
- generated plan/data/test contracts;
- request, attempt, repair and execution evidence;
- Pytest, JUnit, trace, screenshot, video and Allure handling;
- host-delegation review and maintainer semantic review;
- safe aggregate public-summary export.

## Verification

The change is complete when:

1. No tracked runtime or documentation references removed recorder management tools.
2. TRAE configuration resolves the exact pinned official MCP package and retains full official tools.
3. The local baseline, unit/API tests, lint, formatting, type checking and documentation checks pass.
4. The direct MCP configuration is validated without claiming a TRAE-host run occurred.
5. Secret/history scans find no personal credentials or private configuration.
6. The repository contains the maintainer-approved MIT license.

## Release sequence

After verification, present an exact cleanup inventory and delete only approved generated reports,
generated tests, caches, and task-owned temporary copies. Then create a non-public GitHub staging
repository, configure security reporting, run hosted CI, and make it public only after those checks
pass. The latest AI candidate remains an execution demonstration with pending semantic/host review
unless a later reviewed run supersedes it.
