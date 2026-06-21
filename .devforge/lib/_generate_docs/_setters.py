"""Per-package field setters, including package registration.

Every handler here implements the same shape: read state, locate (or
require) the target package record, validate the user-supplied input
field-by-field via `_validation`, mutate, and write state atomically.
The state I/O details and `_die` / `_info` printers come from
`_state` — this module never opens the state file directly so atomic
writes and error formatting stay centralized (Information Expert per
GRASP, anti-pattern #4 stays closed).

Size note: at ~580 lines this module sits in the "plan-a-split" zone
(> 400) per the Design discipline table in `python-engineer.md` and
is approaching the hard 600-line threshold. The cohesion case (all
13 setters share the read-validate-mutate-write idiom) was evaluated
and accepted. Adding the 14th setter is the trigger to split into
per-arity submodules (`_setters_scalar.py` / `_setters_records.py`)
before this file crosses 600.

Inputs are validated AT SET-TIME, not deferred to compose-time
(anti-pattern #2): single-line strings reject every control byte;
enum membership is checked against the schema's allow-tuples; cite
ranges reject malformed `(start, end)` pairs. By the time a value
reaches the state writer it is already known-good.

Idempotency policy:

- `add-package` for an already-registered path is rejected (exit 2)
  rather than silently overwriting a record. This surfaces LLM
  mistakes immediately.
- Single-field setters (`set-package-overview`, etc.) ARE idempotent
  on purpose so the LLM can revise during a fill loop.
- Append-shaped subcommands `add-package-script`, `-export`, and
  `-dep` reject duplicate entries by their natural key (script name,
  export `(name, file, start)` tuple, dep name) — same data goes
  through the call once, not twice.
- `add-package-hazard` ALWAYS appends — no dedup. The same hazard
  observed at two cite locations (or two LLM passes finding the same
  issue worded slightly differently) is legitimately two entries; the
  user reviews and prunes during /generate-docs Phase 4. Verified by
  `AddPackageHazardTests.test_two_hazards_appended`. Concern-tier
  `add-concern-hazard` differs intentionally (see `_setters_concern.py`
  docstring); the asymmetry is documented, not a bug.

Stdlib only. Targets Python 3.8+.
"""

import argparse
from typing import Any, Dict, List, Optional

from generate_docs_schema import (
    DEPENDENCY_KINDS,
    EXPORT_KINDS,
    HAZARD_CATEGORIES,
)

from ._state import (
    StateLoadError,
    _AbortTransaction,
    _die,
    _info,
    _require_package,
    _state_file_path,
    _state_transaction,
    default_package_record,
)
from ._validation import (
    _validate_in_enum,
    _validate_line_range,
    _validate_optional_string,
    _validate_string,
)


# ---------------------------------------------------------------------------
# Subcommand: reset.
# ---------------------------------------------------------------------------


def cmd_reset(args: argparse.Namespace) -> int:
    """Delete the state file if present. Idempotent."""
    path = _state_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            path.unlink()
        except OSError as err:
            return _die(
                "reset: cannot remove {0}: {1}".format(path, err), code=1
            )
        _info("reset: removed {0}".format(path))
    else:
        _info("reset: no state file at {0}".format(path))
    return 0


# ---------------------------------------------------------------------------
# Subcommand: add-package.
# ---------------------------------------------------------------------------


def cmd_add_package(args: argparse.Namespace) -> int:
    try:
        _validate_string(args.path, "add-package --path")
        _validate_string(args.name, "add-package --name")
    except ValueError as err:
        return _die(str(err))
    try:
        with _state_transaction() as state:
            if args.path in state["packages"]:
                raise _AbortTransaction(_die(
                    "package already registered at {0!r}; reset state or "
                    "use a different path".format(args.path)
                ))
            state["packages"][args.path] = default_package_record(
                args.name, args.path,
            )
    except _AbortTransaction as ab:
        return ab.code
    except StateLoadError as err:
        return _die(str(err), code=1)
    except OSError as err:
        return _die("cannot write state: {0}".format(err), code=1)
    _info("add-package {0} at {1}".format(args.name, args.path))
    return 0


# ---------------------------------------------------------------------------
# Per-package scalar setters.
# ---------------------------------------------------------------------------


