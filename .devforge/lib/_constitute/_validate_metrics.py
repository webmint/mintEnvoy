"""4-dimension content quality metrics for cmd_validate.

Dimensions:
  Dim 1 slot_fill — required sections/fields populated
  Dim 2 citation  — path-like tokens resolve under install_root
  Dim 3 code_syntax — code_example.code parses as declared language
  Dim 4 rule_tag  — every rule tag in closed enum
"""

from __future__ import annotations

import ast
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union

import init_helper  # type: ignore  # noqa: E402

from ._render import _IDENTITY_REQUIRED_SUBFIELDS
from ._schema import ENUM_FIELDS, _PATTERNS_BUCKETS


# Regex to extract path-like tokens that look like source/doc file references.
# Matches tokens with a common code/doc extension. Applied to rule text,
# table cells, and code_example annotations.
#
# Alternation order matters: longer suffixes MUST come first so the regex
# engine matches `.tsx` before `.ts`, `.json` before `.js`, `.jsx` before
# `.js`, `.yaml` before `.yml`. Otherwise `tsconfig.json` extracts as
# `tsconfig.js` and the existence check fails on the wrong path.
_PATH_TOKEN_RE = re.compile(
    r"[\w\-\./]+"
    r"\.(?:tsx|ts|jsx|json|yaml|js|vue|py|md|yml|toml)"
)

# Composite weights (must sum to 1.0).
_VALIDATE_WEIGHTS = {
    "slot_fill":   0.30,
    "citation":    0.25,
    "code_syntax": 0.25,
    "rule_tag":    0.20,
}

# Composite pass threshold.
_COMPOSITE_PASS_THRESHOLD = 0.95

# Per-dimension pass thresholds. rule_tag is mechanical (any invalid tag is
# a helper bug); the other 3 dimensions allow up to 5% slop.
_DIM_PASS_THRESHOLDS = {
    "slot_fill":   0.95,
    "citation":    0.95,
    "code_syntax": 0.95,
    "rule_tag":    1.0,
}


# ---------------------------------------------------------------------------
# Dim 1 — Slot-fill rate.
# ---------------------------------------------------------------------------


def _count_slot_fill(state: dict) -> "tuple":
    """Return (filled_slots, total_slots, list_of_failed_slot_names).

    Required slots:
      - project_identity 4 subfields (4 slots)
      - architecture_rules: ≥1 section (1 slot)
      - code_quality_standards: ≥1 section (1 slot)
      - patterns_and_antipatterns: ≥1 rule across 6 buckets (1 slot)
      - domain_rules: ≥1 section (1 slot)
      - workflow_rules: ≥1 section (1 slot)
      - scaffolding_guide (greenfield only): ≥1 starter_directory OR ≥1 sample_file (1 slot)
    Total: 9 (existing-codebase) or 10 (greenfield)
    """
    filled = 0
    total = 0
    failed = []  # type: List[str]

    identity = state.get("project_identity") or {}
    for subfield in _IDENTITY_REQUIRED_SUBFIELDS:
        total += 1
        val = identity.get(subfield)
        if val and str(val).strip():
            filled += 1
        else:
            failed.append("project_identity.{0}".format(subfield))

    for bucket_key, label in [
        ("architecture_rules", "Section 2"),
        ("code_quality_standards", "Section 3"),
        ("domain_rules", "Section 5"),
        ("workflow_rules", "Section 6"),
    ]:
        total += 1
        sections = state.get(bucket_key) or []
        if sections:
            filled += 1
        else:
            failed.append("{0} ({1}): no sub-sections".format(label, bucket_key))

    total += 1
    pat = state.get("patterns_and_antipatterns") or {}
    any_rule = any(
        isinstance(pat.get(b), list) and pat.get(b)
        for b in _PATTERNS_BUCKETS
    )
    if any_rule:
        filled += 1
    else:
        failed.append("Section 4 (patterns_and_antipatterns): no rules in any bucket")

    mode = state.get("mode")
    if mode == "greenfield":
        total += 1
        scaffolding = state.get("scaffolding_guide") or {}
        starter_dirs = scaffolding.get("starter_directories") or []
        sample_files = scaffolding.get("sample_files") or []
        if starter_dirs or sample_files:
            filled += 1
        else:
            failed.append("Section 7 (scaffolding_guide): no starter_directory or sample_file")

    return filled, total, failed


# ---------------------------------------------------------------------------
# Dim 2 — Citation validity.
# ---------------------------------------------------------------------------


def _extract_path_tokens(text: str) -> "List[str]":
    """Return list of path-like tokens extracted from text using _PATH_TOKEN_RE."""
    if not text:
        return []
    return _PATH_TOKEN_RE.findall(text)


