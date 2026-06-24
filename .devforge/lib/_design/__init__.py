"""Internal package for design_helper (the design-fidelity forcing function's
per-element disposition manifest helper — plan 40 Phase 2).

Submodules are underscore-prefixed. External callers invoke via the POSIX
launcher `design_helper` or `design_helper.main`.

Public entry point is `main` (re-exported below). Subcommand verbs are wired
in `_cli.py`; `main` dispatches to the selected handler.

Phase 2 ships 4 verbs:
  resolve-reference       — parse reference.html → elements + values + gap-list
  init-manifest           — skeleton manifest (all unclassified) from resolve output
  validate-manifest       — validate manifest: unclassified/gap → fail
  extract-spacing-scale   — extract spacing scale from styles.css (OQ-6 relaxation)

Later phases add provenance-gate verbs and the runtime-conformance dispatch via
_SUBCOMMAND_REGISTRY in `_cli.py` — no changes to this file required.
"""

from ._cli import main

__all__ = ["main"]
