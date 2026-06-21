"""argparse parser + dispatch + main entry for finalize_helper.

build_parser composes the top-level + subparsers.
_register_subcommands attaches each cmd_* handler via set_defaults(func=...).
main parses argv + dispatches (prints help + returns 2 when no subcommand).

Phase 1 (scaffold) ships 1 verb:
  preflight  — gate on 4-command setup chain + spec **Status**: Complete check
               + source_root / wrapper_mode resolution from CLAUDE.md
               + WIP/checkpoint detection (the "Nothing to finalize" no-op signal)

Phase 2 ships 3 read/compute verbs (NO git history mutation):
  gather-change-data  — assembled scope via _shared.feature_scope + merge-base
  resolve-squash-base — wrapper/install squash base + source-repo base
  check-pushed        — already-pushed guard (origin/<branch>..HEAD)

Extension point for later phases: append to _SUBCOMMAND_REGISTRY and add
the corresponding argument block in _register_subcommands's elif chain.

Phase 3 ships the git-mutating squash verb:
  squash              — git-mutating squash execution; gated by --confirm flag
"""

from __future__ import annotations

import argparse
import json
import sys


# ---------------------------------------------------------------------------
# Phase 1 handler: preflight
# ---------------------------------------------------------------------------


def cmd_gather_change_data(args):
    # type: (argparse.Namespace) -> int
    """Handle the gather-change-data verb.  Delegates to _changes module."""
    from ._changes import cmd_gather_change_data as _impl
    return _impl(args)


def cmd_resolve_squash_base(args):
    # type: (argparse.Namespace) -> int
    """Handle the resolve-squash-base verb.  Delegates to _squash module."""
    from ._squash import cmd_resolve_squash_base as _impl
    return _impl(args)


def cmd_check_pushed(args):
    # type: (argparse.Namespace) -> int
    """Handle the check-pushed verb.  Delegates to _squash module."""
    from ._squash import cmd_check_pushed as _impl
    return _impl(args)


def cmd_squash(args):
    # type: (argparse.Namespace) -> int
    """Handle the squash verb.  Delegates to _squash module."""
    from ._squash import cmd_squash as _impl
    return _impl(args)


