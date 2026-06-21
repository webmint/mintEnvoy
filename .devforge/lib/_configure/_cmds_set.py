"""All cmd_set_* handlers + cmd_reset + cmd_add_package_stack + cmd_set_package_stacks."""

from __future__ import annotations

import argparse
import json
import sys

from ._schema import _PACKAGE_STACK_FIELDS as _SCHEMA_PACKAGE_STACK_FIELDS
from ._state import _state_transaction, _write_state, _output_file_path, default_state
from ._validators import (
    _die,
    _validate_enum,
    _validate_path_value,
    _validate_scalar,
    _validate_string_array,
    _validate_verbatim,
)
from ._yaml import YamlParseError


# ---------------------------------------------------------------------------
# Identity scalar setters (3).
# ---------------------------------------------------------------------------


def cmd_set_project_name(args: argparse.Namespace) -> int:
    """Set project_name scalar."""
    try:
        value = _validate_scalar(args.value, "project_name")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["project_name"] = value
    except (OSError, YamlParseError) as err:
        return _die("set-project-name: {0}".format(err))
    return 0


def cmd_set_project_description(args: argparse.Namespace) -> int:
    """Set project_description scalar."""
    try:
        value = _validate_scalar(args.value, "project_description")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["project_description"] = value
    except (OSError, YamlParseError) as err:
        return _die("set-project-description: {0}".format(err))
    return 0


def cmd_set_project_type(args: argparse.Namespace) -> int:
    """Set project_type scalar."""
    try:
        value = _validate_scalar(args.value, "project_type")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["project_type"] = value
    except (OSError, YamlParseError) as err:
        return _die("set-project-type: {0}".format(err))
    return 0


# ---------------------------------------------------------------------------
# Stack scalar setter (1).
# ---------------------------------------------------------------------------


def cmd_set_primary_language(args: argparse.Namespace) -> int:
    """Set primary_language scalar."""
    try:
        value = _validate_scalar(args.value, "primary_language")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["primary_language"] = value
    except (OSError, YamlParseError) as err:
        return _die("set-primary-language: {0}".format(err))
    return 0


# ---------------------------------------------------------------------------
# Stack string_array setters (7).
# ---------------------------------------------------------------------------


def _cmd_set_string_array(args: argparse.Namespace, field_name: str) -> int:
    """Shared implementation for string_array setters (replace semantics)."""
    try:
        items = _validate_string_array(args.value, field_name)
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state[field_name] = items
    except (OSError, YamlParseError) as err:
        return _die("set-{0}: {1}".format(field_name.replace("_", "-"), err))
    return 0


def cmd_set_languages(args: argparse.Namespace) -> int:
    """Set languages string_array (comma-sep; replaces prior value)."""
    return _cmd_set_string_array(args, "languages")


def cmd_set_frameworks(args: argparse.Namespace) -> int:
    """Set frameworks string_array (comma-sep; replaces prior value)."""
    return _cmd_set_string_array(args, "frameworks")


def cmd_set_architectures(args: argparse.Namespace) -> int:
    """Set architectures string_array (comma-sep; replaces prior value)."""
    return _cmd_set_string_array(args, "architectures")


def cmd_set_project_natures(args: argparse.Namespace) -> int:
    """Set project_natures string_array (comma-sep; replaces prior value).

    Accepts any non-empty atomic nature strings (no enum restriction —
    LLM Phase 2 derives from PROJECT_TYPE + FRAMEWORKS; users may name
    custom natures). Advisory vocabulary: web, backend, mobile, desktop,
    cli, library, plugin, data, ml, game, infra, docs.
    """
    return _cmd_set_string_array(args, "project_natures")


def cmd_set_error_handlings(args: argparse.Namespace) -> int:
    """Set error_handlings string_array (comma-sep; replaces prior value)."""
    return _cmd_set_string_array(args, "error_handlings")


def cmd_set_api_layers(args: argparse.Namespace) -> int:
    """Set api_layers string_array (comma-sep; replaces prior value)."""
    return _cmd_set_string_array(args, "api_layers")


def cmd_set_testings(args: argparse.Namespace) -> int:
    """Set testings string_array (comma-sep; replaces prior value)."""
    return _cmd_set_string_array(args, "testings")


def cmd_set_build_tools(args: argparse.Namespace) -> int:
    """Set build_tools string_array (comma-sep; replaces prior value)."""
    return _cmd_set_string_array(args, "build_tools")


