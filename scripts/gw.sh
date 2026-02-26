#!/usr/bin/env bash
# gw - Create git worktree in ~/.worktrees and open tmux window
#
# Optional gw.json in the repo root can define lifecycle hooks:
#   { "start": ["npm install", ...], "archive": ["rm -rf node_modules", ...] }
# Hook commands receive GW_SOURCE (main repo root) and GW_TARGET (worktree path) as env vars.

set -e

usage() {
  echo "Usage: gw <command> [options]"
  echo ""
  echo "Commands:"
  echo "  create <branch> [prompt]    Create worktree + tmux window"
  echo "  list                        List worktrees"
  echo "  archive <branch>            Run archive hooks + remove worktree + tmux window"
  echo "  remove <branch>             Force remove worktree + tmux window (ignores uncommitted changes)"
}

# Run lifecycle hooks from gw.json
# Usage: run_hooks <config_file> <hook_name>
run_hooks() {
  local config="$1" hook="$2"
  [ -f "$config" ] || return 0
  [ -d "$wt_path" ] || { echo "[gw] Error: $wt_path does not exist"; return 1; }
  export GW_SOURCE="$repo_root"
  export GW_TARGET="$wt_path"
  while IFS= read -r cmd; do
    echo "[gw] Running: $cmd"
    (cd "$wt_path" && sh -c "$cmd")
  done < <(python3 -c "import json,sys;[print(c)for c in json.load(open(sys.argv[1])).get(sys.argv[2],[])]" "$config" "$hook")
}

resolve_repo() {
  repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || {
    echo "Not in a git repository"
    exit 1
  }
  repo_name=$(basename "$repo_root")
}

resolve_worktree() {
  local branch="$1"
  safe_branch="${branch//\//-}"
  wt_path="$HOME/.worktrees/$repo_name/$safe_branch"
  win_name="$repo_name/$safe_branch"
}

cmd_create() {
  local branch="$1" prompt="$2"
  [ -z "$branch" ] && { usage; exit 1; }

  resolve_repo
  resolve_worktree "$branch"

  # Create worktree (try new branch first, fall back to existing)
  git worktree add "$wt_path" -b "$branch" 2>/dev/null || git worktree add "$wt_path" "$branch"

  # Run start hooks from gw.json if present
  run_hooks "$repo_root/gw.json" "start"

  # Open tmux window with dev layout or just print path
  if [ -n "$TMUX" ]; then
    pane0=$(tmux new-window -c "$wt_path" -n "$win_name" -P -F '#{pane_id}')

    # 4-pane layout: yazi | claude | lazygit, terminal below
    tmux split-window -t "$pane0" -h -c "$wt_path" -l 40 'lazygit'
    tmux split-window -t "$pane0" -v -c "$wt_path" -l 16
    claude_cmd="claude"
    [ -n "$prompt" ] && claude_cmd="claude $(printf '%q' "$prompt")"
    claude_pane=$(tmux split-window -t "$pane0" -h -c "$wt_path" -p 50 -P -F '#{pane_id}' "$claude_cmd")
    tmux send-keys -t "$pane0" 'yazi' Enter
    tmux select-pane -t "$claude_pane"
  else
    echo "Worktree created at: $wt_path"
    echo "Not in tmux — cd into it manually:"
    echo "  cd $wt_path"
  fi
}

cmd_list() {
  resolve_repo
  git worktree list
}

cmd_archive() {
  local branch="$1"
  [ -z "$branch" ] && { usage; exit 1; }

  resolve_repo
  resolve_worktree "$branch"

  run_hooks "$repo_root/gw.json" "archive"
  if ! git worktree remove "$wt_path"; then
    echo "Failed to remove worktree (there may be uncommitted changes)"
    exit 1
  fi
  echo "Removed worktree: $wt_path"
  if [ -n "$TMUX" ]; then
    tmux kill-window -t "$win_name" 2>/dev/null || true
  fi
}

cmd_remove() {
  local branch="$1"
  [ -z "$branch" ] && { usage; exit 1; }

  resolve_repo
  resolve_worktree "$branch"

  run_hooks "$repo_root/gw.json" "archive"
  if ! git worktree remove --force "$wt_path"; then
    echo "Failed to force remove worktree"
    exit 1
  fi
  echo "Force removed worktree: $wt_path"
  if [ -n "$TMUX" ]; then
    tmux kill-window -t "$win_name" 2>/dev/null || true
  fi
}

case "${1:-}" in
  create)  shift; cmd_create "$@" ;;
  list)    cmd_list ;;
  archive) shift; cmd_archive "$1" ;;
  remove)  shift; cmd_remove "$1" ;;
  *)       usage; exit 1 ;;
esac
