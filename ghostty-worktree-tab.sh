#!/bin/bash

# Get current repo info
repo_root=$(git rev-parse --show-toplevel 2>/dev/null)
if [[ -z "$repo_root" ]]; then
    echo "Not in a git repository"
    exit 1
fi

repo_name=$(basename "$repo_root")

# Prompt for branch name
printf "Branch name: "
read -r branch_name

if [[ -z "$branch_name" ]]; then
    echo "Branch name required"
    exit 1
fi

# Create worktree as sibling directory
worktree_path="$(dirname "$repo_root")/${repo_name}-${branch_name}"

# Create the worktree with new branch
git worktree add "$worktree_path" -b "$branch_name"

if [[ $? -eq 0 ]]; then
    # Open new Ghostty tab and cd to worktree
    osascript <<EOF
tell application "System Events"
    tell process "ghostty"
        keystroke "t" using command down
        delay 0.3
        keystroke "cd ${worktree_path} && clear"
        key code 36
    end tell
end tell
EOF
    echo "Created worktree at: $worktree_path"
fi
