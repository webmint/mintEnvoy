"""argparse parser + dispatch + main entry for discover_helper.

Dispatcher-only. All cmd_* handler bodies live in sibling modules:
  _cmds_core   — plumbing + topic/date/summary + render + verify
  _cmds_scope  — Phase 0 dimensions + conflicts + coverage + finalize
  _cmds_fit    — Phase 1 prior-art + touchpoints + fit + overall + effort + rationale
  _cmds_design — Phase 2 design-options + recommended + build-vs-buy + derisk + verdict + recommendation + next-step
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from ._state import RUBRIC_DIMENSIONS


# ---------------------------------------------------------------------------
# CLI-level enum constants — used by _register_subcommands choices.
# ---------------------------------------------------------------------------

# Per-dimension state machine values (used in argparse choices).
RUBRIC_STATE_ENUM = ("Clear", "Partial", "Missing")

# Conflict type enum (Phase 0 misalignment detection).
CONFLICT_TYPE_ENUM = ("direct", "drift", "refinement")

# Complexity rating enum.
COMPLEXITY_ENUM = ("Low", "Med", "High")

# Effort enum (used in fit assessments).
EFFORT_ENUM = ("Low", "Medium", "High", "Major refactor required")

# Overall fit enum.
OVERALL_FIT_ENUM = ("Good", "Acceptable", "Strained", "Misfit")

# Prior-art kind enum (Phase 1 record-prior-art).
PRIOR_ART_KIND_ENUM = ("library", "product", "pattern")

# Verdict enum (go/no-go verdict at Phase 2 close).
VERDICT_ENUM = ("Worth pursuing", "Promising with caveats", "Reconsider")

# Build vs Buy recommendation enum.
BUILD_VS_BUY_ENUM = ("Build", "Buy", "Hybrid")

# Hard-gate prerequisites checked by `preflight`. Tuple of
# (relative-path-from-install-root, producer-label). Mirrors
# research_helper.PREFLIGHT_PREREQS exactly.
PREFLIGHT_PREREQS = (
    (".devforge/init.yaml", "/init-forge"),
    ("docs/architecture.md", "/generate-docs"),
    (".devforge/configure.yaml", "/configure"),
    ("constitution.md", "/constitute"),
)


# ---------------------------------------------------------------------------
# Handler imports — must come AFTER constants so back-import from
# _cmds_core (PREFLIGHT_PREREQS) resolves against the partially-loaded
# module namespace.
# ---------------------------------------------------------------------------

from ._cmds_core import (  # noqa: E402
    cmd_preflight,
    cmd_read_memo,
    cmd_read_report,
    cmd_render,
    cmd_reset_memo,
    cmd_reset_report,
    cmd_set_date,
    cmd_set_summary,
    cmd_set_topic,
    cmd_set_verbatim_prompt,
    cmd_verify,
)
from ._cmds_design import (  # noqa: E402
    cmd_set_build_vs_buy,
    cmd_set_constitution_constraints,
    cmd_set_derisk_plan,
    cmd_set_design_option,
    cmd_set_next_step_text,
    cmd_set_recommendation,
    cmd_set_recommended_option,
    cmd_set_verdict,
)
from ._cmds_fit import (  # noqa: E402
    cmd_record_fit_assessment,
    cmd_record_integration_touchpoint,
    cmd_record_prior_art,
    cmd_set_effort_estimate,
    cmd_set_fit_rationale,
    cmd_set_overall_fit,
)
from ._cmds_handoff import (  # noqa: E402
    cmd_append_outcome,
    cmd_finalize_handoff,
)
from ._cmds_intake import (  # noqa: E402
    INTAKE_KIND_ENUM,
    cmd_record_intake_classification,
    cmd_render_intake_echo,
)
from ._cmds_scope import (  # noqa: E402
    _make_scope_dim_setter,
    cmd_check_conflicts,
    cmd_record_conflict_resolution,
    cmd_record_gap,
    cmd_record_references,
    cmd_scope_coverage,
    cmd_scope_finalize,
)


# ---------------------------------------------------------------------------
# Argparse + main.
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="discover_helper",
        description="State helper for /discover. Owns discover artifact shape.",
    )
    parser.add_argument(
        "--devforge-dir",
        default=".devforge",
        help="Path to the .devforge directory (default: .devforge in CWD).",
    )
    parser.add_argument(
        "--install-root",
        default=None,
        help=(
            "Path to the install root (project root for standalone, wrapper "
            "root for wrapper mode). Default: parent of --devforge-dir."
        ),
    )
    subparsers = parser.add_subparsers(dest="subcommand")
    _register_subcommands(subparsers)
    return parser


def _register_subcommands(subparsers) -> None:
    """All cmd_* handlers registered here."""
    # Plumbing
    sp = subparsers.add_parser("reset-memo", help="Write a fresh defaults memo state.")
    sp.set_defaults(func=cmd_reset_memo)

    sp = subparsers.add_parser("reset-report", help="Write a fresh defaults report state.")
    sp.set_defaults(func=cmd_reset_report)

    sp = subparsers.add_parser(
        "read-memo",
        help="Print discover-scope.json (or defaults) as JSON.",
    )
    sp.set_defaults(func=cmd_read_memo)

    sp = subparsers.add_parser(
        "read-report",
        help="Print discover-report.json (or defaults) as JSON.",
    )
    sp.set_defaults(func=cmd_read_report)

    sp = subparsers.add_parser(
        "preflight",
        help="Hard-gate check: 4 setup-chain artefacts present + non-empty.",
    )
    sp.set_defaults(func=cmd_preflight)

    sp = subparsers.add_parser(
        "set-topic",
        help="Set memo.topic + report.topic and auto-derive topic_slug in both.",
    )
    sp.add_argument("--value", required=True, help="Topic text (user's original input).")
    sp.set_defaults(func=cmd_set_topic)

    sp = subparsers.add_parser(
        "set-verbatim-prompt",
        help=(
            "Persist the full raw prompt text to memo.verbatim_prompt. "
            "Called at Phase 0.3 right after set-topic, before scoping. "
            "Distinct from set-topic: carries the full $ARGUMENTS including any "
            "'we should also ...' additions or hypothesis guesses the one-sentence "
            "topic loses."
        ),
    )
    sp.add_argument(
        "--value",
        required=True,
        help="Full raw prompt text (verbatim, multi-sentence ok).",
    )
    sp.set_defaults(func=cmd_set_verbatim_prompt)

    sp = subparsers.add_parser(
        "set-date",
        help="Set memo.date + report.date (YYYY-MM-DD).",
    )
    sp.add_argument("--value", required=True, help="Date in YYYY-MM-DD format.")
    sp.set_defaults(func=cmd_set_date)

    # Phase 0 — dimension setters (8, one per RUBRIC_DIMENSIONS entry).
    for _dim in RUBRIC_DIMENSIONS:
        _sp_name = "set-scope-" + _dim.replace("_", "-")
        sp = subparsers.add_parser(_sp_name, help="Set scope dimension: {0}.".format(_dim))
        sp.add_argument("--value", required=True, help="Value text (non-empty after strip).")
        sp.add_argument(
            "--state",
            default="Clear",
            choices=list(RUBRIC_STATE_ENUM),
            help="Dimension state after this set (default: Clear).",
        )
        sp.add_argument(
            "--increment-turn",
            action="store_true",
            help="Add 1 to dimensions.<dim>.turns.",
        )
        sp.set_defaults(func=_make_scope_dim_setter(_dim), dimension=_dim)

    sp = subparsers.add_parser(
        "record-references",
        help="Set memo.references to a JSON array of strings (replaces, does not append).",
    )
    sp.add_argument(
        "--values",
        required=True,
        help='JSON array of strings, e.g. \'["A","B"]\'. Use "[]" for none.',
    )
    sp.set_defaults(func=cmd_record_references)

    sp = subparsers.add_parser(
        "record-gap",
        help="Append (or replace) a {dimension, description} gap entry in memo.gaps.",
    )
    sp.add_argument(
        "--dimension",
        required=True,
        choices=list(RUBRIC_DIMENSIONS),
        help="Dimension name (underscore form).",
    )
    sp.add_argument("--description", required=True, help="Gap description (non-empty).")
    sp.set_defaults(func=cmd_record_gap)

    sp = subparsers.add_parser(
        "check-conflicts",
        help=(
            "Scan memo dimensions for direct token-overlap contradictions. "
            "Emits JSON array to stdout. Read-only."
        ),
    )
    sp.set_defaults(func=cmd_check_conflicts)

    sp = subparsers.add_parser(
        "record-conflict-resolution",
        help="Persist user resolution for a detected conflict and clear the loser dimension.",
    )
    sp.add_argument("--index", required=True, type=int, help="0-based index into conflicts list.")
    sp.add_argument("--resolution", required=True, help="Resolution label (free text).")
    sp.add_argument(
        "--rewrite-dimension",
        required=True,
        dest="rewrite_dimension",
        choices=list(RUBRIC_DIMENSIONS),
        help="Dimension whose value to clear (the loser).",
    )
    sp.set_defaults(func=cmd_record_conflict_resolution)

    sp = subparsers.add_parser(
        "scope-coverage",
        help="Emit JSON coverage report for all 8 dimensions. Read-only.",
    )
    sp.set_defaults(func=cmd_scope_coverage)

    sp = subparsers.add_parser(
        "scope-finalize",
        help=(
            "Validate memo is finalize-ready. Exit 0 = ready for Phase 1. "
            "Exit 2 if any violations remain."
        ),
    )
    sp.add_argument(
        "--accept-gaps",
        action="store_true",
        help="Accept Partial/Missing dimensions; record override_recorded=True.",
    )
    sp.set_defaults(func=cmd_scope_finalize)

    # Phase 1 — investigation setters.
    sp = subparsers.add_parser(
        "record-prior-art",
        help="Append one prior-art entry to report.prior_art.",
    )
    sp.add_argument("--reference", required=True, help="Library/product/pattern name (non-empty).")
    sp.add_argument(
        "--kind",
        required=True,
        choices=list(PRIOR_ART_KIND_ENUM),
        help="Kind: one of {0}.".format(", ".join(PRIOR_ART_KIND_ENUM)),
    )
    sp.add_argument("--relevance", required=True, help="One-line note tying it to the topic (non-empty).")
    sp.add_argument(
        "--source",
        default="",
        help="URL or Context7 library id (optional; default empty string).",
    )
    sp.set_defaults(func=cmd_record_prior_art)

    sp = subparsers.add_parser(
        "record-integration-touchpoint",
        help="Append one integration touchpoint entry to report.integration_touchpoints.",
    )
    sp.add_argument("--name", required=True, help="Touchpoint name (non-empty).")
    sp.add_argument("--module-path", required=True, dest="module_path", help="Module path (non-empty).")
    sp.add_argument("--reason", required=True, help="Why this touchpoint matters (non-empty).")
    sp.set_defaults(func=cmd_record_integration_touchpoint)

    sp = subparsers.add_parser(
        "record-fit-assessment",
        help="Append one fit-assessment entry to report.fit_assessments.",
    )
    sp.add_argument(
        "--touchpoint",
        required=True,
        help="Must match the name of an existing integration_touchpoint entry.",
    )
    sp.add_argument("--user-expected", required=True, dest="user_expected", help="User's Phase 0 belief (non-empty).")
    sp.add_argument("--reality", required=True, help="What the codebase scan found (non-empty).")
    sp.add_argument(
        "--effort",
        required=True,
        choices=list(EFFORT_ENUM),
        help="Per-touchpoint effort: one of {0}.".format(", ".join(EFFORT_ENUM)),
    )
    sp.add_argument(
        "--blockers",
        default="[]",
        help='JSON array of strings (optional; default "[]").',
    )
    sp.set_defaults(func=cmd_record_fit_assessment)

    sp = subparsers.add_parser(
        "set-overall-fit",
        help="Set report.overall_fit to an OVERALL_FIT_ENUM value.",
    )
    sp.add_argument(
        "--value",
        required=True,
        choices=list(OVERALL_FIT_ENUM),
        help="One of: {0}.".format(", ".join(OVERALL_FIT_ENUM)),
    )
    sp.set_defaults(func=cmd_set_overall_fit)

    sp = subparsers.add_parser(
        "set-effort-estimate",
        help="Set report.effort_estimate to an EFFORT_ENUM value.",
    )
    sp.add_argument(
        "--value",
        required=True,
        choices=list(EFFORT_ENUM),
        help="One of: {0}.".format(", ".join(EFFORT_ENUM)),
    )
    sp.set_defaults(func=cmd_set_effort_estimate)

    sp = subparsers.add_parser(
        "set-fit-rationale",
        help="Set report.fit_rationale to a non-empty string.",
    )
    sp.add_argument("--value", required=True, help="Rationale text (non-empty).")
    sp.set_defaults(func=cmd_set_fit_rationale)

    # Phase 2 — report drafting + render + verify.
    sp = subparsers.add_parser(
        "set-summary",
        help="Set report.summary to a non-empty string.",
    )
    sp.add_argument("--value", required=True, help="Summary text (non-empty).")
    sp.set_defaults(func=cmd_set_summary)

    sp = subparsers.add_parser(
        "set-design-option",
        help="Append one design-option entry to report.design_options.",
    )
    sp.add_argument("--name", required=True, help="Option name (unique, non-empty).")
    sp.add_argument("--shape", required=True, help="Option shape / description (non-empty).")
    sp.add_argument(
        "--pros",
        required=True,
        help="JSON array of non-empty strings (at least 1 entry).",
    )
    sp.add_argument(
        "--cons",
        required=True,
        help="JSON array of non-empty strings (at least 1 entry).",
    )
    sp.add_argument(
        "--complexity",
        required=True,
        choices=list(COMPLEXITY_ENUM),
        help="Complexity: one of {0}.".format(", ".join(COMPLEXITY_ENUM)),
    )
    sp.set_defaults(func=cmd_set_design_option)

    sp = subparsers.add_parser(
        "set-recommended-option",
        help="Set report.recommended_option; --name must match an existing design_option.name.",
    )
    sp.add_argument("--name", required=True, help="Must match an existing design_option name.")
    sp.add_argument("--rationale", required=True, help="Rationale for recommendation (non-empty).")
    sp.set_defaults(func=cmd_set_recommended_option)

    sp = subparsers.add_parser(
        "set-build-vs-buy",
        help="Set report.build_vs_buy.",
    )
    sp.add_argument("--build", required=True, help="Build-path description (non-empty).")
    sp.add_argument("--buy", required=True, help="Buy/adopt-path description (non-empty).")
    sp.add_argument(
        "--recommendation",
        required=True,
        choices=list(BUILD_VS_BUY_ENUM),
        help="Recommendation: one of {0}.".format(", ".join(BUILD_VS_BUY_ENUM)),
    )
    sp.add_argument("--reasoning", required=True, help="Reasoning text (non-empty).")
    sp.set_defaults(func=cmd_set_build_vs_buy)

    sp = subparsers.add_parser(
        "set-derisk-plan",
        help="Set report.derisk_plan to a JSON array of strings.",
    )
    sp.add_argument(
        "--items",
        required=True,
        help="JSON array of non-empty strings (at least 1 item).",
    )
    sp.set_defaults(func=cmd_set_derisk_plan)

    sp = subparsers.add_parser(
        "set-constitution-constraints",
        help="Append one entry to report.constitution_constraints.",
    )
    sp.add_argument("--rule", required=True, help="Constraint rule text (non-empty).")
    sp.add_argument("--impact", required=True, help="Impact description (non-empty).")
    sp.set_defaults(func=cmd_set_constitution_constraints)

    sp = subparsers.add_parser(
        "set-verdict",
        help="Set report.verdict to a VERDICT_ENUM value.",
    )
    sp.add_argument(
        "--value",
        required=True,
        choices=list(VERDICT_ENUM),
        help="Verdict: one of {0}.".format(", ".join(VERDICT_ENUM)),
    )
    sp.set_defaults(func=cmd_set_verdict)

    sp = subparsers.add_parser(
        "set-recommendation",
        help="Set report.recommendation.",
    )
    sp.add_argument("--action", required=True, help="Action text (non-empty).")
    sp.add_argument("--next", required=True, dest="next_text", help="Next step text (non-empty).")
    sp.set_defaults(func=cmd_set_recommendation)

    sp = subparsers.add_parser(
        "set-next-step-text",
        help=(
            "Compose and set report.next_step_text from memo + report state. "
            "Reads memo.functional_scope/users/success_criteria + report.verdict + "
            "report.recommended_option. Optional --topic supplies an LLM-distilled "
            "1-2 sentence topic for the /specify block (otherwise the helper falls "
            "back to the first sentence of memo.functional_scope)."
        ),
    )
    sp.add_argument(
        "--topic",
        required=False,
        default=None,
        help=(
            "Distilled 1-2 sentence topic to embed in the /specify \"...\" block. "
            "Overrides the helper's first-sentence fallback. Pass the same distilled "
            "string the orchestrator composed from functional_scope + users + "
            "success_criteria."
        ),
    )
    sp.set_defaults(func=cmd_set_next_step_text)

    sp = subparsers.add_parser(
        "render",
        help="Render the full discovery report as Markdown to stdout. Read-only.",
    )
    sp.set_defaults(func=cmd_render)

    sp = subparsers.add_parser(
        "verify",
        help=(
            "Cross-field invariant check. Exit 0 = clean. "
            "Exit 2 = violations (all enumerated on stderr)."
        ),
    )
    sp.set_defaults(func=cmd_verify)

    # Step 5 — intake-interrogation gate.
    sp = subparsers.add_parser(
        "record-intake-classification",
        help=(
            "Persist a per-statement binary intake classification "
            "(requirement vs hypothesis/scope-expander) + the minimal_fix. "
            "Called once per statement in the verbatim prompt. "
            "Re-recording the same statement replaces its entry (idempotent). "
            "NOTE discover lane: 'hypothesis' = scope-expander / placement guess; "
            "route to record-gap --dimension integration_points separately."
        ),
    )
    sp.add_argument(
        "--statement",
        required=True,
        help="The prompt statement being classified (verbatim or paraphrased).",
    )
    sp.add_argument(
        "--kind",
        required=True,
        choices=list(INTAKE_KIND_ENUM),
        help="Binary classification: 'requirement' or 'hypothesis' (scope-expander).",
    )
    sp.add_argument(
        "--minimal-fix",
        default=None,
        dest="minimal_fix",
        help=(
            "The minimal scope that satisfies this statement's desired feature intent. "
            "Optional; typically set for requirement statements."
        ),
    )
    sp.set_defaults(func=cmd_record_intake_classification)

    sp = subparsers.add_parser(
        "render-intake-echo",
        help=(
            "Render the discover intake echo-back block (requirements / "
            "scope-expanders-to-verify / minimal scope) to stdout. "
            "Orchestrator copies verbatim to user before one confirmation. "
            "Proportional: no scope-expanders section when none recorded."
        ),
    )
    sp.set_defaults(func=cmd_render_intake_echo)

    # Step 3 -- finalize-handoff.
    sp = subparsers.add_parser(
        "finalize-handoff",
        help="Emit handoff.json from discover state (terminal phase).",
    )
    sp.add_argument(
        "--emit-handoff-json",
        default=None,
        dest="emit_handoff_json",
        help=(
            "Override output path. Default: discover/<report.date>-<memo.topic_slug>.handoff.json"
        ),
    )
    sp.set_defaults(func=cmd_finalize_handoff)

    # Step 5 -- append-outcome.
    sp = subparsers.add_parser(
        "append-outcome",
        help="Record post-discovery outcome into handoff.json (Step 5).",
    )
    sp.add_argument(
        "--handoff-path",
        required=True,
        dest="handoff_path",
        help="Path to the handoff.json file (e.g. discover/<date>-<slug>.handoff.json).",
    )
    sp.add_argument(
        "--design-option-shipped-id",
        required=True,
        dest="design_option_shipped_id",
        choices=("A", "B", "C", "D", "E", "F", "G", "H", "hybrid", "none"),
        help="Which design option actually shipped.",
    )
    sp.add_argument(
        "--design-option-shipped-summary",
        required=True,
        dest="design_option_shipped_summary",
        help="1-3 sentence description of what shipped.",
    )
    sp.add_argument(
        "--build-vs-buy-actual",
        required=True,
        dest="build_vs_buy_actual",
        choices=("Build", "Buy", "Hybrid", "none"),
        help="Actual build-vs-buy path taken.",
    )
    sp.add_argument(
        "--shipped-commit-sha",
        default=None,
        dest="shipped_commit_sha",
        help="Optional: 7-40 char hex SHA of the commit that shipped the feature.",
    )
    sp.add_argument(
        "--delta-from-recommendation",
        default=None,
        dest="delta_from_recommendation",
        help="Required when any match flag is False: how reality diverged from recommendation.",
    )
    sp.add_argument(
        "--internal-extension-followed",
        default=None,
        dest="internal_extension_followed",
        choices=("true", "false"),
        help=(
            "Required when handoff has internal prior-art entries: "
            "whether the internal canonical-pattern extension was followed."
        ),
    )
    sp.set_defaults(func=cmd_append_outcome)


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "func", None) is None:
        parser.print_help(sys.stderr)
        return 2
    if args.install_root is None:
        args.install_root = str(Path(args.devforge_dir).resolve().parent)
    return args.func(args)