# ---------------------------------------------------------------------------
# Per-package string_array setters (4).
# ---------------------------------------------------------------------------


def cmd_set_build_commands(args: argparse.Namespace) -> int:
    """Set build_commands string_array (comma-sep; replaces prior value)."""
    return _cmd_set_string_array(args, "build_commands")


def cmd_set_type_check_commands(args: argparse.Namespace) -> int:
    """Set type_check_commands string_array (comma-sep; replaces prior value)."""
    return _cmd_set_string_array(args, "type_check_commands")


def cmd_set_lint_commands(args: argparse.Namespace) -> int:
    """Set lint_commands string_array (comma-sep; replaces prior value)."""
    return _cmd_set_string_array(args, "lint_commands")


def cmd_set_test_commands(args: argparse.Namespace) -> int:
    """Set test_commands string_array (comma-sep; replaces prior value)."""
    return _cmd_set_string_array(args, "test_commands")


# ---------------------------------------------------------------------------
# Per-package record append setter (1).
# ---------------------------------------------------------------------------


def cmd_add_package_stack(args: argparse.Namespace) -> int:
    """Append one package_stack record. --path and --language are required.

    All other fields default to None when absent. Uses _state_transaction
    for cross-process safety: concurrent invocations serialize via flock
    so no append is silently lost.
    """
    try:
        path_val = _validate_path_value(args.path, "path")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        lang_val = _validate_scalar(args.language, "language")
    except ValueError as err:
        return _die(str(err), code=2)

    # Optional fields: validate only if provided.
    optional = {}
    for attr, field in (
        ("framework", "framework"),
        ("build_tool", "build_tool"),
        ("build_command", "build_command"),
        ("type_check_command", "type_check_command"),
        ("lint_command", "lint_command"),
        ("test_command", "test_command"),
    ):
        raw = getattr(args, attr, None)
        if raw is not None:
            try:
                optional[field] = _validate_scalar(raw, field)
            except ValueError as err:
                return _die(str(err), code=2)
        else:
            optional[field] = None

    record = {
        "path": path_val,
        "language": lang_val,
        "framework": optional["framework"],
        "build_tool": optional["build_tool"],
        "build_command": optional["build_command"],
        "type_check_command": optional["type_check_command"],
        "lint_command": optional["lint_command"],
        "test_command": optional["test_command"],
    }

    try:
        with _state_transaction(args.devforge_dir) as state:
            state["package_stacks"].append(record)
    except (OSError, YamlParseError) as err:
        return _die("add-package-stack: {0}".format(err))
    return 0


# ---------------------------------------------------------------------------
# Per-package record bulk replace setter (1).
# ---------------------------------------------------------------------------

# Derived from _schema._PACKAGE_STACK_FIELDS — _schema.py is the single source
# of truth for field names and order.  Adding a 9th field to the schema tuple
# flows through automatically to both constants below; no manual update needed.

# Frozenset of all 8 known field names — used for O(1) set-subtraction to reject
# unknown keys at record-validation time.
_PACKAGE_STACK_FIELDS = frozenset(_SCHEMA_PACKAGE_STACK_FIELDS)

# Tuple (ordered) of the 6 optional field names — all schema fields except the
# two required ones (path, language).  Iterated in schema declaration order to
# build the normalized record dict with a stable, deterministic field layout.
_OPTIONAL_PACKAGE_STACK_FIELDS = tuple(
    f for f in _SCHEMA_PACKAGE_STACK_FIELDS if f not in ("path", "language")
)


