---
name: worktree
description: This skill should be used when the user asks to "create a worktree", "set up a worktree workspace", "work on multiple branches", "manage worktrees", "list worktrees", "remove worktree", or mentions needing to work on multiple branches simultaneously with tmux integration.
model: haiku
user-invocable: true
---

# Git Worktree Workspace Manager

This skill manages git worktrees with tmux terminal integration, enabling work on multiple branches simultaneously without stashing changes.

## Overview

Git worktrees allow checking out multiple branches of the same repository into separate directories. This skill creates organized workspaces at `~/.worktree/{project-name}/{branch-name}` and opens new tmux windows for each worktree when tmux is running.

## Helper Script

Use the helper script at `scripts/worktree.sh` for all operations:

```bash
# Create worktree with Ghostty tab
~/.claude/skills/worktree/scripts/worktree.sh create <branch-name>

# List existing worktrees
~/.claude/skills/worktree/scripts/worktree.sh list

# Remove worktree
~/.claude/skills/worktree/scripts/worktree.sh remove <name>
```

## Operations

| Operation | Command | Description |
|-----------|---------|-------------|
| Create | `create <branch>` | Creates worktree, opens tmux window with Claude |
| List | `list` | Shows all git worktrees |
| Remove | `remove <name>` | Removes worktree (close tmux window manually) |

## tmux Integration

When creating a worktree, the script:
1. Creates the git worktree at `~/.worktree/{project}/{branch}`
2. Opens a new tmux window (if tmux session exists)
3. Changes to the worktree directory
4. Automatically starts `claude`

## User Interaction

When the user requests worktree operations:

- **No arguments**: Ask what operation to perform (create/list/remove)
- **Branch name only**: Create worktree for that branch
- **"list" or "show"**: List existing worktrees
- **"remove" or "delete"**: Show worktrees and ask which to remove

## Notes

- Worktrees share the same `.git` directory, so commits made in any worktree are visible to all
- Each worktree has its own working directory and index
- Use `Ctrl+b n` / `Ctrl+b p` to switch between tmux windows (or your tmux prefix)
- If tmux is not running, the script still creates the worktree and shows the path
- tmux windows must be closed manually when removing worktrees
