"""Core cmd_* handlers: plumbing + date/topic/summary + render + verify."""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from ._cli import PREFLIGHT_PREREQS
from ._state import (
    _atomic_write_json,
    _load_memo,
    _load_report,
    _memo_path,
    _report_path,
    _state_transaction,
    default_memo_state,
    default_report_state,
)
from ._topic import derive_topic_slug
from ._validators import _die, _validate_scalar


def cmd_reset_memo(args: argparse.Namespace) -> int:
    """Write fresh defaults memo state. Idempotent."""
    try:
        _atomic_write_json(default_memo_state(), _memo_path(args.devforge_dir))
    except OSError as err:
        return _die("reset-memo: {0}".format(err))
    return 0


def cmd_reset_report(args: argparse.Namespace) -> int:
    """Write fresh defaults report state. Idempotent."""
    try:
        _atomic_write_json(default_report_state(), _report_path(args.devforge_dir))
    except OSError as err:
        return _die("reset-report: {0}".format(err))
    return 0


def cmd_read_memo(args: argparse.Namespace) -> int:
    """Print discover-scope.json as JSON to stdout (defaults if missing)."""
    try:
        state = _load_memo(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("read-memo: {0}".format(err))
    json.dump(state, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


def cmd_read_report(args: argparse.Namespace) -> int:
    """Print discover-report.json as JSON to stdout (defaults if missing)."""
    try:
        state = _load_report(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("read-report: {0}".format(err))
    json.dump(state, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


def cmd_preflight(args: argparse.Namespace) -> int:
    """4-artefact hard gate. Exit 2 + BLOCKED message on any missing.

    Checks each PREFLIGHT_PREREQS path relative to --install-root for
    existence + non-empty (size > 0). On any failure, emits a single
    BLOCKED: header followed by one Missing: line per absent artefact and
    exits 2. All missing artefacts are listed — not just the first.
    """
    install_root = Path(args.install_root)
    missing = []  # type: List[Tuple[str, str]]
    for rel_path, producer in PREFLIGHT_PREREQS:
        p = install_root / rel_path
        try:
            if not p.exists():
                missing.append((rel_path, producer))
                continue
            if p.stat().st_size == 0:
                missing.append((rel_path, producer))
        except OSError as err:
            return _die("preflight: stat failed on {0}: {1}".format(p, err))

    if missing:
        sys.stderr.write(
            "BLOCKED: /discover requires the full 4-command setup chain.\n"
        )
        for rel, producer in missing:
            sys.stderr.write("Missing: {0} (produced by {1})\n".format(rel, producer))
        sys.stderr.write(
            "Run: /init-forge → /generate-docs → /configure → /constitute, "
            "then retry /discover.\n"
        )
        return 2
    return 0


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def cmd_set_topic(args: argparse.Namespace) -> int:
    """Set memo.topic + report.topic and auto-derive topic_slug in both.

    Topic comes from the user's original /discover argument. Auto-deriving
    slug here means the orchestrator owns one input string; helper renders
    both topic text and filename slug.
    """
    try:
        value = _validate_scalar(args.value, "topic")
    except ValueError as err:
        return _die(str(err), code=2)
    slug = derive_topic_slug(value)
    try:
        with _state_transaction(args.devforge_dir, "memo") as memo:
            memo["topic"] = value
            memo["topic_slug"] = slug
        with _state_transaction(args.devforge_dir, "report") as report:
            report["topic"] = value
            report["topic_slug"] = slug
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-topic: {0}".format(err))
    return 0


def cmd_set_verbatim_prompt(args: argparse.Namespace) -> int:
    """Persist the full raw prompt text to memo.verbatim_prompt.

    Called at Phase 0.3 immediately after set-topic, before scoping runs.
    The prompt text is stored verbatim (internal whitespace preserved, leading/
    trailing whitespace stripped). This is a DISTINCT field from the one-sentence
    topic set by set-topic: the full prompt may carry 'we should also ...'
    scope-expanders or hypothesis guesses that the paraphrased topic loses.
    """
    try:
        value = _validate_scalar(args.value, "verbatim_prompt")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "memo") as memo:
            memo["verbatim_prompt"] = value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-verbatim-prompt: {0}".format(err))
    return 0


def cmd_set_date(args: argparse.Namespace) -> int:
    """Set memo.date + report.date. Format YYYY-MM-DD enforced.

    Validates format with regex then verifies it is a real calendar date
    via datetime.date.fromisoformat to reject impossible dates like
    2026-13-01 or 2026-02-30.
    """
    if not _DATE_RE.match(args.value):
        return _die(
            "set-date: invalid date {0!r}; expected YYYY-MM-DD".format(args.value),
            code=2,
        )
    try:
        datetime.date.fromisoformat(args.value)
    except ValueError:
        return _die(
            "set-date: {0!r} is not a real calendar date".format(args.value),
            code=2,
        )
    try:
        with _state_transaction(args.devforge_dir, "memo") as memo:
            memo["date"] = args.value
        with _state_transaction(args.devforge_dir, "report") as report:
            report["date"] = args.value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-date: {0}".format(err))
    return 0


def cmd_set_summary(args: argparse.Namespace) -> int:
    """Set report.summary to a non-empty string."""
    try:
        value = _validate_scalar(args.value, "set-summary")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["summary"] = value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-summary: {0}".format(err))
    return 0


# ---------------------------------------------------------------------------
# Render helper — table builder.
# ---------------------------------------------------------------------------


def _md_table(headers: List[str], rows: List[List[str]]) -> str:
    """Build a Markdown table string (no trailing newline).

    Pipes inside cell values are escaped to \\| to keep table structure valid.
    """
    def _esc(s: str) -> str:
        return str(s).replace("|", "\\|")

    header_row = "| " + " | ".join(_esc(h) for h in headers) + " |"
    sep_row = "|" + "|".join("---" for _ in headers) + "|"
    data_rows = [
        "| " + " | ".join(_esc(cell) for cell in row) + " |"
        for row in rows
    ]
    return "\n".join([header_row, sep_row] + data_rows)


_OPTION_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def cmd_render(args: argparse.Namespace) -> int:
    """Render the full discovery report Markdown to stdout. Read-only.

    Walks the locked schema. Sections are emitted in fixed order regardless
    of field population; sparse sections show placeholder text per spec.
    constitution_constraints section is omitted entirely when empty.
    Open uncertainties section is rendered only when memo.gaps is non-empty.
    """
    try:
        report = _load_report(args.devforge_dir)
        memo = _load_memo(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("render: {0}".format(err))

    topic = report.get("topic") or "(topic not set)"
    date = report.get("date") or "(date not set)"
    verdict = report.get("verdict") or "(verdict not set)"

    lines = []  # type: List[str]

    # Header block.
    lines.append("# Discovery: {0}".format(topic))
    lines.append("")
    lines.append("**Date**: {0}".format(date))
    lines.append("**Topic**: {0}".format(topic))
    lines.append("**Verdict**: {0}".format(verdict))
    lines.append("")

    # Summary.
    lines.append("## Summary")
    lines.append("")
    summary = report.get("summary")
    lines.append(summary if summary else "*(summary not set)*")
    lines.append("")

    # Prior Art.
    lines.append("## Prior Art")
    lines.append("")
    prior_art = report.get("prior_art") or []
    if prior_art:
        rows = [
            [
                pa.get("reference", ""),
                pa.get("kind", ""),
                pa.get("relevance", ""),
                pa.get("source", ""),
            ]
            for pa in prior_art
        ]
        lines.append(_md_table(
            ["Reference", "Kind", "Relevance", "Source"],
            rows,
        ))
    else:
        lines.append("*No prior-art references recorded.*")
    lines.append("")

    # Integration Surface.
    lines.append("## Integration Surface")
    lines.append("")
    touchpoints = report.get("integration_touchpoints") or []
    if touchpoints:
        rows = [
            [tp.get("name", ""), tp.get("module_path", ""), tp.get("reason", "")]
            for tp in touchpoints
        ]
        lines.append(_md_table(["Touchpoint", "Module/file", "Why touched"], rows))
    else:
        lines.append("*No integration touchpoints recorded.*")
    lines.append("")

    # Fit Assessment.
    lines.append("## Fit Assessment")
    lines.append("")
    fit_assessments = report.get("fit_assessments") or []
    if fit_assessments:
        rows = [
            [
                fa.get("touchpoint", ""),
                fa.get("user_expected", ""),
                fa.get("reality", ""),
                fa.get("effort", ""),
                "; ".join(fa.get("blockers") or []) or "none",
            ]
            for fa in fit_assessments
        ]
        lines.append(_md_table(
            ["Touchpoint", "User expected", "Reality (scan)", "Effort", "Blockers"],
            rows,
        ))
    else:
        lines.append("*No fit assessments recorded.*")
    lines.append("")
    lines.append("**Overall fit**: {0}".format(report.get("overall_fit") or "(not set)"))
    lines.append("**Effort estimate**: {0}".format(report.get("effort_estimate") or "(not set)"))
    lines.append("**Rationale**: {0}".format(report.get("fit_rationale") or "(not set)"))
    lines.append("")

    # Design Options.
    lines.append("## Design Options")
    lines.append("")
    design_options = report.get("design_options") or []
    for i, opt in enumerate(design_options):
        letter = _OPTION_LETTERS[i] if i < len(_OPTION_LETTERS) else str(i + 1)
        lines.append("### Option {0}: {1}".format(letter, opt.get("name", "")))
        lines.append("- **Shape**:")
        lines.append("```")
        lines.append(opt.get("shape", ""))
        lines.append("```")
        pros = opt.get("pros") or []
        lines.append("- **Pros**:")
        for p in pros:
            lines.append("  - {0}".format(p))
        cons = opt.get("cons") or []
        lines.append("- **Cons**:")
        for c in cons:
            lines.append("  - {0}".format(c))
        lines.append("- **Complexity**: {0}".format(opt.get("complexity", "")))
        lines.append("")
    rec_opt = report.get("recommended_option")
    if isinstance(rec_opt, dict) and rec_opt.get("name"):
        lines.append(
            "**Recommended option**: {0} — {1}".format(
                rec_opt["name"], rec_opt.get("rationale", "")
            )
        )
    else:
        lines.append("**Recommended option**: *(not set)*")
    lines.append("")

    # Build vs Buy.
    lines.append("## Build vs Buy")
    lines.append("")
    bvb = report.get("build_vs_buy")
    if isinstance(bvb, dict):
        lines.append(_md_table(
            ["Build", "Buy/Adopt"],
            [[bvb.get("build", ""), bvb.get("buy", "")]],
        ))
        lines.append("")
        lines.append(
            "**Recommendation**: {0} — {1}".format(
                bvb.get("recommendation", ""),
                bvb.get("reasoning", ""),
            )
        )
    else:
        lines.append("*(build vs buy not set)*")
    lines.append("")

    # Derisk Plan.
    lines.append("## Derisk Plan")
    lines.append("")
    derisk = report.get("derisk_plan") or []
    for idx, item in enumerate(derisk, start=1):
        lines.append("{0}. {1}".format(idx, item))
    if not derisk:
        lines.append("*(no derisk plan recorded)*")
    lines.append("")

    # Constitution Constraints — only rendered when non-empty.
    constraints = report.get("constitution_constraints") or []
    if constraints:
        lines.append("## Constitution Constraints")
        lines.append("")
        rows = [
            [c.get("rule", ""), c.get("impact", "")]
            for c in constraints
        ]
        lines.append(_md_table(["Rule", "Impact"], rows))
        lines.append("")

    # Open Uncertainties — only when memo.gaps is non-empty.
    gaps = memo.get("gaps") or []
    if gaps:
        lines.append("## Open uncertainties")
        lines.append("")
        for gap in gaps:
            dimension = gap.get("dimension", "")
            description = gap.get("description", "")
            lines.append(
                "[NEEDS CLARIFICATION: {0} — {1}]".format(dimension, description)
            )
        lines.append("")

    # Recommendation.
    lines.append("## Recommendation")
    lines.append("")
    rec = report.get("recommendation")
    if isinstance(rec, dict):
        lines.append("**Action**: {0}".format(rec.get("action", "")))
        lines.append("**Next**: {0}".format(rec.get("next", "")))
    else:
        lines.append("*(recommendation not set)*")
    lines.append("")

    # Next step — only when next_step_text is not None.
    next_text = report.get("next_step_text")
    if next_text is not None:
        lines.append("## Next step")
        lines.append("")
        lines.append(
            "Copy the block below into a new /specify session manually. "
            "No automated handoff — user controls when /specify runs."
        )
        lines.append("")
        lines.append("~~~")
        lines.append(next_text)
        lines.append("~~~")
        lines.append("")

    output = "\n".join(lines) + "\n"
    sys.stdout.write(output)
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Cross-field invariant check.

    Rules:
      A. Required-field population under Worth pursuing / Promising with caveats.
      B. Design-options minimum (>=1) under Worth pursuing / Promising with caveats.
      C. Recommended-option name must match a design_option name.
      D. Verdict flip rule: Strained/Misfit overall_fit or Major refactor effort
         requires Reconsider verdict OR memo.override_recorded == True.
         memo.override_recorded is set by scope-finalize --accept-gaps and serves
         dual purpose: (1) user accepted Phase 0 coverage gaps, (2) user accepts
         an unfavorable fit verdict. Document this dual purpose here.
      E. Next-step text: Worth pursuing / Promising with caveats requires non-empty
         next_step_text; Reconsider requires None.
      F. Derisk plan: >=1 entry under Worth pursuing / Promising with caveats.
      G. Internal canonical-pattern cite rule: when any prior_art entry has
         source.startswith("internal:"), the recommended_option.rationale MUST
         contain at least one of those `internal:` file/dir paths as a substring.
         Forces the orchestrator to frame the recommended option as "extend
         existing <path>" rather than "build new <X>" when project-internal
         implementations of the capability already exist.

    Exit 0 only when all rules pass. Exit 2 on any violation.
    """
    try:
        report = _load_report(args.devforge_dir)
        memo = _load_memo(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("verify: {0}".format(err))

    violations = []  # type: List[str]

    verdict = report.get("verdict")
    overall_fit = report.get("overall_fit")
    effort_estimate = report.get("effort_estimate")
    recommended_option = report.get("recommended_option")
    design_options = report.get("design_options") or []
    override_recorded = memo.get("override_recorded", False)
    next_step_text = report.get("next_step_text")

    is_pursue = verdict in ("Worth pursuing", "Promising with caveats")
    is_reconsider = verdict == "Reconsider"

    # Rule A — required-field population.
    if is_pursue:
        required_fields = {
            "summary": report.get("summary"),
            "verdict": verdict,
            "overall_fit": overall_fit,
            "effort_estimate": effort_estimate,
            "fit_rationale": report.get("fit_rationale"),
            "recommended_option": recommended_option,
            "build_vs_buy": report.get("build_vs_buy"),
            "recommendation": report.get("recommendation"),
        }
        missing_fields = [
            k for k, v in required_fields.items()
            if v is None or (isinstance(v, str) and not v.strip())
        ]
        if missing_fields:
            violations.append(
                "A: required fields not set for verdict '{0}': {1}".format(
                    verdict, ", ".join(missing_fields)
                )
            )
    elif is_reconsider:
        # Only summary, verdict, recommendation required.
        rec_fields = {
            "summary": report.get("summary"),
            "verdict": verdict,
            "recommendation": report.get("recommendation"),
        }
        missing_fields = [
            k for k, v in rec_fields.items()
            if v is None or (isinstance(v, str) and not v.strip())
        ]
        if missing_fields:
            violations.append(
                "A: required fields not set for verdict 'Reconsider': {0}".format(
                    ", ".join(missing_fields)
                )
            )

    # Rule B — design-options minimum.
    if is_pursue and len(design_options) < 1:
        violations.append(
            "B: at least 1 design_option required when verdict is '{0}'; "
            "none recorded".format(verdict)
        )

    # Rule C — recommended-option name match.
    if isinstance(recommended_option, dict) and recommended_option.get("name"):
        rec_name = recommended_option["name"]
        existing_names = [
            opt["name"]
            for opt in design_options
            if isinstance(opt, dict) and "name" in opt
        ]
        if rec_name not in existing_names:
            violations.append(
                "C: recommended_option.name {0!r} does not match any design_option.name "
                "(design_options names: {1})".format(
                    rec_name,
                    ", ".join(repr(n) for n in existing_names) if existing_names else "(none)",
                )
            )

    # Rule D — verdict flip rule.
    if overall_fit in ("Strained", "Misfit") and not is_reconsider and not override_recorded:
        violations.append(
            "D: Verdict flip rule: overall_fit is '{0}' but verdict is '{1}'; "
            "flip to Reconsider OR record an override "
            "(scope-finalize --accept-gaps records one).".format(overall_fit, verdict)
        )
    if (
        effort_estimate == "Major refactor required"
        and not is_reconsider
        and not override_recorded
    ):
        violations.append(
            "D: Verdict flip rule: effort_estimate is 'Major refactor required' "
            "but verdict is '{0}'; flip to Reconsider OR record an override.".format(verdict)
        )

    # Rule E — next-step text presence.
    if is_pursue:
        if not next_step_text or not (isinstance(next_step_text, str) and next_step_text.strip()):
            violations.append(
                "E: verdict is '{0}' but next_step_text is not set; "
                "run set-next-step-text.".format(verdict)
            )
    elif is_reconsider:
        if next_step_text is not None:
            violations.append(
                "E: verdict is 'Reconsider' but next_step_text is set (must be None); "
                "run set-next-step-text to clear it."
            )

    # Rule F — derisk plan.
    if is_pursue and len(report.get("derisk_plan") or []) < 1:
        violations.append(
            "F: at least 1 derisk_plan entry required when verdict is '{0}'; "
            "none recorded".format(verdict)
        )

    # Rule G — internal canonical-pattern cite rule.
    prior_art = report.get("prior_art") or []
    internal_sources = []  # type: List[str]
    for entry in prior_art:
        if not isinstance(entry, dict):
            continue
        source = entry.get("source") or ""
        if isinstance(source, str) and source.startswith("internal:"):
            path = source[len("internal:"):].strip()
            if path:
                internal_sources.append(path)
    if (
        internal_sources
        and isinstance(recommended_option, dict)
        and recommended_option.get("name")
    ):
        rationale = recommended_option.get("rationale") or ""
        if not isinstance(rationale, str) or not any(
            path in rationale for path in internal_sources
        ):
            violations.append(
                "G: Internal canonical-pattern cite rule: prior_art has {0} "
                "entry(ies) with source 'internal:<path>' but recommended_option.rationale "
                "does not cite any of: {1}. Reframe rationale as 'extend existing <path>' "
                "or explicitly state which capability the existing implementation does NOT "
                "cover.".format(
                    len(internal_sources),
                    ", ".join(repr(p) for p in internal_sources),
                )
            )

    if violations:
        for v in violations:
            sys.stderr.write("verify: {0}\n".format(v))
        return 2
    return 0
