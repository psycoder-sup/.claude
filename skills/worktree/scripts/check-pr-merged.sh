#!/bin/bash
# Usage: check-pr-merged.sh <branch-name>
# Exit codes: 0 = merged, 1 = not merged/no PR, 2 = error
# Output: JSON with status info

BRANCH="$1"

if [[ -z "$BRANCH" ]]; then
    echo '{"error": "No branch name provided"}'
    exit 2
fi

# Get PR info for the branch
PR_INFO=$(gh pr list --head "$BRANCH" --state all --json number,state,mergedAt --limit 1 2>/dev/null)

if [[ -z "$PR_INFO" || "$PR_INFO" == "[]" ]]; then
    echo '{"status": "no_pr", "branch": "'"$BRANCH"'"}'
    exit 1
fi

# Parse the result
STATE=$(echo "$PR_INFO" | jq -r '.[0].state')
MERGED_AT=$(echo "$PR_INFO" | jq -r '.[0].mergedAt')
PR_NUMBER=$(echo "$PR_INFO" | jq -r '.[0].number')

if [[ "$STATE" == "MERGED" ]]; then
    echo '{"status": "merged", "branch": "'"$BRANCH"'", "pr": '"$PR_NUMBER"', "mergedAt": "'"$MERGED_AT"'"}'
    exit 0
else
    echo '{"status": "'"$(echo $STATE | tr '[:upper:]' '[:lower:]')"'", "branch": "'"$BRANCH"'", "pr": '"$PR_NUMBER"'}'
    exit 1
fi
