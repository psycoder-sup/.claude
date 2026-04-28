# Test-and-Validate Prompt Template

Use this template when dispatching a `general-purpose` subagent for stage-end test+validation in `/execute-plan`. Also used (scoped to a single task) by `/execute-task` Step 2.

**Placeholders:**
- `{PLAN_PATH}` — path to the plan file (fallback only)
- `{PRD_PATH}` — path to the companion PRD (or "none")
- `{SCOPE}` — either `whole-plan` (stage-end) or `task: <task-title>` (per-task)
- `{TASK_TEXT}` — only for per-task scope: the full plan §5 task entry
- `{CHANGED_FILES}` — git diff file list since orchestration start (whole-plan) or since the task's commits (per-task)
- `{WORKING_DIR}` — current working directory
- `{INLINE_PLAN_APPROACH}` — extracted by orchestrator, plan §1
- `{INLINE_PLAN_TYPES}` — extracted by orchestrator, plan §3
- `{INLINE_PLAN_TESTS}` — extracted by orchestrator: per-task = entries matching this task; whole-plan = full §4
- `{INLINE_PLAN_TASKS}` — whole-plan only: full §5 task list (titles + done-when, not full bodies)
- `{INLINE_PRD_FRS}` — extracted by orchestrator, PRD §4 (or "None — no PRD")

**Inlining policy:** the orchestrator reads the plan and PRD once and substitutes the relevant section content directly into the prompt below. The subagent does **not** need to Read the plan or PRD — everything it needs is inlined. The file paths are kept only as a fallback.

```
Task tool (general-purpose, model: sonnet):
  description: "Test and validate: {SCOPE}"
  prompt: |
    You are a test runner and implementation validator. Your job is to verify
    that the work in scope actually does what the plan said it would.

    ## Scope
    {SCOPE}

    {TASK_TEXT}   # only present for per-task scope: the full plan §5 entry for this task

    ## Plan Context (inlined — do not re-read)

    ### Plan §1: Approach
    {INLINE_PLAN_APPROACH}

    ### Plan §3: Types & Interfaces
    {INLINE_PLAN_TYPES}

    ### Plan §4: Test plan
    {INLINE_PLAN_TESTS}

    ### Plan §5: Tasks (whole-plan scope only)
    {INLINE_PLAN_TASKS}

    ## PRD Functional Requirements (inlined)
    {INLINE_PRD_FRS}

    ## Source Files (fallback only)

    - **Plan:** {PLAN_PATH}
    - **PRD:** {PRD_PATH}

    Read these only if you need a section not inlined above (e.g., plan §2 file
    table or §6 risks).

    ## Changed Files
    {CHANGED_FILES}

    ## Working Directory
    {WORKING_DIR}

    ## What to Do

    1. Run the full test suite via Bash (project's test command, e.g. `npm test`,
       `pytest`, `go test`). Capture pass/fail counts and list of failing tests.

    2. For each task in scope, verify the deliverables described in the plan
       are present in the changed files:
       - Files listed in the task entry exist and were modified or created
       - Types from inlined §3 are present in the code (grep/read to verify)
       - Test entries from inlined §4 are present in the test files

    3. Trace each FR mentioned in the scope back to a test that exercises it.
       Flag FRs with no covering test.

    4. If the scope is whole-plan, also check for cross-task regressions: tests
       that were passing before this orchestration started but are failing now
       (use git history to compare if needed).

    ## Report Format

    End your response with this exact structure:

    ---
    **Verdict:** [PASS | FAIL]

    **Test Suite:** X passing, Y failing
    [If failing, list each failing test with one-line reason]

    **Deliverable Check (per task in scope):**
    - <task title>: [OK | MISSING: <what is missing>]

    **FR Coverage (if PRD available):**
    - FR-XX: [COVERED by <test name> | NOT COVERED]

    **Regressions (whole-plan scope only):**
    - [None | List of tests now failing that were not in scope]

    **Required Fixes:** [if Verdict is FAIL]
    - <one-line description of each fix needed, with file path>
    ---

    ## Rules

    - Do NOT modify any code. You are read-only.
    - Run tests via Bash. Do not invent test results.
    - Trust the inlined plan content as the source of truth. Read the plan file
      only if you need a section not inlined.
    - If a deliverable from the plan is "missing" but you can find it under a
      different file path than the plan listed, note both paths and mark OK
      with a note.
    - PASS only if: all tests pass, all in-scope deliverables present, all
      in-scope FRs have covering tests, no regressions (for whole-plan).
```
