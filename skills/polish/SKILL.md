---
name: polish
description: This skill should be used when the user asks to "polish code", "clean up code", "simplify and review", "refine code", or wants to run code simplification followed by code review on recently modified code.
allowed-tools: Task
user-invocable: true
---

# Polish Skill

Run two agents sequentially to polish recently modified code: first simplify, then review.

## Arguments

```
$ARGUMENTS
```

## Execution

### Step 1: Simplify

Launch the `code-simplifier:code-simplifier` agent via the Task tool to simplify and refine code for clarity, consistency, and maintainability while preserving all functionality. Focus on recently modified code unless the user specified otherwise.

If arguments are provided, pass them as scope context to the agent.

Wait for the agent to complete fully before proceeding.

### Step 2: Review

Launch the `code-reviewer` agent via the Task tool to review the simplified code for bugs, logic errors, security vulnerabilities, code quality issues, and adherence to project conventions.

If arguments are provided, pass them as scope context to the agent.

### Step 3: Report

Report the combined results to the user — first the simplification changes made, then the review findings.
