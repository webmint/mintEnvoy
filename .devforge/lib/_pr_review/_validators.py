"""Validation helpers + error utilities for pr_review_helper.

Only the validators needed at scaffold time are included here.
Additional validators ship with the step that requires them.
"""

from __future__ import annotations

import sys
from typing import Union


# ---------------------------------------------------------------------------
# Error helpers.
# ---------------------------------------------------------------------------


def _die(message: str, code: int = 1) -> int:
    """Write error to stderr and return code (caller propagates as exit)."""
    sys.stderr.write("pr_review_helper: {0}\n".format(message))
    return code


# ---------------------------------------------------------------------------
# Validation helpers.
# ---------------------------------------------------------------------------


def _validate_pr_number(value: Union[str, int]) -> int:
    """Parse + validate a PR number.

    Accepts a str or int. Returns the PR number as a positive int.

    Raises:
        TypeError: if value is None.
        ValueError: if value is not a positive integer (0 and negative
            values are rejected; non-numeric strings are rejected).
    """
    if value is None:
        raise TypeError("pr_number must not be None")
    try:
        as_int = int(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(
            "pr_number must be a positive integer, got {0!r}".format(value)
        ) from exc
    if as_int <= 0:
        raise ValueError(
            "pr_number must be a positive integer, got {0!r}".format(value)
        )
    return as_int
