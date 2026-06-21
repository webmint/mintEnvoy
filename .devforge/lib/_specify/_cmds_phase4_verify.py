"""Phase 4 verify cmd_* + cmd_render + cmd_verify_rendered."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from ._render import _canonicalize_for_compare, render_spec
from ._schema import (
    AC_SUBSECTION_ENUM,
    CONSTITUTION_RULE_RE,
    CONSTITUTION_STOPWORDS,
    EARS_REGEX,
    NUMERIC_DIGIT_NOUN_RE,
    NUMERIC_HEADING_RE,
    NUMERIC_TABLE_SEP_RE,
)
from ._state import _load_state
from ._validators import _die
from _shared.text_overlap import tokenize_for_overlap  # type: ignore[import]


def cmd_verify_coverage(args: argparse.Namespace) -> int:
    """Variance rule #5: every finding landed in AC/Constraint/OOS/Risk."""
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("verify-coverage: {0}".format(err))
    unlanded = [
        f for f in state["findings"]
        if f.get("landed_in", "unlanded") == "unlanded"
    ]
    if unlanded:
        sys.stderr.write(
            "verify-coverage: unlanded findings (Variance rule #5):\n"
        )
        for f in unlanded:
            sys.stderr.write(
                "  - {0} (from {1}): {2}\n".format(
                    f.get("finding_id"),
                    f.get("source_path"),
                    (f.get("content", "") or "")[:80],
                )
            )
        return 2
    return 0


def cmd_verify_ac_subsection_coverage(args: argparse.Namespace) -> int:
    """Every of 7 subsections has ≥1 AC OR a non-empty N/A reason."""
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("verify-ac-subsection-coverage: {0}".format(err))
    populated = {
        ac.get("subsection")
        for ac in state["acceptance_criteria"]
        if ac.get("subsection")
    }
    na = {
        sub for sub, reason in state["ac_subsection_na"].items()
        if (reason or "").strip()
    }
    missing = [
        sub for sub in AC_SUBSECTION_ENUM
        if sub not in populated and sub not in na
    ]
    if missing:
        sys.stderr.write(
            "verify-ac-subsection-coverage: subsections without AC or "
            "N/A marker:\n"
        )
        for sub in missing:
            sys.stderr.write("  - {0}\n".format(sub))
        return 2
    return 0


def cmd_verify_ac_shape(args: argparse.Namespace) -> int:
    """Variance rule #10: every AC.statement matches its EARS regex."""
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("verify-ac-shape: {0}".format(err))
    bad: List[Tuple[str, str, str, str]] = []
    for ac in state["acceptance_criteria"]:
        variant = ac.get("ears_variant", "")
        statement = ac.get("statement", "")
        if variant not in EARS_REGEX:
            bad.append(
                (ac.get("ac_id", "?"), variant, statement,
                 "unknown EARS variant")
            )
            continue
        if not EARS_REGEX[variant].match(statement):
            bad.append(
                (ac.get("ac_id", "?"), variant, statement,
                 "regex mismatch")
            )
    if bad:
        sys.stderr.write(
            "verify-ac-shape: AC statements failing EARS regex:\n"
        )
        for ac_id, variant, statement, why in bad:
            sys.stderr.write(
                "  - {0} ({1}): {2} [{3}]\n".format(
                    ac_id, variant, statement[:80], why,
                )
            )
        return 2
    return 0


def cmd_verify_numerical_consistency(args: argparse.Namespace) -> int:
    """Variance rule #6: digit-prefixed nouns consistent across spec."""
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("verify-numerical-consistency: {0}".format(err))
    rendered = render_spec(state)
    groups: Dict[str, Dict[str, List[int]]] = {}
    for lineno, line in enumerate(rendered.splitlines(), 1):
        if NUMERIC_HEADING_RE.match(line):
            continue
        if NUMERIC_TABLE_SEP_RE.match(line):
            continue
        for m in NUMERIC_DIGIT_NOUN_RE.finditer(line):
            num, noun = m.group(1), m.group(2).lower()
            groups.setdefault(noun, {}).setdefault(num, []).append(lineno)
    inconsistencies: List[Tuple[str, Dict[str, List[int]]]] = []
    for noun, value_map in groups.items():
        if len(value_map) >= 2:
            inconsistencies.append((noun, value_map))
    if inconsistencies:
        sys.stderr.write(
            "verify-numerical-consistency: inconsistent digit counts "
            "across rendered sections (Variance rule #6):\n"
        )
        for noun, value_map in sorted(inconsistencies):
            occurrences = ", ".join(
                "{0} (lines {1})".format(v, ",".join(str(L) for L in ls))
                for v, ls in sorted(value_map.items())
            )
            sys.stderr.write(
                "  - {0}: {1}\n".format(noun, occurrences)
            )
        return 2
    return 0


