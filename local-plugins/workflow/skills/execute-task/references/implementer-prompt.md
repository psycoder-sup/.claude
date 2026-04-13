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

    Read the relevant SPEC sections and PRD requirements. Explore the codebase
    to understand existing patterns, conventions, and file structure. Identify
    the test framework and existing test patterns.

    ### 2. Write Tests First (TDD)

    Write failing tests that cover:
    - Each acceptance criterion from the task
    - Happy path and error paths
    - Edge cases mentioned in the spec

    Run the tests to confirm they fail for the expected reasons.
    Use the test-runner-slim agent via Task tool for running tests.

    **If a test passes immediately, you are testing existing behavior, not new behavior.
    Delete it and write a test that actually exercises your new code.**

    ### 3. Implement

    Write the minimum code to make all tests pass.
    - Follow existing codebase patterns and conventions
    - Do not over-engineer or add features not in the task scope
    - If a file grows beyond the task's intent, stop and report DONE_WITH_CONCERNS

    ### 4. Run All Tests

    Run the full test suite (not just your tests) via test-runner-slim agent.
    Ensure no regressions. If tests fail, fix and re-run.

    ### 5. Self-Review

    Before reporting, review your work:
    - Did you implement everything in the task scope?
    - Did you add anything NOT in scope? Remove it.
    - Did you follow existing codebase conventions?
    - Are all tests passing?

    If you find issues, fix them before reporting.

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

    **Summary:** [1-2 sentences on what was implemented]

    **Concerns:** [Only if DONE_WITH_CONCERNS]

    **Blockers:** [Only if BLOCKED — what is blocking and why]

    **Questions:** [Only if NEEDS_CONTEXT — specific questions]
    ---
```
