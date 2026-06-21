"""Validation helpers + error utilities for research_helper.

Scalar / enum / verbatim / file_line validators; probe-script path,
runtime, and inlines-from validators; anchor-gate splitting + collision
detection. All raise ValueError on rejection (callers translate to
non-zero exit via _die).
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Error helpers.
# ---------------------------------------------------------------------------


def _die(message: str, code: int = 1) -> int:
    """Write error to stderr and return code (caller propagates as exit)."""
    sys.stderr.write("research_helper: {0}\n".format(message))
    return code


# ---------------------------------------------------------------------------
# Validation helpers.
# ---------------------------------------------------------------------------


def _validate_scalar(value: str, field_name: str) -> str:
    """Strip + reject empty. Returns stripped string."""
    stripped = value.strip()
    if not stripped:
        raise ValueError("{0}: value cannot be empty".format(field_name))
    return stripped


def _validate_enum(value: str, field_name: str, allowed: tuple) -> str:
    """Case-insensitive match → canonical-cased member of allowed.

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


def _validate_string_array_json(value: str, field_name: str) -> List[str]:
    """Parse value as JSON array of strings. Reject non-list input, non-string items, or blank items. Empty array `[]` IS accepted (callers like approach.does_not_cover, approach.cons, data_flow_chain.intermediate_qns rely on this).

    Used for fields where items may contain commas (rule text, hypothesis
    falsifier). Caller passes a JSON-array string like '["a", "b"]'.
    """
    try:
        decoded = json.loads(value)
    except ValueError as err:
        raise ValueError(
            "{0}: JSON-array form is malformed: {1}".format(field_name, err)
        )
    if not isinstance(decoded, list):
        raise ValueError(
            "{0}: must decode to a list, got {1}".format(
                field_name, type(decoded).__name__
            )
        )
    out = []
    for item in decoded:
        if not isinstance(item, str):
            raise ValueError(
                "{0}: items must be strings, got {1}".format(
                    field_name, type(item).__name__
                )
            )
        stripped = item.strip()
        if not stripped:
            raise ValueError("{0}: item cannot be empty".format(field_name))
        out.append(stripped)
    return out


def _validate_verbatim(value: str, field_name: str) -> str:
    """Reject all-whitespace; preserve internal whitespace verbatim.

    Used for multi-line fields (summary, root-cause-hypothesis, code blocks)
    where leading/trailing newlines matter for round-trip.
    """
    if not value.strip():
        raise ValueError("{0}: value cannot be empty".format(field_name))
    return value


def _validate_file_line(value: str, field_name: str) -> str:
    """Validate path:line format OR literal sentinel '(none)'.

    Accepted forms:
      - The literal string "(none)" (sentinel meaning no grounding available).
      - "<non-empty-path>:<positive-integer>" — e.g. "src/foo.ts:42".

    Raises ValueError on any other form.
    """
    stripped = value.strip()
    if stripped == "(none)":
        return stripped
    # Must contain at least one colon separator.
    colon_idx = stripped.rfind(":")
    if colon_idx <= 0:
        raise ValueError(
            "{0}: must be '<path>:<line>' or '(none)', got {1!r}".format(field_name, stripped)
        )
    path_part = stripped[:colon_idx]
    line_part = stripped[colon_idx + 1:]
    if not path_part:
        raise ValueError(
            "{0}: path portion is empty in {1!r}".format(field_name, stripped)
        )
    try:
        line_num = int(line_part)
    except ValueError:
        raise ValueError(
            "{0}: line portion {2!r} is not an integer in {1!r}".format(
                field_name, stripped, line_part
            )
        )
    if line_num <= 0:
        raise ValueError(
            "{0}: line number must be positive, got {1} in {2!r}".format(
                field_name, line_num, stripped
            )
        )
    return stripped


# ---------------------------------------------------------------------------
# Step 5 — probe-script validators.
# ---------------------------------------------------------------------------

_PROBE_SCRIPT_INLINES_TOKEN_RE = re.compile(r"^[^:]+:\d+$")


def _validate_script_within_research_dir(script_path, research_date, topic_slug):
    # type: (str, str, str) -> None
    """Validate script_path exists on disk AND lives under research/<date>-<slug>/.

    Accepts both absolute and relative paths. The check inspects the path's
    directory parts: the immediate parent must be named '<date>-<slug>' and
    that parent's parent must be named 'research'.

    Raises ValueError with a caller-ready message on any violation.
    """
    expected_dir = "{0}-{1}".format(research_date, topic_slug)
    p = Path(script_path)
    # Check structural containment via path parts.
    # p.parent.name == expected_dir  AND  p.parent.parent.name == "research"
    structurally_valid = (
        p.parent.name == expected_dir
        and p.parent.parent.name == "research"
    )
    if not structurally_valid:
        raise ValueError(
            "record-probe-script: script-path must exist and live under "
            "research/{0}-{1}/ dir; got {2}".format(
                research_date, topic_slug, script_path
            )
        )
    if not p.is_file():
        raise ValueError(
            "record-probe-script: --script-path file does not exist: {0}".format(
                script_path
            )
        )


