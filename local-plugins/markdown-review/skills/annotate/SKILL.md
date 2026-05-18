---
name: annotate
description: >-
  Open a markdown file in a browser and leave block-level comments that are
  saved to a sidecar JSON file alongside it. The skill launches the server
  detached and returns immediately, auto-opening the URL in the user's default
  browser. To apply comments after clicking Done, ask Claude to "apply" — if
  "Auto-apply" was checked in the Submit modal, Claude applies without asking
  for confirmation.
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

Launch the local review server for the given markdown file and hand off to the user's browser. **This skill does not wait for the user to finish** — it returns as soon as the server has bound a port and the URL is visible. The user reviews on their own time; applying comments happens in a separate turn.

## Step 1 — Launch + auto-open

```bash
LOG="$(mktemp -t mdreview.XXXXXX)"
nohup python3 "${CLAUDE_PLUGIN_ROOT}/server/annotate_server.py" "$1" >"$LOG" 2>&1 &
PID=$!
disown 2>/dev/null || true

# Wait up to ~5s for a URL line, an error, or early exit.
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

URL=$(grep -m1 '^http://' "$LOG" || true)
if [ -z "$URL" ]; then
  echo "OUTCOME: LAUNCH_FAILED"
  exit 0
fi

# Best-effort cross-platform browser open. Each opener is detached and silent
# so it never blocks the skill or pollutes the log.
if command -v open >/dev/null 2>&1; then
  (open "$URL" >/dev/null 2>&1 &) || true
elif command -v xdg-open >/dev/null 2>&1; then
  (xdg-open "$URL" >/dev/null 2>&1 &) || true
elif command -v wslview >/dev/null 2>&1; then
  (wslview "$URL" >/dev/null 2>&1 &) || true
fi

echo "OUTCOME: LAUNCHED"
```

The python server keeps running after this Bash call returns — `nohup` + `disown` detaches it from this shell so it survives the skill turn ending.

## Step 2 — Interpret the outcome

### `OUTCOME: LAUNCHED`

The server is up. Tell the user:

- The URL printed above (also shown between the `---` markers) is now open in their default browser. If the auto-open didn't take, they can paste it manually.
- They should click **Done** in the UI when finished. The browser tab will tell them what happens next based on whether they checked **Auto-apply** in the Submit modal.
- When they're ready to apply, they can return and say "apply" (or paste the next-turn prompt from the Submit modal). If they checked Auto-apply, Claude will skip the confirmation prompt; otherwise Claude will ask before editing the file.

Then end the turn. **Do not** wait for Done; do not start applying comments in this turn.

### `OUTCOME: LAUNCH_FAILED`

The server never bound a port. The log between the `---` markers explains why. Common cases:

- `another markdown-review instance is running` — surface the running URL and `target_file` from the log so the user can return to that session.
- `stale lock file detected` — surface the manual-clear instruction from the log verbatim.
- `markdown file not found` / other `error:` lines — relay them as-is.

Do not retry; report and stop.
