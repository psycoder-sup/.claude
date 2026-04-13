---
name: create-prd
description: This skill should be used when the user asks to "create a PRD", "write a PRD", "draft a PRD for [feature]", "make a PRD", "I need a PRD", "PRD for [feature]", "edit the PRD", "update the PRD", "revise the PRD", or wants a production-ready product requirements document for a new feature or to modify an existing one. Orchestrates the feature-planner and devils-advocate agents in a review loop to produce a high-quality PRD that scores above 0.8/1.0.
---

# Create PRD

Draft a PRD directly (clarify requirements one question at a time, then write the document), then invoke the `devils-advocate` subagent for critique. Iterate revise → critique until the PRD meets a quality threshold.

**You (the session running this skill) do the clarification and drafting directly — not via a subagent.** Only the critic is dispatched as a subagent so it reads the draft with fresh eyes.

## When to Use

- The user wants a full PRD document for a new feature
- The user has a feature idea (rough or detailed) and needs it formalized into a PRD
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
Phase 2: Draft      (you write the PRD directly with Write tool)
    |
    v
Phase 3: Review     (devils-advocate subagent critiques; you compute score)
    |
    score >= 0.8? --Yes--> Phase 4: Finalize --> Phase 5: Confirm
    |                                               |
    No                                     User chooses one:
    |                                      /       |        \
    v                                     v        v         v
Phase 3b: Consult                     5b: Walk   Approve   5c: Edits
    |                                 through              then back
    v                                 sections             to Phase 3
Phase 3c: Revise                      together
(you edit the PRD directly)
    |
    v
(back to Phase 3, max 3 cycles)
```

## Detailed Workflow

### Phase 1: Clarify Requirements

You do this directly — no subagent. Read `references/prd-drafting-guide.md` first if you haven't, then:

1. **Explore project context** (proportionate — don't exhaust the codebase for a small feature):
   - Read `CLAUDE.md` at the project root.
   - Read the project's main PRD if one exists.
   - Read the design system doc if referenced in CLAUDE.md.
   - Glob/Grep existing features for duplication or conflicts.

2. **Clarify requirements one question at a time.** Use the `AskUserQuestion` tool — one question per invocation, multiple-choice preferred. Focus on the 1-2 biggest unknowns first (user problem, scope boundaries, success metrics, constraints, edge cases).

3. **Stop asking when you have enough to draft.** If the user's original prompt was detailed, you may skip straight to Phase 2. Don't manufacture questions.

If the feature spans multiple independent subsystems, stop and help the user decompose into sub-features before drafting. See `references/prd-drafting-guide.md` § "When the Scope is Too Large".

### Phase 2: Draft the PRD

You write the PRD directly with the `Write` tool. Do NOT dispatch a subagent.

1. Read `references/prd-template.md` for the 11-section structure.
2. Read `references/prd-drafting-guide.md` for behavioral rules (no impl details, testable FRs, etc.).
3. Compose the PRD based on the user's description + Phase 1 answers + project context.
4. Save to `docs/feature/{feature-name}/{feature-name}-prd.md` (kebab-case).

If the user's project convention for PRD location differs from this default (check CLAUDE.md or existing PRDs), use the project convention.

Once the PRD file is written, proceed to Phase 3.

### Phase 3: Review and Score

Launch the `devils-advocate` agent to critique the PRD. The critic does NOT produce a score — you compute it mechanically from the critic's severity-tagged issues.

**Agent prompt structure:**

```
Review the PRD at {prd-file-path}.

Produce your standard structured critique (What Works, Critique by category, Summary).

Tag every concern with [Category] — [Section N] — [Severity]: [Short Title]
  where Section N is the PRD section number (1-11) and Severity is one of:
  Blocker, Major, Minor, Nit.

DO NOT output a numeric score. Scoring is computed from your severity tags.

