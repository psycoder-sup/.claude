---
allowed-tools: Bash, AskUserQuestion
description: Squash merge a PR, pull main, and clean up worktree/tmux workspace
user-invocable: true
argument-name: pr_number
argument-description: PR number to squash merge
argument-required: true
---

Squash merge PR #$ARGUMENTS and clean up the associated worktree.

## Steps

1. Get PR details using `gh pr view $ARGUMENTS --json title,headRefName,state`
2. If the PR is not open, inform the user and stop.
3. Squash merge: `gh pr merge $ARGUMENTS --squash`
4. Switch to main if not already on it: `git checkout main`
5. Pull latest: `git pull origin main`
6. Use AskUserQuestion to ask the user which worktree/tmux workspace to close (suggest the PR branch name from step 1). If the user says none or skips, stop here.
7. Run `gw archive <branch-name>` with the branch name the user confirmed. This safely removes the worktree and tmux workspace (fails if uncommitted changes exist). If archive fails due to uncommitted changes, ask the user if they want to force remove with `gw remove <branch-name>` instead.
