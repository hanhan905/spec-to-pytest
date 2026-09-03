# Acceptance status

Development checkpoint, 2026-09-03. This is not a v0.1 release announcement.

## Observed so far

- Python 3.14.7 on macOS arm64; lock resolves FastAPI 0.141.1, Starlette 0.52.1,
  AnyIO 4.14.2, Pytest 9.1.1, Playwright 1.62.0, Pillow 12.3.0.
- 13 API/UI checks passed using isolated Chromium (including real image rendering).
- A complete baseline through the new runner produced 13 passed, 0 failed, 0 skipped,
  0 blocked after checking collection, events, JUnit and the process exit status.
- 65 unit/contract tests passed before the additional integrity checks; the 10 added
  integrity/data tests also passed separately. A combined final run is still required.
- Ruff and mypy passed at intermediate checkpoints; final checks run after the remaining changes.

## Observed failures and resolutions

- The first new app regression failed at collection because `create_app` did not exist;
  the factory and isolated state were implemented and the tests then passed.
- The inherited Ruff `exclude` setting replaced default environment exclusions. A formatting
  run touched dependencies in this task's disposable environment/cache. No original project or
  global Python was affected. Exclusions were changed to `extend-exclude`, dependencies reinstalled
  from a fresh private cache, and the file list verified to include only project sources.
- An early browser run happened before the matching browser download finished: 4 API tests
  passed, 9 browser setup errors occurred. After installation, all 13 passed.
- The initial runner missed early registration of its pytest options and returned blocked.
  Explicit plugin loading fixed it; no failed attempt was converted into a passed report.

## Still required before release

Final combined and repeat/order checks; lifecycle timeout/cleanup and repair integration checks;
approved replay and knowledge promotion; a real TRAE host run; final media privacy review;
secret scanning; source/asset review and license approval; actual Linux and GitHub CI runs.
Do not infer these from the local baseline or from schema validation alone.
