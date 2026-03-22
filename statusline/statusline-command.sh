#!/bin/bash
config_file="$HOME/.claude/statusline/statusline-config.txt"
if [ -f "$config_file" ]; then
  source "$config_file"
  show_session=$SHOW_SESSION_ID
  show_dir=$SHOW_DIRECTORY
  show_branch=$SHOW_BRANCH
  show_model=$SHOW_MODEL
  show_context=$SHOW_CONTEXT
  show_usage=$SHOW_USAGE
  show_bar=$SHOW_PROGRESS_BAR
  show_reset=$SHOW_RESET_TIME
else
  show_session=1
  show_dir=1
  show_branch=1
  show_model=1
  show_context=1
  show_usage=1
  show_bar=1
  show_reset=1
fi

input=$(cat)
session_id=$(echo "$input" | grep -o '"session_id":"[^"]*"' | head -1 | sed 's/"session_id":"//;s/"$//' | cut -c1-8)
current_dir_path=$(echo "$input" | grep -o '"current_dir":"[^"]*"' | head -1 | sed 's/"current_dir":"//;s/"$//')
current_dir=$(basename "$current_dir_path")
model_name=$(echo "$input" | grep -o '"display_name":"[^"]*"' | head -1 | sed 's/"display_name":"//;s/"$//')
context_used=$(echo "$input" | grep -o '"used_percentage":[0-9.]*' | head -1 | sed 's/"used_percentage"://' | cut -d'.' -f1)
BLUE=$'\033[0;34m'
GREEN=$'\033[0;32m'
GRAY=$'\033[0;90m'
YELLOW=$'\033[0;33m'
RESET=$'\033[0m'

WHITE=$'\033[1;37m'
CYAN=$'\033[38;5;44m'
DIM=$'\033[0;90m'

# Dot gradient: green → red (shared by all indicators)
DOT_1=$'\033[38;5;22m'    # dark green
DOT_2=$'\033[38;5;28m'    # soft green
DOT_3=$'\033[38;5;34m'    # medium green
DOT_4=$'\033[38;5;76m'    # bright green
DOT_5=$'\033[38;5;142m'   # olive/yellow-green
DOT_6=$'\033[38;5;178m'   # muted yellow
DOT_7=$'\033[38;5;172m'   # yellow-orange
DOT_8=$'\033[38;5;166m'   # darker orange
DOT_9=$'\033[38;5;160m'   # dark red
DOT_10=$'\033[38;5;124m'  # deep red

# Build components (without separators)
session_text=""
if [ "$show_session" = "1" ] && [ -n "$session_id" ]; then
  session_text="${GRAY}${session_id}${RESET}"
fi

dir_text=""
if [ "$show_dir" = "1" ]; then
  dir_text="${BLUE}${current_dir}${RESET}"
fi

branch_text=""
if [ "$show_branch" = "1" ]; then
  if git rev-parse --git-dir > /dev/null 2>&1; then
    branch=$(git branch --show-current 2>/dev/null)
    [ -n "$branch" ] && branch_text="${GREEN}⎇ ${branch}${RESET}"
  fi
fi

PURPLE=$'\033[38;5;141m'

model_text=""
if [ "$show_model" = "1" ] && [ -n "$model_name" ]; then
  model_text="${PURPLE}${model_name}${RESET}"
fi

# Build dot indicator: filled ● for used portion, empty ○ for remaining (5 dots)
build_dots() {
  local pct=$1 total=5
  local filled=$(( (pct * total + 50) / 100 ))
  [ "$filled" -lt 0 ] && filled=0
  [ "$filled" -gt "$total" ] && filled=$total
  local empty=$((total - filled))
  local dots=""
  local i=0
  while [ $i -lt $filled ]; do dots="${dots}●"; i=$((i + 1)); done
  i=0
  while [ $i -lt $empty ]; do dots="${dots}○"; i=$((i + 1)); done
  echo "$dots"
}

# Dot color by percentage (higher = more red)
get_dot_color() {
  local pct=$1
  if [ "$pct" -le 10 ]; then echo "$DOT_1"
  elif [ "$pct" -le 20 ]; then echo "$DOT_2"
  elif [ "$pct" -le 30 ]; then echo "$DOT_3"
  elif [ "$pct" -le 40 ]; then echo "$DOT_4"
  elif [ "$pct" -le 50 ]; then echo "$DOT_5"
  elif [ "$pct" -le 60 ]; then echo "$DOT_6"
  elif [ "$pct" -le 70 ]; then echo "$DOT_7"
  elif [ "$pct" -le 80 ]; then echo "$DOT_8"
  elif [ "$pct" -le 90 ]; then echo "$DOT_9"
  else echo "$DOT_10"
  fi
}

