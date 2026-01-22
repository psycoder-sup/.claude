---
name: git-workflow
description: This skill should be used when the user asks to "create a commit", "commit and push", "make a pull request", "understand branching strategies", "use conventional commits", or needs guidance on git best practices and safe git operations.
allowed-tools: Task, Read, Glob, Grep, AskUserQuestion, Bash(git add:*), Bash(git commit:*), Bash(git status:*), Bash(git log:*), Bash(git diff:*), Bash(git branch:*), Bash(git push:*), Bash(gh pr create:*), Bash(git rev-list:*)
# user-invocable: false
---

# Git Workflow Skill

Provides guidance for git operations using conventional commit format with emoji prefixes, including commit creation and pull request workflows.

## When to Use This Skill

- Creating commits with proper formatting
- Creating pull requests with comprehensive descriptions
- Understanding branching strategies
- Git best practices and safe operations

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

## Creating Commits

### Step 1: Analyze Changes

Use the Task tool with `subagent_type: diff-analyzer` to analyze the repository:

```
Prompt: Analyze the current git changes. Group into logical commits if needed.
```

The diff-analyzer agent will return structured analysis with type, scope, summary, and files.

### Step 2: Create Commit(s)

1. **Display the proposal** - Show files to stage and commit message(s)
2. **Confirm with user** (unless auto mode) - Use AskUserQuestion
3. **Execute** - Stage files and create commit
4. **Verify** - Show result with `git log -1`

### Commit Message Format

Use HEREDOC to preserve formatting:
```bash
git commit -m "$(cat <<'EOF'
<emoji> <type>(<scope>): <description>

[optional body]
EOF
)"
```

## Creating Pull Requests

### Step 1: Analyze Branch Changes

Use the Task tool with `subagent_type: diff-analyzer`:

```
Prompt: Analyze this branch for a pull request.
```

The diff-analyzer agent will return branch analysis with summary, changes, and testing suggestions.

### Step 2: Create Pull Request

1. **Display the proposal** - Show PR title, description, and branch to push
2. **Confirm with user** (unless auto mode) - Use AskUserQuestion
3. **Execute** - Push branch and create PR
4. **Show PR URL** to the user

### PR Description Format

Use HEREDOC:
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

## Safety Guidelines

1. **Never force push to main/master** without explicit user confirmation
2. **Check for uncommitted changes** before checkout/rebase
3. **Suggest backup branches** before risky operations
4. **Show state before and after** operations

## Commands Available

- `/commit` - Create commits with conventional format
- `/create-pr` - Create pull requests with descriptions
