"""argparse parser + dispatch + main entry for research_helper.

build_parser composes the top-level + subparsers. _register_subcommands
attaches every cmd_* handler. main parses argv + dispatches.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from ._constants import (
    CONFIDENCE_VS_PRIMARY_ENUM,
    COMPLEXITY_ENUM,
    FRAMING_ENUM,
    MODE_ENUM,
    RUBRIC_DIMENSIONS,
    RUBRIC_STATE_ENUM,
)
from ._cmds_basic import (
    cmd_preflight,
    cmd_read_memo,
    cmd_read_report,
    cmd_reset_memo,
    cmd_reset_report,
    cmd_set_date,
    cmd_set_topic,
    cmd_set_verbatim_prompt,
    cmd_summary,
)
from ._cmds_phase0 import (
    _make_dim_setter,
    _make_scope_setter,
    cmd_check_conflicts,
    cmd_detect_mode,
    cmd_record_conflict_resolution,
    cmd_record_gap,
    cmd_symptom_coverage,
    cmd_symptom_finalize,
)
from ._cmds_phase1 import (
    cmd_record_contributing_factor,
    cmd_record_finding,
    cmd_record_hypothesis,
    cmd_record_runner_up_framing,
    cmd_set_confidence,
    cmd_set_root_cause_hypothesis,
    cmd_set_root_cause_systemic,
    cmd_set_trigger,
    cmd_set_verify_step,
)
from ._cmds_approach import cmd_set_approach, cmd_set_recommended_approach
from ._cmds_phase2 import (
    cmd_set_complexity,
    cmd_set_constitution_constraints,
    cmd_set_next_step_text,
    cmd_set_summary,
    cmd_set_verdict,
)
from ._cmds_dataflow import (
    cmd_record_consumer_chain,
    cmd_record_data_flow_chain,
    cmd_record_dead_sibling,
    cmd_record_fix_path_helper,
    cmd_record_inbound_caller,
    cmd_record_literal_archaeology,
    cmd_record_probe_script,
    cmd_record_value_production_site,
    cmd_set_value_semantics,
)
from ._cmds_render_verify import cmd_render, cmd_verify, cmd_verify_hypothesis_suppression
from ._cmds_intake import (
    INTAKE_KIND_ENUM,
    cmd_record_intake_classification,
    cmd_render_intake_echo,
)
from ._cmds_handoff import (
    cmd_append_outcome,
    cmd_check_outcome,
    cmd_finalize_handoff,
    cmd_set_probe_feasibility,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="research_helper",
        description="State + render helper for /research. Owns research artifact shape.",
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
    """All cmd_* handlers attached here. Implemented in sibling modules."""
    # Plumbing
    sp = subparsers.add_parser("reset-memo", help="Write a fresh defaults memo state.")
    sp.set_defaults(func=cmd_reset_memo)

    sp = subparsers.add_parser("reset-report", help="Write a fresh defaults report state.")
    sp.set_defaults(func=cmd_reset_report)

    sp = subparsers.add_parser("read-memo", help="Print research-state.json (or defaults) as JSON.")
    sp.set_defaults(func=cmd_read_memo)

    sp = subparsers.add_parser("read-report", help="Print research-report.json (or defaults) as JSON.")
    sp.set_defaults(func=cmd_read_report)

    sp = subparsers.add_parser(
        "preflight",
        help="Hard-gate check: 4 setup-chain artefacts present + non-empty.",
    )
    sp.set_defaults(func=cmd_preflight)

    sp = subparsers.add_parser(
        "set-topic",
        help="Set report.topic + auto-derive memo.topic_slug.",
    )
    sp.add_argument("--value", required=True, help="Topic text (user's original input).")
    sp.set_defaults(func=cmd_set_topic)

    sp = subparsers.add_parser(
        "set-verbatim-prompt",
        help=(
            "Persist the full raw prompt text to memo.verbatim_prompt. "
            "Called at Phase 0.3 right after set-topic, before the rubric. "
            "Distinct from set-topic: carries the full $ARGUMENTS including any "
            "'Suspected cause:' tail or other context the one-sentence topic loses."
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
        help="Set report.date (YYYY-MM-DD).",
    )
    sp.add_argument("--value", required=True, help="Date in YYYY-MM-DD format.")
    sp.set_defaults(func=cmd_set_date)

    sp = subparsers.add_parser(
        "summary",
        help="Render combined memo + report summary to stdout. Read-only.",
    )
    sp.set_defaults(func=cmd_summary)

    # Phase 0 setters — 5 non-scope dims built uniformly in the loop;
    # scope built separately below with the evidence gate.
    for dim in RUBRIC_DIMENSIONS:
        if dim == "scope":
            continue
        sp_name = "set-" + dim.replace("_", "-")
        sp = subparsers.add_parser(sp_name, help="Set {0} dimension.".format(dim))
        sp.add_argument("--value", required=True, help="Value text (verbatim).")
        sp.add_argument(
            "--state",
            default="Clear",
            choices=list(RUBRIC_STATE_ENUM),
            help="State after this set (default: Clear).",
        )
        sp.add_argument(
            "--increment-turn",
            action="store_true",
            help="Increment turn counter (use for follow-ups that didn't fully clear).",
        )
        sp.set_defaults(func=_make_dim_setter(dim))

    # Scope setter — special-cased to add --evidence gate for "one place".
    sp = subparsers.add_parser(
        "set-scope",
        help=(
            "Set scope dimension. "
            "--evidence is required when --value normalizes to 'one place'."
        ),
    )
    sp.add_argument("--value", required=True, help="Value text (verbatim).")
    sp.add_argument(
        "--state",
        default="Clear",
        choices=list(RUBRIC_STATE_ENUM),
        help="State after this set (default: Clear).",
    )
    sp.add_argument(
        "--increment-turn",
        action="store_true",
        help="Increment turn counter (use for follow-ups that didn't fully clear).",
    )
    sp.add_argument(
        "--evidence",
        default=None,
        help=(
            "file:line citation proving the bug is localized. "
            "Required when --value normalizes to 'one place'; ignored otherwise."
        ),
    )
    sp.set_defaults(func=_make_scope_setter())

    sp = subparsers.add_parser(
        "detect-mode",
        help="Detect bug vs enhancement from symptom tokens, optionally with --override.",
    )
    sp.add_argument("--override", default=None, choices=list(MODE_ENUM), help="Force a mode.")
    sp.set_defaults(func=cmd_detect_mode)

    sp = subparsers.add_parser(
        "finalize-handoff",
        help="Emit handoff.json from research state (terminal phase).",
    )
    sp.add_argument("--emit-handoff-json", required=True, dest="emit_handoff_json")
    sp.add_argument("--research-md-path", default=None, dest="research_md_path")
    sp.set_defaults(func=cmd_finalize_handoff)

    sp = subparsers.add_parser(
        "set-probe-feasibility",
        help="Record probe-feasibility flags (5 booleans) before finalize-handoff.",
    )
    for _flag in (
        "--data-shape-only",
        "--auth-required",
        "--network-dependent",
        "--timing-dependent",
        "--is-test-code",
    ):
        sp.add_argument(_flag, required=True, choices=("true", "false"))
    sp.set_defaults(func=cmd_set_probe_feasibility)

    sp = subparsers.add_parser(
        "record-gap",
        help="Record a [NEEDS CLARIFICATION] gap for a dimension and accept exit.",
    )
    sp.add_argument("--dimension", required=True, choices=list(RUBRIC_DIMENSIONS))
    sp.add_argument("--description", required=True, help="Gap description.")
    sp.set_defaults(func=cmd_record_gap)

    sp = subparsers.add_parser(
        "check-conflicts",
        help="Scan dimensions for direct contradictions; emit JSON list.",
    )
    sp.set_defaults(func=cmd_check_conflicts)

    sp = subparsers.add_parser(
        "record-conflict-resolution",
        help="Log user resolution for a previously detected conflict.",
    )
    sp.add_argument("--index", required=True, type=int, help="0-based index into conflicts list.")
    sp.add_argument("--resolution", required=True, help="Resolution label.")
    sp.add_argument(
        "--rewrite-dimension",
        default=None,
        choices=list(RUBRIC_DIMENSIONS),
        help="Optional dimension whose value to clear (loser of direct conflict).",
    )
    sp.set_defaults(func=cmd_record_conflict_resolution)

    sp = subparsers.add_parser(
        "symptom-coverage",
        help="Emit JSON coverage map per dimension + counts.",
    )
    sp.set_defaults(func=cmd_symptom_coverage)

    sp = subparsers.add_parser(
        "symptom-finalize",
        help=(
            "Validate memo: all Clear OR override_recorded; no blocked conflicts. "
            "Exit 0 = ready for Phase 1; non-zero otherwise."
        ),
    )
    sp.add_argument(
        "--accept-gaps",
        action="store_true",
        help="User explicitly accepted Partial/Missing dimensions; record override.",
    )
    sp.set_defaults(func=cmd_symptom_finalize)

    # Phase 1 setters
    sp = subparsers.add_parser(
        "record-finding",
        help="Append a {surface, file_line, relevance, framing} Finding to report.findings.",
    )
    sp.add_argument("--surface", required=True)
    sp.add_argument("--file-line", required=True, dest="file_line")
    sp.add_argument("--relevance", required=True)
    sp.add_argument(
        "--framing",
        default="primary",
        choices=list(FRAMING_ENUM),
        dest="framing",
        help="Which framing this finding supports (default: primary).",
    )
    sp.set_defaults(func=cmd_record_finding)

    sp = subparsers.add_parser(
        "record-runner-up-framing",
        help=(
            "Set report.runner_up_framing {frame, falsifier, confidence_vs_primary}. "
            "Overwrites any prior value (last call wins). "
            "Required before Phase 2.4 searches start."
        ),
    )
    sp.add_argument("--frame", required=True, dest="frame",
                    help="One-sentence alternative root cause.")
    sp.add_argument("--falsifier", required=True, dest="falsifier",
                    help="Concrete evidence that would confirm this framing over the primary.")
    sp.add_argument(
        "--confidence-vs-primary",
        required=True,
        dest="confidence_vs_primary",
        choices=list(CONFIDENCE_VS_PRIMARY_ENUM),
        help="Confidence of runner-up vs primary: lower|comparable|higher.",
    )
    sp.set_defaults(func=cmd_record_runner_up_framing)

    sp = subparsers.add_parser(
        "record-hypothesis",
        help="Append a {cause, falsifier, runtime_probe_needed} Hypothesis to report.hypotheses.",
    )
    sp.add_argument("--cause", required=True)
    sp.add_argument("--falsifier", required=True)
    sp.add_argument(
        "--runtime-probe-needed",
        choices=("yes", "no"),
        required=True,
        dest="runtime_probe_needed",
    )
    sp.set_defaults(func=cmd_record_hypothesis)

    sp = subparsers.add_parser(
        "set-root-cause-hypothesis",
        help="Set primary root-cause-hypothesis text on report.",
    )
    sp.add_argument("--value", required=True)
    sp.set_defaults(func=cmd_set_root_cause_hypothesis)

    sp = subparsers.add_parser(
        "set-confidence",
        help="Set confidence enum (Confirmed | Hypothesis | Speculative).",
    )
    sp.add_argument("--value", required=True)
    sp.set_defaults(func=cmd_set_confidence)

    sp = subparsers.add_parser(
        "set-trigger",
        help="Set structured-root-cause trigger (bug-mode + confidence ≥ Hypothesis only).",
    )
    sp.add_argument("--value", required=True)
    sp.set_defaults(func=cmd_set_trigger)

    sp = subparsers.add_parser(
        "set-root-cause-systemic",
        help="Set structured-root-cause systemic flaw (bug-mode + confidence ≥ Hypothesis only).",
    )
    sp.add_argument("--value", required=True)
    sp.set_defaults(func=cmd_set_root_cause_systemic)

    sp = subparsers.add_parser(
        "record-contributing-factor",
        help="Append a contributing factor (bug-mode + confidence ≥ Hypothesis; max 3).",
    )
    sp.add_argument("--value", required=True)
    sp.set_defaults(func=cmd_record_contributing_factor)

    sp = subparsers.add_parser(
        "set-verify-step",
        help="Set verify-step 3 sub-fields (probe + reproduction + discriminator).",
    )
    sp.add_argument("--probe", required=True)
    sp.add_argument("--reproduction", required=True)
    sp.add_argument("--discriminator", required=True)
    sp.set_defaults(func=cmd_set_verify_step)

    # Phase 2 setters
    sp = subparsers.add_parser(
        "set-approach",
        help="Append an Approach to report.approaches.",
    )
    sp.add_argument("--name", required=True)
    sp.add_argument("--description", required=True)
    sp.add_argument(
        "--addresses-hypotheses",
        required=True,
        dest="addresses",
        help='JSON array of hypothesis-index strings (e.g. ["A","B"]).',
    )
    sp.add_argument(
        "--does-not-cover",
        required=True,
        dest="does_not_cover",
        help='JSON array of hypothesis-index strings.',
    )
    sp.add_argument("--pros", required=True, help='JSON array of pros strings.')
    sp.add_argument("--cons", required=True, help='JSON array of cons strings.')
    sp.add_argument("--complexity", required=True, choices=list(COMPLEXITY_ENUM))
    sp.set_defaults(func=cmd_set_approach)

    sp = subparsers.add_parser(
        "set-recommended-approach",
        help="Set recommended approach. Must cite hypotheses + respect unchanged_behavior.",
    )
    sp.add_argument("--name", required=True, help="Must match an existing approach.name.")
    sp.add_argument("--rationale", required=True)
    sp.add_argument(
        "--hypotheses-addressed",
        required=True,
        dest="hypotheses_addressed",
        help="JSON array of hypothesis-index strings.",
    )
    sp.add_argument(
        "--hypotheses-not-covered",
        required=True,
        dest="hypotheses_not_covered",
        help="JSON array of hypothesis-index strings.",
    )
    sp.add_argument(
        "--single-layer-justification",
        default=None,
        dest="single_layer_justification",
        help=(
            "Prose justification for a single-layer recommendation. Required when all "
            "fix_path_helpers resolve to the same package (single-layer detection) "
            "AND the symptom is NOT a presentation-layer file. "
            "Path is only available for non-presentation-layer symptoms; "
            "presentation-layer symptoms must trace through a package boundary (see check 8b). "
            "Must be accompanied by --cites citing recorded evidence rows."
        ),
    )
    sp.add_argument(
        "--cites",
        default=None,
        dest="cites",
        help=(
            "JSON array of cite tokens (consumer_chain.consumer_qn, value_semantics.value, "
            "value_semantics.evidence, or dead_siblings.method_qn) proving the symptom is "
            "layer-local. Required when --single-layer-justification is provided."
        ),
    )
    sp.add_argument(
        "--proposed-call-shape",
        default=None,
        dest="proposed_call_shape",
        help=(
            "Exact post-fix call as it would appear at the bug site. "
            "REQUIRED when bug mode AND (--single-layer-justification is set "
            "OR --rationale contains literal-replacement prose). Helper checks "
            "for argument duplication (same identifier appearing >1 time) — "
            "duplication signals the default-source belongs at a different layer "
            "(wrapper signature / state-init / use-case default) and rejects."
        ),
    )
    sp.set_defaults(func=cmd_set_recommended_approach)

    sp = subparsers.add_parser(
        "set-constitution-constraints",
        help="Append (rule, impact) record to constitution_constraints.",
    )
    sp.add_argument("--rule", required=True)
    sp.add_argument("--impact", required=True)
    sp.set_defaults(func=cmd_set_constitution_constraints)

    sp = subparsers.add_parser(
        "set-complexity",
        help="Set complexity sub-fields (codebase_changes + risk + verify_cost).",
    )
    sp.add_argument("--codebase-changes", required=True, dest="codebase_changes",
                    choices=list(COMPLEXITY_ENUM))
    sp.add_argument("--codebase-notes", required=True, dest="codebase_notes")
    sp.add_argument("--risk", required=True, choices=list(COMPLEXITY_ENUM))
    sp.add_argument("--risk-notes", required=True, dest="risk_notes")
    sp.add_argument("--verify-cost", required=True, dest="verify_cost",
                    choices=list(COMPLEXITY_ENUM))
    sp.add_argument("--verify-notes", required=True, dest="verify_notes")
    sp.set_defaults(func=cmd_set_complexity)

    sp = subparsers.add_parser(
        "set-verdict",
        help="Set verdict (mode-aware enum). Rejects values outside mode's allowed set.",
    )
    sp.add_argument("--value", required=True)
    sp.set_defaults(func=cmd_set_verdict)

    sp = subparsers.add_parser(
        "set-summary",
        help="Set summary (3-5 sentence opener).",
    )
    sp.add_argument("--value", required=True)
    sp.set_defaults(func=cmd_set_summary)

    sp = subparsers.add_parser(
        "set-next-step-text",
        help="Compose next-step text from memo + report; only when verdict proceeds.",
    )
    sp.set_defaults(func=cmd_set_next_step_text)

    sp = subparsers.add_parser(
        "render",
        help="Walk schema + state; emit research report md to stdout.",
    )
    sp.set_defaults(func=cmd_render)

    sp = subparsers.add_parser(
        "verify",
        help="Cross-check report state for required invariants. Exit 0 pass / 2 violations.",
    )
    sp.set_defaults(func=cmd_verify)

    sp = subparsers.add_parser(
        "verify-hypothesis-suppression",
        help=(
            "Gate: exit 2 when any unverified hypothesis cause overlaps the "
            "recommended-approach rationale (MEDIUM/LOW probe tier or unresolved "
            "feasibility discriminator). Exit 0 when clean or tier is HIGH."
        ),
    )
    sp.set_defaults(func=cmd_verify_hypothesis_suppression)

    # Phase 2.4c setters
    sp = subparsers.add_parser(
        "record-fix-path-helper",
        help="Append a {qn, file_line} helper entry to fix_path_helpers (deduped on qn).",
    )
    sp.add_argument("--helper-qn", required=True, dest="helper_qn")
    sp.add_argument(
        "--file-line",
        required=True,
        dest="file_line",
        help=(
            "Helper definition location as file:line (from search_graph result). "
            "Must be a real path — sentinel '(none)' is rejected here because "
            "the file_line is used for package extraction in check 8b."
        ),
    )
    sp.set_defaults(func=cmd_record_fix_path_helper)

    sp = subparsers.add_parser(
        "record-inbound-caller",
        help="Append a {helper_qn, caller_qn, file_line} record to inbound_callers.",
    )
    sp.add_argument("--helper-qn", required=True, dest="helper_qn")
    sp.add_argument("--caller-qn", required=True, dest="caller_qn")
    sp.add_argument("--file-line", required=True, dest="file_line")
    sp.set_defaults(func=cmd_record_inbound_caller)

    sp = subparsers.add_parser(
        "record-dead-sibling",
        help="Append a {class_qn, method_qn, verified_via} record to dead_siblings.",
    )
    sp.add_argument("--class-qn", required=True, dest="class_qn")
    sp.add_argument("--method-qn", required=True, dest="method_qn")
    sp.add_argument(
        "--verified-via",
        required=True,
        dest="verified_via",
        choices=("trace_path", "search_code"),
    )
    sp.set_defaults(func=cmd_record_dead_sibling)

    sp = subparsers.add_parser(
        "record-consumer-chain",
        help="Append a {value, consumer_qn, file_line, role} record to consumer_chain.",
    )
    sp.add_argument("--value", required=True)
    sp.add_argument("--consumer-qn", required=True, dest="consumer_qn")
    sp.add_argument("--file-line", required=True, dest="file_line")
    sp.add_argument("--role", required=True)
    sp.set_defaults(func=cmd_record_consumer_chain)

    sp = subparsers.add_parser(
        "set-value-semantics",
        help="Upsert a {value, classification, evidence} record in value_semantics.",
    )
    sp.add_argument("--value", required=True)
    sp.add_argument(
        "--classification",
        required=True,
        choices=("preference", "invariant", "unclassified"),
    )
    sp.add_argument("--evidence", required=True)
    sp.add_argument(
        "--stable-across-calls",
        default=None,
        choices=("true", "false", "unknown"),
        dest="stable_across_calls",
        help=(
            "Stability axis for the value across the operation chain. "
            "REQUIRED when --classification invariant. "
            "Optional for other classifications (ignored if set)."
        ),
    )
    sp.set_defaults(func=cmd_set_value_semantics)

    sp = subparsers.add_parser(
        "record-value-production-site",
        help=(
            "Append a {value, file_line, is_stable} record to value_production_sites. "
            "Dedupes by (value, file_line) pair; multiple file_lines per value allowed."
        ),
    )
    sp.add_argument("--value", required=True, help="Symbol whose production site is being recorded.")
    sp.add_argument(
        "--file-line",
        required=True,
        dest="file_line",
        help="path:line where the value is randomized/rewritten (must not be (none)).",
    )
    sp.add_argument(
        "--is-stable",
        required=True,
        dest="is_stable",
        choices=("true", "false"),
        help="Whether the value is stable at this production site.",
    )
    sp.set_defaults(func=cmd_record_value_production_site)

    sp = subparsers.add_parser(
        "record-data-flow-chain",
        help=(
            "Record the data-flow chain from click handler to write-boundary call. "
            "Each intermediate must have a prior Finding row referencing it."
        ),
    )
    sp.add_argument(
        "--handler-qn",
        required=True,
        dest="handler_qn",
        help="Qualified name of the user-action handler (entry point).",
    )
    sp.add_argument(
        "--write-boundary-qn",
        required=True,
        dest="write_boundary_qn",
        help="Qualified name of the persistence / write-boundary call.",
    )
    sp.add_argument(
        "--intermediate-qns",
        required=True,
        dest="intermediate_qns",
        help=(
            "JSON array of intermediate transformer/adapter QNs between handler and "
            "write-boundary. May be empty list '[]' for direct handler→boundary calls."
        ),
    )
    sp.set_defaults(func=cmd_record_data_flow_chain)

    sp = subparsers.add_parser(
        "record-literal-archaeology",
        help=(
            "Record git-archaeology of a hardcoded literal that the recommended approach "
            "proposes to replace. Dedupes by (literal, file_line)."
        ),
    )
    sp.add_argument("--literal", required=True, help="Literal token as it appears in source (e.g. 'false', '0', \"''\").")
    sp.add_argument(
        "--file-line",
        required=True,
        dest="file_line",
        help="path:line where the literal lives (must not be (none)).",
    )
    sp.add_argument(
        "--introduced-by",
        required=True,
        dest="introduced_by",
        help="Commit SHA (7-40 hex chars) of the commit that introduced the literal.",
    )
    sp.add_argument(
        "--introduced-when",
        required=True,
        dest="introduced_when",
        help="ISO date YYYY-MM-DD when the introducing commit landed.",
    )
    sp.add_argument(
        "--commit-subject",
        required=True,
        dest="commit_subject",
        help="One-line subject from the introducing commit.",
    )
    sp.add_argument(
        "--intent",
        required=True,
        choices=("placeholder", "migrated", "deliberate", "forgotten", "inherited-refactor", "generated"),
        help="Classification of the literal's historical intent.",
    )
    sp.set_defaults(func=cmd_record_literal_archaeology)

    sp = subparsers.add_parser(
        "record-probe-script",
        help="Record a Tier-1.5 standalone probe script path + runtime + inlined-from sources.",
    )
    sp.add_argument("--script-path", required=True, dest="script_path")
    sp.add_argument(
        "--runtime",
        required=True,
        choices=("node", "python", "ruby", "deno", "bun"),
    )
    sp.add_argument(
        "--inlines-from",
        required=True,
        dest="inlines_from",
        help='JSON array of "path:line" tokens whose code the script inlines verbatim.',
    )
    sp.set_defaults(func=cmd_record_probe_script)

    # Step 5 — intake-interrogation gate.
    sp = subparsers.add_parser(
        "record-intake-classification",
        help=(
            "Persist a per-statement binary intake classification "
            "(requirement vs hypothesis) + the minimal_fix for that statement. "
            "Called once per statement in the verbatim prompt. "
            "Re-recording the same statement replaces its entry (idempotent)."
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
        help="Binary classification: 'requirement' or 'hypothesis'.",
    )
    sp.add_argument(
        "--minimal-fix",
        default=None,
        dest="minimal_fix",
        help=(
            "The simplest change that satisfies this statement's desired outcome. "
            "Optional; pass for requirement statements. For hypothesis statements "
            "the fix is 'verify first', not a code change."
        ),
    )
    sp.set_defaults(func=cmd_record_intake_classification)

    sp = subparsers.add_parser(
        "render-intake-echo",
        help=(
            "Render the intake echo-back block (requirements / hypotheses-to-verify / "
            "minimal scope) to stdout. Orchestrator copies verbatim to user before "
            "one confirmation. Proportional: no hypothesis section when none recorded."
        ),
    )
    sp.set_defaults(func=cmd_render_intake_echo)

    # Step 7 — append-outcome.
    sp = subparsers.add_parser(
        "append-outcome",
        help="Record the post-probe outcome into handoff.json (Step 7).",
    )
    sp.add_argument("--handoff-path", required=True, dest="handoff_path",
                    help="Path to the handoff.json file (e.g. research/<NNN>/handoff.json).")
    sp.add_argument(
        "--hypothesis-confirmed",
        required=True,
        dest="hypothesis_confirmed",
        choices=("primary", "runner_up", "none", "inconclusive"),
        help="Which hypothesis the evidence confirmed.",
    )
    sp.add_argument(
        "--evidence-source",
        required=True,
        dest="evidence_source",
        choices=("test-result", "llm-ui-session-log", "user-observation"),
        help="Source of the evidence.",
    )
    sp.add_argument("--evidence-cite", required=True, dest="evidence_cite",
                    help="Path, SHA, or verbatim observation that evidences the outcome.")
    sp.add_argument("--actual-fix-path", required=True, dest="actual_fix_path",
                    help="Path(s) actually modified by the fix.")
    sp.add_argument("--delta-from-recommendation", default=None, dest="delta_from_recommendation",
                    help="Optional: how the actual fix diverged from the recommendation.")
    sp.add_argument("--confirmed-commit-sha", default=None, dest="confirmed_commit_sha",
                    help="Optional: 7-40 char hex SHA of the commit that applied the fix.")
    sp.set_defaults(func=cmd_append_outcome)

    # Step 7 — check-outcome.
    sp = subparsers.add_parser(
        "check-outcome",
        help="Print 'unmarked' or 'marked: <details>' for a handoff.json outcome block.",
    )
    sp.add_argument("--handoff-path", required=True, dest="handoff_path",
                    help="Path to the handoff.json file.")
    sp.set_defaults(func=cmd_check_outcome)


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "func", None) is None:
        parser.print_help(sys.stderr)
        return 2
    if args.install_root is None:
        args.install_root = str(Path(args.devforge_dir).resolve().parent)
    return args.func(args)
