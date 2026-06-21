"""_cmds_resolve -- resolve-next-task verb for implement_helper.

Scans specs/*/ directories for features with breakdown-handoff.json, determines
the incomplete-task set by reading each tasks/<NNN>.md **Status**: line, picks
the lowest-numbered feature with at least one incomplete task, and within it
picks the lowest-numbered task whose depends_on are all Complete.

Emits JSON to stdout.  Exit codes:
  0 — task found or all-complete
  2 — blocked (a feature has incomplete tasks but none are dependency-ready)

Status tokens recognised (from storage-rules.md §Task File Format):
  Complete — finished, counts as satisfied for depends_on resolution
  Skipped  — skipped at the gate, counts as satisfied (treated like Complete)
             for dependency purposes so downstream tasks are not permanently
             blocked by a skipped predecessor
  Pending, In Progress, (absent) — incomplete, eligible for execution

COMPLETE_STATUSES: the set of per-task statuses that satisfy a depends_on
reference.  A task whose status is in this set is counted as "done" for
scheduling purposes.  Anything else (including missing Status line) is
incomplete.

Stdlib only. Python 3.8+.
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# These two statuses count as "satisfied" for dependency resolution.
# The plan (07-EXECUTE-TASK-REDESIGN-PLAN.md §Phase 2) defines:
#   incomplete = Status NOT in {Complete, Skipped}
COMPLETE_STATUSES = frozenset(["Complete", "Skipped"])

# The **Status**: markdown frontmatter pattern (mirrors breakdown_helper.py).
#
# IMPORTANT: uses [ \t]* (horizontal whitespace only), NOT \s*.  The status
# value MUST appear on the same line as the **Status**: marker.  Using \s*
# would allow the match to bleed across a blank line and capture a value from
# the next non-empty line in a malformed task file (e.g. "**Status**:\n\n
# Complete\n" would wrongly yield "Complete").
_STATUS_PATTERN = re.compile(r"^\*\*Status\*\*:[ \t]*(.+)$", re.MULTILINE)

# Exit codes (mirrors breakdown_helper.py convention).
EXIT_OK = 0
EXIT_FINDINGS = 2


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _read_task_status(task_md_path):
    # type: (Path) -> Optional[str]
    """Return the stripped value of the **Status**: line, or None if absent.

    If the file is unreadable, returns None (treated as incomplete).
    """
    try:
        text = task_md_path.read_text(encoding="utf-8")
    except (OSError, IOError):
        return None
    m = _STATUS_PATTERN.search(text)
    if not m:
        return None
    return m.group(1).strip()


def _is_complete(status):
    # type: (Optional[str]) -> bool
    """Return True when status satisfies a depends_on reference."""
    return status in COMPLETE_STATUSES


def _task_number_sort_key(number):
    # type: (str) -> int
    """Convert a zero-padded task number string to int for sorting.

    '001' -> 1, '010' -> 10.  Non-numeric strings sort to maxint so they
    appear last rather than crashing.
    """
    try:
        return int(number)
    except (ValueError, TypeError):
        return 2 ** 31


def _feature_sort_key(feature_dir):
    # type: (Path) -> int
    """Sort key for feature directory names by their NNN prefix.

    'specs/001-slug' -> 1, 'specs/012-slug' -> 12.
    Directories without a leading digit prefix sort last.
    """
    name = feature_dir.name
    m = re.match(r"^(\d+)", name)
    if not m:
        return 2 ** 31
    try:
        return int(m.group(1))
    except ValueError:
        return 2 ** 31


def _glob_feature_dirs(root):
    # type: (Path) -> List[Path]
    """Return sorted list of specs/* dirs that contain breakdown-handoff.json.

    Sorted by NNN prefix (lowest-numbered feature first).
    """
    specs_dir = root / "specs"
    if not specs_dir.is_dir():
        return []
    candidates = []
    for entry in specs_dir.iterdir():
        if not entry.is_dir():
            continue
        if (entry / "breakdown-handoff.json").is_file():
            candidates.append(entry)
    candidates.sort(key=_feature_sort_key)
    return candidates


def _read_task_statuses(tasks_dir, task_numbers):
    # type: (Path, List[str]) -> Dict[str, Optional[str]]
    """Read status for each task number from its NNN-*.md file.

    For each number, globs for a file whose name starts with that number
    (e.g. '001-define-types.md').  Returns a dict mapping number -> status
    (or None when the file is absent or has no Status line).
    """
    statuses = {}  # type: Dict[str, Optional[str]]
    for number in task_numbers:
        # The task file name starts with the number prefix.
        matched_path = None  # type: Optional[Path]
        if tasks_dir.is_dir():
            for f in tasks_dir.iterdir():
                if f.suffix == ".md" and f.name.upper() != "README.MD":
                    # Match files whose NNN prefix equals the task number.
                    fname_prefix = re.match(r"^(\d+)", f.name)
                    if fname_prefix:
                        padded = fname_prefix.group(1).zfill(3)
                        if padded == number:
                            matched_path = f
                            break
        if matched_path is not None:
            statuses[number] = _read_task_status(matched_path)
        else:
            # File absent: treat as incomplete (Pending equivalent).
            statuses[number] = None
    return statuses


def _locate_task_file(tasks_dir, number):
    # type: (Path, str) -> Optional[Path]
    """Return the absolute Path of the NNN-*.md file for ``number``, or None.

    Scans tasks_dir for a .md file (excluding README.md) whose leading digit
    prefix, zero-padded to 3 digits, equals ``number``.  Returns None when
    tasks_dir is absent or no matching file is found.

    This is intentionally a single-task lookup separate from
    _read_task_statuses so the bulk scan stays a dict-return function and
    we avoid returning a fat (status, path) tuple from the hot path.  The
    caller only needs the path for the ONE selected task, not for all tasks.
    """
    if not tasks_dir.is_dir():
        return None
    for f in tasks_dir.iterdir():
        if f.suffix == ".md" and f.name.upper() != "README.MD":
            fname_prefix = re.match(r"^(\d+)", f.name)
            if fname_prefix:
                padded = fname_prefix.group(1).zfill(3)
                if padded == number:
                    return f.resolve()
    return None


def _count_progress(statuses):
    # type: (Dict[str, Optional[str]]) -> Tuple[int, int]
    """Return (completed_count, total_count) for the given statuses dict.

    A task counts as completed when its status is in COMPLETE_STATUSES
    (i.e. Complete or Skipped), matching the dependency-satisfaction rule.
    total_count is simply len(statuses).
    """
    completed = sum(1 for s in statuses.values() if s in COMPLETE_STATUSES)
    return completed, len(statuses)


# ---------------------------------------------------------------------------
# Core resolution logic (pure -- accepts a loaded handoff + statuses dict)
# ---------------------------------------------------------------------------


def _resolve_task(tasks, statuses):
    # type: (list, Dict[str, Optional[str]]) -> Tuple[Optional[object], str, List[str]]
    """Pick the lowest-numbered dependency-ready incomplete task.

    Parameters
    ----------
    tasks : list of TaskRow
        All tasks from the breakdown handoff.
    statuses : dict mapping number -> status string or None
        Current status of every task in this feature.

    Returns
    -------
    (selected_task_or_None, reason, blocking_task_numbers)
        selected_task is None when all tasks are complete or blocked.
        reason is "ready", "all-complete", or "blocked".
        blocking_task_numbers lists the number(s) blocking selection.
    """
    # Determine incomplete tasks.
    incomplete = [
        t for t in tasks
        if not _is_complete(statuses.get(t.number))
    ]

    if not incomplete:
        return None, "all-complete", []

    # Among incomplete tasks, find those whose depends_on are all satisfied.
    ready = []
    for task in incomplete:
        deps_satisfied = all(
            _is_complete(statuses.get(dep))
            for dep in task.depends_on
        )
        if deps_satisfied:
            ready.append(task)

    if not ready:
        # All incomplete tasks have unsatisfied dependencies.
        blocking = []
        for task in incomplete:
            for dep in task.depends_on:
                if not _is_complete(statuses.get(dep)):
                    if dep not in blocking:
                        blocking.append(dep)
        return None, "blocked", blocking

    # Pick the lowest-numbered ready task.
    ready.sort(key=lambda t: _task_number_sort_key(t.number))
    return ready[0], "ready", []


# ---------------------------------------------------------------------------
# Public command handler
# ---------------------------------------------------------------------------


def cmd_resolve_next_task(args):
    # type: (object) -> int
    """Scan specs/*/ for the next runnable task and emit JSON to stdout.

    Exits:
      0 with {"state": "task", ...} when a runnable task is found.
      0 with {"state": "all-complete"} when all features are done.
      2 with {"state": "blocked", ...} when a feature has incomplete tasks
        but none are dependency-ready.

    args.root : str
        Project root directory (default: cwd).
    """
    root_str = getattr(args, "root", None) or "."
    root = Path(root_str).resolve()

    # Import handoff reader (lib path arranged by launcher).
    try:
        from _implement._handoff_reader import read_breakdown_handoff  # type: ignore[import]
    except ImportError as exc:
        sys.stderr.write(
            "implement_helper: cannot import handoff reader: {0}\n".format(exc)
        )
        return EXIT_FINDINGS

    feature_dirs = _glob_feature_dirs(root)

    if not feature_dirs:
        # No features with a breakdown-handoff.json at all.
        _emit_json({"state": "all-complete"})
        return EXIT_OK

    for feature_dir in feature_dirs:
        # Load the breakdown handoff for this feature.
        try:
            handoff = read_breakdown_handoff(feature_dir)
        except ValueError as exc:
            sys.stderr.write(
                "implement_helper: skipping {0}: {1}\n".format(feature_dir.name, exc)
            )
            continue

        tasks_dir = feature_dir / "tasks"
        all_numbers = [t.number for t in handoff.tasks]
        statuses = _read_task_statuses(tasks_dir, all_numbers)

        selected, reason, blocking = _resolve_task(handoff.tasks, statuses)

        if reason == "all-complete":
            # This feature is fully done; continue to the next feature.
            continue

        if reason == "blocked":
            # This feature has work to do but no dependency-ready task.
            _emit_json({
                "state": "blocked",
                "feature_dir": str(feature_dir),
                "reason": (
                    "feature {0} has incomplete tasks but none are "
                    "dependency-ready".format(feature_dir.name)
                ),
                "blocking_tasks": blocking,
            })
            return EXIT_FINDINGS

        # reason == "ready": emit the selected task.
        task_file_path = _locate_task_file(tasks_dir, selected.number)
        index_file_path = tasks_dir / "README.md"
        index_file_resolved = index_file_path.resolve() if index_file_path.exists() else None
        completed_count, total_count = _count_progress(statuses)
        _emit_json({
            "state": "task",
            "feature_dir": str(feature_dir),
            "number": selected.number,
            "title": selected.title,
            "agent": selected.agent,
            "depends_on": selected.depends_on,
            "touched_files": selected.touched_files,
            "expects": selected.expects,
            "produces": selected.produces,
            "ac_addressed": selected.ac_addressed,
            "doc_refs": selected.doc_refs,
            "review_checkpoint": selected.review_checkpoint,
            "task_file": str(task_file_path) if task_file_path is not None else None,
            "index_file": str(index_file_resolved) if index_file_resolved is not None else None,
            "completed_count": completed_count,
            "total_count": total_count,
        })
        return EXIT_OK

    # All features exhausted (all complete).
    _emit_json({"state": "all-complete"})
    return EXIT_OK


def _emit_json(data):
    # type: (dict) -> None
    """Write data as compact JSON to stdout with a trailing newline."""
    sys.stdout.write(json.dumps(data, indent=2) + "\n")


# ---------------------------------------------------------------------------
# Argument adder for CLI registration
# ---------------------------------------------------------------------------


def add_args_resolve_next_task(parser):
    # type: (object) -> None
    """Add --root argument to the resolve-next-task subparser."""
    parser.add_argument(
        "--root",
        default=".",
        metavar="DIR",
        help=(
            "Project root directory to scan for specs/*/breakdown-handoff.json "
            "(default: current working directory)."
        ),
    )
