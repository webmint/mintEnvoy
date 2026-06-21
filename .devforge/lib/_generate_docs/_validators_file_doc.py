"""Per-file-doc mechanical validation (Steps B.3 and B.4 of VALIDATOR-LOOP-B-PLAN.md).

B.5 deletion log (2026-05-07):
  Removed from the prior _validators_annotation.py:
    - cmd_validate_annotation  (Part A, Step A.2 — replaced by cmd_validate_file_doc)
    - cmd_verify_annotations   (Part A, Step A.4 — replaced by cmd_verify_file_docs)
  File renamed _validators_annotation -> _validators_file_doc because "annotation"
  no longer describes the contents: all annotation-state code is gone; only the
  per-.md flow (Parts B.3 + B.4) remains.

Owns the per-file-doc validation commands and their helper checks:
  - _check_annotation_schema         — shared record shape validator (used by B.3)
  - _check_annotation_banned_phrase  — banned-phrase label check
  - _check_annotation_cite_resolves  — cite file resolution (missing/binary/range/hash)
  - _recompute_content_hash          — sha256 slice recompute (also imported by
                                       _setters_concern_files.cmd_write_file_doc)
  - _check_file_doc_specificity      — sibling .md label collision check (B.3)
  - cmd_validate_file_doc            — per-md validation command (Step B.3)
  - cmd_verify_file_docs             — post-batch aggregator command (Step B.4)

`cmd_validate_file_doc` exit codes (locked in VALIDATOR-LOOP-B-PLAN.md Step B.3):
  0 — all checks pass
  2 — banned-phrase hit in label
  3 — cite unresolvable (missing / range out-of-bounds / hash drift)
  4 — specificity fail (sibling label collision in same directory)
  5 — schema invalid OR file not found OR front-matter parse error
  6 — cite-file is binary

`cmd_verify_file_docs` exit codes (locked in VALIDATOR-LOOP-B-PLAN.md Step B.4):
  0 — all gates pass
  2 — at least one gate failed (stderr names which)
  5 — state error (package not registered, concern not registered,
      front-matter parse error in any filled md, or state-corrupt
      confidence value in any md's record)

Gate thresholds (locked constants):
  BANNED_PHRASE_TOLERANCE = 0           — no tolerance
  AMBIGUOUS_RATE_THRESHOLD = 0.10       — ≤10% ambiguous docs
  CROSS_CONCERN_DUPLICATE_RATE_THRESHOLD = 0.05 — ≤5% cross-concern label duplicates
  VACUOUS_PASS_TOLERANCE = 0            — no vacuous passes (tree set + zero filled mds)

Stdlib only. Targets Python 3.8+.
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from _banned_phrases import BANNED_PHRASES
from generate_docs_schema import ANNOTATION_CONFIDENCE_VALUES

from ._md_frontmatter import FrontmatterParseError, parse_frontmatter
from ._render import _project_root
from ._state import (
    StateLoadError,
    _die,
    _load_state,
    _require_concern,
    _require_package,
)


# ---------------------------------------------------------------------------
# Gate thresholds for cmd_verify_file_docs (Step B.4).
# Locked constants — do NOT add CLI --threshold flags; callers cannot tune.
# ---------------------------------------------------------------------------

BANNED_PHRASE_TOLERANCE = 0           # 0 tolerated
AMBIGUOUS_RATE_THRESHOLD = 0.10       # ≤10%
CROSS_CONCERN_DUPLICATE_RATE_THRESHOLD = 0.05  # ≤5%
VACUOUS_PASS_TOLERANCE = 0            # non-empty tree + zero filled mds → fail


# Regex for a valid sha256 hex digest: exactly 64 lowercase hex chars.
_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


def _check_annotation_schema(annotation: Dict[str, Any]) -> Optional[str]:
    """Return None on pass, or an error message describing the first bad field.

    Validates the full annotation record shape. Called by `cmd_validate_file_doc`
    to gate all further checks — schema must pass before anything else runs.
    """
    if not isinstance(annotation, dict):
        return "annotation record must be a dict"

    # label: non-empty single-line string, no control chars (< 0x20 or DEL).
    label = annotation.get("label")
    if not isinstance(label, str) or label.strip() == "":
        return "label: must be a non-empty string"
    for ch in label:
        code = ord(ch)
        if code < 0x20 or code == 0x7F:
            return "label: contains control character (0x{0:02X})".format(code)

    # confidence: must be in ANNOTATION_CONFIDENCE_VALUES enum.
    confidence = annotation.get("confidence")
    if confidence not in ANNOTATION_CONFIDENCE_VALUES:
        return "confidence: must be one of {0}, got {1!r}".format(
            sorted(ANNOTATION_CONFIDENCE_VALUES), confidence,
        )

    # evidence: dict with file (str, non-empty), start (int >= 1), end (int >= start).
    evidence = annotation.get("evidence")
    if not isinstance(evidence, dict):
        return "evidence: must be a dict"
    ev_file = evidence.get("file")
    if not isinstance(ev_file, str) or ev_file.strip() == "":
        return "evidence.file: must be a non-empty string"
    ev_start = evidence.get("start")
    if not isinstance(ev_start, int) or isinstance(ev_start, bool):
        return "evidence.start: must be an int"
    if ev_start < 1:
        return "evidence.start: must be >= 1, got {0}".format(ev_start)
    ev_end = evidence.get("end")
    if not isinstance(ev_end, int) or isinstance(ev_end, bool):
        return "evidence.end: must be an int"
    if ev_end < ev_start:
        return "evidence.end: must be >= start ({0}), got {1}".format(
            ev_start, ev_end,
        )

    # model_version: non-empty single-line string.
    model_version = annotation.get("model_version")
    if not isinstance(model_version, str) or model_version.strip() == "":
        return "model_version: must be a non-empty string"

    # content_hash: exactly 64 lowercase hex chars (sha256).
    content_hash = annotation.get("content_hash")
    if not isinstance(content_hash, str):
        return "content_hash: must be a string"
    if not _SHA256_HEX_RE.match(content_hash):
        return (
            "content_hash: must be a 64-character lowercase hex string "
            "(sha256), got {0!r}".format(content_hash[:80])
        )

    return None


def _check_annotation_banned_phrase(label: str) -> Optional[str]:
    """Return the matched banned phrase token, or None if the label is clean.

    Whole-word, case-insensitive match. Multi-word phrases in BANNED_PHRASES
    (e.g. 'responsible for') are matched via re.escape so spaces and other
    metacharacters are treated as literals.
    """
    for phrase in BANNED_PHRASES:
        pattern = r"\b" + re.escape(phrase) + r"\b"
        if re.search(pattern, label, flags=re.IGNORECASE):
            return phrase
    return None


def _recompute_content_hash(path: Path, start: int, end: int) -> str:
    """Recompute sha256 of the inclusive 1-based line slice [start, end].

    Read text with errors='replace', split via splitlines() (strips line
    endings, handles CRLF/CR/LF uniformly), join the slice with '\\n', then
    sha256.hexdigest(). Same input -> same hash as the write-file-doc setter.

    Raises ValueError when start or end exceeds the file's line count so the
    caller can distinguish range-out-of-bounds from hash-drift.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    file_lines = text.splitlines()
    line_count = len(file_lines)
    if start > line_count:
        raise ValueError(
            "cite_start {0} exceeds file line count {1}".format(start, line_count)
        )
    if end > line_count:
        raise ValueError(
            "cite_end {0} exceeds file line count {1}".format(end, line_count)
        )
    slice_lines = file_lines[start - 1:end]
    joined = "\n".join(slice_lines)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _check_annotation_cite_resolves(
    annotation: Dict[str, Any], project_root: Path,
) -> Optional[Tuple[str, str]]:
    """Return (subcase, message) on failure, or None on success.

    Subcases and order:
      'missing' — file does not exist (also used for unreadable)
      'binary'  — first 8 KB contains a NUL byte (checked before hash)
      'range'   — line range out of bounds
      'hash_drift' — content changed since annotation was recorded

    The binary check precedes range/hash recompute: no point hashing a
    binary file, and the error message is more actionable.
    """
    evidence = annotation.get("evidence") or {}
    cite_file = evidence.get("file", "")
    start = evidence.get("start")
    end = evidence.get("end")
    stored_hash = annotation.get("content_hash", "")

    cite_path = project_root / cite_file

    # Sub-case 1: file not found.
    if not cite_path.exists() or not cite_path.is_file():
        return ("missing", "cite-file not found: {0}".format(cite_file))

    # Sub-case 2: binary (NUL byte in first 8192 bytes).
    try:
        with cite_path.open("rb") as fh:
            head = fh.read(8192)
    except OSError as err:
        return (
            "missing",
            "cite-file not readable: {0}: {1}".format(cite_file, err),
        )
    if b"\x00" in head:
        return (
            "binary",
            "cite-file is binary (NUL byte in first 8KB): {0}".format(cite_file),
        )

    # Sub-cases 3 & 4 require reading + hashing.
    try:
        recomputed = _recompute_content_hash(cite_path, start, end)
    except ValueError as err:
        return ("range", str(err))
    except OSError as err:
        return (
            "missing",
            "cite-file not readable: {0}: {1}".format(cite_file, err),
        )

    # Sub-case 4: hash drift.
    if recomputed != stored_hash:
        return (
            "hash_drift",
            "content_hash mismatch: cite-file changed since annotation was "
            "recorded (expected {0} got {1})".format(stored_hash, recomputed),
        )

    return None


