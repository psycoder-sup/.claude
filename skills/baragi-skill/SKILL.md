---
name: baragi-skill
description: Baragi work management CLI reference. Use when the user mentions work items (WORK-NNN), epics (EPIC-NNN), needs baragi command syntax, or starts work on a task.
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

### Epic Commands

| Action | Command |
|--------|---------|
| Create epic | `baragi epic add "name" --description="..."` |
| List epics | `baragi epic list` |
| Show epic | `baragi epic show EPIC-NNN` |
| Update epic | `baragi epic update EPIC-NNN --name="..." --description="..." --status=active\|completed\|archived` |
| Delete epic | `baragi epic delete EPIC-NNN` (use `--force` to unlink works) |

### Work Commands

| Action | Command |
|--------|---------|
| Add work | `baragi work add "title" --epic=EPIC-NNN --priority=medium --description="..." --acceptance-criteria="c1,c2" --related-files="f1,f2" --labels="l1,l2" --depends-on=WORK-NNN --due-date=YYYY-MM-DD` |
| List all works | `baragi work list` |
| List works in epic | `baragi work list --epic=EPIC-NNN` |
| Show work detail | `baragi work show WORK-NNN` |
| Update work | `baragi work update WORK-NNN --title="..." --description="..." --priority=... --status=done --summary="..."` |
| Delete work | `baragi work delete WORK-NNN` |

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
| Next work in an epic | `baragi next --epic=EPIC-NNN` |
| All unblocked works | `baragi next --all` |
| List sessions for a work | `baragi session list --work=WORK-NNN` |
| Show session detail | `baragi session show --session-id=<id>` |
| List active sessions | `baragi session active` |
| Close orphaned session | `baragi session close --session-id=<id>` |

## Epic Scoping

An epic maps to **one git worktree**, enabling parallel processing of multiple epics across separate worktrees.

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
