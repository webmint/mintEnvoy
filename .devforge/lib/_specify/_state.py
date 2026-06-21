"""State plumbing: default_state + atomic write + load + transaction."""

from __future__ import annotations

import contextlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterator, Union

from ._schema import SPEC_STATUS_DEFAULT, STATE_FILE_NAME

try:
    import fcntl
    _HAVE_FCNTL = True
except ImportError:  # pragma: no cover - non-POSIX fallback
    _HAVE_FCNTL = False


def default_state() -> Dict[str, Any]:
    """Fresh SpecDoc state. Full Step 2 schema shape — all phase buckets."""
    return {
        # --- Header / classification ---------------------------------------
        "topic": None,
        "topic_slug": None,
        "date": None,
        "spec_number": None,
        "feature_name": None,
        "feature_slug": None,
        "spec_type": None,
        "spec_type_rationale": None,
        "spec_type_seeded_by_upstream": False,
        "status": SPEC_STATUS_DEFAULT,

        # --- Phase 0 — branch state ----------------------------------------
        "current_branch": None,
        "default_branch": None,
        "branch_decision": None,
        "branch_created": None,

        # --- Phase 1 — input reads -----------------------------------------
        "input_reads": [],
        "phase1_finalized": False,

        # --- Phase 1.5 — findings ------------------------------------------
        "findings": [],
        "source_no_items_relevant": {},
        "findings_finalized": False,

        # --- Phase 2 — decision points -------------------------------------
        "decision_points": [],
        "dp_finalized": False,
        "mode": None,

        # --- Phase 3 — codebase analysis -----------------------------------
        "mandatory_reads": [],
        "discretionary_reads": [],
        "phase3_finalized": False,

        # --- Phase 4 — spec sections ---------------------------------------
        "overview": None,
        "current_state": None,
        "desired_behavior": None,
        "affected_areas": [],
        "acceptance_criteria": [],
        "ac_subsection_na": {},
        "out_of_scope": [],
        "constraints": [],
        "open_questions": [],
        "risks": [],

        # --- Phase 5 — approval + handoff ----------------------------------
        "approval_summary": None,
        "plan_handoff_block": None,

        # --- Downstream — /plan + /breakdown audit -------------------------
        "open_question_resolutions": [],

        # --- Misalignment log ----------------------------------------------
        "conflicts": [],

        # --- Pre-phase — handoff source -----------------------------------
        "source": {
            "handoff_path": None,
            "handoff_kind": None,
            "research_completed_at": None,
            "discover_completed_at": None,
            "discover_recommended_summary": None,
        },
    }


def _state_path(devforge_dir: Union[str, "os.PathLike[str]"]) -> Path:
    return Path(devforge_dir) / STATE_FILE_NAME


def _atomic_write_json(state: Dict[str, Any], target: Path) -> None:
    """Atomically write state as JSON. Same pattern as discover_helper."""
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix="specify-", suffix=".json.tmp", dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, sort_keys=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(target))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _load_state(devforge_dir: Union[str, "os.PathLike[str]"]) -> Dict[str, Any]:
    path = _state_path(devforge_dir)
    if not path.exists():
        return default_state()
    state = json.loads(path.read_text(encoding="utf-8"))
    # Legacy migration warning: --kind=use entries are silently skipped by
    # the new render loop; emit a one-time warning per entry so the drop is
    # visible. Does NOT change exit code or block parsing.
    for c in state.get("constraints", []):
        if c.get("kind") == "use":
            sys.stderr.write(
                "specify_helper: legacy --kind=use constraint found in state"
                " — content: {0!r}\n"
                "  Action: re-record via /specify Step 4.6 using"
                " nfr / constitution_anchor / external_system.\n"
                .format(c.get("content", ""))
            )
    return state


def _lock_path(state_path: Path) -> Path:
    return state_path.parent / (state_path.name + ".lock")


@contextlib.contextmanager
def _state_transaction(
    devforge_dir: Union[str, "os.PathLike[str]"],
) -> Iterator[Dict[str, Any]]:
    """Read-modify-write under POSIX fcntl lock. Mirrors discover_helper."""
    state_path = _state_path(devforge_dir)
    Path(devforge_dir).mkdir(parents=True, exist_ok=True)
    lock = _lock_path(state_path)
    fd = os.open(str(lock), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        if _HAVE_FCNTL:
            fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            state = _load_state(devforge_dir)
            yield state
            _atomic_write_json(state, state_path)
        finally:
            if _HAVE_FCNTL:
                fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)
