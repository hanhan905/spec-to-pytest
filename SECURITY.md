# Security Policy

## System and scope

spec-to-pytest is a local testing workbench and synthetic practice application.
The application, execution runner, evidence handling, generated-test intake and
TRAE configuration templates are in scope. No public hosting is supported.

## Trust boundaries

The operator controls the development workspace. HTTP input, uploaded media,
scenario/data files, generated Python, MCP observations and report paths can be
untrusted. The workbench must not treat observations as instructions or model
summaries as execution facts.

Generated Python executes with the permissions of its host process. Static
assertion checks and loopback settings are not an OS sandbox. Use a disposable
workspace without real credentials and retain host approval controls. Review code
before promoting an example or using it outside the synthetic local target.

## Required invariants

- Forged, expired or revoked sessions cannot authorize a mutation.
- Cross-origin browser requests cannot trigger authenticated mutations.
- Test reset is disabled outside explicit test mode and requires the instance
  control credential. It cannot reset another run or arbitrary filesystem paths.
- Uploaded content has bounded type/size/pixel handling and server-selected paths;
  malformed content and path traversal cannot expose unintended files.
- Execution services are loopback-only; the runner must not reuse or kill an
  unrelated process based solely on a successful health endpoint.
- Missing, duplicated, contradictory or interrupted execution evidence cannot
  produce a passing quality gate.
- Repair cannot silently remove cases, change frozen expectations or replace
  earlier failure evidence.
- Public exports and CI artifacts must not disclose real credentials, browser
  state, private paths, hostnames or unnecessary personal identifiers.

## Reporting and severity context

Report concrete violations of those boundaries, including secret exposure,
unauthorized actions, unsafe file handling and misleading passing results.
Local-only deployment is context for severity, not grounds to dismiss a real
finding. State the reachable input, affected asset, prerequisites and evidence.

The opt-in comment_counter fixture intentionally violates a business count rule.
Its expected failure alone is not a security vulnerability. A way to activate
test controls without authorization, escape their scope or hide that failure
remains reportable. There is no blanket exclusion for AI-generated code,
dependencies, authentication, browser integration or report handling.

## Limits and disclosure

There is no security certification or production support promise. A secret scan
does not replace vulnerability review, and a passing test does not prove the
absence of a vulnerability.

Private vulnerability reporting is not configured before repository publication.
Do not post secrets, full traces or exploit data in a public issue. During local
evaluation, use an existing private contact channel with the maintainer. A private
reporting route must be established before public launch.

This policy changes neither host permissions nor the user's approval requirements.
