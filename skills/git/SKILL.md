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
2. Extract flags if present:
   - `-y` — enables **auto-accept** mode (skip all confirmations)
   - `-A` — enables **all-changes** mode (include all unstaged and untracked files in the analysis, group them into logical commits)
3. Remaining tokens are **actions**: `commit`, `push`, `pr`
4. If no actions are provided, show the **Usage Help** section below and stop

### Examples

| Input | Actions | Auto-accept | All-changes |
|-------|---------|-------------|-------------|
| `commit` | commit | no | no |
| `commit -y` | commit | yes | no |
| `commit -A` | commit | no | yes |
| `commit -A -y` | commit | yes | yes |
| `commit push` | commit, push | no | no |
| `commit push -y` | commit, push | yes | no |
| `pr` | pr | no | no |
| `pr -y` | pr | yes | no |
| `commit pr -y` | commit, pr | yes | no |
| `commit push pr -A -y` | commit, push, pr | yes | yes |

## Usage Help

If no actions are provided, display:

```
Usage: /git <actions> [-y] [-A]

Actions (combinable):
  commit   Analyze changes and create conventional commit(s)
  push     Push current branch to remote
  pr       Create a pull request

Flags:
  -y       Auto-accept (skip confirmations)
  -A       All-changes: include all unstaged and untracked files,
           group them into logical commits automatically

Examples:
  /git commit          Analyze changes and commit with confirmation
  /git commit -y       Analyze changes and commit without confirmation
  /git commit -A       Analyze ALL unstaged/untracked changes, group into logical commits
  /git commit -A -y    Same as above, skip confirmations
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

- **Default mode**: Analyze changes from the current session, or follow user-provided instructions if given, and create commit(s) accordingly.
- **All-changes mode (`-A`)**: Analyze ALL changes including unstaged modifications and untracked files. Group them into multiple logical commits based on related functionality, scope, or purpose.

```
Prompt: Analyze the current git changes. Group into logical commits if needed.
(If -A: also include all untracked files in the analysis.)
```

The diff-analyzer agent will return structured analysis with type, scope, summary, and files.

### Step 2: Propose Commit(s)

Display the proposed files to stage and commit message(s) to the user. When `-A` is used, there will typically be multiple commits — each grouping related changes together.

### Step 3: Confirm

- If **auto-accept** is OFF: Use AskUserQuestion to confirm with the user before proceeding
- If **auto-accept** is ON: Skip confirmation and proceed immediately

### Step 4: Execute

For each proposed commit, stage only the relevant files and create the commit using HEREDOC format:

```bash
git add <file1> <file2> ...
git commit -m "$(cat <<'EOF'
<emoji> <type>(<scope>): <description>

[optional body]
EOF
)"
```

When `-A` produces multiple logical commits, repeat this stage-and-commit cycle for each group sequentially.

### Step 5: Verify

Show result with `git log --oneline -<number of commits created>`.

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
