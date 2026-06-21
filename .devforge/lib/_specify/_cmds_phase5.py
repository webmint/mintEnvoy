"""Phase 5 + downstream cmd_*: render-summary / set-status / render-plan-handoff / resolve-open-question."""

from __future__ import annotations

import argparse
import json
import sys

from ._render import _approval_summary, _plan_handoff_block
from ._schema import RESOLUTION_PHASE_ENUM, SPEC_STATUS_ENUM
from ._state import _load_state, _state_transaction
from ._validators import _die, _utc_timestamp, _validate_enum, _validate_scalar


def cmd_render_summary(args: argparse.Namespace) -> int:
    """Emit 4-bullet approval summary; persist to state.approval_summary."""
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("render-summary: {0}".format(err))
    summary = _approval_summary(state)
    try:
        with _state_transaction(args.devforge_dir) as state2:
            state2["approval_summary"] = summary
    except (OSError, json.JSONDecodeError) as err:
        return _die("render-summary: {0}".format(err))
    sys.stdout.write(summary + "\n")
    return 0


def cmd_set_status(args: argparse.Namespace) -> int:
    """Set spec status; closed enum SPEC_STATUS_ENUM."""
    try:
        status = _validate_enum(args.status, "status", SPEC_STATUS_ENUM)
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["status"] = status
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-status: {0}".format(err))
    return 0


def cmd_render_plan_handoff(args: argparse.Namespace) -> int:
    """Emit deterministic /plan handoff block; persist to state."""
    try:
        state = _load_state(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("render-plan-handoff: {0}".format(err))
    block = _plan_handoff_block(state)
    try:
        with _state_transaction(args.devforge_dir) as state2:
            state2["plan_handoff_block"] = block
    except (OSError, json.JSONDecodeError) as err:
        return _die("render-plan-handoff: {0}".format(err))
    sys.stdout.write(block + "\n")
    return 0


def cmd_resolve_open_question(args: argparse.Namespace) -> int:
    """Record a resolution for an §8 Open Question. Append-only audit log."""
    try:
        qid = _validate_scalar(args.question_id, "question_id")
        text = _validate_scalar(args.resolution_text, "resolution_text")
        phase = _validate_enum(
            args.resolution_phase, "resolution_phase",
            RESOLUTION_PHASE_ENUM,
        )
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["open_question_resolutions"].append({
                "question_id": qid,
                "resolution_text": text,
                "resolution_phase": phase,
                "resolution_timestamp": _utc_timestamp(),
            })
    except (OSError, json.JSONDecodeError) as err:
        return _die("resolve-open-question: {0}".format(err))
    return 0
