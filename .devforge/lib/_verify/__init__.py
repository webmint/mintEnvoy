"""Internal package for verify_helper (the /verify command's mechanical work).

Submodules are underscore-prefixed. External callers invoke via the POSIX
launcher `verify_helper` or `verify_helper.main`.

Public entry point is `main` (re-exported below). Subcommand verbs are wired
in `_cli.py`; `main` dispatches to the selected handler.

Phase 1 ships 2 verbs (scaffold):
  check-status-and-flip  — read or update per-feature verify state
  preflight              — gate on 4-command setup chain + populated constitution

Later phases add AC / scope / verdict / report verbs via _SUBCOMMAND_REGISTRY
in `_cli.py` — no changes to this file required for extensions.
"""

from ._cli import main

__all__ = ["main"]
