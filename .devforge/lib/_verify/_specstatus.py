"""_specstatus.py — spec-status flip + AC-checkbox tick for /verify.

Public surface
--------------
  flip_spec_status(feature_dir, ac_results, spec_path=None)
      -> {flipped, blocker, ticked, spec_path}

      (a) Cross-check every task file in specs/[feature]/tasks/*.md
          (excluding README.md) has **Status**: Complete or Skipped.
          If any task is not satisfied → return {flipped: False, blocker: "Task NNN is <status>"}
          and do NOT modify the spec.

      (b) If all tasks satisfied → in spec.md:
          1. Replace **Status**: <old> with **Status**: Complete
          2. For each AC that PASSED (status PASS or PASS (code)):
             tick its ``- [ ] **AC-N**:`` → ``- [x] **AC-N**:``
          Atomic write (mkstemp + os.replace).

      Returns {flipped: True, blocker: None, ticked: [list of ticked AC ids],
               spec_path: <path>}.

      Idempotent: re-running on an already-Complete spec with ticked boxes
      is a no-op-equivalent (returns flipped=True, ticked=[] because nothing
      actually changed).

      IMPORTANT: the orchestrator gates calling this only on APPROVED verdict;
      the verb itself only does the task cross-check + flip — it does NOT
      read the verdict.

Spec status vocabulary (from _specify/_schema.py SPEC_STATUS_ENUM):
  "Draft" | "Approved" | "In Progress" | "Complete"

Task satisfied set (from _implement/_cmds_resolve.py COMPLETE_STATUSES):
  {"Complete", "Skipped"}

Spec AC checkbox format (from tests/lib/fixtures/specify-sample-migration.md):
  - [ ] **AC-N**: <text>   → not checked
  - [x] **AC-N**: <text>   → checked (tick on PASS/PASS (code))

Stdlib only.  Python 3.8+.  Atomic write for spec mutation.
"""

from __future__ import annotations

import os
import re
import tempfile
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Satisfying task statuses (mirrors COMPLETE_STATUSES in _implement/_cmds_resolve.py)
_COMPLETE_STATUSES = frozenset(["Complete", "Skipped"])

# Matches the **Status**: line in any markdown file (task or spec).
#
# IMPORTANT: uses [ \t]* (horizontal whitespace only), NOT \s*, and does NOT
# use re.DOTALL.  This is intentional — the status value MUST appear on the
# same line as the **Status**: marker.  Using \s* would allow the match to
# bleed across blank lines and capture a value from a subsequent line in a
# malformed spec (e.g. "**Status**:\n\nComplete\n" would wrongly match
# "Complete" from the next non-empty line).
_STATUS_PATTERN = re.compile(r"^\*\*Status\*\*:[ \t]*(.+)$", re.MULTILINE)

# AC statuses that earn a checkbox tick
_PASS_STATUSES = frozenset(["PASS", "PASS (code)"])