def cmd_set_package_stacks(args: argparse.Namespace) -> int:
    """Replace the whole package_stacks list from JSON on stdin.

    Reads a JSON object with a single key ``package_stacks`` whose value
    is a list of record objects.  Each record must be a dict with the
    same 8-field schema as ``cmd_add_package_stack`` writes:

      path (required), language (required), framework, build_tool,
      build_command, type_check_command, lint_command, test_command
      (these 6 optional, null/None allowed).

    **Replace semantics**: the whole ``package_stacks`` list in state is
    replaced atomically — NOT appended.  An empty input list is valid and
    sets ``package_stacks`` to ``[]``.

    Validation: unknown keys are rejected (exit 2) — that is the whole
    point of the verb: the bash loop that triggered the column-shift bug
    bypassed exactly this check.

    Exit 0 on success.  Exit 2 on any validation or parse error.
    Exit 1 on I/O error.
    """
    raw = sys.stdin.read()

    # --- JSON parse ---
    try:
        payload = json.loads(raw)
    except ValueError as err:
        return _die("set-package-stacks: malformed JSON on stdin: {0}".format(err), code=2)

    if not isinstance(payload, dict):
        return _die(
            "set-package-stacks: stdin must be a JSON object, got {0}".format(
                type(payload).__name__
            ),
            code=2,
        )

    if "package_stacks" not in payload:
        return _die(
            "set-package-stacks: stdin JSON object must have a 'package_stacks' key",
            code=2,
        )

    records_raw = payload["package_stacks"]
    if not isinstance(records_raw, list):
        return _die(
            "set-package-stacks: 'package_stacks' must be a list, got {0}".format(
                type(records_raw).__name__
            ),
            code=2,
        )

    # --- Per-record validation + normalization ---
    normalized_records = []
    for idx, rec in enumerate(records_raw):
        if not isinstance(rec, dict):
            return _die(
                "set-package-stacks: record {0} is not an object".format(idx),
                code=2,
            )

        unknown = set(rec.keys()) - _PACKAGE_STACK_FIELDS
        if unknown:
            bad_key = sorted(unknown)[0]
            return _die(
                "set-package-stacks: record {0} has unknown key {1!r}".format(idx, bad_key),
                code=2,
            )

        # Required: path
        if "path" not in rec or rec["path"] is None:
            return _die(
                "set-package-stacks: record {0} missing required field 'path'".format(idx),
                code=2,
            )
        if not isinstance(rec["path"], str):
            return _die(
                "set-package-stacks: record {0}: 'path' must be a string, got {1}".format(
                    idx, type(rec["path"]).__name__
                ),
                code=2,
            )
        try:
            path_val = _validate_path_value(rec["path"], "path")
        except ValueError as err:
            return _die(
                "set-package-stacks: record {0}: {1}".format(idx, err),
                code=2,
            )

        # Required: language
        if "language" not in rec or rec["language"] is None:
            return _die(
                "set-package-stacks: record {0} missing required field 'language'".format(idx),
                code=2,
            )
        if not isinstance(rec["language"], str):
            return _die(
                "set-package-stacks: record {0}: 'language' must be a string, got {1}".format(
                    idx, type(rec["language"]).__name__
                ),
                code=2,
            )
        try:
            lang_val = _validate_scalar(rec["language"], "language")
        except ValueError as err:
            return _die(
                "set-package-stacks: record {0}: {1}".format(idx, err),
                code=2,
            )

        # Optional fields: validate when present and not null.
        optional = {}
        for field in _OPTIONAL_PACKAGE_STACK_FIELDS:
            raw_val = rec.get(field, None)
            if raw_val is not None:
                if not isinstance(raw_val, str):
                    return _die(
                        "set-package-stacks: record {0}: '{1}' must be a string, got {2}".format(
                            idx, field, type(raw_val).__name__
                        ),
                        code=2,
                    )
                try:
                    optional[field] = _validate_scalar(raw_val, field)
                except ValueError as err:
                    return _die(
                        "set-package-stacks: record {0}: {1}".format(idx, err),
                        code=2,
                    )
            else:
                optional[field] = None

        normalized_records.append({
            "path": path_val,
            "language": lang_val,
            "framework": optional["framework"],
            "build_tool": optional["build_tool"],
            "build_command": optional["build_command"],
            "type_check_command": optional["type_check_command"],
            "lint_command": optional["lint_command"],
            "test_command": optional["test_command"],
        })

    # --- Atomic replace ---
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["package_stacks"] = normalized_records
    except (OSError, YamlParseError) as err:
        return _die("set-package-stacks: {0}".format(err))
    return 0


# ---------------------------------------------------------------------------
# Verbatim docs scalar setters (3).
# ---------------------------------------------------------------------------


def cmd_set_project_structure(args: argparse.Namespace) -> int:
    """Set project_structure verbatim scalar (multi-line via --text flag)."""
    try:
        value = _validate_verbatim(args.text, "project_structure")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["project_structure"] = value
    except (OSError, YamlParseError) as err:
        return _die("set-project-structure: {0}".format(err))
    return 0


def cmd_set_dev_commands(args: argparse.Namespace) -> int:
    """Set dev_commands verbatim scalar (multi-line via --text flag)."""
    try:
        value = _validate_verbatim(args.text, "dev_commands")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["dev_commands"] = value
    except (OSError, YamlParseError) as err:
        return _die("set-dev-commands: {0}".format(err))
    return 0


