"""Thin entry-point shim for /grill helper — see _grill/ for implementation.

Per-feature devils-advocate seed review: generates grill-seed.json for
consumption by the /grill slash command.
All logic lives in `_grill/`; this shim provides the stable POSIX launcher path.
"""

import sys
from pathlib import Path

# Make `_grill` importable when this file is run as
# `python3 grill_helper.py` from any cwd. When invoked as a module
# via `python -m devforge.lib.grill_helper`, this is a no-op since
# the lib dir is already on sys.path.
_LIB_DIR = str(Path(__file__).resolve().parent)
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _grill._cli import main  # noqa: E402


if __name__ == "__main__":
    sys.exit(main())
