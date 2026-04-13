---
name: create-spec
description: This skill should be used when the user asks to "create a spec", "write a spec", "draft a spec for [feature]", "make a spec", "I need a spec", "spec for [feature]", "turn this PRD into a spec", "edit the spec", "update the spec", "revise the spec", or wants a production-ready technical specification for a feature. Orchestrates the cto and spec-reviewer agents in a review loop to produce a high-quality SPEC that scores above 0.8/1.0.
---

# Create SPEC

Produce a polished, critically-reviewed technical specification. The initial draft is written by the `cto` subagent (heavy codebase exploration must stay isolated). The critique is done by the `spec-reviewer` subagent (fresh eyes). **Revisions you apply directly** — you have the critique and the user's direction in context, and re-dispatching the cto for small edits loses that context without benefit.

The loop: draft (cto) → critique (spec-reviewer) → consult user → revise (you) → re-critique → …

## When to Use

- The user wants a full SPEC document for a feature
- A PRD has been finalized and needs to be translated into a technical spec
- The user says "create a spec", "write a spec", "spec for X", "turn this PRD into a spec"
- The user wants to edit or update an existing SPEC (see Edit Existing SPEC workflow below)

## Prerequisites

A SPEC should be based on a PRD. If no PRD exists:
1. **Ask the user** if they want to create a PRD first (suggest `/workflow:create-prd`)
2. If they want to proceed without a PRD, acknowledge the risk and continue — the cto agent will work from the user's description directly

## Process Overview

```
User Prompt (PRD path or feature description)
    |
    v
Phase 1: Locate PRD   (find or confirm the PRD to spec against)
    |
    v
Phase 2: Draft         (cto agent explores codebase + writes the SPEC)
    |
    v
Phase 3: Review        (spec-reviewer scores & critiques)
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
    |
    v
(back to Phase 3, max 3 cycles)
```

## Detailed Workflow

### Phase 1: Locate PRD

Identify the PRD that this spec will be based on:

1. If the user provided a PRD path, use it directly
2. If not, search `docs/` for PRD files using Glob (`docs/**/*-prd.md`)
3. If multiple PRDs exist, **use `AskUserQuestion`** to ask which one
4. If no PRD exists, **use `AskUserQuestion`** to ask if they want to create one first or proceed with a feature description

### Phase 2: Draft the SPEC

Launch the `cto` agent with the PRD context.

**Agent prompt structure:**

```
Create a full technical specification for the feature described in the PRD at {prd-file-path}.

Read the PRD thoroughly. Then deeply explore the codebase to understand existing architecture, patterns, and conventions. Design a technical approach that fits naturally into the existing codebase.

Save the SPEC to: docs/feature/{feature-name}/{feature-name}-spec.md (alongside the PRD if one exists).

Follow your standard SPEC template. Fill all 15 sections. Every recommendation must reference real file paths and real patterns from the codebase. No code snippets — describe everything in prose, tables, and lists.
```

If no PRD exists and the user provided a feature description instead:

```
Create a full technical specification for the following feature:

{user's feature description}

There is no formal PRD for this feature. Use the feature description above as your requirements source. Note any ambiguities as open technical questions.

Read the codebase deeply to understand existing architecture, patterns, and conventions. Design a technical approach that fits naturally into the existing codebase.

Save the SPEC to: docs/feature/{feature-name}/{feature-name}-spec.md

Follow your standard SPEC template. Fill all 15 sections. Every recommendation must reference real file paths and real patterns from the codebase. No code snippets — describe everything in prose, tables, and lists.
```

Once the SPEC file is written, proceed to Phase 3.

### Phase 3: Review and Score

Launch the `spec-reviewer` agent to critique the SPEC. The critic does NOT produce a score — you compute it mechanically from the critic's severity-tagged issues.

**Agent prompt structure:**

```
Review the technical specification at {spec-file-path}.

The SPEC is based on the PRD at {prd-file-path} (if applicable).

Produce your standard structured critique (What Works, Critique by category, PRD Coverage Check, Summary).

Tag every concern with [Category] — [Section N] — [Severity]: [Short Title]
  where Section N is the SPEC section number (1-15, or 13.5 for Test Skeletons)
  and Severity is one of: Blocker, Major, Minor, Nit.

DO NOT output a numeric score. Scoring is computed from your severity tags.

List the specific issues that must be fixed to raise quality under a "Required Fixes" heading.
```

**Compute the score yourself (not via subagent):**

After the spec-reviewer returns its critique, extract the severity counts per section, then run the helper script:

```bash
echo "<section> <severity>
<section> <severity>
..." | python3 ${CLAUDE_PLUGIN_ROOT}/skills/create-spec/references/compute-score.py
```

For example, if the critique has one Blocker in Section 2, one Major in Section 9, one Major in Section 13.5, and one Minor in Section 4:

```bash
echo "2 blocker
9 major
13.5 major
4 minor" | python3 ${CLAUDE_PLUGIN_ROOT}/skills/create-spec/references/compute-score.py
```

