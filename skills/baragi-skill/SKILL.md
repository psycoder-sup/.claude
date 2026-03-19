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
2. **Start a baragi session** (creates session, then attaches to work for full context):
   ```bash
   baragi session start --agent=claude-code --session-id="<session-id>"
   baragi session attach --session-id="<session-id>" --work=WORK-NNN
   ```
   Session ID comes from the session start hook at conversation startup. `session start` creates the session locally. `session attach` validates the work, marks it in-progress, and returns full context.
3. **Track progress** using Claude Code's built-in TaskCreate/TaskUpdate tools for plan steps. For plan implementations, always add a final task to use skills.
4. **Mark tasks done** as you go using TaskUpdate.
5. **Do NOT end the baragi work on your own.** Wait for the user to explicitly tell you to mark the work as done. When instructed, update the work:
   ```bash
   baragi work update WORK-NNN --json='{"status":"done","summary":"Brief description"}'
   ```
6. **Session cleanup is automatic.** A `SessionEnd` hook calls `baragi session close` when the Claude Code conversation ends, setting `ended_at` on the session without changing work status. You do NOT need to call `session end` or `session close` manually.

Always check for existing works and active sessions when resuming work.

## Quick Reference

### List Commands

| Action | Command |
|--------|---------|
| Create list | `baragi list add --json='{"name":"...","description":"..."}'` |
| List all lists | `baragi list list` |
| Get list | `baragi list get LIST-NNN` |
| Update list | `baragi list update LIST-NNN --json='{"name":"...","description":"...","status":"active"}'` |
| Delete list | `baragi list delete LIST-NNN` (use `--force` to unlink works) |

### Work Commands

| Action | Command |
|--------|---------|
| Add work | `baragi work add --json='{"title":"...","list_id":"LIST-NNN","priority":"medium","description":"...","labels":["l1","l2"],"depends_on":["WORK-NNN"],"due_date":"YYYY-MM-DD","parent_id":"WORK-NNN"}'` |
| Add child work | `baragi work add --json='{"title":"...","parent_id":"WORK-NNN"}'` (inherits project/list from parent) |
| List all works | `baragi work list --json='{"fields":["title","status","priority","is_blocked"]}'` |
| Filter by status | `baragi work list --json='{"status":"todo"}'` or `--json='{"status":"todo,in_progress"}'` |
| List works in list | `baragi work list --json='{"list_id":"LIST-NNN","fields":["title","status","priority"]}'` |
| List top-level only | `baragi work list --json='{"top_level_only":true,"fields":["title","status","child_count","children_done"]}'` |
| List children of work | `baragi work list --json='{"parent_id":"WORK-NNN","fields":["title","status"]}'` |
| Get work detail | `baragi work get WORK-NNN --json='{"fields":["title","status","priority","description","children","dependencies"]}'` |
| Update work | `baragi work update WORK-NNN --json='{"title":"...","description":"...","priority":"...","status":"done","summary":"..."}'` |
| Re-parent work | `baragi work update WORK-NNN --json='{"parent_id":"WORK-NNN"}'` (clear with `--parent-id=""`) |
| Delete work | `baragi work delete WORK-NNN` (use `--force` if work has children; cascades) |

### Dependency Commands

| Action | Command |
|--------|---------|
| Add dependency | `baragi work depend WORK-NNN --on=WORK-NNN` |
| Remove dependency | `baragi work undepend WORK-NNN --on=WORK-NNN` |
| Show deps for work | `baragi work deps WORK-NNN` |
| Show dependents | `baragi work deps WORK-NNN --json='{"dependents":true}'` |
| Show full dep tree | `baragi work deps --json='{"tree":true}'` |
| Check blocked works | `baragi work list --json='{"blocked":true}'` |

### Discovery & Session Commands

| Action | Command |
|--------|---------|
| Next work to work on | `baragi next --json='{"fields":["title","status","priority","is_blocked"]}'` |
| Next work in a list | `baragi next --json='{"list_id":"LIST-NNN","fields":["title","status","priority"]}'` |
| All unblocked works | `baragi next --json='{"all":true,"fields":["title","status","priority"]}'` |