def _collect_citation_texts(state: dict) -> "List[str]":
    """Collect all text fields that may contain path references.

    Walks:
    - rule.text in all section buckets + patterns buckets
    - table cell strings (all cells in all rows)
    - code_example.annotation strings

    Returns list of individual text strings (one per field value, not per token).
    """
    texts = []  # type: List[str]

    def _add_rule(rule: dict) -> None:
        t = rule.get("text")
        if t:
            texts.append(t)

    def _add_section(section: dict) -> None:
        for rule in section.get("rules", []):
            _add_rule(rule)
        for table in section.get("tables", []):
            for row in table.get("rows", []):
                for cell in row:
                    if cell:
                        texts.append(str(cell))
        for ex in section.get("code_examples", []):
            ann = ex.get("annotation")
            if ann:
                texts.append(ann)

    for bucket_key in ["architecture_rules", "code_quality_standards", "domain_rules", "workflow_rules"]:
        for section in state.get(bucket_key) or []:
            _add_section(section)

    pat = state.get("patterns_and_antipatterns") or {}
    for bucket in _PATTERNS_BUCKETS:
        for rule in pat.get(bucket) or []:
            _add_rule(rule)

    return texts


def _resolve_effective_root(
    install_root: "Union[str, os.PathLike[str]]",
    init_yaml_path: "Optional[Path]",
) -> "Optional[Path]":
    """Return wrapper-mode effective root, or None for standalone."""
    if init_yaml_path is None or not Path(init_yaml_path).exists():
        return None
    try:
        text = Path(init_yaml_path).read_text(encoding="utf-8")
        state = init_helper.parse_yaml(text)
    except Exception:
        return None
    if state.get("workspace_mode") != "wrapper":
        return None
    project_root = state.get("project_root") or ""
    if not project_root or project_root == ".":
        return None
    return Path(install_root) / project_root


def _build_package_name_map(init_yaml_path: "Optional[Path]") -> "Dict[str, str]":
    """Build {package_name: path} from init.yaml packages_detected list."""
    if init_yaml_path is None or not Path(init_yaml_path).exists():
        return {}
    try:
        text = Path(init_yaml_path).read_text(encoding="utf-8")
        state = init_helper.parse_yaml(text)
    except Exception:
        return {}
    result = {}  # type: Dict[str, str]
    for record in state.get("packages_detected") or []:
        p = record.get("path", "")
        name = Path(p).name if p else ""
        if name and p:
            result[name] = p
    return result


def _count_citations(
    state: dict,
    install_root: "Union[str, os.PathLike[str]]",
    devforge_dir: "Union[str, os.PathLike[str]]",
) -> "tuple":
    """Return (score_float, resolved, unresolved, failed_items).

    score = resolved / (resolved + unresolved); if 0 tokens found → 1.0 (N/A).
    failed_items is a list of strings describing unresolved references.
    """
    install_root_path = Path(install_root)
    init_yaml_path = Path(devforge_dir) / init_helper.OUTPUT_FILE_NAME
    pkg_map = _build_package_name_map(init_yaml_path)
    effective_root = _resolve_effective_root(install_root, init_yaml_path)

    texts = _collect_citation_texts(state)
    all_tokens = []  # type: List[str]
    for text in texts:
        all_tokens.extend(_extract_path_tokens(text))

    # Filter URL remnants — see original docstring for the URL-stripping
    # logic. `_PATH_TOKEN_RE` strips the `https:` prefix; the remainder
    # `//example.com/x.json` would resolve to a bogus absolute path.
    all_tokens = [t for t in all_tokens if not t.startswith("//") and ":" not in t]

    if not all_tokens:
        return 1.0, 0, 0, []

    resolved = 0
    unresolved = 0
    failed_items = []  # type: List[str]

    def _try_resolve(token):
        if (install_root_path / token).exists():
            return True
        if effective_root is not None and (effective_root / token).exists():
            return True
        token_name = Path(token).name
        if token_name in pkg_map:
            if (install_root_path / pkg_map[token_name]).exists():
                return True
            if effective_root is not None and (effective_root / pkg_map[token_name]).exists():
                return True
        if effective_root is not None:
            try:
                for found in effective_root.rglob(token):
                    if found.exists():
                        return True
            except (OSError, ValueError):
                pass
            if "/" not in token:
                try:
                    for found in effective_root.rglob("*" + token):
                        if found.exists():
                            return True
                except (OSError, ValueError):
                    pass
        return False

    seen = set()  # type: set
    for token in all_tokens:
        if token in seen:
            continue
        seen.add(token)
        if _try_resolve(token):
            resolved += 1
            continue
        unresolved += 1
        failed_items.append("citation unresolved: {0!r}".format(token))

    total = resolved + unresolved
    score = resolved / total if total > 0 else 1.0
    return score, resolved, unresolved, failed_items


# ---------------------------------------------------------------------------
# Dim 3 — Code-example syntax.
# ---------------------------------------------------------------------------


