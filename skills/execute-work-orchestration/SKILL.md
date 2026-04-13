---
name: execute-work-orchestration
description: >-
  This skill should be used when the user asks to "execute the spec",
  "implement the spec", "run the spec", "build from spec",
  "execute work orchestration", or wants to sequentially implement all
  phases from a SPEC document. Parses the spec, extracts implementation
  phases, and invokes /execute-task for each phase to guarantee the
  3-step implement-review-polish flow.
allowed-tools: [Read, Glob, Grep, Skill, Task, AskUserQuestion, TaskCreate, TaskUpdate]
user-invocable: true
argument-hint: "<spec-file-path>"
---

# Execute Work Orchestration

Parse a SPEC document, extract implementation phases, and execute them sequentially by invoking `/execute-task` for each phase. Every phase goes through the mandatory 3-step flow (implement -> review spec compliance -> polish) enforced by the `/execute-task` skill.

## Arguments

```
$ARGUMENTS
```

Parse the first argument as the path to the SPEC document.

If no argument is provided, search for spec files using `Glob("docs/**/*-spec.md")` and ask the user to pick one via `AskUserQuestion`.

## Process Overview

```
Spec File Path
    |
    v
Phase 1: Parse Spec
    - Read spec, locate PRD, extract implementation phases
    - Present task list for user approval
    |
    v
Phase 2: Execute Phases (sequential)
    - For each phase: invoke /execute-task
    - Progress report between tasks
    |
    v
Phase 3: Final Verification
    - Run full test suite
    - Summary report
```

## Execution

### Phase 1: Parse Spec

1. **Read the spec file** at the provided path.

2. **Locate the companion PRD.** Check the spec's frontmatter or header for a PRD reference. If not found, search the same directory for `*-prd.md`. If no PRD exists, set PRD path to "none".

3. **Extract implementation phases.** Search for the heading containing "Implementation Phases" (do not hardcode a section number — specs vary). Extract each phase as a block containing:
   - Phase title
   - Goal / description
   - Scope (files, modules)
   - Deliverables
   - Acceptance criteria / "done when"

   If phases reference other spec sections (e.g., "See Section 3: Database Schema"), include that referenced content in the phase text so the implementer subagent has full context without reading the spec.

4. **Present the task list** to the user via `AskUserQuestion`:
   - Show: phase number, title, and one-line scope summary for each phase
   - Ask: "Proceed with executing all N phases?" with options to proceed, skip specific phases, or cancel

5. **Create task tracking.** After user approval, use `TaskCreate` to create one task per approved phase. Each task should have:
   - **subject:** "Phase N: {phase title}"
   - **description:** One-line scope summary of the phase

### Phase 2: Execute Phases

For each approved phase, in order:

1. **Mark task in_progress** via `TaskUpdate` — set the phase's task status to `in_progress`.

2. **Report progress:** "Starting phase N/M: {phase title}"

3. **Invoke `/execute-task`** via `Skill` tool, passing pipe-delimited arguments:

   ```
   /execute-task {phase_title} | {phase_full_text} | {spec_path} | {prd_path}
   ```

4. **Handle the result and update task:**
   - **COMPLETE** — mark task `completed` via `TaskUpdate`. Move to next phase.
   - **BLOCKED** — keep task `in_progress`. Halt execution. Present the blocker to the user. Ask whether to skip this phase and continue, or stop entirely.
   - **HALTED_AT_RETRY_LIMIT** — present remaining issues. Ask whether to accept (mark `completed`) and continue, or stop (keep `in_progress`).

5. **Between phases:** Report cumulative progress: "Completed N/M phases. Next: {title}"

### Phase 3: Final Verification

After all phases complete:

1. **Run full test suite** via the `test-runner-slim` agent (Task tool). This catches cross-phase regressions.

2. **Summary report:**

```
## Execution Summary

**Spec:** {spec_path}
**Phases completed:** N/M

| # | Phase | Result | Retries |
|---|-------|--------|---------|
| 1 | {title} | COMPLETE | 0/3 |
| 2 | {title} | COMPLETE | 1/3 |
| ... | ... | ... | ... |

**Final test suite:** X passing, Y failing

**Concerns:** [any DONE_WITH_CONCERNS notes from phases]
**Remaining issues:** [any phases that hit retry limit]
```

## Important Rules

- **Always invoke `/execute-task` for each phase.** Never implement directly in this skill — that would bypass the 3-step enforcement.
- **Sequential execution only.** Do not run phases in parallel — later phases may depend on earlier ones.
- **User approval before execution.** Always present the extracted task list and get confirmation in Phase 1.
- **Enrich phase text.** If a phase references other spec sections, inline that content so the subagent has complete context.
- **Halt on BLOCKED.** Do not skip blocked phases automatically — always consult the user.
