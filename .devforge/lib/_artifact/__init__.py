"""Internal package for artifact_helper (the commit-artifacts verb).

Exposes the shared WIP artifact-commit discipline for pipeline commands
(/research, /discover, /specify, /plan, /grill, /breakdown, /review, /verify)
and the /finalize safety-net.

Public entry point is `main` (re-exported below). Subcommand verbs are wired
in `_cli.py`; `main` dispatches to the selected handler.

Verbs shipped:
  commit-artifacts  -- stage explicit artifact paths + WIP commit to install root
"""

from ._cli import main

__all__ = ["main"]
