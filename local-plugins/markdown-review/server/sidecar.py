"""
Sidecar read/write for the markdown-review plugin.

Sidecar files live at <markdown-file>.comments.json in the same directory.
Writes are atomic: data is written to <path>.tmp then renamed into place via
os.replace().  Malformed JSON triggers a backup to <path>.bak and returns a
fresh empty sidecar so callers can continue without data loss.

FRs covered: FR-22, FR-23, FR-25, FR-26, FR-29.
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict, dataclass
from typing import Optional

SIDECAR_VERSION = 1
COMMENT_BODY_MAX_CHARS = 2000


@dataclass
class Comment:
    id: str                         # uuid4
    anchor: dict                    # serialized Anchor
    body: str
    created_at: str                 # ISO-8601 UTC
    updated_at: str                 # ISO-8601 UTC
    applied: bool = False           # set by next-turn Claude after apply
    applied_at: Optional[str] = None


@dataclass
class Sidecar:
    version: int
    source_file: str                # absolute path to the .md
    comments: list[Comment]


class SidecarWriteError(RuntimeError): ...


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _infer_source_file(sidecar_path: str) -> str:
    """Strip the .comments.json suffix to get the markdown file path."""
    suffix = ".comments.json"
    if sidecar_path.endswith(suffix):
        return sidecar_path[: -len(suffix)]
    return ""


def _comment_from_dict(d: dict) -> Comment:
    """Build a Comment from a raw dict, defaulting optional fields."""
    return Comment(
        id=d["id"],
        anchor=d["anchor"],
        body=d["body"],
        created_at=d["created_at"],
        updated_at=d["updated_at"],
        applied=d.get("applied", False),
        applied_at=d.get("applied_at"),
    )


def _sidecar_to_dict(sidecar: Sidecar) -> dict:
    """Serialise a Sidecar to a plain dict ready for json.dumps."""
    return {
        "version": sidecar.version,
        "source_file": sidecar.source_file,
        "comments": [asdict(c) for c in sidecar.comments],
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def read_sidecar(path: str) -> tuple[Sidecar, list[str]]:
    """Return (sidecar, warnings).

    - Missing file → empty sidecar, no warnings.
    - Malformed JSON → backup to <path>.bak, fresh empty sidecar written, warning.
    - Unknown version → sidecar loaded forward-compatibly, warning added.
    - Missing optional comment fields → defaulted silently.
    """
    warnings: list[str] = []
    source_file = _infer_source_file(path)

    # --- read raw bytes (or treat as missing) ---
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        return Sidecar(version=SIDECAR_VERSION, source_file=source_file, comments=[]), warnings

    # --- parse JSON ---
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        bak_path = path + ".bak"
        # Backup the malformed file
        shutil.copy2(path, bak_path)
        # Write a fresh empty sidecar in-place
        fresh = Sidecar(version=SIDECAR_VERSION, source_file=source_file, comments=[])
        try:
            write_sidecar_atomic(path, fresh)
        except SidecarWriteError:
            pass  # Best-effort; fresh sidecar still returned to caller
        warnings.append(
            f"Sidecar at {path!r} contained malformed JSON; "
            f"original backed up to {bak_path!r} and recovered with a fresh empty sidecar."
        )
        return fresh, warnings

    # --- version check ---
    version = data.get("version", SIDECAR_VERSION)
    if version != SIDECAR_VERSION:
        warnings.append(
            f"Sidecar version {version} is unknown to this skill version "
            f"(expected {SIDECAR_VERSION}); reading forward-compatibly."
        )

    # --- build comments ---
    raw_comments = data.get("comments", [])
    comments: list[Comment] = []
    for c in raw_comments:
        try:
            comments.append(_comment_from_dict(c))
        except KeyError as exc:
            warnings.append(f"Skipped comment with missing required field: {exc}")

    sidecar = Sidecar(
        version=version,
        source_file=data.get("source_file", source_file),
        comments=comments,
    )
    return sidecar, warnings


def write_sidecar_atomic(path: str, sidecar: Sidecar) -> None:
    """Write sidecar to <path> atomically via a temp file.

    Raises SidecarWriteError on any I/O failure.
    """
    tmp_path = path + ".tmp"
    payload = json.dumps(_sidecar_to_dict(sidecar), indent=2, ensure_ascii=False)

    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception as exc:
        # Best-effort cleanup of temp file
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise SidecarWriteError(
            f"Failed to write sidecar to {path!r}: {exc}"
        ) from exc
