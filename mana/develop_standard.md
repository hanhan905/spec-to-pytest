# Generated-test contract

- Read the approved scenario and stable rule IDs; do not derive expected behavior from observed bugs.
- Write only to `tests/generated/<run_id>/` and that run's candidate artifacts.
- Mark each test with exactly one `@pytest.mark.case_id("CASE_ID")`. One planned case maps to one node.
- Use Pytest, Python Playwright and Allure steps. Reuse maintained Page Objects and workflows.
- Include explicit outcome assertions in every generated test file. Setup assertions alone are not
  sufficient; a maintainer must review the business oracle before an example is promoted.
- New AI plans use schema 2.1. Bind each expected result to structured checks and call the
  maintenance-owned `verify(check_id, observation)` helper in the test body. Missing checks,
  cross-case mappings and weakened comparison operators do not satisfy workflow acceptance.
- Read data through `framework.data.content` using `data_id`; it reads the frozen run CSV.
- Use `configured_page` / `authenticated_page` for isolated UI tests and the provided API client.
- Do not reset through browser requests. UI fixtures reset their owned instance; an API-only test
  can use `PracticeApiClient(settings.api_url, control_token=settings.control_token)`.
- Prefer role/name, labels and stable test IDs. Use Playwright expectations rather than fixed sleeps.
- No absolute paths, external network targets, real accounts, downloaded programs, skip/xfail or
  exception handlers that hide failures. `try/finally` resource cleanup is allowed.
- Keep ordinary tests outside generated directories. Shared framework, application, rules, schemas,
  approved/candidate bundles and prompts are maintenance-owned, not automatic-repair targets.
- Up to three documented repair rounds; changes to expectations require a new reviewed scenario/run.
- After first execution, only registered standalone `framework.ai.actions` selector literals and
  existing 100–30000 ms timeouts may be automatically repaired. Imports, helper/class definitions,
  rebinding, API adapters, data, check locators and other statement changes require a new run.
- A stable request ID identifies one intended full execution. Retry an uncertain tool response with
  that same ID; intentional repeats/repairs use linked new IDs and a reason. Never infer the caller
  of a duplicate execution from its timing alone.
- The final verdict comes from a full acceptance attempt's collection, phase events, JUnit and exit code.
  Model-written explanations never replace those artifacts.
- Execution and AI workflow gates are separate. Direct MCP observations do not prove custom-Agent
  delegation; structural checks do not prove arbitrary natural-language semantics. Maintainer
  review is required before workflow verification or public-example promotion.
