---
name: execute-plan
description: >-
  This skill should be used when the user asks to "execute the plan",
  "implement the plan", "run the plan", "build from plan", or wants to
  sequentially implement all tasks from a plan document. Parses plan §4,
  invokes /execute-task for each task in dependency order, runs stage-end
  test+validation, then polish (1× or 2× per change-size heuristic).
allowed-tools: [Read, Glob, Grep, Skill, Task, AskUserQuestion, TaskCreate, TaskUpdate, Bash(git:*)]
user-invocable: true
argument-hint: "<plan-file-path>"
---

# Execute Plan

Parse a plan document, execute its §4 tasks sequentially via `/execute-task`, run stage-end test+validation, then polish.

## Arguments

```
$ARGUMENTS
```

Parse the first argument as the path to the plan document.

If no argument is provided, search for plan files using `Glob("docs/feature/**/*-plan.md")` and ask the user to pick one via `AskUserQuestion`.

## Process Overview

```
Plan File Path
    |
    v
Phase 1: Parse Plan
    - Read plan, locate PRD, extract tasks from §4 (each task carries its own inline Tests list)
    - Capture starting git ref for end-of-run diff
    - Present task list for user approval
    |
    v
Phase 2: Execute Tasks (sequential, in dependency order)
    - For each task: invoke /execute-task with task title, task text, plan path, PRD path
    - Progress report between tasks
    |
    v
Phase 3: Stage-end Test + Validate
    - Dispatch general-purpose subagent with test-and-validate-prompt.md scoped to whole-plan
    |
    v
Phase 4: Polish (1× or 2× per heuristic)
    - git diff --shortstat against starting ref
    - LOC>300 OR files>8 OR phases>4 → polish 2×, else polish 1×
    |
    v
Phase 5: Summary report
```

## Execution

### Phase 1: Parse Plan

1. **Read the plan file** at the provided path. Hold the full content in orchestrator memory — you'll reuse it in Phase 3 for the stage-end validator. `/execute-task` will read it again per-task (cheap; cache hits).

2. **Locate the companion PRD.** Check the plan's `**Based on:**` header. If absent, derive `<feature-name>` from the plan filename (strip the `YYYY-MM-DD-` prefix and `-plan.md` suffix) and look in the plan's own directory first via `Glob("docs/feature/<feature-name>/*-<feature-name>-prd.md")`; fall back to `Glob("docs/feature/**/*-<feature-name>-prd.md")` if not found there. If multiple matches (multiple PRD versions), pick the most recent by date prefix or ask the user. If no PRD exists, set PRD path to `"none"`. Read the PRD if it exists.

3. **Capture starting git ref.** Run `git rev-parse HEAD` and save as `START_REF`. This is used for the post-run diff in Phase 4 and for whole-plan regression detection in Phase 3.

4. **Extract sections** from the plan in memory:
   - **§1 Approach** → `INLINE_PLAN_APPROACH`
   - **§3 Types & Interfaces** → `INLINE_PLAN_TYPES`
   - **§4 Tasks** → list of task entries (capture the full block per task — each entry includes the **Tests:** list)
   - **§4 Tasks (full)** → `INLINE_PLAN_TASKS_FULL` (the entire §4 verbatim — used by the stage-end validator so it can trace every FR to a test)

   From the PRD (if present):
   - **§4 Functional Requirements** → `INLINE_PRD_FRS`

5. **Extract tasks from §4.** Each task is a numbered entry with:
   - Title (the line after the number)
   - Model tag `[model: haiku|sonnet|opus]` — default `sonnet` if missing
   - Files (line under "Files:")
   - Depends on (line under "Depends on:")
   - Done when (line under "Done when:")
   - Tests (bullets under "Tests:" — each bullet tagged with its FR)

   Capture each task's full §4 entry verbatim (including the **Tests:** list) — this becomes `TASK_TEXT` passed to `/execute-task`.

6. **Validate dependency DAG.** Tasks must reference only earlier task numbers in "Depends on:". If a cycle or forward reference exists, halt and report.

7. **Present the task list** to the user via `AskUserQuestion`:
   - Show: task number, title, model tag, one-line scope summary
   - Ask: "Proceed with executing all N tasks?" Options: proceed / skip specific tasks / cancel

8. **Create task tracking.** After approval, use `TaskCreate` to create one task per approved plan task. Each:
   - **subject:** "Task N: {task title}"
   - **description:** one-line scope summary

### Phase 2: Execute Tasks

For each approved task, in dependency order:

1. **Mark task in_progress** via `TaskUpdate`.

2. **Report progress:** `"Starting task N/M: {task title} [model: <tag>]"`

