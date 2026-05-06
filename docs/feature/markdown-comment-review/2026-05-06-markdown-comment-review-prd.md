# PRD: Markdown Comment Review Skill

**Date:** 2026-05-06
**Status:** Approved
**Version:** 1.1

---

## 1. Why

Claude Code produces a steady stream of long markdown artifacts (PRDs, plans, design docs, READMEs) inside a terminal session, and reviewing them there is painful in two ways. First, raw markdown in the terminal is hard to read — headings, lists, tables, and code fences all blur together as flat text, so the user can't quickly skim a doc to find the parts that need attention. Second, the only way to ask for changes today is to describe them conversationally back to Claude ("in section 4, the third paragraph, change…"), which is verbose, error-prone, and frequently lands on the wrong block. The user wants to read the rendered doc in a browser and pin comments directly onto the blocks they want changed, then hand a single structured file back to Claude so the next revision applies the user's intent at exactly the right spots without round-tripping through prose descriptions of locations.

## 2. Goals & Non-Goals

**Goals**
- Render any markdown file in a browser with one command, with a per-block comment affordance.
- Persist comments to a sidecar file alongside the source markdown so Claude can ingest them in any later turn.
- Anchor comments to whole markdown blocks (heading, paragraph, list item, code block, table, blockquote) using an identifier stable enough to survive unrelated edits to the rest of the document.
- Run fully offline with no telemetry and no external network calls.

**Non-Goals**
- Direct in-browser editing of markdown source (all edits are applied by Claude from comments).
- Sentence-level or arbitrary-span anchoring (block-level only in v1).
- Multi-file or directory browsing UI (one file per skill invocation).
- Multi-user or collaborative commenting (single local user only).
- Always-on background daemon (server runs only while the user is reviewing).
- Live reload of the browser when the markdown file changes on disk.

## 3. User Stories

1. As an engineer reviewing a PRD draft Claude wrote, I want to leave anchored comments on specific sections, so the next revision changes exactly the parts I flagged.
2. As a doc author, I want comments saved in a file next to the markdown, so the feedback survives across Claude sessions and isn't trapped in one conversation.
3. As a reviewer, I want to see comments I left previously when I re-open the same file, so I can build on prior feedback instead of starting over.

## 4. Functional Requirements

**Invocation & lifecycle**
- **FR-01:** The skill is a namespaced slash command under a new plugin in `local-plugins/` (e.g. `/markdown-review:annotate <path-to-md>`). It accepts exactly one argument: the path to a markdown file.
- **FR-02:** On invocation, the skill starts a local web server bound to `127.0.0.1` on a free port and prints the URL (e.g. `http://127.0.0.1:8765`) to the conversation.
- **FR-03:** The skill instructs the user to open the URL in a browser and tells them how to finish (click "Done" in the UI or Ctrl-C in the terminal).
- **FR-04:** The server drains all in-flight sidecar write requests before shutting down. The "Done" button is disabled and labelled "Saving…" while any write is in flight, and re-enables once the queue is empty. Ctrl-C in the terminal performs the same drain before exit. After clean exit, the only persisted state is the sidecar comments file.
- **FR-05:** When invoked, if the markdown file does not exist, the skill exits with a clear error message before starting the server.
- **FR-06:** When the chosen default port is already in use, the skill auto-picks the next free port and reports it.
- **FR-07:** When the skill is invoked while another instance is already running, the second invocation refuses to start and reports the running instance's URL and target file. Detection must be cross-process (e.g. a PID/lock file or port probe) so it works across independent terminal sessions.
- **FR-08:** When the source markdown file's modification time changes after initial load, the UI shows a non-blocking banner: "Source file changed on disk. Anchors added after this point may be unstable." The banner exposes a Reload action that re-renders the document; existing comments are preserved across reload. Live reload is **not** required — the banner only appears on user interaction with the UI (e.g. before opening the next comment input).

**Rendering**
- **FR-09:** The browser UI renders the markdown using standard CommonMark + GFM-equivalent features: headings (h1–h6), paragraphs, ordered and unordered lists, nested lists, code blocks (with language tag), inline code, tables, blockquotes, links, images, bold, italic, strikethrough.
- **FR-10:** Each renderable block exposes a comment affordance on hover (e.g. a "comment" icon to the side of the block).
- **FR-11:** The UI loads all existing comments for the open file on first render and visibly associates each with its anchored block.

