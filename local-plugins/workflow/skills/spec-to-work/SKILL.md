---
name: spec-to-work
description: >-
  This skill should be used when the user asks to "create work items from a spec",
  "decompose a spec into work items", "break down the spec into tasks",
  "spec to work items", "create tasks from spec", "plan the implementation for
  this spec", "turn this spec into a work breakdown", or wants to convert a
  technical spec (SPEC) document into structured baragi work items with proper
  dependencies and embedded test criteria.
---

# Spec to Work Items

Decompose a technical spec (SPEC) document into baragi work items: one parent work with layer-scoped children, dependency edges, and embedded test criteria. Each work item includes references to its source SPEC and PRD documents so that the agent working on it has full context.

## Prerequisites

- A SPEC document exists (the user provides the path or references it)
- A baragi project exists (the work items will be created in the current project)

## Workflow

### Phase 1: Read and Analyze the Spec

Read the full spec document. Also locate its companion PRD (typically referenced in the spec's frontmatter or header). Record both file paths — these will be embedded in every work item.

Identify:

1. **Source documents** — Record the absolute paths to:
   - The SPEC document (e.g., `docs/feature/foo/foo-spec.md`)
   - The PRD document (e.g., `docs/feature/foo/foo-prd.md`)

2. **System layers touched** — Which of these layers does the spec affect? (Adapt this list to the project's architecture — not every project has all layers.)
   - Database (schema, migrations, triggers, RPC functions, RLS policies)
   - Core models / types
   - Core utilities (parsers, generators, validators)
   - Repositories / data access
   - CLI commands
   - API / MCP server
   - Dashboard / UI
   - Documentation

3. **Dependency spine** — Which layers depend on which? The typical order is:
   ```
   DB -> Models -> Repositories -> CLI / MCP / Dashboard -> E2E + Docs
   ```

4. **Size assessment** — For each layer, estimate if the changes are small enough for one work item or need splitting. Consult `references/decomposition-guide.md` for sizing criteria.

### Phase 2: Propose Decomposition

Present the proposed work items to the user as a table before creating anything:

```
| # | Title | Scope | Tests | Depends on |
|---|-------|-------|-------|------------|
| P | Parent: [Feature Name] | Overall feature | - | - |
| 1 | DB Migration | schema, triggers, backfill, RPC | SQL validation queries | - |
| 2 | Core: Models + Utilities | model fields, parsers | Unit tests | 1 |
| ...
```

Wait for user confirmation or adjustments before proceeding.

### Phase 3: Create Work Items

After user approval, create work items using the baragi CLI.

**Step 3a — Create the parent work:**

```bash
baragi work add "[Feature Name]" \
  --labels=feature \
  --description="$(cat <<'DESC'
Phase N of [Feature]: [one-sentence goal]. Reference: SPEC [spec-path] Section N ([phase section]). PRD: [prd-path] [FR range].
DESC
)"
```

Capture the parent work ID from the output (e.g., `BAR-010`).

**Parent description rules:**
- **One sentence** stating the high-level goal — what this phase/feature delivers, not how.
- **Source document references** (SPEC and PRD paths with section/FR numbers) — same as children.
- **No `--depends-on`** — the parent is the dependency root, not a dependency itself.
- **Do NOT include** implementation details (files, classes, methods), test strategies, or acceptance criteria — these belong exclusively in the children.
- The parent is a container for tracking and context. The children carry all the detail.

Example parent description:
```
Phase 3 of CLI Tool: implement CRUD commands for CLI-to-app IPC. Reference: SPEC docs/feature/cli-tool/cli-tool-spec.md Section 8 (IPC Commands). PRD: docs/feature/cli-tool/cli-tool-prd.md FR-12 through FR-18.
```

**Step 3b — Create child work items in dependency order:**

For each child, construct a description that includes source document references, scope, changes, tests, and acceptance criteria. Use `--depends-on` at creation time when the dependency already exists:

```bash
baragi work add "[Child Title]" \
  --parent-id=BAR-010 \
  --depends-on=BAR-011 \
  --labels=db \
  --description="$(cat <<'DESC'
**Source Documents:**
- SPEC: docs/feature/foo/foo-spec.md (Section N: [relevant section])
- PRD: docs/feature/foo/foo-prd.md (FR-01 through FR-10)

**Scope:** [files/modules to touch]

**Changes:**
- [concrete change 1]
- [concrete change 2]

**Tests:**
- [test type]: [what to test]
- [test type]: [what to test]

**Done when:**
- [acceptance criterion 1]
- [acceptance criterion 2]
- All tests pass, no regressions
DESC
)"
```

**Description template rules:**
- **Source Documents** section is mandatory. Include the SPEC and PRD paths with the specific section numbers and FR/NFR numbers relevant to this child. This gives the implementing agent full context without reading the entire document.
- **Scope** lists the files and modules to touch.
- **Changes** lists concrete changes (not "update stuff").
- **Tests** specifies test type and what to verify, per `references/decomposition-guide.md`.
- **Done when** lists acceptance criteria derived from the spec's FR/NFR "must" statements.

**Step 3c — Verify the structure:**

```bash
baragi next --all --parent-id=BAR-010 --fields=title,status,is_blocked
```

Confirm all children exist, dependencies are correct, and the first child is unblocked.

## Key Rules

1. **Every work item references its source documents.** The description must include paths to the SPEC and PRD with relevant section/FR numbers. An agent picking up the work item should be able to read the referenced sections and have full context.

2. **Cut by layer, not by feature.** Each child work item scopes to one system layer. Never create a child that spans DB + models + commands.

3. **Every child includes its own tests.** "Done" means "tested." Consult `references/decomposition-guide.md` for which test types belong to which layer.

4. **DB migration is always one work item.** Migrations run as a single transaction. Never split a migration across multiple work items.

5. **The last child is E2E validation + documentation.** Cross-layer smoke tests and doc updates go here — not scattered across every child.

6. **Dependencies must form a DAG.** Use `--depends-on` at creation time. No cycles. Children with no mutual dependency can be parallelized.

7. **Respect the spec's "must" statements.** Every FR/NFR that says "must" maps to at least one test assertion in the relevant child's acceptance criteria.

8. **Size for one session.** If a layer touches 20+ files, split it. If a layer touches 1-2 files trivially, merge it with an adjacent layer. Target 3-15 files per child.

## Handling Edge Cases

- **Spec touches only 2-3 layers:** Create fewer children. A 2-child decomposition (DB + app code) is fine — don't force 7 children when the spec is small.
- **Spec has independent sub-features:** Split by feature first, then by layer within each. Each feature can be its own parent work.
- **No DB changes:** Skip the DB migration child. Start from models or wherever the dependency chain begins.
- **Spec is ambiguous about scope:** Flag the ambiguity to the user before proposing decomposition. Ask which layers are affected.
- **No companion PRD:** If the spec has no PRD, omit the PRD line from the Source Documents section. The SPEC path alone is sufficient.

## Additional Resources

### Reference Files

For detailed decomposition criteria, sizing guidelines, test mapping per layer, and common mistakes:
- **`references/decomposition-guide.md`** — Full decomposition guide with sizing table, test guidelines per layer, work item description template, and common mistakes to avoid
