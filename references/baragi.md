# Baragi — Task Management

Use `baragi` CLI for all task and project management.

## Workflow

1. **Check next baragi task:** `baragi next --json` (use `--all` for all candidates)
2. **Start a baragi session** (marks task in-progress, returns full context):
   ```bash
   baragi session start --task=TASK-NNN --agent=claude-code --session-id="<session-id>"
   ```
   Session ID comes from the session start hook at conversation startup.
3. **Track progress** using Claude Code's built-in TaskCreate/TaskUpdate tools for plan steps. For plan implementations, always add a final task to use skills.
4. **Mark tasks done** as you go using TaskUpdate.
5. **Do NOT end the baragi task on your own.** Wait for the user to explicitly tell you to mark the task as done. When instructed, update the task:
   ```bash
   baragi task update TASK-NNN --status=done --summary="Brief description"
   ```
6. **Session cleanup is automatic.** A `SessionEnd` hook calls `baragi session close` when the Claude Code conversation ends, setting `ended_at` on the session without changing task status. You do NOT need to call `session end` or `session close` manually.

Always check for existing tasks and active sessions when resuming work.

## Quick Reference

| Action | Command |
|--------|---------|
| Next task to work on | `baragi next --json` |
| Next task in an epic | `baragi next --epic=EPIC-NNN --json` |
| All unblocked tasks | `baragi next --all --json` |
| List all tasks | `baragi task list --json` |
| List tasks in an epic | `baragi task list --epic=EPIC-NNN --json` |
| Show task detail | `baragi task show TASK-NNN --json` |
| Add a new task | `baragi task add "title" --priority=medium --description="..."` |
| Update task status | `baragi task update TASK-NNN --status=review` |
| View dependencies | `baragi task deps TASK-NNN --tree` |
| Check blocked tasks | `baragi task list --json --blocked` |
| List sessions for a task | `baragi session list --task=TASK-NNN --json` |
| Show session detail | `baragi session show --session-id=<id> --json` |
| List active sessions | `baragi session active --json` |
| Close orphaned session | `baragi session close --session-id=<id>` |

## Task Scoping

When creating baragi tasks, size them for **one session = one commit**:
- **1-5 files**, **50-300 LOC** changed per task
- If the title needs "and" more than once, split it
- Each repository, each command file, or each distinct concern = its own task
- See `@docs/guidelines/task-scoping.md` for full guidelines

## Rules

- **BEFORE writing any code for a baragi task, you MUST run `baragi session start`.** This is a hard prerequisite — no exceptions, even if the user provides the task ID and plan upfront.
- Always pass `--json` when reading data (structured output for parsing).
- Never manually set task status to `in_progress` — use `session start` which handles this atomically.
- Never mark a task as `done` unless the user explicitly asks you to.
- When a task has dependencies, check `baragi task deps TASK-NNN` before starting.
- The session ID from the startup hook is used for `session start`. Session closing is handled automatically by the `SessionEnd` hook.
