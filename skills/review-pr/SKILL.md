---
name: review-pr
description: >
  This skill should be used when the user asks to "review a PR", "review pull request",
  "check PR #N", "review-pr", or wants a comprehensive pull request review with scoring.
  Usage: /review-pr <pr-number> [additional instructions]
allowed-tools: ["Bash", "Read", "Glob", "Grep", "Skill", "Agent", "Task"]
user-invocable: true
argument-hint: "<pr-number> [additional instructions]"
---

# PR Review Skill

Perform a comprehensive pull request review using multiple specialized assessments and produce a scored report.

## Arguments

```
$ARGUMENTS
```

Parse the first argument as the PR number. Everything after is additional instruction context.

## Execution

### Step 1: Fetch PR Details

Use the `gh` CLI to gather PR information:

```bash
# Get PR metadata (title, body, author, state, labels)
gh pr view <pr-number> --json title,body,author,state,labels,url,baseRefName,headRefName

# Get PR comments and review comments
gh pr view <pr-number> --comments

# Get the list of changed files
gh pr diff <pr-number> --name-only

# Get the full diff
gh pr diff <pr-number>
```

Summarize:
- PR title, author, and description
- Any reviewer comments or requested changes
- List of changed files and scope of changes

### Step 2: Checkout PR Changes Locally

Ensure the diff is available for analysis. Use `gh pr diff <pr-number>` to get the full diff content. Identify which files were added, modified, or deleted.

### Step 3: Code Simplification Assessment

Invoke the `/simplify` skill, scoped to the PR's changed files:

```
/simplify Review the changes from PR #<pr-number>. Focus on: <list of changed files>
```

Capture the simplification findings.

### Step 4: React Native Best Practices Assessment

Invoke the `/vercel-react-native-skills` skill, scoped to the PR's changed files:

```
/vercel-react-native-skills Assess the changes from PR #<pr-number> against React Native and Expo best practices. Files: <list of changed files>
```

Capture the React Native assessment findings.

### Step 5: General Code Review

Launch the `code-reviewer` agent via the Agent tool (subagent_type: `code-reviewer`):

```
Review the changes from PR #<pr-number>.

Changed files:
<list of changed files>

Full diff:
<pr diff content>

Additional context: <any additional instructions from user>

Analyze the code and report any issues with confidence >= 80.
```

Capture the code review findings.

### Step 6: Aggregate & Score

Combine all findings from Steps 3-5 and produce a final report.

**Scoring rubric (0.0 to 1.0):**

| Score Range | Meaning |
|---|---|
| 0.9 - 1.0 | Excellent. No issues or only trivial suggestions. Ready to merge. |
| 0.7 - 0.89 | Good. Minor issues or suggestions, nothing blocking. |
| 0.5 - 0.69 | Fair. Several issues that should be addressed before merge. |
| 0.3 - 0.49 | Needs work. Significant issues found across multiple areas. |
| 0.0 - 0.29 | Major concerns. Critical bugs, security issues, or architectural problems. |

**Deduction guidelines:**
- Critical bug or security issue: -0.2 to -0.3 each
- Important code quality issue: -0.05 to -0.1 each
- React Native anti-pattern: -0.05 to -0.1 each
- Simplification opportunity (minor): -0.02 to -0.05 each
- Missing or poor test coverage for changed code: -0.1
- Positive factors (good patterns, thorough tests, clean code) can offset minor issues

## Output Format

```markdown
# PR Review Report: #<pr-number> — <PR title>

**Author:** <author>
**Score: X.X / 1.0**
**Verdict:** <Excellent | Good | Fair | Needs Work | Major Concerns>

---

## Summary
<Brief 2-3 sentence summary of the PR and overall assessment>

## PR Comments & Context
<Summary of any existing reviewer comments or discussion>

## Findings

### Code Simplification (from /simplify)
<Findings or "No issues found">

### React Native Best Practices (from /vercel-react-native-skills)
<Findings or "No issues found">

### Code Review (from code-reviewer agent)
<Findings grouped by severity, or "No issues found">

## Score Breakdown

| Category | Deductions | Notes |
|---|---|---|
| Bugs & Logic Errors | -X.XX | ... |
| Security | -X.XX | ... |
| Code Quality | -X.XX | ... |
| React Native Practices | -X.XX | ... |
| Simplification | -X.XX | ... |
| **Total Score** | **X.X / 1.0** | |

## Recommended Actions
1. <Prioritized list of things to fix/improve>
```

If the user provided additional instructions, incorporate them into each assessment step and the final report.
