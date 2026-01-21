---
argument-hint: [-a|--auto] [message]
description: Create well-formatted pull request to remote repository
allowed-tools: Task, AskUserQuestion, Bash(git push:*), Bash(git status:*), Bash(git log:*), Bash(git branch:*), Bash(git diff:*), Bash(gh pr create:*)
---

# Smart Git Pull Request Creation

**Arguments:** $ARGUMENTS

Invoke the `git-workflow` skill to create a pull request with comprehensive description.

**Mode:** If `-a` or `--auto` flag is present, skip user confirmation and execute directly.
