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

Perform a comprehensive pull request review using multiple specialized assessments and produce a scored report. The skill is framework-agnostic — tech-stack-specific checks are loaded from `references/` on demand.

## Arguments

```
$ARGUMENTS
```

Parse the first argument as the PR number. Everything after is additional instruction context.

## Execution

### Step 1: Fetch PR Details

Use the `gh` CLI to gather PR information:

```bash
# Metadata (title, body, author, state, labels, branches)
gh pr view <pr-number> --json title,body,author,state,labels,url,baseRefName,headRefName

# Existing review comments and discussion
gh pr view <pr-number> --comments

# Changed files
gh pr diff <pr-number> --name-only

# Full diff
gh pr diff <pr-number>
```

Summarize PR title, author, description, reviewer comments, and scope of changes.

### Step 2: Detect Tech Stack

Infer the primary stack(s) of the changed files. Use a minimal set of signals:

- **File extensions** of changed files: `.tsx/.jsx/.ts/.js`, `.go`, `.py`, `.rs`, `.rb`, `.java`, `.kt`, `.swift`, `.cs`, etc.
- **Manifest files** present in the repo (or touched by the PR):
  - `package.json` — inspect `dependencies` / `devDependencies` for `react-native`, `expo`, `next`, `react`, `vue`, etc.
  - `go.mod` → Go
  - `pyproject.toml` / `requirements.txt` → Python
  - `Cargo.toml` → Rust
  - `Gemfile` → Ruby
  - `pom.xml` / `build.gradle` → Java / Kotlin
  - `Package.swift` → Swift
- **Repo layout**: `ios/` + `android/` next to a JS project suggests React Native.

Record the detected stacks — they determine which references to load in Step 4.

### Step 3: Code Simplification Assessment

Invoke the `/simplify` skill scoped to the PR's changed files:

```
/simplify Review the changes from PR #<pr-number>. Focus on: <changed files>
```

Capture the findings.

### Step 4: Framework-Specific Assessment (Conditional)

For each detected stack, read the matching reference from `references/` and apply its checklist to the changed files. Available references:

- React Native / Expo → `references/react-native.md`

If no reference exists for a detected stack, skip this step for that stack and rely on the general code review in Step 5. When adding support for a new stack, create `references/<stack>.md` and add it to the list above.

Capture the framework-specific findings per stack.

### Step 5: General Code Review

Launch the `code-reviewer` agent via the Agent tool (`subagent_type: code-reviewer`):

```
Review the changes from PR #<pr-number>.

Changed files:
<list of changed files>

Detected stack(s): <from Step 2>

Full diff:
<pr diff content>

Additional context: <any additional instructions from user>

Report only issues with confidence >= 80. Focus on bugs, security, correctness,
and adherence to patterns already present in the codebase.
```

Capture the code review findings.

### Step 6: Aggregate & Score

Combine all findings from Steps 3–5 and produce a final report.

**Scoring rubric (0.0 to 1.0):**

| Score Range | Meaning |
|---|---|
| 0.9 – 1.0 | Excellent. No issues or only trivial suggestions. Ready to merge. |
| 0.7 – 0.89 | Good. Minor issues or suggestions, nothing blocking. |
| 0.5 – 0.69 | Fair. Several issues that should be addressed before merge. |
| 0.3 – 0.49 | Needs work. Significant issues across multiple areas. |
| 0.0 – 0.29 | Major concerns. Critical bugs, security, or architectural problems. |

**Deduction guidelines:**
- Critical bug or security issue: -0.2 to -0.3 each
- Important code quality issue: -0.05 to -0.1 each
- Framework anti-pattern (from a loaded reference): -0.05 to -0.1 each
- Simplification opportunity (minor): -0.02 to -0.05 each
- Missing or poor test coverage for changed code: -0.1
- Positive factors (good patterns, thorough tests, clean code) can offset minor issues

## Output Format

```markdown
# PR Review Report: #<pr-number> — <PR title>

**Author:** <author>
**Detected stack(s):** <list>
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

### Framework-Specific (<stack name>)
<Findings per loaded reference, or "No reference loaded">

### Code Review (from code-reviewer agent)
<Findings grouped by severity, or "No issues found">

## Score Breakdown

| Category | Deductions | Notes |
|---|---|---|
| Bugs & Logic Errors | -X.XX | ... |
| Security | -X.XX | ... |
| Code Quality | -X.XX | ... |
| Framework Practices | -X.XX | only if a reference was loaded |
| Simplification | -X.XX | ... |
| **Total Score** | **X.X / 1.0** | |

## Recommended Actions
1. <Prioritized list of things to fix/improve>
```

Only include a "Framework Practices" row when at least one reference was loaded. If the user provided additional instructions, incorporate them into each assessment step and the final report.
