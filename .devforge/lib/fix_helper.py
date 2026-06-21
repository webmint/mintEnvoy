"""Thin entry-point shim for /fix helper — see _fix/ for implementation.

Proposal-only gated pipeline-remediation: reads pipeline findings
(review.md / verification.md NEEDS-WORK issues), scopes them to the
affected files, gates on the post-/implement / pre-/summarize window,
and delegates the back-half (verify-touched → review panel → forcing-functions
gate → hard gate → wip-commit) to the installed implement_helper binary.
All logic lives in `_fix/`; this shim provides the stable POSIX launcher path.
"""

import sys
from pathlib import Path

# Make `_fix` importable when this file is run as
# `python3 fix_helper.py` from any cwd. When invoked as a module
# via `python -m devforge.lib.fix_helper`, this is a no-op since
# the lib dir is already on sys.path.
_LIB_DIR = str(Path(__file__).resolve().parent)
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _fix._cli import main  # noqa: E402


if __name__ == "__main__":
    sys.exit(main())
