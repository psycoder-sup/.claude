# Baragi — Work Management

Use `baragi` CLI for all work and project management.

## Workflow

1. **Check next baragi work:** `baragi next --json` (use `--all` for all candidates)
2. **Start a baragi session** (marks work in-progress, returns full context):
   ```bash
   baragi session start --work=WORK-NNN --agent=claude-code --session-id="<session-id>"
   ```
   Session ID comes from the session start hook at conversation startup.
3. **Track progress** using Claude Code's built-in TaskCreate/TaskUpdate tools for plan steps. For plan implementations, always add a final task to use skills.
4. **Mark tasks done** as you go using TaskUpdate.
5. **Do NOT end the baragi work on your own.** Wait for the user to explicitly tell you to mark the work as done. When instructed, update the work:
   ```bash
   baragi work update WORK-NNN --status=done --summary="Brief description"
   ```
6. **Session cleanup is automatic.** A `SessionEnd` hook calls `baragi session close` when the Claude Code conversation ends, setting `ended_at` on the session without changing work status. You do NOT need to call `session end` or `session close` manually.

Always check for existing works and active sessions when resuming work.

## Quick Reference

| Action | Command |
|--------|---------|
| Next work to work on | `baragi next --json` |
| Next work in an epic | `baragi next --epic=EPIC-NNN --json` |
| All unblocked works | `baragi next --all --json` |
| List all works | `baragi work list --json` |
| List works in an epic | `baragi work list --epic=EPIC-NNN --json` |
| Show work detail | `baragi work show WORK-NNN --json` |
| Add a new work | `baragi work add "title" --priority=medium --description="..."` |
| Update work status | `baragi work update WORK-NNN --status=done` |
| View dependencies | `baragi work deps WORK-NNN --tree` |
| Check blocked works | `baragi work list --json --blocked` |
| List sessions for a work | `baragi session list --work=WORK-NNN --json` |
| Show session detail | `baragi session show --session-id=<id> --json` |
| List active sessions | `baragi session active --json` |
| Close orphaned session | `baragi session close --session-id=<id>` |

## Work Scoping

When creating baragi works, size them for **one session = one commit**:
- **1-5 files**, **50-300 LOC** changed per work
- If the title needs "and" more than once, split it
- Each repository, each command file, or each distinct concern = its own work

## Rules

- **BEFORE writing any code for a baragi work, you MUST run `baragi session start`.** This is a hard prerequisite — no exceptions, even if the user provides the work ID and plan upfront.
- Always pass `--json` when reading data (structured output for parsing).
- Never manually set work status to `in_progress` — use `session start` which handles this atomically.
- Never mark a work as `done` unless the user explicitly asks you to.
- When a work has dependencies, check `baragi work deps WORK-NNN` before starting.
- The session ID from the startup hook is used for `session start`. Session closing is handled automatically by the `SessionEnd` hook.
