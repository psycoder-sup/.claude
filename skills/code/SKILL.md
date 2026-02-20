---
name: review-code
description: This skill should be used when the user asks to "review code", "check code quality", "find bugs", "security review", or wants code reviewed for bugs, logic errors, security vulnerabilities, and quality issues using confidence-based filtering.
allowed-tools: Task
user-invocable: true
---

# Code Review Skill

Review code for bugs, security issues, and quality problems using the code-reviewer agent with confidence-based filtering.

## Arguments

```
$ARGUMENTS
```

## Execution

Launch the `code-reviewer` agent via the Task tool.

If arguments are provided, include them as scope:

```
Review the following: $ARGUMENTS

Analyze the code and report any issues with confidence >= 80.
```

If no arguments are provided, review unstaged changes:

```
Review the unstaged changes (git diff).

Analyze the code and report any issues with confidence >= 80.
```

## Output

The agent returns:
- Summary of what was reviewed
- High-confidence issues (>= 80) grouped by severity
- For each issue: description, file path, line number, and fix suggestion
- Confirmation if no significant issues found