**Commenting**
- **FR-12:** The user can attach a free-text comment to any commentable block. Submitting the comment writes it to the sidecar file immediately.
- **FR-13:** The comment input is multi-line. Submission is via an explicit "Add Comment" button or Cmd/Ctrl+Enter; bare Enter inserts a newline.
- **FR-14:** A blank or whitespace-only comment is rejected with inline validation; the input remains open with a visible message and is not written to the sidecar.
- **FR-15:** Comment body length is capped at 2,000 characters; the input shows a live character counter and rejects submissions over the cap.
- **FR-16:** Pressing Escape or clicking outside the open input dismisses it without saving. If the user has typed any non-empty text, a "Discard draft?" confirmation appears before closing.
- **FR-17:** On successful save, the input clears and the new comment appears in the right-hand panel anchored to its block. If the save takes longer than 300ms, an inline spinner is shown on the input until the write completes.
- **FR-18:** The user can edit the body of an existing comment from the UI; the sidecar file is updated on save (subject to FR-14, FR-15).
- **FR-19:** The user can delete an existing comment from the UI; the sidecar file is updated on save.
- **FR-20:** A block can have more than one comment attached; comments are ordered by creation time.
- **FR-21:** Each comment is anchored by a stable block identifier scheme that survives edits to *other* blocks in the document. Specific scheme is deferred to the plan (see Open Questions).

**Persistence**
- **FR-22:** Comments are stored in a sidecar file at `<markdown-file>.comments.json` in the same directory as the markdown file.
- **FR-23:** Sidecar writes are atomic — written to a temp file in the same directory, then renamed over the destination — to prevent a partial write from corrupting the file.
- **FR-24:** If a sidecar write fails (disk full, permission denied, directory removed), the UI shows a persistent error banner ("Comment could not be saved — check disk space and permissions"), the affected comment is visually marked as "unsaved", and the "Done" button remains disabled until either the write succeeds on retry or the user explicitly acknowledges the failure.
- **FR-25:** The sidecar file is human-readable JSON, version-tagged, and contains for each comment: anchor identifier, comment body, creation timestamp, last-modified timestamp.
- **FR-26:** If the sidecar file's version tag is unrecognized by the current skill, the skill logs a warning and reads the file forward-compatibly; fields required by the current version that are missing are populated with defaults rather than rejecting the file.
- **FR-27:** When the user re-invokes the skill on the same file, existing comments load and render correctly (round-trip works).
- **FR-28:** When a comment's anchor cannot be resolved against the current markdown (the targeted block was removed or restructured), the comment is shown in a separate "Orphaned (N)" section in the UI but is **not** deleted from the sidecar file. Orphan detection runs once on initial load and once again when the user clicks "Done"; it does not run continuously while the user is commenting.
- **FR-29:** When the sidecar JSON is malformed, the skill backs the file up to `<file>.comments.json.bak` and starts a fresh sidecar; the UI shows a banner explaining the recovery.

**Handoff to Claude**
- **FR-30:** When the user finishes reviewing, the skill prints a copy-pasteable next-turn prompt that the user can use to ask Claude to apply the comments — e.g. "Apply the comments in `path/to/doc.md.comments.json` to `path/to/doc.md`."
- **FR-31:** Applying comments is **not** part of this skill — it is a separate Claude turn. The user must explicitly ask for it. This skill only produces the comment file.

**Offline & isolation**
- **FR-32:** The bundled web UI uses only assets shipped with the skill (no CDN fetches, no external font loads). The skill works on an air-gapped machine.

## 5. UX & Flow

**Happy path:**
1. User runs `/markdown-review:annotate docs/feature/foo/2026-05-06-foo-prd.md`.
2. Skill starts the local server, prints `http://127.0.0.1:8765` and a short usage hint.
3. User opens the URL → sees the rendered PRD with hover-revealed comment affordances on each block.
4. User clicks the comment icon on a block → input appears → types comment → submits → comment is persisted and shown in the right-hand panel.
5. User repeats for as many blocks as needed; can edit/delete existing comments inline.
6. User clicks "Done" in the UI → server shuts down → terminal prints the next-turn prompt.
7. User pastes / says "Apply the comments." → Claude reads the markdown + sidecar file and edits the markdown.

