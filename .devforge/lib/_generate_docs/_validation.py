"""Validates user-supplied strings, line ranges, and enum membership at set-time.

Every setter that accepts CLI input runs values through this module
before mutating state. This ensures invalid input is rejected at the
boundary (anti-pattern #2 — type validation must NOT be deferred to
compose-time) and that downstream code (state writer, renderer) only
ever sees pre-validated values.

Single-line fields reject every control character < 0x20 (incl. `\\n`,
`\\r`, `\\t`) plus DEL (0x7F) so the JSON emitter never has to escape
unexpected bytes (anti-pattern #1). Multi-line fields permit `\\n`,
`\\r`, `\\t` but still reject other control bytes.

Stdlib-only. Targets Python 3.8+.
"""

from typing import Any, Optional, Tuple


def _has_disallowed_controls(value: str, allow_newlines: bool) -> bool:
    """Return True if `value` contains any disallowed control character.

    For single-line fields (`allow_newlines=False`) every char with
    `ord(c) < 0x20` and DEL (0x7F) is rejected.
    For multi-line fields, `\\n` (0x0A), `\\r` (0x0D), and `\\t` (0x09)
    are permitted; everything else < 0x20 plus DEL is rejected.
    """
    for ch in value:
        code = ord(ch)
        if code == 0x7F:
            return True
        if code >= 0x20:
            continue
        if allow_newlines and code in (0x09, 0x0A, 0x0D):
            continue
        return True
    return False


def _validate_string(value: Any, field_label: str, multiline: bool = False) -> None:
    """Reject empty / control-char strings at set-time. Raises ValueError.

    `field_label` is the human-readable name surfaced in error messages
    (e.g. `Export.name`, `set-package-overview --text`).
    """
    if not isinstance(value, str):
        raise ValueError(
            "{0}: expected string, got {1}".format(
                field_label, type(value).__name__
            )
        )
    if value.strip() == "":
        raise ValueError("{0}: value must be non-empty".format(field_label))
    if _has_disallowed_controls(value, allow_newlines=multiline):
        raise ValueError(
            "{0}: control characters are not permitted".format(field_label)
        )


def _validate_optional_string(value: Any, field_label: str) -> Optional[str]:
    """Validate an optional single-line string. Empty string -> None.

    Returns the cleaned value (or None) on success. Raises ValueError on
    bad input.
    """
    if value is None or value == "":
        return None
    _validate_string(value, field_label, multiline=False)
    return value


def _validate_in_enum(value: str, allowed: Tuple[str, ...], field_label: str) -> None:
    """Reject `value` if not a member of `allowed` (a tuple of strings)."""
    if value not in allowed:
        raise ValueError(
            "{0}: must be one of {1}, got {2!r}".format(
                field_label, list(allowed), value
            )
        )


def _validate_line_range(start: int, end: int, field_label: str) -> None:
    """Reject malformed `(start, end)` cite ranges.

    `bool` is explicitly rejected (it's an `int` subclass in Python and
    would otherwise sneak past `isinstance(..., int)` checks).
    """
    if not isinstance(start, int) or isinstance(start, bool):
        raise ValueError("{0}.start: must be an int".format(field_label))
    if not isinstance(end, int) or isinstance(end, bool):
        raise ValueError("{0}.end: must be an int".format(field_label))
    if start < 1:
        raise ValueError(
            "{0}.start: must be >= 1, got {1}".format(field_label, start)
        )
    if end < start:
        raise ValueError(
            "{0}.end ({1}) must be >= {0}.start ({2})".format(
                field_label, end, start
            )
        )
