"""cmd_validate (4-dim content quality) + cmd_verify_universal_defaults (drift detector)
+ cmd_verify_forcing_function_keys (forcing-function key drift detector)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

from ._schema import FORCING_FUNCTION_RULES
from ._universal import (
    _extract_universal_rules_from_state,
    _parse_universal_blocks,
)
from ._state import _load
from ._validate_metrics import (
    _COMPOSITE_PASS_THRESHOLD,
    _DIM_PASS_THRESHOLDS,
    _VALIDATE_WEIGHTS,
    _compute_composite,
    _count_citations,
    _count_code_syntax,
    _count_rule_tags,
    _count_slot_fill,
)


def cmd_validate(args: argparse.Namespace) -> int:
    """4-dimension content quality check for constitute.json.

    Dimensions:
      1. slot_fill   — required sections/fields populated (weight 0.30)
      2. citation    — path citations resolve under install_root (weight 0.25)
      3. code_syntax — code examples parse as declared language (weight 0.25)
      4. rule_tag    — every rule tag in closed enum (weight 0.20)

    Composite >= 0.95 → exit 0 (pass).
    Composite < 0.95  → exit 2 (fail; stderr enumerates per-dimension + failed items).
    Exit 1 on state file unreadable / corrupted JSON.

    stdout always receives a JSON object:
      {"composite": float, "dimensions": {dim: {"score": float, "pass": bool}}, "failed_items": [...]}
    """
    try:
        state = _load(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        sys.stderr.write(
            "constitute_helper validate: cannot load constitute.json: {0}\n".format(err)
        )
        return 1

    # Dim 1 — slot fill.
    filled, total_slots, slot_failed = _count_slot_fill(state)
    slot_score = filled / total_slots if total_slots > 0 else 1.0

    # Dim 2 — citation validity.
    citation_score, _resolved, _unresolved, citation_failed = _count_citations(
        state, args.install_root, args.devforge_dir
    )

    # Dim 3 — code-example syntax.
    syntax_score, _parsed, _total_ex, syntax_failed = _count_code_syntax(state)

    # Dim 4 — rule-tag validity.
    tag_score, _valid_tags, _total_tags, tag_failed = _count_rule_tags(state)

    scores = {
        "slot_fill":   slot_score,
        "citation":    citation_score,
        "code_syntax": syntax_score,
        "rule_tag":    tag_score,
    }
    composite = _compute_composite(scores)
    pass_threshold = _COMPOSITE_PASS_THRESHOLD

    all_failed = slot_failed + citation_failed + syntax_failed + tag_failed

    dimensions = {}
    for dim in ("slot_fill", "citation", "code_syntax", "rule_tag"):
        dimensions[dim] = {
            "score": round(scores[dim], 6),
            "pass": scores[dim] >= _DIM_PASS_THRESHOLDS[dim],
        }

    result_obj = {
        "composite": round(composite, 6),
        "dimensions": dimensions,
        "failed_items": all_failed,
    }
    sys.stdout.write(json.dumps(result_obj, indent=2))
    sys.stdout.write("\n")

    if composite < pass_threshold:
        sys.stderr.write(
            "constitute_helper validate: composite={0:.4f} < {1:.2f} — FAIL\n".format(
                composite, pass_threshold
            )
        )
        for dim in ("slot_fill", "citation", "code_syntax", "rule_tag"):
            sys.stderr.write(
                "  {0}: score={1:.4f} weight={2}\n".format(
                    dim, scores[dim], _VALIDATE_WEIGHTS[dim]
                )
            )
        for item in all_failed:
            sys.stderr.write("  FAIL: {0}\n".format(item))
        return 2

    sys.stderr.write(
        "constitute_helper validate: composite={0:.4f} >= {1:.2f} — PASS\n".format(
            composite, pass_threshold
        )
    )
    return 0


def _normalize_body(text: str) -> str:
    """Normalize a rule body for drift comparison: collapse whitespace.

    Strips leading/trailing whitespace AND collapses runs of internal
    whitespace (spaces, tabs, newlines) to single spaces, so cosmetic
    formatting differences don't surface as DRIFT findings. Body content
    must match semantically; cosmetic differences are silent.
    """
    return " ".join((text or "").split())


def cmd_verify_universal_defaults(args: argparse.Namespace) -> int:
    """Diff consumer's universal-rule bodies vs framework canonical.

    Reads both surfaces via the Phase 1.C parsers, compares per-section
    + per-rule, emits findings per line on stderr. Exit 0 if zero findings;
    exit 2 otherwise. Stdout = JSON report for downstream tooling.

    Args:
        args.consumer_path — consumer project root containing
            .devforge/constitute.json.
        args.canonical_path — path to canonical constitution.md (default:
            src/constitution.md relative to forge repo cwd).
    """
    consumer_path = Path(args.consumer_path).resolve()
    canonical_path = Path(args.canonical_path).resolve()

    consumer_json = consumer_path / ".devforge" / "constitute.json"

    if not canonical_path.is_file():
        sys.stderr.write(
            "verify-universal-defaults: canonical path not found: {0}\n".format(
                canonical_path
            )
        )
        return 2
    if not consumer_json.is_file():
        sys.stderr.write(
            "verify-universal-defaults: consumer constitute.json not found:"
            " {0}\n".format(consumer_json)
        )
        return 2

    canonical_blocks = _parse_universal_blocks(canonical_path)
    consumer_blocks = _extract_universal_rules_from_state(consumer_json)

    findings = []  # type: List[Dict[str, str]]

    for section_key, canonical_data in canonical_blocks.items():
        if section_key not in consumer_blocks:
            findings.append(
                {
                    "kind": "MISSING",
                    "section": section_key,
                    "detail": "consumer state has no entry for {0}".format(
                        section_key
                    ),
                }
            )
            continue
        consumer_data = consumer_blocks[section_key]
        canonical_rules = {
            r["tag_or_label"]: r["body"] for r in canonical_data["rules"]
        }
        consumer_rules = {
            r["tag_or_label"]: r["body"] for r in consumer_data["rules"]
        }
        for label, canonical_body in canonical_rules.items():
            if label not in consumer_rules:
                findings.append(
                    {
                        "kind": "MISSING",
                        "section": section_key,
                        "rule": label,
                        "detail": "consumer missing rule '{0}' in {1}".format(
                            label, section_key
                        ),
                    }
                )
                continue
            consumer_body = consumer_rules[label]
            if _normalize_body(canonical_body) != _normalize_body(consumer_body):
                findings.append(
                    {
                        "kind": "DRIFT",
                        "section": section_key,
                        "rule": label,
                        "detail": "body text differs",
                    }
                )

    report = {
        "consumer": str(consumer_path),
        "canonical": str(canonical_path),
        "findings": findings,
    }
    sys.stdout.write(json.dumps(report, indent=2) + "\n")

    if not findings:
        return 0

    for f in findings:
        line = "{kind} {section}".format(**f)
        if "rule" in f:
            line += " [{0}]".format(f["rule"])
        line += " — {detail}".format(**f)
        sys.stderr.write(line + "\n")
    return 2


def cmd_verify_forcing_function_keys(args: argparse.Namespace) -> int:
    """Diff consumer .devforge/constitute.json forcing_functions keys vs canonical.

    Compares the set of rule keys present under ``forcing_functions`` in the
    consumer's ``.devforge/constitute.json`` against the canonical
    ``FORCING_FUNCTION_RULES`` frozenset from ``_schema``.  Reports ONLY the
    MISSING direction — rules in the schema that are absent from the consumer.
    Extra/unknown consumer keys are silently tolerated (forward-compat).

    Args:
        args.consumer_path — consumer project root containing
            .devforge/constitute.json.

    Exit codes:
        0 — constitute.json exists and has no missing rules.
        1 — constitute.json present but unreadable / invalid JSON.
        2 — constitute.json exists but one or more schema rules are missing
            (drift).
        3 — constitute.json does NOT exist (project not yet constituted).

    stdout — JSON report object (exit 0 and exit 2 only; absent on exit 1
        and exit 3 — always check exit code before parsing stdout):
        {"consumer": "<abs path>", "missing_rules": [...sorted...],
         "schema_rules": [...sorted...]}

    stderr — one ``MISSING forcing-function rule: <name>`` line per missing
        rule (exit 2); or a single diagnostic note on exit codes 1 and 3.
    """
    consumer_path = Path(args.consumer_path).resolve()
    consumer_json = consumer_path / ".devforge" / "constitute.json"

    if not consumer_json.is_file():
        sys.stderr.write(
            "verify-forcing-function-keys: consumer constitute.json not found:"
            " {0}\n".format(consumer_json)
        )
        return 3

    try:
        raw = consumer_json.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError) as err:
        sys.stderr.write(
            "verify-forcing-function-keys: cannot read {path}: {err}\n".format(
                path=consumer_json, err=err
            )
        )
        return 1

    if not isinstance(data, dict):
        sys.stderr.write(
            "verify-forcing-function-keys: cannot read {0}: top-level value is {1},"
            " expected dict\n".format(consumer_json, type(data).__name__)
        )
        return 1

    # forcing_functions absent or null → treat as all rules missing (exit 2 = drift).
    # Covers both a pre-plan-01 install that predates the ff block and a block that
    # was cleared. OQ1 (plan 44 Phase 0) is resolved here: absent inside a present
    # constitute.json == drift. (Greenfield silent-skip — no constitute.json at all —
    # is exit 3, handled separately, and the shell caller also guards on file presence.)
    ff = data.get("forcing_functions")
    consumer_keys = set((ff or {}).keys())
    schema_rules = FORCING_FUNCTION_RULES

    missing = sorted(schema_rules - consumer_keys)
    report = {
        "consumer": str(consumer_path),
        "missing_rules": missing,
        "schema_rules": sorted(schema_rules),
    }
    sys.stdout.write(json.dumps(report, indent=2) + "\n")

    if not missing:
        return 0

    for rule in missing:
        sys.stderr.write(
            "MISSING forcing-function rule: {0}\n".format(rule)
        )
    return 2
