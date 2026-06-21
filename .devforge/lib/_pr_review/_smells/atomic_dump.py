"""Heuristic: atomic_dump — fires when a diff is oversized (too many additions
or too many new files added in a single PR).

Severity: medium

Thresholds:
    additions  > 300 lines    (lines starting with '+' but not '+++')
    new_files  > 4 new files  (diff blocks with 'new file mode' after the header)

Either threshold tripping produces a single finding.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

_DEFAULT_ADDITIONS_THRESHOLD = 300
_DEFAULT_NEW_FILES_THRESHOLD = 4

# Matches an added line: starts with '+' but not '+++' (which is the file header).
_ADDED_LINE_RE = re.compile(r"^\+[^+]", re.MULTILINE)

# Matches the `new file mode` line that follows a `diff --git` block header
# when a new file is being added.
_NEW_FILE_RE = re.compile(r"^new file mode", re.MULTILINE)


def _count_added_lines(diff: str) -> int:
    """Count the number of added lines in a unified diff.

    An added line starts with '+' but not '++' (which is the '+++ b/...' header).
    Lines starting with '++' are excluded to avoid counting the file header.

    Args:
        diff: Raw unified diff string.

    Returns:
        Count of added content lines.
    """
    return len(_ADDED_LINE_RE.findall(diff))


def _count_new_files(diff: str) -> int:
    """Count the number of new files introduced in a unified diff.

    A new file is indicated by a `new file mode NNNN` line that appears
    immediately after the `diff --git a/... b/...` header.

    Args:
        diff: Raw unified diff string.

    Returns:
        Count of new-file blocks.
    """
    return len(_NEW_FILE_RE.findall(diff))


def run(state: Any) -> List[Dict[str, Any]]:
    """Check whether the PR diff exceeds size thresholds for atomic commits.

    Args:
        state: PRReviewState instance.  Only state.diff is read.

    Returns:
        A list with one finding if either threshold is exceeded; otherwise empty.
    """
    diff = state.diff or ""
    if not diff:
        return []

    additions = _count_added_lines(diff)
    new_files = _count_new_files(diff)

    if (
        additions > _DEFAULT_ADDITIONS_THRESHOLD
        or new_files > _DEFAULT_NEW_FILES_THRESHOLD
    ):
        return [
            {
                "name": "atomic_dump",
                "severity": "medium",
                "location": "*",
                "evidence": (
                    "diff added {additions} lines across {new_files} new files"
                    " (threshold {add_thresh}/{file_thresh})".format(
                        additions=additions,
                        new_files=new_files,
                        add_thresh=_DEFAULT_ADDITIONS_THRESHOLD,
                        file_thresh=_DEFAULT_NEW_FILES_THRESHOLD,
                    )
                ),
            }
        ]
    return []
