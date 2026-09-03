# Structured checks and bounded repairs

Policy 2.1 separates an executable comparison from a model's description. It does
not prove that arbitrary natural language has been interpreted correctly.

## Plan an expectation

Each case retains `expected_results` and adds matching `expectations` and `checks`.
This is a **case fragment**, not a full run plan:

```json
{
  "expected_results": ["发布后显示成功提示"],
  "expectations": [
    {"expectation_id": "EXPECT_PUBLISH", "text": "发布后显示成功提示", "check_ids": ["CHECK_PUBLISH"]}
  ],
  "checks": [
    {"check_id": "CHECK_PUBLISH", "subject": "publish.status", "operator": "equals", "expected": "内容发布成功！", "rule_ids": ["POST-01"]}
  ]
}
```

The case also declares those rule IDs. Use an explicit exploratory reason where no
authoritative rule exists. Do not invent a precise error message from a vague rejection
rule. Check and expectation IDs are globally unique within the plan.

Operators: `equals`, `contains`, `ordered_equals`, `count`, `visible`, `url_equals`,
`attribute_equals`, `property_equals`. Attribute/property operands contain `name` and
`value`; visibility uses a boolean, count a nonnegative integer, ordered equality a
list. `expected_ref` can instead name a frozen CSV `data_id` and string field for
equality/containment/URL checks. Declare that row in the case's `data_ids`.

## Execute the frozen comparison

```python
from framework.ai.checks import verify

# The framework loads both comparison and expected text from the frozen plan.
verify("CHECK_PUBLISH", publish_page.success)
```

Provide a real observed scalar or Playwright locator/page. Locator checks use
Playwright auto-waiting; scalar checks do not implicitly coerce booleans.
`bool(error_detail)` cannot fulfil a string-containment check.

Invoke every required check exactly once inside the test body. Checks before and
after refresh need different planned IDs. Setup-only, missing, duplicate and cross-case
checks reject workflow acceptance. Source bindings are compared with concrete Pytest
collection, including the selected-browser suffix.

Load declared data through `framework.data.content.load_row` or `post_data` inside
the test body. Planner-reserved IDs may be created by the expander. Runtime reads
are recorded; extra CSV rows are not executed tests or measured coverage.

## Register narrow repair points

```python
from framework.ai import actions

actions.fill(page, "USERNAME", "admin", label="用户名", timeout=5000)
actions.click(page, "LOGIN", role="button", name="登录", timeout=5000)
actions.wait_visible(page, "DASHBOARD", test_id="current-user", timeout=5000)
```

Action helpers return no observations. Use standalone calls, unique literal IDs
and explicit literal selectors. Choose `role` plus `name`, `label`, `test_id`, or
`css`; `exact` defaults to true.

After first execution, only registered click/fill selector literals or existing
100–30000 ms timeout values may change. Wait conditions stay fixed. The remaining
parsed source is frozen: imports, classes, helpers, assignments, request clients,
checks and observation sources. Ordinary Page Objects work but are not automatic
repair points.

At most three allowed repairs may run. Each has a full-suite execution, new request
ID, parent reference, reason and retained patch. API property/import/syntax mistakes
after execution need a corrected **new run**. Do not introduce wrappers or rebind
objects to retain an old assertion's text. Rejected patches remain under
`repair-proposals/` and do not become the source baseline.

## Limit

An agent can still select a wrong subject or fabricate an observation. Bindings and
AST guards are not a sandbox or general semantic proof. A maintainer reviews rules,
contracts and observation sources before workflow verification and public-example
promotion. See [workflow acceptance](workflow-acceptance.md).
