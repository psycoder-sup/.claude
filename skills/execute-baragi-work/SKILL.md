---
name: execute-baragi-work
description: >-
  This skill should be used when the user asks to "execute the work",
  "implement WORK-NNN", "run WORK-NNN", "execute baragi work",
  "start executing the work items", or wants to sequentially implement
  all children of a baragi parent work item. Fetches the parent and
  children from baragi, reads referenced spec/PRD documents, and invokes
  /execute-task for each child to guarantee the 3-step
  implement-review-polish flow.
allowed-tools: [Read, Glob, Grep, Skill, Task, AskUserQuestion, TaskCreate, TaskUpdate, Bash(baragi:*)]
user-invocable: true
argument-hint: "<WORK-NNN>"
---

# Execute Baragi Work

Fetch a baragi parent work item and its children, read the referenced spec/PRD documents, and execute children sequentially by invoking `/execute-task` for each. Every child goes through the mandatory 3-step flow (implement -> review spec compliance -> polish) enforced by the `/execute-task` skill.

## Arguments

```
$ARGUMENTS
```

Parse the first argument as a baragi work item ID (e.g., `WORK-042`).

If no argument is provided, run `baragi next --fields=title,status,priority,child_count` and ask the user to confirm which parent work to execute.

## Process Overview

```
WORK-NNN (parent work ID)
    |
    v
Phase 1: Fetch Work Items
    - Get parent work details and description
    - List all children with full descriptions
    - Extract spec/PRD paths from descriptions
    - Read spec/PRD for context
    - Present children for user approval
    |
    v
Phase 2: Execute Children (sequential, respecting dependencies)
    - For each child: invoke /execute-task
    - Update baragi work status per child
    - Progress report between children
    |
    v
Phase 3: Final Verification
    - Run full test suite
    - Summary report
```

## Execution

### Phase 1: Fetch Work Items

1. **Fetch the parent work item:**

   ```bash
   baragi work get WORK-NNN --fields=title,status,description,children,dependencies
   ```

2. **List all children with full details** (use `--all` to include all statuses):

   ```bash
   baragi work list --parent-id=WORK-NNN --all --fields=title,status,description,is_blocked,dependencies
   ```

3. **Extract source documents.** Parse the parent work's description (or children's descriptions) for the `**Source Documents:**` section:

   ```
   **Source Documents:**
   - SPEC: docs/feature/foo/foo-spec.md (Section N: ...)
   - PRD: docs/feature/foo/foo-prd.md (FR-01 through FR-10)
   ```

   Extract the spec path and PRD path. If children have their own source document references, use those per-child (they may reference different spec sections).

4. **Read source documents.** Read the spec and PRD files to have context available. Do not pass the entire spec to subagents — each child's description already contains its scoped context.

5. **Determine execution order.** Respect baragi dependencies — children with `is_blocked=true` cannot start until their dependencies are done. Execute unblocked children first, in dependency order.

6. **Filter children.** Skip children with `status=done`. Only execute children with `status=todo` or `status=in_progress`.

7. **Present the execution plan** to the user via `AskUserQuestion`:
   - Show: child work ID, title, status, blocked status, one-line scope for each
   - Show: execution order based on dependencies
   - Ask: "Proceed with executing N children?" with options to proceed, skip specific children, or cancel

8. **Create task tracking.** After user approval, use `TaskCreate` to create one task per child to execute. Each task should have:
   - **subject:** "{WORK-ID}: {child title}"
   - **description:** One-line scope summary from the child's description

### Phase 2: Execute Children

For each child to execute, in dependency order:

1. **Check if unblocked.** Run `baragi work get {CHILD_ID} --fields=status,is_blocked`. If still blocked, wait — re-check after the blocking work completes. If a blocker is outside this parent's scope, halt and consult user.

2. **Mark task in_progress** via `TaskUpdate`.

3. **Update baragi status.** Attach the current session to the child work:

   ```bash
   baragi session attach --session-id="<session-id>" --work={CHILD_ID}
   ```

4. **Build the task text.** Combine:
   - The child's full description from baragi (scope, changes, tests, done-when)
   - Referenced spec sections (read from the spec file at the paths/sections cited in the child's `**Source Documents:**`)
   - PRD functional requirements cited in the child

5. **Invoke `/execute-task`** via Skill tool:

   ```
   /execute-task {child_title} | {enriched_task_text} | {spec_path} | {prd_path}
   ```

6. **Handle the result:**
   - **COMPLETE** — update baragi: `baragi work update {CHILD_ID} --status=done --summary="{summary from execute-task report}"`. Mark task `completed` via `TaskUpdate`. Move to next child.
   - **BLOCKED** — keep baragi status as `in_progress`. Halt execution. Present the blocker to the user. Ask whether to skip and continue, or stop entirely.
   - **HALTED_AT_RETRY_LIMIT** — present remaining issues. Ask whether to accept (mark `done`) and continue, or stop.

7. **Between children:** Report cumulative progress: "Completed N/M: {WORK-ID} {title}. Next: {next child}"

### Phase 3: Final Verification

After all children complete:

1. **Run full test suite** via the `test-runner-slim` agent (Task tool). This catches cross-child regressions.

2. **Summary report:**

```
## Execution Summary

**Parent work:** {WORK-ID} — {parent title}
**Spec:** {spec_path}
**Children completed:** N/M

| # | Work ID | Title | Result | Retries |
|---|---------|-------|--------|---------|
| 1 | WORK-043 | {title} | COMPLETE | 0/3 |
| 2 | WORK-044 | {title} | COMPLETE | 1/3 |
| ... | ... | ... | ... | ... |

**Final test suite:** X passing, Y failing

**Concerns:** [any DONE_WITH_CONCERNS notes]
**Remaining issues:** [any children that hit retry limit]
```

3. **Do NOT mark the parent work as done.** Only the user decides when to mark the parent complete.

## Important Rules

- **Always invoke `/execute-task` for each child.** Never implement directly — that bypasses the 3-step enforcement.
- **Respect dependency order.** Do not execute a blocked child. Wait for its dependencies to complete first.
- **Skip done children.** Only execute `todo` or `in_progress` children.
- **Enrich task text.** Read the spec sections referenced in each child's description and inline them so the subagent has full context.
- **Halt on BLOCKED.** Do not skip blocked children automatically — always consult the user.
- **Never mark the parent done.** Only mark children done after `/execute-task` completes successfully.
- **Use `session attach` before each child.** This gives baragi proper session tracking per work item.
