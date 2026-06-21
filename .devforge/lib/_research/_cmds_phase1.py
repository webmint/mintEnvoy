"""Phase 1 (investigation) command handlers.

Findings + runner-up framing + hypotheses + structured root cause +
confidence + verify-step setters.
"""

from __future__ import annotations

import argparse
import json

from ._constants import (
    CONFIDENCE_ENUM,
    CONFIDENCE_VS_PRIMARY_ENUM,
    FRAMING_ENUM,
)
from ._state import _state_transaction
from ._validators import (
    _die,
    _validate_enum,
    _validate_file_line,
    _validate_scalar,
    _validate_verbatim,
)


def cmd_record_finding(args: argparse.Namespace) -> int:
    """Append a {surface, file_line, relevance, framing} Finding."""
    try:
        surface = _validate_scalar(args.surface, "finding.surface")
        file_line = _validate_file_line(args.file_line, "finding.file_line")
        relevance = _validate_scalar(args.relevance, "finding.relevance")
        framing = _validate_enum(
            getattr(args, "framing", "primary") or "primary",
            "finding.framing",
            FRAMING_ENUM,
        )
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report.setdefault("findings", []).append(
                {
                    "surface": surface,
                    "file_line": file_line,
                    "relevance": relevance,
                    "framing": framing,
                }
            )
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-finding: {0}".format(err))
    return 0


def cmd_record_runner_up_framing(args: argparse.Namespace) -> int:
    """Set report.runner_up_framing. Overwrites any prior value (last call wins)."""
    try:
        frame = _validate_scalar(args.frame, "runner_up_framing.frame")
        falsifier = _validate_scalar(args.falsifier, "runner_up_framing.falsifier")
        confidence = _validate_enum(
            args.confidence_vs_primary,
            "runner_up_framing.confidence_vs_primary",
            CONFIDENCE_VS_PRIMARY_ENUM,
        )
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["runner_up_framing"] = {
                "frame": frame,
                "falsifier": falsifier,
                "confidence_vs_primary": confidence,
            }
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-runner-up-framing: {0}".format(err))
    return 0


def _hypothesis_label(index):
    # type: (int) -> str
    """Convert a zero-based hypothesis index to an uppercase letter label.

    Index 0 → "A", 1 → "B", ..., 25 → "Z", 26 → "AA", 27 → "AB", etc.
    Follows spreadsheet-column naming for indices beyond 25 (unlikely in
    practice but avoids a silent failure on long hypothesis lists).
    """
    label = ""
    n = index
    while True:
        label = chr(ord("A") + (n % 26)) + label
        n = n // 26 - 1
        if n < 0:
            break
    return label


def cmd_record_hypothesis(args: argparse.Namespace) -> int:
    """Append a {label, cause, falsifier, runtime_probe_needed} Hypothesis.

    label is auto-assigned in record order: first hypothesis → "A",
    second → "B", etc. The label is what recommended_approach.hypotheses_addressed
    references so the verify-hypothesis-suppression exemption can match by
    label rather than by cause text (which would couple the setter and the
    verify check to a fragile string-equality comparison).
    """
    try:
        cause = _validate_scalar(args.cause, "hypothesis.cause")
        falsifier = _validate_scalar(args.falsifier, "hypothesis.falsifier")
    except ValueError as err:
        return _die(str(err), code=2)
    runtime = args.runtime_probe_needed == "yes"
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            existing = report.setdefault("hypotheses", [])
            label = _hypothesis_label(len(existing))
            existing.append(
                {
                    "label": label,
                    "cause": cause,
                    "falsifier": falsifier,
                    "runtime_probe_needed": runtime,
                }
            )
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-hypothesis: {0}".format(err))
    return 0


def cmd_set_root_cause_hypothesis(args: argparse.Namespace) -> int:
    """Set root_cause_hypothesis free text."""
    try:
        value = _validate_verbatim(args.value, "root_cause_hypothesis")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["root_cause_hypothesis"] = value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-root-cause-hypothesis: {0}".format(err))
    return 0


def cmd_set_confidence(args: argparse.Namespace) -> int:
    """Set confidence enum."""
    try:
        value = _validate_enum(args.value, "confidence", CONFIDENCE_ENUM)
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["confidence"] = value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-confidence: {0}".format(err))
    return 0


def _ensure_structured_root_cause(report: dict) -> dict:
    """Lazily create the structured_root_cause record on the report."""
    rec = report.get("structured_root_cause")
    if rec is None:
        rec = {"trigger": None, "root_cause_systemic": None, "contributing_factors": []}
        report["structured_root_cause"] = rec
    return rec


def cmd_set_trigger(args: argparse.Namespace) -> int:
    """Set structured_root_cause.trigger (caller is responsible for mode gate)."""
    try:
        value = _validate_verbatim(args.value, "trigger")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            rec = _ensure_structured_root_cause(report)
            rec["trigger"] = value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-trigger: {0}".format(err))
    return 0


def cmd_set_root_cause_systemic(args: argparse.Namespace) -> int:
    """Set structured_root_cause.root_cause_systemic."""
    try:
        value = _validate_verbatim(args.value, "root_cause_systemic")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            rec = _ensure_structured_root_cause(report)
            rec["root_cause_systemic"] = value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-root-cause-systemic: {0}".format(err))
    return 0


def cmd_record_contributing_factor(args: argparse.Namespace) -> int:
    """Append a contributing factor (max 3)."""
    try:
        value = _validate_scalar(args.value, "contributing_factor")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            rec = _ensure_structured_root_cause(report)
            factors = rec.setdefault("contributing_factors", [])
            if len(factors) >= 3:
                return _die(
                    "record-contributing-factor: max 3 entries; already have {0}".format(
                        len(factors)
                    ),
                    code=2,
                )
            factors.append(value)
    except (OSError, json.JSONDecodeError) as err:
        return _die("record-contributing-factor: {0}".format(err))
    return 0


def cmd_set_verify_step(args: argparse.Namespace) -> int:
    """Set verify_step record. 3 sub-fields all required."""
    try:
        probe = _validate_verbatim(args.probe, "verify_step.probe")
        reproduction = _validate_verbatim(args.reproduction, "verify_step.reproduction")
        discriminator = _validate_verbatim(args.discriminator, "verify_step.discriminator")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["verify_step"] = {
                "probe": probe,
                "reproduction": reproduction,
                "discriminator": discriminator,
            }
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-verify-step: {0}".format(err))
    return 0
