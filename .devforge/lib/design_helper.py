"""Thin entry-point shim for design_helper — see _design/ for implementation.

Design-fidelity helper (plan 40 Phase 2, reframed to the anchor/binding
schema in plan 53 Phase 3): validates a per-feature route+pairs binding
(specs/[feature]/design-manifest.json) against a reference.html (+ optional
design/styles.css) via `validate-binding`, `check-design-source`, and
`extract-spacing-scale`.  All logic lives in `_design/`; this shim provides
the stable POSIX launcher path.
"""

import sys
from pathlib import Path

# Make `_design` importable when this file is run as
# `python3 design_helper.py` from any cwd. When invoked as a module
# via `python -m devforge.lib.design_helper`, this is a no-op since
# the lib dir is already on sys.path.
_LIB_DIR = str(Path(__file__).resolve().parent)
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _design._cli import main  # noqa: E402


if __name__ == "__main__":
    sys.exit(main())
