# Plan: Markdown Comment Review Skill

**Date:** 2026-05-06
**Status:** Approved
**Based on:** docs/feature/markdown-comment-review/2026-05-06-markdown-comment-review-prd.md

---

## 1. Approach

Ship a new plugin `local-plugins/markdown-review/` containing one user-invocable skill `annotate`. The skill body shells out to a bundled Python script (`server/annotate_server.py`) that starts a stdlib `ThreadingHTTPServer` on `127.0.0.1:<free-port>` and serves a vanilla HTML/CSS/JS frontend rendered from `server/static/`.

All markdown parsing happens **server-side in Python** — the browser is dumb and just renders pre-parsed block HTML. We vendor [`mistune` v3](https://github.com/lepture/mistune) (BSD, single-file, GFM-capable) under `server/vendor/mistune.py` so the plugin works on a fresh machine with no `pip install` step. The server walks mistune's AST to produce an ordered list of `Block` records (heading, paragraph, list item, code block, table, blockquote) with rendered HTML, plain text, and a stable anchor.

**Anchor scheme — heading-path + index + content-prefix hash + preview** (closes PRD §8 Open Question 1). Each block's anchor is `{heading_path, block_index_in_section, text_hash, preview}` where `text_hash = sha256(plain_text)[:12]` and `preview = plain_text[:100]`. Resolution on re-open: try exact match on all four → fall back to `(heading_path, block_index)` (handles rename) → fall back to `text_hash` alone (handles move) → orphan. This composite anchor is stable across most ordinary edits, human-readable for Claude's apply step, and recoverable when individual axes break.

**Lifecycle and drain.** Comment writes are serialized through a single background worker thread guarded by a `threading.Lock`; an atomic counter tracks in-flight writes. `POST /api/done` flips the server into a "draining" state (refuses new writes) and blocks until the counter is zero, then triggers shutdown via `threading.Timer`. `SIGINT` runs the same drain. The browser disables the Done button whenever the response from any prior write reports `pending_writes > 0`. This satisfies FR-04 without async machinery.

**Cross-process duplicate detection (FR-07).** Lock file at `~/.cache/markdown-review/lock.json` carries `{pid, port, target_file, started_at}`. Startup reads the lock, then **port-probes** (`socket.create_connection((127.0.0.1, port), timeout=0.2)`) to confirm liveness — only a responding port refuses the second instance. A non-responding port is reported as a stale lock with manual-clear instructions (per PRD §8 explicit decline of auto-clear).

**Apply-step handoff** is a template at `skills/annotate/references/apply-comments-prompt.md`, surfaced by the skill body when the server exits — Claude in the next turn reads source markdown + sidecar JSON and applies edits. The skill itself never edits the source markdown.

## 2. File-by-file Changes

| File | Change | Notes |
|------|--------|-------|
| `local-plugins/markdown-review/.claude-plugin/plugin.json` | new | Plugin manifest: name, version, description, author. |
| `local-plugins/markdown-review/README.md` | new | Plugin overview, install, invocation, sidecar format, handoff. |
| `local-plugins/markdown-review/skills/annotate/SKILL.md` | new | Frontmatter (`name`, `description`, `disable-model-invocation: true`, `arguments`) + body: invokes server via `python3 ${CLAUDE_PLUGIN_ROOT}/server/annotate_server.py "$1"`. Body also includes the post-exit user-facing copy of the apply-comments prompt. |
| `local-plugins/markdown-review/skills/annotate/references/apply-comments-prompt.md` | new | Template instructing next-turn Claude to read source MD + sidecar and apply each unapplied comment. |
| `local-plugins/markdown-review/server/annotate_server.py` | new | HTTP server, routes, drain semantics, SIGINT handler, port fallback, mtime endpoint, static serving. Entry point. |
| `local-plugins/markdown-review/server/markdown_blocks.py` | new | mistune-AST-walker → `Block[]`; anchor builder; resolver (`resolve_anchor(anchor, blocks) -> Block | None`). |
| `local-plugins/markdown-review/server/sidecar.py` | new | Read/write/backup of `<file>.comments.json`; atomic temp-file-rename; version tag handling; malformed-JSON backup. |
| `local-plugins/markdown-review/server/lockfile.py` | new | Acquire/probe/release `~/.cache/markdown-review/lock.json` with port-probe liveness check. |
| `local-plugins/markdown-review/server/vendor/__init__.py` | new | Empty marker. |
| `local-plugins/markdown-review/server/vendor/mistune.py` | new | Vendored single-file mistune v3 (BSD-3). |
| `local-plugins/markdown-review/server/vendor/LICENSE-mistune` | new | Verbatim mistune license text. |
| `local-plugins/markdown-review/server/static/index.html` | new | Two-pane layout shell; mounts `app.js`. |
| `local-plugins/markdown-review/server/static/app.css` | new | Two-pane flex layout, comment-affordance hover, banners (mtime, save-failure), Saving state. |
| `local-plugins/markdown-review/server/static/app.js` | new | Frontend logic: fetch document, render blocks, hover affordance, comment input UX, save flow, Done flow, mtime banner, orphan list, save-failure banner. |
| `local-plugins/markdown-review/tests/test_markdown_blocks.py` | new | unittest tests for block parsing + anchor stability + resolver fallbacks. |
| `local-plugins/markdown-review/tests/test_sidecar.py` | new | Round-trip, atomic-write atomicity (concurrent-write probe), malformed-JSON backup, version-tag forward-compat. |
| `local-plugins/markdown-review/tests/test_lockfile.py` | new | Acquire/release/probe/stale-lock-detection. |
| `local-plugins/markdown-review/tests/test_server.py` | new | Spawns the server, hits routes via `urllib.request`. Covers happy path, 404, port fallback, drain on Done, mtime change banner trigger, blank/oversize comment rejection. |
| `local-plugins/markdown-review/tests/e2e.sh` | new | Smoke script: start server, POST a comment, GET document, assert sidecar contents, click Done. Used as a final integration check. |

## 3. Types & Interfaces

> Verbatim Python — implementer subagents copy these directly.

```python
# server/markdown_blocks.py

from dataclasses import dataclass, asdict
from typing import Literal, Optional

BlockKind = Literal[
    "heading", "paragraph", "list_item", "code_block",
    "table", "blockquote", "thematic_break"
]

@dataclass(frozen=True)
class Anchor:
    """Stable identifier for a single block."""
    heading_path: str            # e.g. "## Goals & Non-Goals > Non-Goals"
    block_index_in_section: int  # 0-based, counts non-heading blocks under heading_path
    text_hash: str               # sha256(plain_text)[:12]
    preview: str                 # plain_text[:100]

@dataclass
class Block:
    kind: BlockKind
    anchor: Anchor
    html: str                    # sanitized HTML (mistune escapes by default)
    plain_text: str              # used for hashing + preview
    heading_level: Optional[int] = None  # set when kind == "heading"

def parse_blocks(markdown_source: str) -> list[Block]: ...

def anchor_dict(a: Anchor) -> dict: return asdict(a)

class ResolveOutcome:
    EXACT = "exact"
    BY_PATH_INDEX = "by_path_index"   # heading rename tolerated
    BY_HASH = "by_hash"                # block moved tolerated
    ORPHAN = "orphan"

@dataclass
class ResolveResult:
    outcome: str                  # one of ResolveOutcome.*
    block: Optional[Block]        # None iff outcome == ORPHAN

def resolve_anchor(anchor: Anchor, blocks: list[Block]) -> ResolveResult: ...
```

```python
# server/sidecar.py

from dataclasses import dataclass
from typing import Optional

SIDECAR_VERSION = 1
COMMENT_BODY_MAX_CHARS = 2000

@dataclass
class Comment:
    id: str                       # uuid4
    anchor: dict                  # serialized Anchor
    body: str
    created_at: str               # ISO-8601 UTC
    updated_at: str               # ISO-8601 UTC
    applied: bool = False         # set by next-turn Claude after apply
    applied_at: Optional[str] = None

@dataclass
class Sidecar:
    version: int
    source_file: str              # absolute path to the .md
    comments: list[Comment]

class SidecarWriteError(RuntimeError): ...

def read_sidecar(path: str) -> tuple[Sidecar, list[str]]:
    """Returns (sidecar, warnings). Warnings include version-mismatch notes
    and 'malformed-recovered' when a backup was created."""
    ...

def write_sidecar_atomic(path: str, sidecar: Sidecar) -> None:
    """Writes <path>.tmp then os.replace() to <path>. Raises SidecarWriteError
    on any I/O failure (caller surfaces this as FR-24 banner)."""
    ...
```

```python
# server/lockfile.py

from dataclasses import dataclass
from typing import Optional

LOCK_PATH = "~/.cache/markdown-review/lock.json"  # expanduser at runtime

@dataclass
class LockInfo:
    pid: int
    port: int
    target_file: str
    started_at: str               # ISO-8601 UTC

class LockState:
    FREE = "free"                 # no lock file
    RUNNING = "running"           # lock file present and port responds
    STALE = "stale"               # lock file present but port does not respond

@dataclass
class LockProbeResult:
    state: str                    # one of LockState.*
    info: Optional[LockInfo]      # populated for RUNNING and STALE

def probe_lock() -> LockProbeResult: ...
def acquire_lock(info: LockInfo) -> None: ...   # writes lock file (no auto-clear of stale)
def release_lock() -> None: ...                  # called on clean exit + SIGINT drain
```

```python
# server/annotate_server.py — public surface only

class ServerState:
    INITIALIZING = "initializing"
    READY = "ready"
    DRAINING = "draining"
    STOPPED = "stopped"

# Routes:
#   GET  /                       -> static/index.html
#   GET  /static/<file>          -> static/<file>
#   GET  /api/document           -> { blocks, comments, sidecar_warnings, source_mtime }
#   GET  /api/document/changed   -> { changed: bool, current_mtime, loaded_mtime }
#   POST /api/comments           -> { comment, pending_writes }    body: { anchor, body }
#   PUT  /api/comments/<id>      -> { comment, pending_writes }    body: { body }
#   DELETE /api/comments/<id>    -> { ok, pending_writes }
#   POST /api/done               -> blocks until pending_writes == 0; { ok, orphans }
#   GET  /api/health             -> { state, port, target_file }   used by lock probe

# Validation responses:
#   422 on blank body, oversize body, or unknown anchor
#   409 on edit/delete of unknown comment id
#   503 on writes while state == DRAINING
```

```javascript
// server/static/app.js — public surface (state shape only)

const STATE = {
  blocks: [],          // Block[] from /api/document
  comments: [],        // Comment[]
  loadedMtime: 0,
  pendingWrites: 0,
  serverState: "ready",
  draftAnchor: null,   // Anchor object | null — which block has an open input
  draftBody: "",
  saveFailures: [],    // [{commentId, message}]
  sourceChanged: false // FR-08 banner state
};
```

## 4. Test Plan

> One bullet per test. References the FR + the §5 task. Skeletons included for non-trivial assertions.

**Unit: `markdown_blocks.py` (task 3)**
- **FR-09** (task 3): `parses CommonMark + GFM features into expected block kinds` — covers headings, paragraphs, list items, nested lists, fenced code with lang, tables, blockquotes, links/images/strong/em/strike.
- **FR-09** (task 3): `script tags in source are escaped, not preserved` — sanitization assertion.
- **FR-21** (task 3): `anchor is stable across edits to other blocks` — edit a paragraph, assert untouched paragraphs keep the same anchor.
- **FR-21** (task 3): `resolver finds exact match` / `falls back to (heading_path, index) on hash change` / `falls back to hash-only on heading rename` / `returns ORPHAN when no axis matches`.
  ```python
  def test_resolver_falls_back_to_hash_on_rename():
      blocks_before = parse_blocks("## Goals\n\nFirst paragraph.\n")
      anchor = blocks_before[1].anchor
      blocks_after = parse_blocks("## Aims\n\nFirst paragraph.\n")
      result = resolve_anchor(anchor, blocks_after)
      assert result.outcome == ResolveOutcome.BY_HASH
      assert result.block.plain_text == "First paragraph."
  ```

**Unit: `sidecar.py` (task 4)**
- **FR-22** (task 4): `write then read returns identical sidecar` — round-trip including comment bodies with multi-byte UTF-8.
- **FR-23** (task 4): `partial write is invisible — readers see either old file or new file` — simulate by patching `os.replace` to verify temp-file-then-rename ordering.
- **FR-25** (task 4): `sidecar version tag is written and read`.
- **FR-26** (task 4): `unknown future version still loads with warning, missing fields default`.
- **FR-29** (task 4): `malformed JSON triggers backup to .bak and fresh sidecar with warning`.

**Unit: `lockfile.py` (task 5)**
- **FR-07** (task 5): `probe returns FREE when no lock file`.
- **FR-07** (task 5): `probe returns RUNNING when lock file exists and port is open` — bind a temp socket to mimic a live server.
- **FR-07** (task 5): `probe returns STALE when lock file exists but port refuses connection` — uses an unbound port number in the lock.

**Integration: `annotate_server.py` (task 6)**
- **FR-02** (task 6): `server starts on 127.0.0.1 and prints URL with reachable port`.
- **FR-05** (task 6): `missing markdown file → exits with non-zero before binding the port`.
- **FR-06** (task 6): `port already in use → server picks next free port and reports it` — pre-bind the default port, observe fallback.
- **FR-07** (task 6): `second invocation while first is running → exits non-zero, reports running URL + target file` — mocks `probe_lock` to return RUNNING.
- **FR-04** (task 6): `Done waits for pending writes to drain before shutdown`.
  ```python
  def test_done_drains_writes():
      with running_server(tmp_md) as srv:
          slow_post(srv, "/api/comments", {...})  # forces pending_writes > 0
          resp = post(srv, "/api/done")
          assert resp.status == 200
          assert read_sidecar(tmp_md_sidecar).comments[-1].body == "..."
  ```
- **FR-08** (task 6): `GET /api/document/changed returns changed=true after the source file's mtime advances`.
- **FR-12, FR-14, FR-15** (task 6): `POST /api/comments rejects blank body (422) and bodies over 2000 chars (422); accepts a normal body (201) and persists it`.
- **FR-19** (task 6): `DELETE /api/comments/<id> removes the comment from sidecar`.
- **FR-20** (task 6): `multiple comments on the same anchor are persisted in creation order`.
- **FR-28** (task 6): `Done response payload includes the orphan list when source has changed mid-session`.

**Frontend (task 8)** — manual checklist exercised by `tests/e2e.sh`; per-FR assertions printed and verified.
- **FR-10**: hover any block → comment icon visible.
- **FR-11**: existing comments load on first render and visibly anchor to their blocks.
- **FR-13**: input is multi-line; bare Enter inserts newline; Cmd/Ctrl+Enter and the "Add Comment" button submit.
- **FR-14**: blank submission shows inline message and does not write.
- **FR-15**: typing past 2000 chars blocks input; counter is visible and accurate.
- **FR-16**: Escape on dirty input shows "Discard draft?"; Escape on empty input dismisses immediately.
- **FR-17**: on save, input clears; comment appears anchored; spinner appears if save >300ms (forced by injecting a `?slow=400` query the dev server honors in test mode).
- **FR-18, FR-19**: existing comment can be edited and deleted; sidecar updated.
- **FR-24**: forcing a write failure (read-only sidecar dir, set via test mode) shows the persistent banner; Done remains disabled until acknowledged.

**End-to-end: `tests/e2e.sh` (task 9)**
- **FR-01, FR-02, FR-22, FR-30** (task 9): script invokes the skill body's `python3 …/annotate_server.py <md>`, curls `/api/document`, posts a comment, posts `/api/done`, then asserts: server exits 0, sidecar JSON exists, contains the comment, no orphans on a clean file, the printed apply-comments prompt is non-empty.

**FR-coverage cross-check** (none lost in translation):
- FR-01 → tasks 6 (server takes path arg), 10 (skill body wires `$1`).
- FR-02–FR-07 → task 6.
- FR-08 → task 6 + task 8.
- FR-09–FR-11 → tasks 3, 6, 7, 8.
- FR-12–FR-20 → tasks 3, 4, 6, 8.
- FR-21 → tasks 3, 4.
- FR-22–FR-29 → tasks 4, 6.
- FR-30, FR-31 → tasks 10, 11 (skill body + apply-comments template).
- FR-32 → task 7 (no CDN), enforced by `tests/e2e.sh` running with network blocked is *out of scope* (single-machine local check via `grep -r "https?://" static/` in the e2e script).

## 5. Tasks

1. **[model: haiku]** Plugin skeleton
   - Files: `local-plugins/markdown-review/.claude-plugin/plugin.json`, `local-plugins/markdown-review/README.md`
   - Depends on: —
   - Done when: `plugin.json` declares `markdown-review` v0.1.0 with description and author; README has install + invocation outline; both files lint as valid JSON / markdown.

2. **[model: haiku]** Vendor mistune v3
   - Files: `server/vendor/__init__.py`, `server/vendor/mistune.py`, `server/vendor/LICENSE-mistune`
   - Depends on: 1
   - Done when: `python3 -c "from server.vendor import mistune; print(mistune.__version__)"` succeeds when run from the plugin root; LICENSE file matches upstream BSD-3 text.

3. **[model: sonnet]** Block parser + anchor builder + resolver
   - Files: `server/markdown_blocks.py`, `tests/test_markdown_blocks.py`
   - Depends on: 2
   - Done when: §3 types implemented; all `test_markdown_blocks.py` tests pass; FR-09 and FR-21 covered.

4. **[model: sonnet]** Sidecar read/write
   - Files: `server/sidecar.py`, `tests/test_sidecar.py`
   - Depends on: 1
   - Done when: round-trip + atomic-write + malformed-JSON-backup + version-tag tests pass; FR-22, FR-23, FR-25, FR-26, FR-29 covered.

5. **[model: sonnet]** Lock file
   - Files: `server/lockfile.py`, `tests/test_lockfile.py`
   - Depends on: 1
   - Done when: `probe_lock` distinguishes FREE / RUNNING / STALE in tests; `acquire`/`release` round-trip; FR-07 detection covered.

6. **[model: opus]** HTTP server + lifecycle
   - Files: `server/annotate_server.py`, `tests/test_server.py`
   - Depends on: 3, 4, 5
   - Done when: all routes from §3 respond as documented; drain semantics verified by `test_done_drains_writes`; SIGINT triggers same drain (verified by spawning subprocess + `os.kill(SIGINT)`); port fallback works; FR-02, FR-04, FR-05, FR-06, FR-07, FR-08, FR-12, FR-14, FR-15, FR-19, FR-20, FR-28 server-side tests pass.

7. **[model: sonnet]** Static frontend skeleton
   - Files: `server/static/index.html`, `server/static/app.css`
   - Depends on: 1
   - Done when: HTML mounts an empty `#doc` and `#comments` pane; CSS provides two-pane flex layout, hover-revealed comment icon, banner styles for mtime/save-failure, "Saving…" Done button state. No external resources referenced (`grep -E "https?://" static/` returns empty).

8. **[model: sonnet]** Frontend interactivity
   - Files: `server/static/app.js`
   - Depends on: 6, 7
   - Done when: state shape from §3 implemented; UI checklist for FR-10, FR-11, FR-13, FR-14, FR-15, FR-16, FR-17, FR-18, FR-19, FR-24, FR-28 passes when driven through `tests/e2e.sh`.

9. **[model: sonnet]** End-to-end smoke
   - Files: `tests/e2e.sh`
   - Depends on: 6, 8
   - Done when: script starts the server with a fixture markdown file, posts a comment, asserts sidecar is written, posts `/api/done`, asserts clean exit and printed apply-prompt; exits 0.

10. **[model: haiku]** Skill metadata + invocation body
    - Files: `local-plugins/markdown-review/skills/annotate/SKILL.md`
    - Depends on: 6
    - Done when: SKILL.md frontmatter has `name`, `description`, `disable-model-invocation: true`, `arguments` (single positional `markdown_path`); body invokes `python3 ${CLAUDE_PLUGIN_ROOT}/server/annotate_server.py "$1"` and afterwards renders the apply-comments prompt for the user (FR-30, FR-31).

11. **[model: haiku]** Apply-comments prompt template + README
    - Files: `local-plugins/markdown-review/skills/annotate/references/apply-comments-prompt.md`, `local-plugins/markdown-review/README.md` (extend stub from task 1)
    - Depends on: 10
    - Done when: template instructs next-turn Claude to (a) read source MD, (b) read sidecar, (c) for each `applied: false` comment, locate by `anchor.heading_path` + `anchor.preview` and apply the user's instruction, (d) set `applied: true` + `applied_at` on success, (e) leave any unresolved as orphans with a written summary back to the user; README documents file layout, sidecar format, and the handoff loop.

## 6. Risks & Open Questions

- **Risk:** mistune-AST walk produces an off-by-one in `block_index_in_section` for documents that begin with a non-heading paragraph (no enclosing heading). **Mitigation:** treat the implicit pre-heading scope as `heading_path = ""` and test it explicitly in task 3.
- **Risk:** Atomic-rename guarantee on macOS `os.replace` across hard links / network mounts. **Mitigation:** sidecar lives in the same directory as the source markdown (FR-22), so `os.replace` is intra-filesystem in all realistic cases. Document this constraint in README.
- **Risk:** Vendoring mistune drifts from upstream over time. **Mitigation:** record vendored version + commit hash in `LICENSE-mistune`'s header; re-vendor opportunistically.
- **Risk:** `threading.Timer`-based shutdown after Done might race with the response write. **Mitigation:** schedule the shutdown for `>= 100ms` after the response is sent, and have the browser tolerate connection-reset on the Done call (it already shows "Server stopped" optimistically).
- **Risk:** Browser's `Cmd/Ctrl+Enter` capture conflicts with the OS-level shortcut on some platforms. **Mitigation:** tested on macOS Safari + Chromium; document fallback "Add Comment" button is always available.
- **Open question:** Should `applied: true` comments be hidden from the UI by default? PRD §8 default proposal is yes. The frontend in task 8 will implement "hide applied" as a panel toggle defaulting to on; revisit if it causes confusion in actual use.
- **Open question:** Whether to expose a `--port` CLI flag in v1 for users who want a deterministic port. Not required by any FR; defer until requested.
