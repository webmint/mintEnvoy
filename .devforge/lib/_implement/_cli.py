"""argparse parser + dispatch + main entry for implement_helper.

build_parser composes the top-level ArgumentParser + subparsers.
_register_subcommands attaches each cmd_* handler via set_defaults(func=...).
main parses argv + dispatches (prints help and returns 2 when no subcommand).

Phase 1 ships 0 verbs in the command surface (the substrate is a skeleton
supporting --help and subcommand dispatch).  Later phases add verbs by
appending to _SUBCOMMAND_REGISTRY.

Phase 2 adds: resolve-next-task, preflight
Phase 3 adds: capture-touched-files
Phase 4 adds: verify-touched
Phase 5 adds: review-loop-step
Phase 6 adds: run-forcing-functions-gate
Phase 7 adds: wip-commit
Phase 8 adds: mark-complete, update-session-state

Stdlib only. Python 3.8+.
"""

import argparse
import sys

from _implement._cmds_resolve import cmd_resolve_next_task, add_args_resolve_next_task  # type: ignore[import]
from _implement._cmds_preflight import cmd_preflight, add_args_preflight  # type: ignore[import]
from _implement._cmds_capture import cmd_capture_touched_files, add_args_capture_touched_files  # type: ignore[import]
from _implement._cmds_verify import cmd_verify_touched, add_args_verify_touched  # type: ignore[import]
from _implement._cmds_review_loop import cmd_review_loop_step, add_args_review_loop_step  # type: ignore[import]
from _implement._cmds_review_panel import cmd_merge_review_panel, add_args_merge_review_panel  # type: ignore[import]
from _implement._cmds_gate import cmd_run_forcing_functions_gate, add_args_run_forcing_functions_gate  # type: ignore[import]
from _implement._cmds_commit import cmd_wip_commit, add_args_wip_commit  # type: ignore[import]
from _implement._cmds_complete import cmd_mark_complete, add_args_mark_complete, cmd_mark_skipped, add_args_mark_skipped  # type: ignore[import]
from _implement._cmds_session import cmd_update_session_state, add_args_update_session_state  # type: ignore[import]


# ---------------------------------------------------------------------------
# Registry + parser construction
# ---------------------------------------------------------------------------

