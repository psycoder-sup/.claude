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
  # Check for uncommitted changes
  if ! git -c core.useBuiltinFSMonitor=false --no-optional-locks diff --quiet 2>/dev/null; then
    git_status="✨"  # Modified files
  elif ! git -c core.useBuiltinFSMonitor=false --no-optional-locks diff --cached --quiet 2>/dev/null; then
    git_status="✅"  # Staged files
  else
    git_status="✓"   # Clean
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