def cmd_preflight(args):
    # type: (argparse.Namespace) -> int
    """Check setup-chain artefacts, spec Complete gate, Source-Root, WIP commits.

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
    base_ref = getattr(args, "base", None) or None

    result = preflight_context(workspace_root, spec_path=spec_arg, base_ref=base_ref)

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")

    # Gate 1: missing setup-chain artefacts → exit 2.
    # constitution.md is artefact #1, so its absence is already caught here.
    if not result["setup_chain_ok"]:
        missing = result.get("missing_artefacts", [])
        sys.stderr.write(
            "finalize_helper preflight: setup chain incomplete. "
            "Run the 4-command setup sequence first:\n"
            "  /init-forge -> /generate-docs -> /configure -> /constitute\n"
            "Missing: {0}\n".format(", ".join(missing))
        )
        return 2

    # Gate 2: spec must be Complete (set by /verify on APPROVED verdict).
    # /finalize runs AFTER /verify — the spec **Status**: Complete is the
    # pipeline precondition.  A non-Complete spec means /verify has not yet
    # approved this feature.
    if spec_arg and not result["spec_complete"]:
        status = result.get("spec_status") or "(not found)"
        sys.stderr.write(
            "finalize_helper preflight: spec is not Complete "
            "(current status: {0}). "
            "Run `/verify` first to approve the feature before finalizing.\n".format(
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
#   1. Write the cmd_<verb> function above (or import from its module).
#   2. Append (kebab-name, help, cmd_func) to this list.
#   3. Add the argument block for the verb in the elif chain in
#      _register_subcommands below.
_SUBCOMMAND_REGISTRY = [
    (
        "preflight",
        (
            "Gate on 4-command setup chain + spec **Status**: Complete check "
            "+ source_root/wrapper_mode resolution from CLAUDE.md "
            "+ WIP/checkpoint commit detection (no-op signal) (Phase 1)."
        ),
        cmd_preflight,
    ),
    (
        "gather-change-data",
        (
            "Assemble the feature-branch changed-file list + scope_block + merge_base "
            "via _shared.feature_scope (heading_label='Finalize Scope') for the "
            "tech-writer brief. Emits JSON to stdout (Phase 2)."
        ),
        cmd_gather_change_data,
    ),
    (
        "resolve-squash-base",
        (
            "Compute the squash base SHA for the install repo (merge-base on a feature "
            "branch; oldest [checkpoint] parent on DEFAULT_BRANCH) and, in wrapper mode, "
            "the source repo (merge-base scoped to source_root). Emits JSON to stdout. "
            "NO git history mutation (Phase 2)."
        ),
        cmd_resolve_squash_base,
    ),
    (
        "check-pushed",
        (
            "Report whether the current branch's commits have been pushed to "
            "origin/<branch>. Emits JSON to stdout. Safe-to-squash = NOT is_pushed. "
            "Handles no-remote / no-upstream gracefully (Phase 2)."
        ),
        cmd_check_pushed,
    ),
    (
        "squash",
        (
            "Squash WIP/checkpoint commits into one clean feature commit. "
            "Requires --confirm to execute; without it, emits a dry-run preview (no mutation). "
            "Guards: refuses if commits already pushed; no-op when nothing to squash. "
            "Install/wrapper repo: feat(<name>): <title> + COMMIT_ATTRIBUTION per config. "
            "Source repo (wrapper mode): [TICKET-ID] - Description, NO attribution (D5). "
            "Emits JSON to stdout (Phase 3)."
        ),
        cmd_squash,
    ),
]


def build_parser():
    # type: () -> argparse.ArgumentParser
    """Build and return the top-level ArgumentParser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="finalize_helper",
        description=(
            "Helper for /finalize — the terminal PR-prep step. "
            "Gates on setup chain + spec Complete, dispatches tech-writer for "
            "surgical docs/ updates, and squashes WIP/checkpoint commits into "
            "one clean feature commit. "
            "Stateless (no state file — gates on the spec **Status**: Complete flip)."
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

        if verb == "gather-change-data":
            sp.add_argument(
                "--feature-dir",
                default="",
                dest="feature_dir",
                metavar="DIR",
                help="Path to the specs/NNN-feature/ directory (for context in the scope block).",
            )
            sp.add_argument(
                "--source-root",
                default=".",
                dest="source_root",
                metavar="DIR",
                help="Absolute path to the source repo (where git runs). Default: CWD.",
            )
            sp.add_argument(
                "--install-root",
                default=None,
                dest="install_root",
                metavar="DIR",
                help=(
                    "Absolute path to the forge install root (.devforge/ lives here). "
                    "When omitted, defaults to source_root (standalone)."
                ),
            )
            sp.add_argument(
                "--base",
                default=None,
                dest="base",
                metavar="REF",
                help=(
                    "Base git ref for the diff (e.g. 'main'). "
                    "When omitted, auto-detected via origin/HEAD -> main -> develop -> master."
                ),
            )

        elif verb == "resolve-squash-base":
            sp.add_argument(
                "--install-root",
                default=".",
                dest="install_root",
                metavar="DIR",
                help="Path to the forge install/wrapper root. Default: CWD.",
            )
            sp.add_argument(
                "--source-root",
                default=None,
                dest="source_root",
                metavar="DIR",
                help=(
                    "Path to the source repo (wrapper mode). "
                    "When omitted, defaults to install_root (standalone)."
                ),
            )
            sp.add_argument(
                "--default-branch",
                default=None,
                dest="default_branch",
                metavar="REF",
                help=(
                    "Default/trunk branch name (e.g. 'main'). "
                    "When omitted, auto-detected via origin/HEAD -> main -> develop -> master."
                ),
            )

        elif verb == "check-pushed":
            sp.add_argument(
                "--repo-root",
                default=".",
                dest="repo_root",
                metavar="DIR",
                help="Path to the git repository root to check. Default: CWD.",
            )

        elif verb == "squash":
            sp.add_argument(
                "--install-root",
                default=".",
                dest="install_root",
                metavar="DIR",
                help="Path to the forge install/wrapper root. Default: CWD.",
            )
            sp.add_argument(
                "--source-root",
                default=None,
                dest="source_root",
                metavar="DIR",
                help=(
                    "Path to the source repo (wrapper mode). "
                    "When omitted, defaults to install_root (standalone)."
                ),
            )
            sp.add_argument(
                "--install-message",
                default="",
                dest="install_message",
                metavar="MSG",
                help=(
                    "Commit subject for the install/wrapper repo. "
                    "Convention: 'feat(<feature-name>): <spec title>'. "
                    "COMMIT_ATTRIBUTION is appended by the verb (per config). "
                    "Required when confirm is used."
                ),
            )
            sp.add_argument(
                "--source-message",
                default="",
                dest="source_message",
                metavar="MSG",
                help=(
                    "Commit message for the source repo (wrapper mode only). "
                    "Convention: '[TICKET-ID] - Description'. "
                    "Used AS-IS — no attribution is ever appended (D5)."
                ),
            )
            sp.add_argument(
                "--confirm",
                action="store_true",
                default=False,
                dest="confirm",
                help=(
                    "Execute the squash. Without this flag, emits a dry-run "
                    "preview JSON (confirmed=false) and mutates nothing. "
                    "REQUIRED to perform history mutation."
                ),
            )
            sp.add_argument(
                "--default-branch",
                default=None,
                dest="default_branch",
                metavar="REF",
                help=(
                    "Default/trunk branch name (e.g. 'main'). "
                    "When omitted, auto-detected via origin/HEAD -> main -> develop -> master."
                ),
            )

        elif verb == "preflight":
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
            sp.add_argument(
                "--base",
                default=None,
                dest="base",
                metavar="REF",
                help=(
                    "Base git ref for the WIP/checkpoint commit range "
                    "(e.g. 'main'). When omitted, auto-detected via "
                    "origin/HEAD -> main -> develop -> master precedence."
                ),
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