def _set_package_scalar(
    args: argparse.Namespace,
    field_name: str,
    field_label: str,
    multiline: bool,
    optional: bool,
) -> int:
    """Common path for setters that target a single package-record field.

    `optional=True` allows an empty string to clear the field (-> None),
    used for `framework` / `build_tool`. Required setters reject empty.
    """
    raw = args.text if hasattr(args, "text") else args.value
    if optional and raw == "":
        value: Optional[str] = None
    else:
        try:
            _validate_string(raw, field_label, multiline=multiline)
        except ValueError as err:
            return _die(str(err))
        value = raw
    try:
        with _state_transaction() as state:
            pkg = _require_package(state, args.path)
            if pkg is None:
                raise _AbortTransaction(_die(
                    "package not registered at {0!r}; run add-package "
                    "first".format(args.path)
                ))
            pkg[field_name] = value
    except _AbortTransaction as ab:
        return ab.code
    except StateLoadError as err:
        return _die(str(err), code=1)
    except OSError as err:
        return _die("cannot write state: {0}".format(err), code=1)
    summary = "null" if value is None else "{0} chars".format(len(value))
    _info(
        "{0} at {1} ({2})".format(
            field_label.split(" ")[0], args.path, summary
        )
    )
    return 0


def cmd_set_package_overview(args: argparse.Namespace) -> int:
    return _set_package_scalar(
        args, "overview", "set-package-overview --text",
        multiline=True, optional=False,
    )


def cmd_set_package_tree(args: argparse.Namespace) -> int:
    return _set_package_scalar(
        args, "directory_tree", "set-package-tree --text",
        multiline=True, optional=False,
    )


def cmd_set_package_language(args: argparse.Namespace) -> int:
    return _set_package_scalar(
        args, "primary_language", "set-package-language --value",
        multiline=False, optional=False,
    )


def cmd_set_package_framework(args: argparse.Namespace) -> int:
    return _set_package_scalar(
        args, "framework", "set-package-framework --value",
        multiline=False, optional=True,
    )


def cmd_set_package_build_tool(args: argparse.Namespace) -> int:
    return _set_package_scalar(
        args, "build_tool", "set-package-build-tool --value",
        multiline=False, optional=True,
    )


# ---------------------------------------------------------------------------
# Subcommand: add-package-script.
# ---------------------------------------------------------------------------


def cmd_add_package_script(args: argparse.Namespace) -> int:
    try:
        _validate_string(args.path, "add-package-script --path")
        _validate_string(args.script_name, "add-package-script --script-name")
        _validate_string(args.command, "add-package-script --command")
    except ValueError as err:
        return _die(str(err))
    try:
        with _state_transaction() as state:
            pkg = _require_package(state, args.path)
            if pkg is None:
                raise _AbortTransaction(_die(
                    "package not registered at {0!r}; run add-package "
                    "first".format(args.path)
                ))
            if args.script_name in pkg["scripts"]:
                raise _AbortTransaction(_die(
                    "script {0!r} already registered at {1}; use a "
                    "different name or reset".format(
                        args.script_name, args.path,
                    )
                ))
            pkg["scripts"][args.script_name] = args.command
    except _AbortTransaction as ab:
        return ab.code
    except StateLoadError as err:
        return _die(str(err), code=1)
    except OSError as err:
        return _die("cannot write state: {0}".format(err), code=1)
    _info("add-package-script {0} at {1}".format(args.script_name, args.path))
    return 0


# ---------------------------------------------------------------------------
# Subcommand: add-package-export.
# ---------------------------------------------------------------------------


