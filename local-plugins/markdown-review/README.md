# markdown-review

A local plugin that opens a markdown file in a browser for block-level commenting. Comments are saved to a sidecar JSON file alongside the source. A follow-up Claude turn reads the sidecar and applies the user's comments to the source.

## Install

This is a local plugin. It is automatically discovered from `local-plugins/markdown-review/` — no install step required.

## Invocation

```
/markdown-review:annotate <path-to-markdown>
```

Example:

```
/markdown-review:annotate docs/feature/foo/2026-05-06-foo-prd.md
```

The skill prints a `http://127.0.0.1:<port>` URL **and auto-opens it in your default browser** (via `open` / `xdg-open` / `wslview`). The Claude turn ends immediately — the server is started under the harness's `run_in_background: true` so python is tied to your Claude session and gets cleaned up when the session ends. Boot output is captured at `<source>.review-server.log` (safe to delete). Hover any block to reveal the comment icon; click it to add a comment. Multi-line comments. `Cmd/Ctrl+Enter` (or the "Add Comment" button) submits.

When you're ready, open **Submit & Done** in the panel footer. The modal has an **Auto-apply comments when I click Done** checkbox that controls the next turn:

- **Checked** — clicking Done writes a `<file>.comments.json.auto_apply_pending` marker next to the sidecar. On your next turn, when you say "apply", Claude detects the marker and applies your comments without an extra confirmation prompt.
- **Unchecked** — clicking Done just stops the server. The next time you ask Claude to apply, you'll be asked for explicit confirmation before any edits happen.

## What it does

- Starts a local Python web server on `127.0.0.1` (free port; default 8765).
- Renders the markdown file (server-side, with vendored mistune v3).
- Lets you leave per-block comments through a browser UI.
- Persists comments to `<file>.comments.json` next to the source markdown.
- Never modifies the source markdown directly. Applying comments is a separate Claude turn (`FR-31`).

## Files & layout

```
local-plugins/markdown-review/
├── .claude-plugin/plugin.json
├── README.md                     ← this file
├── skills/annotate/
│   ├── SKILL.md                  ← skill body; invokes the server
│   └── references/
│       └── apply-comments-prompt.md   ← read by next-turn Claude when applying
├── server/
│   ├── annotate_server.py        ← entry point; HTTP server + lifecycle
│   ├── markdown_blocks.py        ← block parsing + anchors + resolver
│   ├── sidecar.py                ← read/write of the .comments.json
│   ├── lockfile.py               ← cross-process duplicate detection
│   ├── static/                   ← bundled HTML/CSS/JS frontend (offline)
│   │   ├── index.html
│   │   ├── app.css
│   │   └── app.js
│   └── vendor/
│       ├── mistune/              ← vendored mistune v3 (BSD-3)
│       └── LICENSE-mistune
└── tests/                        ← unittest + e2e.sh
```

## Sidecar format

The sidecar is human-readable JSON, version-tagged, and stored next to the source as `<file>.comments.json`. Schema (see `server/sidecar.py` for the dataclass definitions):

```json
{
  "version": 1,
  "source_file": "/abs/path/to/doc.md",
  "comments": [
    {
      "id": "<uuid4 hex>",
      "anchor": {
        "heading_path": "## Section > ### Subsection",
        "block_index_in_section": 1,
        "text_hash": "abcd1234ef56",
        "preview": "First 100 chars of the block's plain text…"
      },
      "body": "Replace this paragraph with a clearer summary.",
      "created_at": "2026-05-06T13:42:00+00:00",
      "updated_at": "2026-05-06T13:42:00+00:00",
      "applied": false,
      "applied_at": null
    }
  ]
}
```

Anchor scheme: heading-path + block index + content-prefix hash + preview. Resolution prefers exact match → `(heading_path, block_index_in_section)` (handles heading rename) → `text_hash` alone (handles block move) → orphan.

Atomic writes: the sidecar is written to `<file>.comments.json.tmp` and renamed via `os.replace()`. Malformed JSON is backed up to `<file>.comments.json.bak`; a fresh sidecar is written and a UI banner explains the recovery (FR-29).

## Handoff loop

1. **Annotate** — `/markdown-review:annotate <path>`. The skill issues two Bash calls: Call 1 launches python under `run_in_background: true` so the harness owns the process lifetime (no orphans on session exit), Call 2 polls the boot log at `<source>.review-server.log` and auto-opens the URL in your browser. The Claude turn ends as soon as the URL is visible.
2. **Done** — clicking "Done" in the UI (or `Ctrl-C` in the terminal) drains pending writes and shuts down the server. The Submit modal's auto-apply checkbox decides what next-turn apply looks like:
   - **Auto-apply on** — the server writes `<file>.comments.json.auto_apply_pending` next to the sidecar before shutting down.
   - **Auto-apply off** (or server killed externally) — no marker is written (any stale marker is cleared).
3. **Apply** — in a new turn, ask Claude to "apply". Claude reads `skills/annotate/references/apply-comments-prompt.md`, checks for the marker, and either proceeds without asking (marker present) or asks you for explicit confirmation first (marker absent). It then snapshots the source, edits per each unapplied comment via `Edit`, marks each successfully applied comment as `applied: true` with `applied_at`, and clears the marker.

The full apply-step instructions live at `skills/annotate/references/apply-comments-prompt.md`.

## Pre-apply snapshot

Right before Claude edits the source markdown, the apply step copies the file to `<file>.review-snapshot.md`. The server reads that snapshot on every `/api/document` request and ships a `changed_block_ids` list to the UI; blocks whose content differs from the snapshot get a green left-edge accent and are summarised in a **Recently edited by Claude** section in the right panel. The snapshot is overwritten on each subsequent apply, so the highlights always reflect *this* review cycle's edits — not cumulative drift.

The snapshot is purely informational and safe to delete. Add `*.review-snapshot.md` to `.gitignore` if you'd rather not check it in.

## Offline & isolation

The bundled UI uses only assets shipped with this plugin (FR-32). No CDN, no external font loads. The server only listens on `127.0.0.1`. Comments and the source markdown never leave your machine.

## Cross-process duplicate detection

When invoked while another instance of this plugin is already running, the second invocation refuses to start and reports the running URL + target file (FR-07). Detection uses a lock file at `~/.cache/markdown-review/lock.json` plus a port liveness probe. Stale locks (lock file present, port not responding) are reported with manual-clear instructions — no auto-clear (PRD §8 explicit decline).

## Status

v0.2.1 — server now launched via `run_in_background: true` (harness owns python lifetime instead of `nohup` outliving the session). Builds on v0.2.0: detached skill + auto-open browser, auto-apply marker for next-turn apply, "Recently edited by Claude" highlights from a pre-apply snapshot.
