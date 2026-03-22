#!/usr/bin/env bash
# gw-cmux - Create git worktree in ~/.worktrees and open cmux workspace
#
# Optional gw.json in the repo root can define lifecycle hooks:
#   { "start": ["npm install", ...], "archive": ["rm -rf node_modules", ...] }
# Hook commands receive GW_SOURCE (main repo root) and GW_TARGET (worktree path) as env vars.

set -e

usage() {
  echo "Usage: gw-cmux <command> [options]"
  echo ""
  echo "Commands:"
  echo "  add <branch>        Create worktree + cmux workspace"
  echo "  list                List worktrees"
  echo "  archive <branch>    Run archive hooks + remove worktree + cmux workspace"
  echo "  remove <branch>     Force remove worktree + cmux workspace (ignores uncommitted changes)"
}

run_hooks() {
  local config="$1" hook="$2"
  [ -f "$config" ] || return 0
  [ -d "$wt_path" ] || { echo "[gw-cmux] Error: $wt_path does not exist"; return 1; }
  export GW_SOURCE="$repo_root"
  export GW_TARGET="$wt_path"
  while IFS= read -r cmd; do
    echo "[gw-cmux] Running: $cmd"
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
}

cmd_add() {
  local branch="$1"
  [ -z "$branch" ] && { usage; exit 1; }

  resolve_repo
  resolve_worktree "$branch"

  # Create worktree: use existing branch if found, otherwise create new
  if git show-ref --verify --quiet "refs/remotes/origin/$branch" ||
     git show-ref --verify --quiet "refs/heads/$branch"; then
    git worktree add "$wt_path" "$branch"
  else
    git worktree add "$wt_path" -b "$branch"
  fi

  # Create cmux workspace with worktree as cwd
  local ws_ref s_yazi s_lazygit s_terminal s_claude
  ws_ref=$(cmux new-workspace --cwd "$wt_path" | awk '{print $2}')

  cmux rename-workspace --workspace "$ws_ref" "$repo_name/$safe_branch"

  # Get initial surface and pane refs
  s_yazi=$(cmux list-pane-surfaces --workspace "$ws_ref" | awk '{print $2}')
  local p_yazi
  p_yazi=$(cmux list-panes --workspace "$ws_ref" | awk '{print $2}')

  # Layout: [yazi|lazygit] | claude (top), terminal (full bottom)

  # Split bottom for terminal (full width)
  s_terminal=$(cmux new-split down --workspace "$ws_ref" --surface "$s_yazi" | awk '{print $2}')

  # Split top right for claude
  s_claude=$(cmux new-split right --workspace "$ws_ref" --surface "$s_yazi" | awk '{print $2}')

  # Add lazygit as a tab in the yazi pane
  s_lazygit=$(cmux new-surface --workspace "$ws_ref" --pane "$p_yazi" | awk '{print $2}')

  # Label tabs
  cmux rename-tab --workspace "$ws_ref" --surface "$s_yazi" "yazi"
  cmux rename-tab --workspace "$ws_ref" --surface "$s_claude" "claude"
  cmux rename-tab --workspace "$ws_ref" --surface "$s_lazygit" "lazygit"
  cmux rename-tab --workspace "$ws_ref" --surface "$s_terminal" "terminal"

  # Launch apps
  cmux send --workspace "$ws_ref" --surface "$s_lazygit" "lazygit"
  cmux send-key --workspace "$ws_ref" --surface "$s_lazygit" Enter
  cmux send --workspace "$ws_ref" --surface "$s_claude" "claude"
  cmux send-key --workspace "$ws_ref" --surface "$s_claude" Enter
  cmux send --workspace "$ws_ref" --surface "$s_yazi" "yazi"
  cmux send-key --workspace "$ws_ref" --surface "$s_yazi" Enter

  # Run start hooks from gw.json in the terminal pane
  local config="$repo_root/gw.json"
  if [ -f "$config" ]; then
    cmux send --workspace "$ws_ref" --surface "$s_terminal" "export GW_SOURCE=$(printf '%q' "$repo_root") GW_TARGET=$(printf '%q' "$wt_path")"
    cmux send-key --workspace "$ws_ref" --surface "$s_terminal" Enter
    while IFS= read -r cmd; do
      cmux send --workspace "$ws_ref" --surface "$s_terminal" "$cmd"
      cmux send-key --workspace "$ws_ref" --surface "$s_terminal" Enter
    done < <(python3 -c "import json,sys;[print(c)for c in json.load(open(sys.argv[1])).get('start',[])]" "$config")
  fi

  echo "[gw-cmux] Workspace created: $repo_name/$safe_branch ($ws_ref)"
  echo "[gw-cmux] Worktree path: $wt_path"
}

close_cmux_workspace() {
  local ws_match
  ws_match=$(cmux find-window "$repo_name/$safe_branch" 2>/dev/null | head -1 | awk '{print $1}')
  if [ -n "$ws_match" ]; then
    cmux close-workspace --workspace "$ws_match"
    echo "[gw-cmux] Closed cmux workspace: $repo_name/$safe_branch"
  else
    echo "[gw-cmux] No cmux workspace found for: $repo_name/$safe_branch"
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
  echo "[gw-cmux] Removed worktree: $wt_path"
  close_cmux_workspace
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
  echo "[gw-cmux] Force removed worktree: $wt_path"
  close_cmux_workspace
}

case "${1:-}" in
  add)     shift; cmd_add "$1" ;;
  list)    cmd_list ;;
  archive) shift; cmd_archive "$1" ;;
  remove)  shift; cmd_remove "$1" ;;
  *)       usage; exit 1 ;;
esac
