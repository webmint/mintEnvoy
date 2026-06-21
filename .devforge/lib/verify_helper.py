"""Thin entry-point shim for /verify helper — see _verify/ for implementation.

Per-feature AC verification + verdict: proves acceptance criteria, runs
assembled mechanical checks, folds in /review findings, and renders
APPROVED/NEEDS WORK/REJECTED. All logic lives in `_verify/`; this shim
provides the stable POSIX launcher path.
"""

import sys
from pathlib import Path

# Make `_verify` importable when this file is run as
# `python3 verify_helper.py` from any cwd. When invoked as a module
# via `python -m devforge.lib.verify_helper`, this is a no-op since
# the lib dir is already on sys.path.
_LIB_DIR = str(Path(__file__).resolve().parent)
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _verify._cli import main  # noqa: E402


if __name__ == "__main__":
    sys.exit(main())
