"""Thin entry-point shim for /summarize helper — see _summarize/ for implementation.

PR-ready feature narrative synthesis: reads spec + plan + task completion notes
+ git + verification.md, and orchestrates the inline composition of
specs/[feature]/summary.md.  All logic lives in `_summarize/`; this shim
provides the stable POSIX launcher path.
"""

import sys
from pathlib import Path

# Make `_summarize` importable when this file is run as
# `python3 summarize_helper.py` from any cwd. When invoked as a module
# via `python -m devforge.lib.summarize_helper`, this is a no-op since
# the lib dir is already on sys.path.
_LIB_DIR = str(Path(__file__).resolve().parent)
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _summarize._cli import main  # noqa: E402


if __name__ == "__main__":
    sys.exit(main())