def cmd_add_package_export(args: argparse.Namespace) -> int:
    try:
        _validate_string(args.path, "add-package-export --path")
        _validate_string(args.name, "add-package-export --name")
        _validate_string(args.kind, "add-package-export --kind")
        _validate_in_enum(args.kind, EXPORT_KINDS, "add-package-export --kind")
        # Signature is optional — empty string -> None.
        signature = _validate_optional_string(
            args.signature, "add-package-export --signature"
        )
        _validate_string(
            args.description, "add-package-export --description",
            multiline=True,
        )
        _validate_string(args.language, "add-package-export --language")
        _validate_string(
            args.code_snippet, "add-package-export --code-snippet",
            multiline=True,
        )
        _validate_string(args.cite_file, "add-package-export --cite-file")
        _validate_line_range(
            args.cite_start, args.cite_end, "add-package-export cite"
        )
    except ValueError as err:
        return _die(str(err))
    try:
        with _state_transaction() as state:
            pkg = _require_package(state, args.path)
            if pkg is None:
                raise _AbortTransaction(_die(
                    "package not registered at {0!r}; run add-package "
                    "first".format(args.path)
                ))
            # Idempotency: reject a re-registration with the SAME
            # (name, file, start) tuple. Same name with a different cite
            # is allowed (overloads / multiple definitions in different
            # files).
            for existing in pkg["exports"]:
                if (
                    existing["name"] == args.name
                    and existing["code"]["cite"]["file"] == args.cite_file
                    and existing["code"]["cite"]["start"] == args.cite_start
                ):
                    raise _AbortTransaction(_die(
                        "export {0!r} at {1}:{2} already registered; use "
                        "a different name or different cite".format(
                            args.name, args.cite_file, args.cite_start,
                        )
                    ))
            pkg["exports"].append(
                {
                    "name": args.name,
                    "kind": args.kind,
                    "signature": signature,
                    "description": args.description,
                    "code": {
                        "language": args.language,
                        "snippet": args.code_snippet,
                        "cite": {
                            "file": args.cite_file,
                            "start": args.cite_start,
                            "end": args.cite_end,
                        },
                    },
                }
            )
    except _AbortTransaction as ab:
        return ab.code
    except StateLoadError as err:
        return _die(str(err), code=1)
    except OSError as err:
        return _die("cannot write state: {0}".format(err), code=1)
    _info(
        "add-package-export {0} at {1} (cite={2}:{3}-{4})".format(
            args.name, args.path, args.cite_file, args.cite_start, args.cite_end
        )
    )
    return 0


# ---------------------------------------------------------------------------
# Subcommand: add-package-dep.
# ---------------------------------------------------------------------------


def cmd_add_package_dep(args: argparse.Namespace) -> int:
    try:
        _validate_string(args.path, "add-package-dep --path")
        _validate_string(args.name, "add-package-dep --name")
        _validate_string(args.kind, "add-package-dep --kind")
        _validate_in_enum(args.kind, DEPENDENCY_KINDS, "add-package-dep --kind")
        version = _validate_optional_string(
            args.version, "add-package-dep --version"
        )
        _validate_string(
            args.purpose, "add-package-dep --purpose", multiline=True
        )
        consumer_locations: List[str] = []
        for idx, loc in enumerate(args.consumer_location or []):
            _validate_string(
                loc,
                "add-package-dep --consumer-location[{0}]".format(idx),
            )
            consumer_locations.append(loc)
    except ValueError as err:
        return _die(str(err))
    try:
        with _state_transaction() as state:
            pkg = _require_package(state, args.path)
            if pkg is None:
                raise _AbortTransaction(_die(
                    "package not registered at {0!r}; run add-package "
                    "first".format(args.path)
                ))
            for existing in pkg["dependencies"]:
                if existing["name"] == args.name:
                    raise _AbortTransaction(_die(
                        "dependency {0!r} already registered at {1}; use "
                        "a different name or reset".format(
                            args.name, args.path,
                        )
                    ))
            pkg["dependencies"].append(
                {
                    "name": args.name,
                    "kind": args.kind,
                    "version": version,
                    "purpose": args.purpose,
                    "consumer_locations": consumer_locations,
                }
            )
    except _AbortTransaction as ab:
        return ab.code
    except StateLoadError as err:
        return _die(str(err), code=1)
    except OSError as err:
        return _die("cannot write state: {0}".format(err), code=1)
    _info(
        "add-package-dep {0} at {1} (kind={2})".format(
            args.name, args.path, args.kind
        )
    )
    return 0


# ---------------------------------------------------------------------------
# Subcommand: add-package-hazard.
# ---------------------------------------------------------------------------


