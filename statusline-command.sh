#!/bin/bash

# Read JSON input from stdin
input=$(cat)

# Get data from JSON input
project_dir=$(echo "$input" | jq -r '.workspace.project_dir')
model_name=$(echo "$input" | jq -r '.model.display_name')
output_style=$(echo "$input" | jq -r '.output_style.name')

# Get the project name (basename of project directory)
project_name=$(basename "$project_dir")

# Get the git branch name (skip optional locks for performance)
cd "$project_dir" 2>/dev/null
branch=$(git -c core.useBuiltinFSMonitor=false --no-optional-locks branch --show-current 2>/dev/null)

# Get git status
git_status=""
if [ -n "$branch" ]; then
  # Get file counts from git status --porcelain
  status_output=$(git -c core.useBuiltinFSMonitor=false --no-optional-locks status --porcelain 2>/dev/null)

  staged=0
  modified=0
  untracked=0

  while IFS= read -r line; do
    [ -z "$line" ] && continue
    x="${line:0:1}"
    y="${line:1:1}"

    # Staged changes (index)
    case "$x" in
      [MADRC]) ((staged++)) ;;
    esac

    # Unstaged changes (worktree)
    case "$y" in
      [MD]) ((modified++)) ;;
    esac

    # Untracked files
    [ "$x" = "?" ] && ((untracked++))
  done <<< "$status_output"

  # Build file counts string
  counts=""
  [ $staged -gt 0 ] && counts="+$staged"
  [ $modified -gt 0 ] && counts="$counts ~$modified"
  [ $untracked -gt 0 ] && counts="$counts ?$untracked"
  counts="${counts# }"  # Trim leading space

  # Get ahead/behind info
  ahead_behind=""
  tracking=$(git -c core.useBuiltinFSMonitor=false --no-optional-locks rev-parse --abbrev-ref @{upstream} 2>/dev/null)
  if [ -n "$tracking" ]; then
    ab=$(git -c core.useBuiltinFSMonitor=false --no-optional-locks rev-list --left-right --count HEAD...@{upstream} 2>/dev/null)
    ahead=$(echo "$ab" | cut -f1)
    behind=$(echo "$ab" | cut -f2)
    [ "$ahead" -gt 0 ] 2>/dev/null && ahead_behind="↑$ahead"
    [ "$behind" -gt 0 ] 2>/dev/null && ahead_behind="$ahead_behind↓$behind"
  fi

  # Combine status
  if [ -n "$counts" ] || [ -n "$ahead_behind" ]; then
    git_status="$counts"
    [ -n "$counts" ] && [ -n "$ahead_behind" ] && git_status="$git_status "
    git_status="$git_status$ahead_behind"
  else
    git_status="✓"
  fi
fi

# Calculate context window percentage if available
context_info=""
usage=$(echo "$input" | jq '.context_window.current_usage')
if [ "$usage" != "null" ]; then
  current=$(echo "$usage" | jq '.input_tokens + .cache_creation_input_tokens + .cache_read_input_tokens')
  size=$(echo "$input" | jq '.context_window.context_window_size')
  pct=$((current * 100 / size))

  # Choose emoji based on percentage
  if [ $pct -lt 50 ]; then
    context_emoji="🟢"
  elif [ $pct -lt 75 ]; then
    context_emoji="🟡"
  else
    context_emoji="🔴"
  fi
  context_info=$(printf " %s %d%%" "$context_emoji" "$pct")
fi

# Color codes (will appear dimmed in status line)
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RESET='\033[0m'

# Build the colorful status line with emojis
if [ -n "$branch" ]; then
  printf "${CYAN}📁 %s${RESET} ${MAGENTA}🌿 %s %s${RESET}${YELLOW}%s${RESET} ${BLUE}🤖 %s${RESET}" \
    "$project_name" "$branch" "$git_status" "$context_info" "$model_name"
else
  printf "${CYAN}📁 %s${RESET}${YELLOW}%s${RESET} ${BLUE}🤖 %s${RESET}" \
    "$project_name" "$context_info" "$model_name"
fi
