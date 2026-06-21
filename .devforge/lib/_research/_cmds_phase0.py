"""Phase 0 (symptom clarification) command handlers.

Per-dimension setter factory (_make_dim_setter + _make_scope_setter for
the 'one place' evidence gate). detect-mode, record-gap, check-conflicts,
record-conflict-resolution, symptom-coverage, symptom-finalize.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List

from ._constants import (
    RUBRIC_STATE_DEFAULT,
    RUBRIC_STATE_ENUM,
    TURN_CAP,
)
from ._state import _empty_dimension, _state_transaction
from ._topic_conflicts import (
    _compute_coverage,
    derive_topic_slug,
    detect_direct_conflicts,
    detect_mode_from_symptom,
)
from ._validators import (
    _die,
    _validate_enum,
    _validate_file_line,
    _validate_scalar,
    _validate_verbatim,
)


# --- Phase 0 setter factory --------------------------------------------------


def _make_dim_setter(dim_name: str):
    """Build a setter handler for one rubric dimension.

    Each setter validates value (verbatim non-empty) + state enum +
    optionally increments turn counter, then writes back into
    memo.dimensions[dim_name]. As a side-effect, setting the `symptom`
    dimension auto-derives memo.topic_slug if not already set.
    """
    def handler(args: argparse.Namespace) -> int:
        try:
            value = _validate_verbatim(args.value, dim_name)
            state = _validate_enum(args.state, dim_name + ".state", RUBRIC_STATE_ENUM)
        except ValueError as err:
            return _die(str(err), code=2)
        try:
            with _state_transaction(args.devforge_dir, "memo") as memo:
                rec = memo["dimensions"].get(dim_name) or _empty_dimension()
                rec["value"] = value
                # Bounded-turn cap: once turns >= TURN_CAP and the caller
                # didn't explicitly mark Clear, dimension stays Partial.
                if args.increment_turn:
                    rec["turns"] = int(rec.get("turns", 0)) + 1
                if state == "Clear":
                    rec["state"] = "Clear"
                elif rec["turns"] >= TURN_CAP and state != "Clear":
                    rec["state"] = "Partial"
                else:
                    rec["state"] = state
                memo["dimensions"][dim_name] = rec
                if dim_name == "symptom" and not memo.get("topic_slug"):
                    memo["topic_slug"] = derive_topic_slug(value)
        except (OSError, json.JSONDecodeError) as err:
            return _die("set-{0}: {1}".format(dim_name, err))
        return 0
    handler.__name__ = "cmd_set_" + dim_name
    return handler


def _make_scope_setter():
    """Build the set-scope handler with the 'one place' evidence gate.

    Wraps _make_dim_setter("scope") with a pre-flight check: when --value
    normalizes to 'one place' (case-insensitive, whitespace-stripped), an
    --evidence flag carrying a valid file:line citation is required.
    Narrowing scope to 'one place' gates Phase 2 exploration depth before
    Phase 2 runs — forcing a citation ensures the LLM verifies locality
    before committing to the narrow framing.

    For all other scope values, --evidence is silently ignored (not stored)
    so the dim record stays shape-stable across wide vs narrow framings.
    """
    inner = _make_dim_setter("scope")

    def handler(args: argparse.Namespace) -> int:
        normalized = (args.value or "").strip().lower()
        if normalized == "one place":
            evidence = getattr(args, "evidence", None)
            # Treat empty string identically to missing.
            if not evidence or not evidence.strip():
                sys.stderr.write(
                    "set-scope: --evidence is required when --value == 'one place'. "
                    "Narrowing scope to 'one place' gates Phase 2 exploration depth "
                    "before Phase 2 runs — cite a file:line proving the symptom is "
                    "localized (typically the single symptom site).\n"
                )
                return 2
            try:
                evidence_validated = _validate_file_line(evidence.strip(), "scope.evidence")
            except ValueError as err:
                return _die(str(err), code=2)
            if evidence_validated == "(none)":
                sys.stderr.write(
                    "set-scope: --evidence cannot be '(none)' when --value == 'one place'; "
                    "narrow framing requires a concrete file:line citation.\n"
                )
                return 2
            # Write the dimension record via the inner setter.
            rc = inner(args)
            if rc != 0:
                return rc
            # Append evidence to the scope dim record (second transaction).
            try:
                with _state_transaction(args.devforge_dir, "memo") as memo:
                    rec = memo["dimensions"].get("scope") or _empty_dimension()
                    rec["evidence"] = evidence_validated
                    memo["dimensions"]["scope"] = rec
            except (OSError, json.JSONDecodeError) as err:
                return _die("set-scope: {0}".format(err))
            return 0
        # Non-narrow framing — evidence is optional and not stored.
        return inner(args)

    handler.__name__ = "cmd_set_scope"
    return handler


def cmd_detect_mode(args: argparse.Namespace) -> int:
    """Detect mode from symptom dimension OR apply --override.

    Stdout: JSON {"mode": "bug" | "enhancement" | null, "source": "auto" |
    "override" | "ambiguous"}. Exits 0 always (caller decides how to
    handle ambiguous result). Persists mode into memo.mode on a clear
    detection.
    """
    try:
        with _state_transaction(args.devforge_dir, "memo") as memo:
            if args.override:
                mode = args.override
                source = "override"
            else:
                symptom_val = memo.get("dimensions", {}).get("symptom", {}).get("value") or ""
                mode = detect_mode_from_symptom(symptom_val)
                source = "auto" if mode else "ambiguous"
            memo["mode"] = mode
    except (OSError, json.JSONDecodeError) as err:
        return _die("detect-mode: {0}".format(err))
    json.dump({"mode": mode, "source": source}, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


def cmd_record_gap(args: argparse.Namespace) -> int:
    """Append a {dimension, description} gap; set dimension state to Partial."""
    try:
        desc = _validate_scalar(args.description, "gap.description")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "memo") as memo:
            memo.setdefault("gaps", []).append(
                {"dimension": args.dimension, "description": desc}
            )
            rec = memo["dimensions"].get(args.dimension) or _empty_dimension()
            if rec.get("state") != "Clear":
                rec["state"] = "Partial"
            memo["dimensions"][args.dimension] = rec
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-gap: {0}".format(err))
    return 0


def cmd_check_conflicts(args: argparse.Namespace) -> int:
    """Scan memo for direct contradictions; emit JSON list to stdout.

    Detected conflicts are appended to memo.conflicts (idempotent on
    description text) and emitted as JSON. Caller uses the list to drive
    AskUserQuestion for direct contradictions.
    """
    try:
        with _state_transaction(args.devforge_dir, "memo") as memo:
            detected = detect_direct_conflicts(memo)
            existing_descs = {c.get("description") for c in memo.get("conflicts", [])}
            for c in detected:
                if c["description"] not in existing_descs:
                    memo.setdefault("conflicts", []).append(c)
                    existing_descs.add(c["description"])
            current_open = [
                c for c in memo.get("conflicts", [])
                if c.get("resolution") == "blocked-pending-user"
            ]
    except (OSError, json.JSONDecodeError) as err:
        return _die("check-conflicts: {0}".format(err))
    json.dump(current_open, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


def cmd_record_conflict_resolution(args: argparse.Namespace) -> int:
    """Mark a conflict as resolved; optionally clear a loser dimension."""
    try:
        with _state_transaction(args.devforge_dir, "memo") as memo:
            conflicts = memo.get("conflicts", [])
            if args.index < 0 or args.index >= len(conflicts):
                return _die(
                    "record-conflict-resolution: index {0} out of range "
                    "(have {1})".format(args.index, len(conflicts)),
                    code=2,
                )
            conflicts[args.index]["resolution"] = args.resolution
            if args.rewrite_dimension:
                rec = memo["dimensions"].get(args.rewrite_dimension) or _empty_dimension()
                rec["value"] = None
                rec["state"] = RUBRIC_STATE_DEFAULT
                rec["turns"] = 0
                memo["dimensions"][args.rewrite_dimension] = rec
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-conflict-resolution: {0}".format(err))
    return 0


def cmd_symptom_coverage(args: argparse.Namespace) -> int:
    """Emit JSON coverage map + counts to stdout."""
    try:
        from ._state import _load_memo
        memo = _load_memo(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("symptom-coverage: {0}".format(err))
    state_map, clear, partial, missing = _compute_coverage(memo)
    out = {
        "per_dimension": state_map,
        "counts": {"Clear": clear, "Partial": partial, "Missing": missing},
        "mode": memo.get("mode"),
        "conflicts_open": sum(
            1 for c in memo.get("conflicts", [])
            if c.get("resolution") == "blocked-pending-user"
        ),
    }
    json.dump(out, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


def cmd_symptom_finalize(args: argparse.Namespace) -> int:
    """Validate memo is finalize-ready.

    Exit 0 when:
      - all 6 dimensions are Clear, AND
      - no conflicts with resolution == "blocked-pending-user".

    OR exit 0 with override_recorded=true persisted when:
      - --accept-gaps passed AND no blocked conflicts.

    Exit 2 otherwise. stderr enumerates each blocker.
    """
    try:
        with _state_transaction(args.devforge_dir, "memo") as memo:
            state_map, clear, partial, missing = _compute_coverage(memo)
            blocked = [
                c for c in memo.get("conflicts", [])
                if c.get("resolution") == "blocked-pending-user"
            ]
            violations = []  # type: List[str]
            if blocked:
                for c in blocked:
                    violations.append(
                        "blocked conflict ({0}): {1}".format(
                            "+".join(c.get("dimensions", [])),
                            c.get("description", ""),
                        )
                    )
            if (partial or missing) and not args.accept_gaps:
                for d, st in state_map.items():
                    if st != "Clear":
                        violations.append("{0}: {1}".format(d, st))

            if violations:
                for v in violations:
                    sys.stderr.write("symptom-finalize: {0}\n".format(v))
                return 2

            if (partial or missing) and args.accept_gaps:
                memo["override_recorded"] = True
    except (OSError, json.JSONDecodeError) as err:
        return _die("symptom-finalize: {0}".format(err))
    return 0