def _constitution_keywords(rule_text: str) -> set:
    """Tokenize a constitution rule, drop stopwords + short tokens."""
    tokens = re.findall(r"[a-zA-Z]{4,}", rule_text.lower())
    return {t for t in tokens if t not in CONSTITUTION_STOPWORDS}


def _body_tokens(body: str) -> set:
    return set(re.findall(r"[a-zA-Z]{4,}", (body or "").lower()))


def cmd_check_constitution_compliance(args: argparse.Namespace) -> int:
    """Token-overlap scan of constitution MUST/SHALL lines vs AC/Constraint/OOS.

    Non-blocking — exit 0 always.
    """
    cpath = Path(args.constitution_path or "constitution.md")
    if not cpath.exists():
        sys.stderr.write(
            "check-constitution-compliance: constitution at {0!r} not "
            "found; skipping (non-blocking).\n".format(str(cpath))
        )
        return 0
    try:
        text = cpath.read_text(encoding="utf-8")
    except OSError as err:
        sys.stderr.write(
            "check-constitution-compliance: read failed on {0}: {1} "
            "(non-blocking)\n".format(cpath, err)
        )
        return 0
    rules: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if CONSTITUTION_RULE_RE.search(stripped):
            rules.append(stripped)
    if not rules:
        return 0
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        sys.stderr.write(
            "check-constitution-compliance: state read failed: "
            "{0} (non-blocking)\n".format(err)
        )
        return 0
    targets: List[Tuple[str, str]] = []
    for ac in state["acceptance_criteria"]:
        targets.append((
            "AC {0}".format(ac.get("ac_id", "")),
            ac.get("statement", ""),
        ))
    for c in state["constraints"]:
        targets.append((
            "Constraint ({0})".format(c.get("kind", "")),
            c.get("content", ""),
        ))
    for o in state["out_of_scope"]:
        targets.append(("OOS", o.get("content", "")))
    warnings: List[Tuple[str, str, str, List[str]]] = []
    for rule in rules:
        kws = _constitution_keywords(rule)
        if not kws:
            continue
        for tag, body in targets:
            overlap = kws & _body_tokens(body)
            if overlap:
                warnings.append((rule, tag, body, sorted(overlap)))
    if warnings:
        sys.stderr.write(
            "check-constitution-compliance: review constitution "
            "mandates overlapping with spec entries (non-blocking):\n"
        )
        for rule, tag, body, overlap in warnings:
            sys.stderr.write(
                "  - rule: {0}\n    {1}: {2}\n    overlap: {3}\n".format(
                    rule[:120], tag, (body or "")[:120], ", ".join(overlap),
                )
            )
    return 0


