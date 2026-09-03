# Launch and contribution plan

Do not publish this pre-release until the acceptance gates, source/license review and privacy checks
are complete. Stars are not a quality guarantee and there is no reliable promise of earning them.

## Make the first five minutes useful

- Keep the no-model baseline one command away after setup.
- Show one healthy run, one preserved business failure and one rejected incomplete result.
- Provide real screenshots and readable evidence, not a conceptual mockup presented as execution.
- Keep the maintainer's time bounded with clear supported modes, troubleshooting and small examples.

## Initial contribution candidates

These are draft ideas, not existing GitHub issues. Create only tasks that are still useful after release.

1. **PowerShell setup verification:** document commands and verify a clean Windows setup without
   weakening privacy/defaults. Acceptance: recorded environment and the same baseline/contract checks.
2. **Keyboard-only UI regression:** cover login, publish and feed controls using keyboard focus.
   Acceptance: deterministic local tests and any accessibility fix documented with evidence.
3. **Duplicate-title Page Object helper:** add selection by stable post ID and regression with two
   matching titles. Acceptance: intended card selected without positional selectors or weakened asserts.
4. **Plan rule-distribution summary:** show how cases reference rules without calling this full
   requirements coverage. Acceptance: known mapping fixture, no invented coverage percentages.
5. **A worked repair-receipt tutorial:** explain one before/after locator repair and preserved failure,
   using sanitized artifacts. Acceptance: commands reproduce the demonstrated state transitions.

## Reach people who have this problem

After launch, write a technical LinkedIn walkthrough and share within relevant testing/TRAE communities
according to their rules. Answer early reproducibility questions. Use focused releases and a changelog.
Do not buy stars, request unrelated mutual stars, mass-post or submit unreviewed promotional PRs.
Track reproducible usage, useful issues and outside contributions alongside stars.

## Unsent LinkedIn draft

I'm building spec-to-pytest, a small local workbench for AI-assisted test generation with Python,
Playwright and Pytest. My focus is the evidence around a test result: what was planned, what was
collected, what actually ran, and whether those records agree.

One example deliberately introduces a wrong comment count. The test keeps failing, with its original
evidence preserved. A successful demonstration does not turn the failed business assertion green.

There is also a no-model baseline and a separately labelled historical replay. The TRAE integration
uses two focused roles for test generation and test data. I want to make the limits as clear as the
useful parts, especially around generated assertions and safe execution.

Feedback from QA engineers and Python test-framework maintainers would be valuable—particularly on
reproducibility, reviewable test oracles and making a first contribution easy.

Add a repository link only after publication. Update the draft with actual host/CI verification status;
do not imply that a personal project is production work experience.
