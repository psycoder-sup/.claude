<!-- project-kit:begin — managed block. Safe to edit; re-running /project-kit updates only between these markers. -->

## Status

{{ONE_LINER}}

**Live state lives in [`docs/pm/status.md`](docs/pm/status.md) — read it first each session.** Keep this section to a 2–4 line summary of the current focus; let `status.md` carry the detail.

- **Now:** {{NOW}}
- **Next:** {{NEXT}}

## Repo layout (context docs)

- `docs/pm/status.md` — live project state (Now / Next / milestones / blocked / shipped). The first thing to read each session.
- `docs/pm/decisions/` — decision records (ADRs): one per direction change, numbered, fixed once accepted. `README.md` is the auto-generated index; `_template.md` is the skeleton.
{{OPTIONAL_LAYOUT_LINES}}
## Keeping the record current (do this without being asked)

`docs/pm/status.md` is the project's live state and the first thing to read each session. It's only useful if it's true, so maintaining it is part of finishing the work — not a separate request. **After completing any meaningful unit of work — a task, a milestone step, a decision, a notable dead-end — update the record before treating the job as done:**

- **`docs/pm/status.md`** — move the finished item to *Shipped* (dated, newest first, link the commit); set the new *Now* / *Next*; add or clear *Blocked / open*; tick a milestone box if one completed; bump *Last updated*.
- **`CLAUDE.md` → Status** — only if the current focus changed. Keep it to the 2–4 line summary (it's auto-loaded every session) and let it point at `status.md` for detail.
- **A decision record** (`docs/pm/decisions/NNNN-*.md`) — only when direction changed: a choice a future session shouldn't silently reverse. Routine progress needs no ADR. After adding one, refresh the index in `docs/pm/decisions/README.md`.

Keep entries specific and falsifiable — cite dates, link commits/ADRs. A stale status is worse than none: if unsure whether something shipped, say so in the file rather than guessing. `status.md` is a snapshot, not a journal — git history is the fine-grained log.

<!-- project-kit:end -->
