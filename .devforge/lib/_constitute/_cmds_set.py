"""Setter handlers: cmd_reset + 10 cmd_set_* / cmd_add_* setters."""

from __future__ import annotations

import argparse
import json
import re

from ._schema import ENUM_FIELDS, _PATTERN_SCOPE_TO_SUFFIX, _SECTION_BUCKET_TO_KEY
from ._state import (
    _empty_section,
    _find_section,
    _load,
    _state_transaction,
    _write_state,
    default_state,
)
from ._validators import (
    _die,
    _validate_enum,
    _validate_path_value,
    _validate_scalar,
    _validate_string_array,
    _validate_verbatim,
)


def cmd_reset(args: argparse.Namespace) -> int:
    """Write a fresh defaults state file. Idempotent: byte-identical re-runs."""
    _write_state(default_state(), args.devforge_dir)
    return 0


def cmd_set_project_name(args: argparse.Namespace) -> int:
    """Set project_name scalar."""
    try:
        value = _validate_scalar(args.value, "project_name")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["project_name"] = value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-project-name: {0}".format(err))
    return 0


def cmd_set_mode(args: argparse.Namespace) -> int:
    """Set mode enum (existing-codebase | greenfield)."""
    try:
        value = _validate_enum(args.value, "mode", ENUM_FIELDS["mode"])
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["mode"] = value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-mode: {0}".format(err))
    return 0


def cmd_set_dates(args: argparse.Namespace) -> int:
    """Set generated_date and last_updated (both YYYY-MM-DD)."""
    date_re = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    for date_value, field_name in (
        (args.generated, "generated_date"),
        (args.updated, "last_updated"),
    ):
        if not date_re.match(date_value):
            return _die(
                "{0}: invalid date format {1!r}; expected YYYY-MM-DD".format(
                    field_name, date_value
                ),
                code=2,
            )
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["generated_date"] = args.generated
            state["last_updated"] = args.updated
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-dates: {0}".format(err))
    return 0


def cmd_set_project_identity(args: argparse.Namespace) -> int:
    """Set project_identity record (name, type, domain, stack). Replaces prior value."""
    try:
        name = _validate_scalar(args.name, "project_identity.name")
        ptype = _validate_scalar(args.type, "project_identity.type")
        domain = _validate_scalar(args.domain, "project_identity.domain")
        stack = _validate_scalar(args.stack, "project_identity.stack")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["project_identity"] = {
                "name": name,
                "type": ptype,
                "domain": domain,
                "stack": stack,
            }
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-project-identity: {0}".format(err))
    return 0


def cmd_add_section(args: argparse.Namespace) -> int:
    """Append (or replace-metadata-of) a Section in the given bucket.

    Idempotent on (bucket, number): second call with same (bucket, number)
    replaces the section's metadata while preserving its rules/tables/
    code_examples. Idempotency is bucket-local — same number in a different
    bucket creates a phantom duplicate that downstream add-rule will never
    reach (per _find_section's first-match policy). Phase 5 spec convention
    avoids this by numbering each bucket non-overlappingly.
    """
    bucket_arg = args.bucket
    if bucket_arg not in _SECTION_BUCKET_TO_KEY:
        return _die(
            "add-section: unknown bucket {0!r}; allowed: {1}".format(
                bucket_arg, sorted(_SECTION_BUCKET_TO_KEY.keys())
            ),
            code=2,
        )
    bucket_key = _SECTION_BUCKET_TO_KEY[bucket_arg]

    number = args.number
    if not re.match(r"^\d+(\.\d+)*$", number):
        return _die(
            "add-section: invalid section number {0!r}; expected format like '2', '2.1', '5.3.1'".format(number),
            code=2,
        )

    try:
        title = _validate_scalar(args.title, "section.title")
    except ValueError as err:
        return _die(str(err), code=2)

    tag = None
    if args.tag is not None:
        try:
            tag = _validate_enum(args.tag, "section_tag", ENUM_FIELDS["section_tag"])
        except ValueError as err:
            return _die(str(err), code=2)

    description = args.description  # Optional; no validation beyond presence.

    try:
        with _state_transaction(args.devforge_dir) as state:
            bucket = state[bucket_key]
            for existing in bucket:
                if existing.get("number") == number:
                    existing["title"] = title
                    existing["tag"] = tag
                    existing["description"] = description
                    break
            else:
                section = _empty_section()
                section["number"] = number
                section["title"] = title
                section["tag"] = tag
                section["description"] = description
                bucket.append(section)
    except (OSError, json.JSONDecodeError) as err:
        return _die("add-section: {0}".format(err))
    return 0


