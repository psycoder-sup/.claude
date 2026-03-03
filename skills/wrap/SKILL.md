---
name: wrap
description: >
  This skill should be used when the user asks to "wrap up", "wrap session",
  "finish up", "wrap this work", "close out this work", "I'm done",
  "finalize this", "let's finish", or "end this work". It orchestrates
  session finalization: runs the polish skill for code quality checks,
  commits all changes via the git skill, and marks the current baragi
  work as done with a summary.
version: 0.1.0
---

# Wrap — Session Finalization Workflow

Finalize the current session by polishing code, committing changes, and marking the baragi work as done. Execute these steps sequentially — each step must complete successfully before proceeding to the next.

## Step 1: Polish

Check whether the `/polish` skill has already been run during this conversation.

- **If already run:** Skip to Step 2.
- **If not yet run:** Invoke the `/polish` skill and wait for it to complete. If polish surfaces issues, address them before continuing.

## Step 2: Commit

Invoke the `/git` skill to commit all changes from this session:

```
/git commit
```

## Step 3: Mark Work Done

Retrieve the work ID from the `baragi session start` call made earlier in this conversation. If no session was started, ask the user which work to mark as done.

Update the work status to done using the baragi MCP tool (`update_work`), setting status to "done" and providing a brief summary of what was accomplished.

Write a concise summary describing the work delivered during this session, not a list of files changed.

## Important Notes

- If any step fails, stop and report the issue to the user rather than continuing.
- Do not skip the polish step unless it was already executed earlier in this conversation.
- The work summary should describe what was delivered, not what files were touched.
