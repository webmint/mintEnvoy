"""Heuristic: hedge_defensive — fires when diff additions contain patterns that
indicate defensive over-hedging rather than proper type-safe code.

Severity: low

Emits ONE finding PER MATCH.  A diff with 3 `|| ''` chains produces 3 findings.

Patterns (applied to each added line in the diff):
    1. || '' / || "" / || `` (string-empty fallback)
    2. || 0               (zero fallback)
    3. || []              (array-empty fallback)
    4. || {}              (object-empty fallback)
    5. a = b = c = ...    (triple-assignment chain — bare-token '=' chain >= 3 deep)

Location format: "diff:line+<N>" where N is the 0-indexed position within the
list of added lines.  (Real file:line mapping is Step 4b territory.)
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

# Each entry: (pattern_re, human_label).
# Patterns are applied to each added line; multiple patterns may match the same line.
_PATTERNS: List[Tuple[Any, str]] = [
    # String-empty fallback: || '' or || "" or || ``
    (re.compile(r'\|\|\s*(?:\'\'|""|``)'), "string-empty fallback"),
    # Zero fallback: || 0 (not followed by a digit or '.', to avoid || 0.5, || 000)
    (re.compile(r'\|\|\s*0(?![\d.])'), "zero fallback"),
    # Array-empty fallback: || []
    (re.compile(r'\|\|\s*\[\]'), "array-empty fallback"),
    # Object-empty fallback: || {}
    (re.compile(r'\|\|\s*\{\}'), "object-empty fallback"),
    # Triple-assignment chain: at least 3 bare tokens linked by '='
    # Pattern: word = word = word (optionally followed by more = word)
    # Anchored to bare-token assignment (no ==, !=, <=, >=).
    (re.compile(r'\b\w+\s*=\s*\w+\s*=\s*\w+\s*='), "triple-assignment chain"),
]

# Matches an added line: starts with '+' but not '++' or bare '+\n'.
# [^+\n] rejects both the second '+' of '+++' headers and bare newlines, preventing
# a blank added line (bare '+\n') from causing the class to consume the newline
# and capture content of the following diff line.
_ADDED_LINE_RE = re.compile(r"^\+([^+\n].*)$", re.MULTILINE)


def run(state: Any) -> List[Dict[str, Any]]:
    """Scan diff additions for hedge-defensive patterns.

    Args:
        state: PRReviewState instance.  Only state.diff is read.

    Returns:
        List of findings — one per pattern match.  Empty if no matches.
    """
    diff = state.diff or ""
    if not diff:
        return []

    # Extract added lines (strip the leading '+').
    added_lines = []
    for match in _ADDED_LINE_RE.finditer(diff):
        # match.group(0) starts with '+'; actual line content is everything after it.
        added_lines.append(match.group(0)[1:])

    findings: List[Dict[str, Any]] = []
    for idx, line in enumerate(added_lines):
        for pattern_re, _label in _PATTERNS:
            for m in pattern_re.finditer(line):
                findings.append(
                    {
                        "name": "hedge_defensive",
                        "severity": "low",
                        "location": "diff:line+{n}".format(n=idx),
                        "evidence": m.group(0),
                    }
                )

    return findings
