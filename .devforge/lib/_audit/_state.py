"""Session state for audit_helper.

Owns the AuditState schema, path helper, and atomic read/write.
One active audit at a time — stored at <workspace_root>/audits/.state.json.
"""

from __future__ import annotations

import dataclasses
import json
import os
import tempfile
from dataclasses import dataclass, field
from typing import List, Optional


_STATE_FILENAME = ".state.json"
_AUDITS_DIR = "audits"


@dataclass
class AuditState:
    """Per-audit session state stored at <workspace_root>/audits/.state.json.

    Fields are populated by successive verb invocations across phases.
    Defaults represent the empty/unset sentinel for each field type.
    """

    phase: str = ""                  # audit phase label (e.g. "1".."6" or "preflight")
    mode: str = ""                   # narrow / hotspot / broad
    scope_description: str = ""
    scope_files: List[str] = field(default_factory=list)
    out_path: str = ""               # target audits/YYYY-MM-DD-audit.md path
    status: str = "in_progress"      # in_progress -> complete


def state_path(workspace_root: str) -> str:
    """Return the absolute path to the audit state JSON file.

    Path: <workspace_root>/audits/.state.json

    workspace_root may be relative or absolute; result is always absolute
    (via os.path.abspath) so callers can rely on it without knowing cwd.
    """
    abs_root = os.path.abspath(workspace_root)
    return os.path.join(abs_root, _AUDITS_DIR, _STATE_FILENAME)


def read_state(path: str) -> Optional[AuditState]:
    """Read AuditState from a JSON file at path.

    Returns None on OSError (file absent, permission denied) or
    json.JSONDecodeError (corrupt content). Tolerates unknown keys by
    filtering to known dataclass field names before construction.
    """
    known = {f.name for f in dataclasses.fields(AuditState)}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None
    filtered = {k: v for k, v in raw.items() if k in known}
    return AuditState(**filtered)


def write_state(path: str, state: AuditState) -> None:
    """Atomically write state as JSON to path.

    Creates the parent directory if needed. Uses mkstemp + os.replace for
    atomicity; unlinks the temp file on failure before re-raising.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix="audit-state-",
        suffix=".json.tmp",
        dir=os.path.dirname(path),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(dataclasses.asdict(state), fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def flip_phase(path: str, to_phase: str, to_status: Optional[str] = None) -> AuditState:
    """Read current state (or start fresh), set phase + optional status, write back.

    Raises ValueError if to_phase is empty or whitespace.
    Returns the updated AuditState.
    """
    if not to_phase or not to_phase.strip():
        raise ValueError("to_phase must be non-empty")
    state = read_state(path)
    if state is None:
        state = AuditState()
    state.phase = to_phase
    if to_status is not None:
        state.status = to_status
    write_state(path, state)
    return state
