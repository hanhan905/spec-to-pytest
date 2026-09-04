# Architecture and trust

Four responsibilities stay separate: the local practice app; maintained automation; the optional
generation host; and deterministic evidence checking. `framework/ai/` contains no LLM client.

The TRAE built-in Agent coordinates the generator and data expander. The generator designs cases
and writes Python; the expander writes CSV. The Skill describes that data process. The official MCP
server directly operates a real local browser. Pytest executes assertions. The reconciler checks the
formal execution records; it does not authenticate the MCP exploration transcript.

## Why explore before running tests?

Exploration is a real preflight interaction to learn locators, transitions and observable states.
It changes data, so it uses a separate instance. Its success is not a test passing. Later pytest
starts clean and evaluates business assertions. Local knowledge promotion requires a checked passing
run and matching exploration evidence. In v0.1 a partially failed batch does not promote knowledge.

## Results are not free-form text

Unique case IDs link the frozen plan to collection, setup/call/teardown events, JUnit and process exit
status. Missing cases, duplicate IDs, broken XML, unexpected skips and interruption cannot become green.
Final acceptance covers the entire plan; earlier isolated passes are not combined across source versions.

The maintained baseline's inventory comes from pytest collection, not a separate requirement plan.
It checks record consistency, not requirement completeness. Generated and replayed runs instead
supply a pre-existing plan whose case set is checked against execution.

Hashes detect changed files, not an attacker who can rewrite all records. Assertion guards are
conservative checks, not semantic proof or execution containment. A generator can initially choose a
bad oracle; maintainer review and known-defect checks remain essential.

| Directory | Ownership and role |
|---|---|
| `practice_app/` | Maintained local business system |
| `framework/pages`, `workflows`, `plugins` | Reusable deterministic automation |
| `framework/ai/` | Contracts, integrity, reconciliation and step checks |
| `mana/` | Scenarios, rules, schemas and generation instructions |
| `integrations/trae/`, `.agents/skills/` | Optional host configuration and data workflow |
| `tests/` | Maintained app/workbench regressions |
| `tests/generated/` | Ignored per-run output, never auto-promoted |
| `examples/candidates/` | Historical ports pending maintainer approval |
| `examples/approved/` | Created only after the corresponding snapshot is approved |
| `reports/runs/` | Private attempts, source snapshots and machine evidence |
| `.local/` | Private exploration data, locks and verified knowledge |

The migration retains provenance without publishing old Git history, private settings or reports.
