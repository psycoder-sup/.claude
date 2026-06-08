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
git add -A && git commit && git push
```

## Step 3: Prune Per-Feature Agent Memory

Per-document critique state belongs in the PRD/plan markdown, not in agent memory. After a feature ships, clean up any stale entries that snuck in.

1. Glob `.claude/agent-memory/*/critic_*.md` to find per-document critic memories.
2. If no matches exist, skip this step silently.
3. Otherwise, list the matches and use `AskUserQuestion` to confirm which to delete (default: all entries tied to the just-shipped feature; offer "delete all", "keep all", or per-file selection).
4. For each file the user approves:
   - Delete the file.
   - Remove its line from the same agent's `MEMORY.md` index (if present).

Do not delete memory files that look like durable project facts (paths, conventions, stack quirks) — those stay. Only the `critic_*` per-document files are in scope.
