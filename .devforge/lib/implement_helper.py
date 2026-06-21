"""Thin entry-point shim for /implement helper -- see _implement/ for implementation.

Task execution for /implement: resolve-next-task, preflight, agent dispatch,
scope-aware verify, autonomous review loop, forcing-functions gate, per-task
WIP commit. All logic lives in `_implement/`; this shim provides the stable
POSIX launcher path.
"""

import sys
from pathlib import Path

# Make `_implement` importable when this file is run as
# `python3 implement_helper.py` from any cwd. When invoked as a module
# via `python -m devforge.lib.implement_helper`, this is a no-op since
# the lib dir is already on sys.path.
_LIB_DIR = str(Path(__file__).resolve().parent)
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _implement._cli import main  # noqa: E402


if __name__ == "__main__":
    sys.exit(main())
