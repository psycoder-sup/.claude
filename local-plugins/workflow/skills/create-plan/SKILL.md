---
name: create-plan
description: This skill should be used when the user asks to "create a plan", "write a plan", "draft a plan for [feature]", "implementation plan for [feature]", "turn this PRD into a plan", "edit the plan", or wants a technical implementation plan that bridges a PRD to code. Drafts a plan directly (approach, file changes, types, test plan, tagged task list), runs a single optional critic pass via devils-advocate, batches user decisions in one AskUserQuestion.
---

# Create Plan

Bridge a PRD to executable code. The plan includes approach, file-by-file changes, types, test plan, and a tagged task list that `/execute-plan` runs against.

**You (the session running this skill) draft the plan directly — not via a subagent.** Critic is optional and runs once if invoked.

**No automatic re-critique loop.** If the user wants another pass after revisions, they ask explicitly.

## When to Use

- A PRD is finalized and the user wants the implementation plan
- The user says "create a plan", "implementation plan for X", "turn this PRD into a plan"
- The user wants to edit or update an existing plan

## Prerequisites

A plan should be based on a PRD. If no PRD exists:
1. **Ask the user** if they want to create a PRD first (suggest `/workflow:create-prd`)
2. If they want to proceed without a PRD, acknowledge the risk and continue — you will work from the user's description directly. Note any ambiguities as Open Questions in §6.

## Process Overview

```
PRD path (or feature description)
    |
    v
Phase 1: Locate PRD + read context
    |
    v
Phase 2: Explore codebase (you, in main session)
    |
    v
Phase 3: Draft plan (you, with Write)
    |
    v
Phase 4: (Optional) Critique  → batched AskUserQuestion → you revise with Edit
    |
    v
Phase 5: Confirm (approve / walk through / request edits)
```

## Detailed Workflow

### Phase 1: Locate PRD and Read Context

1. If the user provided a PRD path, use it. Otherwise search `docs/feature/**/*-prd.md` via Glob.
2. If multiple PRDs exist, ask which one via `AskUserQuestion`. Show feature directory + date prefix + feature name to help the user identify.
3. Read CLAUDE.md, the PRD, and any existing plan for the same feature (`docs/feature/<feature-name>/*-<feature-name>-plan.md`).
4. If no PRD exists, ask via `AskUserQuestion` whether to create one first or proceed with a description.

### Phase 2: Explore Codebase

Proportionate exploration — do not exhaust the codebase for a small feature. Find:
- Existing patterns the new code should follow (similar features, hooks, services, screens)
- Files the plan will touch (Glob/Grep)
- The test framework and existing test patterns
- The project's migration / type / API conventions
- Any cross-cutting concerns (auth guards, feature flags, analytics) the feature must integrate with

You do this directly — do not dispatch a subagent for exploration.

### Phase 3: Draft the Plan

Read `references/plan-template.md` for the structure.

Write the plan with `Write` to `docs/feature/<feature-name>/YYYY-MM-DD-<feature-name>-plan.md`. Use today's date for `YYYY-MM-DD` (run `date +%Y-%m-%d` via Bash if unsure). The feature name (and the directory it lives in) must match the companion PRD's feature name (the part between the date and `-prd`). The PRD's feature directory is reused — do not create a sibling directory.

**This path convention is mandatory.** Do not defer to project-specific conventions, existing plans in other locations, or `CLAUDE.md` overrides — always write to `docs/feature/<feature-name>/YYYY-MM-DD-<feature-name>-plan.md`.

Fill all 6 sections:
- §1 Approach — prose, 10-20 lines
- §2 File-by-file changes — table
- §3 Types & interfaces — verbatim code in the project's language
- §4 Test plan — bullet per test, traced to FR + task
- §5 Tasks — numbered, dependency-ordered, each tagged `[model: haiku|sonnet|opus]`
- §6 Risks & open questions

**Tagging tasks with model tier (§5):** apply this heuristic when assigning a tag:

| Tier | Use when |
|---|---|
| **haiku** | 1 file, <50 LOC, mechanical (rename, format, simple wire-up, copy boilerplate) |
| **sonnet** *(default)* | 1–3 files, follows existing patterns, well-specified |
| **opus** | Multi-file design work, debugging unfamiliar code, novel pattern, ambiguous scope |

