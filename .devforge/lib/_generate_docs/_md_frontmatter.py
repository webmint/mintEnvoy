"""Stdlib-only YAML-subset parser + writer for per-source-file .md front-matter.

Owns the schema shape for the per-file .md documents introduced in Step B.3
of VALIDATOR-LOOP-B-PLAN.md. The LLM never writes raw front-matter; it calls
`write-file-doc` which delegates to `render_frontmatter` here.

Parser rules (locked in B.3 spec):
  - Document MUST start with `---` on line 1.
  - Read key: value lines until the next `---` line.
  - Closing fence must appear within 100 lines of opening fence.
  - Duplicate keys are rejected.
  - Lines that cannot be parsed (no `:` separator outside quotes) are rejected.
  - Leading `"` on value → quoted string (strip outer quotes, unescape `\"` and `\\`).
  - No leading `"` + all-digits → int. Otherwise → unquoted string.
  - Blank lines inside the fence are silently skipped.
  - Everything after the closing fence is the body (preserved verbatim).

Writer rules (locked in B.3 spec):
  - Keys appear in canonical order; extras (forward-compat) follow in sorted order.
  - String fields (label, evidence_file, content_hash, model_version) always
    double-quoted; embedded `"` escaped as `\"`; embedded `\` escaped as `\\`.
  - Int fields (evidence_start, evidence_end) unquoted.
  - confidence: bare unquoted (enum, no spaces).
  - Newlines in any value rejected at render time (raise ValueError).

Stdlib only. Targets Python 3.8+.
"""

from typing import Any, Dict, List, Optional, Tuple


class FrontmatterParseError(Exception):
    pass


# Canonical key order for the v0 schema. Keys not in this list are emitted
# after the canonical block in sorted order (forward-compat extension point).
_CANONICAL_KEYS: List[str] = [
    "label",
    "confidence",
    "evidence_file",
    "evidence_start",
    "evidence_end",
    "content_hash",
    "model_version",
]

# Fields whose values are always emitted with double-quotes.
_QUOTED_STRING_FIELDS = frozenset(
    ["label", "evidence_file", "content_hash", "model_version"]
)

# Maximum number of lines to scan from the opening fence for a closing fence.
_FRONTMATTER_LINE_LIMIT = 100


def _quote_string(value: str) -> str:
    """Return `value` wrapped in double quotes with embedded `"` escaped.

    Newlines in `value` are rejected here because front-matter is a
    single-line format; newlines would corrupt the YAML-subset structure
    and are rejected at set-time by `_validate_string` as well.
    """
    if "\n" in value or "\r" in value:
        raise ValueError(
            "render_frontmatter: string value contains a newline — "
            "newlines are not permitted in front-matter fields: {0!r}".format(value[:80])
        )
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return '"{0}"'.format(escaped)


def _parse_value(raw: str) -> Any:
    """Parse a raw (stripped) YAML-subset value token into a Python scalar.

    Rules (in order):
      1. Leading `"` → quoted string: strip outer `"`, unescape `\"` and `\\`.
      2. All-digit characters (optionally leading `-`) → int.
      3. Otherwise → unquoted string (strip whitespace).
    """
    stripped = raw.strip()
    if stripped.startswith('"'):
        return _unescape_quoted(stripped)
    if stripped.lstrip("-").isdigit() and stripped != "-":
        return int(stripped)
    return stripped


def _unescape_quoted(raw: str) -> str:
    """Walk `raw` (must start with `"`) and return the unescaped inner string.

    Handles two escape sequences: `\"` → `"` and `\\` → `\`. An unrecognised
    escape (e.g. `\n` literal) emits the backslash verbatim and continues with
    the next char as a normal character. Stops at the first unescaped `"`. If
    no closing quote is found, returns whatever was accumulated.
    """
    if not raw.startswith('"'):
        return raw
    i = 1
    out: List[str] = []
    while i < len(raw):
        ch = raw[i]
        if ch == "\\" and i + 1 < len(raw):
            nxt = raw[i + 1]
            if nxt == '"':
                out.append('"')
                i += 2
                continue
            if nxt == "\\":
                out.append("\\")
                i += 2
                continue
            out.append("\\")
            i += 1
            continue
        if ch == '"':
            break
        out.append(ch)
        i += 1
    return "".join(out)


def parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    """Parse a .md document. Return (record, body).

    `record` is the front-matter dict (values are str or int).
    `body` is the post-fence text (may be empty string).

    Raises FrontmatterParseError on malformed input (see module docstring).
    """
    lines = text.split("\n")

    # Document must start with `---` on line 1.
    if not lines or lines[0].rstrip("\r") != "---":
        raise FrontmatterParseError("missing leading --- fence")

    record: Dict[str, Any] = {}
    closing_index: Optional[int] = None

    for i in range(1, min(len(lines), _FRONTMATTER_LINE_LIMIT + 1)):
        line = lines[i].rstrip("\r")
        if line == "---":
            closing_index = i
            break
        if line.strip() == "":
            continue
        # Must be `key: value`.
        if ":" not in line:
            raise FrontmatterParseError(
                "unparseable front-matter line (no ':' separator): {0!r}".format(line)
            )
        # Split on first `:` only — values may contain colons.
        colon_pos = line.index(":")
        key = line[:colon_pos].strip()
        value_raw = line[colon_pos + 1:]
        if key in record:
            raise FrontmatterParseError("duplicate key {0!r}".format(key))
        record[key] = _parse_value(value_raw)

    if closing_index is None:
        raise FrontmatterParseError(
            "missing closing --- fence (not found within {0} lines)".format(
                _FRONTMATTER_LINE_LIMIT
            )
        )

    # Body = everything after the closing fence line.
    body = "\n".join(lines[closing_index + 1:])
    return record, body


def render_frontmatter(record: Dict[str, Any], body_header: str) -> str:
    """Render `record` + `body_header` into a .md document string.

    Output format:
      ---
      label: "<value>"
      confidence: <value>
      evidence_file: "<value>"
      evidence_start: <int>
      evidence_end: <int>
      content_hash: "<value>"
      model_version: "<value>"
      ---

      <body_header>

    Trailing newline is guaranteed. String fields that require quoting
    raise ValueError if they contain newline characters.
    """
    lines: List[str] = ["---"]

    # Emit canonical keys first, then extras in sorted order.
    extra_keys = sorted(k for k in record if k not in _CANONICAL_KEYS)
    key_order = _CANONICAL_KEYS + extra_keys

    for key in key_order:
        if key not in record:
            continue
        value = record[key]
        if key in _QUOTED_STRING_FIELDS:
            if not isinstance(value, str):
                raise ValueError(
                    "render_frontmatter: field {0!r} must be a string, got {1!r}".format(
                        key, type(value).__name__
                    )
                )
            formatted = _quote_string(value)
        elif key in ("evidence_start", "evidence_end"):
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError(
                    "render_frontmatter: field {0!r} must be an int, got {1!r}".format(
                        key, type(value).__name__
                    )
                )
            formatted = str(value)
        else:
            # Unquoted (e.g. confidence enum, or any extra key).
            formatted = str(value)
        lines.append("{0}: {1}".format(key, formatted))

    lines.append("---")
    lines.append("")
    lines.append(body_header.rstrip("\n"))
    lines.append("")
    return "\n".join(lines)