List the specific issues that must be fixed to raise quality under a "Required Fixes" heading.
```

**Compute the score yourself (not via subagent):**

After the devils-advocate returns its critique, extract the severity counts per section, then run the helper script:

```bash
echo "<section> <severity>
<section> <severity>
..." | python3 ${CLAUDE_PLUGIN_ROOT}/skills/create-prd/references/compute-score.py
```

For example, if the critique has one Blocker in Section 5, one Major in Section 5, one Minor in Section 2, and one Nit in Section 11:

```bash
echo "5 blocker
5 major
2 minor
11 nit" | python3 ${CLAUDE_PLUGIN_ROOT}/skills/create-prd/references/compute-score.py
```

The script outputs `overall_score` and a `verdict`. Use `overall_score` to decide whether to proceed to Phase 4 (≥ 0.8) or loop to Phase 3b (< 0.8).

### Phase 3b: Consult User (if score < 0.8)

If the score is below 0.8, **do not send the critique directly to feature-planner**. Instead, present the critique to the user and ask for their direction.

**Use the `AskUserQuestion` tool** to present:

1. The current score
2. A concise summary of each issue under "Required Fixes" (one bullet per issue)
3. For each issue, ask the user how they'd like to address it — e.g., accept the suggestion, take a different approach, defer to a later version, or disagree and keep as-is

Wait for the user's responses before proceeding.

### Phase 3c: Revise (apply user's direction)

You revise the PRD directly with the `Edit` tool — no subagent. You already have:
- The full critique from devils-advocate (in your current context)
- The user's direction per issue from Phase 3b
- The PRD file on disk

For each issue the user accepted: apply the fix via `Edit`. For each issue the user deferred: move it to Section 10 (Open Questions) if appropriate. For each issue the user disagreed with: leave as-is (optionally note the rationale in Section 10). Update the PRD version number (e.g., 1.0 → 1.1) in the header.

Do not remove or weaken existing strong sections.

Then return to Phase 3 (review again). **Maximum 3 revision cycles** — if the score hasn't reached 0.8 after 3 revisions, finalize anyway and note the remaining concerns.

### Phase 4: Finalize

Once the score is >= 0.8 (or max cycles reached):

1. Report the final score to the user
2. Summarize key strengths and any remaining minor concerns
3. Confirm the PRD file location
4. Update the PRD status from "Draft" to "Review" if score >= 0.8
5. Proceed to Phase 5 for user confirmation

### Phase 5: User Confirmation

**Use the `AskUserQuestion` tool** to ask the user how they'd like to proceed:

- **Review section by section** — walk through the PRD together (Phase 5b)
- **Approve as-is** — mark the PRD as Approved, done
- **Request specific edits** — user describes what to change (Phase 5c)

### Phase 5b: Section-by-Section Review

Walk through each of the 11 PRD sections with the user, one at a time:

1. Present a concise summary of the current section (not the raw text — summarize the key points)
2. Ask the user if they want to change anything or move to the next section
3. If the user requests changes, apply edits directly using the Edit tool — do not re-launch the feature-planner agent for small changes
4. If changes are substantial enough to affect other sections, flag this to the user
5. After all 11 sections are reviewed, update the version number and version history, then mark the PRD as Approved

**Guidelines for this phase:**
- Be concise when presenting sections — bullet points over full quotes
- Proactively flag inconsistencies you notice (e.g., a user story that contradicts a functional requirement based on earlier decisions)
- When the user says something that contradicts the PRD, confirm the change before applying it
- Apply edits incrementally as you go — don't batch them up
- After editing, re-read the changed section to verify correctness if the user asks to see it

### Phase 5c: User-Requested Edits

Apply the user's edits directly with `Edit`. Then return to Phase 3 (review loop resets to 3 new cycles).

---

## Edit Existing PRD Workflow

For "edit the PRD", "update the PRD for X", "revise the PRD":

1. **Identify the PRD file** — if not specified, look in the project's PRD directory. If multiple exist, use `AskUserQuestion` to ask which one.
2. **Apply edits directly** with `Edit` based on the user's description.
3. **Review loop** (Phase 3) with same scoring rules
4. **User confirmation** (Phase 5)

## Important Rules

- **You draft and revise; only the critic is a subagent.** The clarification, drafting (Phase 2), and revisions (Phases 3c, 5c) all run in your main session — call `Write`/`Edit` directly. Dispatch `devils-advocate` via the `Task` tool only for Phase 3 critique.
- **Always use `AskUserQuestion` tool to present clarifying questions** — one at a time, multiple-choice preferred. Do not answer on the user's behalf.
- **Never auto-revise** — when the devil's advocate raises issues, always consult the user first (Phase 3b) before revising.
- **Show progress** — after each review cycle, tell the user the current score and what's being revised.
- **Cap revisions at 3** — avoid infinite loops.
- **Use kebab-case** for the PRD filename: `docs/feature/{feature-name}/{feature-name}-prd.md`.

## Additional Resources

### Reference Files

- **`references/prd-template.md`** — The 11-section PRD structure you fill in during Phase 2.
- **`references/prd-drafting-guide.md`** — Behavioral rules for clarification dialog and drafting (scope, testable FRs, no impl details, etc.).
- **`references/scoring-rubric.md`** — Per-section weights and criteria used by `compute-score.py`.
- **`references/compute-score.py`** — Helper script you run to compute the weighted score from the critic's severity-tagged issues.