# Matches an AC checkbox line:
#   - [ ] **AC-N**: <text>   (unchecked)
#   - [x] **AC-N**: <text>   (checked — already ticked)
# Group 1 = check char (space or x/X)
# Group 2 = AC number
# Group 3 = rest of the line
_AC_CHECKBOX_RE = re.compile(r"^(- \[)([xX ])(\] \*\*AC-(\d+)\*\*:.*)", re.MULTILINE)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_task_status(task_path):
    # type: (str) -> Optional[str]
    """Return the stripped **Status**: value from a task file, or None."""
    try:
        with open(task_path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return None
    m = _STATUS_PATTERN.search(text)
    if not m:
        return None
    return m.group(1).strip()


def _task_sort_key(name):
    # type: (str) -> int
    """Sort task files by their leading NNN prefix (numeric sort)."""
    prefix = ""
    for ch in name:
        if ch.isdigit():
            prefix += ch
        else:
            break
    try:
        return int(prefix)
    except ValueError:
        return 2 ** 31


# ---------------------------------------------------------------------------
# flip_spec_status
# ---------------------------------------------------------------------------


def flip_spec_status(feature_dir, ac_results, spec_path=None):
    # type: (str, List[Dict], Optional[str]) -> Dict
    """Cross-check tasks + flip spec to Complete + tick passed AC checkboxes.

    Parameters
    ----------
    feature_dir : str
        Path to the feature directory (e.g. "specs/001-auth").
    ac_results : list[dict]
        merge_ac_results output: per-AC dicts with ``id`` and ``status``.
    spec_path : str or None
        Explicit path to spec.md. When None, defaults to
        <feature_dir>/spec.md.

    Returns
    -------
    dict:
        {
          "flipped":   bool,         # True when the spec was (or already was) Complete
          "blocker":   str or None,  # None on success; message on failure
          "ticked":    list[str],    # AC ids that were ticked in this call
          "spec_path": str,          # path to spec.md
        }
    """
    if spec_path is None:
        spec_path = os.path.join(feature_dir, "spec.md")

    tasks_dir = os.path.join(feature_dir, "tasks")

    # --- (a) Task cross-check -------------------------------------------------
    if os.path.isdir(tasks_dir):
        task_names = sorted(
            [
                n for n in os.listdir(tasks_dir)
                if n.endswith(".md") and n.lower() != "readme.md"
            ],
            key=_task_sort_key,
        )
        for task_name in task_names:
            task_path = os.path.join(tasks_dir, task_name)
            status = _read_task_status(task_path)
            if status is None:
                # Unreadable or missing Status line — treat as incomplete
                return {
                    "flipped": False,
                    "blocker": "Task {0} has no Status line (unreadable or absent)".format(
                        task_name
                    ),
                    "ticked": [],
                    "spec_path": spec_path,
                }
            if status not in _COMPLETE_STATUSES:
                return {
                    "flipped": False,
                    "blocker": "Task {0} is {1!r} (must be Complete or Skipped)".format(
                        task_name, status
                    ),
                    "ticked": [],
                    "spec_path": spec_path,
                }
    # If tasks_dir doesn't exist, there are no tasks to cross-check — proceed.

    # --- (b) Read spec.md -----------------------------------------------------
    try:
        with open(spec_path, encoding="utf-8") as fh:
            spec_text = fh.read()
    except OSError as exc:
        return {
            "flipped": False,
            "blocker": "Cannot read spec.md: {0}".format(exc),
            "ticked": [],
            "spec_path": spec_path,
        }

    # --- (c) Build the set of passing AC ids ----------------------------------
    passing_ids = frozenset(
        ac["id"]
        for ac in (ac_results or [])
        if ac.get("status", "") in _PASS_STATUSES
    )

    # --- (d) Replace **Status**: line -----------------------------------------
    new_text, n_status_subs = _STATUS_PATTERN.subn(
        "**Status**: Complete",
        spec_text,
        count=1,
    )
    if n_status_subs == 0:
        # No **Status**: line found — append one? No — the spec format
        # always has a status line (verified: specify-sample-migration.md:4).
        # Return an error rather than silently corrupt the spec.
        return {
            "flipped": False,
            "blocker": "spec.md has no **Status**: line — cannot flip",
            "ticked": [],
            "spec_path": spec_path,
        }

    # --- (e) Tick passing AC checkboxes ---------------------------------------
    ticked = []  # type: List[str]

    def _tick_ac(m):
        # type: (re.Match) -> str  # type: ignore[type-arg]
        """Replace ``- [ ]`` with ``- [x]`` for passing ACs."""
        prefix = m.group(1)  # "- ["
        check_char = m.group(2)  # " " or "x"/"X"
        rest = m.group(3)        # "] **AC-N**: <text>"
        ac_num = m.group(4)      # "N"
        ac_id = "AC-{0}".format(ac_num)
        if ac_id in passing_ids:
            # Tick if not already ticked (handles both lowercase [x] and uppercase [X])
            if check_char.lower() != "x":
                ticked.append(ac_id)
                return "{0}x{1}".format(prefix, rest)
            # Already ticked — leave as-is
        return m.group(0)  # no change

    new_text = _AC_CHECKBOX_RE.sub(_tick_ac, new_text)

    # --- (f) Atomic write back -----------------------------------------------
    spec_dir = os.path.dirname(spec_path) or "."
    tmp_fd, tmp_path = tempfile.mkstemp(
        prefix=".tmp-spec-",
        suffix=".md",
        dir=spec_dir,
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            fh.write(new_text)
        os.replace(tmp_path, spec_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    return {
        "flipped": True,
        "blocker": None,
        "ticked": ticked,
        "spec_path": spec_path,
    }