If unsure → sonnet. The tag determines the starting model `/execute-task` uses; failures escalate one tier per retry.

**Behavioral rules during drafting:**
- Every PRD FR must map to at least one test in §4 and at least one task in §5
- Every file in §2 must appear in at least one task in §5
- §3 type code must be real (compiles against existing types) — not placeholder
- Don't include code anywhere except §3 (types) and §4 (test skeletons)
- Sequence §5 by dependency, not by layer or alphabet
- Cap task scope: if a task touches more than ~5 files or spans multiple layers, split it

### Phase 4: (Optional) Critique

After the plan is written, ask the user via `AskUserQuestion` whether to run a critic pass. Default offered choice: **skip critic** (the plan is already grounded in the PRD and codebase exploration).

If the user wants critique, launch `devils-advocate`:

**Agent prompt:**

```
Review the implementation plan at {plan-file-path}.

The plan is based on the PRD at {prd-file-path} (if applicable).

Produce your standard structured critique (What Works, Critique by category, Summary).

Tag every concern with [Category] — [Severity]: [Short Title]
  where Severity is one of: Blocker, Major, Minor, Nit.

Reference the relevant plan section by name in each concern.

Focus on: technical soundness of §1 (approach), correctness of §3 (types) against the
codebase, completeness of §4 (test plan) against the PRD's FRs, dependency ordering of
§5 (tasks), and feasibility of model tier assignments.

List the issues that must be fixed under a "Required Fixes" heading.
```

After the critique, present **all** Required Fixes to the user in **one** batched `AskUserQuestion` (multi-select). For each issue: Accept / Defer / Disagree.

Apply the user's directions with `Edit`:
- Accept → apply fix
- Defer → move to §6 Open Questions
- Disagree → leave as-is (note rationale in §6 if user provided one)

**Do NOT re-dispatch the critic.** If the user wants another pass after edits, they will ask.

### Phase 5: Confirm

Use `AskUserQuestion` to ask how to proceed:
- **Approve as-is** — mark plan as Approved, done
- **Walk through section by section** — review together (5b)
- **Request specific edits** — user describes (5c)

#### Phase 5b: Section-by-Section Review

For each of the 6 sections:
1. Present a concise summary (bullets, not raw text)
2. Ask if changes needed
3. Apply edits directly with `Edit` — no subagent
4. Flag inconsistencies you notice (e.g., a task in §5 that touches a file not listed in §2)

After all sections reviewed, mark the plan as Approved.

#### Phase 5c: User-Requested Edits

Apply edits with `Edit`. Don't auto-trigger another critic pass.

---

## Edit Existing Plan Workflow

For "edit the plan", "update the plan for X":

1. Identify the plan file (search `docs/feature/**/*-plan.md` if not specified, ask which one if multiple).
2. Apply edits directly with `Edit`.
3. Optionally offer a critic pass via `devils-advocate`. Default: don't run it unless the user asks.

## Important Rules

- **Single optional critique pass.** No automatic re-critique after revisions.
- **You draft and revise; only the critic is a subagent.** Phase 1 (locate), Phase 2 (explore), Phase 3 (draft), Phase 5 (revise) all run in your main session.
- **Tag every task in §5 with `[model: ...]`.** This is what `/execute-plan` uses to pick the implementer model. If unsure, tag `sonnet`.
- **Always use `AskUserQuestion` to present choices** — do not decide on the user's behalf.
- **Batch Phase 4 user decisions into one AskUserQuestion** — never one question per issue.
- **Use kebab-case** for both the feature directory and the plan filename: `docs/feature/<feature-name>/YYYY-MM-DD-<feature-name>-plan.md`. Use today's date.
- **Plan and PRD share the feature directory `docs/feature/<feature-name>/`** — the PRD/plan pair is identified by living in the same `<feature-name>` directory and by matching `<feature-name>` between the date prefix and the `-prd.md` / `-plan.md` suffix.

## Additional Resources

### Reference Files

- **`references/plan-template.md`** — The 6-section structure you fill in during Phase 3
