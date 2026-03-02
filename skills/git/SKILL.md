---
name: git
description: This skill should be used when the user asks to "create a commit", "commit and push", "make a pull request", "understand branching strategies", "use conventional commits", or needs guidance on git best practices and safe git operations.
allowed-tools: Read, Glob, Grep, Bash(git add:*), Bash(git commit:*), Bash(git status:*), Bash(git log:*), Bash(git diff:*), Bash(git branch:*), Bash(git push:*), Bash(gh pr create:*), Bash(git rev-list:*)
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
   - `-A` — enables **all-changes** mode (include ALL changes in the repository, not just from the current session)
3. **Auto-accept is always ON** — never ask the user for confirmation, proceed immediately
4. Remaining tokens are **actions**: `commit`, `push`, `pr`
4. If no actions are provided, show the **Usage Help** section below and stop

### Examples

| Input | Actions | All-changes |
|-------|---------|-------------|
| `commit` | commit | no |
| `commit -A` | commit | yes |
| `commit push` | commit, push | no |
| `pr` | pr | no |
| `commit pr` | commit, pr | no |
| `commit push pr -A` | commit, push, pr | yes |

## Usage Help

If no actions are provided, display:

```
Usage: /git <actions> [-A]

Actions (combinable):
  commit   Analyze changes and create conventional commit(s)
  push     Push current branch to remote
  pr       Create a pull request

Flags:
  -A       All-changes: include ALL repo changes (not just current session)

Note: All actions proceed without confirmation (auto-accept always on).

Examples:
  /git commit          Commit current session's changes
  /git commit -A       Commit ALL changes in the repo, group into logical commits
  /git commit push     Commit then push
  /git pr              Create a pull request
  /git commit pr       Commit then create PR
  /git commit push pr -A  Full workflow with all changes
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

**Default mode** — commit changes from the current Claude Code session:

- `git status` — see all changed and untracked files
- `git diff` — see unstaged modifications
- `git diff --staged` — see staged modifications
- Identify which files were changed during the current session (based on conversation context) and only commit those
- Read untracked files with the Read tool since they won't appear in `git diff`

**All-changes mode (`-A`)** — commit ALL changes in the repository:

- `git status` — see all changed and untracked files
- `git diff` — see unstaged modifications
- `git diff --staged` — see staged modifications
- Every file shown in `git status` (modified, staged, AND untracked) MUST be included in exactly one commit
- Group them into multiple logical commits based on related functionality, scope, or purpose
- After grouping, verify that no files were left out
- Read untracked files with the Read tool since they won't appear in `git diff`

From the output, determine the commit type, scope, summary, and which files belong to each commit.

### Step 2: Propose Commit(s)

Display the proposed files to stage and commit message(s) to the user. Group related changes into logical commits when appropriate.

### Step 3: Confirm

Skip confirmation and proceed immediately.

### Step 4: Execute

For each proposed commit, stage only the relevant files and create the commit:

```bash
git add <file1> <file2> ...
git commit -m "<emoji> <type>(<scope>): <description>"
```

For commits with a body, use multiple `-m` flags:

```bash
git commit -m "<emoji> <type>(<scope>): <description>" -m "<body>"
```

When `-A` produces multiple logical commits, repeat this stage-and-commit cycle for each group sequentially.

### Step 5: Verify

Show result with `git log --oneline -<number of commits created>`.

## Action: push

### Step 1: Show Branch and Remote

Display the current branch and its remote tracking status using `git branch -vv`.

### Step 2: Confirm

Skip confirmation and proceed immediately.

### Step 3: Execute

```bash
git push -u origin <current-branch>
```

### Step 4: Verify

Show result with `git log --oneline -1` and confirm push succeeded.

## Action: pr

### Step 1: Analyze Branch Changes

Run the following git commands directly to understand the branch:

- `git log main..HEAD --oneline` — see all commits on this branch
- `git diff main...HEAD` — see the full diff against the base branch
- `git branch -vv` — see current branch and tracking info

From the output, determine the PR title, summary of changes, and testing suggestions.

### Step 2: Propose PR

Display the proposed PR title and description to the user.

### Step 3: Confirm

Skip confirmation and proceed immediately.

### Step 4: Execute

Push the branch if not already pushed, then create the PR:
```bash
gh pr create --title "<title>" --body "## Summary
<brief summary>

## Changes
<bullet points of changes>

## Test Plan
<how to test>"
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
5. **Always use plain git commands** — never use `git -C <path>`. Use `git add`, `git commit`, `git status`, etc. directly. The working directory is already the project root.