def cmd_add_rule(args: argparse.Namespace) -> int:
    """Append a rule to the section identified by --section number."""
    try:
        tag = _validate_enum(args.tag, "rule_tag", ENUM_FIELDS["rule_tag"])
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        text = _validate_verbatim(args.text, "rule.text")
    except ValueError as err:
        return _die(str(err), code=2)

    # Pre-check section exists (read-only — no lock). Avoids entering the
    # _state_transaction on a guaranteed-fail path; `return` inside the
    # with-block would still trigger _dump and silently re-write identical
    # state, breaking the transaction's "NOT written if body raises" contract.
    try:
        prev_state = _load(args.devforge_dir)
    except (OSError, ValueError) as err:
        return _die("add-rule: {0}".format(err))
    if _find_section(prev_state, args.section)[1] is None:
        return _die(
            "add-rule: section {0!r} not found; run add-section first".format(
                args.section
            ),
            code=2,
        )

    try:
        with _state_transaction(args.devforge_dir) as state:
            _bucket, section = _find_section(state, args.section)
            assert section is not None, (
                "add-rule: section {0!r} disappeared between check and lock".format(
                    args.section
                )
            )
            section["rules"].append({"tag": tag, "text": text})
    except (OSError, json.JSONDecodeError) as err:
        return _die("add-rule: {0}".format(err))
    return 0


def cmd_add_table(args: argparse.Namespace) -> int:
    """Append a table to the section identified by --section number."""
    try:
        columns = _validate_string_array(args.columns, "table.columns")
    except ValueError as err:
        return _die(str(err), code=2)

    try:
        rows_raw = json.loads(args.rows_json)
    except ValueError as err:
        return _die(
            "add-table: --rows-json is malformed JSON: {0}".format(err), code=2
        )
    if not isinstance(rows_raw, list):
        return _die(
            "add-table: --rows-json must be a JSON array of arrays, got {0}".format(
                type(rows_raw).__name__
            ),
            code=2,
        )
    rows = []  # type: list
    for i, row in enumerate(rows_raw):
        if not isinstance(row, list):
            return _die(
                "add-table: row {0} must be a JSON array, got {1}".format(
                    i, type(row).__name__
                ),
                code=2,
            )
        if len(row) != len(columns):
            return _die(
                "add-table: row {0} has {1} cells but table has {2} columns".format(
                    i, len(row), len(columns)
                ),
                code=2,
            )
        row_strs = []
        for j, cell in enumerate(row):
            if not isinstance(cell, str):
                return _die(
                    "add-table: row {0} cell {1} must be a string, got {2}".format(
                        i, j, type(cell).__name__
                    ),
                    code=2,
                )
            row_strs.append(cell)
        rows.append(row_strs)

    try:
        prev_state = _load(args.devforge_dir)
    except (OSError, ValueError) as err:
        return _die("add-table: {0}".format(err))
    if _find_section(prev_state, args.section)[1] is None:
        return _die(
            "add-table: section {0!r} not found; run add-section first".format(
                args.section
            ),
            code=2,
        )

    try:
        with _state_transaction(args.devforge_dir) as state:
            _bucket, section = _find_section(state, args.section)
            assert section is not None, (
                "add-table: section {0!r} disappeared between check and lock".format(
                    args.section
                )
            )
            section["tables"].append({"columns": columns, "rows": rows})
    except (OSError, json.JSONDecodeError) as err:
        return _die("add-table: {0}".format(err))
    return 0


