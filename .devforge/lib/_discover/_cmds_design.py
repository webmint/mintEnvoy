"""Phase 2 design-drafting handlers: design-options + recommended + build-vs-buy + derisk + constitution + verdict + recommendation + next-step."""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import List, Optional, Tuple

from ._state import _load_memo, _load_report, _state_transaction
from ._validators import _die, _validate_scalar


def _decode_string_array(raw: str, flag_name: str) -> Tuple[Optional[List[str]], int]:
    """Decode a JSON array of non-empty strings.

    Returns (list, 0) on success or (None, exit_code) on error.
    Caller must call _die separately — this only returns the code.
    """
    try:
        decoded = json.loads(raw)
    except ValueError as err:
        sys.stderr.write(
            "discover_helper: {0}: not valid JSON: {1}\n".format(flag_name, err)
        )
        return None, 2
    if not isinstance(decoded, list):
        sys.stderr.write(
            "discover_helper: {0}: must be a JSON array, got {1}\n".format(
                flag_name, type(decoded).__name__
            )
        )
        return None, 2
    cleaned = []  # type: List[str]
    for item in decoded:
        if not isinstance(item, str):
            sys.stderr.write(
                "discover_helper: {0}: every item must be a string, got {1}\n".format(
                    flag_name, type(item).__name__
                )
            )
            return None, 2
        if not item.strip():
            sys.stderr.write(
                "discover_helper: {0}: items must be non-empty strings\n".format(flag_name)
            )
            return None, 2
        cleaned.append(item)
    return cleaned, 0


_OPTION_LETTER_PREFIX_RE = re.compile(r"^(option\s+)?[a-z]\s*:\s*", re.IGNORECASE)

_INLINE_ESCAPE_RE = re.compile(r"(?:\\r\\n|\\n|\\r|\\t)+")


def _clean_inline_escapes(value: str) -> str:
    """Collapse literal `\\n` / `\\r` / `\\t` escape sequences to single space.

    Fix F2 — orchestrator-passed setter values sometimes carry literal
    backslash-n substrings from shell-escape leakage; these render as ugly
    literal escapes inside markdown and break shell-quoting on copy-paste of
    `/specify "..."`. Collapse contiguous runs to a single space, then trim
    repeated whitespace.
    """
    if not isinstance(value, str):
        return value
    cleaned = _INLINE_ESCAPE_RE.sub(" ", value)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip()


