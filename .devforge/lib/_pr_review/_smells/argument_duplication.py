"""Heuristic: argument_duplication — fires when a function call in diff additions
has duplicate identifier arguments.

Severity: medium

Logic:
    1. Extract added lines from state.diff.
    2. For each added line, find all function-call substrings via _FUNCTION_CALL_RE
       (unanchored — matches calls embedded in surrounding code).  Passes each full
       call-shape string (e.g. "fn(a, b, b)") to _detect_arg_duplication from the
       canonical _shared module, which applies its own anchored CALL_SHAPE_RE
       internally to parse the arg list.
    3. If _detect_arg_duplication returns (ident, count), emit a finding.
    4. Cap at _MAX_CALL_SHAPES per PR.

Finding schema:
    {
        "name": "argument_duplication",
        "severity": "medium",
        "location": "diff:line+<N>",   # 0-based index in added-lines list
        "evidence": "<fn_name>(<args>) — identifier <ident> appears <count>x"
    }

Constants:
    _MAX_CALL_SHAPES = 100

Git operations: NONE.  This heuristic reads only state.diff.  No subprocess.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from _shared.literal_call_shape import _detect_arg_duplication

_MAX_CALL_SHAPES = 100

# Matches an added content line (not '+++' header or bare '+\n').
_ADDED_LINE_RE = re.compile(r"^\+([^+\n].*)$", re.MULTILINE)

# Extracts function-call substrings from diff lines (unanchored).
# Matches an identifier (with optional dotted member access) followed by a
# parenthesized arg list with no nested parens.  The full match group(0) is a
# complete call shape (e.g. "fn(a, b, b)") suitable for _detect_arg_duplication.
# Requires a word boundary before the identifier to avoid matching numeric-prefixed
# tokens like "5(a, a)".
_FUNCTION_CALL_RE = re.compile(r"\b[A-Za-z_][\w.]*\([^)]*\)")


def run(state: Any) -> List[Dict[str, Any]]:
    """Scan diff additions for function calls with duplicate identifier arguments.

    Args:
        state: PRReviewState instance.  Only state.diff is read.

    Returns:
        List of findings — one per call shape with a duplicate identifier.
        Empty if no smells detected.
    """
    diff = state.diff or ""
    if not diff:
        return []

    # Extract added lines (strip the leading '+').
    added_lines = [m.group(1) for m in _ADDED_LINE_RE.finditer(diff)]

    findings: List[Dict[str, Any]] = []
    shapes_seen = 0

    for idx, line in enumerate(added_lines):
        for match in _FUNCTION_CALL_RE.finditer(line):
            if shapes_seen >= _MAX_CALL_SHAPES:
                break
            shapes_seen += 1

            call_shape = match.group(0)
            dup = _detect_arg_duplication(call_shape)
            if dup is None:
                continue

            ident, count = dup
            findings.append({
                "name": "argument_duplication",
                "severity": "medium",
                "location": "diff:line+{n}".format(n=idx),
                "evidence": (
                    "{call} — identifier {ident} appears {count}x".format(
                        call=call_shape,
                        ident=ident,
                        count=count,
                    )
                ),
            })

        if shapes_seen >= _MAX_CALL_SHAPES:
            break

    return findings
