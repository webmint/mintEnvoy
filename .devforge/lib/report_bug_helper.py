"""Thin entry-point shim for /report-bug helper — see _report_bug/ for implementation.

User-facing bug filing: resolves the bugs/ directory under install_root
(via resolve_workspace, fail-soft to standalone), builds a single issue dict
from CLI arguments, and delegates writing to the shared file_bugs() writer.
All logic lives in `_report_bug/`; this shim provides the stable POSIX launcher path.
"""

import sys
from pathlib import Path

# Make `_report_bug` importable when this file is run as
# `python3 report_bug_helper.py` from any cwd.  When invoked as a module
# via `python -m devforge.lib.report_bug_helper`, this is a no-op since
# the lib dir is already on sys.path.
_LIB_DIR = str(Path(__file__).resolve().parent)
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _report_bug._cli import main  # noqa: E402


if __name__ == "__main__":
    sys.exit(main())
