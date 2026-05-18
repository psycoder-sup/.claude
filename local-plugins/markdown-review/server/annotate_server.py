"""
HTTP server + lifecycle for the markdown-review plugin.

Implements the routes described in plan §3:

    GET  /                       -> static/index.html (or placeholder)
    GET  /static/<file>          -> static/<file>
    GET  /api/document           -> { blocks, comments, sidecar_warnings, source_mtime }
    GET  /api/document/changed   -> { changed, current_mtime, loaded_mtime }
    POST /api/comments           -> { comment, pending_writes }    body: { anchor, body }
    PUT  /api/comments/<id>      -> { comment, pending_writes }    body: { body }
    DELETE /api/comments/<id>    -> { ok, pending_writes }
    POST /api/done               -> blocks until pending_writes == 0; { ok, orphans }
    GET  /api/health             -> { state, port, target_file }

Drain semantics:

* Comment writes are serialized through ``ctx.write_lock``. ``ctx.pending_writes``
  is incremented under ``ctx.state_lock`` before the write begins and decremented
  in a ``finally`` clause when it completes (success or failure).
* ``POST /api/done`` flips state to ``DRAINING`` (further writes 503), launches
  ``drain_and_stop`` in a background thread, and waits on ``ctx.drain_event``
  before sending the response. The shutdown is scheduled via a ``threading.Timer``
  so the response can flush first.
* ``SIGINT`` runs the same ``drain_and_stop`` flow.

FRs covered: FR-02, FR-04, FR-05, FR-06, FR-07, FR-08, FR-12, FR-14, FR-15,
FR-19, FR-20, FR-28.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import signal
import socket
import sys
import threading
import time
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Optional
from urllib.parse import unquote, urlparse

# Allow `python3 server/annotate_server.py` to find sibling modules under
# `server.*` without requiring `python3 -m` or an external PYTHONPATH.
_PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, _PLUGIN_ROOT)

from server.lockfile import (
    LockInfo,
    LockState,
    _resolve_lock_path,
    acquire_lock,
    probe_lock,
    release_lock,
)
from server.markdown_blocks import (
    Anchor,
    ResolveOutcome,
    anchor_dict,
    parse_blocks,
    resolve_anchor,
)
from server.sidecar import (
    COMMENT_BODY_MAX_CHARS,
    SIDECAR_VERSION,
    Comment,
    Sidecar,
    SidecarWriteError,
    read_sidecar,
    write_sidecar_atomic,
)
from server.snapshot import read_snapshot


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class ServerState:
    INITIALIZING = "initializing"
    READY = "ready"
    DRAINING = "draining"
    STOPPED = "stopped"


DEFAULT_PORT = 8765
PORT_FALLBACK_RANGE = 50  # try DEFAULT_PORT..DEFAULT_PORT+49
DRAIN_TIMEOUT_SECONDS = 30.0
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
PLACEHOLDER_INDEX_HTML = (
    "<!doctype html><html><body>"
    "annotate placeholder &mdash; frontend pending (task 7/8)"
    "</body></html>"
)


# ---------------------------------------------------------------------------
# AppContext
# ---------------------------------------------------------------------------

class AppContext:
    """Shared mutable state across handler threads.

    Threading rules:
      * ``state_lock`` guards ``state`` and ``pending_writes``.
      * ``write_lock`` serializes sidecar writes (one writer at a time).
      * ``drain_event`` is set by ``drain_and_stop`` once writes have flushed.
    """

    def __init__(self, target_file: str):
        self.target_file = os.path.abspath(target_file)
        self.sidecar_path = self.target_file + ".comments.json"
        self.state = ServerState.INITIALIZING
        self.loaded_mtime: float = 0.0
        self.pending_writes: int = 0
        self.write_lock = threading.Lock()
        self.state_lock = threading.Lock()
        self.drain_event = threading.Event()
        self.sidecar_warnings: list[str] = []
        self.markdown_source: str = ""
        self.blocks: list = []
        self.sidecar: Sidecar = Sidecar(
            version=SIDECAR_VERSION, source_file=self.target_file, comments=[]
        )
        self.port: int = 0
        self.httpd: Optional[ThreadingHTTPServer] = None
        # Set once drain has begun so SIGINT/POST /done are idempotent.
        self._drain_started = False

    def reload_source(self) -> None:
        with open(self.target_file, "r", encoding="utf-8") as f:
            self.markdown_source = f.read()
        self.blocks = parse_blocks(self.markdown_source)
        self.loaded_mtime = os.path.getmtime(self.target_file)

    def reload_sidecar(self) -> None:
        sc, warnings = read_sidecar(self.sidecar_path)
        self.sidecar = sc
        self.sidecar_warnings = warnings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _block_to_dict(b: Any) -> dict:
    return {
        "kind": b.kind,
        "anchor": anchor_dict(b.anchor),
        "html": b.html,
        "plain_text": b.plain_text,
        "heading_level": b.heading_level,
    }


def _anchor_key(a: Any) -> str:
    """Match the frontend's anchorKey() in server/static/app.js:71."""
    return f"{a.heading_path}::{a.block_index_in_section}::{a.text_hash}"


