---
argument-hint: [-a|--auto] [message]
description: Create well-formatted commits with conventional commit format and emoji. Automatically groups related changes into logical commits.
allowed-tools: Task, AskUserQuestion, Bash(git add:*), Bash(git commit:*), Bash(git status:*), Bash(git log:*), Bash(git diff:*)
---

# Smart Git Commit

**Arguments:** $ARGUMENTS

Invoke the `git-workflow` skill to create commits following conventional commit format with emojis.

**Mode:** If `-a` or `--auto` flag is present, skip user confirmation and execute directly.