def cmd_add_package_hazard(args: argparse.Namespace) -> int:
    try:
        _validate_string(args.path, "add-package-hazard --path")
        _validate_string(args.category, "add-package-hazard --category")
        _validate_in_enum(
            args.category, HAZARD_CATEGORIES, "add-package-hazard --category"
        )
        _validate_string(
            args.description, "add-package-hazard --description",
            multiline=True,
        )
    except ValueError as err:
        return _die(str(err))
    cite_present = (
        args.cite_file is not None
        or args.cite_start is not None
        or args.cite_end is not None
    )
    cite_complete = (
        args.cite_file is not None
        and args.cite_start is not None
        and args.cite_end is not None
    )
    if cite_present and not cite_complete:
        return _die(
            "hazard cite requires --cite-file + --cite-start + --cite-end "
            "together, or none"
        )
    cite: Optional[Dict[str, Any]] = None
    if cite_complete:
        try:
            _validate_string(
                args.cite_file, "add-package-hazard --cite-file"
            )
            _validate_line_range(
                args.cite_start, args.cite_end, "add-package-hazard cite"
            )
        except ValueError as err:
            return _die(str(err))
        cite = {
            "file": args.cite_file,
            "start": args.cite_start,
            "end": args.cite_end,
        }
    try:
        with _state_transaction() as state:
            pkg = _require_package(state, args.path)
            if pkg is None:
                raise _AbortTransaction(_die(
                    "package not registered at {0!r}; run add-package "
                    "first".format(args.path)
                ))
            pkg["hazards"].append(
                {
                    "category": args.category,
                    "description": args.description,
                    "cite": cite,
                }
            )
    except _AbortTransaction as ab:
        return ab.code
    except StateLoadError as err:
        return _die(str(err), code=1)
    except OSError as err:
        return _die("cannot write state: {0}".format(err), code=1)
    _info(
        "add-package-hazard {0} at {1}".format(args.category, args.path)
    )
    return 0


# ---------------------------------------------------------------------------
# Subcommand: set-package-usage-example.
# ---------------------------------------------------------------------------


def cmd_set_package_usage_example(args: argparse.Namespace) -> int:
    try:
        _validate_string(args.path, "set-package-usage-example --path")
        _validate_string(
            args.language, "set-package-usage-example --language"
        )
        _validate_string(
            args.code_snippet,
            "set-package-usage-example --code-snippet",
            multiline=True,
        )
        _validate_string(
            args.cite_file, "set-package-usage-example --cite-file"
        )
        _validate_line_range(
            args.cite_start, args.cite_end,
            "set-package-usage-example cite",
        )
    except ValueError as err:
        return _die(str(err))
    try:
        with _state_transaction() as state:
            pkg = _require_package(state, args.path)
            if pkg is None:
                raise _AbortTransaction(_die(
                    "package not registered at {0!r}; run add-package "
                    "first".format(args.path)
                ))
            pkg["usage_example"] = {
                "language": args.language,
                "snippet": args.code_snippet,
                "cite": {
                    "file": args.cite_file,
                    "start": args.cite_start,
                    "end": args.cite_end,
                },
            }
    except _AbortTransaction as ab:
        return ab.code
    except StateLoadError as err:
        return _die(str(err), code=1)
    except OSError as err:
        return _die("cannot write state: {0}".format(err), code=1)
    _info(
        "set-package-usage-example at {0} (cite={1}:{2}-{3})".format(
            args.path, args.cite_file, args.cite_start, args.cite_end
        )
    )
    return 0


# ---------------------------------------------------------------------------
# Subcommand: set-package-consumer-pattern.
#
# Mirrors `set-package-usage-example` exactly — same CodeBlock shape,
# same validation, same overwrite policy. The two subcommands target
# different fields of the same package record (`usage_example` vs
# `consumer_pattern`); the registered code is otherwise indistinguishable.
# ---------------------------------------------------------------------------


def cmd_set_package_consumer_pattern(args: argparse.Namespace) -> int:
    try:
        _validate_string(args.path, "set-package-consumer-pattern --path")
        _validate_string(
            args.language, "set-package-consumer-pattern --language"
        )
        _validate_string(
            args.code_snippet,
            "set-package-consumer-pattern --code-snippet",
            multiline=True,
        )
        _validate_string(
            args.cite_file, "set-package-consumer-pattern --cite-file"
        )
        _validate_line_range(
            args.cite_start, args.cite_end,
            "set-package-consumer-pattern cite",
        )
    except ValueError as err:
        return _die(str(err))
    try:
        with _state_transaction() as state:
            pkg = _require_package(state, args.path)
            if pkg is None:
                raise _AbortTransaction(_die(
                    "package not registered at {0!r}; run add-package "
                    "first".format(args.path)
                ))
            pkg["consumer_pattern"] = {
                "language": args.language,
                "snippet": args.code_snippet,
                "cite": {
                    "file": args.cite_file,
                    "start": args.cite_start,
                    "end": args.cite_end,
                },
            }
    except _AbortTransaction as ab:
        return ab.code
    except StateLoadError as err:
        return _die(str(err), code=1)
    except OSError as err:
        return _die("cannot write state: {0}".format(err), code=1)
    _info(
        "set-package-consumer-pattern at {0} (cite={1}:{2}-{3})".format(
            args.path, args.cite_file, args.cite_start, args.cite_end
        )
    )
    return 0
