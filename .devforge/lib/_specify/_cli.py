"""argparse parser + dispatch + main entry for specify_helper."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from ._cmds_phase01 import (
    cmd_detect_mode,
    cmd_findings_finalize,
    cmd_mark_source_no_items_relevant,
    cmd_phase1_finalize,
    cmd_preflight,
    cmd_read_state,
    cmd_record_finding,
    cmd_record_input_read,
    cmd_render_findings,
    cmd_reset_state,
    cmd_verify_findings,
)
from ._cmds_phase2 import (
    cmd_dp_coverage,
    cmd_dp_finalize,
    cmd_record_decision_point,
    cmd_rubric_coverage,
    cmd_rubric_finalize,
    cmd_set_dp_answer,
    cmd_set_dp_default_applied,
    cmd_set_dp_deferral,
    cmd_verify_decision_coverage,
)
from ._cmds_phase3 import (
    cmd_classify_spec_type,
    cmd_phase3_finalize,
    cmd_record_mandatory_read,
    cmd_summary,
    cmd_verify_mandatory_reads,
)
from ._cmds_phase4_setters import (
    _LANDABLE_BUCKETS,
    cmd_add_ac,
    cmd_assign_feature_name,
    cmd_assign_spec_number,
    cmd_create_branch,
    cmd_record_affected_area,
    cmd_record_constraint,
    cmd_record_open_question,
    cmd_record_out_of_scope,
    cmd_record_risk,
    cmd_set_current_state,
    cmd_set_date,
    cmd_set_design_source,
    cmd_set_desired_behavior,
    cmd_set_finding_landed,
    cmd_set_overview,
)
from ._cmds_phase4_verify import (
    cmd_check_constitution_compliance,
    cmd_render,
    cmd_verify_ac_shape,
    cmd_verify_ac_subsection_coverage,
    cmd_verify_coverage,
    cmd_verify_numerical_consistency,
    cmd_verify_rendered,
    cmd_verify_scope_coherence,
)
from ._cmds_handoff import (
    cmd_find_handoffs,
    cmd_finalize_handoff,
    cmd_import_handoff,
)
from ._cmds_phase5 import (
    cmd_render_plan_handoff,
    cmd_render_summary,
    cmd_resolve_open_question,
    cmd_set_status,
)
from ._schema import (
    AC_SUBSECTION_ENUM,
    CONSTRAINT_KIND_ENUM,
    DESIGN_SOURCE_SCHEME_ENUM,
    DP_DEFERRAL_KIND_ENUM,
    IMPACT_ENUM,
    LANDED_IN_DEFAULT,
    LIKELIHOOD_ENUM,
    RESOLUTION_PHASE_ENUM,
    SPEC_STATUS_ENUM,
    SPEC_TYPE_ENUM,
    SPECS_ROOT_DEFAULT,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="specify_helper",
        description="State helper for /specify; owns "
                    ".devforge/specify-state.json shape.",
    )
    parser.add_argument(
        "--devforge-dir", default=".devforge",
        help="Path to .devforge dir (default: .devforge)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("reset-state", help="Reset state to defaults.")
    sp.set_defaults(func=cmd_reset_state)

    sp = sub.add_parser("read-state", help="Dump state JSON to stdout.")
    sp.set_defaults(func=cmd_read_state)

    sp = sub.add_parser(
        "preflight", help="Hard-gate 4-command chain + constitution guard.",
    )
    sp.add_argument("--install-root", default=".")
    sp.set_defaults(func=cmd_preflight)

    sp = sub.add_parser(
        "record-input-read",
        help="Record a Phase 1 input read (path-tagged source_origin).",
    )
    sp.add_argument("--path", required=True)
    sp.set_defaults(func=cmd_record_input_read)

    sp = sub.add_parser(
        "phase1-finalize",
        help="Gate Phase 1 → Phase 1.5 (all 4 mandatory reads recorded).",
    )
    sp.set_defaults(func=cmd_phase1_finalize)

    sp = sub.add_parser(
        "record-finding", help="Record a Phase 1.5 finding.",
    )
    sp.add_argument("--source-path", required=True, dest="source_path")
    sp.add_argument("--content", required=True)
    sp.add_argument(
        "--source-section", default="", dest="source_section",
    )
    sp.add_argument(
        "--landed-in", default=LANDED_IN_DEFAULT, dest="landed_in",
    )
    sp.add_argument("--landed-ref", default="", dest="landed_ref")
    sp.set_defaults(func=cmd_record_finding)

    sp = sub.add_parser(
        "mark-source-no-items-relevant",
        help="Mark a read source as irrelevant (waives ≥3-bullet rule).",
    )
    sp.add_argument("--source-path", required=True, dest="source_path")
    sp.set_defaults(func=cmd_mark_source_no_items_relevant)

    sp = sub.add_parser(
        "verify-findings",
        help="Per-source coverage check (≥3 findings or marker).",
    )
    sp.set_defaults(func=cmd_verify_findings)

    sp = sub.add_parser(
        "render-findings", help="Emit Phase 1.5 section to stdout.",
    )
    sp.set_defaults(func=cmd_render_findings)

    sp = sub.add_parser(
        "findings-finalize",
        help="Gate Phase 1.5 → Phase 2 (verify-findings + stamp).",
    )
    sp.set_defaults(func=cmd_findings_finalize)

    # ----- Phase 2 ---------------------------------------------------------

    sp = sub.add_parser(
        "detect-mode",
        help="Resolve auto vs interactive mode from C-strict signals.",
    )
    sp.add_argument(
        "--auto", action="store_true", default=False,
        help="Force auto mode (one of three C-strict signals).",
    )
    sp.add_argument(
        "--reminder-text", default="", dest="reminder_text",
        help="Text of latest <system-reminder> block (orchestrator-supplied).",
    )
    sp.set_defaults(func=cmd_detect_mode)

    sp = sub.add_parser(
        "record-decision-point",
        help="Record a Phase 2 DecisionPoint (≥2 valid_implementations).",
    )
    sp.add_argument("--category", required=True)
    sp.add_argument("--description", required=True)
    sp.add_argument(
        "--valid-implementations", default="[]",
        dest="valid_implementations",
        help="JSON array of strings; ≥2 entries required.",
    )
    sp.add_argument(
        "--no-dp-in-category", action="store_true", default=False,
        dest="no_dp_in_category",
        help="Record terminal NoDPInCategory marker (skips ≥2-impl rule).",
    )
    sp.set_defaults(func=cmd_record_decision_point)

    sp = sub.add_parser(
        "set-dp-answer",
        help="Interactive path: mark DP answered with user_answer.",
    )
    sp.add_argument("--dp-id", required=True, dest="dp_id")
    sp.add_argument("--user-answer", required=True, dest="user_answer")
    sp.set_defaults(func=cmd_set_dp_answer)

    sp = sub.add_parser(
        "set-dp-default-applied",
        help="Auto path: mark DP default_applied with named default.",
    )
    sp.add_argument("--dp-id", required=True, dest="dp_id")
    sp.add_argument(
        "--default-applied", required=True, dest="default_applied",
    )
    sp.set_defaults(func=cmd_set_dp_default_applied)

    sp = sub.add_parser(
        "set-dp-deferral",
        help="Defer DP to OOS or open-question (auto-fires turn cap).",
    )
    sp.add_argument("--dp-id", required=True, dest="dp_id")
    sp.add_argument(
        "--deferral-kind", required=True, dest="deferral_kind",
        choices=list(DP_DEFERRAL_KIND_ENUM),
    )
    sp.add_argument("--reason", required=True)
    sp.add_argument(
        "--increment-turn", action="store_true", default=False,
        dest="increment_turn",
        help="Bump per-DP follow-up counter; turn cap may force open-question.",
    )
    sp.set_defaults(func=cmd_set_dp_deferral)

    sp = sub.add_parser(
        "dp-coverage", help="Emit per-DP {dp_id: status} JSON.",
    )
    sp.set_defaults(func=cmd_dp_coverage)

    sp = sub.add_parser(
        "rubric-coverage",
        help="Emit per-category {category: state} JSON.",
    )
    sp.set_defaults(func=cmd_rubric_coverage)

    sp = sub.add_parser(
        "verify-decision-coverage",
        help="Gate: every category ∈ {Clear, NoDPInCategory}.",
    )
    sp.set_defaults(func=cmd_verify_decision_coverage)

    sp = sub.add_parser(
        "rubric-finalize",
        help="Same gate as verify-decision-coverage (plan line 333).",
    )
    sp.set_defaults(func=cmd_rubric_finalize)

    sp = sub.add_parser(
        "dp-finalize",
        help="Gate Phase 2 → Phase 3 (verify-decision-coverage + stamp).",
    )
    sp.set_defaults(func=cmd_dp_finalize)

    # ----- Phase 3 ---------------------------------------------------------

    sp = sub.add_parser(
        "classify-spec-type",
        help="Set spec_type + rationale + (optional) seeded-by-upstream flag.",
    )
    sp.add_argument(
        "--spec-type", required=True, dest="spec_type",
        choices=list(SPEC_TYPE_ENUM),
    )
    sp.add_argument("--rationale", required=True)
    sp.add_argument(
        "--seeded-by-upstream", action="store_true", default=False,
        dest="seeded_by_upstream",
        help="Phase 1 adapter pre-seeded from /discover (path-based).",
    )
    sp.set_defaults(func=cmd_classify_spec_type)

    sp = sub.add_parser(
        "record-mandatory-read",
        help="Record a Phase 3 mandatory-read entry (--read-path or "
             "--n-a-reason+--slot-pattern).",
    )
    sp.add_argument(
        "--read-path", default="", dest="read_path",
        help="Actual file path read (mutually exclusive with --n-a-reason).",
    )
    sp.add_argument(
        "--slot-pattern", default="", dest="slot_pattern",
        help="Explicit slot pattern (required with --n-a-reason; "
             "optional with --read-path for sentinel slots).",
    )
    sp.add_argument(
        "--n-a-reason", default="", dest="n_a_reason",
        help="Reason for marking the slot N/A.",
    )
    sp.set_defaults(func=cmd_record_mandatory_read)

    sp = sub.add_parser(
        "verify-mandatory-reads",
        help="Walk MANDATORY_READS_BY_TYPE; every slot must be covered.",
    )
    sp.set_defaults(func=cmd_verify_mandatory_reads)

    sp = sub.add_parser(
        "phase3-finalize",
        help="Gate Phase 3 → Phase 4 (verify-mandatory-reads + stamp).",
    )
    sp.set_defaults(func=cmd_phase3_finalize)

    # ----- Phase 4 ---------------------------------------------------------

    sp = sub.add_parser(
        "assign-spec-number",
        help="Scan specs/ for highest NNN-*; emit + persist next.",
    )
    sp.add_argument(
        "--specs-root", default=SPECS_ROOT_DEFAULT, dest="specs_root",
        help="Path to specs/ root (default: specs).",
    )
    sp.set_defaults(func=cmd_assign_spec_number)

    sp = sub.add_parser(
        "assign-feature-name",
        help="Validate 2-4 word kebab-case + persist feature_name/slug.",
    )
    sp.add_argument("--feature-name", required=True, dest="feature_name")
    sp.set_defaults(func=cmd_assign_feature_name)

    sp = sub.add_parser(
        "set-date",
        help="Set spec header Date (YYYY-MM-DD).",
    )
    sp.add_argument("--date", required=True)
    sp.set_defaults(func=cmd_set_date)

    sp = sub.add_parser(
        "set-design-source",
        help=(
            "Set the design_source field rendered as **Design source**: in "
            "spec.md. --value must be 'none' or '<scheme>:<target>' where "
            "scheme ∈ {html, figma, screenshot} and target is non-empty."
        ),
    )
    sp.add_argument(
        "--value", required=True,
        help=(
            "Design source value. Valid forms: "
            "html:<path> | figma:<url> | screenshot:<path> | none"
        ),
    )
    sp.set_defaults(func=cmd_set_design_source)

    sp = sub.add_parser(
        "create-branch",
        help="Emit git checkout-b for spec branch when on default branch.",
    )
    sp.add_argument(
        "--current-branch", required=True, dest="current_branch",
    )
    sp.add_argument(
        "--default-branch", required=True, dest="default_branch",
    )
    sp.set_defaults(func=cmd_create_branch)

    sp = sub.add_parser(
        "record-affected-area",
        help="Append §4 row {area, files, impact}.",
    )
    sp.add_argument("--area", required=True)
    sp.add_argument(
        "--files", default="[]",
        help="JSON array of strings.",
    )
    sp.add_argument("--impact", required=True)
    sp.set_defaults(func=cmd_record_affected_area)

    sp = sub.add_parser(
        "set-overview", help="Set §1 Overview content.",
    )
    sp.add_argument("--content", required=True)
    sp.set_defaults(func=cmd_set_overview)

    sp = sub.add_parser(
        "set-current-state", help="Set §2 Current State content.",
    )
    sp.add_argument("--content", required=True)
    sp.set_defaults(func=cmd_set_current_state)

    sp = sub.add_parser(
        "set-desired-behavior",
        help="Set §3 Desired Behavior content.",
    )
    sp.add_argument("--content", required=True)
    sp.set_defaults(func=cmd_set_desired_behavior)

    sp = sub.add_parser(
        "add-ac",
        help="Add §5 Acceptance Criterion (validates EARS regex + "
             "subsection-EARS constraint).",
    )
    sp.add_argument("--ac-id", default="", dest="ac_id")
    sp.add_argument(
        "--subsection", required=True,
        choices=list(AC_SUBSECTION_ENUM),
    )
    sp.add_argument(
        "--ears-variant", default="", dest="ears_variant",
    )
    sp.add_argument("--statement", default="")
    sp.add_argument(
        "--verification-command", default="",
        dest="verification_command",
    )
    sp.add_argument(
        "--test-anchor", default="", dest="test_anchor",
    )
    sp.add_argument(
        "--n-a-reason", default="", dest="n_a_reason",
    )
    sp.add_argument(
        "--mark-na", action="store_true", default=False, dest="mark_na",
        help="Record subsection-level N/A marker (requires --n-a-reason).",
    )
    sp.add_argument(
        "--finding-ref", action="append", dest="finding_ref", default=None,
        metavar="FINDING_ID",
        help="Phase 1.5 finding_id to land in this AC (repeatable).",
    )
    sp.set_defaults(func=cmd_add_ac)

    sp = sub.add_parser(
        "record-out-of-scope",
        help="Append §6 OOS entry {content, finding_ref?}.",
    )
    sp.add_argument("--content", required=True)
    sp.add_argument(
        "--finding-ref", default="", dest="finding_ref",
        help="Optional cross-ref to Phase 1.5 finding_id.",
    )
    sp.set_defaults(func=cmd_record_out_of_scope)

    sp = sub.add_parser(
        "record-constraint",
        help="Append §7 Constraint entry — kind-specific shape.",
    )
    sp.add_argument(
        "--kind",
        required=True,
        choices=list(CONSTRAINT_KIND_ENUM) + ["use"],
        help=(
            "Constraint kind. `use` is reserved + rejected at runtime "
            "to surface a migration message; new code must pick one of "
            "follow / not_break / nfr / constitution_anchor / external_system."
        ),
    )
    sp.add_argument("--content", required=True)
    sp.add_argument(
        "--quantifier",
        default=None,
        help="REQUIRED for --kind nfr. Numeric threshold + unit OR named-class citation.",
    )
    sp.add_argument(
        "--constitution-ref",
        default=None,
        dest="constitution_ref",
        help="REQUIRED for --kind constitution_anchor (e.g. '§3.6'). Helper greps constitution.md.",
    )
    sp.add_argument(
        "--protocol",
        default=None,
        help="EITHER --protocol OR --contract-doc-ref required for --kind external_system.",
    )
    sp.add_argument(
        "--contract-doc-ref",
        default=None,
        dest="contract_doc_ref",
        help="EITHER --protocol OR --contract-doc-ref required for --kind external_system.",
    )
    sp.add_argument(
        "--finding-ref", action="append", dest="finding_ref", default=None,
        metavar="FINDING_ID",
        help="Phase 1.5 finding_id to land as this Constraint (repeatable).",
    )
    sp.set_defaults(func=cmd_record_constraint)

    sp = sub.add_parser(
        "record-open-question",
        help="Append §8 Open Question entry.",
    )
    sp.add_argument(
        "--question-id", required=True, dest="question_id",
    )
    sp.add_argument("--content", required=True)
    sp.add_argument(
        "--category-no-dp-reason", default="",
        dest="category_no_dp_reason",
        help="Optional: per-Phase-2-category 'no DP' rationale.",
    )
    sp.set_defaults(func=cmd_record_open_question)

    sp = sub.add_parser(
        "record-risk",
        help="Append §9 Risks row {risk, likelihood, impact, mitigation}.",
    )
    sp.add_argument("--risk", required=True)
    sp.add_argument(
        "--likelihood", required=True, choices=list(LIKELIHOOD_ENUM),
    )
    sp.add_argument(
        "--impact", required=True, choices=list(IMPACT_ENUM),
    )
    sp.add_argument("--mitigation", required=True)
    sp.add_argument(
        "--finding-ref", action="append", dest="finding_ref", default=None,
        metavar="FINDING_ID",
        help="Phase 1.5 finding_id to land as this Risk (repeatable).",
    )
    sp.set_defaults(func=cmd_record_risk)

    sp = sub.add_parser(
        "set-finding-landed",
        help="Directly flip landed_in/landed_ref on a Phase 1.5 finding.",
    )
    sp.add_argument(
        "--finding-id", required=True, dest="finding_id",
        help="finding_id of the finding to update (e.g. F-constitution-1).",
    )
    sp.add_argument(
        "--landed-in", required=True, dest="landed_in",
        choices=list(_LANDABLE_BUCKETS),
        help="Destination bucket (AC / Constraint / OOS / Risk).",
    )
    sp.add_argument(
        "--landed-ref", default="", dest="landed_ref",
        help="Optional reference to the landing entry (e.g. AC-3, Constraint-1).",
    )
    sp.set_defaults(func=cmd_set_finding_landed)

    sp = sub.add_parser(
        "verify-coverage",
        help="Variance rule #5: every finding landed in AC/Constraint/OOS/Risk.",
    )
    sp.set_defaults(func=cmd_verify_coverage)

    sp = sub.add_parser(
        "verify-numerical-consistency",
        help="Variance rule #6: digit-prefixed nouns consistent across spec.",
    )
    sp.set_defaults(func=cmd_verify_numerical_consistency)

    sp = sub.add_parser(
        "verify-ac-subsection-coverage",
        help="Every of 7 subsections has ≥1 AC or N/A reason.",
    )
    sp.set_defaults(func=cmd_verify_ac_subsection_coverage)

    sp = sub.add_parser(
        "verify-ac-shape",
        help="Variance rule #10: every AC.statement matches EARS regex.",
    )
    sp.set_defaults(func=cmd_verify_ac_shape)

    sp = sub.add_parser(
        "check-constitution-compliance",
        help="Non-blocking: surface constitution MUST/SHALL overlap warnings.",
    )
    sp.add_argument(
        "--constitution-path", default="constitution.md",
        dest="constitution_path",
        help="Path to constitution.md (default: ./constitution.md).",
    )
    sp.set_defaults(func=cmd_check_constitution_compliance)

    sp = sub.add_parser(
        "verify-scope-coherence",
        help=(
            "Non-blocking: flag §5 ACs / §4 affected-areas whose text "
            "token-overlaps a §6 Out-of-Scope entry (§5↔§6 contradiction "
            "candidate). Exits 0 always; warnings to stderr."
        ),
    )
    sp.set_defaults(func=cmd_verify_scope_coherence)

    sp = sub.add_parser(
        "render", help="Emit 9-section spec markdown to stdout.",
    )
    sp.set_defaults(func=cmd_render)

    sp = sub.add_parser(
        "verify-rendered",
        help="Post-write integrity check: on-disk spec.md vs helper render"
             " (canonical-form compare).",
    )
    sp.add_argument(
        "--path", required=True,
        help="Path to the rendered spec.md to verify.",
    )
    sp.set_defaults(func=cmd_verify_rendered)

    # ----- Phase 5 ---------------------------------------------------------

    sp = sub.add_parser(
        "render-summary",
        help="Emit 4-bullet approval summary; persist to state.",
    )
    sp.set_defaults(func=cmd_render_summary)

    sp = sub.add_parser(
        "set-status",
        help="Set spec.status; closed enum.",
    )
    sp.add_argument(
        "--status", required=True, choices=list(SPEC_STATUS_ENUM),
    )
    sp.set_defaults(func=cmd_set_status)

    sp = sub.add_parser(
        "render-plan-handoff",
        help="Emit deterministic /plan handoff block; persist to state.",
    )
    sp.set_defaults(func=cmd_render_plan_handoff)

    # ----- Downstream ------------------------------------------------------

    sp = sub.add_parser(
        "resolve-open-question",
        help="Append resolution audit entry for §8 Open Question.",
    )
    sp.add_argument(
        "--question-id", required=True, dest="question_id",
    )
    sp.add_argument(
        "--resolution-text", required=True, dest="resolution_text",
    )
    sp.add_argument(
        "--resolution-phase", required=True, dest="resolution_phase",
        choices=list(RESOLUTION_PHASE_ENUM),
    )
    sp.set_defaults(func=cmd_resolve_open_question)

    # ----- Pre-phase — handoff import + discovery -------------------------

    sp = sub.add_parser(
        "import-handoff",
        help="Pre-seed specify state from a research handoff.json.",
    )
    sp.add_argument(
        "--handoff-path", required=True, dest="handoff_path",
        help="Path to handoff.json (absolute or relative to cwd).",
    )
    sp.set_defaults(func=cmd_import_handoff)

    sp = sub.add_parser(
        "finalize-handoff",
        help="Emit specify->plan handoff.json from approved specify state.",
    )
    sp.add_argument(
        "--emit-handoff-json", dest="emit_handoff_json", default=None,
        help=(
            "Override output path for handoff.json. "
            "Defaults to {specs-root}/{spec_number}-{feature_slug}/handoff.json."
        ),
    )
    sp.add_argument(
        "--specs-root", dest="specs_root", default="specs",
        help="Root directory for specs (default: 'specs').",
    )
    sp.add_argument(
        "--completed-at", dest="completed_at", default=None,
        help=(
            "ISO-8601 UTC timestamp for specify_completed_at. "
            "Defaults to current UTC time. Use for deterministic tests."
        ),
    )
    sp.set_defaults(func=cmd_finalize_handoff)

    sp = sub.add_parser(
        "find-handoffs",
        help="Glob research/**/handoff.json; filter by mtime within --since window.",
    )
    sp.add_argument(
        "--since", required=True,
        help="Duration window, e.g. '7 days', '24 hours', '1 hour'.",
    )
    sp.add_argument(
        "--require", action="store_true", default=False,
        help=(
            "Exit 2 with a BLOCKED message when zero handoffs are found. "
            "Used by Phase 0.4 to enforce the research/discover precondition. "
            "No override path exists."
        ),
    )
    sp.set_defaults(func=cmd_find_handoffs)

    # ----- Cross-phase -----------------------------------------------------

    sp = sub.add_parser(
        "summary", help="Emit phase-progress + counts dashboard JSON.",
    )
    sp.set_defaults(func=cmd_summary)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
