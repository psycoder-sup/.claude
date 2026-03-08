---
name: baragi-skill
description: Baragi work management CLI reference. Use when the user mentions work items (WORK-NNN), lists (LIST-NNN), needs baragi command syntax, or starts work on a task.
allowed-tools: Bash(baragi:*)
user-invocable: true
---

# Baragi — Work Management

Use `baragi` CLI for all work and project management.

## Workflow

1. **Check next baragi work:** `baragi next` (use `--all` for all candidates)
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

### List Commands

| Action | Command |
|--------|---------|
| Create list | `baragi list add "name" --description="..."` |
| List all lists | `baragi list list` |
| Show list | `baragi list show LIST-NNN` |
| Update list | `baragi list update LIST-NNN --name="..." --description="..." --status=active\|archived` |
| Delete list | `baragi list delete LIST-NNN` (use `--force` to unlink works) |

### Work Commands

| Action | Command |
|--------|---------|
| Add work | `baragi work add "title" --list=LIST-NNN --priority=medium --description="..." --labels="l1,l2" --depends-on=WORK-NNN --due-date=YYYY-MM-DD --parent=WORK-NNN` |
| Add child work | `baragi work add "title" --parent=WORK-NNN` (inherits project/list from parent) |
| List all works | `baragi work list` |
| List works in list | `baragi work list --list=LIST-NNN` |
| List top-level only | `baragi work list --top-level-only` (excludes children) |
| List children of work | `baragi work list --parent=WORK-NNN` |
| Show work detail | `baragi work show WORK-NNN` (shows `children` array for parents, `parent_id` for children) |
| Update work | `baragi work update WORK-NNN --title="..." --description="..." --priority=... --status=done --summary="..."` |
| Re-parent work | `baragi work update WORK-NNN --parent=WORK-NNN` (clear with `--parent=""`) |
| Delete work | `baragi work delete WORK-NNN` (use `--force` if work has children; cascades) |

### Dependency Commands

| Action | Command |
|--------|---------|
| Add dependency | `baragi work depend WORK-NNN --on=WORK-NNN` |
| Remove dependency | `baragi work undepend WORK-NNN --on=WORK-NNN` |
| Show deps for work | `baragi work deps WORK-NNN` |
| Show dependents | `baragi work deps WORK-NNN --dependents` |
| Show full dep tree | `baragi work deps --tree` |
| Check blocked works | `baragi work list --blocked` |

### Discovery & Session Commands

| Action | Command |
|--------|---------|
| Next work to work on | `baragi next` |
| Next work in a list | `baragi next --list=LIST-NNN` |
| All unblocked works | `baragi next --all` |
| List sessions for a work | `baragi session list --work=WORK-NNN` |
| Show session detail | `baragi session show --session-id=<id>` |
| List active sessions | `baragi session active` |
| Close orphaned session | `baragi session close --session-id=<id>` |

## List Scoping

A list maps to **one git worktree**, enabling parallel processing of multiple lists across separate worktrees.

## Parent/Child Works

Works support **1-level nesting** (parent → children, no grandchildren). Use parent works to group related subtasks.
- `--parent=WORK-NNN` on `work add` creates a child that inherits the parent's project and list.
- A work with children cannot itself become a child. A child cannot have children.
- Deleting a parent cascades to all children (requires `--force`).
- `work show` on a parent includes a `children` array; on a child includes `parent_id`.
- `work list` enriches parents with `child_count` and `children_done` counts.

## Work Scoping

When creating baragi works, size them for **one session = one commit**:
- **1-5 files**, **50-300 LOC** changed per work
- If the title needs "and" more than once, split it
- Each repository, each command file, or each distinct concern = its own work

## Rules

- **BEFORE writing any code for a baragi work, you MUST run `baragi session start`.** This is a hard prerequisite — no exceptions, even if the user provides the work ID and plan upfront.
- JSON output is the default — no need to pass `--json` (it no longer exists; use `--human` for human-readable output).
- Never manually set work status to `in_progress` — use `session start` which handles this atomically.
- Never mark a work as `done` unless the user explicitly asks you to.
- When a work has dependencies, check `baragi work deps WORK-NNN` before starting.
- The session ID from the startup hook is used for `session start`. Session closing is handled automatically by the `SessionEnd` hook.
