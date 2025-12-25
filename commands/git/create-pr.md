---
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git push:*), Bash(gh pr create:*), Bash(gh pr view:*), Bash(gh pr edit:*)
argument-hint: [message]
description: Create well-formatted pull request to remote repository
---

# Smart Git Pull Request Creation

Create well formatted pull requests: $ARGUMENTS

## Current Repository State

- Git status: !`git status --porcelain`
- Current branch: !`git branch --show-current`
- Diff: !`git diff main...HEAD`
- commit history: !`git log main...HEAD`

## Read all the relevant code

To understand code changes, read all the code that is different from main branch.

## Create PR contents

Based on your research create a comprehensive PR contents and create PR.