def _check_python_syntax(code: str) -> bool:
    """Return True if code parses as valid Python via ast.parse."""
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def _check_json_syntax(code: str) -> bool:
    """Return True if code parses as valid JSON via json.loads."""
    try:
        json.loads(code)
        return True
    except (json.JSONDecodeError, ValueError):
        return False


def _check_balanced_braces(code: str) -> bool:
    """Return True if brace count is balanced (abs(open - close) <= 1) and code is non-empty.

    Used for TS/JS/TSX/JSX — tolerates single-brace imbalance from string literals.
    """
    stripped = code.strip()
    if not stripped:
        return False
    count_open = stripped.count("{")
    count_close = stripped.count("}")
    return abs(count_open - count_close) <= 1


def _check_code_example_syntax(lang: str, code: str) -> bool:
    """Check syntax for a single code example given its language tag.

    python/python3/py → ast.parse
    json → json.loads
    ts/tsx/typescript/js/jsx/javascript → balanced-brace + non-empty heuristic
    other → non-empty heuristic only
    """
    lang_lower = (lang or "").strip().lower()
    if lang_lower in ("python", "python3", "py"):
        return _check_python_syntax(code)
    if lang_lower == "json":
        return _check_json_syntax(code)
    if lang_lower in ("ts", "tsx", "typescript", "js", "jsx", "javascript"):
        return _check_balanced_braces(code)
    return bool(code.strip())


def _collect_code_examples(state: dict) -> "List[dict]":
    """Collect all code_example records from all section buckets."""
    examples = []  # type: List[dict]
    for bucket_key in ["architecture_rules", "code_quality_standards", "domain_rules", "workflow_rules"]:
        for section in state.get(bucket_key) or []:
            examples.extend(section.get("code_examples") or [])
    return examples


def _count_code_syntax(state: dict) -> "tuple":
    """Return (score_float, parsed_clean, total, failed_items).

    score = parsed_clean / total; total == 0 → 1.0 (N/A).
    failed_items lists examples that failed syntax check.
    """
    examples = _collect_code_examples(state)
    if not examples:
        return 1.0, 0, 0, []

    parsed_clean = 0
    failed_items = []  # type: List[str]
    for i, ex in enumerate(examples):
        lang = ex.get("language") or ""
        code = ex.get("code") or ""
        label = ex.get("label") or "?"
        if _check_code_example_syntax(lang, code):
            parsed_clean += 1
        else:
            failed_items.append(
                "code_example[{0}] label={1!r} lang={2!r}: syntax check failed".format(
                    i, label, lang
                )
            )

    total = len(examples)
    score = parsed_clean / total if total > 0 else 1.0
    return score, parsed_clean, total, failed_items


# ---------------------------------------------------------------------------
# Dim 4 — Rule-tag validity.
# ---------------------------------------------------------------------------


def _collect_all_rule_tags(state: dict) -> "List[tuple]":
    """Collect all (tag, context_label) from all rule records in all buckets.

    Used to validate every rule tag against the closed enum.
    """
    entries = []  # type: List[tuple]

    for bucket_key in ["architecture_rules", "code_quality_standards", "domain_rules", "workflow_rules"]:
        for i, section in enumerate(state.get(bucket_key) or []):
            for j, rule in enumerate(section.get("rules") or []):
                label = "{0}[{1}].rules[{2}]".format(bucket_key, i, j)
                entries.append((rule.get("tag"), label))

    pat = state.get("patterns_and_antipatterns") or {}
    for bucket in _PATTERNS_BUCKETS:
        for j, rule in enumerate(pat.get(bucket) or []):
            label = "patterns_and_antipatterns.{0}[{1}]".format(bucket, j)
            entries.append((rule.get("tag"), label))

    return entries


def _count_rule_tags(state: dict) -> "tuple":
    """Return (score_float, valid_count, total_count, failed_items).

    score = valid_tags / total_tags. Zero tags → 1.0 (N/A).
    Pass threshold = 1.0 (mechanical check; failure indicates helper bug).
    """
    entries = _collect_all_rule_tags(state)
    if not entries:
        return 1.0, 0, 0, []

    valid_enum = ENUM_FIELDS["rule_tag"]
    valid_count = 0
    failed_items = []  # type: List[str]
    for tag, label in entries:
        if tag in valid_enum:
            valid_count += 1
        else:
            failed_items.append(
                "{0}: invalid rule tag {1!r} (allowed: {2})".format(
                    label, tag, sorted(valid_enum)
                )
            )

    total = len(entries)
    score = valid_count / total if total > 0 else 1.0
    return score, valid_count, total, failed_items


def _compute_composite(scores: "Dict[str, float]") -> float:
    """Compute weighted composite score from per-dimension float scores."""
    return sum(_VALIDATE_WEIGHTS[d] * scores[d] for d in _VALIDATE_WEIGHTS)
