"""State plumbing for discover_helper — defaults + IO + transactions.

Owns the shape of the two /discover state files (discover-scope.json and
discover-report.json) and the read-modify-write transaction primitive
used by every setter handler.
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from pathlib import Path
from typing import Iterator, Union

try:
    import fcntl
    _HAVE_FCNTL = True
except ImportError:  # pragma: no cover - non-POSIX fallback
    _HAVE_FCNTL = False


# ---------------------------------------------------------------------------
# Schema constants — single source of truth.
# ---------------------------------------------------------------------------

MEMO_FILE_NAME = "discover-scope.json"
REPORT_FILE_NAME = "discover-report.json"

# Phase 0 rubric — 8 dimensions. Locked order: this is the order
# coverage emits, render uses, and tests verify.
RUBRIC_DIMENSIONS = (
    "functional_scope",
    "users",
    "inputs_outputs",
    "integration_points",
    "constraints",
    "non_goals",
    "success_criteria",
    "edge_cases",
)

# Per-dimension state machine. Helper transitions Missing→Partial→Clear
# as setters fire.
RUBRIC_STATE_DEFAULT = "Missing"


# ---------------------------------------------------------------------------
# Default-state builders.
# ---------------------------------------------------------------------------


def _empty_dimension() -> dict:
    """Return a fresh rubric-dimension record."""
    return {"value": None, "state": RUBRIC_STATE_DEFAULT, "turns": 0}


def default_memo_state() -> dict:
    """Return a fresh ScopingMemo state matching schema."""
    return {
        "topic": None,
        "topic_slug": None,
        "date": None,
        # verbatim_prompt (v1.1): the raw user prompt text, persisted by
        # set-verbatim-prompt at Phase 0.3 right after set-topic.
        # None until set; finalize-handoff guards on this field before
        # constructing Intent.verbatim_prompt.
        "verbatim_prompt": None,
        "dimensions": {d: _empty_dimension() for d in RUBRIC_DIMENSIONS},
        "references": [],
        "gaps": [],
        "override_recorded": False,
        "conflicts": [],
        # Step 5 — intake classification records. Each entry:
        # {statement: str, kind: "requirement"|"hypothesis", minimal_fix: str|None}.
        # Appended by record-intake-classification; read by render-intake-echo.
        # NOTE discover lane divergence: a "hypothesis" kind here is a
        # scope-expander or placement guess, routed to record-gap
        # --dimension integration_points — NOT a research-style suspected
        # cause. discover has no record-hypothesis verb.
        # Idempotent: same statement replaces existing entry.
        "intake_classifications": [],
    }


def default_report_state() -> dict:
    """Return a fresh DiscoveryReport state matching schema."""
    return {
        "topic": None,
        "date": None,
        "topic_slug": None,
        "summary": None,
        "prior_art": [],
        "integration_touchpoints": [],
        "fit_assessments": [],
        "overall_fit": None,
        "effort_estimate": None,
        "fit_rationale": None,
        "design_options": [],
        "recommended_option": None,
        "build_vs_buy": None,
        "derisk_plan": [],
        "constitution_constraints": [],
        "verdict": None,
        "recommendation": None,
        "next_step_text": None,
        "open_uncertainties": [],
    }


# ---------------------------------------------------------------------------
# State-file plumbing (load / dump / transaction).
# ---------------------------------------------------------------------------


def _memo_path(devforge_dir: Union[str, "os.PathLike[str]"]) -> Path:
    return Path(devforge_dir) / MEMO_FILE_NAME


def _report_path(devforge_dir: Union[str, "os.PathLike[str]"]) -> Path:
    return Path(devforge_dir) / REPORT_FILE_NAME


def _atomic_write_json(state: dict, target: Path) -> None:
    """Atomically write state as JSON to target.

    Uses tempfile.mkstemp in the same directory + os.replace.
    flush + fsync precede os.replace for durability.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix="discover-",
        suffix=".json.tmp",
        dir=str(target.parent),
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


def _load_memo(devforge_dir: Union[str, "os.PathLike[str]"]) -> dict:
    """Load discover-scope.json. Missing → default_memo_state()."""
    path = _memo_path(devforge_dir)
    if not path.exists():
        return default_memo_state()
    return json.loads(path.read_text(encoding="utf-8"))


def _load_report(devforge_dir: Union[str, "os.PathLike[str]"]) -> dict:
    """Load discover-report.json. Missing → default_report_state()."""
    path = _report_path(devforge_dir)
    if not path.exists():
        return default_report_state()
    return json.loads(path.read_text(encoding="utf-8"))


def _lock_path(state_path: Path) -> Path:
    return state_path.parent / (state_path.name + ".lock")


@contextlib.contextmanager
def _state_transaction(
    devforge_dir: Union[str, "os.PathLike[str]"],
    which: str,
) -> Iterator[dict]:
    """Read-modify-write either memo or report under fcntl lock.

    `which` in {"memo", "report"}. On POSIX, fcntl.flock(LOCK_EX) on the
    sidecar lock file. On Windows (no fcntl), no-op locking — out of
    scope for AIDevTeamForge. Body raise → write skipped, exception
    propagates.
    """
    if which == "memo":
        state_path = _memo_path(devforge_dir)
        loader = _load_memo
    elif which == "report":
        state_path = _report_path(devforge_dir)
        loader = _load_report
    else:
        raise ValueError("unknown state {0!r}".format(which))

    devforge_path = Path(devforge_dir)
    devforge_path.mkdir(parents=True, exist_ok=True)
    lock = _lock_path(state_path)
    fd = os.open(str(lock), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        if _HAVE_FCNTL:
            fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            state = loader(devforge_dir)
            yield state
            _atomic_write_json(state, state_path)
        finally:
            if _HAVE_FCNTL:
                fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)
