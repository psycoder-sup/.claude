#!/bin/bash
config_file="$HOME/.claude/statusline/statusline-config.txt"
if [ -f "$config_file" ]; then
  source "$config_file"
else
  SHOW_SESSION_ID=1 SHOW_DIRECTORY=1 SHOW_BRANCH=1 SHOW_MODEL=1
  SHOW_CONTEXT=1 SHOW_USAGE=1 SHOW_PROGRESS_BAR=1 SHOW_RESET_TIME=1
fi

input=$(cat)
session_id=$(echo "$input" | grep -o '"session_id":"[^"]*"' | head -1 | sed 's/"session_id":"//;s/"$//' | cut -c1-8)
current_dir_path=$(echo "$input" | grep -o '"current_dir":"[^"]*"' | head -1 | sed 's/"current_dir":"//;s/"$//')
current_dir=$(basename "$current_dir_path")
model_name=$(echo "$input" | grep -o '"display_name":"[^"]*"' | head -1 | sed 's/"display_name":"//;s/"$//' | sed 's/^\([A-Z]\)[a-z]* \([0-9.]*\).*/\1 \2/')
context_used=$(echo "$input" | grep -o '"used_percentage":[0-9.]*' | head -1 | sed 's/"used_percentage"://' | cut -d'.' -f1)

RESET=$'\033[0m'
DIM=$'\033[0;90m'
WHITE=$'\033[1;37m'
CYAN=$'\033[38;5;44m'

# Powerline round caps
PL_L=$'\xee\x82\xb6'
PL_R=$'\xee\x82\xb4'

# Pill: make_pill <cap_color_code> <bg_color_code> <fg_color_code> <text>
make_pill() {
  local cap_fg=$'\033[38;5;'"$1"'m'
  local bg=$'\033[48;5;'"$1"'m'
  local fg=$'\033[38;5;'"$2"'m'
  local text="$3"
  printf '%s' "${cap_fg}${PL_L}${bg}${fg} ${text} ${RESET}${cap_fg}${PL_R}${RESET}"
}

# Dot gradient: green -> red
DOT_1=$'\033[38;5;22m'
DOT_2=$'\033[38;5;28m'
DOT_3=$'\033[38;5;34m'
DOT_4=$'\033[38;5;76m'
DOT_5=$'\033[38;5;142m'
DOT_6=$'\033[38;5;178m'
DOT_7=$'\033[38;5;172m'
DOT_8=$'\033[38;5;166m'
DOT_9=$'\033[38;5;160m'
DOT_10=$'\033[38;5;124m'

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

# Line 1: pill badges
session_text=""
if [ "$SHOW_SESSION_ID" = "1" ] && [ -n "$session_id" ]; then
  session_text=$(make_pill 238 248 "$session_id")
fi

model_text=""
if [ "$SHOW_MODEL" = "1" ] && [ -n "$model_name" ]; then
  model_text=$(make_pill 141 16 "$model_name")
fi

dir_text=""
if [ "$SHOW_DIRECTORY" = "1" ] && [ -n "$current_dir" ]; then
  dir_text=$(make_pill 24 153 "$current_dir")
fi

branch_text=""
if [ "$SHOW_BRANCH" = "1" ]; then
  if git rev-parse --git-dir > /dev/null 2>&1; then
    branch=$(git branch --show-current 2>/dev/null)
    [ -n "$branch" ] && branch_text=$(make_pill 22 150 "$(printf '\xe2\x8e\x87') ${branch}")
  fi
fi

# Line 2: context | 5h | 7d
context_text=""
if [ "$SHOW_CONTEXT" = "1" ] && [ -n "$context_used" ] && [ "$context_used" -eq "$context_used" ] 2>/dev/null; then
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
if [ "$SHOW_USAGE" = "1" ]; then
  swift_result=$(swift "$HOME/.claude/statusline/fetch-claude-usage.swift" 2>/dev/null)

  if [ -n "$swift_result" ]; then
    util_5h=$(echo "$swift_result" | cut -d'|' -f1)
    resets_5h=$(echo "$swift_result" | cut -d'|' -f2)
    util_7d=$(echo "$swift_result" | cut -d'|' -f3)
    resets_7d=$(echo "$swift_result" | cut -d'|' -f4)

    if [ -n "$util_5h" ] && [ "$util_5h" != "ERROR" ]; then
      dot_color_5h=$(get_dot_color "$util_5h")
      dots_5h=$(build_dots "$util_5h")
      reset_5h_display=""
      [ "$SHOW_RESET_TIME" = "1" ] && reset_5h_display=$(format_reset_time "$resets_5h")
      usage_5h_text="${WHITE}5h ${dot_color_5h}${dots_5h} ${CYAN}${util_5h}%${DIM}${reset_5h_display}${RESET}"
    else
      usage_5h_text="${WHITE}5h ${DIM}○○○○○ ~${RESET}"
    fi

    if [ -n "$util_7d" ] && [ "$util_7d" != "ERROR" ]; then
      dot_color_7d=$(get_dot_color "$util_7d")
      dots_7d=$(build_dots "$util_7d")
      reset_7d_display=""
      if [ "$SHOW_RESET_TIME" = "1" ] && [ -n "$resets_7d" ] && [ "$resets_7d" != "null" ]; then
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
separator="${DIM} │ ${RESET}"

append_spaced() { local -n _ref=$1; _ref="${_ref:+$_ref }$2"; }
append_sep()    { local -n _ref=$1; _ref="${_ref:+$_ref$separator}$2"; }

# Line 1: pill badges, space separated
for part in "$session_text" "$model_text" "$dir_text" "$branch_text"; do
  [ -n "$part" ] && append_spaced line1 "$part"
done

# Line 2: context | 5h usage | 7d usage
for part in "$context_text" "$usage_5h_text" "$usage_7d_text"; do
  [ -n "$part" ] && append_sep line2 "$part"
done

printf "%s\n%s\n" "$line1" "$line2"
