"""Heuristic: verbose_commit_msg — fires when a commit subject line is overly
verbose, either by matching known verbose-phrasing patterns or by exceeding
the word-count threshold.

Severity: nit

Data source: state.commit_subjects (list of commit subject strings populated
by intake from `gh pr view --json commits`).

Patterns:
    r"^Refactor .+ to improve .+ and .+"
    r"^Update .+ to handle .+"
    r"^Improve .+ for .+"

Word-count threshold: 12 words.

A commit subject that matches ANY pattern OR exceeds the word threshold
produces one finding.  Subjects that match both a pattern AND the word
threshold produce only one finding (first match wins).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

_VERBOSE_PATTERNS = [
    re.compile(r"^Refactor .+ to improve .+ and .+", re.IGNORECASE),
    re.compile(r"^Update .+ to handle .+", re.IGNORECASE),
    re.compile(r"^Improve .+ for .+", re.IGNORECASE),
]

_LONG_SUBJECT_WORD_THRESHOLD = 12


def run(state: Any) -> List[Dict[str, Any]]:
    """Check commit subject lines for verbose phrasing or excessive length.

    Args:
        state: PRReviewState instance.  Only state.commit_subjects is read.

    Returns:
        List of findings — one per verbose commit subject.  Empty if none found.
    """
    subjects = state.commit_subjects or []
    findings: List[Dict[str, Any]] = []

    for idx, subject in enumerate(subjects):
        if not subject:
            continue

        # Check pattern match first.
        matched = False
        for pattern in _VERBOSE_PATTERNS:
            if pattern.search(subject):
                findings.append(
                    {
                        "name": "verbose_commit_msg",
                        "severity": "nit",
                        "location": "commit:{idx}".format(idx=idx),
                        "evidence": subject,
                    }
                )
                matched = True
                break

        if matched:
            continue

        # Check word count.
        word_count = len(subject.split())
        if word_count > _LONG_SUBJECT_WORD_THRESHOLD:
            findings.append(
                {
                    "name": "verbose_commit_msg",
                    "severity": "nit",
                    "location": "commit:{idx}".format(idx=idx),
                    "evidence": subject,
                }
            )

    return findings
