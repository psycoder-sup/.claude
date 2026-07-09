#!/bin/bash
config_file="$HOME/.claude/statusline/statusline-config.txt"
if [ -f "$config_file" ]; then
  source "$config_file"
else
  SHOW_SESSION_ID=1 SHOW_DIRECTORY=1 SHOW_BRANCH=1 SHOW_MODEL=1
  SHOW_CONTEXT=1 SHOW_USAGE=1 SHOW_PROGRESS_BAR=1 SHOW_RESET_TIME=1
  SHOW_CAVEMAN=1
fi

input=$(cat)

# Parse fields with jq (handles nested objects and absent fields cleanly).
# `// empty` makes absent fields produce no output instead of "null".
session_id=$(printf '%s' "$input" | jq -r '.session_id // empty' | cut -c1-8)
current_dir_path=$(printf '%s' "$input" | jq -r '.workspace.current_dir // .cwd // empty')
current_dir=$(basename "$current_dir_path")
model_display=$(printf '%s' "$input" | jq -r '.model.display_name // empty')
model_name=$(printf '%s' "$model_display" | sed 's/^\([A-Z]\)[a-z]* \([0-9.]*\).*/\1 \2/')
context_used=$(printf '%s' "$input" | jq -r '.context_window.used_percentage // 0' | cut -d'.' -f1)

# Rate limit fields (may be absent for free tier / before first API response).
util_5h=$(printf '%s' "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty' | cut -d'.' -f1)
resets_5h=$(printf '%s' "$input" | jq -r '.rate_limits.five_hour.resets_at // empty')
util_7d=$(printf '%s' "$input" | jq -r '.rate_limits.seven_day.used_percentage // empty' | cut -d'.' -f1)
resets_7d=$(printf '%s' "$input" | jq -r '.rate_limits.seven_day.resets_at // empty')

ESC=$'\033'
RESET=$'\033[0m'
DIM=$'\033[0;90m'
WHITE=$'\033[1;37m'
CYAN=$'\033[38;5;44m'

# Powerline round caps
PL_L=$'\xee\x82\xb6'
PL_R=$'\xee\x82\xb4'

# Visible (display-column) length of a string, stripping SGR escapes.
visible_len() {
  printf '%s' "$1" | awk '{ gsub(/\033\[[0-9;]*m/, ""); print length }'
}

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

# Caveman mode badge, mirrors the caveman plugin's own statusline script
# (src/hooks/caveman-statusline.sh) without depending on its plugin-cache
# path, which is versioned by a content hash and moves on plugin update.
caveman_text=""
if [ "$SHOW_CAVEMAN" = "1" ]; then
  caveman_config_dir="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
  caveman_flag="${caveman_config_dir}/.caveman-active"
  # Refuse symlinks: a local attacker could point the flag at a sensitive
  # file and have the statusline render its bytes to the terminal.
  if [ ! -L "$caveman_flag" ] && [ -f "$caveman_flag" ]; then
    caveman_mode=$(head -c 64 "$caveman_flag" 2>/dev/null | tr -d '\n\r' | tr '[:upper:]' '[:lower:]')
    caveman_mode=$(printf '%s' "$caveman_mode" | tr -cd 'a-z0-9-')
    case "$caveman_mode" in
      off|lite|full|ultra|wenyan-lite|wenyan|wenyan-full|wenyan-ultra|commit|review|compress)
        if [ -z "$caveman_mode" ] || [ "$caveman_mode" = "full" ]; then
          caveman_badge="CAVEMAN"
        else
          caveman_badge="CAVEMAN:$(printf '%s' "$caveman_mode" | tr '[:lower:]' '[:upper:]')"
        fi
        if [ "${CAVEMAN_STATUSLINE_SAVINGS:-1}" != "0" ]; then
          caveman_suffix_file="${caveman_config_dir}/.caveman-statusline-suffix"
          if [ -f "$caveman_suffix_file" ] && [ ! -L "$caveman_suffix_file" ]; then
            caveman_savings=$(head -c 64 "$caveman_suffix_file" 2>/dev/null | tr -d '\000-\037')
            [ -n "$caveman_savings" ] && caveman_badge="${caveman_badge} ${caveman_savings}"
          fi
        fi
        caveman_text=$(make_pill 172 16 "$caveman_badge")
        ;;
    esac
  fi
