# Visual and interaction QA

Local check on 2026-09-03 using the project's Python Playwright and isolated Chromium.
Browser plugin/skill was unavailable in this session; the project test workflow was used.
The tested URL was `http://127.0.0.1:8767/feed`; that temporary owned service has been stopped.

Real image upload, search, like and comment were exercised at 1440×900 and 390×844.
Only synthetic content and the demo admin account were used, not personal browser state.

| Check | Result |
|---|---|
| Page identity and expected title | Passed |
| Meaningful non-blank content | Passed |
| No framework/error overlay | Passed |
| Browser console/page errors | None observed |
| Stored image actually decoded | Passed, 320×180 synthetic PNG |
| Desktop publish → search → like → comment | Passed |
| Mobile like cancellation and count update | Passed |
| Horizontal overflow | None at either tested size |

The blue image is a real uploaded synthetic fixture, not a mockup of the application.
Screenshots were visually reviewed for private content before inclusion; PNG metadata has no EXIF.
Full traces, videos, cookies and database files remain local-only.

See [desktop screenshot](../assets/demo-desktop.png) and [mobile first viewport](../assets/demo-mobile.png).
The raw local result is `reports/verification/visual/result.json` and is not committed.
Other viewports, operating systems and browser engines were not verified. Keyboard-only or
assistive-technology audits are not implied by these checks.

For future interactive in-app QA, a plugin exposing the Browser skill could provide a convenient
navigation/evidence workflow; no plugin installation was performed for this check.