context_text=""
if [ "$show_context" = "1" ] && [ -n "$context_used" ] && [ "$context_used" -eq "$context_used" ] 2>/dev/null; then
  ctx_dot_color=$(get_dot_color "$context_used")
  ctx_dots=$(build_dots "$context_used")
  context_text="${WHITE}Ctx ${ctx_dot_color}${ctx_dots} ${CYAN}${context_used}%${RESET}"
fi

format_reset_time() {
  local resets_at="$1"
  if [ -n "$resets_at" ] && [ "$resets_at" != "null" ]; then
    local iso_time=$(echo "$resets_at" | sed 's/\.[0-9]*Z$//')
    local epoch=$(date -ju -f "%Y-%m-%dT%H:%M:%S" "$iso_time" "+%s" 2>/dev/null)
    if [ -n "$epoch" ]; then
      local reset_time=$(date -r "$epoch" "+%H:%M" 2>/dev/null)
      [ -n "$reset_time" ] && echo " @${reset_time}"
    fi
  fi
}

usage_5h_text=""
usage_7d_text=""
if [ "$show_usage" = "1" ]; then
  swift_result=$(swift "$HOME/.claude/statusline/fetch-claude-usage.swift" 2>/dev/null)

  if [ $? -eq 0 ] && [ -n "$swift_result" ]; then
    util_5h=$(echo "$swift_result" | cut -d'|' -f1)
    resets_5h=$(echo "$swift_result" | cut -d'|' -f2)
    util_7d=$(echo "$swift_result" | cut -d'|' -f3)
    resets_7d=$(echo "$swift_result" | cut -d'|' -f4)

    if [ -n "$util_5h" ] && [ "$util_5h" != "ERROR" ]; then
      dot_color_5h=$(get_dot_color "$util_5h")
      dots_5h=$(build_dots "$util_5h")
      reset_5h_display=""
      [ "$show_reset" = "1" ] && reset_5h_display=$(format_reset_time "$resets_5h")
      usage_5h_text="${WHITE}5h ${dot_color_5h}${dots_5h} ${CYAN}${util_5h}%${DIM}${reset_5h_display}${RESET}"
    else
      usage_5h_text="${WHITE}5h ${DIM}○○○○○ ~${RESET}"
    fi

    if [ -n "$util_7d" ] && [ "$util_7d" != "ERROR" ]; then
      dot_color_7d=$(get_dot_color "$util_7d")
      dots_7d=$(build_dots "$util_7d")
      reset_7d_display=""
      if [ "$show_reset" = "1" ] && [ -n "$resets_7d" ] && [ "$resets_7d" != "null" ]; then
        iso_7d=$(echo "$resets_7d" | sed 's/\.[0-9]*[+-].*$//')
        epoch_7d=$(date -ju -f "%Y-%m-%dT%H:%M:%S" "$iso_7d" "+%s" 2>/dev/null)
        [ -n "$epoch_7d" ] && reset_7d_display=" @$(date -r "$epoch_7d" "+%m/%d" 2>/dev/null)"
      fi
      usage_7d_text="${WHITE}7d ${dot_color_7d}${dots_7d} ${CYAN}${util_7d}%${DIM}${reset_7d_display}${RESET}"
    else
      usage_7d_text="${WHITE}7d ${DIM}○○○○○ ~${RESET}"
    fi
  else
    usage_5h_text="${WHITE}5h ${DIM}○○○○○ ~${RESET}"
    usage_7d_text="${WHITE}7d ${DIM}○○○○○ ~${RESET}"
  fi
fi

line1=""
line2=""
separator="${GRAY} │ ${RESET}"

# Line 1: session | model | project root | branch
[ -n "$session_text" ] && line1="${session_text}"

if [ -n "$model_text" ]; then
  [ -n "$line1" ] && line1="${line1}${separator}"
  line1="${line1}${model_text}"
fi

if [ -n "$dir_text" ]; then
  [ -n "$line1" ] && line1="${line1}${separator}"
  line1="${line1}${dir_text}"
fi

if [ -n "$branch_text" ]; then
  [ -n "$line1" ] && line1="${line1}${separator}"
  line1="${line1}${branch_text}"
fi

# Line 2: context | 5h usage | 7d usage
if [ -n "$context_text" ]; then
  line2="${context_text}"
fi

if [ -n "$usage_5h_text" ]; then
  [ -n "$line2" ] && line2="${line2}${separator}"
  line2="${line2}${usage_5h_text}"
fi

if [ -n "$usage_7d_text" ]; then
  [ -n "$line2" ] && line2="${line2}${separator}"
  line2="${line2}${usage_7d_text}"
fi

printf "%s\n%s\n" "$line1" "$line2"