When `next` returns no work, the JSON response includes a `reason` field: `no_works` (nothing exists), `all_done` (all complete), or `all_blocked` (remaining are blocked).
| List all sessions | `baragi session list` |
| List sessions for a work | `baragi session list --json='{"work":"WORK-NNN"}'` |
| Attach session to work | `baragi session attach --session-id=<id> --work=WORK-NNN` |
| Get session detail | `baragi session get --session-id=<id>` |
| List active sessions | `baragi session active` |
| Close orphaned session | `baragi session close --session-id=<id>` |

## Hierarchy Scoping

| Level | Scope | Decision test |
|-------|-------|---------------|
| **List** | Thematic grouping / sprint / milestone. Groups related-but-independent features. Maps to **one git worktree** for parallel processing. | Multiple PRs under this umbrella? |
| **Parent work** | One feature = one PR. One user-visible outcome, 1–3 days of agent effort. | PR title on a Kanban board? |
| **Child work** | One implementation step. One session, one layer, one commit. 1–5 files, 50–300 LOC. | Checklist item inside a PR? |
| **Standalone work** | Small enough to not need decomposition. | One session, no breakdown needed? |

**Anti-patterns:** Parent with 1 child (use standalone), parent with 10+ children (split into 2–3 parents), child spanning multiple layers (split by layer), list with only 1 work (probably doesn't need its own list).

## Parent/Child Works

Works support **1-level nesting** (parent → children, no grandchildren). Use parent works to group related subtasks.
- `--parent=WORK-NNN` on `work add` creates a child that inherits the parent's project and list.
- A work with children cannot itself become a child. A child cannot have children.
- Deleting a parent cascades to all children (requires `--force`).
- `work get` on a parent includes a `children` array; on a child includes `parent_id`.
- `work list` enriches parents with `child_count` and `children_done` counts.

## Structuring Dependencies

### Within a parent (sibling dependencies)
- Add dependencies when there's a real build order (model → repo → command) — helps `baragi next` pick the right child
- Skip when siblings are truly parallel (e.g., two independent commands)

### Between parents (cross-parent dependencies)
- **Prefer parent-on-parent** for coarse ordering ("auth feature before permissions feature")
- **Use child-on-child cross-parent** only when one specific child blocks another specific child — avoids waiting for an entire parent to finish

### When NOT to add dependencies
- Soft preferences ("nice to do X first") — only add when starting out of order causes real failures (missing model, missing table, missing API)
- Between a parent and its own children (parent-child relationship already implies this)

### Rule of thumb
If an agent starts the work without the dependency done and hits a compile error or missing table — it needs a dependency. If it just feels like a natural order — it doesn't.

## Rules

- **BEFORE writing any code for a baragi work, you MUST run `baragi session start` followed by `baragi session attach`.** This is a hard prerequisite — no exceptions, even if the user provides the work ID and plan upfront.
- JSON output is the default. Use `--json` (global option) on any command for structured input (not output). Prefer `--json` over individual CLI flags.
- Never manually set work status to `in_progress` — use `session start` which handles this atomically.
- Never mark a work as `done` unless the user explicitly asks you to.
- When a work has dependencies, check `baragi work deps WORK-NNN` before starting.
- The session ID from the startup hook is used for `session start`. Session closing is handled automatically by the `SessionEnd` hook.

## Agent DX Flags

| Flag | Scope | Purpose |
|------|-------|---------|
| `--json='{"key":"val"}'` | **All commands** (global) | Structured input — prefer over individual flags. CLI flags override JSON values. String fields: `"status":"todo"`. Bool fields: `"all":true`. Arrays: `"labels":["a","b"]`. Fields filter: `"fields":["title","status"]` |
| `--dry-run` | All mutating commands | Validate input without executing. Returns `{dry_run:true, parsed:{...}}` |
| `--fields=title,status` | All resource-returning commands | Filter response fields to reduce output. `id` always included. Ignored in `--human` mode. Prefer `"fields"` inside `--json` |
| `--ndjson` | List commands (work list, list list, etc.) | One JSON object per line, no envelope. Conflicts with `--human`. Can also be set via `--json='{"ndjson":true}'` |
| `baragi describe [cmd] [sub]` | Standalone | Schema introspection — discover command options, types, formats at runtime |
