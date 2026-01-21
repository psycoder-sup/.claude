#!/bin/bash
# validate-git-command.sh
# PreToolUse hook to validate git commands before execution
# Blocks dangerous operations like force push to main/master

# Read JSON input from stdin
INPUT=$(cat)

# Extract the command from the tool input
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# If not a git command, allow it
if [[ ! "$COMMAND" =~ ^git[[:space:]] ]]; then
    exit 0
fi

# Block force push to main/master
if echo "$COMMAND" | grep -qE 'git\s+push\s+.*(-f|--force).*\s+(main|master)'; then
    echo '{"error": "Blocked: Force push to main/master is not allowed. Use a feature branch instead."}'
    exit 2
fi

if echo "$COMMAND" | grep -qE 'git\s+push\s+(-f|--force).*origin\s+(main|master)'; then
    echo '{"error": "Blocked: Force push to main/master is not allowed. Use a feature branch instead."}'
    exit 2
fi

# Block hard reset on main/master
if echo "$COMMAND" | grep -qE 'git\s+reset\s+--hard' && git branch --show-current 2>/dev/null | grep -qE '^(main|master)$'; then
    echo '{"error": "Warning: Hard reset on main/master branch. Consider using a feature branch."}'
    exit 2
fi

# Block deleting main/master branch
if echo "$COMMAND" | grep -qE 'git\s+branch\s+(-d|-D)\s+(main|master)'; then
    echo '{"error": "Blocked: Cannot delete main/master branch."}'
    exit 2
fi

# Allow the command
exit 0
