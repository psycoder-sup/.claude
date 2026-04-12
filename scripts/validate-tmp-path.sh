#!/bin/bash
set -euo pipefail

input=$(cat)

file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // .tool_input.notebook_path // empty')

if [ -z "$file_path" ]; then
  exit 0
fi

case "$file_path" in
  /tmp|/tmp/*|/private/tmp|/private/tmp/*)
    jq -nc \
      --arg reason "Files under /tmp are blocked. Use .dev/tmp/ in the project root instead — it is gitignored and persists with the project. Create the directory if it does not exist." \
      '{
        hookSpecificOutput: {
          hookEventName: "PreToolUse",
          permissionDecision: "deny",
          permissionDecisionReason: $reason
        }
      }'
    exit 0
    ;;
esac

exit 0
