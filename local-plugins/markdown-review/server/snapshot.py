"""
Pre-apply snapshot of the source markdown.

The apply step (see ``skills/annotate/references/apply-comments-prompt.md``)
copies the source markdown to ``<source>.review-snapshot.md`` *before* making
any edit. The server reads that snapshot on every ``/api/document`` request
and computes which blocks have changed since, so the review UI can highlight
exactly what Claude (or any other writer) just modified.

The snapshot is read-only from the server's perspective — writes are owned by
the apply step. Missing or unreadable snapshot ⇒ no diff information; the UI
just shows nothing extra, matching the pre-feature behavior.
"""

from __future__ import annotations

import os
from typing import Optional

SNAPSHOT_SUFFIX = ".review-snapshot.md"


def snapshot_path(source_path: str) -> str:
    """Return the snapshot path for a given markdown source path."""
    return source_path + SNAPSHOT_SUFFIX


def read_snapshot(source_path: str) -> Optional[str]:
    """Read the snapshot for ``source_path``, or ``None`` if missing/unreadable.

    Any I/O error (FileNotFoundError, PermissionError, unicode decode failures)
    collapses to ``None`` — the snapshot is best-effort. Callers treat ``None``
    as "no baseline; show no diff."
    """
    path = snapshot_path(source_path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return None