# Each entry: (verb_name, help_text, handler_function, arg_adder_or_None)
# arg_adder, if set, is called as arg_adder(subparser) to add arguments.
_SUBCOMMAND_REGISTRY = [
    # Phase 2 verbs.
    (
        "resolve-next-task",
        (
            "Scan specs/*/ for breakdown-handoff.json files and emit JSON "
            "describing the next runnable task (lowest-numbered feature, "
            "lowest dependency-ready incomplete task). "
            "Emits {state: task|all-complete|blocked}."
        ),
        cmd_resolve_next_task,
        add_args_resolve_next_task,
    ),
    (
        "preflight",
        (
            "Run pre-task checks: constitution populated, feature branch, "
            "no stale wip.md. Emits JSON {constitution_digest, memory_digest, "
            "head_sha, branch} on success. Exit 2 on any failure."
        ),
        cmd_preflight,
        add_args_preflight,
    ),
    # Phase 3 verbs.
    (
        "capture-touched-files",
        (
            "Capture files changed since the task-start checkpoint. "
            "Combines git diff --name-only <checkpoint-sha> (tracked changes) "
            "with git status --porcelain (new untracked files). "
            "Emits a JSON array of relative file paths to stdout."
        ),
        cmd_capture_touched_files,
        add_args_capture_touched_files,
    ),
    # Phase 4 verbs.
    (
        "verify-touched",
        (
            "Run scope-aware type-check + lint + build over touched files. "
            "Loads PACKAGE_STACKS from .devforge/project-config.json; "
            "longest-path-prefix matches each file to its package commands. "
            "Implements a self-repair counter (helper-owned cap=3): "
            "exit 0 on pass or self_repair; exit 2 on cap-reached failure."
        ),
        cmd_verify_touched,
        add_args_verify_touched,
    ),
    # Phase 5 verbs.
    (
        "review-loop-step",
        (
            "Parse the code-reviewer agent's markdown and emit JSON controlling "
            "the autonomous review loop: {clean, escalate, iteration, verdict}. "
            "Reads from --verdict-file <path> or stdin. "
            "clean=true for APPROVE; clean=false for REQUEST CHANGES or BLOCK. "
            "escalate=true when --iteration N >= REVIEW_LOOP_CAP (3). "
            "Exit 0 on success; exit 2 on parse error (no verdict line)."
        ),
        cmd_review_loop_step,
        add_args_review_loop_step,
    ),
    # Phase 5 (panel) verbs.
    (
        "merge-review-panel",
        (
            "Aggregate verdicts from all four per-task panel reviewers into a "
            "single control-flow signal: {clean, escalate, iteration, per_reviewer}. "
            "Takes --reviewer agent-name:path pairs (one per reviewer). "
            "clean=true only when ALL reviewers emit their clean token "
            "(APPROVE / ADEQUATE / PASS / MEETS TARGETS). "
            "escalate=true when --iteration N >= REVIEW_LOOP_CAP (3). "
            "Exit 0 on success; exit 2 on any parse error (stderr names the "
            "failing reviewer; no JSON emitted)."
        ),
        cmd_merge_review_panel,
        add_args_merge_review_panel,
    ),
    # Phase 6 verbs.
    (
        "run-forcing-functions-gate",
        (
            "Run each enabled forcing_functions rule from .devforge/constitute.json "
            "by invoking constitute_helper verify-<rule>. "
            "Aggregates per-rule exit codes + stdout JSON reports. "
            "Emits {gate, rules_run, rules_failed, reports, aggregate_exit}. "
            "Exit 0 if no enabled rule failed; exit 2 if any failed; "
            "exit 0 + empty rules_run if no rules are enabled."
        ),
        cmd_run_forcing_functions_gate,
        add_args_run_forcing_functions_gate,
    ),
    # Phase 7 verbs.
    (
        "wip-commit",
        (
            "Stage touched_files + task file + index ONLY (never git add -A), "
            "compose a commit message per wrapper/non-wrapper convention, "
            "commit, capture HEAD SHA, and clear wip.md. "
            "Wrapper mode: '[TICKET-ID] - <title> (Task NNN)'. "
            "Non-wrapper: '[WIP] task: <title> (Task NNN)'. "
            "Honors COMMIT_ATTRIBUTION from .devforge/project-config.json. "
            "Emits {committed, head_sha, message}."
        ),
        cmd_wip_commit,
        add_args_wip_commit,
    ),
    # Phase 8 verbs.
    (
        "mark-complete",
        (
            "Mark a task Complete in tasks/<NNN>.md: set **Status**: Complete, "
            "tick Done-When checkboxes, fill Completion Notes (Completed, "
            "Files changed, Contract, Notes). Update the matching Status cell "
            "in tasks/README.md. Emits {marked: true}."
        ),
        cmd_mark_complete,
        add_args_mark_complete,
    ),
    (
        "update-session-state",
        (
            "Fully overwrite .devforge/session-state.md (<=40 lines, sliding "
            "window: feature, N-of-M progress, last 3 task mods, last 3 decisions). "
            "Append one task-outcome line to .devforge/memory.md. "
            "Emits {updated: true}."
        ),
        cmd_update_session_state,
        add_args_update_session_state,
    ),
    (
        "mark-skipped",
        (
            "Mark a task Skipped in tasks/<NNN>.md: set **Status**: Skipped. "
            "Update the matching Status cell in tasks/README.md via region-aware "
            "_update_readme_row (same as mark-complete). Does NOT fill Completion "
            "Notes (skip ≠ complete) and does NOT touch git. "
            "Emits {marked_skipped: true}."
        ),
        cmd_mark_skipped,
        add_args_mark_skipped,
    ),
]


def build_parser():
    # type: () -> argparse.ArgumentParser
    """Build and return the top-level ArgumentParser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="implement_helper",
        description=(
            "Task execution helper for /implement. "
            "Drains a feature's breakdown tasks one at a time with per-task "
            "hard-gate approval before committing."
        ),
    )

    subparsers = parser.add_subparsers(dest="subcommand")
    _register_subcommands(subparsers)
    return parser


def _register_subcommands(subparsers):
    # type: (object) -> None
    """Attach all handlers from _SUBCOMMAND_REGISTRY."""
    for entry in _SUBCOMMAND_REGISTRY:
        verb, help_text, handler = entry[0], entry[1], entry[2]
        arg_adder = entry[3] if len(entry) > 3 else None

        sp = subparsers.add_parser(verb, help=help_text)
        sp.set_defaults(func=handler)

        if arg_adder is not None:
            arg_adder(sp)


def main(argv=None):
    # type: (object) -> int
    """Parse argv and dispatch to the selected subcommand handler.

    Returns
    -------
    int
        Exit code: 0 on success, 1 for I/O failure, 2 for usage error.
        When no subcommand is given, prints help to stdout and returns 2.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help(sys.stdout)
        return 2

    return args.func(args)
