"""Plumbing + summary subcommand handlers.

reset-memo / reset-report / read-memo / read-report / preflight /
set-topic / set-date / summary. Plus the topic-slug / scope-evidence
side effects on memo writes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List, Tuple

from ._constants import (
    PREFLIGHT_PREREQS,
    RUBRIC_DIMENSIONS,
    RUBRIC_STATE_DEFAULT,
)
from ._layer_package import _extract_package
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
from ._topic_conflicts import _compute_coverage, derive_topic_slug
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
    """Print research-state.json as JSON to stdout (defaults if missing)."""
    try:
        state = _load_memo(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("read-memo: {0}".format(err))
    json.dump(state, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


def cmd_read_report(args: argparse.Namespace) -> int:
    """Print research-report.json as JSON to stdout (defaults if missing)."""
    try:
        state = _load_report(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("read-report: {0}".format(err))
    json.dump(state, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


def cmd_preflight(args: argparse.Namespace) -> int:
    """4-artefact hard gate. Non-zero exit 2 + BLOCKED message on missing.

    Checks each PREFLIGHT_PREREQS path relative to --install-root for
    existence + non-empty (size > 0). On any failure, emits a single
    BLOCKED message naming the missing artefact + the producer command
    and exits 2.

    Distinct from generate_docs_helper preflight (which refreshes the
    CBM index stamp). This gate enforces that the 4-command setup chain
    is complete before /research runs.
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
            "BLOCKED: /research requires the full 4-command setup chain.\n"
        )
        for rel, producer in missing:
            sys.stderr.write("Missing: {0} (produced by {1})\n".format(rel, producer))
        sys.stderr.write(
            "Run: /init-forge → /generate-docs → /configure → /constitute, "
            "then retry /research.\n"
        )
        return 2
    return 0


def cmd_set_topic(args: argparse.Namespace) -> int:
    """Set report.topic + auto-derive memo.topic_slug from topic.

    Topic comes from the user's original /research argument. Auto-deriving
    slug at this layer means the orchestrator only owns one input string;
    helper renders both topic text and filename slug.
    """
    try:
        value = _validate_scalar(args.value, "topic")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["topic"] = value
        with _state_transaction(args.devforge_dir, "memo") as memo:
            memo["topic_slug"] = derive_topic_slug(value)
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-topic: {0}".format(err))
    return 0


def cmd_set_verbatim_prompt(args: argparse.Namespace) -> int:
    """Persist the full raw prompt text to memo.verbatim_prompt.

    Called at Phase 0.3 immediately after set-topic, before the rubric runs.
    The prompt text is stored verbatim (internal whitespace preserved, leading/
    trailing whitespace stripped). This is a DISTINCT field from the one-sentence
    topic set by set-topic: the full prompt may carry a 'Suspected cause:' tail
    or other context that the paraphrased topic loses.
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


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def cmd_set_date(args: argparse.Namespace) -> int:
    """Set report.date. Format YYYY-MM-DD enforced."""
    if not _DATE_RE.match(args.value):
        return _die(
            "set-date: invalid date {0!r}; expected YYYY-MM-DD".format(args.value),
            code=2,
        )
    try:
        with _state_transaction(args.devforge_dir, "report") as report:
            report["date"] = args.value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-date: {0}".format(err))
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    """Read-only stdout summary across both state files."""
    try:
        memo = _load_memo(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("summary: cannot load memo: {0}".format(err), code=1)
    try:
        report = _load_report(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("summary: cannot load report: {0}".format(err), code=1)

    state_map, clear, partial, missing = _compute_coverage(memo)
    lines = []  # type: List[str]
    lines.append("Phase 0 (memo):")
    lines.append("  mode: {0}".format(memo.get("mode") or "(unset)"))
    lines.append("  topic_slug: {0}".format(memo.get("topic_slug") or "(unset)"))
    for d in RUBRIC_DIMENSIONS:
        rec = memo.get("dimensions", {}).get(d, {})
        val = rec.get("value") or "(unset)"
        st = rec.get("state") or RUBRIC_STATE_DEFAULT
        turns = rec.get("turns", 0)
        line = "  {0}: state={1} turns={2} value={3!r}".format(d, st, turns, val[:80])
        # Surface evidence field for scope narrow-framing runs.
        if d == "scope":
            scope_evidence = rec.get("evidence")
            if scope_evidence:
                line += " evidence={0}".format(scope_evidence)
        lines.append(line)
    lines.append("  coverage: Clear={0} Partial={1} Missing={2}".format(clear, partial, missing))
    lines.append("  gaps: {0}".format(len(memo.get("gaps", []))))
    lines.append("  conflicts: {0}".format(len(memo.get("conflicts", []))))
    lines.append("  override_recorded: {0}".format(memo.get("override_recorded", False)))

    lines.append("")
    lines.append("Phase 1+2 (report):")
    lines.append("  mode: {0}".format(report.get("mode") or "(unset)"))
    lines.append("  verdict: {0}".format(report.get("verdict") or "(unset)"))
    lines.append("  confidence: {0}".format(report.get("confidence") or "(unset)"))
    lines.append("  findings: {0}".format(len(report.get("findings", []))))
    lines.append("  hypotheses: {0}".format(len(report.get("hypotheses", []))))
    lines.append("  approaches: {0}".format(len(report.get("approaches", []))))
    lines.append("  recommended_approach: {0}".format(
        (report.get("recommended_approach") or {}).get("name") or "(unset)"
    ))
    # Single-layer detection summary line: shown for bug mode + non-empty fix_path_helpers.
    mode_for_summary = report.get("mode") or memo.get("mode")
    fix_path_helpers_for_summary = report.get("fix_path_helpers") or []
    if mode_for_summary == "bug" and fix_path_helpers_for_summary:
        packages_summary = set()
        for h in fix_path_helpers_for_summary:
            if isinstance(h, dict) and h.get("file_line"):
                pkg = _extract_package(h["file_line"].rsplit(":", 1)[0])
                if pkg:
                    packages_summary.add(pkg)
        single_layer_label = "yes" if len(packages_summary) == 1 else "no"
        lines.append("  recommended_approach.single_layer: {0}".format(single_layer_label))
    lines.append("  structured_root_cause: {0}".format(
        "set" if report.get("structured_root_cause") else "(unset)"
    ))
    lines.append("  verify_step: {0}".format("set" if report.get("verify_step") else "(unset)"))
    lines.append("  next_step_text: {0}".format("set" if report.get("next_step_text") else "(unset)"))
    # Rejection log: surface count when non-empty (useful debug signal for anchor gate).
    rejection_log_for_summary = report.get("helper_rejection_log") or []
    if rejection_log_for_summary:
        lines.append("  helper_rejection_count: {0}".format(len(rejection_log_for_summary)))

    sys.stdout.write("\n".join(lines) + "\n")
    return 0
