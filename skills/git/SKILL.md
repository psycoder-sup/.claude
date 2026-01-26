---
name: git
description: This skill should be used when the user asks to "create a commit", "commit and push", "make a pull request", "understand branching strategies", "use conventional commits", or needs guidance on git best practices and safe git operations.
allowed-tools: Task, Read, Glob, Grep, AskUserQuestion, Bash(git add:*), Bash(git commit:*), Bash(git status:*), Bash(git log:*), Bash(git diff:*), Bash(git branch:*), Bash(git push:*), Bash(gh pr create:*), Bash(git rev-list:*)
user-invocable: true
---

# Git Skill

Provides git commit, push, and pull request workflows using conventional commit format with emoji prefixes.

## Arguments

```
$ARGUMENTS
```

## Argument Parsing

1. Split `$ARGUMENTS` into tokens
2. Extract the `-y` flag if present — this enables **auto-accept** mode (skip all confirmations)
3. Remaining tokens are **actions**: `commit`, `push`, `pr`
4. If no actions are provided, show the **Usage Help** section below and stop

### Examples

| Input | Actions | Auto-accept |
|-------|---------|-------------|
| `commit` | commit | no |
| `commit -y` | commit | yes |
| `commit push` | commit, push | no |
| `commit push -y` | commit, push | yes |
| `pr` | pr | no |
| `pr -y` | pr | yes |
| `commit pr` | commit, pr | no |
| `commit pr -y` | commit, pr | yes |
| `commit push pr -y` | commit, push, pr | yes |

## Usage Help

If no actions are provided, display:

```
Usage: /git <actions> [-y]

Actions (combinable):
  commit   Analyze changes and create conventional commit(s)
  push     Push current branch to remote
  pr       Create a pull request

Flags:
  -y       Auto-accept (skip confirmations)

Examples:
  /git commit          Commit with confirmation
  /git commit -y       Commit without confirmation
  /git commit push     Commit then push
  /git pr              Create a pull request
  /git commit pr -y    Commit then create PR, no confirmations
```

## Conventional Commit Format

All commits follow this format:
```
<emoji> <type>(<scope>): <description>
```

### Commit Types and Emojis

| Type | Emoji | Description |
|------|-------|-------------|
| feat | ✨ | New feature |
| fix | 🐛 | Bug fix |
| docs | 📝 | Documentation |
| style | 💄 | Formatting, styling |
| refactor | ♻️ | Code restructuring |
| perf | ⚡️ | Performance improvement |
| test | ✅ | Adding tests |
| chore | 🔧 | Maintenance tasks |
| ci | 👷 | CI/CD changes |
| security | 🔒️ | Security fix |
| deps | ➕/➖ | Add/remove dependencies |
| breaking | 💥 | Breaking changes |

## Action: commit

### Step 1: Analyze Changes

Use the Task tool with `subagent_type: diff-analyzer` to analyze the repository:

```
Prompt: Analyze the current git changes. Group into logical commits if needed.
```

The diff-analyzer agent will return structured analysis with type, scope, summary, and files.

### Step 2: Propose Commit(s)

Display the proposed files to stage and commit message(s) to the user.

### Step 3: Confirm

- If **auto-accept** is OFF: Use AskUserQuestion to confirm with the user before proceeding
- If **auto-accept** is ON: Skip confirmation and proceed immediately

### Step 4: Execute

Stage files and create commit using HEREDOC format:
```bash
git commit -m "$(cat <<'EOF'
<emoji> <type>(<scope>): <description>

[optional body]
EOF
)"
```

### Step 5: Verify

Show result with `git log -1`.

## Action: push

### Step 1: Show Branch and Remote

Display the current branch and its remote tracking status using `git branch -vv`.

### Step 2: Confirm

- If **auto-accept** is OFF: Use AskUserQuestion to confirm
- If **auto-accept** is ON: Skip confirmation

### Step 3: Execute

```bash
git push -u origin <current-branch>
```

### Step 4: Verify

Show result with `git log --oneline -1` and confirm push succeeded.

## Action: pr

### Step 1: Analyze Branch Changes

Use the Task tool with `subagent_type: diff-analyzer`:

```
Prompt: Analyze this branch for a pull request.
```

The diff-analyzer agent will return branch analysis with summary, changes, and testing suggestions.

### Step 2: Propose PR

Display the proposed PR title and description to the user.

### Step 3: Confirm

- If **auto-accept** is OFF: Use AskUserQuestion to confirm
- If **auto-accept** is ON: Skip confirmation

### Step 4: Execute

Push the branch if not already pushed, then create the PR:
```bash
gh pr create --title "<title>" --body "$(cat <<'EOF'
## Summary
<brief summary>

## Changes
<bullet points of changes>

## Test Plan
<how to test>
EOF
)"
```

### Step 5: Show PR URL

Display the resulting PR URL to the user.

## Action Chaining

When multiple actions are specified, execute them **sequentially** in this order:

1. `commit` (first, if present)
2. `push` (second, if present)
3. `pr` (last, if present)

**Stop immediately on any error** — do not proceed to the next action if the current one fails.

## Safety Guidelines

1. **Never force push to main/master** without explicit user confirmation
2. **Check for uncommitted changes** before checkout/rebase
3. **Suggest backup branches** before risky operations
4. **Show state before and after** operations
