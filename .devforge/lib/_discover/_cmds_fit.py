"""Phase 1 fit-assessment handlers: prior-art + touchpoints + fit + overall + effort + rationale."""

from __future__ import annotations

import argparse
import json
from typing import List

from ._state import _state_transaction
from ._validators import _die, _validate_scalar


def cmd_record_prior_art(args: argparse.Namespace) -> int:
    """Append one prior-art entry to report.prior_art.

    --kind is validated by argparse choices before this handler runs.
    --reference and --relevance must be non-empty after strip.
    --source is optional; defaults to empty string.
    """
    try:
        reference = _validate_scalar(args.reference, "record-prior-art.reference")
        relevance = _validate_scalar(args.relevance, "record-prior-art.relevance")
    except ValueError as err:
        return _die(str(err), code=2)
    entry = {
        "reference": reference,
        "kind": args.kind,
        "relevance": relevance,
        "source": args.source,
    }
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["prior_art"].append(entry)
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-prior-art: {0}".format(err))
    return 0


def cmd_record_integration_touchpoint(args: argparse.Namespace) -> int:
    """Append one integration-touchpoint entry to report.integration_touchpoints.

    All three fields (--name, --module-path, --reason) are required and
    must be non-empty after strip.
    """
    try:
        name = _validate_scalar(args.name, "record-integration-touchpoint.name")
        module_path = _validate_scalar(args.module_path, "record-integration-touchpoint.module_path")
        reason = _validate_scalar(args.reason, "record-integration-touchpoint.reason")
    except ValueError as err:
        return _die(str(err), code=2)
    entry = {"name": name, "module_path": module_path, "reason": reason}
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["integration_touchpoints"].append(entry)
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-integration-touchpoint: {0}".format(err))
    return 0


def cmd_record_fit_assessment(args: argparse.Namespace) -> int:
    """Append one fit-assessment entry to report.fit_assessments.

    --touchpoint must match the name of an existing integration_touchpoints
    entry. --effort is validated by argparse choices. --blockers is a JSON
    array of strings (defaults to "[]").
    """
    # Decode and validate --blockers before entering the transaction.
    try:
        blockers_raw = json.loads(args.blockers)
    except ValueError as err:
        return _die(
            "record-fit-assessment: --blockers is not valid JSON: {0}".format(err),
            code=2,
        )
    if not isinstance(blockers_raw, list):
        return _die(
            "record-fit-assessment: --blockers must be a JSON array, got {0}".format(
                type(blockers_raw).__name__
            ),
            code=2,
        )
    for item in blockers_raw:
        if not isinstance(item, str):
            return _die(
                "record-fit-assessment: every blocker must be a string, got {0}".format(
                    type(item).__name__
                ),
                code=2,
            )
    try:
        user_expected = _validate_scalar(args.user_expected, "record-fit-assessment.user_expected")
        reality = _validate_scalar(args.reality, "record-fit-assessment.reality")
    except ValueError as err:
        return _die(str(err), code=2)

    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            # Cross-check: touchpoint name must exist in integration_touchpoints.
            existing_names = [
                tp["name"]
                for tp in report.get("integration_touchpoints", [])
                if isinstance(tp, dict) and "name" in tp
            ]
            if args.touchpoint not in existing_names:
                return _die(
                    "fit-assessment touchpoint '{0}' does not match any "
                    "integration_touchpoint name; record-integration-touchpoint first".format(
                        args.touchpoint
                    ),
                    code=2,
                )
            entry = {
                "touchpoint": args.touchpoint,
                "user_expected": user_expected,
                "reality": reality,
                "effort": args.effort,
                "blockers": list(blockers_raw),
            }
            report["fit_assessments"].append(entry)
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-fit-assessment: {0}".format(err))
    return 0


def cmd_set_overall_fit(args: argparse.Namespace) -> int:
    """Set report.overall_fit to an OVERALL_FIT_ENUM value.

    --value is validated by argparse choices before this handler runs.
    """
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["overall_fit"] = args.value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-overall-fit: {0}".format(err))
    return 0


def cmd_set_effort_estimate(args: argparse.Namespace) -> int:
    """Set report.effort_estimate to an EFFORT_ENUM value.

    --value is validated by argparse choices before this handler runs.
    """
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["effort_estimate"] = args.value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-effort-estimate: {0}".format(err))
    return 0


def cmd_set_fit_rationale(args: argparse.Namespace) -> int:
    """Set report.fit_rationale to a non-empty string."""
    try:
        value = _validate_scalar(args.value, "set-fit-rationale")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["fit_rationale"] = value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-fit-rationale: {0}".format(err))
    return 0
