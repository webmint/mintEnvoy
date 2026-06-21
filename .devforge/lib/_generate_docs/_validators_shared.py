"""Cross-tier helper primitives shared by package, concern, and decomposition
validators.

Owns the error-dict shape (`_err`), whitespace normalization
(`_normalize_for_compare`), snippet diff formatting (`_slice_snippet_diff`),
per-CodeBlock filesystem + verbatim-match checks (`_check_codeblock`), and
the two CLI output helpers (`_format_error_line`, `_print_errors`).

No sibling validator modules are imported here (import order: this module
must be importable before the tier-specific modules).

Stdlib only. Targets Python 3.8+.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List


def _err(rule: str, field: str, message: str, **extra: Any) -> Dict[str, Any]:
    """Build a structured error dict with a stable shape."""
    out: Dict[str, Any] = {"rule": rule, "field": field, "message": message}
    out.update(extra)
    return out


def _normalize_for_compare(text: str) -> str:
    """Apply the whitespace normalization rules.

    Rules: CRLF→LF, strip trailing whitespace per line, drop leading
    and trailing fully-blank lines. Implemented here as a deterministic
    pure function so both sides of the comparison go through the same
    code path.
    """
    # Normalize CRLF -> LF (covers '\r\n' AND lone '\r' from old Macs).
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Strip per-line trailing whitespace.
    lines = [ln.rstrip() for ln in text.split("\n")]
    # Trim leading + trailing fully-blank lines.
    start = 0
    end = len(lines)
    while start < end and lines[start] == "":
        start += 1
    while end > start and lines[end - 1] == "":
        end -= 1
    return "\n".join(lines[start:end])


def _slice_snippet_diff(expected: str, actual: str) -> str:
    """Build a small diff fragment for a STALE snippet error.

    Truncated to ~5 lines per side so the error message stays readable
    when a long snippet drifts.
    """
    e_lines = expected.split("\n")[:5]
    a_lines = actual.split("\n")[:5]
    return (
        "expected (from source):\n  "
        + "\n  ".join(e_lines)
        + "\nactual (registered):\n  "
        + "\n  ".join(a_lines)
    )


def _check_codeblock(
    code: Dict[str, Any], field: str, project_root: Path,
) -> List[Dict[str, Any]]:
    """Filesystem + verbatim-match checks for a single CodeBlock dict."""
    cite = code.get("cite") or {}
    cite_file = cite.get("file")
    cite_start = cite.get("start")
    cite_end = cite.get("end")
    if not isinstance(cite_file, str) or cite_file.strip() == "":
        return [_err("cite-file-missing", field,
                     "{0}.cite.file is unset".format(field))]
    if not isinstance(cite_start, int) or not isinstance(cite_end, int):
        return [_err("cite-range-malformed", field,
                     "{0}.cite.start/end must be ints".format(field))]
    src_path = project_root / cite_file
    if not src_path.exists():
        return [_err("cite-file-not-found", field,
                     "{0}.cite.file {1!r} does not exist under project root "
                     "{2}".format(field, cite_file, project_root))]
    try:
        text = src_path.read_text(encoding="utf-8")
    except OSError as err:
        return [_err("cite-file-unreadable", field,
                     "{0}.cite.file {1!r} cannot be read: {2}".format(
                         field, cite_file, err))]
    file_lines = text.split("\n")
    # `split('\n')` produces N+1 items for files ending in '\n'.
    file_line_count = len(file_lines) - 1 if text.endswith("\n") else len(file_lines)
    if cite_end > file_line_count:
        return [_err("cite-range-out-of-bounds", field,
                     "{0}.cite.end ({1}) exceeds file line count ({2}) for "
                     "{3!r}".format(field, cite_end, file_line_count, cite_file))]
    expected_slice = "\n".join(file_lines[cite_start - 1:cite_end])
    expected_norm = _normalize_for_compare(expected_slice)
    actual_norm = _normalize_for_compare(code.get("snippet") or "")
    if expected_norm != actual_norm:
        return [_err("snippet-verbatim", field,
                     "{0}: snippet does not match {1}:{2}-{3}".format(
                         field, cite_file, cite_start, cite_end),
                     diff=_slice_snippet_diff(expected_norm, actual_norm))]
    return []


def _format_error_line(err: Dict[str, Any]) -> str:
    """Render one error dict as a plain-text line for the CLI."""
    parts = [
        "[{0}] {1}: {2}".format(
            err.get("rule", "?"),
            err.get("field", "?"),
            err.get("message", ""),
        ),
    ]
    if "diff" in err:
        parts.append("  " + err["diff"].replace("\n", "\n  "))
    return "\n".join(parts)


def _print_errors(errors: List[Dict[str, Any]]) -> None:
    for err in errors:
        sys.stderr.write(_format_error_line(err) + "\n")
