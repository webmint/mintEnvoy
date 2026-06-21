"""Thin entry-point shim for /audit helper — see _audit/ for implementation.

Adversarial whole-codebase audit: mislogic hunt, hotspot scoring,
agent ensemble (code-reviewer, architect, qa-reviewer, security-reviewer),
consensus merge, and report generation. All logic lives in `_audit/`;
this shim provides the stable POSIX launcher path.
"""

import sys
from pathlib import Path

# Make `_audit` importable when this file is run as
# `python3 audit_helper.py` from any cwd. When invoked as a module
# via `python -m devforge.lib.audit_helper`, this is a no-op since
# the lib dir is already on sys.path.
_LIB_DIR = str(Path(__file__).resolve().parent)
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _audit._cli import main  # noqa: E402


if __name__ == "__main__":
    sys.exit(main())
