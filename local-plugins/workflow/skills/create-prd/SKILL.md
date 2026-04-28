---
name: create-prd
description: This skill should be used when the user asks to "create a PRD", "write a PRD", "draft a PRD for [feature]", "make a PRD", "I need a PRD", "PRD for [feature]", "edit the PRD", "update the PRD", "revise the PRD", or wants a product requirements document for a new feature or to modify an existing one. Drafts a PRD directly, runs a single critic pass via the devils-advocate subagent, then lets the user direct revisions in one batched interaction.
---

# Create PRD

Draft a PRD directly (clarify requirements one question at a time, then write the document), run **one** critique pass via the `devils-advocate` subagent, present all issues to the user in **one** batched AskUserQuestion, apply the user's directions, done.

**No automatic re-critique loop.** The critic runs once. If the user wants another pass after revisions, they ask explicitly.

**You (the session running this skill) do the clarification, drafting, and revisions directly.** Only the critic is dispatched as a subagent so it reads the draft with fresh eyes.

## When to Use

- The user wants a PRD document for a new feature
- The user has a feature idea (rough or detailed) and needs it formalized
- The user says "create a PRD", "write a PRD", "PRD for X"
- The user wants to edit or update an existing PRD (see Edit Existing PRD workflow below)

## Process Overview

```
User Prompt
    |
    v
Phase 1: Clarify    (you ask one question at a time until you can draft)
    |
    v
Phase 2: Draft      (you write the PRD directly with Write)
    |
    v
Phase 3: Critique   (devils-advocate subagent, single pass)
    |
    v
Phase 4: Decide     (one batched AskUserQuestion — user picks accept / defer / disagree per issue)
    |
    v
Phase 5: Revise     (you apply user's directions with Edit; no re-critique)
    |
    v
Phase 6: Confirm    (approve / walk through / request edits)
```

## Detailed Workflow

### Phase 1: Clarify Requirements

Read `references/prd-drafting-guide.md` first if you haven't, then:

1. **Explore project context** (proportionate — don't exhaust the codebase for a small feature):
   - Read `CLAUDE.md` at the project root
   - Read the project's main PRD if one exists
   - Read the design system doc if referenced in CLAUDE.md
   - Glob/Grep existing features for duplication or conflicts

2. **Clarify requirements one question at a time.** Use `AskUserQuestion` — one question per invocation, multiple-choice preferred. Focus on the 1-2 biggest unknowns first (user problem, scope boundaries, success metrics, constraints, edge cases).

3. **Stop asking when you have enough to draft.** If the user's original prompt was detailed, skip straight to Phase 2. Don't manufacture questions.

If the feature spans multiple independent subsystems, stop and help the user decompose into sub-features before drafting. See `references/prd-drafting-guide.md` § "When the Scope is Too Large".

### Phase 2: Draft the PRD

Write the PRD directly with `Write`. Do NOT dispatch a subagent.

1. Read `references/prd-template.md` for the section structure.
2. Read `references/prd-drafting-guide.md` for behavioral rules (no impl details, testable FRs, etc.).
3. Compose the PRD based on the user's description + Phase 1 answers + project context.
4. Save to `docs/feature/YYYY-MM-DD-<feature-name>-prd.md` (kebab-case feature name; use today's date for `YYYY-MM-DD` — run `date +%Y-%m-%d` via Bash if unsure).

If the user's project convention for PRD location differs from this default (check CLAUDE.md or existing PRDs), use the project convention.

### Phase 3: Critique (Single Pass)

Launch the `devils-advocate` agent.

**Agent prompt:**

```
Review the PRD at {prd-file-path}.

Produce your standard structured critique (What Works, Critique by category, Summary).

Tag every concern with [Category] — [Severity]: [Short Title]
  where Severity is one of: Blocker, Major, Minor, Nit.

Reference the relevant PRD section by name in each concern (don't tag by section number).

List the issues that must be fixed under a "Required Fixes" heading.
```

### Phase 4: Decide (One Batched AskUserQuestion)

Present the critique to the user in **one** AskUserQuestion call, using a multi-select question per issue (or a single multi-select if the issues are simple).

Format the AskUserQuestion so the user can mark each Required Fix as one of:
- **Accept** — apply the suggested fix
- **Defer** — move to Open Questions in the PRD for later
- **Disagree** — leave as-is, optionally noting rationale

Do not ask a separate question per issue — batch them.

If there are no Blocker or Major issues, skip Phase 4 entirely and proceed to Phase 5 with a brief note that minor/nit issues are being left as-is.

### Phase 5: Revise

Apply the user's directions with `Edit`:
- For each Accept: apply the fix
- For each Defer: move to Open Questions section
- For each Disagree: leave as-is (note rationale in Open Questions if user provided one)

Update the PRD version (e.g., 1.0 → 1.1).

**Do NOT re-dispatch the critic.** If the user wants another critique pass after seeing revisions, they will ask.

### Phase 6: Confirm

**Use `AskUserQuestion`** to ask how to proceed:

- **Approve as-is** — mark the PRD as Approved, done
- **Walk through section by section** — review together (Phase 6b)
- **Request specific edits** — user describes what to change (Phase 6c)

### Phase 6b: Section-by-Section Review

Walk through each PRD section with the user. For each:

1. Present a concise summary (bullet points, not raw text)
2. Ask if they want changes or to move on
3. Apply edits directly with `Edit` — do not re-launch any subagent
4. Flag inconsistencies you notice between sections

After all sections reviewed, update the version + version history, mark as Approved.

### Phase 6c: User-Requested Edits

Apply the user's edits directly with `Edit`. If the user wants another critic pass after the edits, they will ask — do not auto-trigger.

---

## Edit Existing PRD Workflow

For "edit the PRD", "update the PRD for X", "revise the PRD":

1. **Identify the PRD file** — if not specified, look in the project's PRD directory. If multiple exist, use `AskUserQuestion` to ask which one.
2. **Apply edits directly** with `Edit` based on the user's description.
3. **Optionally** offer to run a critique pass via `devils-advocate` once edits are done. Default: don't run it unless the user asks.

## Important Rules

- **Single critique pass only.** No automatic re-critique after revisions.
- **You draft and revise; only the critic is a subagent.** Clarification (Phase 1), drafting (Phase 2), revisions (Phases 5, 6b, 6c) all run in your main session.
- **Always use `AskUserQuestion` to present choices** — do not decide on the user's behalf.
- **Batch Phase 4 into one AskUserQuestion call** — do not ask per-issue.
- **Show progress** — after the critique, briefly note how many Blocker/Major issues were found before opening the AskUserQuestion.
- **Use kebab-case** for the PRD filename: `docs/feature/YYYY-MM-DD-<feature-name>-prd.md`.

## Additional Resources

### Reference Files

- **`references/prd-template.md`** — The section structure you fill in during Phase 2.
- **`references/prd-drafting-guide.md`** — Behavioral rules for clarification dialog and drafting.
