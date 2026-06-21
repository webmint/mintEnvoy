"""Internal package for audit_helper (the /audit command's mechanical work).

Submodules are underscore-prefixed; schema modules (findings_schema,
hotspot_schema) are not. External callers invoke via the POSIX launcher
`audit_helper` or `audit_helper.main`.

Public entry point is `main` (re-exported below). All 18 subcommand verbs
(Phase 0–5) are wired in `_cli.py`; `main` dispatches to the selected handler.
"""

from ._cli import main

__all__ = ["main"]
