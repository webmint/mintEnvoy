"""Phase 0 + Phase 1 + Phase 1.5 cmd_* handlers + detect_mode helper."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ._schema import (
    AUTO_MODE_ENV_VAR,
    AUTO_MODE_REMINDER_SUBSTRINGS,
    CONSTITUTION_POPULATE_GUARD,
    LANDED_IN_DEFAULT,
    LANDED_IN_ENUM,
    PHASE1_MANDATORY_READS,
    PREFLIGHT_PREREQS,
    _RENDER_SECTION_ORDER,
)
from ._state import (
    _atomic_write_json,
    _load_state,
    _state_path,
    _state_transaction,
    default_state,
)
from ._topic import source_origin_for_path
from ._validators import _die, _utc_timestamp, _validate_enum, _validate_scalar


def cmd_reset_state(args: argparse.Namespace) -> int:
    """Reset .devforge/specify-state.json to default. Idempotent."""
    try:
        _atomic_write_json(default_state(), _state_path(args.devforge_dir))
    except OSError as err:
        return _die("reset-state: {0}".format(err))
    return 0


def cmd_read_state(args: argparse.Namespace) -> int:
    """Dump current state as JSON to stdout."""
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("read-state: {0}".format(err))
    json.dump(state, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


def cmd_preflight(args: argparse.Namespace) -> int:
    """4-artefact hard gate + constitution populate-guard."""
    install_root = Path(args.install_root)
    missing: List[Tuple[str, str]] = []
    populate_guard_present = False
    for rel_path, producer in PREFLIGHT_PREREQS:
        p = install_root / rel_path
        try:
            if not p.exists():
                missing.append((rel_path, producer))
                continue
            if p.stat().st_size == 0:
                missing.append((rel_path, producer))
                continue
        except OSError as err:
            return _die("preflight: stat failed on {0}: {1}".format(p, err))
        if rel_path == "constitution.md":
            try:
                text = p.read_text(encoding="utf-8")
            except OSError as err:
                return _die(
                    "preflight: read failed on {0}: {1}".format(p, err)
                )
            if CONSTITUTION_POPULATE_GUARD in text:
                populate_guard_present = True

    if missing or populate_guard_present:
        sys.stderr.write(
            "BLOCKED: /specify requires the full 4-command setup chain.\n"
        )
        for rel, producer in missing:
            sys.stderr.write(
                "Missing: {0} (produced by {1})\n".format(rel, producer)
            )
        if populate_guard_present:
            sys.stderr.write(
                "constitution.md present but populate-guard literal "
                "{0!r} still in place — run /constitute to populate.\n".format(
                    CONSTITUTION_POPULATE_GUARD,
                )
            )
        sys.stderr.write(
            "Run: /init-forge → /generate-docs → /configure → /constitute, "
            "then retry /specify.\n"
        )
        return 2
    return 0


def cmd_record_input_read(args: argparse.Namespace) -> int:
    """Record one Phase 1 input read; auto-tag source_origin from path.

    Idempotent: re-recording the same path overwrites the prior entry.
    """
    try:
        path = _validate_scalar(args.path, "record-input-read.path")
    except ValueError as err:
        return _die(str(err), code=2)
    origin = source_origin_for_path(path)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["input_reads"] = [
                r for r in state["input_reads"] if r.get("path") != path
            ]
            state["input_reads"].append({
                "path": path,
                "source_origin": origin,
                "read_timestamp": _utc_timestamp(),
            })
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-input-read: {0}".format(err))
    return 0


def cmd_phase1_finalize(args: argparse.Namespace) -> int:
    """Gate Phase 1 → Phase 1.5. All 4 mandatory base reads required."""
    try:
        with _state_transaction(args.devforge_dir) as state:
            read_paths = {r.get("path") for r in state["input_reads"]}
            missing = [
                m for m in PHASE1_MANDATORY_READS if m not in read_paths
            ]
            if missing:
                sys.stderr.write(
                    "phase1-finalize: missing mandatory input reads:\n"
                )
                for m in missing:
                    sys.stderr.write("  - {0}\n".format(m))
                return 2
            state["phase1_finalized"] = True
    except (OSError, json.JSONDecodeError) as err:
        return _die("phase1-finalize: {0}".format(err))
    return 0


def _finding_slug(source_path: str) -> str:
    """Derive the source-slug used in F-<slug>-N finding ids."""
    stem = Path(source_path).stem.lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", stem).strip("-")
    return cleaned or "src"


def _next_finding_id(state: Dict[str, Any], source_path: str) -> str:
    slug = _finding_slug(source_path)
    prefix = "F-{0}-".format(slug)
    n = 1 + sum(
        1 for f in state["findings"]
        if f.get("finding_id", "").startswith(prefix)
    )
    return "{0}{1}".format(prefix, n)


def cmd_record_finding(args: argparse.Namespace) -> int:
    """Record one Phase 1.5 finding. Auto-clears no-items-relevant marker."""
    try:
        source_path = _validate_scalar(args.source_path, "source_path")
        content = _validate_scalar(args.content, "content")
        landed_in = args.landed_in or LANDED_IN_DEFAULT
        _validate_enum(landed_in, "landed_in", LANDED_IN_ENUM)
    except ValueError as err:
        return _die(str(err), code=2)
    source_section = (args.source_section or "").strip()
    landed_ref = (args.landed_ref or "").strip()
    try:
        with _state_transaction(args.devforge_dir) as state:
            fid = _next_finding_id(state, source_path)
            state["findings"].append({
                "finding_id": fid,
                "source_path": source_path,
                "source_section": source_section,
                "content": content,
                "landed_in": landed_in,
                "landed_ref": landed_ref,
            })
            if source_path in state["source_no_items_relevant"]:
                del state["source_no_items_relevant"][source_path]
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-finding: {0}".format(err))
    sys.stdout.write(fid + "\n")
    return 0


def cmd_mark_source_no_items_relevant(args: argparse.Namespace) -> int:
    """Mark a read source as having no task-relevant content."""
    try:
        source_path = _validate_scalar(args.source_path, "source_path")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            read_paths = {r.get("path") for r in state["input_reads"]}
            if source_path not in read_paths:
                return _die(
                    "mark-source-no-items-relevant: {0!r} not in "
                    "input_reads (record-input-read first)".format(
                        source_path,
                    ),
                    code=2,
                )
            if any(
                f.get("source_path") == source_path
                for f in state["findings"]
            ):
                return _die(
                    "mark-source-no-items-relevant: {0!r} already has "
                    "findings".format(source_path),
                    code=2,
                )
            state["source_no_items_relevant"][source_path] = True
    except (OSError, json.JSONDecodeError) as err:
        return _die("mark-source-no-items-relevant: {0}".format(err))
    return 0


def _source_coverage(
    state: Dict[str, Any], path: str,
) -> Tuple[str, int]:
    """Return (status, n_findings). status ∈ {clear, partial, marker, none}."""
    count = sum(
        1 for f in state["findings"] if f.get("source_path") == path
    )
    if count >= 3:
        return ("clear", count)
    if count >= 1:
        return ("partial", count)
    if state["source_no_items_relevant"].get(path):
        return ("marker", 0)
    return ("none", 0)


def cmd_verify_findings(args: argparse.Namespace) -> int:
    """Per-source: ≥3 findings OR no-items-relevant marker. Variance rule #3."""
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("verify-findings: {0}".format(err))
    problems: List[Tuple[str, str, int]] = []
    for r in state["input_reads"]:
        path = r.get("path")
        status, count = _source_coverage(state, path)
        if status in ("partial", "none"):
            problems.append((path, status, count))
    if problems:
        sys.stderr.write(
            "verify-findings: insufficient findings per source:\n"
        )
        for path, status, count in problems:
            sys.stderr.write(
                "  - {0}: {1} ({2} findings; need ≥3 or "
                "no-items-relevant marker)\n".format(path, status, count)
            )
        return 2
    return 0


