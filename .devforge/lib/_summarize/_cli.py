"""argparse parser + dispatch + main entry for summarize_helper.

build_parser composes the top-level + subparsers.
_register_subcommands attaches each cmd_* handler via set_defaults(func=...).
main parses argv + dispatches (prints help + returns 2 when no subcommand).

Phase 1 (scaffold) ships 1 verb:
  preflight  — gate on 4-command setup chain + spec **Status**: Complete check
               + source_root / wrapper_mode resolution from CLAUDE.md

Phase 2 ships input / gather verbs:
  gather-change-data      — assembled scope (via _shared) + git diff --stat totals
  read-verification       — parse verification.md AC table + verdict
  parse-completion-notes  — parse task ## Completion Notes into structured data
  read-plan-decisions     — read plan.md key-decisions section (D9: plan.md, NOT plan-handoff.json)

Extension point for later phases: append to _SUBCOMMAND_REGISTRY and add
the corresponding argument block in _register_subcommands's elif chain.
"""

from __future__ import annotations

import argparse
import json
import sys

from ._changes import cmd_gather_change_data  # noqa: E402
from ._inputs import (  # noqa: E402
    cmd_read_verification,
    cmd_parse_completion_notes,
    cmd_read_plan_decisions,
)


# ---------------------------------------------------------------------------
# Phase 1 handler: preflight
# ---------------------------------------------------------------------------


def cmd_preflight(args):
    # type: (argparse.Namespace) -> int
    """Check setup-chain artefacts, spec Complete gate, Source-Root.

    Always emits JSON to stdout before any non-zero exit so the orchestrator
    can read context from the scratch chain even on failure.

    Exit codes:
      0 — all checks pass (setup chain ok, spec is Complete)
      2 — missing setup-chain artefact (user-facing message to stderr)
      3 — spec not Complete or spec absent (user-facing "run /verify first")
    """
    from ._preflight import preflight_context

    workspace_root = getattr(args, "workspace_root", ".") or "."
    # spec_arg is used as both a presence-sentinel ("was --spec provided?") and
    # as the display value in the error message.  The `or None` coercion turns
    # an empty-string default into None so the sentinel check is a clean `if`.
    spec_arg = getattr(args, "spec", None) or None

    result = preflight_context(workspace_root, spec_path=spec_arg)

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")

    # Gate 1: missing setup-chain artefacts → exit 2.
    # constitution.md is artefact #1, so its absence is already caught here.
    if not result["setup_chain_ok"]:
        missing = result.get("missing_artefacts", [])
        sys.stderr.write(
            "summarize_helper preflight: setup chain incomplete. "
            "Run the 4-command setup sequence first:\n"
            "  /init-forge -> /generate-docs -> /configure -> /constitute\n"
            "Missing: {0}\n".format(", ".join(missing))
        )
        return 2

    # Gate 2: spec must be Complete (set by /verify on APPROVED verdict).
    # /summarize runs AFTER /verify — the spec **Status**: Complete is the
    # pipeline precondition.  A non-Complete spec means /verify has not yet
    # approved this feature.
    if spec_arg and not result["spec_complete"]:
        status = result.get("spec_status") or "(not found)"
        sys.stderr.write(
            "summarize_helper preflight: spec is not Complete "
            "(current status: {0}). "
            "Run `/verify` first to approve the feature before summarizing.\n".format(
                status
            )
        )
        return 3

    return 0


# ---------------------------------------------------------------------------
# Registry + parser construction
# ---------------------------------------------------------------------------

# _SUBCOMMAND_REGISTRY is the extension point for new verbs.
# Each entry is a (verb_name, help_text, handler_function) triple.
# To add a Phase-2+ verb:
#   1. Write the cmd_<verb> function above.
#   2. Append (kebab-name, help, cmd_func) to this list.
#   3. Add the argument block for the verb in the elif chain in
#      _register_subcommands below.
_SUBCOMMAND_REGISTRY = [
    (
        "preflight",
        (
            "Gate on 4-command setup chain + spec **Status**: Complete check "
            "+ source_root/wrapper_mode resolution from CLAUDE.md (Phase 1)."
        ),
        cmd_preflight,
    ),
    (
        "gather-change-data",
        (
            "Assemble changed-file list + scope_block via _shared.feature_scope "
            "(heading_label='Summary Scope') + git diff --stat +/- totals + "
            "group-by-directory. Wrapper-mode: also gathers source-repo changes "
            "via git -C <source_root>. (Phase 2)."
        ),
        cmd_gather_change_data,
    ),
    (
        "read-verification",
        (
            "Parse verification.md's ## Acceptance Criteria table (per-AC status "
            "+ evidence) and the ## Verdict value. The AC status is AUTHORITATIVE "
            "(D3) — /summarize does not re-derive ACs from the spec. (Phase 2)."
        ),
        cmd_read_verification,
    ),
    (
        "parse-completion-notes",
        (
            "Parse one or more task files' ## Completion Notes sections "
            "(filled by implement_helper mark-complete) into structured data: "
            "completed_at, files_changed, expects_met, produces_met, notes, "
            "has_unverified. (Phase 2)."
        ),
        cmd_parse_completion_notes,
    ),
    (
        "read-plan-decisions",
        (
            "Parse plan.md's key-decisions section (D9: reads plan.md, NOT "
            "plan-handoff.json). Supports '### Key Design Decisions' "
            "(current template, triple-hash) and '## Architecture Decisions' "
            "(older plans). Emits a normalized list of decisions. (Phase 2)."
        ),
        cmd_read_plan_decisions,
    ),
]