def _changed_block_keys(blocks: list, snapshot_text: Optional[str]) -> list[str]:
    """Set-difference current blocks against snapshot blocks by text_hash.

    A block is "changed" if its content hash isn't present in the snapshot
    (covers modified, added, and (within their new home) re-split blocks).
    Reordering alone — same content moved to a new heading — does not count.
    Returns [] when no snapshot exists.
    """
    if snapshot_text is None:
        return []
    snapshot_blocks = parse_blocks(snapshot_text)
    snapshot_hashes = {b.anchor.text_hash for b in snapshot_blocks}
    return [
        _anchor_key(b.anchor)
        for b in blocks
        if b.anchor.text_hash not in snapshot_hashes
    ]


def find_free_port(start: int, count: int) -> int:
    """Find a free port in ``[start, start+count)`` on 127.0.0.1."""
    for p in range(start, start + count):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", p))
            except OSError:
                continue
        return p
    raise OSError(f"No free port in range {start}..{start + count - 1}")


def drain_and_stop(ctx: AppContext) -> None:
    """Flip state to DRAINING, wait for in-flight writes, then schedule shutdown.

    Idempotent: safe to call multiple times (e.g. POST /done + SIGINT).
    """
    with ctx.state_lock:
        if ctx.state == ServerState.STOPPED:
            ctx.drain_event.set()
            return
        if ctx._drain_started:
            return  # another drainer is already in flight; let it complete
        ctx._drain_started = True
        ctx.state = ServerState.DRAINING

    # Wait for pending writes to drain (bounded).
    deadline = time.monotonic() + DRAIN_TIMEOUT_SECONDS
    while True:
        with ctx.state_lock:
            if ctx.pending_writes == 0:
                break
        if time.monotonic() > deadline:
            # Surface the issue but proceed to shutdown anyway.
            print(
                f"warning: drain timeout after {DRAIN_TIMEOUT_SECONDS}s; "
                f"pending_writes={ctx.pending_writes}",
                file=sys.stderr,
            )
            break
        time.sleep(0.01)

    # Signal Done waiters NOW (writes are flushed).
    ctx.drain_event.set()

    # Defer the actual shutdown so the response can flush first.
    def _stop() -> None:
        try:
            if ctx.httpd is not None:
                ctx.httpd.shutdown()
        finally:
            with ctx.state_lock:
                ctx.state = ServerState.STOPPED
            try:
                release_lock()
            except Exception:
                pass

    timer = threading.Timer(0.1, _stop)
    timer.daemon = True
    timer.start()


# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------