def _group_for_path(path: str) -> str:
    """Map a recorded input path to its render-group key."""
    p = path.strip()
    if p.startswith("./"):
        p = p[2:]
    for prefix in ("research/", "discover/", "docs/", "specs/"):
        if p.startswith(prefix):
            return prefix
    return p


def cmd_render_findings(args: argparse.Namespace) -> int:
    """Emit Phase 1.5 findings section in v3-verbatim format."""
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("render-findings: {0}".format(err))
    lines: List[str] = ["## Findings from Inputs", ""]
    reads_by_group: Dict[str, List[str]] = {}
    for r in state["input_reads"]:
        g = _group_for_path(r.get("path", ""))
        reads_by_group.setdefault(g, []).append(r["path"])

    for group in _RENDER_SECTION_ORDER:
        paths = sorted(reads_by_group.get(group, []))
        if not paths:
            continue
        for path in paths:
            lines.append("### From {0}".format(path))
            f_for_path = [
                f for f in state["findings"]
                if f.get("source_path") == path
            ]
            f_for_path.sort(key=lambda f: f.get("finding_id", ""))
            if f_for_path:
                for i, f in enumerate(f_for_path, 1):
                    lines.append("{0}. {1}".format(i, f.get("content", "")))
            elif state["source_no_items_relevant"].get(path):
                lines.append("No items relevant to this spec.")
            else:
                lines.append("_(no findings recorded yet)_")
            lines.append("")

    sys.stdout.write("\n".join(lines).rstrip() + "\n")
    return 0


def cmd_findings_finalize(args: argparse.Namespace) -> int:
    """Gate Phase 1.5 → Phase 2. Re-runs verify-findings then stamps."""
    rc = cmd_verify_findings(args)
    if rc != 0:
        return rc
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["findings_finalized"] = True
    except (OSError, json.JSONDecodeError) as err:
        return _die("findings-finalize: {0}".format(err))
    return 0


def detect_mode(
    env: Dict[str, str],
    auto_flag: bool,
    reminder_text: str,
) -> str:
    """C-strict mode detection (Variance rule #8). Three signals:

      - DEVFORGE_AUTO_MODE env var == "1"
      - --auto flag set
      - case-insensitive substring of any AUTO_MODE_REMINDER_SUBSTRINGS in
        the supplied reminder_text

    No LLM judgment — defaults to "interactive" when no signal fires.
    """
    if env.get(AUTO_MODE_ENV_VAR) == "1":
        return "auto"
    if auto_flag:
        return "auto"
    if reminder_text:
        haystack = reminder_text.lower()
        for needle in AUTO_MODE_REMINDER_SUBSTRINGS:
            if needle in haystack:
                return "auto"
    return "interactive"


def cmd_detect_mode(args: argparse.Namespace) -> int:
    """Resolve mode from C-strict signals, persist, print to stdout."""
    mode = detect_mode(
        os.environ,
        bool(args.auto),
        args.reminder_text or "",
    )
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["mode"] = mode
    except (OSError, json.JSONDecodeError) as err:
        return _die("detect-mode: {0}".format(err))
    sys.stdout.write(mode + "\n")
    return 0
