---
name: polish
description: This skill should be used when the user asks to "polish code", "clean up code", "simplify and review", "refine code", or wants to run code simplification followed by gated code review on recently modified code.
allowed-tools: Skill, Task
user-invocable: true
---

# Polish Skill

Simplify recently modified code, then run `code-reviewer` as a **gated loop** — if the reviewer flags Blocker or Major issues, dispatch a fix subagent and re-review until clean (or the polish retry limit of 2 is hit).

## Arguments

```
$ARGUMENTS
```

## Execution

Initialize: `polish_retry = 0` (separate from the caller's retry counter).

### Step 1: Simplify

Invoke the `/simplify` skill to refine code for clarity, consistency, and maintainability while preserving all functionality. Focus on recently modified code unless the user specified otherwise.

If arguments are provided, pass them as scope context.

Wait for the agent to complete fully before proceeding.

### Step 2: Code Review (gated)

Launch the `code-reviewer` agent via the Task tool to review the simplified code.

If arguments are provided, pass them as scope context.

Wait for the reviewer to complete.

### Step 2b: Handle Review Findings

Classify the reviewer's findings:

- **Blocker or Major** findings → Go to Step 2c (fix loop).
- **Minor or Nit only, or no findings** → Go to Step 3 (report).

### Step 2c: Fix Loop

If `polish_retry >= 2`, exit the loop and return verdict `FAIL_AT_LIMIT` with the remaining findings (see Step 3).

Otherwise:

1. **Dispatch a fix subagent** via Task tool (general-purpose):

   ```
   Task tool (general-purpose):
     description: "Fix polish findings"
     prompt: |
       The code-reviewer agent flagged the following issues in recently modified code.
       Fix each Blocker and Major finding. Leave Minor and Nit findings unchanged
       unless the fix is trivial.

       **Findings:**
       {code-reviewer's Blocker + Major findings, verbatim with file paths}

       **Scope:**
       {changed files from the caller, or args}

       Apply fixes directly with Edit. Do not rewrite unrelated code. When done,
       report the files you changed and a one-line summary of each fix.
   ```

2. Wait for the fix subagent to complete.
3. Increment `polish_retry`.
4. Re-dispatch `code-reviewer` on the changed files (return to Step 2).

### Step 3: Report

Return a structured verdict to the caller:

- **Verdict**: `PASS` (no Blocker/Major findings remain) or `FAIL_AT_LIMIT` (retry limit reached with unresolved issues).
- **Simplification changes** made in Step 1.
- **Review findings** from the final `code-reviewer` pass:
  - Blocker/Major (only present if `FAIL_AT_LIMIT`)
  - Minor/Nit (informational)
- **Retries used**: `polish_retry` / 2.

Example report:

```
## Polish Result

**Verdict:** PASS
**Retries used:** 1/2

**Simplification:**
- Extracted duplicate validation into `validateEmail` helper
- Removed unreachable branch in `parseConfig`

**Code review findings:**
- (None)
- Minor: Consider renaming `temp` to `cachedResult` in `store.ts:42`
```

## Notes

- **Retry counter is local to polish.** It does not share state with `/workflow:execute-task`'s retry counter. A caller (like `/workflow:execute-task`) may retry polish itself within its own budget.
- **Fixer is a subagent, not the current session.** Polish runs in the current session's context (so the simplify agent's changes are visible), but fixing is delegated to keep the current session clean.
- **Minor and Nit findings do not gate.** They're reported for caller awareness only.
