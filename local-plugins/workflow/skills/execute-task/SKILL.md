---
name: execute-task
description: >-
  This skill should be used when executing a single implementation task from a
  plan document. Runs the task through implement → validate, with retry +
  model escalation on validation failure. Called by /execute-plan for each task,
  or directly for re-running a single task.
allowed-tools: [Read, Glob, Grep, Task, Skill, AskUserQuestion, Bash(git:*)]
user-invocable: true
argument-hint: "<task-title> | <task-text> | <plan-path> | <prd-path>"
---

# Execute Task

Execute a single implementation task using a slim 2-step flow with model escalation on retry. The task text from the plan should include a `[model: haiku|sonnet|opus]` tag — that's the starting tier. On validation failure, the next attempt uses the next tier up (capped at opus).

## Arguments

```
$ARGUMENTS
```

Parse the arguments as pipe-delimited fields:
- **Task title** — short name for the task
- **Task text** — full task description from plan §4, including the `[model: ...]` tag, files, dependencies, deliverables, "done when", and the inline **Tests:** list
- **Plan path** — path to the plan document
- **PRD path** — path to the companion PRD (or "none")

If arguments are not pipe-delimited, treat the entire input as a task description and ask for the missing fields via `AskUserQuestion`.

## Process Overview

```
Step 1: IMPLEMENT     (general-purpose, model = current_tier, TDD, 2 commits)
    |
    status?
    |-- DONE / DONE_WITH_CONCERNS --> Step 2
    |-- BLOCKED --> halt, report to caller
    |-- NEEDS_CONTEXT --> ask user, re-dispatch Step 1
    |
Step 2: VALIDATE      (general-purpose, sonnet, scoped to THIS task)
    |
    verdict?
    |-- PASS --> Step 3
    |-- FAIL --> escalate model tier, retry Step 1 (retry_count++)
    |
(max 3 retries → 4 total attempts)
    |
Step 3: VERIFY COMMITS (orchestrator-side check, no subagent)
    |
    --> TASK COMPLETE
```

## Execution

Initialize:
- `retry_count = 0`
- `current_tier` = parse `[model: ...]` from task text; default `sonnet` if absent
- `previous_issues = "None"`

### Step 0: Inline Plan + PRD Context (orchestrator-side)

Before dispatching Step 1 or Step 2, read the plan and PRD files **once** in the orchestrator and extract the sections that will be inlined into subagent prompts. This avoids each subagent re-reading the full files.

1. `Read` the plan file at `{PLAN_PATH}`. Extract:
   - **§1 Approach** — full content, verbatim
   - **§3 Types & Interfaces** — full content, verbatim (this is critical — types must not drift between plan and implementation)

   Tests for this task are already part of the task's §4 entry, which the caller passes as `{TASK_TEXT}`. No separate test extraction is needed.
2. `Read` the PRD file at `{PRD_PATH}` if it exists. Extract:
   - **§4 Functional Requirements** — full FR list, verbatim

These extracted blocks become `{INLINE_PLAN_APPROACH}`, `{INLINE_PLAN_TYPES}`, `{INLINE_PRD_FRS}` placeholders in the implementer and validator prompts.

### Step 1: Implement

Build the implementer prompt using the template at `references/implementer-prompt.md`. Fill placeholders:
- `{TASK_TITLE}` — task title
- `{TASK_TEXT}` — full task text (plan §4 entry, includes `[model: ...]` tag and the **Tests:** list)
- `{PLAN_PATH}` — plan file path (for fallback deep-reads)
- `{PRD_PATH}` — PRD file path (or "none")
- `{WORKING_DIR}` — current working directory
- `{PREVIOUS_ISSUES}` — issues from the prior validate cycle, or "None" on first attempt
- `{INLINE_PLAN_APPROACH}` — extracted in Step 0
- `{INLINE_PLAN_TYPES}` — extracted in Step 0
- `{INLINE_PRD_FRS}` — extracted in Step 0 (or "None — no PRD")

Dispatch via **Task tool** (`general-purpose`, **model = current_tier**). Wait for completion.

