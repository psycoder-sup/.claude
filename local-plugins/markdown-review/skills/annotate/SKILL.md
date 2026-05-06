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

## Step 1 — Run the server

Run the bundled server. It binds to a free port on 127.0.0.1, prints the URL, and waits until the user clicks Done in the browser or sends Ctrl-C.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/server/annotate_server.py" "$1"
```

If the markdown file does not exist, the server exits non-zero with an error before binding. If another instance is already running (lock file at `~/.cache/markdown-review/lock.json`), the second invocation refuses to start and reports the running URL + target file.

While the server is running:
- Open the printed URL in a browser.
- Hover any block to reveal the comment icon; click it to add a comment.
- Multi-line comments. `Cmd/Ctrl+Enter` (or the "Add Comment" button) submits.
- Click "Done" in the UI (or `Ctrl-C` here in the terminal) to stop the server.

## Step 2 — Show the apply-comments prompt (FR-30)

After the server exits, present the user with this exact next-turn prompt so they can paste it back to Claude. Replace `<MD_PATH>` with `$1`:

> Apply the comments from `<MD_PATH>.comments.json` to `<MD_PATH>`. Use the apply-comments instructions at `${CLAUDE_PLUGIN_ROOT}/skills/annotate/references/apply-comments-prompt.md`. Do not start applying until I confirm.

(The `references/apply-comments-prompt.md` template, populated by task 11, has the full step-by-step apply instructions for the next-turn Claude.)

**Important (FR-31):** Do not start applying comments in this turn. The user must explicitly ask in a separate turn.