def build_parser():
    # type: () -> argparse.ArgumentParser
    """Build and return the top-level ArgumentParser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="summarize_helper",
        description=(
            "Helper for /summarize — the per-feature PR-ready narrative synthesis. "
            "Reads spec + plan + task completion notes + git + verification.md, "
            "and orchestrates the inline composition of specs/[feature]/summary.md. "
            "Agent-free (no finder ensemble, no refutation, no verdict)."
        ),
    )

    subparsers = parser.add_subparsers(dest="subcommand")
    _register_subcommands(subparsers)
    return parser


def _register_subcommands(subparsers):
    # type: (argparse._SubParsersAction) -> None
    """Attach all handlers from _SUBCOMMAND_REGISTRY."""
    for verb, help_text, handler in _SUBCOMMAND_REGISTRY:
        sp = subparsers.add_parser(verb, help=help_text)

        if verb == "preflight":
            sp.add_argument(
                "--workspace-root",
                default=".",
                dest="workspace_root",
                metavar="DIR",
                help=(
                    "Workspace root to check for setup-chain artefacts. "
                    "In wrapper mode this is the wrapper root (not the project "
                    "sub-directory). Default: CWD."
                ),
            )
            sp.add_argument(
                "--spec",
                default=None,
                dest="spec",
                metavar="PATH",
                help=(
                    "Path to the feature spec.md to check for **Status**: Complete. "
                    "When omitted, the spec gate is skipped (only setup chain is "
                    "checked). The orchestrator resolves the most-recent feature "
                    "spec path and passes it here."
                ),
            )

        elif verb == "gather-change-data":
            sp.add_argument(
                "--feature-dir",
                required=True,
                dest="feature_dir",
                metavar="DIR",
                help="Path to the specs/NNN-<name>/ feature directory.",
            )
            sp.add_argument(
                "--source-root",
                default=".",
                dest="source_root",
                metavar="DIR",
                help=(
                    "Absolute path to the source git repository. "
                    "In standalone mode this equals the workspace root. "
                    "Default: CWD."
                ),
            )
            sp.add_argument(
                "--install-root",
                default=None,
                dest="install_root",
                metavar="DIR",
                help=(
                    "Absolute path to the forge install root (where .devforge/ lives). "
                    "Required for wrapper-mode path prefixing. "
                    "When omitted, defaults to --source-root."
                ),
            )
            sp.add_argument(
                "--base",
                default=None,
                dest="base",
                metavar="REF",
                help=(
                    "Git ref for the branch the feature forked from (e.g. 'main'). "
                    "When omitted, auto-detected via the _shared resolver's precedence."
                ),
            )

        elif verb == "read-verification":
            sp.add_argument(
                "--path",
                required=True,
                dest="verification_path",
                metavar="PATH",
                help="Path to the verification.md file to parse.",
            )

        elif verb == "parse-completion-notes":
            sp.add_argument(
                "--task-file",
                action="append",
                required=True,
                dest="task_files",
                metavar="PATH",
                help=(
                    "Path to a task .md file whose ## Completion Notes section "
                    "to parse. Repeatable for multiple tasks."
                ),
            )

        elif verb == "read-plan-decisions":
            sp.add_argument(
                "--path",
                required=True,
                dest="plan_path",
                metavar="PATH",
                help="Path to plan.md to parse for key-decisions section.",
            )

        sp.set_defaults(func=handler)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv=None):
    # type: (list) -> int
    """Parse argv and dispatch to the selected subcommand handler.

    Returns the handler's exit code (0 = success, non-zero = error).
    When no subcommand is given, prints help and returns 2.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help(sys.stderr)
        return 2

    return args.func(args)