# ---------------------------------------------------------------------------
# Step B.3 — Per-file-doc validation helpers and command.
# ---------------------------------------------------------------------------


def _check_file_doc_specificity(
    md_path: Path, current_label: str,
) -> Optional[str]:
    """Return an error message if a sibling .md shares a normalized label, or None.

    Walks `md_path.parent.glob("*.md")`, excluding `md_path` itself.
    For each sibling: parses front-matter and compares normalized labels
    (lower() + strip()). Sibling parse errors are silently skipped — the
    sibling will be flagged when it is independently validated.

    Only immediate siblings are checked (no recursive subdirectory scan)
    because each concern subdirectory is a scope boundary — sibling
    collisions within the same directory level are the relevant check.
    """
    this_label_norm = current_label.lower().strip()
    try:
        siblings = list(md_path.parent.glob("*.md"))
    except OSError:
        return None

    for sibling in siblings:
        if sibling.resolve() == md_path.resolve():
            continue
        try:
            sibling_text = sibling.read_text(encoding="utf-8", errors="replace")
            sibling_record, _ = parse_frontmatter(sibling_text)
        except (OSError, FrontmatterParseError):
            # Silently skip unparseable siblings per spec.
            continue
        sibling_label = sibling_record.get("label", "")
        if not isinstance(sibling_label, str):
            continue
        if sibling_label.lower().strip() == this_label_norm:
            return "label collides with sibling: {0!r} has same label".format(
                sibling.name
            )
    return None


