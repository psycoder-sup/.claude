---
name: worktree
description: This skill should be used when the user asks to "create a worktree", "set up a worktree workspace", "work on multiple branches", "manage worktrees", "list worktrees", "remove worktree", or mentions needing to work on multiple branches simultaneously with tmux integration.
model: haiku
user-invocable: true
allowed-tools: AskUserQuestion, Bash(~/.claude/skills/worktree/scripts/worktree.sh:*), Bash(~/.claude/skills/worktree/scripts/check-pr-merged.sh:*), Bash(git branch:*), Bash(git worktree list:*), Bash(gh pr view:*)
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
| Remove | `remove <name>` | Removes worktree and closes tmux window |

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

### Remove Worktree Workflow

When removing a worktree, follow these steps:

1. **Check PR status**: Run `~/.claude/skills/worktree/scripts/check-pr-merged.sh <branch-name>` to check if the branch's PR has been merged

2. **Confirm removal if not merged**: If the PR is NOT merged (or has no PR), ask the user to confirm before proceeding:
   ```json
   {
     "questions": [{
       "question": "The PR for '<branch-name>' is not merged (or has no PR). Remove the worktree anyway?",
       "header": "Worktree",
       "multiSelect": false,
       "options": [
         {
           "label": "No, keep the worktree",
           "description": "Cancel removal and keep working on this branch"
         },
         {
           "label": "Yes, remove the worktree",
           "description": "Remove worktree but branch will still exist"
         }
       ]
     }]
   }
   ```
   If user selects "No", stop here. If PR is merged, skip this step.

3. **Remove worktree**: Run `~/.claude/skills/worktree/scripts/worktree.sh remove <name>` to remove the worktree directory and close the tmux window

4. **Ask about branch deletion**: Use `AskUserQuestion` to ask the user if they want to delete the local branch, including the PR merge status in the question:

   **If PR is merged:**
   ```json
   {
     "questions": [{
       "question": "The PR for '<branch-name>' has been merged. Delete the local branch?",
       "header": "Branch",
       "multiSelect": false,
       "options": [
         {
           "label": "Yes, delete the branch (Recommended)",
           "description": "Branch is merged, safe to delete"
         },
         {
           "label": "No, keep the branch",
           "description": "Keep the local branch for reference"
         }
       ]
     }]
   }
   ```

   **If PR is not merged or has no PR:**
   ```json
   {
     "questions": [{
       "question": "Delete the local branch '<branch-name>'?",
       "header": "Branch",
       "multiSelect": false,
       "options": [
         {
           "label": "No, keep the branch",
           "description": "Keep the local branch for future use"
         },
         {
           "label": "Yes, delete the branch",
           "description": "Delete the local branch (can be recovered from remote if pushed)"
         }
       ]
     }]
   }
   ```

5. **Delete branch if confirmed**: If user selects "Yes", run `git branch -d <branch-name>`
   - If the branch has unmerged changes, inform the user and offer to force delete with `git branch -D <branch-name>`

## Notes

- Worktrees share the same `.git` directory, so commits made in any worktree are visible to all
- Each worktree has its own working directory and index
- Use `Ctrl+b n` / `Ctrl+b p` to switch between tmux windows (or your tmux prefix)
- If tmux is not running, the script still creates the worktree and shows the path
