# Plan Template

Use this structure when writing an implementation plan. The plan is the bridge between PRD (what+why) and code (how). It includes the technical approach, file-by-file changes, types, test plan, and a tagged task list that `/execute-plan` runs against.

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
**Verbatim type code in the project's language.** This is the ONE place code lives in the plan. Implementer subagents copy these directly — do not summarize.

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

## 4. Test Plan
One bullet per test. Reference the FR from the PRD and the task from §5 it belongs to.

- **FR-01** (task 2): `creates a foo and lists it` — integration test in `tests/foo.test.ts`
- **FR-02** (task 2): `rejects duplicate foo URL` — unit test in `tests/foo-validate.test.ts`
- **FR-03** (task 3): `displays empty state when user has no foos` — component test in `tests/FooList.test.tsx`

For non-trivial tests, include a one-line skeleton:

```ts
// FR-01:
it("creates a foo and lists it", async () => {
  const user = await createUser();
  await createFoo({ userId: user.id, url: "..." });
  const list = await listFoos(user.id);
  expect(list).toHaveLength(1);
});
```

Skip skeletons for trivial assertions.

## 5. Tasks
Numbered, dependency-ordered. Each task has a model tag, file scope, dependencies, deliverables, and "done when."

1. **[model: sonnet]** DB migration for `foo` table
   - Files: `db/migrations/NNN-foo.sql`
   - Depends on: —
   - Done when: migration applies cleanly, schema includes `foo` table with columns from §3

2. **[model: sonnet]** Backend: foo repository + create/list functions
   - Files: `src/foo/repository.ts`, `src/foo/service.ts`
   - Depends on: 1
   - Done when: FR-01, FR-02 covered by passing tests

3. **[model: haiku]** UI: FooList component (display only)
   - Files: `src/components/FooList.tsx`
   - Depends on: 2
   - Done when: FR-03 covered, renders empty state, renders populated state

4. **[model: opus]** Wire FooList into the existing dashboard, including auth guard
   - Files: `src/screens/Dashboard.tsx`, `src/auth/guards.ts`
   - Depends on: 2, 3
   - Done when: feature accessible from dashboard nav, gated by existing auth, all tests pass

### Model tag heuristic

| Tier | Use when |
|---|---|
| **haiku** | 1 file, <50 LOC, mechanical (rename, format, simple wire-up, copy boilerplate) |
| **sonnet** *(default)* | 1–3 files, follows existing patterns, well-specified |
| **opus** | Multi-file design work, debugging unfamiliar code, novel pattern, ambiguous scope |

If unsure → sonnet.

## 6. Risks & Open Questions
- **Risk:** <what could go wrong, mitigation>
- **Open question:** <unresolved decision, who needs to weigh in>

If empty, write "None known" — empty section is suspicious.
```

**Filename convention:** `docs/feature/<feature-name>/YYYY-MM-DD-<feature-name>-plan.md` (kebab-case feature name for both the directory and the file; date is the day the plan was authored — does not need to match the PRD's date). The plan lives in the same `docs/feature/<feature-name>/` directory as the PRD.
