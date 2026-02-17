#!/usr/bin/env bash
# gw - Create git worktree in ~/.worktrees and open tmux window

set -e

usage() {
  echo "Usage: gw <branch> [-d]"
  echo "  gw feature-foo      Create worktree + tmux window"
  echo "  gw feature-foo -d   Remove worktree + tmux window"
  echo "  gw -l               List worktrees"
}

if [ -z "$1" ]; then
  usage
  exit 1
fi

if [ "$1" = "-l" ]; then
  git worktree list
  exit 0
fi

branch="$1"
repo_name=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)") || {
  echo "Not in a git repository"
  exit 1
}

wt_path="$HOME/.worktrees/$repo_name/$branch"

# Remove mode
if [ "$2" = "-d" ]; then
  git worktree remove "$wt_path" 2>/dev/null && echo "Removed worktree: $wt_path" || echo "Failed to remove worktree"
  if [ -n "$TMUX" ]; then
    tmux kill-window -t "$repo_name/$branch" 2>/dev/null || true
  fi
  exit 0
fi

# Create worktree (try new branch first, fall back to existing)
git worktree add "$wt_path" -b "$branch" 2>/dev/null || git worktree add "$wt_path" "$branch"

# Open tmux window or just print path
if [ -n "$TMUX" ]; then
  tmux new-window -c "$wt_path" -n "$repo_name/$branch"
else
  echo "Worktree created at: $wt_path"
  echo "Not in tmux — cd into it manually:"
  echo "  cd $wt_path"
fi