**Handle the implementer's status:**
- **DONE** — capture the report (changed files, test results, summary). Proceed to Step 2.
- **DONE_WITH_CONCERNS** — note the concerns. Proceed to Step 2.
- **NEEDS_CONTEXT** — present the implementer's questions to the user via `AskUserQuestion`. Re-dispatch Step 1 with the answers added (no retry counter increment).
- **BLOCKED** — report the blocker to the user. Halt execution. Do not proceed.

### Step 2: Validate

Build the validator prompt using the template at `${CLAUDE_PLUGIN_ROOT}/skills/execute-plan/references/test-and-validate-prompt.md`. Fill placeholders:
- `{PLAN_PATH}` — plan file path (for fallback deep-reads)
- `{PRD_PATH}` — PRD file path (or "none")
- `{SCOPE}` — `task: {TASK_TITLE}`
- `{TASK_TEXT}` — the full plan §4 task entry (includes the **Tests:** list)
- `{CHANGED_FILES}` — list of files from the implementer's report
- `{WORKING_DIR}` — current working directory
- `{INLINE_PLAN_APPROACH}` — same extracted block as Step 1
- `{INLINE_PLAN_TYPES}` — same extracted block as Step 1
- `{INLINE_PRD_FRS}` — same extracted block as Step 1

Dispatch via **Task tool** (`general-purpose`, **model: sonnet**). Wait for completion.

**Handle the validator's verdict:**
- **PASS** — proceed to Step 3.
- **FAIL** — increment `retry_count`. If `retry_count <= 3`:
  1. Escalate `current_tier` per the ladder below.
  2. Set `previous_issues` to the validator's `Required Fixes` list verbatim.
  3. Go back to Step 1.

  If `retry_count > 3` (4 attempts exhausted), report remaining issues to the user via `AskUserQuestion` with options:
  - **Accept as tech debt and proceed** (mark task COMPLETE with concerns)
  - **Halt** (status `HALTED_AT_RETRY_LIMIT`)

### Model Escalation Ladder

| Current tier | Next tier on failure |
|---|---|
| haiku | sonnet |
| sonnet | opus |
| opus | opus (no further escalation) |

The validator stays on **sonnet** for every attempt — judging is cheaper than doing.

### Step 3: Verify Commits

The implementer subagent produces TWO commits per task (TDD enforcement):
1. `test:` commit with the failing tests
2. `feat:` commit with the implementation

Verify the final state:

1. Run `git log --oneline -n 5`. Confirm `feat: ...` is at HEAD and `test: ...` is its parent (or earlier).
2. If neither commit is present, the implementer failed TDD enforcement — report `BLOCKED`.
3. **Do not** squash `test:` and `feat:` into a single commit — the ordering is what makes TDD verifiable after the fact.

## Report

When the task completes (or halts), report:

```
## Task: {TASK_TITLE}

**Result:** [COMPLETE | BLOCKED | HALTED_AT_RETRY_LIMIT]
**Commit:** [short hash and message, or "none" if BLOCKED]
**Retries used:** N/3
**Final tier:** [haiku | sonnet | opus]
**Changed files:** [list]
**Concerns:** [any DONE_WITH_CONCERNS notes]
**Remaining issues:** [if halted at retry limit]
```

## Important Rules

- **Two-step flow only.** Implement, validate. Polish runs at stage-end in `/execute-plan` — never per-task.
- **Model tier comes from the plan.** Parse `[model: ...]` from task text. Don't guess.
- **Escalate on validation failure**, not implementer-reported concerns. `DONE_WITH_CONCERNS` proceeds to Step 2; only Step 2 `FAIL` triggers escalation.
- **Validator stays on sonnet.** Never escalate the validator.
- **Fresh context per step.** Implementer and validator start with no conversation history.
- **Do not fix code yourself.** Always dispatch a subagent. Fixing code in the orchestrator pollutes context.
- **If BLOCKED, halt immediately.** Do not attempt workarounds.

## Additional Resources

### Reference Files

- **`references/implementer-prompt.md`** — Prompt template for the implementer subagent
- **`../execute-plan/references/test-and-validate-prompt.md`** — Prompt template for the validator (also used at stage-end by `/execute-plan`)
