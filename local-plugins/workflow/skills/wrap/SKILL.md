---
name: wrap
description: >
  This skill should be used when the user asks to "wrap up", "wrap session",
  "finish up", "wrap this work", "close out this work", "I'm done",
  "finalize this", "let's finish", or "end this work". It orchestrates
  session finalization: polish loop, commit, push, and mark work done.
version: 0.2.0
---

# Wrap — Session Finalization Workflow

Execute these steps sequentially. Stop and report on any failure.

## Step 1: Polish Loop

1. Run `/workflow:polish`. Skip only if the most recent code edits have already been polished (no new changes since last polish).
2. If polish produced code changes, run `/workflow:polish` again.
3. Repeat until polish finds nothing to fix.

## Step 2: Commit & Push

```
/git-skill commit push
```

## Step 3: Mark Work Done

Retrieve the work ID from the `baragi session start` call made earlier in this conversation. If no session was started, ask the user which work to mark as done.

### Parent work (has children)

1. List child works using `baragi work list --parent=WORK-NNN` (or check earlier conversation context).
2. **Validate** all child works have status `done`. If any are not done, report which are incomplete and stop — do not mark the parent done.
3. If all children are done, mark the parent work as done with a summary.

### Leaf work (no children)

Update the work status to done using the baragi CLI, setting status to "done" and providing a brief summary of what was delivered (not a list of files changed).
