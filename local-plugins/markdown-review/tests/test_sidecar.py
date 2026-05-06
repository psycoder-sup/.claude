"""
Tests for server.sidecar — read/write, atomic writes, version handling, malformed JSON.

Covers:
- FR-22: round-trip (write then read returns identical sidecar)
- FR-23: atomic write (temp-file + rename, partial-write invisible)
- FR-25: version tag written and read
- FR-26: unknown future version loads with warning
- FR-29: malformed JSON → backup to .bak, fresh sidecar, warning
"""

import json
import os
import stat
import unittest
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from server.sidecar import (
    Comment,
    Sidecar,
    SidecarWriteError,
    SIDECAR_VERSION,
    read_sidecar,
    write_sidecar_atomic,
)


def _make_comment(body="Test comment body") -> Comment:
    now = datetime.now(timezone.utc).isoformat()
    return Comment(
        id="11111111-1111-1111-1111-111111111111",
        anchor={"block_path": ["Introduction"], "block_index": 0, "content_hash": "abc123"},
        body=body,
        created_at=now,
        updated_at=now,
    )


def _make_sidecar(source_file: str, comments=None) -> Sidecar:
    return Sidecar(
        version=SIDECAR_VERSION,
        source_file=source_file,
        comments=comments if comments is not None else [],
    )


# ---------------------------------------------------------------------------
# Round-trip tests — FR-22
# ---------------------------------------------------------------------------

class TestRoundTrip(unittest.TestCase):

    def test_round_trip_simple(self):
        """Write a Sidecar with one Comment, read back, fields match exactly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = os.path.join(tmpdir, "notes.md")
            sidecar_path = md_path + ".comments.json"

            comment = _make_comment("Hello, world!")
            original = _make_sidecar(md_path, [comment])

            write_sidecar_atomic(sidecar_path, original)
            result, warnings = read_sidecar(sidecar_path)

            self.assertEqual(warnings, [])
            self.assertEqual(result.version, SIDECAR_VERSION)
            self.assertEqual(result.source_file, md_path)
            self.assertEqual(len(result.comments), 1)

            c = result.comments[0]
            self.assertEqual(c.id, comment.id)
            self.assertEqual(c.anchor, comment.anchor)
            self.assertEqual(c.body, comment.body)
            self.assertEqual(c.created_at, comment.created_at)
            self.assertEqual(c.updated_at, comment.updated_at)
            self.assertEqual(c.applied, False)
            self.assertIsNone(c.applied_at)

    def test_round_trip_multibyte_utf8(self):
        """Comment body with multi-byte UTF-8 characters round-trips correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = os.path.join(tmpdir, "notes.md")
            sidecar_path = md_path + ".comments.json"

            body = "한글 — émojis: 🐉🌸"
            comment = _make_comment(body)
            original = _make_sidecar(md_path, [comment])

            write_sidecar_atomic(sidecar_path, original)
            result, warnings = read_sidecar(sidecar_path)

            self.assertEqual(warnings, [])
            self.assertEqual(result.comments[0].body, body)

    def test_round_trip_empty_sidecar(self):
        """Sidecar with no comments writes and reads back as empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = os.path.join(tmpdir, "notes.md")
            sidecar_path = md_path + ".comments.json"

            original = _make_sidecar(md_path, [])
            write_sidecar_atomic(sidecar_path, original)
            result, warnings = read_sidecar(sidecar_path)

            self.assertEqual(warnings, [])
            self.assertEqual(result.comments, [])
            self.assertEqual(result.source_file, md_path)


# ---------------------------------------------------------------------------
# Atomic write tests — FR-23
# ---------------------------------------------------------------------------

class TestAtomicWrite(unittest.TestCase):

    def test_atomic_write_uses_temp_then_rename(self):
        """os.replace is called with (tmp_path, dest_path) exactly once."""
        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = os.path.join(tmpdir, "notes.md")
            sidecar_path = md_path + ".comments.json"
            tmp_path = sidecar_path + ".tmp"

            sidecar = _make_sidecar(md_path)

            replace_calls = []
            original_replace = os.replace

            def recording_replace(src, dst):
                replace_calls.append((src, dst))
                return original_replace(src, dst)

            with patch("os.replace", side_effect=recording_replace):
                write_sidecar_atomic(sidecar_path, sidecar)

            self.assertEqual(len(replace_calls), 1)
            self.assertEqual(replace_calls[0], (tmp_path, sidecar_path))
            # temp file should not exist after successful rename
            self.assertFalse(os.path.exists(tmp_path))

    def test_atomic_write_failure_raises_sidecar_write_error(self):
        """Read-only directory causes SidecarWriteError; destination file unchanged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = os.path.join(tmpdir, "notes.md")
            sidecar_path = md_path + ".comments.json"

            sidecar = _make_sidecar(md_path)

            # Make directory read-only so we cannot create any file in it
            os.chmod(tmpdir, 0o555)
            try:
                with self.assertRaises(SidecarWriteError):
                    write_sidecar_atomic(sidecar_path, sidecar)
                self.assertFalse(os.path.exists(sidecar_path))
            finally:
                # Restore so tempdir cleanup can succeed
                os.chmod(tmpdir, 0o755)

    def test_partial_write_invisible(self):
        """If write fails mid-way, destination retains original content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = os.path.join(tmpdir, "notes.md")
            sidecar_path = md_path + ".comments.json"

            # Write initial content X
            comment_x = _make_comment("Content X")
            sidecar_x = _make_sidecar(md_path, [comment_x])
            write_sidecar_atomic(sidecar_path, sidecar_x)

            # Attempt to write content Y but fail before os.replace
            comment_y = _make_comment("Content Y")
            sidecar_y = _make_sidecar(md_path, [comment_y])

            with patch("os.replace", side_effect=OSError("simulated failure")):
                with self.assertRaises(SidecarWriteError):
                    write_sidecar_atomic(sidecar_path, sidecar_y)

            # Destination should still contain X
            result, _ = read_sidecar(sidecar_path)
            self.assertEqual(result.comments[0].body, "Content X")


# ---------------------------------------------------------------------------
# Version tag tests — FR-25, FR-26
# ---------------------------------------------------------------------------

class TestVersionTag(unittest.TestCase):

    def test_version_tag_is_written(self):
        """Written JSON file contains 'version': 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = os.path.join(tmpdir, "notes.md")
            sidecar_path = md_path + ".comments.json"

            write_sidecar_atomic(sidecar_path, _make_sidecar(md_path))

            with open(sidecar_path, encoding="utf-8") as f:
                data = json.load(f)

            self.assertIn("version", data)
            self.assertEqual(data["version"], SIDECAR_VERSION)

    def test_unknown_future_version_loads_with_warning(self):
        """Version 99 sidecar loads; warnings mention version 99; missing fields default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = os.path.join(tmpdir, "notes.md")
            sidecar_path = md_path + ".comments.json"

            now = datetime.now(timezone.utc).isoformat()
            future_data = {
                "version": 99,
                "source_file": md_path,
                "comments": [
                    {
                        "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                        "anchor": {"block_path": ["Intro"], "block_index": 0, "content_hash": "xyz"},
                        "body": "Future comment",
                        "created_at": now,
                        "updated_at": now,
                        # applied_at intentionally omitted
                    }
                ],
            }
            with open(sidecar_path, "w", encoding="utf-8") as f:
                json.dump(future_data, f)

            result, warnings = read_sidecar(sidecar_path)

            self.assertEqual(len(result.comments), 1)
            self.assertIsNone(result.comments[0].applied_at)
            self.assertTrue(any("99" in w for w in warnings),
                            f"Expected warning mentioning version 99; got: {warnings}")

    def test_missing_optional_fields_default(self):
        """Comment missing 'applied' and 'applied_at' loads with defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = os.path.join(tmpdir, "notes.md")
            sidecar_path = md_path + ".comments.json"

            now = datetime.now(timezone.utc).isoformat()
            data = {
                "version": SIDECAR_VERSION,
                "source_file": md_path,
                "comments": [
                    {
                        "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                        "anchor": {"block_path": ["Sec"], "block_index": 1, "content_hash": "hash1"},
                        "body": "Minimal comment",
                        "created_at": now,
                        "updated_at": now,
                        # 'applied' and 'applied_at' intentionally omitted
                    }
                ],
            }
            with open(sidecar_path, "w", encoding="utf-8") as f:
                json.dump(data, f)

            result, warnings = read_sidecar(sidecar_path)

            self.assertEqual(warnings, [])
            c = result.comments[0]
            self.assertEqual(c.applied, False)
            self.assertIsNone(c.applied_at)