def cmd_set_architecture_details(args: argparse.Namespace) -> int:
    """Set architecture_details verbatim scalar (multi-line via --text flag)."""
    try:
        value = _validate_verbatim(args.text, "architecture_details")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["architecture_details"] = value
    except (OSError, YamlParseError) as err:
        return _die("set-architecture-details: {0}".format(err))
    return 0


# ---------------------------------------------------------------------------
# Enum scalar setters (6).
# ---------------------------------------------------------------------------


def _cmd_set_enum(args: argparse.Namespace, field_name: str) -> int:
    """Shared implementation for enum scalar setters."""
    try:
        value = _validate_enum(args.value, field_name)
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state[field_name] = value
    except (OSError, YamlParseError) as err:
        return _die("set-{0}: {1}".format(field_name.replace("_", "-"), err))
    return 0


def cmd_set_workflow_enforcement(args: argparse.Namespace) -> int:
    """Set workflow_enforcement enum scalar (Strict | Moderate | Light)."""
    return _cmd_set_enum(args, "workflow_enforcement")


def cmd_set_ai_attribution(args: argparse.Namespace) -> int:
    """Set ai_attribution enum scalar (Yes | No)."""
    return _cmd_set_enum(args, "ai_attribution")


def _cmd_set_claude_tier(args: argparse.Namespace, field_name: str) -> int:
    """Shared implementation for claude_tier_* setters.

    These fields are NOT enum-restricted (see ENUM_FIELDS comment) — they
    accept any non-empty scalar so users can name custom Claude routes
    via Q11's `Other` branch.
    """
    try:
        value = _validate_scalar(args.value, field_name)
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state[field_name] = value
    except (OSError, YamlParseError) as err:
        return _die("set-{0}: {1}".format(field_name.replace("_", "-"), err))
    return 0


def cmd_set_claude_tier_think(args: argparse.Namespace) -> int:
    """Set claude_tier_think (free-text scalar; Opus/Sonnet/Haiku recommended)."""
    return _cmd_set_claude_tier(args, "claude_tier_think")


def cmd_set_claude_tier_do(args: argparse.Namespace) -> int:
    """Set claude_tier_do (free-text scalar; Opus/Sonnet/Haiku recommended)."""
    return _cmd_set_claude_tier(args, "claude_tier_do")


def cmd_set_claude_tier_verify(args: argparse.Namespace) -> int:
    """Set claude_tier_verify (free-text scalar; Opus/Sonnet/Haiku recommended)."""
    return _cmd_set_claude_tier(args, "claude_tier_verify")


def cmd_set_ac_verification_mode(args: argparse.Namespace) -> int:
    """Set ac_verification_mode enum scalar (code-only | tests | runtime-assisted | off)."""
    return _cmd_set_enum(args, "ac_verification_mode")


# ---------------------------------------------------------------------------
# AC runtime scalar setters (3).
# ---------------------------------------------------------------------------


def cmd_set_ac_runtime_url(args: argparse.Namespace) -> int:
    """Set ac_runtime_url scalar."""
    try:
        value = _validate_scalar(args.value, "ac_runtime_url")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["ac_runtime_url"] = value
    except (OSError, YamlParseError) as err:
        return _die("set-ac-runtime-url: {0}".format(err))
    return 0


def cmd_set_ac_runtime_api_base(args: argparse.Namespace) -> int:
    """Set ac_runtime_api_base scalar."""
    try:
        value = _validate_scalar(args.value, "ac_runtime_api_base")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["ac_runtime_api_base"] = value
    except (OSError, YamlParseError) as err:
        return _die("set-ac-runtime-api-base: {0}".format(err))
    return 0


def cmd_set_ac_runtime_cli_command(args: argparse.Namespace) -> int:
    """Set ac_runtime_cli_command scalar."""
    try:
        value = _validate_scalar(args.value, "ac_runtime_cli_command")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["ac_runtime_cli_command"] = value
    except (OSError, YamlParseError) as err:
        return _die("set-ac-runtime-cli-command: {0}".format(err))
    return 0


def cmd_reset(args: argparse.Namespace) -> int:
    """Write a fresh defaults yaml. Idempotent: byte-identical on re-run."""
    try:
        _write_state(default_state(), args.devforge_dir)
    except OSError as err:
        return _die(
            "reset: cannot write {0}: {1}".format(
                _output_file_path(args.devforge_dir), err
            )
        )
    return 0
