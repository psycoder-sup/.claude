---
name: workspace
description: This skill should be used when the user asks to "create a worktree", "new workspace", "open workspace", "remove workspace", "archive workspace", "list worktrees", "clean up workspace", or needs to manage git worktrees.
allowed-tools: Bash(git:*)
user-invocable: true
---

# Workspace Skill

Manage git worktrees using `git worktree` commands. Worktrees are stored at `~/.worktrees/<repo>/<branch>`.

## Arguments

```
$ARGUMENTS
```

Parse `$ARGUMENTS` into a **command** (`add`, `list`, `archive`, `remove`) and an optional **branch name**. If no command given, ask the user.

## Commands

### add `<branch>`

Create a new worktree. Branch names with `/` are sanitized to `-` in the path.

```bash
# Determine repo info
repo_root=$(git rev-parse --show-toplevel)
repo_name=$(basename "$repo_root")
safe_branch="${branch//\//-}"
wt_path="$HOME/.worktrees/$repo_name/$safe_branch"

# Create worktree (skip if already exists)
if [ -d "$wt_path" ]; then
  echo "Worktree already exists: $wt_path"
elif git show-ref --verify --quiet "refs/remotes/origin/$branch" || \
     git show-ref --verify --quiet "refs/heads/$branch"; then
  git worktree add "$wt_path" "$branch"
else
  git worktree add "$wt_path" -b "$branch"
fi
```

### list

```bash
git worktree list
```

### archive `<branch>`

Safe removal — fails if there are uncommitted changes.

```bash
repo_root=$(git rev-parse --show-toplevel)
repo_name=$(basename "$repo_root")
safe_branch="${branch//\//-}"
wt_path="$HOME/.worktrees/$repo_name/$safe_branch"

git worktree remove "$wt_path"
```

### remove `<branch>`

Force removal — discards uncommitted changes.

```bash
repo_root=$(git rev-parse --show-toplevel)
repo_name=$(basename "$repo_root")
safe_branch="${branch//\//-}"
wt_path="$HOME/.worktrees/$repo_name/$safe_branch"

git worktree remove --force "$wt_path"
```

## When to Use Archive vs Remove

- **archive** — safe removal; aborts if there are uncommitted changes
- **remove** — force removal; use when you want to discard uncommitted work
