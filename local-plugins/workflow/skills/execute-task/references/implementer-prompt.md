# Implementer Prompt Template

Use this template when dispatching an implementer subagent via the Task tool.

**Placeholders:** `{TASK_TITLE}`, `{TASK_TEXT}`, `{SPEC_PATH}`, `{PRD_PATH}`, `{WORKING_DIR}`, `{PREVIOUS_ISSUES}`

```
Task tool (general-purpose):
  description: "Implement: {TASK_TITLE}"
  prompt: |
    You are implementing a single task from a technical specification using TDD.

    ## Task

    **{TASK_TITLE}**

    {TASK_TEXT}

    ## Source Documents

    - **SPEC:** {SPEC_PATH}
    - **PRD:** {PRD_PATH}

    Read the referenced SPEC sections and PRD requirements for full context on
    architecture, patterns, and constraints relevant to this task.

    ## Previous Issues

    {PREVIOUS_ISSUES}

    If previous issues are listed above, address ALL of them before proceeding.

    ## Before You Begin

    If you have questions about:
    - The requirements or acceptance criteria
    - The approach or implementation strategy
    - Dependencies or assumptions
    - Anything unclear in the task description

    **Ask them now.** Report with status NEEDS_CONTEXT. Do not guess.

    ## Your Job

    Work from: {WORKING_DIR}

    ### 1. Explore Context

    Read the relevant SPEC sections and PRD requirements. Pay special attention to:
    - **SPEC Section 7 (Type Definitions)** — use these types verbatim; do not invent new ones unless the spec is wrong.
    - **SPEC Section 13.5 (Test Skeletons)** — these are your starting failing tests.

    Explore the codebase to understand existing patterns, conventions, and file structure.
    Identify the test framework and existing test patterns.

    ### 2. Write Tests First (TDD) — MANDATORY TWO-COMMIT RHYTHM

    This is a hard gate. Tests commit first, implementation commits second.

    **Step 2a — Write the failing tests:**

    Copy the test skeletons from SPEC Section 13.5 for the acceptance criteria in this task.
    Flesh out skeleton bodies (imports, setup, assertions) enough to make them real, executable,
    failing tests. If Section 13.5 is missing a skeleton for an acceptance criterion, write one.

    Do NOT invent tests beyond what the acceptance criteria require. Do NOT write placeholder
    `expect(true).toBe(true)` — every assertion must exercise real behavior.

    **Step 2b — Run the failing tests:**

    Use the `test-runner-slim` agent via Task tool. Confirm the tests fail for the EXPECTED
    reason (function not defined, type not found, etc. — not a syntax error or setup bug).

    **If a test passes immediately, you are testing existing behavior, not new behavior.**
    Delete it and write a test that actually exercises your new code.

    **Step 2c — Commit the failing tests (first commit):**

    Stage ONLY the test files and commit with message prefix `test:`:

    ```
    test({scope}): add failing tests for {task-title}

    Covers FR-XX from PRD.
    All tests fail as expected: {brief failure summary}
    ```

    Do NOT include implementation files in this commit.

    ### 3. Implement (Second Commit)

    **Step 3a — Write the minimum code to make all tests pass:**

    - Use the types from SPEC Section 7 verbatim.
    - Follow existing codebase patterns and conventions.
    - Do not over-engineer or add features not in the task scope.
    - If a file grows beyond the task's intent, stop and report DONE_WITH_CONCERNS.

    **Step 3b — Run all tests** (full suite via test-runner-slim). Ensure no regressions.

    **Step 3c — Commit the implementation (second commit):**

    ```
    feat({scope}): implement {task-title}

    Implements {acceptance criteria summary}.
    All tests pass.
    ```

    ### 4. Self-Review

    Before reporting, review your work:
    - Did you implement everything in the task scope?
    - Did you add anything NOT in scope? Remove it.
    - Did you follow existing codebase conventions?
    - Are all tests passing?
    - Is the test commit BEFORE the implementation commit? (`git log` should show `test:` then `feat:`.)

    If you find issues, fix them before reporting. Amending commits is fine if the TDD ordering is preserved; if not, reset and redo the commits in the correct order.

    ## When You're Stuck

    It is always OK to stop and escalate. Bad work is worse than no work.

    **STOP and escalate when:**
    - The task requires architectural decisions not covered by the spec
    - You need to understand code beyond what was provided
    - The task involves restructuring code the spec didn't anticipate
    - You feel uncertain about whether your approach is correct

    Report with status BLOCKED. Describe what you're stuck on and what you tried.

    ## Report Format

    End your response with this exact structure:

    ---
    **Status:** [DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT]

    **Changed Files:**
    - path/to/file1 (created | modified)
    - path/to/file2 (created | modified)

    **Tests:**
    - X tests written, Y passing, Z failing

    **Commits (in order):**
    - `test: ...` — {short sha + message}
    - `feat: ...` — {short sha + message}

    **Summary:** [1-2 sentences on what was implemented]

    **Concerns:** [Only if DONE_WITH_CONCERNS]

    **Blockers:** [Only if BLOCKED — what is blocking and why]

    **Questions:** [Only if NEEDS_CONTEXT — specific questions]
    ---
```
