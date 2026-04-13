---
name: execute-task
description: >-
  This skill should be used when executing a single implementation task from a
  SPEC document. It enforces a mandatory 3-step flow: implement (TDD) -> review
  spec compliance -> polish. Called by /execute-work-orchestration for each phase,
  or directly for re-running a single task.
allowed-tools: [Read, Glob, Grep, Task, Skill, AskUserQuestion, Bash(git:*)]
user-invocable: true
argument-hint: "<task-title> | <task-text> | <spec-path> | <prd-path>"
---

# Execute Task

Execute a single implementation task using a mandatory 3-step flow with fresh-context subagents. This skill guarantees that every task goes through implement, spec review, and polish — no step can be skipped.

## Arguments

```
$ARGUMENTS
```

Parse the arguments as pipe-delimited fields:
- **Task title** — short name for the task
- **Task text** — full task description (scope, deliverables, acceptance criteria)
- **Spec path** — path to the SPEC document
- **PRD path** — path to the companion PRD (or "none")

If arguments are not pipe-delimited, treat the entire input as a task description and ask for the missing fields via `AskUserQuestion`.

## Process Overview

```
Step 1: IMPLEMENT (fresh subagent, TDD)
    |
    status?
    |-- DONE / DONE_WITH_CONCERNS --> Step 2
    |-- BLOCKED --> halt, report to caller
    |-- NEEDS_CONTEXT --> ask user, re-dispatch Step 1
    |
Step 2: REVIEW SPEC COMPLIANCE (fresh subagent)
    |
    verdict?
    |-- PASS --> Step 3
    |-- FAIL --> back to Step 1 with issues (retry++)
    |
Step 3: POLISH (invoke /polish on changed files)
    |
    changes made?
    |-- no changes --> Step 4
    |-- changes made --> back to Step 2 to re-verify (retry++)
    |
(max 3 retries across all steps)
    |
Step 4: COMMIT (atomic commit for this task)
    |
    --> TASK COMPLETE
```

## Execution

Initialize: `retry_count = 0`, `previous_issues = "None"`

### Step 1: Implement

Build the implementer prompt using the template from `references/implementer-prompt.md`. Fill placeholders:
- `{TASK_TITLE}` — task title from arguments
- `{TASK_TEXT}` — full task text from arguments
- `{SPEC_PATH}` — spec file path
- `{PRD_PATH}` — PRD file path
- `{WORKING_DIR}` — current working directory
- `{PREVIOUS_ISSUES}` — issues from prior review/polish cycles, or "None" on first run

Dispatch via **Task tool** (general-purpose subagent). Wait for completion.

**Handle the implementer's status:**
- **DONE** — capture the report (changed files, test results, summary). Proceed to Step 2.
- **DONE_WITH_CONCERNS** — note the concerns. Proceed to Step 2.
- **NEEDS_CONTEXT** — present the implementer's questions to the user via `AskUserQuestion`. Re-dispatch Step 1 with the answers added to context.
- **BLOCKED** — report the blocker to the user. Halt execution. Do not proceed.

### Step 2: Review Spec Compliance

Build the reviewer prompt using the template from `references/spec-reviewer-prompt.md`. Fill placeholders:
- `{TASK_TITLE}` — task title
- `{TASK_TEXT}` — full task text
- `{SPEC_PATH}` — spec file path
- `{PRD_PATH}` — PRD file path
- `{IMPLEMENTER_REPORT}` — the implementer's full report from Step 1
- `{CHANGED_FILES}` — list of changed files from the implementer's report

Dispatch via **Task tool** (general-purpose subagent). Wait for completion.

**Handle the reviewer's verdict:**
- **PASS** — proceed to Step 3.
- **FAIL** — increment `retry_count`. If `retry_count < 3`, set `previous_issues` to the reviewer's issues list and go back to Step 1. If `retry_count >= 3`, report remaining issues to the user via `AskUserQuestion` and ask whether to continue or halt.

### Step 3: Polish

Invoke the `/polish` skill via **Skill tool**, passing the changed files as scope:

```
/polish <changed-files-from-implementer-report>
```

Wait for completion.

**Handle polish results:**
- **No issues found / no changes made** — proceed to Step 4.
- **Changes were made** — increment `retry_count`. If `retry_count < 3`, go back to Step 2 to re-verify spec compliance after polish changes. If `retry_count >= 3`, accept the current state and proceed to Step 4 with a note that retry limit was reached.

### Step 4: Commit

Create an atomic commit for this task's changes. This runs in the orchestrator session (not a subagent).

1. **Stage changed files** — `git add` the specific files from the implementer's changed files list. Do not use `git add -A`.
2. **Commit** with a descriptive message following the project's conventional commit style:

```bash
git commit -m "$(cat <<'EOF'
feat({scope}): {task title}

Implements phase from {spec filename}.
- {1-2 line summary of what was built}

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

3. If the commit fails (e.g., pre-commit hook), fix the issue and retry the commit. Do not use `--no-verify`.

## Report

When the task completes (or halts), report:

```
## Task: {TASK_TITLE}

**Result:** [COMPLETE | BLOCKED | HALTED_AT_RETRY_LIMIT]
**Commit:** [short hash and message, or "none" if BLOCKED]
**Retries used:** N/3
**Changed files:** [list]
**Concerns:** [any DONE_WITH_CONCERNS notes]
**Remaining issues:** [if halted at retry limit]
```

## Model Selection

Use the least powerful model that can handle each role to conserve cost and increase speed. Model selection is based on the **task complexity**, assessed before dispatching Step 1.

**Mechanical tasks** (isolated functions, clear spec, 1-2 files): use a fast, cheap model. Most tasks are mechanical when the spec is well-defined.

**Integration and judgment tasks** (multi-file coordination, pattern matching, debugging): use a standard model.

**Architecture, design, and review tasks** (broad codebase understanding, design judgment): use the most capable model.

**Task complexity signals:**
- Touches 1-2 files with a complete spec → cheap model
- Touches multiple files with integration concerns → standard model
- Requires design judgment or broad codebase understanding → most capable model

The chosen model tier applies to **Step 1 (Implement)** and **Step 2 (Review)** equally — the reviewer needs at least as much capability as the implementer to verify the work. Step 3 (Polish) inherits the session model. Step 4 (Commit) runs in the orchestrator, no subagent.

**Escalation on retry:**
- If the implementer reports BLOCKED or fails review, re-assess: is it a context problem or a reasoning problem?
- Context problem → provide more context, re-dispatch with the same model
- Reasoning problem → upgrade one tier and re-dispatch
- Never force the same model to retry without changes

## Important Rules

- **Never skip a step.** All 3 steps are mandatory for every task.
- **Fresh context per step.** Each subagent (implement, review) starts with no conversation history. Only `/polish` runs in the current session context.
- **Retry counter is shared** across Steps 1-3. Total max 3 retries per task, not per step.
- **Do not fix code yourself.** Always dispatch a subagent. Fixing code in the orchestrator pollutes context.
- **Use test-runner-slim** for all test execution (subagents handle this internally).
- **If BLOCKED, halt immediately.** Do not attempt workarounds.

## Additional Resources

### Reference Files

- **`references/implementer-prompt.md`** — Prompt template for the implementer subagent
- **`references/spec-reviewer-prompt.md`** — Prompt template for the spec compliance reviewer
