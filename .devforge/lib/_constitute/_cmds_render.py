"""cmd_render + cmd_verify + cmd_summary handlers."""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from ._render import (
    _IDENTITY_REQUIRED_SUBFIELDS,
    _RENDER_REQUIRED_SCALARS,
    _expected_section_count,
    _parse_rendered_constitution,
    _render_constitution,
    _write_constitution_atomic,
)
from ._schema import ENUM_FIELDS, _PATTERNS_BUCKETS, validate_forcing_functions
from ._state import _load
from ._summary import _render_constitute_summary


def cmd_render(args: argparse.Namespace) -> int:
    """Walk schema, concatenate constitution.md, atomic write.

    Reads <devforge_dir>/constitute.json. Concatenates and writes
    <install_root>/constitution.md atomically.

    Exit 0 = success.
    Exit 1 = state file missing / unreadable (JSON parse error).
    Exit 2 = required field missing (project_name, generated_date,
             last_updated, mode, project_identity with all 4 subfields).
    """
    try:
        state = _load(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        sys.stderr.write(
            "constitute_helper render: cannot load constitute.json: {0}\n".format(err)
        )
        return 1

    try:
        text = _render_constitution(state)
    except ValueError as err:
        sys.stderr.write("constitute_helper {0}\n".format(err))
        return 2

    try:
        _write_constitution_atomic(text, args.install_root)
    except OSError as err:
        sys.stderr.write(
            "constitute_helper render: cannot write constitution.md: {0}\n".format(err)
        )
        return 1

    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Cross-check constitute.json for correctness and round-trip identity.

    Checks:
    1. Required scalars non-null: project_name, generated_date, last_updated,
       mode, project_identity (all 4 subfields).
    2. Each section in section_arrays: number + title populated; tag in enum or
       None; each rule has tag in enum + non-empty text; each code_example has
       label in enum + non-empty code; each table: len(row)==len(columns) for
       every row.
    3. patterns_and_antipatterns: each of 6 buckets is a list; each rule has
       tag in enum + non-empty text.
    4. ScaffoldingGuide: when mode==greenfield, scaffolding_guide must be
       non-null; when non-null, starter_directories is a list of strings;
       sample_files is a list of {path, language, content} dicts.
    5. forcing_functions block (when present): validated by
       validate_forcing_functions(); absent block is a no-op.
    6. Round-trip identity: render to string; re-parse project_name + section
       count; compare to state.

    Exit 0 = all checks pass.
    Exit 2 = at least one violation (stderr enumerates each).
    """
    try:
        state = _load(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        sys.stderr.write(
            "constitute_helper verify: cannot load constitute.json: {0}\n".format(err)
        )
        return 2

    violations = []  # type: List[str]

    # --- Check 1: Required scalars ---
    for field in _RENDER_REQUIRED_SCALARS:
        if state.get(field) is None:
            violations.append("required field {0!r} is null".format(field))

    identity = state.get("project_identity")
    if identity is None:
        violations.append("required field 'project_identity' is null")
    else:
        for sub in _IDENTITY_REQUIRED_SUBFIELDS:
            if identity.get(sub) is None:
                violations.append(
                    "project_identity.{0} is null".format(sub)
                )

    # --- Check 2: Section arrays ---
    section_bucket_keys = [
        "architecture_rules",
        "code_quality_standards",
        "domain_rules",
        "workflow_rules",
    ]
    for bucket_key in section_bucket_keys:
        sections = state.get(bucket_key, [])
        if not isinstance(sections, list):
            violations.append("{0} must be a list".format(bucket_key))
            continue
        for i, section in enumerate(sections):
            prefix = "{0}[{1}]".format(bucket_key, i)
            if not section.get("number"):
                violations.append("{0}: number is missing or empty".format(prefix))
            if not section.get("title"):
                violations.append("{0}: title is missing or empty".format(prefix))
            tag = section.get("tag")
            if tag is not None and tag not in ENUM_FIELDS["section_tag"]:
                violations.append(
                    "{0}: tag {1!r} not in allowed set {2}".format(
                        prefix, tag, sorted(ENUM_FIELDS["section_tag"])
                    )
                )
            for j, rule in enumerate(section.get("rules", [])):
                rule_prefix = "{0}.rules[{1}]".format(prefix, j)
                rtag = rule.get("tag")
                if rtag not in ENUM_FIELDS["rule_tag"]:
                    violations.append(
                        "{0}: tag {1!r} not in allowed set {2}".format(
                            rule_prefix, rtag, sorted(ENUM_FIELDS["rule_tag"])
                        )
                    )
                if not rule.get("text", "").strip():
                    violations.append("{0}: text is empty".format(rule_prefix))
            for j, ex in enumerate(section.get("code_examples", [])):
                ex_prefix = "{0}.code_examples[{1}]".format(prefix, j)
                elabel = ex.get("label")
                if elabel not in ENUM_FIELDS["code_label"]:
                    violations.append(
                        "{0}: label {1!r} not in allowed set {2}".format(
                            ex_prefix, elabel, sorted(ENUM_FIELDS["code_label"])
                        )
                    )
                if not ex.get("code", "").strip():
                    violations.append("{0}: code is empty".format(ex_prefix))
            for j, table in enumerate(section.get("tables", [])):
                tbl_prefix = "{0}.tables[{1}]".format(prefix, j)
                cols = table.get("columns", [])
                for k, row in enumerate(table.get("rows", [])):
                    if len(row) != len(cols):
                        violations.append(
                            "{0}.rows[{1}]: has {2} cells but table has {3} columns".format(
                                tbl_prefix, k, len(row), len(cols)
                            )
                        )

    # --- Check 3: patterns_and_antipatterns ---
    pat = state.get("patterns_and_antipatterns", {})
    if not isinstance(pat, dict):
        violations.append("patterns_and_antipatterns must be a dict")
    else:
        for bucket_key in _PATTERNS_BUCKETS:
            bucket = pat.get(bucket_key)
            if not isinstance(bucket, list):
                violations.append(
                    "patterns_and_antipatterns.{0} must be a list".format(bucket_key)
                )
                continue
            for j, rule in enumerate(bucket):
                rule_prefix = "patterns_and_antipatterns.{0}[{1}]".format(bucket_key, j)
                rtag = rule.get("tag")
                if rtag not in ENUM_FIELDS["rule_tag"]:
                    violations.append(
                        "{0}: tag {1!r} not in allowed set {2}".format(
                            rule_prefix, rtag, sorted(ENUM_FIELDS["rule_tag"])
                        )
                    )
                if not rule.get("text", "").strip():
                    violations.append("{0}: text is empty".format(rule_prefix))

    # --- Check 4: scaffolding_guide ---
    mode = state.get("mode")
    scaffolding = state.get("scaffolding_guide")
    if mode == "greenfield" and scaffolding is None:
        violations.append(
            "scaffolding_guide is null but mode is 'greenfield'; "
            "set-scaffolding-guide is required for greenfield projects"
        )
    if scaffolding is not None:
        starter_dirs = scaffolding.get("starter_directories")
        if not isinstance(starter_dirs, list):
            violations.append("scaffolding_guide.starter_directories must be a list")
        else:
            for i, d in enumerate(starter_dirs):
                if not isinstance(d, str):
                    violations.append(
                        "scaffolding_guide.starter_directories[{0}] must be a string".format(i)
                    )
        sample_files = scaffolding.get("sample_files")
        if not isinstance(sample_files, list):
            violations.append("scaffolding_guide.sample_files must be a list")
        else:
            required_sf_keys = {"path", "language", "content"}
            for i, sf in enumerate(sample_files):
                sf_prefix = "scaffolding_guide.sample_files[{0}]".format(i)
                if not isinstance(sf, dict):
                    violations.append("{0}: must be a dict".format(sf_prefix))
                    continue
                missing_keys = required_sf_keys - set(sf.keys())
                if missing_keys:
                    violations.append(
                        "{0}: missing keys {1}".format(sf_prefix, sorted(missing_keys))
                    )

    # --- Check 5: forcing_functions block (when present) ---
    ff_block = state.get("forcing_functions")  # None when key absent
    ff_errors = validate_forcing_functions(ff_block)
    violations.extend(ff_errors)

    # --- Check 6: Round-trip identity (minimal) ---
    if not violations:
        try:
            rendered_text = _render_constitution(state)
            parsed = _parse_rendered_constitution(rendered_text)
        except ValueError as err:
            violations.append("round-trip render error: {0}".format(err))
        else:
            if parsed.get("project_name") != state.get("project_name"):
                violations.append(
                    "round-trip identity: project_name mismatch: "
                    "rendered={0!r}, state={1!r}".format(
                        parsed.get("project_name"), state.get("project_name")
                    )
                )
            expected_secs = _expected_section_count(state)
            actual_secs = parsed.get("section_count", 0)
            if actual_secs != expected_secs:
                violations.append(
                    "round-trip identity: section count mismatch: "
                    "rendered={0}, expected={1}".format(actual_secs, expected_secs)
                )

    if violations:
        for v in violations:
            sys.stderr.write("verify: {0}\n".format(v))
        return 2

    sys.stderr.write("verify: ok\n")
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    """Render the constitute helper summary to stdout. Read-only.

    Reads constitute.json (defaults if missing → exit 0 with all-unset
    output). Corrupted JSON → exit 1 + stderr message (matches init/
    configure helper precedent; preserves the script-pipeable signal).
    Output is deterministic across re-runs — suitable for piping + diffing.
    """
    try:
        state = _load(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        sys.stderr.write(
            "constitute_helper summary: cannot load constitute.json: {0}\n".format(err)
        )
        return 1
    sys.stdout.write(_render_constitute_summary(state))
    return 0
