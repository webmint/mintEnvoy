"""Thin entry-point shim for artifact_helper — see _artifact/ for implementation.

Shared WIP artifact-commit discipline for pipeline commands:
stages ONLY the explicitly named artifact paths (spec.md, plan.md,
*-handoff.json, review.md, etc.) into the install repo and creates a
[WIP] <label> commit, so each command's work is git-safe the moment it
is written.  Per-step [WIP] commits fold into /finalize's existing
git reset --soft squash — the final PR is byte-identical to today.

All logic lives in `_artifact/`; this shim provides the stable POSIX
launcher path.
"""

import sys
from pathlib import Path

# Make `_artifact` importable when this file is run as
# `python3 artifact_helper.py` from any cwd. When invoked as a module
# via `python -m devforge.lib.artifact_helper`, this is a no-op since
# the lib dir is already on sys.path.
_LIB_DIR = str(Path(__file__).resolve().parent)
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _artifact._cli import main  # noqa: E402


if __name__ == "__main__":
    sys.exit(main())
