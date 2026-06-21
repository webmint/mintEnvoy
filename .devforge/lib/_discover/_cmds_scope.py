"""Phase 0 scope handlers: dimension setters + references + gaps + conflicts + coverage + finalize."""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Tuple

from ._state import (
    RUBRIC_DIMENSIONS,
    RUBRIC_STATE_DEFAULT,
    _empty_dimension,
    _load_memo,
    _state_transaction,
)
from ._topic import _compute_scope_coverage, _detect_scope_conflicts
from ._validators import _die, _validate_scalar


def _make_scope_dim_setter(dimension: str):
    """Closure factory for set-scope-<dim> subcommands.

    Returns a handler that writes args.value + args.state into
    memo.dimensions[dimension] and optionally increments turns.
    """

    def _handler(args: argparse.Namespace) -> int:
        try:
            value = _validate_scalar(args.value, "set-scope-" + dimension)
        except ValueError as err:
            return _die(str(err), code=2)
        try:
            with _state_transaction(args.devforge_dir, "memo") as memo:
                rec = memo["dimensions"].get(dimension)
                if not isinstance(rec, dict):
                    rec = _empty_dimension()
                rec["value"] = value
                rec["state"] = args.state
                if getattr(args, "increment_turn", False):
                    rec["turns"] = int(rec.get("turns", 0)) + 1
                memo["dimensions"][dimension] = rec
        except (OSError, json.JSONDecodeError) as err:
            return _die("set-scope-{0}: {1}".format(dimension, err))
        return 0

    return _handler


def cmd_record_references(args: argparse.Namespace) -> int:
    """Replace memo.references with a JSON-array-of-strings payload."""
    try:
        decoded = json.loads(args.values)
    except ValueError as err:
        return _die("record-references: --values is not valid JSON: {0}".format(err), code=2)
    if not isinstance(decoded, list):
        return _die(
            "record-references: --values must decode to a JSON array, got {0}".format(
                type(decoded).__name__
            ),
            code=2,
        )
    cleaned = []  # type: List[str]
    for item in decoded:
        if not isinstance(item, str):
            return _die(
                "record-references: every item must be a string, got {0}".format(
                    type(item).__name__
                ),
                code=2,
            )
        cleaned.append(item)
    try:
        with _state_transaction(args.devforge_dir, "memo") as memo:
            memo["references"] = cleaned
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-references: {0}".format(err))
    return 0


def cmd_record_gap(args: argparse.Namespace) -> int:
    """Append or replace a {dimension, description} gap entry in memo.gaps."""
    try:
        description = _validate_scalar(args.description, "record-gap.description")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "memo") as memo:
            gaps = memo.get("gaps", [])
            # Replace existing gap for this dimension (idempotent), else append.
            replaced = False
            for entry in gaps:
                if isinstance(entry, dict) and entry.get("dimension") == args.dimension:
                    entry["description"] = description
                    replaced = True
                    break
            if not replaced:
                gaps.append({"dimension": args.dimension, "description": description})
            memo["gaps"] = gaps
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-gap: {0}".format(err))
    return 0


def _filter_unresolved(detected: List[dict], existing: List[dict]) -> List[dict]:
    """Drop detected conflicts whose (dimensions-pair) is already resolved."""
    resolved_pairs = set()
    for entry in existing:
        if not isinstance(entry, dict):
            continue
        if entry.get("resolution") is None:
            continue
        dims = entry.get("dimensions") or []
        if isinstance(dims, list) and len(dims) == 2:
            resolved_pairs.add((dims[0], dims[1]))
    out = []
    for c in detected:
        dims = c.get("dimensions", [])
        key = (dims[0], dims[1]) if len(dims) == 2 else None
        if key is not None and key in resolved_pairs:
            continue
        out.append(c)
    return out


