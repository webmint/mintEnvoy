"""Internal package for finalize_helper (the /finalize command's mechanical work).

Submodules are underscore-prefixed. External callers invoke via the POSIX
launcher `finalize_helper` or `finalize_helper.main`.

Public entry point is `main` (re-exported below). Subcommand verbs are wired
in `_cli.py`; `main` dispatches to the selected handler.

Phase 1 ships 1 verb (scaffold):
  preflight  — gate on 4-command setup chain + spec **Status**: Complete check
               + source_root / wrapper_mode resolution from CLAUDE.md
               + WIP/checkpoint detection (the no-op signal)

Later phases add gather-change-data / resolve-squash-base / check-pushed /
squash verbs via _SUBCOMMAND_REGISTRY in `_cli.py` — no changes to this
file required for extensions.
"""

from ._cli import main

__all__ = ["main"]
