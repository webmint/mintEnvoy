"""Thin entry-point shim for /pr-review helper — see _pr_review/ for implementation.

Personal-overlay PR review of foreign repos: AI-slop detection,
blast-radius analysis, and scope-drift checking. All logic lives in
`_pr_review/`; this shim provides the stable POSIX launcher path.
"""

import sys
from pathlib import Path

# Make `_pr_review` importable when this file is run as
# `python3 pr_review_helper.py` from any cwd. When invoked as a module
# via `python -m devforge.lib.pr_review_helper`, this is a no-op since
# the lib dir is already on sys.path.
_LIB_DIR = str(Path(__file__).resolve().parent)
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _pr_review._cli import main  # noqa: E402


if __name__ == "__main__":
    sys.exit(main())
