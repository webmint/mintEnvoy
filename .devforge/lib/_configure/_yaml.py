"""YAML emit + parse for configure.yaml (closed shape, schema-driven)."""

from __future__ import annotations

from typing import Optional

from ._schema import FIELD_SCHEMA, _PACKAGE_STACK_FIELDS


# YAML reserved words (case-insensitive); a bare scalar matching one of
# these would be ambiguous, so it must be quoted.
_YAML_RESERVED_WORDS = {
    "null", "true", "false", "yes", "no", "on", "off", "~", "n/a",
}

# Characters whose presence in a scalar forces quoting. Newlines/CR are
# included so multi-line scalars (e.g. project_structure verbatim from
# docs/) round-trip via \n/\r escape sequences instead of producing
# broken yaml that splits across physical lines.
_YAML_SPECIAL_CHARS = set(" :[]{},#&*!|>'\"%@`\n\r")


def _needs_quoting(s: str) -> bool:
    """Return True if a string scalar must be double-quoted on emit.

    Matches init_helper._needs_quoting logic exactly: empty string,
    YAML reserved words, purely numeric strings, and strings containing
    YAML special chars all require quoting.
    """
    if s == "":
        return True
    if s.lower() in _YAML_RESERVED_WORDS:
        return True
    # Purely numeric (int or float-ish) — must be quoted.
    try:
        int(s, 0)
        return True
    except (ValueError, TypeError):
        pass
    try:
        float(s)
        return True
    except ValueError:
        pass
    for ch in s:
        if ch in _YAML_SPECIAL_CHARS:
            return True
    return False


def _emit_scalar(value: Optional[str]) -> str:
    """Render a scalar value (str or None) as a YAML token.

    None → null. Strings are double-quoted when _needs_quoting is True,
    with embedded backslashes, double-quotes, newlines, and carriage
    returns escaped. Mirrors init_helper._emit_scalar plus newline
    escaping (intentional divergence so verbatim multi-line docs
    sections round-trip).
    """
    if value is None:
        return "null"
    if _needs_quoting(value):
        escaped = (
            value.replace("\\", "\\\\")
            .replace("\"", "\\\"")
            .replace("\n", "\\n")
            .replace("\r", "\\r")
        )
        return "\"{0}\"".format(escaped)
    return value


def emit_yaml(state: dict) -> str:
    """Serialize `state` to a deterministic YAML string.

    Walks FIELD_SCHEMA in locked order. Field order is part of the
    diff-stability contract — do not sort or reorder.

    scalar None → null
    scalar str  → double-quoted when needed; unquoted otherwise
    string_array empty → []
    string_array populated → block list, each item double-quoted
    package_stack_array empty → []
    package_stack_array populated → block records, nullable sub-fields as null
    """
    lines = []
    for name, kind in FIELD_SCHEMA:
        value = state.get(name)
        if kind == "scalar":
            lines.append("{0}: {1}".format(name, _emit_scalar(value)))
        elif kind == "string_array":
            if not value:
                lines.append("{0}: []".format(name))
            else:
                lines.append("{0}:".format(name))
                for item in value:
                    lines.append("  - {0}".format(_emit_scalar(item)))
        elif kind == "package_stack_array":
            if not value:
                lines.append("{0}: []".format(name))
            else:
                lines.append("{0}:".format(name))
                for record in value:
                    first = True
                    for field in _PACKAGE_STACK_FIELDS:
                        fval = record.get(field)
                        token = _emit_scalar(fval)
                        if first:
                            lines.append("  - {0}: {1}".format(field, token))
                            first = False
                        else:
                            lines.append("    {0}: {1}".format(field, token))
        else:
            raise AssertionError("unknown field kind: {0}".format(kind))
    return "\n".join(lines) + "\n"


class YamlParseError(ValueError):
    """Raised when parser encounters input outside the closed shape."""


def _parse_scalar_token(token: str, lineno: int) -> Optional[str]:
    """Parse a single scalar token (the RHS of `key: <token>`).

    Mirrors init_helper._parse_scalar_token exactly.
    """
    token = token.strip()
    if token == "null":
        return None
    if token == "[]":
        raise YamlParseError(
            "line {0}: unexpected inline empty list".format(lineno)
        )
    if token.startswith("\""):
        if not token.endswith("\"") or len(token) < 2:
            raise YamlParseError(
                "line {0}: unterminated double-quoted string".format(lineno)
            )
        body = token[1:-1]
        result = []
        i = 0
        while i < len(body):
            ch = body[i]
            if ch == "\\" and i + 1 < len(body):
                nxt = body[i + 1]
                if nxt == "\\":
                    result.append("\\")
                elif nxt == "\"":
                    result.append("\"")
                elif nxt == "n":
                    result.append("\n")
                elif nxt == "r":
                    result.append("\r")
                else:
                    raise YamlParseError(
                        "line {0}: unknown escape sequence \\{1}".format(lineno, nxt)
                    )
                i += 2
            else:
                result.append(ch)
                i += 1
        return "".join(result)
    if token.startswith("&") or token.startswith("*"):
        raise YamlParseError(
            "line {0}: anchors/aliases are not supported".format(lineno)
        )
    if token in ("|", ">"):
        raise YamlParseError(
            "line {0}: multi-line scalars are not supported".format(lineno)
        )
    if token.startswith("{"):
        raise YamlParseError(
            "line {0}: flow-style mappings are not supported".format(lineno)
        )
    if token.startswith("'"):
        raise YamlParseError(
            "line {0}: single-quoted strings are not supported".format(lineno)
        )
    return token


