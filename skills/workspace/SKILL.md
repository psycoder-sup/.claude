---
name: workspace
description: This skill should be used when the user asks to "create a worktree", "new workspace", "open workspace", "remove workspace", "archive workspace", "list worktrees", "clean up workspace", or needs to manage cmux workspaces with git worktrees.
allowed-tools: Bash(gw-cmux:*), Bash(cmux:*), Bash(git:*)
user-invocable: true
---

# Workspace Skill

Manage git worktrees with cmux workspaces using `gw-cmux`.

## Arguments

```
$ARGUMENTS
```

Parse `$ARGUMENTS` into a **command** (`add`, `list`, `archive`, `remove`) and an optional **branch name**. If no command given, ask the user.

## Commands

| Command | Usage | Description |
|---------|-------|-------------|
| `add` | `gw-cmux add <branch>` | Create worktree at `~/.worktrees/<repo>/<branch>` + cmux workspace with 4-pane layout (yazi, claude, lazygit, terminal) |
| `list` | `gw-cmux list` | List all worktrees for the current repo |
| `archive` | `gw-cmux archive <branch>` | Run archive hooks, remove worktree + cmux workspace. Fails if uncommitted changes exist. |
| `remove` | `gw-cmux remove <branch>` | Force remove worktree + cmux workspace. Ignores uncommitted changes. |

## Execution

```bash
gw-cmux <command> <branch>
```

Branch names with `/` are sanitized to `-` in the worktree path automatically.

## When to Use Archive vs Remove

- **archive** — safe removal; aborts if there are uncommitted changes
- **remove** — force removal; use when you want to discard uncommitted work
