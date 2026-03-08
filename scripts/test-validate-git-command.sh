#!/bin/bash
# test-validate-git-command.sh
# Test suite for validate-git-command.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$SCRIPT_DIR/validate-git-command.sh"

PASS=0
FAIL=0
TOTAL=0

test_cmd() {
    local desc="$1"
    local cmd="$2"
    local expect="$3"  # "allow" or "block"
    ((TOTAL++))

    result=$(echo "{\"tool_input\":{\"command\":\"$cmd\"}}" | bash "$SCRIPT" 2>/dev/null)
    code=$?

    if [[ "$expect" == "block" && $code -eq 2 ]]; then
        echo "  PASS: $desc"
        ((PASS++))
    elif [[ "$expect" == "allow" && $code -eq 0 ]]; then
        echo "  PASS: $desc"
        ((PASS++))
    else
        echo "  FAIL: $desc (expected=$expect, exit=$code)"
        ((FAIL++))
    fi
}

section() {
    echo ""
    echo "=== $1 ==="
}

# --- Basic commands ---
section "Basic commands"
test_cmd "Allow git status" "git status" "allow"
test_cmd "Allow git diff" "git diff" "allow"
test_cmd "Allow git log" "git log --oneline -5" "allow"
test_cmd "Allow non-git command" "echo hello" "allow"
test_cmd "Allow empty command" "" "allow"

# --- Force push ---
section "Force push to main/master"
test_cmd "Block: git push --force origin main" "git push --force origin main" "block"
test_cmd "Block: git push -f origin main" "git push -f origin main" "block"
test_cmd "Block: git push --force origin master" "git push --force origin master" "block"
test_cmd "Block: git push -f origin master" "git push -f origin master" "block"
test_cmd "Block: git push --force-with-lease origin main" "git push --force-with-lease origin main" "block"
test_cmd "Allow: git push origin main (no force)" "git push origin main" "allow"
test_cmd "Allow: git push --force origin feature" "git push --force origin feature-branch" "allow"

# --- Branch deletion ---
section "Branch deletion"
test_cmd "Block: git branch -D main" "git branch -D main" "block"
test_cmd "Block: git branch -d main" "git branch -d main" "block"
test_cmd "Block: git branch -D master" "git branch -D master" "block"
test_cmd "Block: git branch -d master" "git branch -d master" "block"

# --- False positive: branch name substring ---
section "Branch name substring (should NOT false-positive)"
test_cmd "Allow: git branch -D main-feature" "git branch -D main-feature" "allow"
test_cmd "Allow: git branch -D maintenance" "git branch -D maintenance" "allow"
test_cmd "Allow: git branch -d master-backup" "git branch -d master-backup" "allow"
test_cmd "Allow: git push --force origin main-dev" "git push --force origin main-dev" "allow"

# --- Chained commands ---
section "Chained commands with dangerous subcommand"
test_cmd "Block: echo && git push --force origin main" "echo hi && git push --force origin main" "block"
test_cmd "Block: git status && git push -f origin master" "git status && git push -f origin master" "block"
test_cmd "Block: echo ; git branch -D main" "echo foo ; git branch -D main" "block"
test_cmd "Block: git status || git push --force origin main" "git status || git push --force origin main" "block"
test_cmd "Block: git log | git push --force origin main" "git log | git push --force origin main" "block"

section "Chained commands (all safe)"
test_cmd "Allow: git status && git diff" "git status && git diff" "allow"
test_cmd "Allow: git status && echo done" "git status && echo done" "allow"
test_cmd "Allow: echo && echo" "echo hi && echo bye" "allow"
test_cmd "Allow: multi-git safe chain" "git status && echo --- && git diff && echo --- && git log --oneline -5" "allow"

# --- Full path to git ---
section "Full path to git binary"
test_cmd "Block: /usr/bin/git push --force origin main" "/usr/bin/git push --force origin main" "block"
test_cmd "Block: /usr/local/bin/git push -f origin master" "/usr/local/bin/git push -f origin master" "block"
test_cmd "Block: /usr/bin/git branch -D main" "/usr/bin/git branch -D main" "block"
test_cmd "Allow: /usr/bin/git status" "/usr/bin/git status" "allow"

# --- Prefix commands (env, sudo) ---
section "Prefix commands (env, sudo)"
test_cmd "Block: env git push --force origin main" "env git push --force origin main" "block"
test_cmd "Block: sudo git push --force origin main" "sudo git push --force origin main" "block"
test_cmd "Block: command git branch -D main" "command git branch -D main" "block"
test_cmd "Allow: env git status" "env git status" "allow"
test_cmd "Allow: sudo git diff" "sudo git diff" "allow"

# --- Prefix + chained ---
section "Prefix commands in chains"
test_cmd "Block: echo hi && env git push --force origin main" "echo hi && env git push --force origin main" "block"
test_cmd "Block: echo hi && /usr/bin/git branch -D main" "echo hi && /usr/bin/git branch -D main" "block"

# --- Results ---
echo ""
echo "=============================="
echo "Results: $PASS/$TOTAL passed, $FAIL failed"
echo "=============================="

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
