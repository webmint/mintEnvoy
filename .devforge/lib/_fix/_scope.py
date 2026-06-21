"""_scope.py — map the working list to the narrow file set for verify-touched.

OQ-2 decision: NARROW (finding-targeted) — /fix remediates a finding set, not
the whole assembled-feature diff. The file set fed to
``implement_helper verify-touched --files`` is the union of files actually
cited across all working-list items, NOT the assembled-feature merge-base diff
that _shared/feature_scope.py computes.

Rationale: pulling in the whole assembled diff would re-run verification over
every file the feature touched — that is /verify's job. /fix targets the
exact files the findings name. An empty finding list yields an empty file set
(a STOP signal: nothing to verify against).

Public surface
--------------
  resolve_scope(items) -> dict
      Map a working list (output of read_findings["items"]) to the narrow
      touched-file set that feeds ``implement_helper verify-touched --files``.

      Returns:
        {
          "files":       list[str],   # deduplicated, sorted, non-empty
          "file_count":  int,
          "empty":       bool,        # True when no files were cited in findings
        }

      ``files`` is a JSON-serialisable list of relative path strings, suitable
      for direct use as the ``--files`` argument value.

Stdlib only.  Python 3.8+.  No I/O.
"""

from __future__ import annotations

from typing import Dict, List


def resolve_scope(items):
    # type: (List[Dict]) -> Dict
    """Map the working list → the narrow touched-file set for verify-touched.

    Parameters
    ----------
    items : list[dict]
        RemediationItem list from read_findings (each item has a "files_cited"
        key containing a list of file path strings).

    Returns
    -------
    dict:
      {
        "files":      list[str],  # deduplicated, sorted file paths
        "file_count": int,
        "empty":      bool,       # True when the union is empty
      }
    """
    seen = set()  # type: set
    for item in items:
        for f in item.get("files_cited") or []:
            f = f.strip()
            if f:
                seen.add(f)

    files = sorted(seen)
    return {
        "files": files,
        "file_count": len(files),
        "empty": len(files) == 0,
    }
