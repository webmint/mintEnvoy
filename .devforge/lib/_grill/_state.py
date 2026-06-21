"""Session state for grill_helper.

Owns the GrillState schema, path helper, and atomic read/write.

/grill is a per-feature command. State is stored alongside the feature's
other artifacts at:

    <feature_dir>/grill-state.json

where <feature_dir> is the path to the feature directory passed by the
orchestrator (e.g. specs/001-auth/).  This follows the precedent set by
`_review/_state.py`, which scopes state to the per-entity directory
rather than a global singleton like `_audit`'s `audits/.state.json`.

The grill flow is: scope -> attack -> validate -> refute -> classify ->
report.  The phase field is updated by each verb to record which phase
the run is currently in.

Precedent followed: `_review/_state.py` (per-entity scoped state) —
state path rooted in the per-feature dir, not a global `audits/` dir.
"""

import dataclasses
import json
import os
import tempfile
from dataclasses import dataclass, field
from typing import List, Optional


_STATE_FILENAME = "grill-state.json"

# Recognised phase labels for documentation; not enforced at write-time
# so future phases can be added without a schema migration.
GRILL_PHASES = ("scope", "attack", "validate", "refute", "classify", "report")


@dataclass
class GrillState:
    """Per-feature grill session state stored at <feature_dir>/grill-state.json.

    Fields are populated by successive verb invocations across phases.
    Defaults represent the empty/unset sentinel for each field type.
    """

    phase: str = ""              # grill phase label (e.g. "scope", "attack", "1".."6")
    feature_dir: str = ""        # path to feature directory (e.g. specs/001-auth/)
    status: str = "in_progress"  # in_progress -> complete
    out_path: str = ""           # target path for the grill report (specs/.../grill.md)
    scope_files: List[str] = field(default_factory=list)
    agent_assignments: List[str] = field(default_factory=list)


def state_path(feature_dir: str) -> str:
    """Return the absolute path to the grill state JSON file.

    Path: <feature_dir>/grill-state.json

    feature_dir may be relative or absolute; result is always absolute
    (via os.path.abspath) so callers can rely on it without knowing cwd.
    """
    abs_dir = os.path.abspath(feature_dir)
    return os.path.join(abs_dir, _STATE_FILENAME)


def read_state(path: str) -> Optional[GrillState]:
    """Read GrillState from a JSON file at path.

    Returns None on OSError (file absent, permission denied) or
    json.JSONDecodeError (corrupt content). Tolerates unknown keys by
    filtering to known dataclass field names before construction.
    """
    known = {f.name for f in dataclasses.fields(GrillState)}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None
    filtered = {k: v for k, v in raw.items() if k in known}
    return GrillState(**filtered)


def write_state(path: str, state: GrillState) -> None:
    """Atomically write state as JSON to path.

    Creates the parent directory if needed. Uses mkstemp + os.replace for
    atomicity; unlinks the temp file on failure before re-raising.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix="grill-state-",
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


def flip_phase(
    path: str, to_phase: str, to_status: Optional[str] = None
) -> GrillState:
    """Read current state (or start fresh), set phase + optional status, write back.

    Raises ValueError if to_phase is empty or whitespace.
    Returns the updated GrillState.
    """
    if not to_phase or not to_phase.strip():
        raise ValueError("to_phase must be non-empty")
    state = read_state(path)
    if state is None:
        state = GrillState()
    state.phase = to_phase
    if to_status is not None:
        state.status = to_status
    write_state(path, state)
    return state
