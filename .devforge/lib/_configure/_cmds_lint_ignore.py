"""lint-ignore command handler: exclude framework folders from consumer linters."""

from __future__ import annotations

import argparse
import json
import sys

from ._lint_ignore import run_lint_ignore


def cmd_lint_ignore(args: argparse.Namespace) -> int:
    """Detect linter configs under install_root and emit a JSON exclude report.

    Default (no --apply): dry-run, JSON report to stdout.
    With --apply: writes the auto-tier changes, leaves manual-tier untouched,
    prints what was done as JSON.

    Exit 0 = report emitted (with or without --apply).
    Exit 1 = unexpected error during scanning.
    """
    try:
        report = run_lint_ignore(
            install_root=args.install_root,
            devforge_dir=args.devforge_dir,
            apply=args.apply,
        )
    except Exception as exc:
        sys.stderr.write(
            "configure_helper lint-ignore: unexpected error: {0}\n".format(exc)
        )
        return 1
    sys.stdout.write(json.dumps(report, indent=2))
    sys.stdout.write("\n")
    return 0