**States:**
- **Loading:** rendered doc appears as soon as the server is ready; comment panel shows "Loading…" briefly, then the comment list (or "No comments yet" if empty).
- **Empty:** no comments — the right panel reads "No comments yet. Hover any block and click the comment icon to add one."
- **Saving:** while a sidecar write is in flight, the affected comment shows an inline spinner and the global "Done" button is disabled and labelled "Saving…".
- **Source-changed banner:** when the markdown file's mtime changes mid-session, a non-blocking banner appears at the top of the rendered pane with a Reload action; comments are preserved on reload.
- **Orphaned comments:** when anchors do not resolve against the current parsed document (checked on load and on Done), a collapsed "Orphaned (N)" section appears at the top of the comment panel listing them with their original anchor info and body. Not deleted from the sidecar.
- **Save failure:** if a sidecar write fails, a persistent error banner appears at the top of the comment panel and the affected comment is visually marked "unsaved"; "Done" remains disabled until resolution or explicit acknowledgement.
- **Error:** markdown parse failure → render raw markdown source with a warning banner above ("This file could not be parsed cleanly. You can still comment, but anchors may be unstable."). Sidecar JSON corruption → see FR-29.
- **Port conflict:** auto-fallback (FR-06) — the printed URL just reflects the new port; no user-visible error.

**Mockups:** n/a — UI is a two-pane layout (rendered markdown on the left, comment list / thread on the right). No design system; ship plain HTML/CSS bundled with the skill.

## 6. Permissions, Privacy, Analytics

**Permissions:** Bash (to run the bundled server script), Read on the source markdown and sidecar file, Write on the sidecar file. No write access to the source markdown is needed — the skill never edits it.

**Data:** Comments are stored in plaintext JSON next to the source markdown. Nothing is uploaded, sent over the network, or logged outside the user's machine. The server only listens on `127.0.0.1`.

**Events:** None. No telemetry in v1.

**Success metric:** Within 30 days of ship, the skill is invoked at least once per active doc-writing week, and the sidecar handoff is sufficient — i.e. Claude's first revision after applying comments lands the user's intent without the user needing to re-prompt with location descriptions in prose.

## 7. Release

- **Feature flag:** n/a — local plugin.
- **Rollout:** Ship as a new plugin in `local-plugins/` (e.g. `local-plugins/markdown-review/`) with one skill (`annotate`). Distribution is single-machine for now; no marketplace publishing in v1.
- **Update required:** n/a — local files only.

## 8. Open Questions

- [ ] **Anchor scheme.** Heading-path (e.g. `## Goals > para 2`), sequential block index, content hash of the block, or a hybrid? Owner: plan author. Trade-off: heading-path is human-readable but breaks when headings move; index breaks when blocks are inserted; content hash breaks on any wording change. Hybrid (heading-path + content hash with fallback) is most robust but most complex.
- [ ] **Comment lifecycle after Claude applies them.** Does Claude clear applied comments from the sidecar, mark them as `applied: true` with a timestamp, or leave them for the user to clean up? Default proposal: mark as applied, keep in file, hide from default UI view.
- [ ] **Multiple-file workflow.** v1 is one file per invocation. If the user wants to comment across a directory of docs, do they invoke the skill N times, or is a `--dir` mode worth adding in v1.x? Defer.
- [ ] **Bundled-assets build step.** If the skill uses a JS-side markdown renderer, should those assets be vendored as pre-built files in the plugin, or built on first run? Default proposal: vendor pre-built — keeps invocation fast and offline-clean.
- [ ] **Stale-lock recovery on crash (declined for v1).** If the prior process crashed without releasing its PID/lock file, the skill currently refuses to start with a "running instance" message until the user manually clears the lock. Revisit only if this becomes a frequent annoyance in practice.

---

## Version History

New row on each status change (Draft → Approved → Shipped) or on a major revision.

| Version | Date | Notes |
|---|---|---|
| 1.0 | 2026-05-06 | Initial draft. |
| 1.1 | 2026-05-06 | Sharpened Why (terminal readability + conversational-edit pain). Critic pass 1 applied: drain-on-shutdown + Saving guard (FR-04), mtime-change banner (FR-08), cross-process duplicate detection (FR-07), comment input UX (multi-line, blank rejection, 2k-char cap, dismiss with Discard prompt — FR-13–FR-17), atomic writes + write-failure handling (FR-23, FR-24), forward-compatible sidecar version reads (FR-26), bounded orphan-detection timing (FR-28). Stale-lock crash recovery declined; moved to Open Questions. Success metric replaced with measurable target. |
