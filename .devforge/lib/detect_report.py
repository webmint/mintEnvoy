"""detect_report — composes the Phase 1 Detection Report (legacy /setup-wizard).

ORPHANED — its sole consumer `/setup-wizard` was retired in plan 30 (2026-06-21).
The architecture pivot replaced it with per-command helpers (`init_helper` for
`/init-forge`, `configure_helper` for `/configure`, etc.). No 2.0 command or
helper invokes this file (verified: only comment references remain). It is dead
code retained pending an explicit deletion pass — do NOT extend it; new work
goes to the per-command helpers.

This helper writes `.devforge/detection_report.yaml` containing project facts
discovered by the wizard's detection phase (workspace mode, languages,
frameworks, packages, etc.).

Architecture notes:

- The yaml IS the state. There is no intermediate JSON state file. Each setter
  reads the yaml from disk (or loads defaults if the file is absent), mutates
  an in-memory dict, and writes yaml back atomically via tempfile.mkstemp +
  os.replace.

- A single `FIELD_SCHEMA` is the source of truth for field order, type, and
  set-time validation. The yaml emitter and parser are tightly coupled to it
  and assume only the closed shape this helper produces.

- All scalars default to `None`; all arrays default to `[]`. Loud-fail
  downstream when a required field is `None` is the design — no "sensible
  default" overrides.

- `reset` writes a fresh defaults yaml; it does NOT delete the file. The
  artifact always exists post-reset.

- Cross-field validation is intentionally NOT performed here. `primary_language`
  is user-overridable; parallel-array length parity is wizard-driven. The
  helper validates set-time per-field shape only.

Stdlib only. No third-party dependencies. Targets Python 3.8+.
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path

# Published artifact name (NOT a hidden state file — downstream phases read it).
OUTPUT_FILE_NAME = "detection_report.yaml"


# ---------------------------------------------------------------------------
# FIELD_SCHEMA — single source of truth for field order, type, and defaults.
# ---------------------------------------------------------------------------

# Type tags:
#   "scalar"               — string-or-None value
#   "package_record_array" — list of {"path": str, "manifest": str} records
#   "value_path_array"     — list of {"path": str, "value": str|None} records
FIELD_SCHEMA = [
    ("project_root", "scalar"),
    ("workspace_mode", "scalar"),
    ("project_state", "scalar"),
    ("default_branch", "scalar"),
    ("primary_language", "scalar"),
    ("packages_detected", "package_record_array"),
    ("languages", "value_path_array"),
    ("frameworks", "value_path_array"),
    ("build_tools", "value_path_array"),
    ("build_commands", "value_path_array"),
    ("type_check_commands", "value_path_array"),
    ("lint_commands", "value_path_array"),
    # Library categories — value field + evidence sibling pairs.
    ("auth_layer", "scalar"),
    ("auth_layer_evidence", "scalar"),
    ("state_management", "scalar"),
    ("state_management_evidence", "scalar"),
    ("styling", "scalar"),
    ("styling_evidence", "scalar"),
    ("routing", "scalar"),
    ("routing_evidence", "scalar"),
    ("validation_library", "scalar"),
    ("validation_library_evidence", "scalar"),
    ("error_handling_library", "scalar"),
    ("error_handling_library_evidence", "scalar"),
    ("error_handling_pattern", "scalar"),
    ("error_handling_pattern_evidence", "scalar"),
    # Architecture shape (closed enum) + evidence sibling.
    ("architecture_shape", "scalar"),
    ("architecture_evidence", "scalar"),
    # Runtime URL value + paired source (provenance).
    ("runtime_url_value", "scalar"),
    ("runtime_url_source", "scalar"),
]

# Enum-restricted scalars; key = field name, value = allowed set.
ENUM_FIELDS = {
    "workspace_mode": {"standalone", "wrapper"},
    "project_state": {"empty", "brownfield"},
    "architecture_shape": {
        "layered",
        "feature-modular",
        "monorepo",
        "feature-modular-monorepo",
        "clean",
        "clean-feature-modular-monorepo",
        "hexagonal",
        "mvc",
        "bloc",
        "flat",
        "other",
    },
}

# Library-category fields where the helper writes both the value field and a
# matching `<name>_evidence` sibling. Used by `set-<library-category>` setters.
LIBRARY_CATEGORY_FIELDS = (
    "auth_layer",
    "state_management",
    "styling",
    "routing",
    "validation_library",
    "error_handling_library",
    "error_handling_pattern",
)

# Built-in skip list for find-nested-git.
NESTED_GIT_SKIP = {
    "node_modules",
    "target",
    "dist",
    "build",
    "__pycache__",
    ".venv",
    "venv",
    ".git",
}

# YAML reserved words (case-insensitive); a bare scalar matching one of these
# would be ambiguous (parsed as bool/null/etc.), so it must be quoted. `n/a` is
# included as a stylistic choice, not a YAML-ambiguity rescue: bare `n/a` would
# parse fine as the string "n/a", but quoting it visually distinguishes the
# "by-design absent" sentinel from the bare `null` sentinel on the wire.
YAML_RESERVED_WORDS = {
    "null", "true", "false", "yes", "no", "on", "off", "~", "n/a",
}

# Characters whose presence in a scalar forces quoting.
YAML_SPECIAL_CHARS = set(" :[]{},#&*!|>'\"%@`")


# ---------------------------------------------------------------------------
# Path resolution.
# ---------------------------------------------------------------------------


def _output_file_path():
    """Resolve the output file path at call time (not import time).

    Honors the `DEVFORGE_DIR` environment variable when set — used by tests
    and by unusual install layouts. When unset, computes the path from this
    script's own location: `<target>/.devforge/lib/detect_report.py` lives
    one directory below `<target>/.devforge/`, where the artifact belongs.
    """
    env_dir = os.environ.get("DEVFORGE_DIR")
    if env_dir:
        return Path(env_dir) / OUTPUT_FILE_NAME
    return Path(__file__).resolve().parent.parent / OUTPUT_FILE_NAME


# ---------------------------------------------------------------------------
# Defaults + validators.
# ---------------------------------------------------------------------------


def default_state():
    """Return a fresh defaults dict matching FIELD_SCHEMA shape."""
    state = {}
    for name, kind in FIELD_SCHEMA:
        if kind == "scalar":
            state[name] = None
        else:
            state[name] = []
    return state


def _has_control_chars(value):
    """Return True if `value` contains any control char (< 0x20 or DEL)."""
    for ch in value:
        code = ord(ch)
        if code < 0x20 or code == 0x7F:
            return True
    return False


def _validate_string(value, field_name):
    """Reject empty / control-char strings at set-time. Raises ValueError."""
    if not isinstance(value, str):
        raise ValueError(
            "{0}: expected string, got {1}".format(field_name, type(value).__name__)
        )
    if not value.strip():
        raise ValueError("{0}: value must be non-empty".format(field_name))
    if _has_control_chars(value):
        raise ValueError(
            "{0}: control characters are not permitted".format(field_name)
        )


def _validate_enum(value, field_name):
    """Reject values not in the allowed enum set."""
    allowed = ENUM_FIELDS[field_name]
    if value not in allowed:
        raise ValueError(
            "{0}: must be one of {1}, got {2!r}".format(
                field_name, sorted(allowed), value
            )
        )


def _validate_path(value, field_name):
    """Reject paths that escape the project root or are absolute.

    A valid path is either `.` (the project-root sentinel) or a relative path
    rooted inside the project (no leading `/` or `\\`, no Windows drive prefix
    like `C:\\` or `c:/`, and no `..` path segment that could traverse upward).

    Path-segment splitting recognizes BOTH `/` and `\\` as separators so that a
    Windows-style `foo\\..\\bar` is caught the same as the POSIX form. The
    trailing slash is permitted at this stage; `_normalize_path` strips it for
    storage. Empty / control-char strings are rejected up-front via
    `_validate_string` so the existing checks still run.
    """
    _validate_string(value, field_name)
    # POSIX absolute path or unix-style root-relative.
    if value.startswith("/") or value.startswith("\\"):
        raise ValueError(
            "{0}: absolute paths are not permitted, got {1!r}".format(
                field_name, value
            )
        )
    # Windows drive prefix: letter + ':' + ('\\' or '/'). Match `C:\foo`,
    # `c:/foo`, etc. A bare `C:` (no separator) is unusual but still treated
    # as drive-relative on Windows; reject it too for consistency.
    if len(value) >= 2 and value[0].isalpha() and value[1] == ":":
        raise ValueError(
            "{0}: absolute paths are not permitted, got {1!r}".format(
                field_name, value
            )
        )
    # Any `..` path segment is forbidden — splits on both separators so a
    # mixed-style `foo\..\bar` is caught alongside the POSIX form.
    segments = value.replace("\\", "/").split("/")
    for seg in segments:
        if seg == "..":
            raise ValueError(
                "{0}: parent-directory traversal '..' is not permitted, got {1!r}".format(
                    field_name, value
                )
            )


def _normalize_path(p):
    """Strip a single trailing slash. Used for path comparison + storage.

    `client/` and `client` should refer to the same directory. We normalize at
    every compare site AND at the storage site so callers passing either form
    end up with one canonical record. `_normalize_path("")` returns `""`, which
    is fine — empty strings are already rejected by `_validate_string`.
    """
    return p.rstrip("/")


# ---------------------------------------------------------------------------
# YAML emitter (closed-shape).
# ---------------------------------------------------------------------------


def _needs_quoting(s):
    """Return True if a string scalar must be double-quoted in our emit form."""
    if s == "":
        return True
    if s.lower() in YAML_RESERVED_WORDS:
        return True
    # Purely numeric (int or float-ish) — must be quoted to avoid YAML
    # interpreting as a number on read.
    try:
        float(s)
        return True
    except ValueError:
        pass
    for ch in s:
        if ch in YAML_SPECIAL_CHARS:
            return True
    return False


def _emit_scalar(value):
    """Render a scalar value (str or None) as a YAML token."""
    if value is None:
        return "null"
    # Control chars are rejected at set-time; emitter only escapes " and \.
    if _needs_quoting(value):
        escaped = value.replace("\\", "\\\\").replace("\"", "\\\"")
        return "\"{0}\"".format(escaped)
    return value


def emit_yaml(state):
    """Serialize `state` to a deterministic YAML string.

    Field order follows FIELD_SCHEMA. Empty arrays render as `field: []`.
    Arrays of records use block style with two-space indentation.
    """
    lines = []
    for name, kind in FIELD_SCHEMA:
        value = state.get(name)
        if kind == "scalar":
            lines.append("{0}: {1}".format(name, _emit_scalar(value)))
        elif kind == "package_record_array":
            if not value:
                lines.append("{0}: []".format(name))
            else:
                lines.append("{0}:".format(name))
                for record in value:
                    lines.append("  - path: {0}".format(_emit_scalar(record["path"])))
                    lines.append(
                        "    manifest: {0}".format(_emit_scalar(record["manifest"]))
                    )
        elif kind == "value_path_array":
            if not value:
                lines.append("{0}: []".format(name))
            else:
                lines.append("{0}:".format(name))
                for record in value:
                    lines.append("  - path: {0}".format(_emit_scalar(record["path"])))
                    lines.append(
                        "    value: {0}".format(_emit_scalar(record["value"]))
                    )
        else:
            raise AssertionError("unknown field kind: {0}".format(kind))
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# YAML parser (closed-shape — inverse of emitter).
# ---------------------------------------------------------------------------


class YamlParseError(ValueError):
    """Raised when parser encounters input outside the closed shape."""


def _parse_scalar_token(token, lineno):
    """Parse a single scalar token (the RHS of `key: <token>`)."""
    token = token.strip()
    if token == "null":
        return None
    if token == "[]":
        # Caller treats `field: []` specially; this branch handles a record
        # value of `[]` which we don't emit, so reject for safety.
        raise YamlParseError(
            "line {0}: unexpected inline empty list".format(lineno)
        )
    if token.startswith("\""):
        if not token.endswith("\"") or len(token) < 2:
            raise YamlParseError(
                "line {0}: unterminated double-quoted string".format(lineno)
            )
        body = token[1:-1]
        # Reverse the emitter's escapes.
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
                else:
                    raise YamlParseError(
                        "line {0}: unknown escape sequence \\{1}".format(lineno, nxt)
                    )
                i += 2
            else:
                result.append(ch)
                i += 1
        return "".join(result)
    # Reject features we don't emit — anchors, multi-line, flow mappings.
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
            "line {0}: single-quoted strings are not supported — values are written double-quoted by the owning helper; this file was likely edited outside the setter API (convert the value to double quotes, or regenerate the file via its owning command)".format(lineno)
        )
    return token


def parse_yaml(text):
    """Parse a YAML string previously emitted by `emit_yaml`.

    Returns a state dict. Raises YamlParseError on input outside the closed
    shape (anchors, flow mappings, multi-line scalars, deeper than one nested
    array level).
    """
    field_kinds = dict(FIELD_SCHEMA)
    state = default_state()
    current_field = None
    current_kind = None
    current_record = None  # dict being filled in for value_path_array / package_record_array

    lines = text.splitlines()
    for idx, raw_line in enumerate(lines, start=1):
        # Strip trailing whitespace; preserve leading whitespace.
        line = raw_line.rstrip()
        if line == "":
            continue

        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        if indent == 0:
            # Top-level key. Finalize any pending record.
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
                # Array. Either empty (`field: []`) or block (`field:`).
                if rest == "[]":
                    state[key] = []
                    current_field = None
                    current_kind = None
                elif rest == "":
                    state[key] = []
                    # Records will follow at indent 2.
                else:
                    raise YamlParseError(
                        "line {0}: expected '[]' or empty after array key, got {1!r}".format(
                            idx, rest
                        )
                    )
        elif indent == 2:
            # Item under the current array. Must start with "- ".
            if current_field is None or current_kind == "scalar":
                raise YamlParseError(
                    "line {0}: nested content without an open array".format(idx)
                )
            if not stripped.startswith("- "):
                raise YamlParseError(
                    "line {0}: array item must start with '- '".format(idx)
                )
            item_body = stripped[2:]
            if ":" not in item_body:
                raise YamlParseError(
                    "line {0}: array item must be 'key: value'".format(idx)
                )
            key, _, rest = item_body.partition(":")
            key = key.strip()
            rest = rest.strip()
            current_record = {key: _parse_scalar_token(rest, idx)}
            state[current_field].append(current_record)
        elif indent == 4:
            # Continuation of the current record.
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

    return state


# ---------------------------------------------------------------------------
# Read-modify-write helpers.
# ---------------------------------------------------------------------------


def _load_state():
    """Read yaml from disk if present; otherwise return defaults."""
    path = _output_file_path()
    if not path.exists():
        return default_state()
    text = path.read_text(encoding="utf-8")
    state = parse_yaml(text)
    # Backfill any field that wasn't present on disk (forward-compatibility
    # if FIELD_SCHEMA grows; not currently expected to trigger).
    for name, kind in FIELD_SCHEMA:
        if name not in state:
            state[name] = None if kind == "scalar" else []
    return state


def _write_state(state):
    """Atomically write `state` to the output yaml path.

    Uses tempfile.mkstemp in the same directory as the target so os.replace is
    atomic on a single filesystem. On any failure, attempts to remove the temp
    file and re-raises.
    """
    target = _output_file_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix="detection-report-",
        suffix=".yaml.tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(emit_yaml(state))
        os.replace(tmp_path, str(target))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Subcommand implementations.
# ---------------------------------------------------------------------------


def _die(message, code=1):
    sys.stderr.write("detect_report: {0}\n".format(message))
    return code


def cmd_reset(args):
    """Write a fresh defaults yaml. Idempotent: byte-identical on re-run."""
    try:
        _write_state(default_state())
    except OSError as err:
        return _die("reset: cannot write {0}: {1}".format(_output_file_path(), err))
    return 0


def _set_scalar(field_name, value):
    """Common path for scalar setters. Returns CLI exit code."""
    try:
        _validate_string(value, field_name)
        if field_name in ENUM_FIELDS:
            _validate_enum(value, field_name)
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        state = _load_state()
    except (OSError, YamlParseError) as err:
        return _die("cannot load state: {0}".format(err))
    state[field_name] = value
    try:
        _write_state(state)
    except OSError as err:
        return _die("cannot write state: {0}".format(err))
    return 0


def cmd_set_project_root(args):
    # project_root is a path (`.` for standalone, an inner folder name for
    # wrapper mode), so it gets path-shape validation in addition to the
    # scalar-shape validation performed by `_set_scalar`.
    try:
        _validate_path(args.value, "project_root")
    except ValueError as err:
        return _die(str(err), code=2)
    return _set_scalar("project_root", args.value)


def cmd_set_workspace_mode(args):
    return _set_scalar("workspace_mode", args.value)


def cmd_set_project_state(args):
    return _set_scalar("project_state", args.value)


def cmd_set_default_branch(args):
    return _set_scalar("default_branch", args.value)


def cmd_set_primary_language(args):
    return _set_scalar("primary_language", args.value)


def cmd_add_package(args):
    """Append a {path, manifest} record. Errors on duplicate path."""
    try:
        _validate_path(args.path, "packages_detected.path")
        _validate_string(args.manifest, "packages_detected.manifest")
    except ValueError as err:
        return _die(str(err), code=2)
    path = _normalize_path(args.path)
    try:
        state = _load_state()
    except (OSError, YamlParseError) as err:
        return _die("cannot load state: {0}".format(err))
    for record in state["packages_detected"]:
        if record.get("path") == path:
            return _die(
                "add-package: path {0!r} already present in packages_detected".format(
                    path
                ),
                code=2,
            )
    state["packages_detected"].append({"path": path, "manifest": args.manifest})
    try:
        _write_state(state)
    except OSError as err:
        return _die("cannot write state: {0}".format(err))
    return 0


def _resolve_value_or_null(args):
    """Return the value to store given mutually-exclusive --value / --null."""
    if getattr(args, "null", False):
        return None
    return args.value


def _add_value_path(field_name, args, allow_null):
    """Common path for value/path arrays. Upserts by path, validates FK to packages_detected."""
    # Resolve and validate value.
    if allow_null:
        value = _resolve_value_or_null(args)
        if value is not None:
            try:
                _validate_string(value, "{0}.value".format(field_name))
            except ValueError as err:
                return _die(str(err), code=2)
    else:
        value = args.value
        try:
            _validate_string(value, "{0}.value".format(field_name))
        except ValueError as err:
            return _die(str(err), code=2)
    # Validate path.
    try:
        _validate_path(args.path, "{0}.path".format(field_name))
    except ValueError as err:
        return _die(str(err), code=2)
    path = _normalize_path(args.path)
    try:
        state = _load_state()
    except (OSError, YamlParseError) as err:
        return _die("cannot load state: {0}".format(err))
    # FK check — path must already exist in packages_detected.
    known_paths = {
        _normalize_path(r.get("path", "")) for r in state["packages_detected"]
    }
    if path not in known_paths:
        return _die(
            "{0}: path {1!r} not found in packages_detected (add-package first)".format(
                field_name, path
            ),
            code=2,
        )
    # Upsert by path.
    for record in state[field_name]:
        if record.get("path") == path:
            record["value"] = value
            break
    else:
        state[field_name].append({"path": path, "value": value})
    try:
        _write_state(state)
    except OSError as err:
        return _die("cannot write state: {0}".format(err))
    return 0


def cmd_add_language(args):
    # languages: --value is required (no --null sentinel for languages).
    return _add_value_path("languages", args, allow_null=False)


def cmd_add_framework(args):
    return _add_value_path("frameworks", args, allow_null=True)


def cmd_add_build_tool(args):
    return _add_value_path("build_tools", args, allow_null=True)


def cmd_add_build_command(args):
    return _add_value_path("build_commands", args, allow_null=True)


def cmd_add_type_check_command(args):
    return _add_value_path("type_check_commands", args, allow_null=True)


def cmd_add_lint_command(args):
    return _add_value_path("lint_commands", args, allow_null=True)


def _set_library_category(field_name, args):
    """Common path for the seven library-category setters.

    Each setter writes BOTH `<field_name>` and `<field_name>_evidence` in a
    single load-mutate-write pass. The CLI surface is:

      --null                          → value=None, evidence=None
      --value "N/A"                   → value="N/A", evidence=None
      --value <other> --evidence <t>  → value=<other>, evidence=<t>

    `--null` with `--evidence` is rejected (carve-out for clarity).
    `--value "N/A"` with `--evidence` is rejected (spec: no evidence when the
    concern doesn't apply).
    `--value <other>` without `--evidence` is rejected (spec: confirmed library
    detections require an evidence citation).
    """
    evidence_field = "{0}_evidence".format(field_name)
    null_flag = getattr(args, "null", False)
    value = getattr(args, "value", None)
    evidence = getattr(args, "evidence", None)

    if null_flag:
        if evidence is not None:
            return _die(
                "{0}: --evidence is not permitted with --null".format(field_name),
                code=2,
            )
        target_value = None
        target_evidence = None
    else:
        # --value branch. argparse mutex guarantees value is not None here.
        try:
            _validate_string(value, field_name)
        except ValueError as err:
            return _die(str(err), code=2)
        if value == "N/A":
            if evidence is not None:
                return _die(
                    "{0}: --evidence is not permitted with --value \"N/A\"".format(
                        field_name
                    ),
                    code=2,
                )
            target_value = "N/A"
            target_evidence = None
        else:
            if evidence is None:
                return _die(
                    "{0}: --evidence is required for confirmed library detections".format(
                        field_name
                    ),
                    code=2,
                )
            try:
                _validate_string(evidence, evidence_field)
            except ValueError as err:
                return _die(str(err), code=2)
            target_value = value
            target_evidence = evidence

    try:
        state = _load_state()
    except (OSError, YamlParseError) as err:
        return _die("cannot load state: {0}".format(err))
    state[field_name] = target_value
    state[evidence_field] = target_evidence
    try:
        _write_state(state)
    except OSError as err:
        return _die("cannot write state: {0}".format(err))
    return 0


def cmd_set_auth_layer(args):
    return _set_library_category("auth_layer", args)


def cmd_set_state_management(args):
    return _set_library_category("state_management", args)


def cmd_set_styling(args):
    return _set_library_category("styling", args)


def cmd_set_routing(args):
    return _set_library_category("routing", args)


def cmd_set_validation_library(args):
    return _set_library_category("validation_library", args)


def cmd_set_error_handling_library(args):
    return _set_library_category("error_handling_library", args)


def cmd_set_error_handling_pattern(args):
    return _set_library_category("error_handling_pattern", args)


def cmd_set_architecture_shape(args):
    """Set the project-wide architectural shape (closed enum) + evidence.

    `--value other` accepts an optional `--evidence`.
    Every other enum value REQUIRES `--evidence`.
    """
    value = args.value
    evidence = getattr(args, "evidence", None)
    try:
        _validate_string(value, "architecture_shape")
        _validate_enum(value, "architecture_shape")
    except ValueError as err:
        return _die(str(err), code=2)
    if value == "other":
        if evidence is not None:
            try:
                _validate_string(evidence, "architecture_evidence")
            except ValueError as err:
                return _die(str(err), code=2)
        target_evidence = evidence  # may be None
    else:
        if evidence is None:
            return _die(
                "architecture_shape: --evidence is required for {0!r}".format(value),
                code=2,
            )
        try:
            _validate_string(evidence, "architecture_evidence")
        except ValueError as err:
            return _die(str(err), code=2)
        target_evidence = evidence
    try:
        state = _load_state()
    except (OSError, YamlParseError) as err:
        return _die("cannot load state: {0}".format(err))
    state["architecture_shape"] = value
    state["architecture_evidence"] = target_evidence
    try:
        _write_state(state)
    except OSError as err:
        return _die("cannot write state: {0}".format(err))
    return 0


def _install_root():
    """Resolve the install root (parent of `.devforge/`).

    Used by `set-runtime-url` for relative-path validation. Mirrors the
    `find-nested-git` resolution: `_output_file_path().parent` is the
    `.devforge/` directory; its parent is the install root.
    """
    return _output_file_path().parent.parent


def cmd_set_runtime_url(args):
    """Set the local-development runtime URL with provenance.

    Two distinct call shapes (mutually exclusive):

    Shape A (set):
        --value <url> --source <config-path | "framework-default">
    Shape B (clear):
        --null --reason <text>

    Shape A path validation: when `--source` is anything other than the
    literal `framework-default`, the value is treated as a filesystem path
    that must exist. Relative paths are resolved against the install root +
    `project_root` (read from current state). Absolute paths must already
    exist on disk verbatim.
    """
    null_flag = getattr(args, "null", False)
    value = getattr(args, "value", None)
    source = getattr(args, "source", None)
    reason = getattr(args, "reason", None)

    if null_flag:
        # Shape B: --null --reason <text>
        if value is not None or source is not None:
            return _die(
                "set-runtime-url: --value/--source are not permitted with --null",
                code=2,
            )
        if reason is None:
            return _die(
                "set-runtime-url: --reason is required with --null", code=2
            )
        try:
            _validate_string(reason, "runtime_url_source")
        except ValueError as err:
            return _die(str(err), code=2)
        target_value = None
        target_source = reason
    else:
        # Shape A: --value <url> --source <path|framework-default>
        if reason is not None:
            return _die(
                "set-runtime-url: --reason is only valid with --null", code=2
            )
        if value is None:
            return _die("set-runtime-url: --value is required", code=2)
        if source is None:
            return _die("set-runtime-url: --source is required", code=2)
        try:
            _validate_string(value, "runtime_url_value")
        except ValueError as err:
            return _die(str(err), code=2)
        try:
            _validate_string(source, "runtime_url_source")
        except ValueError as err:
            return _die(str(err), code=2)
        if source != "framework-default":
            # Treat as filesystem path; validate existence.
            if os.path.isabs(source):
                resolved = Path(source)
            else:
                # Relative path: validate shape (no `..` segments, no
                # backslash-prefix, no Windows drive prefix) BEFORE resolving.
                # `_validate_path` rejects these, blocking traversal attempts
                # like `--source ../etc/config.ts` even when a file exists at
                # that location. The absolute branch above runs its own
                # existence check and is intentionally not routed through
                # `_validate_path` (which would reject any absolute path).
                try:
                    _validate_path(source, "runtime_url_source")
                except ValueError as err:
                    return _die(str(err), code=2)
                # Resolve relative to install_root + project_root.
                try:
                    state_for_pr = _load_state()
                except (OSError, YamlParseError) as err:
                    return _die("cannot load state: {0}".format(err))
                project_root = state_for_pr.get("project_root")
                if project_root is None:
                    return _die(
                        "set-runtime-url: project_root is unset; cannot resolve "
                        "relative --source path {0!r}".format(source),
                        code=2,
                    )
                base = _install_root()
                if project_root != ".":
                    base = base / project_root
                resolved = base / source
            if not resolved.exists():
                return _die(
                    "set-runtime-url: --source path does not exist: {0}".format(
                        resolved
                    ),
                    code=2,
                )
        target_value = value
        target_source = source

    try:
        state = _load_state()
    except (OSError, YamlParseError) as err:
        return _die("cannot load state: {0}".format(err))
    state["runtime_url_value"] = target_value
    state["runtime_url_source"] = target_source
    try:
        _write_state(state)
    except OSError as err:
        return _die("cannot write state: {0}".format(err))
    return 0


# ---------------------------------------------------------------------------
# Summary rendering.
# ---------------------------------------------------------------------------


# Per-package fields rendered in the "Per-package classification" section.
# Order is locked — matches the documented summary format.
SUMMARY_PER_PACKAGE_FIELDS = (
    "languages",
    "frameworks",
    "build_tools",
    "build_commands",
    "type_check_commands",
    "lint_commands",
)

# Project-level fields rendered in the "Project-level classification" section.
# Order is locked — matches the documented summary format. Evidence siblings
# are intentionally absent: the summary surfaces values, not provenance.
SUMMARY_PROJECT_FIELDS = (
    "primary_language",
    "auth_layer",
    "state_management",
    "styling",
    "routing",
    "validation_library",
    "error_handling_library",
    "error_handling_pattern",
    "architecture_shape",
    "runtime_url_value",
    "runtime_url_source",
)

# Workspace fields (the four lines of the "Workspace" section).
SUMMARY_WORKSPACE_FIELDS = (
    "workspace_mode",
    "project_root",
    "project_state",
    "default_branch",
)


def _render_scalar_for_summary(value):
    """Render a project-level / workspace scalar for the summary text.

    `None` becomes the literal string `null` (unquoted) so the reader can
    distinguish it from a string value of `"null"`. Empty strings render
    quoted (`""`) for the same disambiguation reason — empty string is a
    permitted scalar shape on the wire (set-time validation rejects it for
    user-supplied inputs, but a hand-edited yaml could plant one and the
    summary should not silently swallow it).
    """
    if value is None:
        return "null"
    if value == "":
        return "\"\""
    return value


def _format_value_path_array(records):
    """Group `records` by `value`, return `<v> (<n>), ...` count-desc string.

    Each record is `{"path": ..., "value": ...}`. `value` may be `None` —
    rendered as the literal string `null` (unquoted, matching scalar
    rendering) so all values participate in the grouping. Empty strings
    render quoted (`""`) for the same disambiguation reason — bare colon
    output (`- field:  (1)`) is visually indistinguishable from a
    truncated field label. Sort: count descending, ties broken by
    ascending alphabetical (case-sensitive Python default string
    compare). `null` and `""` participate in the same sort as any other
    value.
    """
    counts = {}
    for record in records:
        raw = record.get("value")
        key = "null" if raw is None else ("\"\"" if raw == "" else raw)
        counts[key] = counts.get(key, 0) + 1
    # Stable sort: primary by count desc, secondary by value asc.
    sorted_items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return ", ".join("{0} ({1})".format(value, count) for value, count in sorted_items)


def _render_summary(state):
    """Build the deterministic summary string from `state`.

    Output ends with one trailing newline. Field order is locked by the
    SUMMARY_* tuples above.
    """
    lines = []
    lines.append("## Detection Report Summary")
    lines.append("")
    lines.append("### Workspace")
    for field in SUMMARY_WORKSPACE_FIELDS:
        lines.append(
            "- {0}: {1}".format(field, _render_scalar_for_summary(state.get(field)))
        )
    lines.append("")

    packages = state.get("packages_detected") or []
    pkg_count = len(packages)
    lines.append(
        "### Per-package classification ({0} packages)".format(pkg_count)
    )
    if pkg_count == 0:
        lines.append("- no packages detected")
    else:
        for field in SUMMARY_PER_PACKAGE_FIELDS:
            records = state.get(field) or []
            formatted = _format_value_path_array(records)
            if formatted == "":
                # Field has no records but packages exist — defensive shape
                # the wizard's normal flow doesn't produce, but a partially
                # populated yaml could. Render the bare label so the reader
                # can see the field is present-but-empty.
                lines.append("- {0}:".format(field))
            else:
                lines.append("- {0}: {1}".format(field, formatted))
    lines.append("")

    lines.append("### Project-level classification")
    for field in SUMMARY_PROJECT_FIELDS:
        lines.append(
            "- {0}: {1}".format(field, _render_scalar_for_summary(state.get(field)))
        )

    return "\n".join(lines) + "\n"


def cmd_summary(args):
    """Render the deterministic detection-report summary to stdout.

    Reads `.devforge/detection_report.yaml`. If the file is missing, fails
    with a clear stderr message naming the absent path. If the yaml is
    malformed (cannot be parsed by the closed-shape parser), fails with a
    parse-error message on stderr.
    """
    path = _output_file_path()
    if not path.exists():
        sys.stderr.write(
            "detect_report summary: detection_report.yaml not found at {0}\n".format(
                path
            )
        )
        return 1
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as err:
        sys.stderr.write(
            "detect_report summary: cannot read {0}: {1}\n".format(path, err)
        )
        return 1
    try:
        state = parse_yaml(text)
    except YamlParseError as err:
        sys.stderr.write(
            "detect_report summary: parse error in {0}: {1}\n".format(path, err)
        )
        return 1
    # Backfill any missing fields (forward-compat with FIELD_SCHEMA growth).
    for name, kind in FIELD_SCHEMA:
        if name not in state:
            state[name] = None if kind == "scalar" else []
    sys.stdout.write(_render_summary(state))
    return 0


def cmd_find_nested_git(args):
    """List depth-1 directories under the install root that contain `.git/`.

    The install root is the parent of `.devforge/` (i.e., the directory that
    owns the wizard install). Hidden dirs and the built-in skip list are
    filtered out. One path per line on stdout. No state is written.
    """
    devforge_dir = _output_file_path().parent
    install_root = devforge_dir.parent
    try:
        children = sorted(install_root.iterdir())
    except OSError as err:
        return _die("find-nested-git: cannot list {0}: {1}".format(install_root, err))
    for entry in children:
        if not entry.is_dir():
            continue
        name = entry.name
        if name.startswith("."):
            continue
        if name in NESTED_GIT_SKIP:
            continue
        if (entry / ".git").is_dir():
            sys.stdout.write("{0}\n".format(name))
    return 0


# ---------------------------------------------------------------------------
# CLI wiring.
# ---------------------------------------------------------------------------


def _add_value_or_null_args(parser):
    """Add mutually-exclusive --value / --null to a subparser."""
    parser.add_argument("--path", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--value")
    group.add_argument("--null", action="store_true")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="detect_report",
        description="Compose the Phase 1 Detection Report (legacy /setup-wizard; orphaned).",
    )
    subparsers = parser.add_subparsers(dest="subcommand")

    sp = subparsers.add_parser("reset", help="Write a fresh defaults yaml.")
    sp.set_defaults(func=cmd_reset)

    sp = subparsers.add_parser("set-project-root")
    sp.add_argument("value")
    sp.set_defaults(func=cmd_set_project_root)

    sp = subparsers.add_parser("set-workspace-mode")
    sp.add_argument("value")
    sp.set_defaults(func=cmd_set_workspace_mode)

    sp = subparsers.add_parser("set-project-state")
    sp.add_argument("value")
    sp.set_defaults(func=cmd_set_project_state)

    sp = subparsers.add_parser("set-default-branch")
    sp.add_argument("value")
    sp.set_defaults(func=cmd_set_default_branch)

    sp = subparsers.add_parser("set-primary-language")
    sp.add_argument("value")
    sp.set_defaults(func=cmd_set_primary_language)

    sp = subparsers.add_parser("add-package")
    sp.add_argument("--path", required=True)
    sp.add_argument("--manifest", required=True)
    sp.set_defaults(func=cmd_add_package)

    sp = subparsers.add_parser("add-language")
    sp.add_argument("--path", required=True)
    sp.add_argument("--value", required=True)
    sp.set_defaults(func=cmd_add_language)

    sp = subparsers.add_parser("add-framework")
    _add_value_or_null_args(sp)
    sp.set_defaults(func=cmd_add_framework)

    sp = subparsers.add_parser("add-build-tool")
    _add_value_or_null_args(sp)
    sp.set_defaults(func=cmd_add_build_tool)

    sp = subparsers.add_parser("add-build-command")
    _add_value_or_null_args(sp)
    sp.set_defaults(func=cmd_add_build_command)

    sp = subparsers.add_parser("add-type-check-command")
    _add_value_or_null_args(sp)
    sp.set_defaults(func=cmd_add_type_check_command)

    sp = subparsers.add_parser("add-lint-command")
    _add_value_or_null_args(sp)
    sp.set_defaults(func=cmd_add_lint_command)

    sp = subparsers.add_parser("find-nested-git")
    sp.set_defaults(func=cmd_find_nested_git)

    sp = subparsers.add_parser(
        "summary",
        help="Render a deterministic plain-text summary of the detection report.",
    )
    sp.set_defaults(func=cmd_summary)

    # Library-category setters (7) — value/null mutex + optional --evidence.
    _library_setter_funcs = {
        "set-auth-layer": cmd_set_auth_layer,
        "set-state-management": cmd_set_state_management,
        "set-styling": cmd_set_styling,
        "set-routing": cmd_set_routing,
        "set-validation-library": cmd_set_validation_library,
        "set-error-handling-library": cmd_set_error_handling_library,
        "set-error-handling-pattern": cmd_set_error_handling_pattern,
    }
    for sub_name, func in _library_setter_funcs.items():
        sp = subparsers.add_parser(sub_name)
        group = sp.add_mutually_exclusive_group(required=True)
        group.add_argument("--value")
        group.add_argument("--null", action="store_true")
        sp.add_argument("--evidence")
        sp.set_defaults(func=func)

    # Architecture shape: --value <enum> [--evidence <text>]; no --null.
    sp = subparsers.add_parser("set-architecture-shape")
    sp.add_argument("--value", required=True)
    sp.add_argument("--evidence")
    sp.set_defaults(func=cmd_set_architecture_shape)

    # Runtime URL: two shapes (set vs clear) governed by --null mutex.
    sp = subparsers.add_parser("set-runtime-url")
    group = sp.add_mutually_exclusive_group(required=True)
    group.add_argument("--value")
    group.add_argument("--null", action="store_true")
    sp.add_argument("--source")
    sp.add_argument("--reason")
    sp.set_defaults(func=cmd_set_runtime_url)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "func", None) is None:
        parser.print_help(sys.stderr)
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
