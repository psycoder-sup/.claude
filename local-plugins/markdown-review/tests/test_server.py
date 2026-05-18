"""
Tests for server.annotate_server — HTTP server + lifecycle.

Covers:
- FR-02: server binds 127.0.0.1, free port, prints URL
- FR-04: drain on Done — POST /api/done waits for pending writes; SIGINT same drain
- FR-05: missing markdown → exit non-zero before binding
- FR-06: port-in-use → next free port
- FR-07: second instance refuses (RUNNING); stale lock manual-clear instructions
- FR-08: mtime-change detection via /api/document/changed
- FR-12, FR-14, FR-15: POST /api/comments — accept normal body, reject blank/oversize/unknown anchor
- FR-19: DELETE /api/comments/<id> removes from sidecar
- FR-20: multiple comments on same anchor preserved in creation order
- FR-28: Done returns orphan list when source has changed mid-session
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from server.annotate_server import (
    AppContext,
    DEFAULT_PORT,
    PORT_FALLBACK_RANGE,
    ServerState,
    drain_and_stop,
    find_free_port,
    main,
    make_handler,
)
from server.lockfile import LockInfo, LockProbeResult, LockState
from server.markdown_blocks import parse_blocks
from server.sidecar import read_sidecar


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@contextlib.contextmanager
def running_inprocess_server(target_md_path: str):
    """Spin up an AppContext-driven ThreadingHTTPServer in a thread."""
    ctx = AppContext(target_md_path)
    ctx.reload_source()
    ctx.reload_sidecar()
    ctx.port = find_free_port(40000, 200)  # avoid 8765
    httpd = ThreadingHTTPServer(("127.0.0.1", ctx.port), make_handler(ctx))
    ctx.httpd = httpd
    ctx.state = ServerState.READY
    th = threading.Thread(target=httpd.serve_forever, daemon=True)
    th.start()
    try:
        yield ctx
    finally:
        try:
            httpd.shutdown()
        except Exception:
            pass
        httpd.server_close()
        th.join(timeout=5)


def _url(ctx: AppContext, path: str) -> str:
    return f"http://127.0.0.1:{ctx.port}{path}"


def _request(method: str, full_url: str, body=None, headers=None, timeout: float = 5.0):
    data = None
    h = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(full_url, data=data, headers=h, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        raw = resp.read()
        ctype = resp.headers.get("Content-Type", "")
        if ctype.startswith("application/json"):
            return resp.status, json.loads(raw.decode("utf-8"))
        return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw.decode("utf-8"))
        except Exception:
            return e.code, raw


def _make_md_file(tmpdir: str, contents: str = None) -> str:
    if contents is None:
        contents = (
            "# Title\n"
            "\n"
            "First paragraph here.\n"
            "\n"
            "## Section A\n"
            "\n"
            "Para A1.\n"
            "\n"
            "Para A2.\n"
        )
    p = os.path.join(tmpdir, "doc.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write(contents)
    return p


def _first_paragraph_anchor(md_path: str) -> dict:
    with open(md_path, "r", encoding="utf-8") as f:
        src = f.read()
    blocks = parse_blocks(src)
    for b in blocks:
        if b.kind == "paragraph":
            from dataclasses import asdict
            return asdict(b.anchor)
    raise RuntimeError("no paragraph in fixture")


# ---------------------------------------------------------------------------
# Document + comments
# ---------------------------------------------------------------------------

class TestDocumentEndpoint(unittest.TestCase):
    def test_server_returns_document_blocks_and_comments(self):
        with tempfile.TemporaryDirectory() as d:
            md = _make_md_file(d)
            with running_inprocess_server(md) as ctx:
                status, body = _request("GET", _url(ctx, "/api/document"))
        self.assertEqual(status, 200)
        self.assertIn("blocks", body)
        self.assertIn("comments", body)
        self.assertIn("sidecar_warnings", body)
        self.assertIn("source_mtime", body)
        self.assertIn("changed_block_ids", body)
        self.assertGreater(len(body["blocks"]), 0)
        self.assertEqual(body["comments"], [])
        # No snapshot file → no diff info.
        self.assertEqual(body["changed_block_ids"], [])

    def test_changed_block_ids_empty_when_snapshot_identical(self):
        with tempfile.TemporaryDirectory() as d:
            md = _make_md_file(d)
            # Snapshot = byte-identical copy of source.
            with open(md, "r", encoding="utf-8") as f:
                current = f.read()
            with open(md + ".review-snapshot.md", "w", encoding="utf-8") as f:
                f.write(current)
            with running_inprocess_server(md) as ctx:
                status, body = _request("GET", _url(ctx, "/api/document"))
        self.assertEqual(status, 200)
        self.assertEqual(body["changed_block_ids"], [])

    def test_changed_block_ids_includes_modified_paragraph(self):
        # Snapshot has "First paragraph here." but the current source has been
        # rewritten with "Rewritten first paragraph." for that one block — and
        # nothing else changed.
        with tempfile.TemporaryDirectory() as d:
            md = _make_md_file(d)  # has "First paragraph here."
            # Snapshot retains the original.
            with open(md, "r", encoding="utf-8") as f:
                original = f.read()
            with open(md + ".review-snapshot.md", "w", encoding="utf-8") as f:
                f.write(original)
            # Rewrite just the first paragraph.
            rewritten = original.replace(
                "First paragraph here.", "Rewritten first paragraph."
            )
            self.assertNotEqual(original, rewritten)
            with open(md, "w", encoding="utf-8") as f:
                f.write(rewritten)

            with running_inprocess_server(md) as ctx:
                status, body = _request("GET", _url(ctx, "/api/document"))
        self.assertEqual(status, 200)
        ids = body["changed_block_ids"]
        self.assertEqual(len(ids), 1, f"expected 1 changed block, got {ids}")
        # The lone changed block must be the rewritten paragraph.
        para = next(
            b for b in body["blocks"]
            if b["plain_text"].strip() == "Rewritten first paragraph."
        )
        a = para["anchor"]
        expected = f"{a['heading_path']}::{a['block_index_in_section']}::{a['text_hash']}"
        self.assertEqual(ids, [expected])

    def test_health_returns_state_and_port(self):
        with tempfile.TemporaryDirectory() as d:
            md = _make_md_file(d)
            with running_inprocess_server(md) as ctx:
                status, body = _request("GET", _url(ctx, "/api/health"))
                self.assertEqual(status, 200)
                self.assertEqual(body["state"], ServerState.READY)
                self.assertEqual(body["port"], ctx.port)
                self.assertEqual(body["target_file"], ctx.target_file)

    def test_static_index_html_served_or_placeholder(self):
        with tempfile.TemporaryDirectory() as d:
            md = _make_md_file(d)
            with running_inprocess_server(md) as ctx:
                status, body = _request("GET", _url(ctx, "/"))
        self.assertEqual(status, 200)
        # body could be bytes; ensure html
        text = body.decode("utf-8") if isinstance(body, (bytes, bytearray)) else body
        self.assertIn("<", text)


class TestPostComment(unittest.TestCase):
    def test_post_comment_persists_to_sidecar_and_returns_201(self):
        with tempfile.TemporaryDirectory() as d:
            md = _make_md_file(d)
            anchor = _first_paragraph_anchor(md)
            with running_inprocess_server(md) as ctx:
                status, body = _request(
                    "POST",
                    _url(ctx, "/api/comments"),
                    body={"anchor": anchor, "body": "Looks good!"},
                )
            self.assertEqual(status, 201)
            self.assertIn("comment", body)
            self.assertIn("pending_writes", body)
            self.assertEqual(body["comment"]["body"], "Looks good!")
            # Sidecar persisted
            sc, _ = read_sidecar(md + ".comments.json")
            self.assertEqual(len(sc.comments), 1)
            self.assertEqual(sc.comments[0].body, "Looks good!")

    def test_post_blank_body_rejected_with_422(self):
        with tempfile.TemporaryDirectory() as d:
            md = _make_md_file(d)
            anchor = _first_paragraph_anchor(md)
            with running_inprocess_server(md) as ctx:
                status, body = _request(
                    "POST",
                    _url(ctx, "/api/comments"),
                    body={"anchor": anchor, "body": "   "},
                )
        self.assertEqual(status, 422)
        self.assertIn("error", body)

    def test_post_oversize_body_rejected_with_422(self):
        with tempfile.TemporaryDirectory() as d:
            md = _make_md_file(d)
            anchor = _first_paragraph_anchor(md)
            with running_inprocess_server(md) as ctx:
                status, body = _request(
                    "POST",
                    _url(ctx, "/api/comments"),
                    body={"anchor": anchor, "body": "x" * 2001},
                )
        self.assertEqual(status, 422)

    def test_post_unknown_anchor_rejected_with_422(self):
        with tempfile.TemporaryDirectory() as d:
            md = _make_md_file(d)
            bad_anchor = {
                "heading_path": "## Nonexistent",
                "block_index_in_section": 99,
                "text_hash": "deadbeef0000",
                "preview": "ghost",
            }
            with running_inprocess_server(md) as ctx:
                status, body = _request(
                    "POST",
                    _url(ctx, "/api/comments"),
                    body={"anchor": bad_anchor, "body": "hi"},
                )
        self.assertEqual(status, 422)


class TestPutComment(unittest.TestCase):
    def test_put_edit_existing_comment(self):
        with tempfile.TemporaryDirectory() as d:
            md = _make_md_file(d)
            anchor = _first_paragraph_anchor(md)
            with running_inprocess_server(md) as ctx:
                _, post_body = _request(
                    "POST",
                    _url(ctx, "/api/comments"),
                    body={"anchor": anchor, "body": "first"},
                )
                cid = post_body["comment"]["id"]
                # Sleep to ensure updated_at changes
                time.sleep(0.01)
                status, body = _request(
                    "PUT",
                    _url(ctx, f"/api/comments/{cid}"),
                    body={"body": "edited"},
                )
        self.assertEqual(status, 200)
        self.assertEqual(body["comment"]["body"], "edited")
        self.assertEqual(body["comment"]["id"], cid)

    def test_put_unknown_id_returns_409(self):
        with tempfile.TemporaryDirectory() as d:
            md = _make_md_file(d)
            with running_inprocess_server(md) as ctx:
                status, _ = _request(
                    "PUT",
                    _url(ctx, "/api/comments/doesnotexist"),
                    body={"body": "x"},
                )
        self.assertEqual(status, 409)

    def test_put_blank_body_rejected_422(self):
        with tempfile.TemporaryDirectory() as d:
            md = _make_md_file(d)
            anchor = _first_paragraph_anchor(md)
            with running_inprocess_server(md) as ctx:
                _, post_body = _request(
                    "POST",
                    _url(ctx, "/api/comments"),
                    body={"anchor": anchor, "body": "first"},
                )
                cid = post_body["comment"]["id"]
                status, _ = _request(
                    "PUT",
                    _url(ctx, f"/api/comments/{cid}"),
                    body={"body": "   "},
                )
        self.assertEqual(status, 422)


class TestDeleteComment(unittest.TestCase):
    def test_delete_existing_comment_removes_from_sidecar(self):
        with tempfile.TemporaryDirectory() as d:
            md = _make_md_file(d)
            anchor = _first_paragraph_anchor(md)
            with running_inprocess_server(md) as ctx:
                _, post_body = _request(
                    "POST",
                    _url(ctx, "/api/comments"),
                    body={"anchor": anchor, "body": "to-delete"},
                )
                cid = post_body["comment"]["id"]
                status, body = _request(
                    "DELETE",
                    _url(ctx, f"/api/comments/{cid}"),
                )
            self.assertEqual(status, 200)
            self.assertTrue(body["ok"])
            sc, _ = read_sidecar(md + ".comments.json")
            self.assertEqual(sc.comments, [])

    def test_delete_unknown_id_returns_409(self):
        with tempfile.TemporaryDirectory() as d:
            md = _make_md_file(d)
            with running_inprocess_server(md) as ctx:
                status, _ = _request(
                    "DELETE",
                    _url(ctx, "/api/comments/nope"),
                )
        self.assertEqual(status, 409)


class TestCreationOrder(unittest.TestCase):
    """FR-20: multiple comments on the same anchor are preserved in creation order."""

    def test_multiple_comments_on_same_anchor_preserved_in_creation_order(self):
        with tempfile.TemporaryDirectory() as d:
            md = _make_md_file(d)
            anchor = _first_paragraph_anchor(md)
            with running_inprocess_server(md) as ctx:
                bodies = ["one", "two", "three", "four"]
                ids = []
                for b in bodies:
                    _, resp = _request(
                        "POST",
                        _url(ctx, "/api/comments"),
                        body={"anchor": anchor, "body": b},
                    )
                    ids.append(resp["comment"]["id"])
            sc, _ = read_sidecar(md + ".comments.json")
            self.assertEqual([c.body for c in sc.comments], bodies)
            self.assertEqual([c.id for c in sc.comments], ids)


# ---------------------------------------------------------------------------
# mtime-change endpoint (FR-08)
# ---------------------------------------------------------------------------

class TestDocumentChanged(unittest.TestCase):
    def test_get_document_changed_returns_changed_true_after_mtime_advances(self):
        # macOS HFS/APFS may have ~1s mtime granularity. Sleep 1.1s
        # between the snapshot and the rewrite to ensure mtime advances reliably.
        with tempfile.TemporaryDirectory() as d:
            md = _make_md_file(d)
            with running_inprocess_server(md) as ctx:
                status, body = _request("GET", _url(ctx, "/api/document/changed"))
                self.assertEqual(status, 200)
                self.assertFalse(body["changed"])
                time.sleep(1.1)
                with open(md, "w", encoding="utf-8") as f:
                    f.write("# completely different\n\nnew para\n")
                status, body = _request("GET", _url(ctx, "/api/document/changed"))
        self.assertEqual(status, 200)
        self.assertTrue(body["changed"])
        self.assertGreater(body["current_mtime"], body["loaded_mtime"])


# ---------------------------------------------------------------------------
# Done / drain (FR-04, FR-28)
# ---------------------------------------------------------------------------

class TestDoneDrains(unittest.TestCase):
    def test_done_drains_writes_and_returns_orphans_when_source_changed(self):
        # Fast path: with no in-flight writes and no source change, Done returns
        # ok=True, orphans=[] and shuts the server down.
        with tempfile.TemporaryDirectory() as d:
            md = _make_md_file(d)
            anchor = _first_paragraph_anchor(md)
            ctx = AppContext(md)
            ctx.reload_source()
            ctx.reload_sidecar()
            ctx.port = find_free_port(40000, 200)
            httpd = ThreadingHTTPServer(("127.0.0.1", ctx.port), make_handler(ctx))
            ctx.httpd = httpd
            ctx.state = ServerState.READY
            th = threading.Thread(target=httpd.serve_forever, daemon=True)
            th.start()
            try:
                # Post a comment first
                _, post_body = _request(
                    "POST",
                    _url(ctx, "/api/comments"),
                    body={"anchor": anchor, "body": "keep me"},
                )
                # Mutate source so the existing comment becomes an orphan.
                time.sleep(1.1)
                with open(md, "w", encoding="utf-8") as f:
                    f.write("# unrelated\n\nfresh content has nothing in common.\n")
                status, body = _request("POST", _url(ctx, "/api/done"), body={})
            finally:
                # Server should self-shutdown via the drain timer; just join.
                th.join(timeout=10)
                try:
                    httpd.server_close()
                except Exception:
                    pass
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertGreater(len(body["orphans"]), 0)

    def test_done_waits_for_pending_writes_to_drain_before_shutdown(self):
        """Force pending_writes > 0 by patching write_sidecar_atomic to sleep."""
        from server import annotate_server as srv

        with tempfile.TemporaryDirectory() as d:
            md = _make_md_file(d)
            anchor = _first_paragraph_anchor(md)
            ctx = AppContext(md)
            ctx.reload_source()
            ctx.reload_sidecar()
            ctx.port = find_free_port(40000, 200)
            httpd = ThreadingHTTPServer(("127.0.0.1", ctx.port), make_handler(ctx))
            ctx.httpd = httpd
            ctx.state = ServerState.READY
            th = threading.Thread(target=httpd.serve_forever, daemon=True)
            th.start()

            real_write = srv.write_sidecar_atomic
            slow_started = threading.Event()

            def slow_write(path, sidecar):
                slow_started.set()
                time.sleep(0.5)
                return real_write(path, sidecar)

            try:
                # Patch the symbol used inside annotate_server
                with patch("server.annotate_server.write_sidecar_atomic", side_effect=slow_write):
                    # Kick off a slow POST in a thread so it occupies pending_writes
                    post_done = threading.Event()
                    post_status_holder = {}

                    def slow_post():
                        s, b = _request(
                            "POST",
                            _url(ctx, "/api/comments"),
                            body={"anchor": anchor, "body": "slow"},
                            timeout=10,
                        )
                        post_status_holder["status"] = s
                        post_status_holder["body"] = b
                        post_done.set()

                    poster = threading.Thread(target=slow_post, daemon=True)
                    poster.start()
                    # Wait until the slow write actually started
                    self.assertTrue(slow_started.wait(timeout=5))
                    # Issue Done while pending_writes > 0
                    s2, b2 = _request("POST", _url(ctx, "/api/done"), body={}, timeout=15)
                    # Done must wait for pending writes to flush
                    self.assertEqual(s2, 200)
                    self.assertTrue(b2["ok"])
                    # And the post must have completed by the time Done returned
                    self.assertTrue(post_done.wait(timeout=5))
                    self.assertEqual(post_status_holder["status"], 201)
                    sc, _ = read_sidecar(md + ".comments.json")
                    self.assertEqual(len(sc.comments), 1)
            finally:
                th.join(timeout=10)
                try:
                    httpd.server_close()
                except Exception:
                    pass

    def test_done_defaults_auto_apply_to_false(self):
        """No body / no auto_apply field → response echoes auto_apply: False
        and AUTO_APPLY: 0 is printed to stdout."""
        buf = io.StringIO()
        with tempfile.TemporaryDirectory() as d:
            md = _make_md_file(d)
            with running_inprocess_server(md) as ctx:
                with contextlib.redirect_stdout(buf):
                    status, body = _request("POST", _url(ctx, "/api/done"), body={})
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(body["auto_apply"], False)
        self.assertIn("AUTO_APPLY: 0", buf.getvalue())

    def test_done_with_auto_apply_true(self):
        """Body {auto_apply: true} → response echoes True, AUTO_APPLY: 1
        printed, and the .auto_apply_pending marker file appears next to the
        sidecar for the next-turn apply step to detect."""
        buf = io.StringIO()
        with tempfile.TemporaryDirectory() as d:
            md = _make_md_file(d)
            marker = md + ".comments.json.auto_apply_pending"
            with running_inprocess_server(md) as ctx:
                with contextlib.redirect_stdout(buf):
                    status, body = _request(
                        "POST", _url(ctx, "/api/done"), body={"auto_apply": True}
                    )
            self.assertTrue(os.path.exists(marker), f"marker missing: {marker}")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(body["auto_apply"], True)
        self.assertIn("AUTO_APPLY: 1", buf.getvalue())

    def test_done_auto_apply_false_clears_stale_marker(self):
        """A leftover .auto_apply_pending from a previous Done click must be
        cleared when Done is now clicked without auto_apply."""
        with tempfile.TemporaryDirectory() as d:
            md = _make_md_file(d)
            marker = md + ".comments.json.auto_apply_pending"
            # Plant a stale marker.
            with open(marker, "w", encoding="utf-8") as f:
                f.write("")
            self.assertTrue(os.path.exists(marker))
            with running_inprocess_server(md) as ctx:
                status, body = _request(
                    "POST", _url(ctx, "/api/done"), body={"auto_apply": False}
                )
            self.assertFalse(os.path.exists(marker), "stale marker not cleared")
        self.assertEqual(status, 200)
        self.assertEqual(body["auto_apply"], False)

    def test_done_rejects_non_bool_auto_apply(self):
        """A string / number for auto_apply should 400, not crash."""
        with tempfile.TemporaryDirectory() as d:
            md = _make_md_file(d)
            with running_inprocess_server(md) as ctx:
                status, body = _request(
                    "POST", _url(ctx, "/api/done"), body={"auto_apply": "yes"}
                )
        self.assertEqual(status, 400)
        self.assertIn("auto_apply", body.get("error", ""))


# ---------------------------------------------------------------------------
# Drain refuses new writes (state == DRAINING -> 503)
# ---------------------------------------------------------------------------

class TestDrainRefuses(unittest.TestCase):
    def test_post_during_draining_returns_503(self):
        with tempfile.TemporaryDirectory() as d:
            md = _make_md_file(d)
            anchor = _first_paragraph_anchor(md)
            ctx = AppContext(md)
            ctx.reload_source()
            ctx.reload_sidecar()
            ctx.port = find_free_port(40000, 200)
            httpd = ThreadingHTTPServer(("127.0.0.1", ctx.port), make_handler(ctx))
            ctx.httpd = httpd
            ctx.state = ServerState.DRAINING  # force immediately
            th = threading.Thread(target=httpd.serve_forever, daemon=True)
            th.start()
            try:
                status, body = _request(
                    "POST",
                    _url(ctx, "/api/comments"),
                    body={"anchor": anchor, "body": "nope"},
                )
                self.assertEqual(status, 503)
            finally:
                httpd.shutdown()
                th.join(timeout=5)
                httpd.server_close()


# ---------------------------------------------------------------------------
# CLI / main()
# ---------------------------------------------------------------------------

class TestCli(unittest.TestCase):
    def test_main_exits_nonzero_if_markdown_file_missing(self):
        with tempfile.TemporaryDirectory() as d:
            target = os.path.join(d, "missing.md")
            with contextlib.redirect_stderr(io.StringIO()):
                rc = main([target])
        self.assertNotEqual(rc, 0)

    def test_main_refuses_when_another_instance_running(self):
        with tempfile.TemporaryDirectory() as d:
            target = _make_md_file(d)
            running = LockProbeResult(
                state=LockState.RUNNING,
                info=LockInfo(
                    pid=999,
                    port=12345,
                    target_file="/tmp/x.md",
                    started_at="2026-05-06T00:00:00Z",
                ),
            )
            with patch("server.annotate_server.probe_lock", return_value=running):
                with contextlib.redirect_stderr(io.StringIO()):
                    rc = main([target])
        self.assertNotEqual(rc, 0)

    def test_main_reports_stale_lock_with_manual_clear(self):
        with tempfile.TemporaryDirectory() as d:
            target = _make_md_file(d)
            stale = LockProbeResult(
                state=LockState.STALE,
                info=LockInfo(
                    pid=999,
                    port=12345,
                    target_file="/tmp/x.md",
                    started_at="2026-05-06T00:00:00Z",
                ),
            )
            with patch("server.annotate_server.probe_lock", return_value=stale):
                # Capture stderr to verify "manual clear" instructions
                buf = io.StringIO()
                with contextlib.redirect_stderr(buf):
                    rc = main([target])
        self.assertNotEqual(rc, 0)
        stderr = buf.getvalue()
        # Must mention how to manually clear (the lock path or "rm")
        self.assertTrue(
            "rm " in stderr or "lock" in stderr.lower(),
            f"expected manual-clear instructions in stderr, got: {stderr!r}",
        )


# ---------------------------------------------------------------------------
# Port handling
# ---------------------------------------------------------------------------

class TestPortFallback(unittest.TestCase):
    def test_find_free_port_skips_bound_port(self):
        # Bind a known port, then ensure find_free_port returns something else
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        bound = s.getsockname()[1]
        try:
            # Start the search at the bound port so the first try fails.
            found = find_free_port(bound, 50)
            self.assertNotEqual(found, bound)
        finally:
            s.close()

    def test_port_fallback_when_default_in_use(self):
        # Bind a port via the kernel's "free port 0" assignment, then ask
        # find_free_port to start from that bound port. It must skip past it.
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        bound = s.getsockname()[1]
        try:
            found = find_free_port(bound, 50)
            self.assertNotEqual(found, bound)
            self.assertGreaterEqual(found, bound)
        finally:
            s.close()


# ---------------------------------------------------------------------------
# Subprocess: SIGINT triggers drain + clean exit (FR-04)
# ---------------------------------------------------------------------------

class TestSigintSubprocess(unittest.TestCase):
    def test_sigint_triggers_drain_and_clean_exit(self):
        # macOS sometimes lags on SIGINT; allow a generous timeout.
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write("# hi\n\npara\n")
            target = f.name

        plugin_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Make sure no prior lock exists to confuse the subprocess.
        from server.lockfile import _resolve_lock_path
        lock_path = _resolve_lock_path()
        had_lock = os.path.exists(lock_path)
        if had_lock:
            backup = lock_path + ".test-backup"
            os.replace(lock_path, backup)
        else:
            backup = None

        try:
            proc = subprocess.Popen(
                [sys.executable, "-m", "server.annotate_server", target],
                cwd=plugin_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                # Wait for the URL line so we know the server bound
                url_line = proc.stdout.readline()
                self.assertIn("http://127.0.0.1:", url_line)
                proc.send_signal(signal.SIGINT)
                rc = proc.wait(timeout=15)
                self.assertEqual(rc, 0)
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=5)
                # Close pipes to avoid ResourceWarning in test output.
                for stream in (proc.stdout, proc.stderr, proc.stdin):
                    if stream is not None:
                        try:
                            stream.close()
                        except Exception:
                            pass
        finally:
            try:
                os.unlink(target)
            except OSError:
                pass
            sc = target + ".comments.json"
            if os.path.exists(sc):
                try:
                    os.unlink(sc)
                except OSError:
                    pass
            # Restore prior lock if any; else clear our subprocess's lock.
            if backup is not None:
                os.replace(backup, lock_path)
            else:
                try:
                    os.remove(lock_path)
                except FileNotFoundError:
                    pass


# ---------------------------------------------------------------------------
# drain_and_stop is re-entrant
# ---------------------------------------------------------------------------

class TestDrainReentrant(unittest.TestCase):
    def test_drain_and_stop_is_idempotent_when_already_stopped(self):
        with tempfile.TemporaryDirectory() as d:
            md = _make_md_file(d)
            ctx = AppContext(md)
            ctx.reload_source()
            ctx.reload_sidecar()
            ctx.port = find_free_port(40000, 200)
            httpd = ThreadingHTTPServer(("127.0.0.1", ctx.port), make_handler(ctx))
            ctx.httpd = httpd
            ctx.state = ServerState.STOPPED
            # Should not raise.
            drain_and_stop(ctx)
            httpd.server_close()


if __name__ == "__main__":
    unittest.main()