def _validate_runtime_on_path(runtime):
    # type: (str) -> None
    """Validate runtime is resolvable via shutil.which.

    Raises ValueError if not found on PATH.
    """
    if shutil.which(runtime) is None:
        raise ValueError(
            "record-probe-script: --runtime {0} not found on PATH".format(runtime)
        )


def _validate_inlines_from_tokens(json_string):
    # type: (str) -> List[str]
    """Parse --inlines-from as JSON array of path:line tokens.

    Raises ValueError with a caller-ready message if:
    - json_string is not valid JSON
    - decoded value is not a list
    - list is empty
    - any item does not match <non-empty-path>:<digits>
    Returns the list of validated token strings on success.
    """
    try:
        decoded = json.loads(json_string)
    except (ValueError, TypeError) as err:
        raise ValueError(
            "record-probe-script: --inlines-from must be non-empty JSON array of "
            '"path:line" tokens; got {0}'.format(err)
        )
    if not isinstance(decoded, list):
        raise ValueError(
            "record-probe-script: --inlines-from must be non-empty JSON array of "
            '"path:line" tokens; got non-list {0}'.format(type(decoded).__name__)
        )
    if not decoded:
        raise ValueError(
            "record-probe-script: --inlines-from must be non-empty JSON array of "
            '"path:line" tokens; got empty list'
        )
    validated = []
    for item in decoded:
        if not isinstance(item, str):
            raise ValueError(
                "record-probe-script: --inlines-from must be non-empty JSON array of "
                '"path:line" tokens; got non-string item {0!r}'.format(item)
            )
        if not _PROBE_SCRIPT_INLINES_TOKEN_RE.match(item):
            raise ValueError(
                "record-probe-script: --inlines-from must be non-empty JSON array of "
                '"path:line" tokens; got {0!r} (expected <path>:<line-number>)'.format(item)
            )
        validated.append(item)
    return validated


# ---------------------------------------------------------------------------
# Patch 5 — anchor-gate helpers (_split_path_line + _has_anchor_finding).
# ---------------------------------------------------------------------------

# Line-number tolerance window for anchor-gate collision (lenient to absorb
# minor CBM/trace offsets between a finding's recorded line and the helper's
# definition line as returned by search_graph). Single source of truth for
# the numeric tolerance; prose mentions of "±5" in docstrings and error
# messages are documentation and stay as literals.
_ANCHOR_LINE_WINDOW = 5


def _split_path_line(file_line: str) -> Tuple[Optional[str], Optional[int]]:
    """Split "path/to/file.ts:42" into ("path/to/file.ts", 42).

    Returns (None, None) for malformed input (no colon, non-integer line).
    Returns ("(none)", None) for the sentinel so (none) findings never
    accidentally match a real helper file_line (sentinels have no line number
    and therefore no ±5 neighbourhood).
    """
    if not file_line or not file_line.strip():
        return (None, None)
    stripped = file_line.strip()
    if stripped == "(none)":
        return ("(none)", None)
    colon_idx = stripped.rfind(":")
    if colon_idx <= 0:
        return (None, None)
    path_part = stripped[:colon_idx]
    line_part = stripped[colon_idx + 1:]
    if not path_part:
        return (None, None)
    try:
        line_num = int(line_part)
    except ValueError:
        return (None, None)
    return (path_part, line_num)


def _has_anchor_finding(target_file_line: str, findings: list) -> bool:
    """True iff some finding's file_line collides with target_file_line.

    Collision: exact match OR same path with line numbers within ±5
    (lenient to absorb minor CBM/trace offset). Sentinel (none) in
    target_file_line always returns False — (none) is not a real anchor.
    Per Patch 5 fix-path-helper anchor gate.
    """
    target_path, target_line = _split_path_line(target_file_line)
    if target_path is None or target_path == "(none)":
        return False
    for f in findings:
        if not isinstance(f, dict):
            continue
        fl = f.get("file_line") or ""
        if fl == target_file_line:
            return True
        f_path, f_line = _split_path_line(fl)
        if f_path is None or f_path == "(none)":
            continue
        if f_path == target_path and target_line is not None and f_line is not None:
            if abs(f_line - target_line) <= _ANCHOR_LINE_WINDOW:
                return True
    return False
