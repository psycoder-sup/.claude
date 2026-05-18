---
name: annotate
description: >-
  Open a markdown file in a browser and leave block-level comments that are
  saved to a sidecar JSON file alongside it. The sidecar can then be applied
  to the source markdown by Claude — automatically when the user checks
  "Auto-apply" in the Submit modal, or in a follow-up turn otherwise.
allowed-tools: [Bash, Read, Edit]
user-invocable: true
disable-model-invocation: true
argument-hint: "<path-to-markdown>"
arguments:
  - name: markdown_path
    description: Absolute or relative path to the markdown file to review.
    required: true
---

# annotate

Open the given markdown file in a local browser tab for block-level commenting. Comments are persisted to `<file>.comments.json` next to the source.

The user reviews in the browser, then clicks **Done**. The Submit modal has an **Auto-apply comments when I click Done** checkbox:

- **Checked** → after Done, this skill resumes in the same turn and you (Claude) apply the comments by following `${CLAUDE_PLUGIN_ROOT}/skills/annotate/references/apply-comments-prompt.md` against the source markdown.
- **Unchecked** → after Done, you print the copy-pasteable next-turn prompt (FR-30 behavior) and stop. The user can apply later in a separate turn.

This skill never edits the source markdown directly — applying is always your work, driven by `apply-comments-prompt.md`.

## Step 1 — Launch the server and wait for Done

**Run this block with Bash. Set the Bash tool's `timeout` to `600000` (10 min — the max) so the internal 9-minute wait below has comfortable headroom.**

```bash
LOG="$(mktemp -t mdreview.XXXXXX)"
nohup python3 "${CLAUDE_PLUGIN_ROOT}/server/annotate_server.py" "$1" >"$LOG" 2>&1 &
PID=$!
disown 2>/dev/null || true

# Phase A: up to ~5s for URL line, an error, or early exit.
for _ in $(seq 1 25); do
  if grep -qE '^(http://|error:)' "$LOG"; then break; fi
  if ! kill -0 "$PID" 2>/dev/null; then break; fi
  sleep 0.2
done

echo "PID: $PID"
echo "Log: $LOG"
echo "---"
cat "$LOG"
echo "---"

# If launch failed (process exited before printing a URL), bail out.
if ! kill -0 "$PID" 2>/dev/null && ! grep -q '^http://' "$LOG"; then
  echo "OUTCOME: LAUNCH_FAILED"
  exit 0
fi

# Phase B: wait up to 540s (9 min) for the user to click Done.
# kill -0 is a no-op signal that just probes whether $PID is alive.
DEADLINE=$((SECONDS + 540))
while kill -0 "$PID" 2>/dev/null; do
  if [ $SECONDS -ge $DEADLINE ]; then break; fi
  sleep 1
done

if kill -0 "$PID" 2>/dev/null; then
  echo "OUTCOME: STILL_RUNNING"
  exit 0
fi

# Server exited. The server prints AUTO_APPLY: <0|1> to stdout when Done was
# clicked. No marker means it was killed externally (e.g. Ctrl-C / kill PID)
# — treat that as NO_AUTO.
if grep -q '^AUTO_APPLY: 1' "$LOG"; then
  echo "OUTCOME: AUTO_APPLY"
else
  echo "OUTCOME: NO_AUTO"
fi
```

## Step 2 — Interpret the outcome

The bash block always ends with one of four `OUTCOME:` lines. Read it and act:

### `OUTCOME: LAUNCH_FAILED`

The server never bound a port. The log section between the `---` markers explains why. Common cases:

- `another markdown-review instance is running` — surface the running URL and `target_file` from the log so the user can return to that session.
- `stale lock file detected` — surface the manual-clear instruction from the log verbatim.
- Other `error:` lines — relay them as-is.

Do not retry; report and stop.

### `OUTCOME: AUTO_APPLY`

The user clicked Done with auto-apply selected. **Apply the comments now, in this turn, without asking for confirmation.**

1. Read `${CLAUDE_PLUGIN_ROOT}/skills/annotate/references/apply-comments-prompt.md` for the full procedure.
2. The inputs are `$1` (the markdown file) and `$1.comments.json` (the sidecar).
3. Follow that file's steps to read the sidecar, locate each block by anchor, apply the user's instruction via `Edit`, and mark each comment `applied: true` in the sidecar.
4. End with the one-paragraph summary that file prescribes — how many applied, how many orphaned, any warnings.

### `OUTCOME: NO_AUTO`

The user clicked Done without auto-apply (or killed the server externally). Print this exact next-turn prompt so they can paste it back later, replacing `<MD_PATH>` with `$1`:

> Apply the comments from `<MD_PATH>.comments.json` to `<MD_PATH>`. Use the apply-comments instructions at `${CLAUDE_PLUGIN_ROOT}/skills/annotate/references/apply-comments-prompt.md`. Do not start applying until I confirm.

Then stop — do not start applying. The user must explicitly ask in a separate turn (FR-31).

### `OUTCOME: STILL_RUNNING`

The user has not clicked Done after 9 minutes. The server is still running (its PID is in the bash output). Tell the user briefly:

- The URL from the bash log is still live.
- To resume waiting for Done from Claude, ask the user to re-run `/markdown-review:annotate <same path>` — the running instance will be detected via the lockfile and the same URL will be surfaced.
- Alternatively, if they've already clicked Done, they can just say "apply" and you'll pick up where the skill left off (read the sidecar and apply).

Do not start applying on STILL_RUNNING — comments may not yet be final.