The script outputs `overall_score` and a `verdict`. Use `overall_score` to decide whether to proceed to Phase 4 (≥ 0.8) or loop to Phase 3b (< 0.8).

### Phase 3b: Consult User (if score < 0.8)

If the score is below 0.8, **do not send the critique directly to cto**. Instead, present the critique to the user and ask for their direction.

**Use the `AskUserQuestion` tool** to present:

1. The current score
2. A concise summary of each issue under "Required Fixes" (one bullet per issue)
3. For each issue, ask the user how they'd like to address it — e.g., accept the suggestion, take a different approach, defer as tech debt, or disagree and keep as-is

Wait for the user's responses before proceeding.

### Phase 3c: Revise (apply user's direction)

You revise the SPEC directly with the `Edit` tool — no subagent. You already have the full critique from spec-reviewer and the user's direction per issue from Phase 3b, plus the SPEC file on disk.

For each issue the user accepted: apply the fix via `Edit`. For each issue the user deferred: move it to Section 15 (Open Technical Questions). For each issue the user disagreed with: leave as-is (optionally note the rationale in Section 15). Update the SPEC version number (e.g., 1.0 → 1.1) in the header.

**Exception — re-dispatch `cto` when the revision requires new codebase exploration you don't have in context.** For example, if the user accepts an issue that says "this schema pattern doesn't match the existing billing module" and you haven't read the billing module, dispatch `cto` for that revision with a scoped prompt. For targeted textual edits you can make in-context, do not re-dispatch.

Do not remove or weaken existing strong sections.

Then return to Phase 3 (review again). **Maximum 3 revision cycles** — if the score hasn't reached 0.8 after 3 revisions, finalize anyway and note the remaining concerns.

### Phase 4: Finalize

Once the score is >= 0.8 (or max cycles reached):

1. Report the final score to the user
2. Summarize key strengths and any remaining technical concerns
3. Confirm the SPEC file location
4. Update the SPEC status from "Draft" to "Review" if score >= 0.8
5. Proceed to Phase 5 for user confirmation

### Phase 5: User Confirmation

**Use the `AskUserQuestion` tool** to ask the user how they'd like to proceed:

- **Review section by section** — walk through the SPEC together (Phase 5b)
- **Approve as-is** — mark the SPEC as Approved, done
- **Request specific edits** — user describes what to change (Phase 5c)

### Phase 5b: Section-by-Section Review

Walk through each of the 15 SPEC sections with the user, one at a time:

1. Present a concise summary of the current section (not the raw text — summarize the key points)
2. Ask the user if they want to change anything or move to the next section
3. If the user requests changes, apply edits directly using the Edit tool — do not re-launch the cto agent for small changes
4. If changes are substantial enough to affect other sections (e.g., schema change affects API layer), flag this to the user
5. After all 15 sections are reviewed, update the version number and version history, then mark the SPEC as Approved

**Guidelines for this phase:**
- Be concise when presenting sections — bullet points over full quotes
- Proactively flag inconsistencies you notice (e.g., a type definition that doesn't match the schema, a test strategy that misses a PRD requirement)
- When the user says something that contradicts the SPEC, confirm the change before applying it
- Apply edits incrementally as you go — don't batch them up
- After editing, re-read the changed section to verify correctness if the user asks to see it

### Phase 5c: User-Requested Edits

Apply the user's edits directly with `Edit`. Only re-dispatch `cto` if the edits require new codebase exploration. Then return to Phase 3 (review loop resets to 3 new cycles).

---

## Edit Existing SPEC Workflow

For "edit the spec", "update the spec for X", "revise the spec":

1. **Identify the SPEC file** — if not specified, look in the project's docs directory. If multiple exist, use `AskUserQuestion` to ask which one.
2. **Apply edits directly** with `Edit` based on the user's description. Re-dispatch `cto` only when the revision needs codebase exploration you don't have.
3. **Review loop** (Phase 3) with same scoring rules
4. **User confirmation** (Phase 5)

## Important Rules

- **`cto` drafts; you revise.** Phase 2 (initial draft) uses the `cto` subagent because codebase exploration is heavy. Phase 3c (revise) is done by you directly with `Edit` — the critique and user direction are already in context. Re-dispatch `cto` only when revisions need new codebase exploration you don't have.
- **`spec-reviewer` critiques only; you score.** The critic tags severity per section; you run `references/compute-score.py` to get the weighted score.
- **Always use `AskUserQuestion` tool to present choices** — do not decide on the user's behalf.
- **Never auto-revise** — when the spec-reviewer raises issues, always consult the user first (Phase 3b) before revising.
- **Show progress** — after each review cycle, tell the user the current score and what's being revised.
- **Cap revisions at 3** — avoid infinite loops.
- **Use kebab-case** for the SPEC filename: `docs/feature/{feature-name}/{feature-name}-spec.md`.
- **SPEC lives alongside PRD** — save in the same feature directory when a PRD exists.

## Additional Resources

### Reference Files

- **`references/scoring-rubric.md`** — Per-section weights and criteria used by `compute-score.py`.
- **`references/compute-score.py`** — Helper script you run to compute the weighted score from the critic's severity-tagged issues.
