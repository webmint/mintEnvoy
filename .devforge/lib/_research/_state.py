"""State-file plumbing for research_helper memo + report JSON files.

Owns default-state builders, atomic read/write, and the fcntl-locked
state-transaction context manager. Memo (research-state.json) holds
Phase 0 rubric Q&A; report (research-report.json) holds Phase 1+2
findings/hypotheses/approaches/verdict/etc.
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Iterator, Union

from ._constants import (
    MEMO_FILE_NAME,
    REPORT_FILE_NAME,
    RUBRIC_DIMENSIONS,
    RUBRIC_STATE_DEFAULT,
)

try:
    import fcntl
    _HAVE_FCNTL = True
except ImportError:  # pragma: no cover - non-POSIX fallback
    _HAVE_FCNTL = False


# ---------------------------------------------------------------------------
# Default-state builders.
# ---------------------------------------------------------------------------


def _empty_dimension() -> dict:
    """Return a fresh rubric-dimension record."""
    return {"value": None, "state": RUBRIC_STATE_DEFAULT, "turns": 0}


def default_memo_state() -> dict:
    """Return a fresh SymptomMemo state matching schema."""
    return {
        "mode": None,
        "topic_slug": None,
        # verbatim_prompt (v1.1): the raw user prompt text, persisted by
        # set-verbatim-prompt at Phase 0.3 right after set-topic.
        # None until set; finalize-handoff guards on this field before
        # constructing Intent.verbatim_prompt.
        "verbatim_prompt": None,
        "dimensions": {d: _empty_dimension() for d in RUBRIC_DIMENSIONS},
        "gaps": [],
        "override_recorded": False,
        "conflicts": [],
        # Step 5 — intake classification records. Each entry:
        # {statement: str, kind: "requirement"|"hypothesis", minimal_fix: str|None}.
        # Appended by record-intake-classification; read by render-intake-echo.
        # Append-only; re-recording the same statement replaces its entry (idempotent).
        "intake_classifications": [],
    }


def default_report_state() -> dict:
    """Return a fresh ResearchReport state matching schema.

    Mirrors SymptomMemo by copying mode + symptom snapshot at Phase 1
    dispatch time; orchestrator is responsible for snapshotting.
    """
    return {
        "topic": None,
        "date": None,
        "mode": None,
        "symptom_snapshot": {d: None for d in RUBRIC_DIMENSIONS},
        "summary": None,
        "findings": [],
        "hypotheses": [],
        "root_cause_hypothesis": None,
        "confidence": None,
        "structured_root_cause": None,
        "verify_step": None,
        "approaches": [],
        "recommended_approach": None,
        "constitution_constraints": [],
        "complexity": None,
        "open_uncertainties": [],
        "verdict": None,
        "next_step_text": None,
        # Phase 2.3b — runner-up framing. None until record-runner-up-framing fires;
        # overwritten (last call wins) if called more than once.
        "runner_up_framing": None,
        # Phase 2.4c — helper-API surface enumeration fields.
        "fix_path_helpers": [],
        "inbound_callers": [],
        "dead_siblings": [],
        "consumer_chain": [],
        "value_semantics": [],
        # Patch 5 — anchor-gate rejection log. Each entry: {qn, file_line}.
        # Records (qn, file_line) combos rejected by the anchor check so that
        # sticky-reject can block post-hoc-anchor adversarial retries.
        "helper_rejection_log": [],
        # Patch 6 — data-flow chain (Gap 6: adapter tracing). None until
        # record-data-flow-chain fires; overwritten (last-write-wins) on re-call.
        "data_flow_chain": None,
        # Patch 7 — value production sites (Gap 7: id-stability axis). Each entry:
        # {value, file_line, is_stable}. Multi-site per value via distinct file_line
        # dedupe: same (value, file_line) pair is no-op; different file_lines append.
        "value_production_sites": [],
        # Patch 8 (V3) — literal archaeology rows for hardcoded literals that the
        # recommended approach proposes to replace. Each entry:
        # {literal, file_line, introduced_by, introduced_when, commit_subject, intent}.
        # Dedupe on (literal, file_line) — re-recording same pair is no-op.
        "literal_archaeology": [],
        # Step 4 — probe-tier feasibility (set by LLM via set-probe-feasibility before
        # finalize-handoff). All five booleans default None; helper rejects finalize-
        # handoff with any None when classifier runs. Closed enum: True/False/None.
        "probe_feasibility": {
            "data_shape_only": None,
            "auth_required": None,
            "network_dependent": None,
            "timing_dependent": None,
            "is_test_code": None,
        },
        # Step 5 — Tier-1.5 standalone probe scripts. Each entry:
        # {script_path, runtime, inlines_from: [list], recorded_at: ISO-UTC}.
        # Append-only; deduped by script_path (same path is no-op).
        # finalize-handoff uses probe_scripts[-1]["script_path"] when tier=1.5.
        "probe_scripts": [],
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
        prefix="research-",
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
    """Load research-state.json. Missing → default_memo_state()."""
    path = _memo_path(devforge_dir)
    if not path.exists():
        return default_memo_state()
    return json.loads(path.read_text(encoding="utf-8"))


def _load_report(devforge_dir: Union[str, "os.PathLike[str]"]) -> dict:
    """Load research-report.json. Missing → default_report_state()."""
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

    `which` ∈ {"memo", "report"}. On POSIX, fcntl.flock(LOCK_EX) on the
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
