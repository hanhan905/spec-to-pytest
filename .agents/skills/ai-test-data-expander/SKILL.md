---
name: ai-test-data-expander
description: Expand local spec-to-pytest lifecycle CSV data from a validated test plan using equivalence classes, boundaries and negative cases. Use for test-data generation, not browser execution or business-rule changes.
---

# Expand lifecycle test data

Inputs are a run's candidate plan, `mana/business_rules.md`, and
`mana/test_data/content_base.csv`. Work only inside the prepared local run directory.

1. Read the plan and identify which rules and input dimensions need data.
2. Preserve all baseline rows. Add unique uppercase `data_id` values; these identify data rows,
   not test cases. Keep columns exactly `data_id,title,content,tags,comment,expected_valid`.
3. Use valid/invalid equivalence classes, min/max/just-outside boundaries, whitespace, Unicode,
   duplicate tags and relevant combinations. Do not invent unsupported business capabilities.
4. For this lifecycle dataset, `expected_valid` is the conjunction of trimmed title length 1–50,
   body length 1–500 and comment length 1–100. It is not the outcome of an entire test.
   Image data belongs in code fixtures, not binary CSV fields.
5. Write a new `candidate-data.csv` under the run directory. Never overwrite the baseline or
   already-frozen `data.csv`. Do not edit the plan's business expectations.
6. Run `uv run --frozen python -m scripts.validate_ai_assets csv <candidate-data.csv>`.
   Repair only the candidate data if validation fails; do not weaken the validator or rules.
7. Return the relative output path, row count, added data IDs, covered dimensions and validation
   outcome. The coordinator passes these back to the test generator.

Do not call browser tools, run generated tests, change application/framework code, read real
credentials or claim a test has passed. Loading this Skill does not itself invoke another Agent.