def cmd_validate_file_doc(args: argparse.Namespace) -> int:
    """Mechanical gate for a per-source-file .md document (Step B.3).

    Reads the .md at `args.md_path`, parses front-matter, builds an
    annotation-shaped dict, then runs the same 4 helper checks as
    the old cmd_validate_annotation plus a directory-scoped specificity check.

    Exit codes:
      0 — all checks pass
      2 — banned-phrase hit in label
      3 — cite unresolvable (missing / range out-of-bounds / hash drift)
      4 — specificity fail (sibling label collision in same directory)
      5 — schema invalid OR file not found OR front-matter parse error
      6 — cite-file is binary
    """
    if not args.md_path or not args.md_path.strip():
        return _die("validate-file-doc: --md-path must be non-empty", code=5)

    md_path = Path(args.md_path)
    if not md_path.is_absolute():
        md_path = _project_root() / md_path

    # --- Read the .md file ---
    if not md_path.exists() or not md_path.is_file():
        return _die(
            "validate-file-doc: file not found: {0}".format(md_path), code=5,
        )

    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
    except OSError as err:
        return _die(
            "validate-file-doc: cannot read {0}: {1}".format(md_path, err), code=5,
        )

    # --- Parse front-matter ---
    try:
        fm_record, _ = parse_frontmatter(text)
    except FrontmatterParseError as err:
        return _die(
            "validate-file-doc: front-matter parse error: {0}".format(err), code=5,
        )

    # --- Build annotation-shaped dict for the 4 reused helpers ---
    # The 4 helpers (_check_annotation_schema, _check_annotation_banned_phrase,
    # _check_annotation_cite_resolves) expect the Part-A nested evidence shape.
    annotation = {
        "label": fm_record.get("label"),
        "confidence": fm_record.get("confidence"),
        "evidence": {
            "file": fm_record.get("evidence_file"),
            "start": fm_record.get("evidence_start"),
            "end": fm_record.get("evidence_end"),
        },
        "content_hash": fm_record.get("content_hash"),
        "model_version": fm_record.get("model_version"),
    }

    # Check 1 — Schema (exit 5).
    schema_err = _check_annotation_schema(annotation)
    if schema_err is not None:
        return _die(schema_err, code=5)

    # Check 2 — Banned phrase (exit 2).
    label = annotation.get("label", "")
    banned = _check_annotation_banned_phrase(label)
    if banned is not None:
        return _die(
            "label contains banned phrase: {0!r} in {1!r}".format(banned, label),
            code=2,
        )

    # Check 3 + 6 — Cite resolution (binary -> exit 6; all other -> exit 3).
    project_root = _project_root()
    cite_result = _check_annotation_cite_resolves(annotation, project_root)
    if cite_result is not None:
        subcase, msg = cite_result
        exit_code = 6 if subcase == "binary" else 3
        return _die(msg, code=exit_code)

    # Check 4 — Specificity vs sibling .md files in same directory (exit 4).
    sibling_err = _check_file_doc_specificity(md_path, label)
    if sibling_err is not None:
        return _die(sibling_err, code=4)

    sys.stdout.write("validate-file-doc {0}: ok\n".format(md_path))
    return 0


