# Troubleshooting

| Symptom | Check first | Do not do this |
|---|---|---|
| Port occupied | Pick an unused loopback port; separate MCP from pytest | Kill or silently reuse another service |
| Browser executable missing | Finish `uv run playwright install chromium` | Mark setup errors passed or delete cases |
| Data/rule reference rejected | Check data IDs, rule IDs and candidate validation | Weaken the schema |
| Protected inputs changed | Create a new run after the maintenance change | Rewrite frozen records |
| Missing case or unexpected skip | Compare plan and collection.json | Drop the case to obtain green |
| Defect-mode comment-count failure | Read the inner failure and database evidence | Change the expected count to zero |
| Allure command missing | Read manifest/JUnit or install optional CLI separately | Treat report rendering as a passing test |
| Second role not called | Check host settings or use the labelled Skill fallback | Pretend delegation happened |

Exit codes: 0 for a passing checked gate, 1 for test/gate failure, 2 for environmental/evidence
blockage. Raw pytest exit codes remain separate. Raw artifacts can include local paths, cookies and
typed values; keep them private. Public export includes only aggregates and a hashed run reference.
