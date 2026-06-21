"""Phase 3 cmd_* handlers + cross-phase cmd_summary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ._cmds_phase2 import _category_state
from ._schema import (
    DP_CATEGORY_ENUM,
    DP_STATUS_ENUM,
    MANDATORY_READS_BY_TYPE,
    SPEC_TYPE_ENUM,
)
from ._state import _load_state, _state_transaction
from ._validators import _die, _validate_enum, _validate_scalar


def _slot_matches_path(slot_pattern: str, read_path: str) -> bool:
    """Return True iff `read_path` satisfies `slot_pattern`."""
    if slot_pattern.startswith("__") and slot_pattern.endswith("__"):
        return False
    try:
        if Path(read_path).match(slot_pattern):
            return True
    except (ValueError, TypeError):
        pass
    # Substring fallback for path-suffix matches like `.github/workflows/*`.
    base = slot_pattern.rstrip("*").rstrip("/")
    if base and base in read_path:
        return True
    return False


def cmd_classify_spec_type(args: argparse.Namespace) -> int:
    """Set spec_type + rationale. Helper does NOT auto-derive the type."""
    try:
        spec_type = _validate_enum(
            args.spec_type, "spec_type", SPEC_TYPE_ENUM,
        )
        rationale = _validate_scalar(args.rationale, "rationale")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["spec_type"] = spec_type
            state["spec_type_rationale"] = rationale
            state["spec_type_seeded_by_upstream"] = bool(
                args.seeded_by_upstream
            )
    except (OSError, json.JSONDecodeError) as err:
        return _die("classify-spec-type: {0}".format(err))
    return 0


def cmd_record_mandatory_read(args: argparse.Namespace) -> int:
    """Record a Phase 3 per-spec-type mandatory-read entry."""
    has_read = bool(args.read_path)
    has_na = bool(args.n_a_reason)
    if has_read and has_na:
        return _die(
            "record-mandatory-read: --read-path and --n-a-reason are "
            "mutually exclusive",
            code=2,
        )
    if not has_read and not has_na:
        return _die(
            "record-mandatory-read: one of --read-path / --n-a-reason "
            "required",
            code=2,
        )
    try:
        with _state_transaction(args.devforge_dir) as state:
            spec_type = state.get("spec_type")
            if not spec_type:
                return _die(
                    "record-mandatory-read: spec_type unset "
                    "(call classify-spec-type first)",
                    code=2,
                )
            entry: Dict[str, Any] = {
                "spec_type": spec_type,
                "read_path": "",
                "slot_pattern": "",
                "n_a_reason": "",
            }
            if has_read:
                entry["read_path"] = args.read_path.strip()
                entry["slot_pattern"] = (args.slot_pattern or "").strip()
            else:
                if not args.slot_pattern:
                    return _die(
                        "record-mandatory-read: --n-a-reason requires "
                        "--slot-pattern",
                        code=2,
                    )
                entry["slot_pattern"] = args.slot_pattern.strip()
                entry["n_a_reason"] = args.n_a_reason.strip()
            state["mandatory_reads"].append(entry)
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-mandatory-read: {0}".format(err))
    return 0


def _slot_covered(
    state: Dict[str, Any], slot_pattern: str,
) -> bool:
    for e in state["mandatory_reads"]:
        if e.get("n_a_reason") and e.get("slot_pattern") == slot_pattern:
            return True
        rp = e.get("read_path", "")
        if not rp:
            continue
        if e.get("slot_pattern") == slot_pattern:
            return True
        if _slot_matches_path(slot_pattern, rp):
            return True
    return False


def cmd_verify_mandatory_reads(args: argparse.Namespace) -> int:
    """Walk MANDATORY_READS_BY_TYPE[spec_type]; every slot must be covered."""
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("verify-mandatory-reads: {0}".format(err))
    spec_type = state.get("spec_type")
    if not spec_type:
        return _die(
            "verify-mandatory-reads: spec_type unset "
            "(call classify-spec-type first)",
            code=2,
        )
    if spec_type not in MANDATORY_READS_BY_TYPE:
        return _die(
            "verify-mandatory-reads: no mandatory-read table for "
            "spec_type {0!r}".format(spec_type),
            code=2,
        )
    missing: List[Tuple[str, str]] = []
    for slot_pattern, description in MANDATORY_READS_BY_TYPE[spec_type]:
        if not _slot_covered(state, slot_pattern):
            missing.append((slot_pattern, description))
    if missing:
        sys.stderr.write(
            "verify-mandatory-reads: missing slots for spec_type "
            "{0!r}:\n".format(spec_type)
        )
        for slot, desc in missing:
            sys.stderr.write("  - {0} — {1}\n".format(slot, desc))
        return 2
    return 0


def cmd_phase3_finalize(args: argparse.Namespace) -> int:
    """Gate Phase 3 → Phase 4. Re-runs verify-mandatory-reads + stamps."""
    rc = cmd_verify_mandatory_reads(args)
    if rc != 0:
        return rc
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["phase3_finalized"] = True
    except (OSError, json.JSONDecodeError) as err:
        return _die("phase3-finalize: {0}".format(err))
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    """Emit phase-progress + counts dashboard JSON."""
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("summary: {0}".format(err))

    dp_status_counts: Dict[str, int] = {s: 0 for s in DP_STATUS_ENUM}
    for d in state["decision_points"]:
        st = d.get("status")
        if st in dp_status_counts:
            dp_status_counts[st] += 1

    rubric: Dict[str, str] = {
        cat: _category_state(state, cat) for cat in DP_CATEGORY_ENUM
    }

    out = {
        "topic": state.get("topic"),
        "spec_type": state.get("spec_type"),
        "spec_type_seeded_by_upstream": state.get(
            "spec_type_seeded_by_upstream", False,
        ),
        "status": state.get("status"),
        "mode": state.get("mode"),
        "phase_finalized": {
            "phase1": bool(state.get("phase1_finalized")),
            "findings": bool(state.get("findings_finalized")),
            "dp": bool(state.get("dp_finalized")),
            "phase3": bool(state.get("phase3_finalized")),
        },
        "counts": {
            "input_reads": len(state.get("input_reads", [])),
            "findings": len(state.get("findings", [])),
            "decision_points": len(state.get("decision_points", [])),
            "decision_points_by_status": dp_status_counts,
            "mandatory_reads": len(state.get("mandatory_reads", [])),
            "discretionary_reads": len(state.get("discretionary_reads", [])),
            "affected_areas": len(state.get("affected_areas", [])),
            "acceptance_criteria": len(state.get("acceptance_criteria", [])),
            "out_of_scope": len(state.get("out_of_scope", [])),
            "constraints": len(state.get("constraints", [])),
            "open_questions": len(state.get("open_questions", [])),
            "risks": len(state.get("risks", [])),
            "conflicts": len(state.get("conflicts", [])),
        },
        "rubric_coverage": rubric,
    }
    json.dump(out, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0
