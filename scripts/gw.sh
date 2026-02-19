#!/usr/bin/env bash
# gw - Create git worktree in ~/.worktrees and open tmux window
#
# Optional gw.json in the repo root can define lifecycle hooks:
#   { "start": ["npm install", ...], "archive": ["rm -rf node_modules", ...] }
# Hook commands receive GW_SOURCE (main repo root) and GW_TARGET (worktree path) as env vars.

set -e

usage() {
  echo "Usage: gw <branch> [-d] [prompt]"
  echo "  gw feature-foo              Create worktree + tmux window"
  echo "  gw feature-foo \"prompt\"      Create worktree + tmux window + run claude"
  echo "  gw feature-foo -d           Remove worktree + tmux window"
  echo "  gw -l                       List worktrees"
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
repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || {
  echo "Not in a git repository"
  exit 1
}
repo_name=$(basename "$repo_root")

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

# Run start hooks from gw.json if present
gw_config="$repo_root/gw.json"
if [ -f "$gw_config" ]; then
  export GW_SOURCE="$repo_root"
  export GW_TARGET="$wt_path"
  while IFS= read -r cmd; do
    echo "[gw] Running: $cmd"
    (cd "$wt_path" && sh -c "$cmd")
  done < <(python3 -c "import json,sys;[print(c)for c in json.load(open(sys.argv[1])).get('start',[])]" "$gw_config")
fi

# Open tmux window with dev layout or just print path
if [ -n "$TMUX" ]; then
  pane0=$(tmux new-window -c "$wt_path" -n "$repo_name/$branch" -P -F '#{pane_id}')

  # 4-pane layout: yazi | claude | lazygit, terminal below
  tmux split-window -t "$pane0" -h -c "$wt_path" -l 40 'lazygit'
  tmux split-window -t "$pane0" -v -c "$wt_path" -l 16
  if [ -n "$2" ]; then
    export GW_PROMPT="$2"
    claude_pane=$(tmux split-window -t "$pane0" -h -c "$wt_path" -p 50 -P -F '#{pane_id}' 'claude "$GW_PROMPT"')
  else
    claude_pane=$(tmux split-window -t "$pane0" -h -c "$wt_path" -p 50 -P -F '#{pane_id}' 'claude')
  fi
  tmux send-keys -t "$pane0" 'yazi' Enter
  tmux select-pane -t "$claude_pane"
else
  echo "Worktree created at: $wt_path"
  echo "Not in tmux — cd into it manually:"
  echo "  cd $wt_path"
fi
