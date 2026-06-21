"""Internal package for report_bug_helper (the /report-bug command's mechanical work).

Submodules are underscore-prefixed.  External callers invoke via the POSIX
launcher `report_bug_helper` or `report_bug_helper.main`.

Public entry point is `main` (re-exported below).  Subcommand verbs are wired
in `_cli.py`; `main` dispatches to the selected handler.

Verbs:
  preflight   — resolve workspace (install_root / source_root / is_wrapper)
                via resolve_workspace (fail-soft to standalone like _fix does);
                emit JSON {bugs_dir, root, is_wrapper} to stdout.
  write-bug   — build a single issue dict and call file_bugs() from
                _shared/bug_file.py with source="manual".  Emits the written
                path(s) as a JSON array to stdout.
"""

from ._cli import main

__all__ = ["main"]
