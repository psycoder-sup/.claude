---
name: create-spec
description: This skill should be used when the user asks to "create a spec", "write a spec", "draft a spec for [feature]", "make a spec", "I need a spec", "spec for [feature]", "turn this PRD into a spec", "edit the spec", "update the spec", "revise the spec", or wants a production-ready technical specification for a feature. Orchestrates the cto and spec-reviewer agents in a review loop to produce a high-quality SPEC that scores above 0.8/1.0.
---

# Create SPEC

Orchestrate the `cto` and `spec-reviewer` agents to produce a polished, critically-reviewed technical specification for a feature. The process uses an iterative refinement loop: explore, draft, critique, revise — until the SPEC meets a quality threshold.

## When to Use

- The user wants a full SPEC document for a feature
- A PRD has been finalized and needs to be translated into a technical spec
- The user says "create a spec", "write a spec", "spec for X", "turn this PRD into a spec"
- The user wants to edit or update an existing SPEC (see Edit Existing SPEC workflow below)

## Prerequisites

A SPEC should be based on a PRD. If no PRD exists:
1. **Ask the user** if they want to create a PRD first (suggest `/create-prd`)
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

Launch the `spec-reviewer` agent to critique the SPEC.

**Agent prompt structure:**

```
Review the technical specification at {spec-file-path}.

The SPEC is based on the PRD at {prd-file-path} (if applicable).

Produce your standard structured critique (What Works, Critique by category, PRD Coverage Check, Summary).

After your critique, assign an overall quality score between 0.0 and 1.0 using the scoring rubric below:

- 0.9-1.0: Exceptional — technically sound, ready to implement, no blockers
- 0.8-0.89: Strong — ready to implement with minor refinements
- 0.7-0.79: Decent — has Major issues that should be addressed before implementing
- 0.6-0.69: Weak — has Blockers or multiple Major issues
- Below 0.6: Needs significant rework

Use the detailed per-section scoring criteria from the scoring rubric (reference: references/scoring-rubric.md) to calculate a weighted score.

Format your score as:

**Score: X.X/1.0**

List the specific issues that must be fixed to raise the score above 0.8 under a "Required Fixes" heading.
```

### Phase 3b: Consult User (if score < 0.8)

If the score is below 0.8, **do not send the critique directly to cto**. Instead, present the critique to the user and ask for their direction.

**Use the `AskUserQuestion` tool** to present:

1. The current score
2. A concise summary of each issue under "Required Fixes" (one bullet per issue)
3. For each issue, ask the user how they'd like to address it — e.g., accept the suggestion, take a different approach, defer as tech debt, or disagree and keep as-is

Wait for the user's responses before proceeding.

### Phase 3c: Revise (apply user's direction)

Launch the `cto` agent to revise based on the user's decisions.

**Agent prompt structure:**

```
Revise the SPEC at {spec-file-path}.

The spec-reviewer scored it {score}/1.0. Here is the critique:

{full critique from spec-reviewer}

The user has reviewed the critique and provided the following direction:

{user's responses from Phase 3b}

Apply the user's decisions to the SPEC. Where the user accepted a suggestion, address it. Where the user disagreed or deferred, leave that section as-is or move it to Open Technical Questions as appropriate. Do not remove or weaken existing strong sections. Update the SPEC version number (e.g., 1.0 -> 1.1).
```

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

Launch the `cto` agent to apply edits, then return to Phase 3 (review loop resets to 3 new cycles).

---

## Edit Existing SPEC Workflow

For "edit the spec", "update the spec for X", "revise the spec":

1. **Identify the SPEC file** — if not specified, look in the project's docs directory. If multiple exist, use `AskUserQuestion` to ask which one.
2. **Apply edits** via cto agent
3. **Review loop** (Phase 3) with same scoring rules
4. **User confirmation** (Phase 5)

## Important Rules

- **Always use `AskUserQuestion` tool to present choices** — do not decide on the user's behalf
- **Never auto-revise** — when the spec-reviewer raises issues, always consult the user first (Phase 3b) before having cto revise
- **Show progress** — after each review cycle, tell the user the current score and what's being revised
- **Preserve context** — pass both the full critique and the user's direction to the cto agent during revision
- **Cap revisions at 3** — avoid infinite loops
- **Use kebab-case** for the SPEC filename: `docs/feature/{feature-name}/{feature-name}-spec.md`
- **SPEC lives alongside PRD** — save in the same feature directory when a PRD exists

## Additional Resources

### Reference Files

- **`references/scoring-rubric.md`** — Detailed scoring criteria for each SPEC section
