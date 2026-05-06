"""
Tests for server.lockfile — probe_lock, acquire_lock, release_lock.

Covers:
- FR-07: cross-process duplicate detection via lock file + port probe
- FREE: no lock file present
- RUNNING: lock file + port responds
- STALE: lock file + port does not respond
- acquire/release round-trip
- No auto-clear of stale locks (PRD §8)
"""

import json
import os
import socket
import tempfile
import unittest
from unittest.mock import patch

from server.lockfile import (
    LockInfo,
    LockProbeResult,
    LockState,
    acquire_lock,
    probe_lock,
    release_lock,
)


class TestProbeFree(unittest.TestCase):
    def test_probe_returns_free_when_no_lock_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = os.path.join(tmp, "lock.json")
            with patch("server.lockfile.LOCK_PATH", lock_path):
                result = probe_lock()
        self.assertEqual(result.state, LockState.FREE)
        self.assertIsNone(result.info)


class TestProbeRunning(unittest.TestCase):
    def test_probe_returns_running_when_port_responds(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = os.path.join(tmp, "lock.json")
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
                listener.bind(("127.0.0.1", 0))
                listener.listen(1)
                port = listener.getsockname()[1]
                info = LockInfo(
                    pid=os.getpid(),
                    port=port,
                    target_file="/tmp/x.md",
                    started_at="2026-05-06T00:00:00Z",
                )
                with patch("server.lockfile.LOCK_PATH", lock_path):
                    acquire_lock(info)
                    result = probe_lock()
            self.assertEqual(result.state, LockState.RUNNING)
            self.assertIsNotNone(result.info)
            self.assertEqual(result.info.port, port)


class TestProbeStale(unittest.TestCase):
    def _get_unbound_port(self) -> int:
        """Bind a socket, capture the port, then close it so the port is unbound."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        return port

    def test_probe_returns_stale_when_port_does_not_respond(self):
        port = self._get_unbound_port()
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = os.path.join(tmp, "lock.json")
            info = LockInfo(
                pid=os.getpid(),
                port=port,
                target_file="/tmp/y.md",
                started_at="2026-05-06T00:00:00Z",
            )
            with patch("server.lockfile.LOCK_PATH", lock_path):
                acquire_lock(info)
                result = probe_lock()
        self.assertEqual(result.state, LockState.STALE)
        self.assertIsNotNone(result.info)
        self.assertEqual(result.info.port, port)

    def test_probe_does_not_auto_clear_stale_lock(self):
        """PRD §8: stale lock must NOT be auto-cleared by probe_lock."""
        port = self._get_unbound_port()
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = os.path.join(tmp, "lock.json")
            info = LockInfo(
                pid=os.getpid(),
                port=port,
                target_file="/tmp/z.md",
                started_at="2026-05-06T00:00:00Z",
            )
            with patch("server.lockfile.LOCK_PATH", lock_path):
                acquire_lock(info)
                probe_lock()
                # Lock file must still exist after probe
                self.assertTrue(
                    os.path.exists(lock_path),
                    "probe_lock() must not auto-clear a stale lock (PRD §8)",
                )


class TestAcquireRelease(unittest.TestCase):
    def test_acquire_writes_lock_file_with_expected_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = os.path.join(tmp, "lock.json")
            info = LockInfo(
                pid=12345,
                port=8080,
                target_file="/home/user/notes.md",
                started_at="2026-05-06T12:00:00Z",
            )
            with patch("server.lockfile.LOCK_PATH", lock_path):
                acquire_lock(info)
            with open(lock_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        self.assertEqual(data["pid"], 12345)
        self.assertEqual(data["port"], 8080)
        self.assertEqual(data["target_file"], "/home/user/notes.md")
        self.assertEqual(data["started_at"], "2026-05-06T12:00:00Z")

    def test_acquire_creates_parent_directory_if_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Point at a nested non-existent directory
            lock_path = os.path.join(tmp, "nested", "deep", "lock.json")
            info = LockInfo(
                pid=os.getpid(),
                port=9000,
                target_file="/tmp/a.md",
                started_at="2026-05-06T00:00:00Z",
            )
            with patch("server.lockfile.LOCK_PATH", lock_path):
                acquire_lock(info)
            self.assertTrue(os.path.exists(lock_path))

    def test_release_removes_lock_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = os.path.join(tmp, "lock.json")
            info = LockInfo(
                pid=os.getpid(),
                port=9001,
                target_file="/tmp/b.md",
                started_at="2026-05-06T00:00:00Z",
            )
            with patch("server.lockfile.LOCK_PATH", lock_path):
                acquire_lock(info)
                self.assertTrue(os.path.exists(lock_path))
                release_lock()
                self.assertFalse(os.path.exists(lock_path))

    def test_release_on_missing_file_is_no_op(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = os.path.join(tmp, "lock.json")
            with patch("server.lockfile.LOCK_PATH", lock_path):
                # Should not raise even though no file exists
                release_lock()


if __name__ == "__main__":
    unittest.main()
