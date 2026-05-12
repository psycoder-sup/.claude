---
name: annotate
description: >-
  Open a markdown file in a browser and leave block-level comments that are
  saved to a sidecar JSON file alongside it. The sidecar can then be applied
  to the source markdown by Claude in a follow-up turn.
allowed-tools: [Bash]
user-invocable: true
disable-model-invocation: true
argument-hint: "<path-to-markdown>"
arguments:
  - name: markdown_path
    description: Absolute or relative path to the markdown file to review.
    required: true
---

# annotate

Open the given markdown file in a local browser tab for block-level commenting. Comments are persisted to `<file>.comments.json` next to the source. When the user finishes, this skill prints a copy-pasteable next-turn prompt that you (Claude) can use to apply the comments to the source markdown in a separate turn (FR-30, FR-31).

This skill never edits the source markdown. Applying comments is a separate Claude turn — the user must ask for it.

## Step 1 — Launch the server in the background

Run the server detached so this turn can report the URL and end. The python process keeps running after the Bash call returns; the user stops it from the UI's **Done** button or by killing the PID.

```bash
LOG="$(mktemp -t mdreview.XXXXXX)"
nohup python3 "${CLAUDE_PLUGIN_ROOT}/server/annotate_server.py" "$1" >"$LOG" 2>&1 &
PID=$!
disown 2>/dev/null || true
# Wait up to ~5s for the URL line, an error, or early exit.
for _ in $(seq 1 25); do
  if grep -qE '^(http://|error:)' "$LOG"; then break; fi
  if ! kill -0 "$PID" 2>/dev/null; then break; fi
  sleep 0.2
done
echo "PID: $PID"
echo "Log: $LOG"
echo "---"
cat "$LOG"
```

Then interpret the output:

- **URL printed** (line starts with `http://`): report that URL and the PID to the user.
- **`another markdown-review instance is running`**: an earlier server is still up — surface its URL and `target_file` from the error message.
- **Other `error:` line**: report the error verbatim.

Do **not** block waiting for the server to exit. The Bash call must return immediately after the log check loop above.

While the server is running:
- Hover any block to reveal the comment icon; click it to add a comment.
- Multi-line comments. `Cmd/Ctrl+Enter` (or the "Add Comment" button) submits.
- Click **Done** in the UI to stop the server, or run `kill <PID>` later.

## Step 2 — Show the apply-comments prompt (FR-30)

Right after reporting the URL, give the user this exact next-turn prompt so they can paste it back in a new turn once they're finished. Replace `<MD_PATH>` with `$1`:

> Apply the comments from `<MD_PATH>.comments.json` to `<MD_PATH>`. Use the apply-comments instructions at `${CLAUDE_PLUGIN_ROOT}/skills/annotate/references/apply-comments-prompt.md`. Do not start applying until I confirm.

(The `references/apply-comments-prompt.md` template has the full step-by-step apply instructions for the next-turn Claude.)

**Important (FR-31):** Do not start applying comments in this turn. The user must explicitly ask in a separate turn.
