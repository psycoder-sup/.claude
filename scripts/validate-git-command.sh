#!/bin/bash
# validate-git-command.sh
# PreToolUse hook to validate git commands before execution
# Blocks dangerous operations like force push to main/master

# Read JSON input from stdin
INPUT=$(cat)

# Extract the command from the tool input
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Normalize a subcommand: strip leading whitespace, env/sudo prefixes, and full git path
normalize_cmd() {
    local cmd="$1"

    # Strip leading whitespace
    cmd="${cmd#"${cmd%%[![:space:]]*}"}"

    # Strip common prefix commands (env, sudo, command, builtin)
    cmd=$(echo "$cmd" | sed -E 's/^(env|sudo|command|builtin)[[:space:]]+//')

    # Normalize full path to git binary
    cmd=$(echo "$cmd" | sed -E 's|^[/a-zA-Z0-9._-]*/git[[:space:]]|git |')

    echo "$cmd"
}

# Validate a single git subcommand
validate_git_command() {
    local cmd
    cmd=$(normalize_cmd "$1")

    # Skip non-git commands
    if [[ ! "$cmd" =~ ^git[[:space:]] ]]; then
        return 0
    fi

    # Block force push (--force or -f, and --force-with-lease) to main/master
    # Match "main" or "master" only as exact arguments (end of string or followed by space)
    if echo "$cmd" | grep -qE 'git[[:space:]]+push[[:space:]]+.*(-f|--force|--force-with-lease)' && \
       echo "$cmd" | grep -qE '(^|[[:space:]])(main|master)([[:space:]]|$)'; then
        echo '{"error": "Blocked: Force push to main/master is not allowed. Use a feature branch instead."}'
        exit 2
    fi

    # Block hard reset on main/master
    if echo "$cmd" | grep -qE 'git[[:space:]]+reset[[:space:]]+--hard' && git branch --show-current 2>/dev/null | grep -qE '^(main|master)$'; then
        echo '{"error": "Warning: Hard reset on main/master branch. Consider using a feature branch."}'
        exit 2
    fi

    # Block deleting main/master branch (exact match, not prefix like "main-feature")
    if echo "$cmd" | grep -qE 'git[[:space:]]+branch[[:space:]]+(-d|-D)[[:space:]]+(main|master)([[:space:]]|$)'; then
        echo '{"error": "Blocked: Cannot delete main/master branch."}'
        exit 2
    fi
}

# Split on &&, ||, ;, | and validate each subcommand
# Replace longer delimiters first to avoid double-splitting
SUBCMDS=$(echo "$COMMAND" | sed 's/&&/\n/g' | sed 's/||/\n/g' | sed 's/;/\n/g' | sed 's/|/\n/g')

while IFS= read -r subcmd; do
    validate_git_command "$subcmd"
done <<< "$SUBCMDS"

# Allow the command
exit 0
