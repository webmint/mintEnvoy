"""Phase 2 — decision-point cmd_* handlers + coverage helpers."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple

from ._schema import (
    DP_CATEGORY_ENUM,
    DP_DEFERRAL_KIND_ENUM,
    DP_TURN_CAP,
    DP_TURN_CAP_REASON,
    _DEFERRAL_KIND_TO_STATUS,
    _DP_CLEAR_STATUSES,
)
from ._state import _load_state, _state_transaction
from ._validators import _die, _validate_enum, _validate_scalar


def _next_dp_id(state: Dict[str, Any], category: str) -> str:
    prefix = "DP-{0}-".format(category)
    n = 1 + sum(
        1 for d in state["decision_points"]
        if d.get("dp_id", "").startswith(prefix)
    )
    return "{0}{1}".format(prefix, n)


def _find_dp(state: Dict[str, Any], dp_id: str) -> Optional[Dict[str, Any]]:
    for d in state["decision_points"]:
        if d.get("dp_id") == dp_id:
            return d
    return None


def cmd_record_decision_point(args: argparse.Namespace) -> int:
    """Record a new DecisionPoint. ≥2 valid_implementations required."""
    try:
        category = _validate_enum(
            args.category, "category", DP_CATEGORY_ENUM,
        )
    except ValueError as err:
        return _die(str(err), code=2)

    if args.no_dp_in_category:
        try:
            description = _validate_scalar(
                args.description, "description",
            )
        except ValueError as err:
            return _die(str(err), code=2)
        valid_implementations: List[str] = []
        status = "no_DP_in_category"
    else:
        try:
            description = _validate_scalar(
                args.description, "description",
            )
        except ValueError as err:
            return _die(str(err), code=2)
        try:
            parsed = json.loads(args.valid_implementations or "[]")
        except json.JSONDecodeError as err:
            return _die(
                "valid_implementations: not valid JSON ({0})".format(err),
                code=2,
            )
        if not isinstance(parsed, list) or not all(
            isinstance(v, str) for v in parsed
        ):
            return _die(
                "valid_implementations: must be a JSON array of strings",
                code=2,
            )
        valid_implementations = [v.strip() for v in parsed if v.strip()]
        if len(valid_implementations) < 2:
            return _die(
                "valid_implementations: ≥2 entries required (got {0})".format(
                    len(valid_implementations),
                ),
                code=2,
            )
        status = "pending"

    try:
        with _state_transaction(args.devforge_dir) as state:
            dp_id = _next_dp_id(state, category)
            state["decision_points"].append({
                "dp_id": dp_id,
                "category": category,
                "description": description,
                "valid_implementations": valid_implementations,
                "status": status,
                "user_answer": "",
                "default_applied": "",
                "deferral_reason": "",
                "turns": 0,
            })
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-decision-point: {0}".format(err))
    sys.stdout.write(dp_id + "\n")
    return 0


def cmd_set_dp_answer(args: argparse.Namespace) -> int:
    """Interactive path. Sets DP.status=answered + user_answer."""
    try:
        user_answer = _validate_scalar(args.user_answer, "user_answer")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            if state.get("mode") == "auto":
                return _die(
                    "set-dp-answer: mode=auto rejects user-answer setter "
                    "(use set-dp-default-applied)",
                    code=2,
                )
            dp = _find_dp(state, args.dp_id)
            if dp is None:
                return _die(
                    "set-dp-answer: dp_id {0!r} not found".format(args.dp_id),
                    code=2,
                )
            if dp.get("status") == "no_DP_in_category":
                return _die(
                    "set-dp-answer: {0} is no_DP_in_category (terminal)".format(
                        args.dp_id,
                    ),
                    code=2,
                )
            dp["status"] = "answered"
            dp["user_answer"] = user_answer
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-dp-answer: {0}".format(err))
    return 0


def cmd_set_dp_default_applied(args: argparse.Namespace) -> int:
    """Auto path. Sets DP.status=default_applied + default_applied."""
    try:
        default_applied = _validate_scalar(
            args.default_applied, "default_applied",
        )
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            if state.get("mode") == "interactive":
                return _die(
                    "set-dp-default-applied: mode=interactive rejects "
                    "default-applied setter (use set-dp-answer)",
                    code=2,
                )
            dp = _find_dp(state, args.dp_id)
            if dp is None:
                return _die(
                    "set-dp-default-applied: dp_id {0!r} not found".format(
                        args.dp_id,
                    ),
                    code=2,
                )
            if dp.get("status") == "no_DP_in_category":
                return _die(
                    "set-dp-default-applied: {0} is no_DP_in_category "
                    "(terminal)".format(args.dp_id),
                    code=2,
                )
            dp["status"] = "default_applied"
            dp["default_applied"] = default_applied
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-dp-default-applied: {0}".format(err))
    return 0


def cmd_set_dp_deferral(args: argparse.Namespace) -> int:
    """Defer a DP to OOS or open-question. Enforces per-DP turn cap."""
    try:
        kind = _validate_enum(
            args.deferral_kind, "deferral_kind", DP_DEFERRAL_KIND_ENUM,
        )
        reason = _validate_scalar(args.reason, "reason")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            dp = _find_dp(state, args.dp_id)
            if dp is None:
                return _die(
                    "set-dp-deferral: dp_id {0!r} not found".format(args.dp_id),
                    code=2,
                )
            if dp.get("status") == "no_DP_in_category":
                return _die(
                    "set-dp-deferral: {0} is no_DP_in_category "
                    "(terminal)".format(args.dp_id),
                    code=2,
                )
            if args.increment_turn:
                dp["turns"] = int(dp.get("turns", 0)) + 1
            if int(dp.get("turns", 0)) >= DP_TURN_CAP:
                dp["status"] = "deferred_open_question"
                dp["deferral_reason"] = DP_TURN_CAP_REASON
            else:
                dp["status"] = _DEFERRAL_KIND_TO_STATUS[kind]
                dp["deferral_reason"] = reason
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-dp-deferral: {0}".format(err))
    return 0


def _category_state(state: Dict[str, Any], category: str) -> str:
    """Compute per-category coverage state per plan §Phase 2 table."""
    in_cat = [
        d for d in state["decision_points"]
        if d.get("category") == category
    ]
    if not in_cat:
        return "Missing"
    if any(d.get("status") == "no_DP_in_category" for d in in_cat):
        return "NoDPInCategory"
    if any(d.get("status") in _DP_CLEAR_STATUSES for d in in_cat):
        return "Clear"
    if any(d.get("status") == "pending" for d in in_cat):
        return "Partial"
    return "Missing"


def cmd_dp_coverage(args: argparse.Namespace) -> int:
    """Emit per-DP {dp_id: status} JSON map (debug aid)."""
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("dp-coverage: {0}".format(err))
    out = {
        d.get("dp_id"): d.get("status")
        for d in state["decision_points"]
    }
    json.dump(out, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


def cmd_rubric_coverage(args: argparse.Namespace) -> int:
    """Emit per-category {category: state} JSON map. Deterministic order."""
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("rubric-coverage: {0}".format(err))
    out: Dict[str, str] = {}
    for cat in DP_CATEGORY_ENUM:
        out[cat] = _category_state(state, cat)
    json.dump(out, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


def cmd_verify_decision_coverage(args: argparse.Namespace) -> int:
    """Gate: every category state ∈ {Clear, NoDPInCategory}."""
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("verify-decision-coverage: {0}".format(err))
    failing: List[Tuple[str, str]] = []
    for cat in DP_CATEGORY_ENUM:
        st = _category_state(state, cat)
        if st not in ("Clear", "NoDPInCategory"):
            failing.append((cat, st))
    if failing:
        sys.stderr.write(
            "verify-decision-coverage: categories not covered:\n"
        )
        for cat, st in failing:
            sys.stderr.write("  - {0}: {1}\n".format(cat, st))
        return 2
    return 0


def cmd_rubric_finalize(args: argparse.Namespace) -> int:
    """Same gate as verify-decision-coverage."""
    return cmd_verify_decision_coverage(args)


def cmd_dp_finalize(args: argparse.Namespace) -> int:
    """Gate Phase 2 → Phase 3. Re-runs decision-coverage + stamps."""
    rc = cmd_verify_decision_coverage(args)
    if rc != 0:
        return rc
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["dp_finalized"] = True
    except (OSError, json.JSONDecodeError) as err:
        return _die("dp-finalize: {0}".format(err))
    return 0