def cmd_check_conflicts(args: argparse.Namespace) -> int:
    """Emit JSON array of currently-detectable direct contradictions. Read-only."""
    try:
        memo = _load_memo(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("check-conflicts: {0}".format(err))
    detected = _detect_scope_conflicts(memo)
    existing = memo.get("conflicts", []) or []
    filtered = _filter_unresolved(detected, existing)
    json.dump(filtered, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


def cmd_record_conflict_resolution(args: argparse.Namespace) -> int:
    """Persist a user-chosen resolution and clear the loser dimension.

    If state.conflicts is empty, run detect first and append the detected
    conflicts; then apply the resolution at --index. Out-of-range index
    after that is exit 2.
    """
    try:
        with _state_transaction(args.devforge_dir, "memo") as memo:
            conflicts = memo.get("conflicts") or []
            if not conflicts:
                detected = _detect_scope_conflicts(memo)
                if not detected:
                    return _die(
                        "record-conflict-resolution: --index {0} out of range; "
                        "check-conflicts must be called first OR no conflicts exist.".format(
                            args.index
                        ),
                        code=2,
                    )
                conflicts = list(detected)
                memo["conflicts"] = conflicts
            if args.index < 0 or args.index >= len(conflicts):
                return _die(
                    "record-conflict-resolution: --index {0} out of range "
                    "(0..{1}); check-conflicts must be called first.".format(
                        args.index, len(conflicts) - 1
                    ),
                    code=2,
                )
            conflicts[args.index]["resolution"] = args.resolution
            memo["dimensions"][args.rewrite_dimension] = _empty_dimension()
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-conflict-resolution: {0}".format(err))
    return 0


def cmd_scope_coverage(args: argparse.Namespace) -> int:
    """Emit JSON coverage report on stdout. Read-only."""
    try:
        memo = _load_memo(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("scope-coverage: {0}".format(err))
    state_map, clear, partial, missing = _compute_scope_coverage(memo)
    per_dimension = {}
    dims = memo.get("dimensions", {})
    for d in RUBRIC_DIMENSIONS:
        rec = dims.get(d, _empty_dimension())
        per_dimension[d] = {
            "state": state_map[d],
            "value": rec.get("value"),
            "turns": int(rec.get("turns", 0)),
        }
    conflicts = memo.get("conflicts") or []
    open_conflicts = sum(
        1 for c in conflicts
        if isinstance(c, dict) and c.get("resolution") is None
    )
    payload = {
        "per_dimension": per_dimension,
        "counts": {"Clear": clear, "Partial": partial, "Missing": missing},
        "references_count": len(memo.get("references") or []),
        "gaps_count": len(memo.get("gaps") or []),
        "conflicts_open": open_conflicts,
    }
    json.dump(payload, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


def cmd_scope_finalize(args: argparse.Namespace) -> int:
    """Validate memo is finalize-ready. Exit 0 = ready, 2 = blocked.

    Open conflicts always block (regardless of --accept-gaps).
    Partial/Missing dimensions block unless --accept-gaps is passed;
    when passed, sets memo.override_recorded = True.
    """
    try:
        with _state_transaction(args.devforge_dir, "memo") as memo:
            conflicts = memo.get("conflicts") or []
            open_indices = [
                i for i, c in enumerate(conflicts)
                if isinstance(c, dict) and c.get("resolution") is None
            ]
            dims = memo.get("dimensions", {})
            offending = []  # type: List[Tuple[str, str]]
            for d in RUBRIC_DIMENSIONS:
                rec = dims.get(d, _empty_dimension())
                st = rec.get("state", RUBRIC_STATE_DEFAULT)
                if st in ("Partial", "Missing"):
                    offending.append((d, st))

            violations = []  # type: List[str]
            for i in open_indices:
                violations.append(
                    "Unresolved conflict at index {0}; resolve via "
                    "record-conflict-resolution.".format(i)
                )
            if not args.accept_gaps:
                for d, st in offending:
                    violations.append(
                        "Dimension '{0}' is {1}; pass --accept-gaps to proceed.".format(
                            d, st
                        )
                    )
            else:
                if not open_indices:
                    memo["override_recorded"] = True

            if violations:
                for v in violations:
                    sys.stderr.write("scope-finalize: {0}\n".format(v))
                raise _FinalizeBlocked()
    except _FinalizeBlocked:
        return 2
    except (OSError, json.JSONDecodeError) as err:
        return _die("scope-finalize: {0}".format(err))
    return 0


class _FinalizeBlocked(Exception):
    """Sentinel to abort the scope-finalize transaction without writing."""
