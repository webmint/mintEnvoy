"""Heuristic: empty_pr_body — fires when the PR body is absent or too short.

Severity: low

Threshold: body (stripped) has length <= 30 characters.
The threshold catches both empty bodies and trivially-minimal ones
("Fix bug", "WIP") that provide no reviewer context.
"""

from __future__ import annotations

from typing import Any, Dict, List

_THRESHOLD = 30


def run(state: Any) -> List[Dict[str, Any]]:
    """Check whether the PR body is empty or below the minimum length threshold.

    Args:
        state: PRReviewState instance.  Only state.pr_body is read.

    Returns:
        A list with one finding if body length <= _THRESHOLD; otherwise empty.
    """
    body = (state.pr_body or "").strip()
    if len(body) <= _THRESHOLD:
        return [
            {
                "name": "empty_pr_body",
                "severity": "low",
                "location": "*",
                "evidence": "PR body length = {length} chars (threshold ≤30)".format(
                    length=len(body)
                ),
            }
        ]
    return []