def make_handler(ctx: AppContext):
    class Handler(BaseHTTPRequestHandler):
        # Silence default access logging (keeps test output clean).
        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

        # ----------------------- response helpers -------------------------
        def _send_json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def _send_bytes(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def _read_json_body(self) -> Optional[dict]:
            try:
                length = int(self.headers.get("Content-Length", "0") or "0")
            except ValueError:
                return None
            raw = self.rfile.read(length) if length > 0 else b""
            if not raw:
                return {}
            try:
                return json.loads(raw.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                return None

        # -------------------- pending_writes accounting --------------------
        def _begin_write(self) -> None:
            with ctx.state_lock:
                ctx.pending_writes += 1

        def _end_write(self) -> int:
            with ctx.state_lock:
                ctx.pending_writes -= 1
                if ctx.pending_writes < 0:
                    ctx.pending_writes = 0
                return ctx.pending_writes

        def _persist(self, new_comments: list) -> Optional[dict]:
            """Build a Sidecar with ``new_comments`` and write it atomically.

            Returns ``None`` on success (caller proceeds to send the success
            response) or a dict to send as a 500 response on write failure.
            Caller must hold ``ctx.write_lock`` and be inside the
            ``_begin_write`` / ``_end_write`` accounting.
            """
            new_sidecar = Sidecar(
                version=SIDECAR_VERSION,
                source_file=ctx.sidecar.source_file or ctx.target_file,
                comments=new_comments,
            )
            try:
                write_sidecar_atomic(ctx.sidecar_path, new_sidecar)
            except SidecarWriteError as exc:
                return {"error": "sidecar-write-failed", "message": str(exc)}
            ctx.sidecar = new_sidecar
            return None

        def _refuse_if_draining(self) -> bool:
            with ctx.state_lock:
                if ctx.state in {ServerState.DRAINING, ServerState.STOPPED}:
                    self._send_json(503, {"error": "draining"})
                    return True
            return False

        # -------------------------- dispatch ------------------------------
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            if path == "/" or path == "/index.html":
                return self._serve_index()
            if path.startswith("/static/"):
                return self._serve_static(path[len("/static/"):])
            if path == "/api/document":
                return self._handle_get_document()
            if path == "/api/document/changed":
                return self._handle_get_document_changed()
            if path == "/api/health":
                return self._handle_get_health()
            self._send_json(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            if path == "/api/comments":
                return self._handle_post_comments()
            if path == "/api/done":
                return self._handle_post_done()
            self._send_json(404, {"error": "not found"})

        def do_PUT(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            if path.startswith("/api/comments/"):
                cid = unquote(path[len("/api/comments/"):])
                return self._handle_put_comment(cid)
            self._send_json(404, {"error": "not found"})

        def do_DELETE(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            if path.startswith("/api/comments/"):
                cid = unquote(path[len("/api/comments/"):])
                return self._handle_delete_comment(cid)
            self._send_json(404, {"error": "not found"})

        # ---------------------- static + index ---------------------------
        def _serve_index(self) -> None:
            index_path = os.path.join(STATIC_DIR, "index.html")
            try:
                with open(index_path, "rb") as f:
                    body = f.read()
            except OSError:
                body = PLACEHOLDER_INDEX_HTML.encode("utf-8")
            self._send_bytes(200, "text/html; charset=utf-8", body)

        def _serve_static(self, name: str) -> None:
            # Reject path traversal attempts.
            name = unquote(name)
            base_real = os.path.realpath(STATIC_DIR)
            full = os.path.realpath(os.path.join(STATIC_DIR, name))
            if not full.startswith(base_real + os.sep) and full != base_real:
                self._send_json(404, {"error": "not found"})
                return
            if not os.path.isfile(full):
                self._send_json(404, {"error": "not found"})
                return
            ctype, _ = mimetypes.guess_type(full)
            if ctype is None:
                ctype = "application/octet-stream"
            try:
                with open(full, "rb") as f:
                    body = f.read()
            except OSError:
                self._send_json(404, {"error": "not found"})
                return
            self._send_bytes(200, ctype, body)

        # ----------------------- /api/document ---------------------------
        def _handle_get_document(self) -> None:
            try:
                source_mtime = os.path.getmtime(ctx.target_file)
            except OSError:
                source_mtime = ctx.loaded_mtime
            # Read snapshot fresh on each request so apply-step writes are
            # picked up without a server restart.
            snapshot_text = read_snapshot(ctx.target_file)
            payload = {
                "blocks": [_block_to_dict(b) for b in ctx.blocks],
                "comments": [asdict(c) for c in ctx.sidecar.comments],
                "sidecar_warnings": list(ctx.sidecar_warnings),
                "source_mtime": source_mtime,
                "changed_block_ids": _changed_block_keys(ctx.blocks, snapshot_text),
            }
            self._send_json(200, payload)

        def _handle_get_document_changed(self) -> None:
            try:
                current = os.path.getmtime(ctx.target_file)
            except OSError:
                current = ctx.loaded_mtime
            self._send_json(200, {
                "changed": current > ctx.loaded_mtime,
                "current_mtime": current,
                "loaded_mtime": ctx.loaded_mtime,
            })

        def _handle_get_health(self) -> None:
            with ctx.state_lock:
                state = ctx.state
            self._send_json(200, {
                "state": state,
                "port": ctx.port,
                "target_file": ctx.target_file,
            })

        # ----------------------- /api/comments ---------------------------
        def _handle_post_comments(self) -> None:
            if self._refuse_if_draining():
                return
            req = self._read_json_body()
            if req is None or not isinstance(req, dict):
                self._send_json(400, {"error": "invalid json"})
                return
            anchor_raw = req.get("anchor")
            body = req.get("body", "")
            if not isinstance(body, str) or body.strip() == "":
                self._send_json(422, {"error": "blank"})
                return
            if len(body) > COMMENT_BODY_MAX_CHARS:
                self._send_json(422, {"error": "oversize"})
                return
            if not isinstance(anchor_raw, dict):
                self._send_json(422, {"error": "unknown anchor"})
                return
            try:
                anchor = Anchor(**anchor_raw)
            except TypeError:
                self._send_json(422, {"error": "unknown anchor"})
                return
            result = resolve_anchor(anchor, ctx.blocks)
            if result.outcome == ResolveOutcome.ORPHAN:
                self._send_json(422, {"error": "unknown anchor"})
                return

            self._begin_write()
            try:
                with ctx.write_lock:
                    now = _now_iso()
                    comment = Comment(
                        id=uuid.uuid4().hex,
                        anchor=anchor_dict(anchor),
                        body=body,
                        created_at=now,
                        updated_at=now,
                        applied=False,
                        applied_at=None,
                    )
                    new_comments = list(ctx.sidecar.comments) + [comment]
                    write_error = self._persist(new_comments)
                    if write_error is not None:
                        self._send_json(500, write_error)
                        return
            finally:
                pending_after = self._end_write()

            self._send_json(201, {
                "comment": asdict(comment),
                "pending_writes": pending_after,
            })

        def _handle_put_comment(self, cid: str) -> None:
            if self._refuse_if_draining():
                return
            req = self._read_json_body()
            if req is None or not isinstance(req, dict):
                self._send_json(400, {"error": "invalid json"})
                return
            new_body = req.get("body", "")
            if not isinstance(new_body, str) or new_body.strip() == "":
                self._send_json(422, {"error": "blank"})
                return
            if len(new_body) > COMMENT_BODY_MAX_CHARS:
                self._send_json(422, {"error": "oversize"})
                return

            self._begin_write()
            try:
                with ctx.write_lock:
                    idx = next(
                        (i for i, c in enumerate(ctx.sidecar.comments) if c.id == cid),
                        -1,
                    )
                    if idx < 0:
                        self._send_json(409, {"error": "unknown comment"})
                        return
                    existing = ctx.sidecar.comments[idx]
                    updated = Comment(
                        id=existing.id,
                        anchor=existing.anchor,
                        body=new_body,
                        created_at=existing.created_at,
                        updated_at=_now_iso(),
                        applied=existing.applied,
                        applied_at=existing.applied_at,
                    )
                    new_comments = list(ctx.sidecar.comments)
                    new_comments[idx] = updated
                    write_error = self._persist(new_comments)
                    if write_error is not None:
                        self._send_json(500, write_error)
                        return
            finally:
                pending_after = self._end_write()

            self._send_json(200, {
                "comment": asdict(updated),
                "pending_writes": pending_after,
            })

        def _handle_delete_comment(self, cid: str) -> None:
            if self._refuse_if_draining():
                return
            self._begin_write()
            try:
                with ctx.write_lock:
                    idx = next(
                        (i for i, c in enumerate(ctx.sidecar.comments) if c.id == cid),
                        -1,
                    )
                    if idx < 0:
                        self._send_json(409, {"error": "unknown comment"})
                        return
                    new_comments = list(ctx.sidecar.comments)
                    del new_comments[idx]
                    write_error = self._persist(new_comments)
                    if write_error is not None:
                        self._send_json(500, write_error)
                        return
            finally:
                pending_after = self._end_write()

            self._send_json(200, {"ok": True, "pending_writes": pending_after})

        # ------------------------- /api/done ------------------------------
        def _handle_post_done(self) -> None:
            # Always allowed; this is the path that triggers drain.
            # Parse the optional `auto_apply` flag from the request body. A
            # missing body / missing field defaults to False and matches the
            # pre-feature behavior (no auto-apply).
            req = self._read_json_body()
            if req is None:
                self._send_json(400, {"error": "invalid json"})
                return
            auto_apply_raw = req.get("auto_apply", False) if isinstance(req, dict) else False
            if not isinstance(auto_apply_raw, bool):
                self._send_json(400, {"error": "auto_apply must be boolean"})
                return
            auto_apply = bool(auto_apply_raw)

            # Re-parse the source from disk in case mtime has advanced —
            # then compute orphans against that fresh tree.
            try:
                with open(ctx.target_file, "r", encoding="utf-8") as f:
                    fresh_source = f.read()
                fresh_blocks = parse_blocks(fresh_source)
            except OSError:
                fresh_blocks = ctx.blocks

            orphans: list[dict] = []
            for c in ctx.sidecar.comments:
                try:
                    a = Anchor(**c.anchor)
                except TypeError:
                    a = None
                if a is None:
                    continue
                result = resolve_anchor(a, fresh_blocks)
                if result.outcome == ResolveOutcome.ORPHAN:
                    orphans.append({
                        "id": c.id,
                        "anchor": c.anchor,
                        "body": c.body,
                        "preview": c.anchor.get("preview", ""),
                    })

            # Single-line marker for the launching skill to grep — printed
            # *before* drain so it lands in $LOG even if shutdown is racing.
            print(f"AUTO_APPLY: {1 if auto_apply else 0}", flush=True)

            # Kick off drain in a background thread so we can wait for it
            # via drain_event without blocking the response.
            t = threading.Thread(target=drain_and_stop, args=(ctx,), daemon=True)
            t.start()

            ok = ctx.drain_event.wait(timeout=DRAIN_TIMEOUT_SECONDS)
            self._send_json(200, {
                "ok": bool(ok),
                "orphans": orphans,
                "auto_apply": auto_apply,
            })

    return Handler


# ---------------------------------------------------------------------------
# Signal handling + main()
# ---------------------------------------------------------------------------

def install_signal_handlers(ctx: AppContext) -> None:
    def handler(signum, frame):  # noqa: ARG001
        # Drain in a background thread so the signal handler returns quickly.
        threading.Thread(
            target=lambda: drain_and_stop(ctx), daemon=True
        ).start()

    try:
        signal.signal(signal.SIGINT, handler)
    except (ValueError, OSError):
        # Not main thread / not supported on this platform.
        pass
    try:
        signal.signal(signal.SIGTERM, handler)
    except (ValueError, OSError):
        pass


def _print_running_instance(info: LockInfo) -> None:
    url = f"http://127.0.0.1:{info.port}"
    print("error: another markdown-review instance is running.", file=sys.stderr)
    print(f"  url: {url}", file=sys.stderr)
    print(f"  target_file: {info.target_file}", file=sys.stderr)


def _print_stale_lock(info: Optional[LockInfo]) -> None:
    lock_path = _resolve_lock_path()
    port_str = str(info.port) if info is not None else "?"
    print(
        f"error: stale lock file detected (port {port_str} not responding).",
        file=sys.stderr,
    )
    print(f"  to clear: rm {lock_path}", file=sys.stderr)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="markdown-review",
        description="Run a local HTTP server for inline markdown comment review.",
    )
    parser.add_argument("markdown_path", help="Path to the markdown file to review.")
    args = parser.parse_args(argv)

    target = args.markdown_path
    if not os.path.isfile(target):
        print(f"error: markdown file not found: {target}", file=sys.stderr)
        return 2

    # Cross-process duplicate detection (FR-07).
    probe = probe_lock()
    if probe.state == LockState.RUNNING and probe.info is not None:
        _print_running_instance(probe.info)
        return 3
    if probe.state == LockState.STALE:
        _print_stale_lock(probe.info)
        return 4

    # Pick a free port (FR-02, FR-06).
    try:
        port = find_free_port(DEFAULT_PORT, PORT_FALLBACK_RANGE)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 5

    ctx = AppContext(target)
    ctx.port = port
    try:
        ctx.reload_source()
    except OSError as exc:
        print(f"error: failed to read markdown file: {exc}", file=sys.stderr)
        return 2
    ctx.reload_sidecar()

    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(ctx))
    ctx.httpd = httpd

    try:
        acquire_lock(LockInfo(
            pid=os.getpid(),
            port=port,
            target_file=ctx.target_file,
            started_at=_now_iso(),
        ))
    except OSError as exc:
        print(f"warning: failed to write lock file: {exc}", file=sys.stderr)

    with ctx.state_lock:
        ctx.state = ServerState.READY

    install_signal_handlers(ctx)

    print(f"http://127.0.0.1:{port}", flush=True)
    print(f"target_file: {ctx.target_file}", flush=True)
    print(
        "Open the URL in a browser. Click Done in the UI or Ctrl-C here when finished.",
        flush=True,
    )

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        # Defensive: SIGINT handler should have already fired.
        drain_and_stop(ctx)
    finally:
        with ctx.state_lock:
            ctx.state = ServerState.STOPPED
        try:
            httpd.server_close()
        except Exception:
            pass
        try:
            release_lock()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
