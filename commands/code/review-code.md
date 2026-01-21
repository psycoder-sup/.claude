---
argument-hint: [files|scope]
description: Review code for bugs, security issues, and quality problems using confidence-based filtering
allowed-tools: Task
---

# Code Review

**Arguments:** $ARGUMENTS

## Execution

Use the Task tool with `subagent_type: base:code-reviewer` to review the code.

**Prompt for the agent:**

If arguments are provided, include them in the scope:
```
Review the following: $ARGUMENTS

Analyze the code and report any issues with confidence ≥ 80.
```

If no arguments are provided, review unstaged changes:
```
Review the unstaged changes (git diff).

Analyze the code and report any issues with confidence ≥ 80.
```

## Output

The agent will return:
- Summary of what was reviewed
- High-confidence issues (≥ 80) grouped by severity
- For each issue: description, file path, line number, and fix suggestion
- Confirmation if no significant issues found
