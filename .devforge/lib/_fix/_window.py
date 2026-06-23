"""_window.py — detect the post-/implement, pre-/summarize window.

OQ-4 decision: helper verb (in-fix-window) — so the always-on rule in
src/CLAUDE.md stays short (plan-08 discipline) and the detection is
deterministic rather than model-judged.

The window is the post-/implement / pre-/summarize state: the feature's
WIP commits are still open (not squashed/finalized), so an in-place /fix
lands cleanly as another [WIP] commit.

Window signals (AND — all three must be true):
  1. The feature directory has at least one task file in tasks/ AND ALL
     task files have ``**Status**: Complete`` or ``**Status**: Skipped``
     (i.e. /implement has fully drained them — not a no-task edge case
     with an empty tasks/ directory, and not mid-/implement with tasks
     still in progress).  README.md is deliberately excluded from the
     scan: it is the /breakdown-generated task INDEX (a per-task status
     TABLE, not a task file), and it never carries a ``**Status**:`` line.
     Parity with _implement/_cmds_resolve.py which uses the same exclusion.
  2. specs/[feature]/summary.md does NOT exist yet (i.e. /summarize has
     NOT run — the feature is not sealed).
  3. The spec ``**Status**:`` is NOT ``Complete`` (i.e. /verify has not
     flipped the spec — a belt-and-suspenders check that reinforces #2).

Out-of-window cases:
  - summary.md present                             → sealed, return False
  - spec **Status**: Complete                       → sealed, return False
  - no tasks/ directory or tasks/ is empty          → not-yet-implemented, return False
  - any task still In Progress / not complete       → return False, reason=not_all_tasks_complete
    (tasks must ALL be terminal/complete; mid-/implement means /fix is not yet valid —
    a wip-commit landing here would stomp /implement's .devforge/wip.md marker)

Candidate signal design rationale:
  - summary.md presence is the strongest sealed signal (/summarize writes it).
  - Task-file scanning (ALL complete) confirms /implement has fully drained
    the feature, distinguishing the in-window case from a not-yet-started or
    still-in-progress feature.
  - Spec status Complete is belt-and-suspenders (the /verify APPROVED path
    always flips it before /summarize can write summary.md).
  - We do NOT gate on verification.md existence: /fix can be triggered by
    /review findings before /verify runs, so verification.md is optional.

Public surface
--------------
  in_fix_window(feature_dir) -> dict
      Returns:
        {
          "in_window": bool,
          "reason":    str,   # machine-readable reason slug (see below)
        }

      reason slugs:
        "in_window"              — all signals pass (in-window)
        "no_tasks_dir"           — tasks/ directory absent → not-yet-implemented
        "no_task_files"          — tasks/ is empty → not-yet-implemented
        "all_tasks_complete"     — all tasks terminal, summary absent, spec not
                                   Complete → in-window (this IS the in_window reason)
        "summary_present"        — summary.md exists → sealed
        "spec_complete"          — spec **Status**: Complete → sealed (without summary)
        "not_all_tasks_complete" — at least one task is not Complete/Skipped
                                   → not-yet-fully-implemented, return False

Stdlib only.  Python 3.8+.  No I/O except file reads.
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Canonical repo-wide **Status**: pattern — matches the rest-of-line after the
# colon so that "Complete", "In Progress", "Skipped" etc. are all captured.
# Same form used in _implement/_cmds_resolve.py, _verify/_specstatus.py,
# plan_helper.py, breakdown_helper.py.  Use .strip().lower() on the captured
# group for comparison.
_STATUS_RE = re.compile(r"^\*\*Status\*\*:[ \t]*(.+)$", re.MULTILINE)

# Complete/Skipped terminal states for tasks.
_TERMINAL_STATUSES = frozenset(["complete", "skipped", "done"])

_SPEC_COMPLETE_STATUSES = frozenset(["complete", "done"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _task_is_terminal(task_path):
    # type: (str) -> Optional[bool]
    """Return True if the task file has a terminal Status, False if not, None on error."""
    try:
        with open(task_path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return None
    m = _STATUS_RE.search(text)
    if m:
        status = m.group(1).strip().lower()
        return status in _TERMINAL_STATUSES
    # No Status line found — treat as not-terminal (in progress).
    return False


def _spec_is_complete(spec_path):
    # type: (str) -> bool
    """Return True if the spec.md has **Status**: Complete."""
    try:
        with open(spec_path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return False
    m = _STATUS_RE.search(text)
    if m:
        return m.group(1).strip().lower() in _SPEC_COMPLETE_STATUSES
    return False


# ---------------------------------------------------------------------------
# in_fix_window (public)
# ---------------------------------------------------------------------------


def in_fix_window(feature_dir):
    # type: (str) -> Dict
    """Detect whether feature_dir is in the post-/implement, pre-/summarize window.

    Parameters
    ----------
    feature_dir : str
        Path to the feature directory (e.g. "specs/001-auth/").
        Expected layout:
          <feature_dir>/spec.md        — the feature spec
          <feature_dir>/tasks/*.md     — task files (at least one required)
          <feature_dir>/summary.md     — written by /summarize (must NOT exist)

    Returns
    -------
    dict:
      {
        "in_window": bool,
        "reason":    str,
      }
    """
    feature_dir = feature_dir.rstrip("/\\")

    # Signal 2: summary.md must NOT exist (strongest sealed signal).
    summary_path = os.path.join(feature_dir, "summary.md")
    if os.path.isfile(summary_path):
        return {"in_window": False, "reason": "summary_present"}

    # Signal 3: spec must NOT be Complete.
    spec_path = os.path.join(feature_dir, "spec.md")
    if _spec_is_complete(spec_path):
        return {"in_window": False, "reason": "spec_complete"}

    # Signal 1: tasks/ must exist and have at least one .md file.
    tasks_dir = os.path.join(feature_dir, "tasks")
    if not os.path.isdir(tasks_dir):
        return {"in_window": False, "reason": "no_tasks_dir"}

    # Collect task .md files, excluding:
    #   - dotfiles (e.g. .gitkeep)
    #   - README.md (case-insensitive) — the /breakdown-generated task INDEX
    #     that holds a per-task status TABLE; it never carries a **Status**: line
    #     and must not be treated as a task file.  Parity with
    #     _implement/_cmds_resolve.py lines 147 and 179.
    task_files = [
        os.path.join(tasks_dir, f)
        for f in sorted(os.listdir(tasks_dir))
        if f.endswith(".md")
        and not f.startswith(".")
        and f.upper() != "README.MD"
    ]  # type: List[str]

    if not task_files:
        return {"in_window": False, "reason": "no_task_files"}

    # Check whether all tasks are terminal.
    # All must be terminal (Complete/Skipped/Done) — mid-/implement means not in-window.
    # If all tasks are terminal, /implement has completed → in-window (pre-/summarize).
    all_terminal = True
    for tf in task_files:
        terminal = _task_is_terminal(tf)
        if terminal is False:
            all_terminal = False
        # None (unreadable) is treated conservatively as in-progress (not terminal).
        elif terminal is None:
            all_terminal = False

    if not all_terminal:
        # Mid-/implement: tasks not yet fully drained → NOT in-window.
        # A /fix wip-commit landing here would stomp /implement's .devforge/wip.md
        # crash-recovery marker, so the window is strictly post-/implement.
        return {"in_window": False, "reason": "not_all_tasks_complete"}

    # All tasks complete, summary absent, spec not sealed → in-window.
    return {"in_window": True, "reason": "all_tasks_complete"}