fi

# Line 2: context | 5h | 7d
context_text=""
if [ "$SHOW_CONTEXT" = "1" ]; then
  if [ -n "$context_used" ] && [ "$context_used" -eq "$context_used" ] 2>/dev/null; then
    ctx_dot_color=$(get_dot_color "$context_used")
    ctx_dots=$(build_dots "$context_used")
    context_text="${WHITE}Ctx ${ctx_dot_color}${ctx_dots} ${CYAN}${context_used}%${RESET}"
  else
    ctx_dot_color=$(get_dot_color 0)
    ctx_dots=$(build_dots 0)
    context_text="${WHITE}Ctx ${ctx_dot_color}${ctx_dots} ${CYAN}0%${RESET}"
  fi
fi

# resets_at is Unix epoch seconds; format with the system `date` tool.
format_reset_time() {
  local epoch="$1" fmt="$2"
  [ -z "$epoch" ] && return
  [ "$epoch" = "null" ] && return
  [ "$epoch" -eq "$epoch" ] 2>/dev/null || return
  local out
  out=$(date -r "$epoch" "+${fmt}" 2>/dev/null) || return
  [ -n "$out" ] && echo " @${out}"
}

usage_5h_text=""
usage_7d_text=""
if [ "$SHOW_USAGE" = "1" ]; then
  if [ -n "$util_5h" ]; then
    dot_color_5h=$(get_dot_color "$util_5h")
    dots_5h=$(build_dots "$util_5h")
    reset_5h_display=""
    [ "$SHOW_RESET_TIME" = "1" ] && reset_5h_display=$(format_reset_time "$resets_5h" "%H:%M")
    usage_5h_text="${WHITE}5h ${dot_color_5h}${dots_5h} ${CYAN}${util_5h}%${DIM}${reset_5h_display}${RESET}"
  else
    usage_5h_text="${WHITE}5h ${DIM}○○○○○ ~${RESET}"
  fi

  if [ -n "$util_7d" ]; then
    dot_color_7d=$(get_dot_color "$util_7d")
    dots_7d=$(build_dots "$util_7d")
    reset_7d_display=""
    [ "$SHOW_RESET_TIME" = "1" ] && reset_7d_display=$(format_reset_time "$resets_7d" "%m/%d")
    usage_7d_text="${WHITE}7d ${dot_color_7d}${dots_7d} ${CYAN}${util_7d}%${DIM}${reset_7d_display}${RESET}"
  else
    usage_7d_text="${WHITE}7d ${DIM}○○○○○ ~${RESET}"
  fi
fi

line1=""
line2=""
separator="${DIM} │ ${RESET}"

line1_pills=("$session_text" "$model_text" "$dir_text" "$branch_text" "$caveman_text")
line1_pill_lens=()
for p in "${line1_pills[@]}"; do
  if [ -n "$p" ]; then
    line1_pill_lens+=( "$(visible_len "$p")" )
  else
    line1_pill_lens+=( 0 )
  fi
done

build_line1() {
  local start=$1 i p
  line1=""
  for ((i=start; i<${#line1_pills[@]}; i++)); do
    p="${line1_pills[$i]}"
    [ -n "$p" ] && line1="${line1:+$line1 }$p"
  done
}
build_line1 0

for part in "$context_text" "$usage_5h_text" "$usage_7d_text"; do
  [ -n "$part" ] && line2="${line2:+$line2$separator}$part"
done

printf "%s\n%s\n" "$line1" "$line2"
