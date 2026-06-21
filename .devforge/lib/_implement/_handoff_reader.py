"""_handoff_reader -- read and validate breakdown-handoff.json for /implement.

Public API:

  read_breakdown_handoff(feature_dir) -> Breakdown
      Locate specs/<feature>/breakdown-handoff.json, parse the JSON, and
      construct a validated Breakdown instance via the imported
      _breakdown.handoff_schema dataclasses.

      Raises ValueError on:
        - File not found (breakdown-handoff.json absent in feature_dir).
        - Malformed JSON (JSONDecodeError wrapped in ValueError).
        - Wrong handoff_kind (not "breakdown").
        - Schema validation failure (Breakdown.__post_init__ rejects the data).

  task_row(handoff, number) -> TaskRow
      Return the TaskRow whose number matches the given string.
      Raises ValueError if no task with that number exists.

Dependency note:

  Both functions import from _breakdown.handoff_schema (the sibling package).
  The caller is responsible for ensuring src/devforge/lib is on sys.path before
  importing this module -- the launcher (implement_helper.py) arranges this by
  inserting the lib directory at import time.

  Import style mirrors how breakdown_helper.py imports from _plan.handoff_schema:
    from _breakdown.handoff_schema import Breakdown, TaskRow, HANDOFF_KIND, SCHEMA_VERSION

Stdlib only. No third-party dependencies. Python 3.8+.
"""

import json
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Lazy import helper: _breakdown.handoff_schema
# ---------------------------------------------------------------------------
# We do NOT import at module top level because this file is used by both
# the subprocess CLI (where lib is on sys.path via the launcher) and by
# unit tests (which insert the lib dir before importing). A top-level import
# would fail when the module is imported before the path is set up.
#
# The _get_schema() function performs the import once and caches the results.

_schema_cache = None  # type: Optional[object]