def parse_yaml(text: str) -> dict:
    """Parse a YAML string previously emitted by `emit_yaml`.

    Returns a state dict matching FIELD_SCHEMA shape. Raises YamlParseError
    on input outside the closed shape (anchors, flow mappings, multi-line
    scalars, unknown fields, unexpected indentation).

    Round-trip invariant: parse_yaml(emit_yaml(state)) == state for all
    valid state shapes.
    """
    # Local import to avoid circular dependency with _state (which depends
    # on parse_yaml). default_state() returns a fresh skeleton dict.
    from ._state import default_state

    field_kinds = dict(FIELD_SCHEMA)
    state = default_state()
    current_field = None
    current_kind = None
    current_record = None  # for package_stack_array records
    current_record_lineno = 0  # for missing-subfield error message

    def _close_record(at_lineno):
        # Close the open package_stack record (if any) by validating it
        # has all required subfields. Closed-shape contract: a record
        # missing a REQUIRED subfield is rejected at parse time.
        # OPTIONAL subfields (test_command) default to None for backward
        # compatibility with configure.yaml files written before these
        # fields existed.
        if current_record is None:
            return
        _OPTIONAL_SUBFIELDS = {"test_command"}
        missing_required = [
            f for f in _PACKAGE_STACK_FIELDS
            if f not in current_record and f not in _OPTIONAL_SUBFIELDS
        ]
        if missing_required:
            raise YamlParseError(
                "line {0}: package_stack record opened at line {1} "
                "is missing required subfield(s): {2}".format(
                    at_lineno, current_record_lineno, ", ".join(missing_required)
                )
            )
        # Default optional subfields to None if absent.
        for f in _OPTIONAL_SUBFIELDS:
            if f not in current_record:
                current_record[f] = None

    lines = text.splitlines()
    for idx, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip()
        if line == "":
            continue

        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        if indent == 0:
            _close_record(idx)
            current_record = None
            if ":" not in stripped:
                raise YamlParseError(
                    "line {0}: expected 'key: value' or 'key:'".format(idx)
                )
            key, _, rest = stripped.partition(":")
            key = key.strip()
            rest = rest.strip()
            if key not in field_kinds:
                raise YamlParseError(
                    "line {0}: unknown top-level field {1!r}".format(idx, key)
                )
            current_field = key
            current_kind = field_kinds[key]
            if current_kind == "scalar":
                state[key] = _parse_scalar_token(rest, idx)
                current_field = None
                current_kind = None
            else:
                # string_array or package_stack_array
                if rest == "[]":
                    state[key] = []
                    current_field = None
                    current_kind = None
                elif rest == "":
                    state[key] = []
                else:
                    raise YamlParseError(
                        "line {0}: expected '[]' or empty after array key, got {1!r}".format(
                            idx, rest
                        )
                    )
        elif indent == 2:
            if current_field is None or current_kind == "scalar":
                raise YamlParseError(
                    "line {0}: nested content without an open array".format(idx)
                )
            if not stripped.startswith("- "):
                raise YamlParseError(
                    "line {0}: array item must start with '- '".format(idx)
                )
            item_body = stripped[2:]
            if current_kind == "string_array":
                # Items are scalars.
                state[current_field].append(_parse_scalar_token(item_body, idx))
                current_record = None
            elif current_kind == "package_stack_array":
                # New record starting — close prior (if any) before opening.
                _close_record(idx)
                # First field of a record.
                if ":" not in item_body:
                    raise YamlParseError(
                        "line {0}: package_stack record item must be 'key: value'".format(idx)
                    )
                key, _, rest = item_body.partition(":")
                key = key.strip()
                rest = rest.strip()
                current_record = {key: _parse_scalar_token(rest, idx)}
                current_record_lineno = idx
                state[current_field].append(current_record)
        elif indent == 4:
            # Continuation of a package_stack_array record.
            if current_record is None:
                raise YamlParseError(
                    "line {0}: continuation line without an open record".format(idx)
                )
            if ":" not in stripped:
                raise YamlParseError(
                    "line {0}: continuation must be 'key: value'".format(idx)
                )
            key, _, rest = stripped.partition(":")
            key = key.strip()
            rest = rest.strip()
            current_record[key] = _parse_scalar_token(rest, idx)
        else:
            raise YamlParseError(
                "line {0}: unexpected indentation {1}".format(idx, indent)
            )

    # End of input — validate any record still open.
    _close_record(len(lines))
    return state
