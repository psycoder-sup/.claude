---
name: wrap
description: >
  This skill should be used when the user asks to "wrap up", "wrap session",
  "finish up", "wrap this task", "close out this task", "I'm done",
  "finalize this", "let's finish", or "end this task". It orchestrates
  session finalization: runs the polish skill for code quality checks,
  commits all changes via the git skill, and marks the current baragi
  task as done with a summary.
disable-model-invocation: true
version: 0.1.0
---

# Wrap — Session Finalization Workflow

Finalize the current session by polishing code, committing changes, and marking the baragi task as done. Execute these steps sequentially — each step must complete successfully before proceeding to the next.

## Step 1: Polish

Check whether the `/polish` skill has already been run during this conversation.

- **If already run:** Skip to Step 2.
- **If not yet run:** Invoke the `/polish` skill and wait for it to complete. If polish surfaces issues, address them before continuing.

## Step 2: Commit

Invoke the `/git` skill with auto-accept mode to commit all changes from this session:

```
/git commit -y
```

## Step 3: Mark Task Done

Retrieve the task ID from the `baragi session start` call made earlier in this conversation. If no session was started, ask the user which task to mark as done.

Update the task status to done:

```bash
baragi task update TASK-NNN --status=done --summary="Brief summary of what was accomplished"
```

Write a concise summary describing the work delivered during this session, not a list of files changed.

## Important Notes

- If any step fails, stop and report the issue to the user rather than continuing.
- Do not skip the polish step unless it was already executed earlier in this conversation.
- The task summary should describe what was delivered, not what files were touched.
