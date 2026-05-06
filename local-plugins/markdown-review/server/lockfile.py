"""
Cross-process duplicate detection via lock file + port probe.

FR-07: When the skill is invoked while another instance is already running,
the second invocation refuses to start and reports the running instance's
URL and target file.

Lock file path: ~/.cache/markdown-review/lock.json
Detection: port probe with 200ms timeout (socket.create_connection).

States:
  FREE    — no lock file
  RUNNING — lock file present and port responds
  STALE   — lock file present but port does not respond

PRD §8: No auto-clear of stale locks. Manual clear only.
"""

import json
import os
import socket
from dataclasses import asdict, dataclass
from typing import Optional

LOCK_PATH = "~/.cache/markdown-review/lock.json"
PROBE_TIMEOUT_SECONDS = 0.2


@dataclass
class LockInfo:
    pid: int
    port: int
    target_file: str
    started_at: str  # ISO-8601 UTC


class LockState:
    FREE = "free"       # no lock file
    RUNNING = "running" # lock file present and port responds
    STALE = "stale"     # lock file present but port does not respond


@dataclass
class LockProbeResult:
    state: str                # one of LockState.*
    info: Optional[LockInfo]  # populated for RUNNING and STALE


def _resolve_lock_path() -> str:
    return os.path.expanduser(LOCK_PATH)


def _port_is_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=PROBE_TIMEOUT_SECONDS):
            return True
    except (OSError, ConnectionRefusedError):
        return False


def probe_lock() -> LockProbeResult:
    """Read the lock file and probe the port to determine current state.

    Does NOT auto-clear stale locks (PRD §8).
    """
    path = _resolve_lock_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        info = LockInfo(**data)
    except FileNotFoundError:
        return LockProbeResult(state=LockState.FREE, info=None)
    except (OSError, ValueError, TypeError):
        # Unreadable or malformed lock — treat as stale with no info.
        return LockProbeResult(state=LockState.STALE, info=None)
    if _port_is_open(info.port):
        return LockProbeResult(state=LockState.RUNNING, info=info)
    return LockProbeResult(state=LockState.STALE, info=info)


def acquire_lock(info: LockInfo) -> None:
    """Write the lock file. Creates parent directories as needed.

    Does not auto-clear an existing stale lock — callers should check
    probe_lock() first.
    """
    path = _resolve_lock_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(info), f, indent=2)


def release_lock() -> None:
    """Remove the lock file. Called on clean exit + SIGINT drain.

    No-op if the lock file does not exist.
    """
    path = _resolve_lock_path()
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
