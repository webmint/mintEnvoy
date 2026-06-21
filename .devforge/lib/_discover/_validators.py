"""Validation + error helpers for discover_helper."""

from __future__ import annotations

import sys
from typing import Tuple


def _die(message: str, code: int = 1) -> int:
    """Write error to stderr and return code (caller propagates as exit)."""
    sys.stderr.write("discover_helper: {0}\n".format(message))
    return code


def _validate_scalar(value: str, field_name: str) -> str:
    """Strip + reject empty. Returns stripped string."""
    stripped = value.strip()
    if not stripped:
        raise ValueError("{0}: value cannot be empty".format(field_name))
    return stripped


def _validate_enum(value: str, field_name: str, allowed: Tuple[str, ...]) -> str:
    """Case-insensitive match to canonical-cased member of allowed.

    Raises ValueError if empty or no match (enumerates allowed in message).
    """
    stripped = _validate_scalar(value, field_name)
    if stripped in allowed:
        return stripped
    lower_to_canonical = {member.lower(): member for member in allowed}
    if stripped.lower() in lower_to_canonical:
        return lower_to_canonical[stripped.lower()]
    raise ValueError(
        "{0}: invalid value {1!r}; allowed: {2}".format(
            field_name, stripped, list(allowed)
        )
    )
