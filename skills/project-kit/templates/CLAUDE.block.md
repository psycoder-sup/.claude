<!-- project-kit:begin — managed block. Safe to edit; re-running /project-kit updates only between these markers. -->

## Status

{{ONE_LINER}}

**Live state lives in [`docs/pm/status.json`](docs/pm/status.json) — read it first each session.** It's structured JSON; keep this section to a 2–4 line summary of the current focus and let `status.json` carry the detail. Humans: launch the live dashboard with `python3 docs/pm/dashboard/serve.py`.

- **Now:** {{NOW}}
- **Next:** {{NEXT}}

## Repo layout (context docs)

- `docs/pm/status.json` — live project state (now / next / milestones / blocked / shipped). The first thing to read each session. Shape: `docs/pm/schema/status.schema.json`.
- `docs/pm/decisions/` — decision records (ADRs): one JSON per direction change, numbered, fixed once accepted. `NNNN-*.json` are the records (shape: `schema/decision.schema.json`), `_template.json` is the skeleton, `README.md` is the auto-generated index.
- `docs/pm/schema/` — JSON Schemas: the field-by-field contract + guidance for each doc. Consult before writing/updating a JSON file.
- `docs/pm/dashboard/` — the read-only viewer: `serve.py` (stdlib, no installs) serves the docs and live-reloads on change; `index.html` is the dashboard. Run `python3 docs/pm/dashboard/serve.py`.
{{OPTIONAL_LAYOUT_LINES}}
## Keeping the record current (do this without being asked)

`docs/pm/status.json` is the project's live state and the first thing to read each session. It's only useful if it's true, so maintaining it is part of finishing the work — not a separate request. The dashboard renders it live, so updates show up the moment you save. **After completing any meaningful unit of work — a task, a milestone step, a decision, a notable dead-end — update the record before treating the job as done:**

- **`docs/pm/status.json`** — add the finished item to `shipped` (with `date` and `commit`); reset `now` / `next`; add or clear `blocked`; flip a milestone's `done` to `true` if one completed; bump `lastUpdated`. Match `schema/status.schema.json`.
- **`CLAUDE.md` → Status** — only if the current focus changed. Keep it to the 2–4 line summary (it's auto-loaded every session) and let it point at `status.json` for detail.
- **A decision record** (`docs/pm/decisions/NNNN-*.json`) — only when direction changed: a choice a future session shouldn't silently reverse. Routine progress needs no ADR. When one supersedes an earlier ADR, set `supersedes` on the new record and set `supersededBy` (and `status: "Superseded"`) on the old one. After adding or changing a record, regenerate `docs/pm/decisions/README.md`.

Keep entries specific and falsifiable — cite dates, link commits/ADRs. A stale status is worse than none: if unsure whether something shipped, say so in the file rather than guessing. `status.json` is a snapshot, not a journal — git history is the fine-grained log.

<!-- project-kit:end -->