# ---------------------------------------------------------------------------
# Step B.4 — Post-batch aggregator: verify-file-docs
# ---------------------------------------------------------------------------


def cmd_verify_file_docs(args: argparse.Namespace) -> int:
    """Post-batch quality gate for all filled .md files in one concern's docs dir.

    Sources records from the filesystem (docs/<P>/<C>/**/*.md).
    Applies 4 hard gates with identical thresholds and exit codes.

    Empty .md skeletons (size == 0 bytes) are silently skipped — they count
    as "not yet filled" and are gated separately by validate-concern's
    file-docs-incomplete rule (B.2). B.4 evaluates only filled records.

    Exit codes:
      0 — all gates pass
      2 — at least one gate failed (stderr names which)
      5 — state error (package not registered, concern not registered,
          front-matter parse error in any filled md, or state-corrupt
          confidence value in any md's record)
    """
    try:
        state = _load_state()
    except StateLoadError as err:
        return _die(str(err), code=5)

    # Resolve package (exit 5 — state error, not a lookup miss).
    pkg = _require_package(state, args.package)
    if pkg is None:
        return _die(
            "package not registered: {0}".format(args.package), code=5,
        )

    # Resolve concern (exit 5 — state error).
    concern = _require_concern(state, args.package, args.concern)
    if concern is None:
        return _die(
            "concern not registered: {0}/{1}".format(args.package, args.concern),
            code=5,
        )

    project_root = _project_root()
    docs_dir = project_root / "docs" / args.package / args.concern

    # Collect (md_path, record) tuples from all filled (non-empty) .md files.
    file_doc_records = []  # type: ignore[var-annotated]

    if docs_dir.is_dir():
        for md_path in sorted(docs_dir.rglob("*.md")):
            # Skip zero-byte skeletons — they have no records to evaluate.
            # validate-concern's file-docs-incomplete rule gates them.
            try:
                size = md_path.stat().st_size
            except OSError:
                continue
            if size == 0:
                continue

            # Parse front-matter. Any parse error on a non-empty file is a
            # state error (the fill operation produced malformed output).
            try:
                text = md_path.read_text(encoding="utf-8", errors="replace")
            except OSError as err:
                return _die(
                    "file-doc read error in {0}: {1}; run write-file-doc again".format(
                        md_path, err
                    ),
                    code=5,
                )

            try:
                record, _ = parse_frontmatter(text)
            except FrontmatterParseError as err:
                return _die(
                    "file-doc parse error in {0}: {1}; run write-file-doc again".format(
                        md_path, err
                    ),
                    code=5,
                )

            file_doc_records.append((md_path, record))

    total = len(file_doc_records)

    # --- Metric 1: banned_phrase_count ---
    banned_phrase_count = 0
    for _md, record in file_doc_records:
        label = record.get("label", "") if isinstance(record, dict) else ""
        if isinstance(label, str) and _check_annotation_banned_phrase(label) is not None:
            banned_phrase_count += 1

    # --- Metric 2: sibling_collision_count ---
    # Count mds whose normalized label collides with ANY other md IN THE SAME
    # CONCERN'S DOCS TREE (concern-scoped, not directory-scoped). Each
    # colliding md is counted once.
    sibling_collision_count = 0
    for i, (md_path_i, record_i) in enumerate(file_doc_records):
        label_i = record_i.get("label", "")
        if not isinstance(label_i, str):
            continue
        norm_i = label_i.lower().strip()
        for j, (md_path_j, record_j) in enumerate(file_doc_records):
            if i == j:
                continue
            label_j = record_j.get("label", "")
            if not isinstance(label_j, str):
                continue
            if label_j.lower().strip() == norm_i:
                sibling_collision_count += 1
                break  # count each md at most once

    # --- Metric 3: missing_cite_count ---
    # File-exists pre-flight only (no hash recompute).
    missing_cite_count = 0
    for _md, record in file_doc_records:
        cite_file = record.get("evidence_file", "")
        if cite_file and isinstance(cite_file, str):
            cite_path = project_root / cite_file
            if not cite_path.exists() or not cite_path.is_file():
                missing_cite_count += 1

    # --- Metric 4: confidence_distribution ---
    # State-corrupt (unknown value) → exit 5.
    conf_dist = {"ambiguous": 0, "extracted": 0, "inferred": 0}
    for md_path, record in file_doc_records:
        conf = record.get("confidence")
        if conf not in ANNOTATION_CONFIDENCE_VALUES:
            return _die(
                "state-corrupt confidence value {0!r} in {1}; "
                "run write-file-doc again".format(conf, md_path),
                code=5,
            )
        conf_dist[conf] = conf_dist.get(conf, 0) + 1

    ambiguous_rate = conf_dist["ambiguous"] / total if total > 0 else 0.0

    # --- Metric 5: cross_concern_duplicate_count ---
    # Walk all OTHER concern dirs under the same package's docs dir.
    # Parse each sibling md (skip empty / parse errors silently — they surface
    # in their own concern's verify-file-docs run). Build union of normalized
    # labels from those dirs, then count how many of the current concern's
    # records appear in that union.
    all_concern_dirs = []
    package_docs_dir = project_root / "docs" / args.package
    if package_docs_dir.is_dir():
        for entry in package_docs_dir.iterdir():
            if entry.is_dir() and entry.name != args.concern:
                all_concern_dirs.append(entry)

    other_labels = set()  # type: ignore[var-annotated]
    for other_dir in all_concern_dirs:
        for sibling_md in other_dir.rglob("*.md"):
            try:
                ssize = sibling_md.stat().st_size
            except OSError:
                continue
            if ssize == 0:
                continue
            try:
                stext = sibling_md.read_text(encoding="utf-8", errors="replace")
                srec, _ = parse_frontmatter(stext)
            except (OSError, FrontmatterParseError):
                # Silently skip — these surface in the other concern's run.
                continue
            slabel = srec.get("label", "")
            if isinstance(slabel, str) and slabel.strip():
                other_labels.add(slabel.lower().strip())

    cross_concern_duplicate_count = 0
    for _md, record in file_doc_records:
        label = record.get("label", "")
        if isinstance(label, str) and label.lower().strip() in other_labels:
            cross_concern_duplicate_count += 1

    cross_concern_duplicate_rate = (
        cross_concern_duplicate_count / total if total > 0 else 0.0
    )

    # --- Gate evaluation ---
    gate_banned = "pass" if banned_phrase_count == 0 else "fail"
    gate_ambiguous = (
        "pass" if ambiguous_rate <= AMBIGUOUS_RATE_THRESHOLD else "fail"
    )
    gate_cross = (
        "pass"
        if cross_concern_duplicate_rate <= CROSS_CONCERN_DUPLICATE_RATE_THRESHOLD
        else "fail"
    )

    # --- Gate: vacuous_pass ---
    # A concern with a non-empty directory_tree but zero filled mds is a
    # vacuous pass: the orchestrator skipped the fill loop entirely.
    # A concern with no tree set (None or empty) is legitimately empty.
    directory_tree = concern.get("directory_tree") or ""
    if directory_tree and total == 0:
        gate_vacuous = "fail"
    else:
        gate_vacuous = "pass"

    report = {
        "ambiguous_rate": ambiguous_rate,
        "banned_phrase_count": banned_phrase_count,
        "concern": args.concern,
        "confidence_distribution": conf_dist,
        "cross_concern_duplicate_count": cross_concern_duplicate_count,
        "cross_concern_duplicate_rate": cross_concern_duplicate_rate,
        "gates": {
            "ambiguous_rate": gate_ambiguous,
            "banned_phrase": gate_banned,
            "cross_concern_duplicate": gate_cross,
            "vacuous_pass": gate_vacuous,
        },
        "missing_cite_count": missing_cite_count,
        "package": args.package,
        "sibling_collision_count": sibling_collision_count,
        "total_md_files": total,
    }

    sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")

    # Emit one stderr line per failed gate; collect all failures before exiting.
    any_fail = False

    if gate_banned == "fail":
        any_fail = True
        sys.stderr.write(
            "verify-file-docs: banned_phrase gate FAIL: "
            "{0} md file(s) contain banned phrases\n".format(banned_phrase_count)
        )

    if gate_ambiguous == "fail":
        any_fail = True
        pct = round(ambiguous_rate * 100, 1)
        sys.stderr.write(
            "verify-file-docs: ambiguous_rate gate FAIL: "
            "{0}% (threshold: 10%)\n".format(pct)
        )

    if gate_cross == "fail":
        any_fail = True
        pct = round(cross_concern_duplicate_rate * 100, 1)
        sys.stderr.write(
            "verify-file-docs: cross_concern_duplicate gate FAIL: "
            "{0}% (threshold: 5%)\n".format(pct)
        )

    if gate_vacuous == "fail":
        any_fail = True
        sys.stderr.write(
            "verify-file-docs: vacuous_pass gate FAIL: "
            "concern has tree but zero filled md files\n"
        )

    return 2 if any_fail else 0