# ---------------------------------------------------------------------------
# Malformed JSON tests — FR-29
# ---------------------------------------------------------------------------

class TestMalformedJson(unittest.TestCase):

    def test_malformed_json_triggers_backup_and_fresh_sidecar(self):
        """Garbage JSON triggers .bak, fresh empty sidecar, and warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = os.path.join(tmpdir, "document.md")
            sidecar_path = md_path + ".comments.json"
            bak_path = sidecar_path + ".bak"

            garbage = b"}{not valid json at all!!"
            with open(sidecar_path, "wb") as f:
                f.write(garbage)

            result, warnings = read_sidecar(sidecar_path)

            # 1. Backup exists with original garbage content
            self.assertTrue(os.path.exists(bak_path),
                            ".bak file should be created")
            with open(bak_path, "rb") as f:
                self.assertEqual(f.read(), garbage)

            # 2. Returned sidecar has empty comments list
            self.assertEqual(result.comments, [])

            # 3. Warnings mention malformed / recovered
            self.assertTrue(
                any("malformed" in w.lower() or "recovered" in w.lower() for w in warnings),
                f"Expected warning with 'malformed' or 'recovered'; got: {warnings}",
            )

            # 4. Sidecar file is reset to fresh empty sidecar (readable JSON)
            with open(sidecar_path, encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["comments"], [])
            self.assertIn("version", data)


# ---------------------------------------------------------------------------
# Read missing file
# ---------------------------------------------------------------------------

class TestReadMissingFile(unittest.TestCase):

    def test_read_nonexistent_returns_empty_sidecar(self):
        """read_sidecar on a nonexistent path returns empty Sidecar, no warnings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sidecar_path = os.path.join(tmpdir, "ghost.md.comments.json")

            result, warnings = read_sidecar(sidecar_path)

            self.assertEqual(warnings, [])
            self.assertEqual(result.version, SIDECAR_VERSION)
            self.assertEqual(result.comments, [])


if __name__ == "__main__":
    unittest.main()
