---
name: annotate
description: >-
  Open a markdown file in a browser and leave block-level comments that are
  saved to a sidecar JSON file alongside it. The skill launches the server in
  the harness's background (so python is tied to your Claude session, not
  orphaned) and auto-opens the URL in your default browser. To apply comments
  after clicking Done, ask Claude to "apply" — if "Auto-apply" was checked in
  the Submit modal, Claude proceeds without asking for confirmation.
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

Launch the local review server for the given markdown file and hand off to the user's browser. **This skill does not wait for the user to finish** — Step 2 returns as soon as the URL is visible. Applying comments happens in a separate turn.

The two Bash calls are split deliberately:

- **Step 1** runs python under `run_in_background: true` so the harness owns the process lifetime. No `nohup`, no `disown`, no shell `&`.
- **Step 2** is a fast foreground poll of the log Step 1 is writing — that's how we surface the URL and open the browser without blocking the turn.

## Step 1 — Launch the server (run_in_background: true)

**Invoke the Bash tool with `run_in_background: true`** so the python process starts but Claude's turn isn't blocked on its completion. The harness will keep python alive in the background until it exits (Done click, kill, or session end) and notify Claude when it does.

```bash
LOG="$1.review-server.log"
: > "$LOG"  # truncate any leftover from a prior run
python3 "${CLAUDE_PLUGIN_ROOT}/server/annotate_server.py" "$1" >"$LOG" 2>&1
```

Step 1 returns immediately because of `run_in_background: true` — but the python process is now writing its boot output to `$LOG` ("http://..." on success, "error:..." on failure).

## Step 2 — Surface the URL and open the browser (foreground)

**Run this with Bash (default foreground).** It polls the same log Step 1 is writing, prints the outcome, and best-effort opens the URL.

```bash
LOG="$1.review-server.log"
for _ in $(seq 1 50); do
  if grep -qE '^(http://|error:)' "$LOG" 2>/dev/null; then break; fi
  sleep 0.2
done

echo "Log: $LOG"
echo "---"
cat "$LOG" 2>/dev/null || true
echo "---"

URL=$(grep -m1 '^http://' "$LOG" 2>/dev/null || true)
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

## Step 3 — Interpret the outcome

### `OUTCOME: LAUNCHED`

The server is up and the URL was opened in the user's default browser. Tell the user:

- The URL printed above (also shown between the `---` markers) is now live. If the auto-open didn't take, they can paste the URL manually.
- They should click **Done** in the UI when finished. The browser tab will explain what happens next based on whether they checked **Auto-apply** in the Submit modal.
- When they're ready to apply, they can return and say "apply" (or paste the next-turn prompt from the Submit modal). If they checked Auto-apply, Claude will skip the confirmation prompt; otherwise Claude will ask before editing the file.

Then end the turn. **Do not** wait for Done; do not start applying comments in this turn.

### `OUTCOME: LAUNCH_FAILED`

The server never bound a port. The log between the `---` markers explains why. Common cases:

- `another markdown-review instance is running` — surface the running URL and `target_file` from the log so the user can return to that session.
- `stale lock file detected` — surface the manual-clear instruction from the log verbatim.
- `markdown file not found` / other `error:` lines — relay them as-is.

Do not retry; report and stop.
