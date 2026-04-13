# Spec-to-Work Decomposition Guide

## Decomposition Axis: Cut by Layer, Not by Feature

Spec documents describe a feature end-to-end. Work items should cut **horizontally by system layer**, not vertically by sub-feature.

```
Good (by layer):              Bad (by feature):
  DB Migration                  "Prefix support"
  Core Models                   "Slug support"  
  Core Repositories             "Ref-ID support"
  CLI Commands                  "Search updates"
  API / MCP Server              "Error message updates"
  Dashboard / UI
```

**Why:** Layers have clear interfaces. A model change is testable in isolation. A "feature slice" like "prefix support" touches DB + models + repos + CLI + MCP + dashboard — it's a mini-project, not a work item.

**Exception:** If a spec has genuinely independent features with no shared code (e.g., "add CSV export" and "add webhook notifications"), split by feature first, then by layer within each.

## Dependency Chain = Execution Order

Every spec has a natural dependency spine. Identify it and make it the child work order:

```
Database schema
  +-> Core models / types
       +-> Data access (repositories, queries)
            +-> Consumer A (CLI commands)
            +-> Consumer B (API / MCP server)  <- can parallelize
            +-> Consumer C (Dashboard / UI)    <- can parallelize
                 +-> E2E validation + documentation
```

**Rules:**
- Every child must have its dependencies explicitly declared via `--depends-on`
- The dependency graph must be a DAG (no cycles)
- If two children have no dependency on each other, they can be executed in parallel
- The first child is always the one with zero dependencies (usually DB or schema)

## Sizing: One Session, One Layer, One Deliverable

Each work item should be completable in a **single focused session**. Gauge by:

| Signal | Too small | Right size | Too big |
|--------|-----------|------------|---------|
| Files touched | 1-2 files, trivial changes | 3-15 files in one layer | 20+ files across layers |
| Conceptual scope | Single field rename | All model changes for a feature | Models + repos + commands |
| Test surface | Nothing meaningful to test alone | Has own unit/integration tests | Requires multi-layer tests to verify |

**If too big:** Split within the layer. E.g., "CLI Commands" can become "CLI: Command Infrastructure (helpers, resolvers)" + "CLI: All Command Updates" when the helper refactor is substantial enough.

**If too small:** Merge with an adjacent item. Don't create a work item for "add one field to one model" — bundle it with the broader model change.

## Test Guidelines

**Rule: Every work item includes its own tests. "Done" means "tested."**

### What tests belong to which work item:

| Layer | Test Type | What to Test |
|-------|-----------|-------------|
| **DB Migration** | SQL validation queries | Backfill completeness, constraint enforcement, trigger behavior, idempotency. Run against empty DB and seeded DB. |
| **Core Models / Types** | Unit tests | `fromMap()`, `toJson()`, `copyWith()`, validation logic, edge cases (nulls, empty strings, boundary values) |
| **Core Utilities** | Unit tests | Parser functions, generators, validators — happy path + every edge case in the spec |
| **Repositories** | Unit tests (in-memory DB) | New query methods, create/update with new fields, error cases (not found, duplicate) |
| **CLI Commands** | Integration tests (subprocess) | Each changed command with new input formats, error messages, output shape. At minimum: one happy path + one error path per command. |
| **API / MCP Server** | Integration tests | Tool input acceptance, response format, resolution logic, error responses |
| **Dashboard / UI** | Widget tests (if coverage exists) | Only if the project already has widget test patterns. Don't introduce a new test layer just for this. |

### What goes in the final E2E work item:

The last child work item covers **cross-layer concerns only**:

- **End-to-end smoke tests** — full workflow spanning multiple layers (e.g., create entity via CLI -> verify in DB -> query via MCP -> check dashboard renders)
- **Migration validation** — run migration against production-like data, verify data integrity
- **Performance validation** — if the spec has NFRs on latency/throughput
- **Documentation** — update project specs, guides, memory files

### Test rules of thumb:

1. **If the spec says "must", write a test.** Every FR and NFR that says "must" maps to at least one test assertion.
2. **Test the contract, not the implementation.** Test that `toJson()` outputs the right shape, not that it calls a specific internal method.
3. **Error paths are first-class.** The spec's "Error States" section maps directly to test cases. Every error message in the spec = one test.
4. **Edge cases from the spec's "Edge Cases" section get explicit tests.** Don't assume they're covered by happy-path tests.
5. **Don't test what the database enforces.** If a CHECK constraint prevents invalid data, there is no need for an application-level test for the same validation (but do test that the app surfaces the error gracefully).

## Common Mistakes

| Mistake | Why it's bad | Fix |
|---------|-------------|-----|
| "Write tests" as a separate work item per layer | Context loss; code author knows edge cases best | Embed tests in each layer's work item |
| One giant "update all commands" item | Too big for one session, unclear progress | Split by infrastructure vs. commands, or by entity type if very large |
| Splitting DB migration into multiple items | Migrations run as one transaction; partial migrations are dangerous | Keep as one work item, even if the SQL is long |
| "Documentation" scattered across every item | Docs get stale if updated before code stabilizes | Bundle docs in the final E2E item after all code ships |
| No explicit dependency edges | Work items get started out of order, hit blockers | Always state `--depends-on` |
| Vertical slicing by sub-feature | Each slice touches every layer, creating cross-cutting work | Cut horizontally by layer instead |
| Parent description repeats child details | Implementation details and test strategies appear in both parent and children, causing drift and noise | Parent gets one-sentence goal + source doc references only; all detail lives in children |

## Work Item Description Template

The canonical child description template is in **SKILL.md Step 3b**. Key constraints repeated here for quick reference:

- **Source Documents** is mandatory — SPEC and PRD paths with section/FR numbers.
- **Changes** must be concrete (not "update stuff").
- **Tests** must specify type and what to verify, per the Test Guidelines table above.
- **Done when** lists acceptance criteria from the spec's FR/NFR "must" statements.

For the parent description template, see **SKILL.md Step 3a** — one-sentence goal + source doc references only.
