"""Tests for server.snapshot — pre-apply markdown snapshot helpers."""

from __future__ import annotations

import os
import tempfile
import unittest

from server.snapshot import SNAPSHOT_SUFFIX, read_snapshot, snapshot_path


class TestSnapshotPath(unittest.TestCase):
    def test_path_is_source_plus_suffix(self):
        self.assertEqual(
            snapshot_path("/tmp/doc.md"),
            "/tmp/doc.md" + SNAPSHOT_SUFFIX,
        )

    def test_path_handles_no_extension(self):
        self.assertEqual(snapshot_path("/tmp/notes"), "/tmp/notes" + SNAPSHOT_SUFFIX)


class TestReadSnapshot(unittest.TestCase):
    def test_returns_none_when_missing(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "doc.md")
            with open(src, "w", encoding="utf-8") as f:
                f.write("# hello\n")
            # No snapshot file exists yet.
            self.assertIsNone(read_snapshot(src))

    def test_returns_content_when_present(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "doc.md")
            with open(src, "w", encoding="utf-8") as f:
                f.write("# current\n")
            snap = snapshot_path(src)
            with open(snap, "w", encoding="utf-8") as f:
                f.write("# original\n\nfirst paragraph.\n")
            self.assertEqual(read_snapshot(src), "# original\n\nfirst paragraph.\n")

    def test_returns_none_on_unreadable(self):
        # A directory at the snapshot path is unreadable as text — should
        # collapse to None, not raise.
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "doc.md")
            with open(src, "w", encoding="utf-8") as f:
                f.write("# x\n")
            os.makedirs(snapshot_path(src))
            self.assertIsNone(read_snapshot(src))


if __name__ == "__main__":
    unittest.main()
