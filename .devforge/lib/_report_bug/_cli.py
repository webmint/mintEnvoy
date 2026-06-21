"""argparse parser + dispatch + main entry for report_bug_helper.

build_parser composes the top-level + subparsers.
_register_subcommands attaches each cmd_* handler via set_defaults(func=...).
main parses argv + dispatches (prints help + returns 2 when no subcommand).

Mirrors _fix/_cli.py in structure — verb-registry pattern with
_SUBCOMMAND_REGISTRY of (verb_name, help_text, handler) triples.

Verbs:
  preflight   — resolve workspace via resolve_workspace (fail-soft); emit
                JSON {bugs_dir, root, is_wrapper} to stdout; exit 0.
  write-bug   — validate args, build one issue dict, call file_bugs() from
                _shared/bug_file.py, emit written paths as JSON array;
                exit 0 ok, exit 2 arg error, exit 1 I/O error.

Extension point: append to _SUBCOMMAND_REGISTRY and add the argument block
in the elif chain in _register_subcommands.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_VALID_SEVERITIES = ("Critical", "Warning", "Info")


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def cmd_preflight(args):
    # type: (argparse.Namespace) -> int
    """Resolve workspace and emit bugs/ directory context.

    Always emits JSON to stdout.  Returns 0 — this verb never fails;
    workspace resolution is fail-soft (standalone on any config error).
    bugs_dir = <install_root>/bugs (created on write, not on preflight).

    JSON shape:
      {
        "bugs_dir": "<absolute path>/bugs",
        "root":     "<absolute install_root>",
        "is_wrapper": bool
      }
    """
    # Resolve _implement._workspace lazily so import errors surface here.
    from _implement._workspace import resolve_workspace

    workspace_root = getattr(args, "workspace_root", ".") or "."

    ws = resolve_workspace(workspace_root)

    bugs_dir = str(ws.install_root / "bugs")

    result = {
        "bugs_dir": bugs_dir,
        "root": str(ws.install_root),
        "is_wrapper": ws.is_wrapper,
    }

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_write_bug(args):
    # type: (argparse.Namespace) -> int
    """Build one issue dict and write it via file_bugs().

    Argument errors (missing --date, bad --severity) → exit 2.
    I/O errors (cannot create bugs_dir, cannot write) → exit 1.
    Success → emit written paths as JSON array, exit 0.
    """
    from _shared.bug_file import file_bugs

    # --- Required argument validation -----------------------------------------
    bugs_dir = getattr(args, "bugs_dir", None) or ""
    if not bugs_dir:
        sys.stderr.write("report_bug_helper write-bug: --bugs-dir is required\n")
        return 2

    date = getattr(args, "date", None) or ""
    if not date:
        sys.stderr.write("report_bug_helper write-bug: --date is required (YYYY-MM-DD)\n")
        return 2

    description = getattr(args, "description", None) or ""
    if not description:
        sys.stderr.write("report_bug_helper write-bug: --description is required\n")
        return 2

    # --- Optional args with defaults ------------------------------------------
    title = getattr(args, "title", None) or description
    severity = getattr(args, "severity", None) or "Warning"

    if severity not in _VALID_SEVERITIES:
        sys.stderr.write(
            "report_bug_helper write-bug: --severity must be one of "
            "{0}; got: {1!r}\n".format(", ".join(_VALID_SEVERITIES), severity)
        )
        return 2

    file_path = getattr(args, "file", None) or ""

    # --- --file existence check: warn but continue ----------------------------
    files = []
    if file_path:
        if not os.path.exists(file_path):
            sys.stderr.write(
                "report_bug_helper write-bug: warning: --file path does not "
                "exist on disk: {0!r} (continuing)\n".format(file_path)
            )
        files = [{"path": file_path, "detail": ""}]

    # --- Build issue dict -----------------------------------------------------
    issue = {
        "title": title,
        "severity": severity,
        "description": description,
        "expected": "",
        "actual": "",
        "files": files,
        "evidence": "Reported by user.",
        "ac_ref": "N/A",
    }

    # --- Write via the shared writer ------------------------------------------
    try:
        written = file_bugs(
            bugs_dir=bugs_dir,
            issues=[issue],
            feature_spec_path="N/A",
            date=date,
            source="manual",
        )
    except OSError as exc:
        sys.stderr.write(
            "report_bug_helper write-bug: I/O error writing bug file: {0}\n".format(exc)
        )
        return 1

    sys.stdout.write(json.dumps(written, indent=2) + "\n")
    return 0


# ---------------------------------------------------------------------------
# Registry + parser construction
# ---------------------------------------------------------------------------

# _SUBCOMMAND_REGISTRY is the extension point for new verbs.
# Each entry is a (verb_name, help_text, handler_function) triple.
# To add a future verb:
#   1. Write the cmd_<verb> function above.
#   2. Append (kebab-name, help, cmd_func) to this list.
#   3. Add the argument block for the verb in the elif chain in
#      _register_subcommands below.
_SUBCOMMAND_REGISTRY = [
    (
        "preflight",
        (
            "Resolve workspace (install_root / source_root / is_wrapper) "
            "via resolve_workspace; emit JSON {bugs_dir, root, is_wrapper} "
            "to stdout.  Fail-soft to standalone on any config error."
        ),
        cmd_preflight,
    ),
    (
        "write-bug",
        (
            "Build a single issue dict and write it to bugs/NNN-<slug>.md "
            "via the shared file_bugs() writer (source='manual').  Emits "
            "the written path(s) as a JSON array to stdout."
        ),
        cmd_write_bug,
    ),
]


def build_parser():
    # type: () -> argparse.ArgumentParser
    """Build and return the top-level ArgumentParser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="report_bug_helper",
        description=(
            "Helper for /report-bug — user-facing bug filing command. "
            "Resolves the bugs/ directory under install_root and writes "
            "bug reports in storage-rules.md format via the shared "
            "file_bugs() writer."
        ),
    )

    subparsers = parser.add_subparsers(dest="subcommand")
    _register_subcommands(subparsers)
    return parser


def _register_subcommands(subparsers):
    # type: (...) -> None
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
                    "Workspace root to resolve.  In wrapper mode this is "
                    "the wrapper root (not the project sub-directory). "
                    "Default: CWD."
                ),
            )

        elif verb == "write-bug":
            sp.add_argument(
                "--bugs-dir",
                required=True,
                dest="bugs_dir",
                metavar="DIR",
                help="Absolute path to the bugs/ directory (from preflight output).",
            )
            sp.add_argument(
                "--date",
                required=True,
                metavar="YYYY-MM-DD",
                help=(
                    "Report date in YYYY-MM-DD format.  REQUIRED — "
                    "the helper never calls the clock."
                ),
            )
            sp.add_argument(
                "--description",
                required=True,
                metavar="TEXT",
                help="What is wrong (1–3 sentences).",
            )
            sp.add_argument(
                "--title",
                default=None,
                metavar="TEXT",
                help=(
                    "Short title (1–5 words).  Defaults to --description when "
                    "omitted."
                ),
            )
            sp.add_argument(
                "--severity",
                default="Warning",
                choices=list(_VALID_SEVERITIES),
                metavar="SEVERITY",
                help=(
                    "Severity level: Critical | Warning | Info.  "
                    "Default: Warning."
                ),
            )
            sp.add_argument(
                "--file",
                default=None,
                dest="file",
                metavar="PATH",
                help=(
                    "Optional path to the relevant file.  If the path does "
                    "not exist on disk a warning is emitted to stderr but "
                    "the bug is still written."
                ),
            )

        sp.set_defaults(func=handler)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv=None):
    # type: (...) -> int
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