def cmd_verify_scope_coherence(args: argparse.Namespace) -> int:
    """Non-blocking token-overlap scan: §5 ACs / §4 affected-areas vs §6 OOS.

    For each §6 Out-of-Scope entry, extracts salient terms via the shared
    tokenize_for_overlap helper, then checks whether any §5 AC statement or
    §4 affected-area impact shares tokens with those terms.  A shared token
    indicates the AC or affected-area may mandate behaviour that the §6 entry
    explicitly excludes — a §5 ↔ §6 coherence contradiction.

    This is a heuristic check that WILL produce false positives (two entries
    sharing a noun without truly conflicting).  The posture is therefore
    intentionally NON-BLOCKING: warnings are written to stderr but the
    command always exits 0.  The author is prompted to reconcile manually —
    either drop the §6 entry (the concern is in scope) or weaken/remove the
    §5/§4 mandate (the concern is out of scope).  The check must not
    auto-resolve; that decision belongs to the author.

    Recovery advisory (inline per warning): reconcile — drop the §6 entry
    (concern is in scope) OR weaken/remove the §5/§4 mandate (concern is out
    of scope).
    """
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        sys.stderr.write(
            "verify-scope-coherence: state read failed: "
            "{0} (non-blocking)\n".format(err)
        )
        return 0

    oos_entries = state.get("out_of_scope", [])
    if not oos_entries:
        return 0

    # Build target list: (tag, text) pairs from §5 ACs and §4 affected areas.
    targets: List[Tuple[str, str]] = []
    for ac in state.get("acceptance_criteria", []):
        statement = (ac.get("statement") or "").strip()
        if statement:
            targets.append(("AC {0}".format(ac.get("ac_id", "?")), statement))
    for area in state.get("affected_areas", []):
        impact = (area.get("impact") or "").strip()
        if impact:
            targets.append((
                "Affected area {0!r}".format(area.get("area", "?")),
                impact,
            ))

    if not targets:
        return 0

    warnings: List[Tuple[str, str, str, List[str]]] = []
    for oos in oos_entries:
        oos_text = (oos.get("content") or "").strip()
        if not oos_text:
            continue
        oos_tokens = set(tokenize_for_overlap(oos_text))
        if not oos_tokens:
            continue
        for tag, body in targets:
            body_tokens = set(tokenize_for_overlap(body))
            overlap = oos_tokens & body_tokens
            if overlap:
                warnings.append((oos_text, tag, body, sorted(overlap)))

    if warnings:
        sys.stderr.write(
            "verify-scope-coherence: §5/§4 entries may mandate behaviour "
            "excluded by §6 Out-of-Scope (non-blocking — review and reconcile):\n"
        )
        for oos_text, tag, body, overlap in warnings:
            sys.stderr.write(
                "  - §6 OOS: {0}\n"
                "    {1}: {2}\n"
                "    overlap tokens: {3}\n"
                "    reconcile: drop the §6 entry (concern is in scope) OR"
                " weaken/remove the §5/§4 mandate (concern is out of scope).\n"
                .format(
                    oos_text[:120],
                    tag,
                    body[:120],
                    ", ".join(overlap),
                )
            )
    # Always exit 0 — non-blocking warning, mirrors check-constitution-compliance.
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    """Emit spec markdown to stdout. Pure read — no state mutation."""
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("render: {0}".format(err))
    sys.stdout.write(render_spec(state))
    return 0


def cmd_verify_rendered(args: argparse.Namespace) -> int:
    """Post-write integrity check: on-disk spec.md vs helper render."""
    path = Path(args.path)
    if not path.is_file():
        sys.stderr.write(
            "verify-rendered: path not found: {0}\n".format(path)
        )
        return 2
    try:
        disk_bytes = path.read_bytes()
    except OSError as err:
        sys.stderr.write(
            "verify-rendered: cannot read {0}: {1}\n".format(path, err)
        )
        return 2
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("verify-rendered: cannot load state: {0}".format(err))
    rendered = render_spec(state).encode("utf-8")
    canonical_disk = _canonicalize_for_compare(disk_bytes)
    canonical_rendered = _canonicalize_for_compare(rendered)
    if canonical_disk == canonical_rendered:
        return 0
    disk_lines = canonical_disk.decode("utf-8").split("\n")
    rendered_lines = canonical_rendered.decode("utf-8").split("\n")
    first_diff_line = None
    for idx in range(min(len(disk_lines), len(rendered_lines))):
        if disk_lines[idx] != rendered_lines[idx]:
            first_diff_line = idx + 1
            break
    if first_diff_line is None:
        first_diff_line = min(len(disk_lines), len(rendered_lines)) + 1
    sys.stderr.write(
        "verify-rendered: drift at line {0} (disk {1} bytes vs rendered"
        " {2} bytes after canonicalization)\n"
        .format(first_diff_line, len(canonical_disk), len(canonical_rendered))
    )
    return 2