def cmd_set_design_option(args: argparse.Namespace) -> int:
    """Append one design-option entry to report.design_options.

    --name must be unique among existing entries. --pros and --cons are JSON
    arrays of non-empty strings (at least 1 entry each). --complexity is
    validated by argparse choices. --name must NOT carry a letter prefix
    (`A:`, `Option B:`, `c -`, etc.) — the helper auto-assigns the letter
    based on insertion order during render. A baked-in prefix produces
    `### Option A: A: ...` double-prefix render artifacts.
    """
    try:
        name = _validate_scalar(args.name, "set-design-option.name")
        shape = _validate_scalar(args.shape, "set-design-option.shape")
    except ValueError as err:
        return _die(str(err), code=2)
    if _OPTION_LETTER_PREFIX_RE.match(name):
        return _die(
            "set-design-option: --name {0!r} starts with a letter prefix "
            "(e.g. 'A:', 'Option B:'); helper auto-assigns the letter during "
            "render. Strip the prefix and retry.".format(name),
            code=2,
        )
    pros, code = _decode_string_array(args.pros, "--pros")
    if pros is None:
        return code
    if not pros:
        return _die("set-design-option: --pros must have at least 1 entry", code=2)
    cons, code = _decode_string_array(args.cons, "--cons")
    if cons is None:
        return code
    if not cons:
        return _die("set-design-option: --cons must have at least 1 entry", code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            existing_names = [
                opt["name"]
                for opt in report.get("design_options", [])
                if isinstance(opt, dict) and "name" in opt
            ]
            if name in existing_names:
                return _die(
                    "set-design-option: name {0!r} already exists in design_options; "
                    "use a unique name".format(name),
                    code=2,
                )
            report["design_options"].append({
                "name": name,
                "shape": shape,
                "pros": pros,
                "cons": cons,
                "complexity": args.complexity,
            })
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-design-option: {0}".format(err))
    return 0


def cmd_set_recommended_option(args: argparse.Namespace) -> int:
    """Set report.recommended_option; --name must match an existing design_option name."""
    try:
        name = _validate_scalar(args.name, "set-recommended-option.name")
        rationale = _validate_scalar(args.rationale, "set-recommended-option.rationale")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            existing_names = [
                opt["name"]
                for opt in report.get("design_options", [])
                if isinstance(opt, dict) and "name" in opt
            ]
            if name not in existing_names:
                return _die(
                    "recommended-option name {0!r} does not match any design_option.name; "
                    "record design_options first".format(name),
                    code=2,
                )
            report["recommended_option"] = {"name": name, "rationale": rationale}
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-recommended-option: {0}".format(err))
    return 0


def cmd_set_build_vs_buy(args: argparse.Namespace) -> int:
    """Set report.build_vs_buy.

    All four fields required. --recommendation validated by argparse choices.
    """
    try:
        build = _validate_scalar(args.build, "set-build-vs-buy.build")
        buy = _validate_scalar(args.buy, "set-build-vs-buy.buy")
        reasoning = _validate_scalar(args.reasoning, "set-build-vs-buy.reasoning")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["build_vs_buy"] = {
                "build": build,
                "buy": buy,
                "recommendation": args.recommendation,
                "reasoning": reasoning,
            }
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-build-vs-buy: {0}".format(err))
    return 0


def cmd_set_derisk_plan(args: argparse.Namespace) -> int:
    """Set report.derisk_plan to a JSON array of non-empty strings."""
    items, code = _decode_string_array(args.items, "--items")
    if items is None:
        return code
    if not items:
        return _die("set-derisk-plan: --items must have at least 1 entry", code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["derisk_plan"] = items
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-derisk-plan: {0}".format(err))
    return 0


def cmd_set_constitution_constraints(args: argparse.Namespace) -> int:
    """Append one entry to report.constitution_constraints. Append-only (not replace)."""
    try:
        rule = _validate_scalar(args.rule, "set-constitution-constraints.rule")
        impact = _validate_scalar(args.impact, "set-constitution-constraints.impact")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["constitution_constraints"].append({"rule": rule, "impact": impact})
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-constitution-constraints: {0}".format(err))
    return 0


def cmd_set_verdict(args: argparse.Namespace) -> int:
    """Set report.verdict. --value validated by argparse choices."""
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["verdict"] = args.value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-verdict: {0}".format(err))
    return 0


def cmd_set_recommendation(args: argparse.Namespace) -> int:
    """Set report.recommendation = {action, next}. Both non-empty."""
    try:
        action = _validate_scalar(args.action, "set-recommendation.action")
        next_text = _validate_scalar(args.next_text, "set-recommendation.next")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["recommendation"] = {"action": action, "next": next_text}
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-recommendation: {0}".format(err))
    return 0


def cmd_set_next_step_text(args: argparse.Namespace) -> int:
    """Compose and set report.next_step_text from memo + report state.

    Composed (no --value). Reads memo.functional_scope, memo.users,
    memo.success_criteria, report.verdict, report.recommended_option,
    memo.topic_slug, report.date, report.gaps. Composes a copy-pasteable
    /specify block and sets report.next_step_text.

    If verdict == 'Reconsider': sets next_step_text = None. Exit 0.
    If any required input is missing: exit 2.
    """
    try:
        memo = _load_memo(args.devforge_dir)
        report = _load_report(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-next-step-text: {0}".format(err))

    verdict = report.get("verdict")

    if verdict == "Reconsider":
        try:
            with _state_transaction(args.devforge_dir, "report") as rep:
                rep["next_step_text"] = None
        except (OSError, json.JSONDecodeError) as err:
            return _die("set-next-step-text: {0}".format(err))
        return 0

    # Collect required inputs; report all missing at once.
    dims = memo.get("dimensions", {})
    functional_scope_val = (dims.get("functional_scope") or {}).get("value")
    users_val = (dims.get("users") or {}).get("value")
    success_criteria_val = (dims.get("success_criteria") or {}).get("value")
    recommended_option = report.get("recommended_option")
    recommended_name = (recommended_option or {}).get("name") if isinstance(recommended_option, dict) else None

    missing = []  # type: List[str]
    if not functional_scope_val:
        missing.append("memo.functional_scope.value")
    if not users_val:
        missing.append("memo.users.value")
    if not success_criteria_val:
        missing.append("memo.success_criteria.value")
    if not recommended_option:
        missing.append("report.recommended_option")
    elif not recommended_name:
        missing.append("report.recommended_option.name")

    if missing:
        sys.stderr.write(
            "discover_helper: set-next-step-text: missing required input(s): {0}\n".format(
                ", ".join(missing)
            )
        )
        return 2

    # F1: prefer caller-supplied --topic (LLM-distilled 1-2 sentence form);
    # else fall back to first sentence of functional_scope.value split on ". ".
    topic_arg = getattr(args, "topic", None)
    if topic_arg and topic_arg.strip():
        distilled = _clean_inline_escapes(topic_arg.strip())
    else:
        parts = functional_scope_val.split(". ", 1)
        distilled = _clean_inline_escapes(parts[0])

    # F2: strip literal `\n` / `\n\n` escape sequences from setter values before
    # embedding in the next-step block. They render as ugly literal escapes
    # inside markdown and break shell-quoting on copy-paste of /specify "...".
    functional_scope_clean = _clean_inline_escapes(functional_scope_val)
    users_clean = _clean_inline_escapes(users_val)
    success_criteria_clean = _clean_inline_escapes(success_criteria_val)
    recommended_name_clean = _clean_inline_escapes(recommended_name or "")

    date = report.get("date") or memo.get("date") or "unknown-date"
    topic_slug = report.get("topic_slug") or memo.get("topic_slug") or "topic"
    gaps = memo.get("gaps") or []
    gaps_count = len(gaps)

    lines = [
        '/specify "{0}"'.format(distilled),
        "",
        "Discovery reference: discover/{0}-{1}.md".format(date, topic_slug),
        "Key facts:",
        "- Functional scope: {0}".format(functional_scope_clean),
        "- Users: {0}".format(users_clean),
        "- Success criteria: {0}".format(success_criteria_clean),
        "- Recommended option: {0}".format(recommended_name_clean),
        "- Open uncertainties: {0} (see discovery doc §Open uncertainties)".format(gaps_count),
    ]
    composed = "\n".join(lines)

    try:
        with _state_transaction(args.devforge_dir, "report") as rep:
            rep["next_step_text"] = composed
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-next-step-text: {0}".format(err))
    return 0