def _get_schema():
    """Return a namespace object with Breakdown, TaskRow, HANDOFF_KIND.

    Imports from _breakdown.handoff_schema on first call and caches.
    Raises ImportError if _breakdown is not importable (lib not on sys.path).
    """
    global _schema_cache
    if _schema_cache is not None:
        return _schema_cache

    from _breakdown.handoff_schema import (  # type: ignore[import]
        Breakdown,
        Provenance,
        TaskRow,
        HANDOFF_KIND,
        SCHEMA_VERSION,
    )

    class _Schema:
        pass

    s = _Schema()
    s.Breakdown = Breakdown  # type: ignore[attr-defined]
    s.Provenance = Provenance  # type: ignore[attr-defined]
    s.TaskRow = TaskRow  # type: ignore[attr-defined]
    s.HANDOFF_KIND = HANDOFF_KIND  # type: ignore[attr-defined]
    s.SCHEMA_VERSION = SCHEMA_VERSION  # type: ignore[attr-defined]
    _schema_cache = s
    return s


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def read_breakdown_handoff(feature_dir):
    # type: (object) -> object
    """Parse and validate breakdown-handoff.json from feature_dir.

    Parameters
    ----------
    feature_dir : str or Path
        Path to the feature directory (e.g. specs/001-widget-catalog/).
        The file breakdown-handoff.json must be a direct child of this dir.

    Returns
    -------
    Breakdown
        A validated Breakdown dataclass instance.

    Raises
    ------
    ValueError
        - breakdown-handoff.json not found in feature_dir.
        - JSON parse error.
        - handoff_kind is not "breakdown".
        - Schema validation failure from Breakdown.__post_init__.
    """
    schema = _get_schema()

    feature_path = Path(feature_dir)
    handoff_file = feature_path / "breakdown-handoff.json"

    if not handoff_file.exists():
        raise ValueError(
            "breakdown-handoff.json not found in {0}; "
            "run 'breakdown_helper finalize-handoff' first".format(feature_dir)
        )

    try:
        raw_text = handoff_file.read_text(encoding="utf-8")
    except (OSError, IOError) as exc:
        raise ValueError(
            "cannot read breakdown-handoff.json at {0}: {1}".format(handoff_file, exc)
        )

    try:
        d = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "breakdown-handoff.json at {0} is not valid JSON: {1}".format(
                handoff_file, exc
            )
        )

    if not isinstance(d, dict):
        raise ValueError(
            "breakdown-handoff.json at {0}: root must be a JSON object, "
            "got {1}".format(handoff_file, type(d).__name__)
        )

    # Validate handoff_kind before attempting schema construction, so the
    # error message names the wrong kind explicitly rather than failing deep
    # inside __post_init__.
    if d.get("handoff_kind") != schema.HANDOFF_KIND:
        raise ValueError(
            "breakdown-handoff.json at {0}: wrong handoff_kind: "
            "expected {1!r}, got {2!r}".format(
                handoff_file, schema.HANDOFF_KIND, d.get("handoff_kind")
            )
        )

    # Construct Provenance from the nested dict.
    prov_d = d.get("provenance") or {}
    if not isinstance(prov_d, dict):
        raise ValueError(
            "breakdown-handoff.json at {0}: 'provenance' must be a JSON object".format(
                handoff_file
            )
        )
    try:
        provenance = schema.Provenance(
            upstream_handoff_path=prov_d.get("upstream_handoff_path"),
            upstream_handoff_kind=prov_d.get("upstream_handoff_kind"),
            plan_path=prov_d.get("plan_path"),
            spec_path=prov_d.get("spec_path"),
        )
    except ValueError as exc:
        raise ValueError(
            "breakdown-handoff.json at {0}: provenance validation failed: {1}".format(
                handoff_file, exc
            )
        )

    # Construct TaskRow list from the tasks array.
    tasks_raw = d.get("tasks")
    if not isinstance(tasks_raw, list):
        raise ValueError(
            "breakdown-handoff.json at {0}: 'tasks' must be a JSON array".format(
                handoff_file
            )
        )
    tasks = []
    for i, t in enumerate(tasks_raw):
        if not isinstance(t, dict):
            raise ValueError(
                "breakdown-handoff.json at {0}: tasks[{1}] must be a JSON object".format(
                    handoff_file, i
                )
            )
        try:
            row = schema.TaskRow(
                number=t.get("number", ""),
                title=t.get("title", ""),
                agent=t.get("agent", ""),
                depends_on=t.get("depends_on") or [],
                blocks=t.get("blocks") or [],
                touched_files=t.get("touched_files") or [],
                expects=t.get("expects") or [],
                produces=t.get("produces") or [],
                ac_addressed=t.get("ac_addressed") or [],
                doc_refs=t.get("doc_refs") or [],
                review_checkpoint=bool(t.get("review_checkpoint", False)),
            )
        except ValueError as exc:
            raise ValueError(
                "breakdown-handoff.json at {0}: tasks[{1}] validation failed: "
                "{2}".format(handoff_file, i, exc)
            )
        tasks.append(row)

    # Construct the top-level Breakdown record.
    try:
        breakdown = schema.Breakdown(
            schema_version=d.get("schema_version", ""),
            handoff_kind=d.get("handoff_kind", ""),
            tasks_dir=d.get("tasks_dir", ""),
            breakdown_completed_at=d.get("breakdown_completed_at", ""),
            provenance=provenance,
            tasks=tasks,
            additions=d.get("additions") or [],
            dependency_graph=d.get("dependency_graph") or "",
        )
    except ValueError as exc:
        raise ValueError(
            "breakdown-handoff.json at {0}: schema validation failed: {1}".format(
                handoff_file, exc
            )
        )

    return breakdown


def task_row(handoff, number):
    # type: (object, str) -> object
    """Return the TaskRow from handoff whose number matches the given string.

    Parameters
    ----------
    handoff : Breakdown
        A Breakdown instance (as returned by read_breakdown_handoff).
    number : str
        The task number to look up (e.g. "001", "002").

    Returns
    -------
    TaskRow
        The matching TaskRow.

    Raises
    ------
    ValueError
        No task with the given number exists in the handoff.
    """
    for row in handoff.tasks:
        if row.number == number:
            return row
    raise ValueError(
        "no task with number {0!r} found in handoff "
        "(tasks_dir={1!r}); available: {2!r}".format(
            number,
            handoff.tasks_dir,
            [r.number for r in handoff.tasks],
        )
    )