3. **Invoke `/workflow:execute-task`** via `Skill` tool with pipe-delimited arguments:

   ```
   /execute-task {task_title} | {task_full_text} | {plan_path} | {prd_path}
   ```

   `{task_full_text}` includes the `[model: ...]` tag — `/execute-task` parses it.

4. **Handle the result:**
   - **COMPLETE** — mark task `completed`. Move to next.
   - **BLOCKED** — keep `in_progress`. Halt execution. Present blocker to user via `AskUserQuestion`: skip this task and continue / stop entirely.
   - **HALTED_AT_RETRY_LIMIT** — present remaining issues to user. Ask: accept (mark completed) and continue / stop (keep in_progress).

5. **Between tasks:** Report cumulative progress: `"Completed N/M tasks. Next: {title}"`

### Phase 3: Stage-end Test + Validate

After all tasks have completed (or user accepted concerns):

Build the validator prompt using `references/test-and-validate-prompt.md`. Fill placeholders:
- `{PLAN_PATH}` — plan file path (fallback only)
- `{PRD_PATH}` — PRD path (or "none")
- `{SCOPE}` — `whole-plan`
- `{TASK_TEXT}` — leave empty
- `{CHANGED_FILES}` — output of `git diff --name-only ${START_REF}..HEAD`
- `{WORKING_DIR}` — current working directory
- `{INLINE_PLAN_APPROACH}` — from Phase 1, plan §1
- `{INLINE_PLAN_TYPES}` — from Phase 1, plan §3
- `{INLINE_PLAN_TASKS}` — `INLINE_PLAN_TASKS_FULL` (the entire §4 verbatim — full task entries including each task's **Tests:** list, so the validator can trace every FR to a covering test)
- `{INLINE_PRD_FRS}` — from Phase 1, PRD §4 (or "None — no PRD")

Dispatch via **Task tool** (`general-purpose`, **model: sonnet**). Wait for completion.

**Handle the verdict:**
- **PASS** — proceed to Phase 4.
- **FAIL** — present `Required Fixes` to the user via `AskUserQuestion`. Options:
  - Re-run failed tasks via `/execute-task` (user picks which)
  - Accept failures as tech debt and proceed to Phase 4
  - Halt entirely

### Phase 4: Polish (1× or 2× per heuristic)

Compute change size:
```bash
git diff --shortstat ${START_REF}..HEAD
```

Parse the output for total LOC changed and files changed. Count phases completed (= number of tasks).

**Apply heuristic:**

| Condition | Polish runs |
|---|---|
| LOC > 300 **OR** files > 8 **OR** tasks > 4 | **2×** |
| Otherwise | **1×** |

**Run polish:**

```
Skill /workflow:polish <changed-files-from-diff>
```

If 2× heuristic triggered, run polish again after the first finishes (sequentially, not in parallel — the second pass acts on whatever the first left behind).

**Handle polish verdict:**
- **PASS** — proceed to Phase 5.
- **FAIL_AT_LIMIT** — note unresolved findings in the summary report; do not loop further.

### Phase 5: Summary Report

```
## Plan Execution Summary

**Plan:** {plan_path}
**Tasks completed:** N/M
**Polish runs:** {1 or 2}

| # | Task | Result | Tier (final) | Retries |
|---|------|--------|--------------|---------|
| 1 | {title} | COMPLETE | sonnet | 0/3 |
| 2 | {title} | COMPLETE | opus | 1/3 |
| ... | ... | ... | ... | ... |

**Stage-end validation:** {PASS | FAIL with required fixes}
**Final test suite:** X passing, Y failing
**Diff:** {LOC} LOC, {files} files changed since {START_REF}

**Concerns:** [DONE_WITH_CONCERNS notes from any tasks]
**Remaining issues:** [tasks halted at retry limit, accepted-as-tech-debt failures]
**Polish findings:** [unresolved Blocker/Major from FAIL_AT_LIMIT, if any]
```

## Important Rules

- **Always invoke `/workflow:execute-task` for each task.** Never implement directly in this skill.
- **Sequential execution only.** Tasks run in dependency order — do not parallelize.
- **User approval before execution.** Always present the parsed task list and get confirmation in Phase 1.
- **Pass the full §4 task entry** (including the `[model: ...]` tag and the inline **Tests:** list) as `task_text` — `/execute-task` parses the tag and the implementer relies on the inline tests.
- **Halt on BLOCKED.** Do not skip blocked tasks automatically — always consult the user.
- **Polish runs once at stage-end** (or twice for big changes), never per-task. Per-task validation handled by `/execute-task` Step 2.
- **Stage-end validate is whole-plan scope**, not per-task — catches cross-task regressions and integration issues that per-task validation misses.

## Additional Resources

### Reference Files

- **`references/test-and-validate-prompt.md`** — Prompt template for the validator subagent (used at stage-end here, and per-task by `/execute-task`)
