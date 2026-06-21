"""Thin entry-point shim for /finalize helper — see _finalize/ for implementation.

Terminal PR-prep step: gates on setup chain + spec Complete, dispatches
tech-writer for surgical docs/ updates, and squashes WIP/checkpoint commits
into one clean feature commit.  All logic lives in `_finalize/`; this shim
provides the stable POSIX launcher path.
"""

import sys
from pathlib import Path

# Make `_finalize` importable when this file is run as
# `python3 finalize_helper.py` from any cwd. When invoked as a module
# via `python -m devforge.lib.finalize_helper`, this is a no-op since
# the lib dir is already on sys.path.
_LIB_DIR = str(Path(__file__).resolve().parent)
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _finalize._cli import main  # noqa: E402


if __name__ == "__main__":
    sys.exit(main())