def cmd_add_code_example(args: argparse.Namespace) -> int:
    """Append a code example to the section identified by --section number."""
    try:
        label = _validate_enum(args.label, "code_label", ENUM_FIELDS["code_label"])
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        language = _validate_scalar(args.language, "code_example.language")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        code = _validate_verbatim(args.code, "code_example.code")
    except ValueError as err:
        return _die(str(err), code=2)
    annotation = args.annotation  # Optional; no validation.

    try:
        prev_state = _load(args.devforge_dir)
    except (OSError, ValueError) as err:
        return _die("add-code-example: {0}".format(err))
    if _find_section(prev_state, args.section)[1] is None:
        return _die(
            "add-code-example: section {0!r} not found; run add-section first".format(
                args.section
            ),
            code=2,
        )

    try:
        with _state_transaction(args.devforge_dir) as state:
            _bucket, section = _find_section(state, args.section)
            assert section is not None, (
                "add-code-example: section {0!r} disappeared between check and lock".format(
                    args.section
                )
            )
            section["code_examples"].append({
                "label": label,
                "language": language,
                "code": code,
                "annotation": annotation,
            })
    except (OSError, json.JSONDecodeError) as err:
        return _die("add-code-example: {0}".format(err))
    return 0


def cmd_add_pattern_rule(args: argparse.Namespace) -> int:
    """Append a rule to a patterns_and_antipatterns bucket."""
    allowed_buckets = {"always", "never", "prefer"}
    if args.bucket not in allowed_buckets:
        return _die(
            "add-pattern-rule: unknown bucket {0!r}; allowed: {1}".format(
                args.bucket, sorted(allowed_buckets)
            ),
            code=2,
        )
    if args.scope not in _PATTERN_SCOPE_TO_SUFFIX:
        return _die(
            "add-pattern-rule: unknown scope {0!r}; allowed: {1}".format(
                args.scope, sorted(_PATTERN_SCOPE_TO_SUFFIX.keys())
            ),
            code=2,
        )
    pattern_key = "{0}_{1}".format(args.bucket, _PATTERN_SCOPE_TO_SUFFIX[args.scope])

    try:
        tag = _validate_enum(args.tag, "rule_tag", ENUM_FIELDS["rule_tag"])
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        text = _validate_verbatim(args.text, "pattern_rule.text")
    except ValueError as err:
        return _die(str(err), code=2)

    try:
        with _state_transaction(args.devforge_dir) as state:
            state["patterns_and_antipatterns"][pattern_key].append(
                {"tag": tag, "text": text}
            )
    except (OSError, json.JSONDecodeError) as err:
        return _die("add-pattern-rule: {0}".format(err))
    return 0


def cmd_set_scaffolding_guide(args: argparse.Namespace) -> int:
    """Set scaffolding_guide record (starter_directories + sample_files). Replaces prior value."""
    try:
        starter_dirs = _validate_string_array(args.starter_dirs, "scaffolding_guide.starter_directories")
    except ValueError as err:
        return _die(str(err), code=2)

    try:
        sample_files_raw = json.loads(args.sample_files_json)
    except ValueError as err:
        return _die(
            "set-scaffolding-guide: --sample-files-json is malformed JSON: {0}".format(err),
            code=2,
        )
    if not isinstance(sample_files_raw, list):
        return _die(
            "set-scaffolding-guide: --sample-files-json must be a JSON array, got {0}".format(
                type(sample_files_raw).__name__
            ),
            code=2,
        )
    required_keys = {"path", "language", "content"}
    for i, item in enumerate(sample_files_raw):
        if not isinstance(item, dict):
            return _die(
                "set-scaffolding-guide: sample file {0} must be a JSON object, got {1}".format(
                    i, type(item).__name__
                ),
                code=2,
            )
        missing = required_keys - set(item.keys())
        if missing:
            return _die(
                "set-scaffolding-guide: sample file {0} is missing keys: {1}".format(
                    i, sorted(missing)
                ),
                code=2,
            )

    try:
        with _state_transaction(args.devforge_dir) as state:
            state["scaffolding_guide"] = {
                "starter_directories": starter_dirs,
                "sample_files": sample_files_raw,
            }
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-scaffolding-guide: {0}".format(err))
    return 0
