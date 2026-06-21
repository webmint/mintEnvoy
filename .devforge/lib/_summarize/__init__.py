"""Internal package for summarize_helper (the /summarize command's mechanical work).

Submodules are underscore-prefixed. External callers invoke via the POSIX
launcher `summarize_helper` or `summarize_helper.main`.

Public entry point is `main` (re-exported below). Subcommand verbs are wired
in `_cli.py`; `main` dispatches to the selected handler.

Phase 1 ships 1 verb (scaffold):
  preflight  — gate on 4-command setup chain + spec **Status**: Complete check

Later phases add gather-change-data / read-verification / parse-completion-notes /
read-plan-decisions verbs via _SUBCOMMAND_REGISTRY in `_cli.py` — no changes
to this file required for extensions.
"""

from ._cli import main

__all__ = ["main"]
