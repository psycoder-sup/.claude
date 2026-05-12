# Plan Template

Use this structure when writing an implementation plan. The plan is the bridge between PRD (what+why) and code (how). It includes the technical approach, file-by-file changes, types, and a tagged task list — each task carries its own tests — that `/execute-plan` runs against.

```markdown
# Plan: <feature>

**Date:** YYYY-MM-DD
**Status:** Draft | Approved | Executed
**Based on:** docs/feature/<feature-name>/YYYY-MM-DD-<feature-name>-prd.md

---

## 1. Approach
~10-20 lines of prose. Explain:
- How this feature fits into the existing architecture
- The key design decision(s) and why this approach over alternatives
- Which existing patterns/modules it follows or extends
- Anything load-bearing that the rest of the plan depends on

If you can't write this without filler, the design isn't ready.

## 2. File-by-file Changes
| File | Change | Notes |
|------|--------|-------|
| src/x.ts | new | Exports `useFoo` hook |
| src/y.ts | modify | Add `foo` column handling |
| db/migrations/NNN-foo.sql | new | Adds `foo` table |

One row per file. Be specific in "Notes" about what changes — not "update stuff."

## 3. Types & Interfaces
**Verbatim type code in the project's language.** This is the ONE place code lives in the plan (test skeletons in §4 are the other). Implementer subagents copy these directly — do not summarize.

```ts
// Real declarations. Example (TypeScript):
export interface Foo {
  id: string;
  userId: string;
  createdAt: Date;
}

export type FooStatus =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ready"; foos: Foo[] };
```

If types span multiple files (frontend + backend, schema + types), include each block with a clear file path comment.

## 4. Tasks
Numbered, dependency-ordered. Each task has a model tag, file scope, dependencies, deliverables, "done when", and an inline **Tests** list. Tests live with the task that introduces them — there is no separate test-plan section.

Per-task structure:

1. **[model: sonnet]** DB migration for `foo` table
   - **Files:** `db/migrations/NNN-foo.sql`
   - **Depends on:** —
   - **Done when:** migration applies cleanly, schema includes `foo` table with columns from §3
   - **Tests:**
     - **FR-04**: `foo table created with expected columns` — `db/migrations/__tests__/NNN-foo.test.ts`
     - **FR-04**: `unique constraint on foo.url rejects duplicates` — same file

2. **[model: sonnet]** Backend: foo repository + create/list functions
   - **Files:** `src/foo/repository.ts`, `src/foo/service.ts`
   - **Depends on:** 1
   - **Done when:** FR-01, FR-02 covered by passing tests
   - **Tests:**
     - **FR-01**: `creates a foo and lists it` — integration test in `tests/foo.test.ts`
     - **FR-02**: `rejects duplicate foo URL` — unit test in `tests/foo-validate.test.ts`

     ```ts
     // FR-01 skeleton (only include skeletons for non-trivial tests):
     it("creates a foo and lists it", async () => {
       const user = await createUser();
       await createFoo({ userId: user.id, url: "..." });
       const list = await listFoos(user.id);
       expect(list).toHaveLength(1);
     });
     ```

3. **[model: haiku]** UI: FooList component (display only)
   - **Files:** `src/components/FooList.tsx`
   - **Depends on:** 2
   - **Done when:** FR-03 covered, renders empty state, renders populated state
   - **Tests:**
     - **FR-03**: `displays empty state when user has no foos` — `tests/FooList.test.tsx`
     - **FR-03**: `renders populated list` — same file

4. **[model: opus]** Wire FooList into the existing dashboard, including auth guard
   - **Files:** `src/screens/Dashboard.tsx`, `src/auth/guards.ts`
   - **Depends on:** 2, 3
   - **Done when:** feature accessible from dashboard nav, gated by existing auth, all tests pass
   - **Tests:**
     - **FR-05**: `unauthenticated users redirected to /login` — `tests/Dashboard.test.tsx`
     - **FR-05**: `authenticated users see FooList in dashboard` — same file

### Authoring rules for §4

- **Every task must list at least one test** under **Tests:**, even if it's a single happy-path assertion. A task with no tests is a smell.
- **Every PRD FR must appear in at least one task's Tests list.** If an FR has no covering test in any task, the plan is incomplete.
- **Tag each test with its FR** (e.g., `**FR-01**:`) so coverage is auditable at a glance.
- **Skeletons are optional** — include a short code block when the test logic is non-obvious. Skip skeletons for trivial assertions.
- Tests for a task should exercise behavior the task itself introduces. If a test depends on code from a later task, the test belongs in that later task.

### Model tag heuristic

| Tier | Use when |
|---|---|
| **haiku** | 1 file, <50 LOC, mechanical (rename, format, simple wire-up, copy boilerplate) |
| **sonnet** *(default)* | 1–3 files, follows existing patterns, well-specified |
| **opus** | Multi-file design work, debugging unfamiliar code, novel pattern, ambiguous scope |

If unsure → sonnet.

## 5. Risks & Open Questions
- **Risk:** <what could go wrong, mitigation>
- **Open question:** <unresolved decision, who needs to weigh in>

If empty, write "None known" — empty section is suspicious.
```

**Filename convention:** `docs/feature/<feature-name>/YYYY-MM-DD-<feature-name>-plan.md` (kebab-case feature name for both the directory and the file; date is the day the plan was authored — does not need to match the PRD's date). The plan lives in the same `docs/feature/<feature-name>/` directory as the PRD.
