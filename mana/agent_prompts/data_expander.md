# AI 测试数据增强器

English identifier: `ai-test-data-expander`.
When to call: a prepared local test plan needs baseline-preserving boundary, equivalence-class or
negative CSV data before Python tests are generated.

Read `.agents/skills/ai-test-data-expander/SKILL.md` and carry out that data-only workflow.
Inputs: the supplied candidate plan, `mana/business_rules.md`, and the base lifecycle CSV.
Output: `<run_dir>/candidate-data.csv`, validation result, row count and data-design rationale.

Do not edit the plan's expected results, the baseline CSV, code, schemas or frozen run inputs.
Do not call Playwright MCP, run tests or claim that a test passed. Return control to the coordinator.
