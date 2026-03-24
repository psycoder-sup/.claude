---
name: create-prd
description: This skill should be used when the user asks to "create a PRD", "write a PRD", "draft a PRD for [feature]", "make a PRD", "I need a PRD", "PRD for [feature]", "edit the PRD", "update the PRD", "revise the PRD", or wants a production-ready product requirements document for a new feature or to modify an existing one. Orchestrates the feature-planner and devils-advocate agents in a review loop to produce a high-quality PRD that scores above 0.8/1.0.
---

# Create PRD

Orchestrate the `feature-planner` and `devils-advocate` agents to produce a polished, critically-reviewed PRD for a new feature. The process uses an iterative refinement loop: plan, draft, critique, revise — until the PRD meets a quality threshold.

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
Phase 1: Clarify    (feature-planner asks questions, fills gaps)
    |
    v
Phase 2: Draft      (feature-planner writes the PRD)
    |
    v
Phase 3: Review     (devils-advocate scores & critiques)
    |
    score >= 0.8? --Yes--> Phase 4: Finalize --> Phase 5: Confirm
    |
    No
    |
    v
Phase 3b: Revise    (feature-planner addresses critique)
    |
    v
(back to Phase 3, max 3 cycles)
```

## Detailed Workflow

### Phase 1: Clarify Requirements

Launch the `feature-planner` agent with the user's feature description. The agent's task is strictly to **clarify and refine** — not to write the PRD yet.

**Agent prompt structure:**

```
The user wants to create a PRD for the following feature:

{user's feature description}

Your task in this phase is to clarify requirements ONLY. Do NOT write a PRD yet.

1. Read CLAUDE.md and any referenced product/design docs for project context
2. Explore relevant parts of the codebase to understand existing patterns
3. Identify what's missing or ambiguous in the user's description
4. Return 3-5 focused clarifying questions to fill gaps in:
   - User problem and motivation
   - Scope boundaries (what's in vs out for v1)
   - Key user flows and edge cases
   - Success metrics
   - Business constraints or feature dependencies

Be concise. Return only the questions — do not answer them yourself.
```

After the feature-planner returns questions, **use the `AskUserQuestion` tool** to present them to the user and collect answers. If the user's original prompt is already detailed enough, skip directly to Phase 2.

### Phase 2: Draft the PRD

Launch the `feature-planner` agent again with the full context.

**Agent prompt structure:**

```
Create a full PRD for the following feature. Save it to the project's PRD directory (e.g., docs/prd/{feature-name}-prd.md).

Feature description:
{user's feature description}

Clarified requirements:
{answers from Phase 1}

Follow your standard PRD template. Fill all 11 sections. Be specific and testable in functional requirements. Do not include technical implementation details.
```

Once the PRD file is written, proceed to Phase 3.

### Phase 3: Review and Score

Launch the `devils-advocate` agent to critique the PRD.

**Agent prompt structure:**

```
Review the PRD at {prd-file-path}.

Produce your standard structured critique (What Works, Critique by category, Summary).

After your critique, assign an overall quality score between 0.0 and 1.0 using these guidelines:

- 0.9-1.0: Exceptional — ready to build, no blockers, minor nits only
- 0.8-0.89: Strong — ready to build with minor refinements
- 0.7-0.79: Decent — has Major issues that should be addressed before building
- 0.6-0.69: Weak — has Blockers or multiple Major issues
- Below 0.6: Needs significant rework

Format your score as:

**Score: X.X/1.0**

List the specific issues that must be fixed to raise the score above 0.8 under a "Required Fixes" heading.
```

### Phase 3b: Revise (if score < 0.8)

If the score is below 0.8, launch the `feature-planner` agent to revise.

**Agent prompt structure:**

```
Revise the PRD at {prd-file-path}.

The devils-advocate review scored it {score}/1.0. Here is the critique:

{full critique from devils-advocate}

Address all issues listed under "Required Fixes". Do not remove or weaken existing strong sections. Update the PRD version number (e.g., 1.0 -> 1.1).
```

Then return to Phase 3 (review again). **Maximum 3 revision cycles** — if the score hasn't reached 0.8 after 3 revisions, finalize anyway and note the remaining concerns.

### Phase 4: Finalize

Once the score is >= 0.8 (or max cycles reached):

1. Report the final score to the user
2. Summarize key strengths and any remaining minor concerns
3. Confirm the PRD file location
4. Update the PRD status from "Draft" to "Review" if score >= 0.8
5. Proceed to Phase 5 for user confirmation

### Phase 5: User Confirmation

**Use the `AskUserQuestion` tool** to ask the user to review and confirm or request edits.

- If the user **approves**, the PRD is done.
- If the user **requests edits**, proceed to Phase 5b.

### Phase 5b: User-Requested Edits

Launch the `feature-planner` agent to apply edits, then return to Phase 3 (review loop resets to 3 new cycles).

---

## Edit Existing PRD Workflow

For "edit the PRD", "update the PRD for X", "revise the PRD":

1. **Identify the PRD file** — if not specified, look in the project's PRD directory. If multiple exist, use `AskUserQuestion` to ask which one.
2. **Apply edits** via feature-planner agent
3. **Review loop** (Phase 3) with same scoring rules
4. **User confirmation** (Phase 5)

## Important Rules

- **Always use `AskUserQuestion` tool to present clarifying questions** — do not answer on the user's behalf
- **Show progress** — after each review cycle, tell the user the current score and what's being revised
- **Preserve context** — pass the full critique text to the feature-planner during revision
- **Cap revisions at 3** — avoid infinite loops
- **Use kebab-case** for the PRD filename: `docs/feature/{feature-name}/{feature-name}-prd.md`

## Additional Resources

### Reference Files

- **`references/scoring-rubric.md`** — Detailed scoring criteria for each PRD section
