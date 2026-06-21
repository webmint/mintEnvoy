"""Thin entry-point shim — see src/devforge/lib/_discover/ for implementation.

This file exists so the POSIX launcher (`src/devforge/lib/discover_helper`)
continues to invoke a single Python file at a stable path, and so test
code that does `import discover_helper` continues to find the public
API. All logic lives in the `_discover` package alongside; this shim
only forwards.

Refactor lineage: prior to the split into `_discover/`, all logic was
in this file as a 2123-line monolith. The split was driven by Phase A1
of `REFACTOR-MONOLITHIC-HELPERS-PLAN.md`. Module shape mirrors
`_generate_docs/` precedent.

The constants + functions re-exported below keep the helper's public
import surface stable for direct-import tests
(`tests/lib/test_discover_helper.py` reaches for these attributes).
Setter handlers are intentionally NOT re-exported — they're internal
CLI handlers and should be invoked through `main`.
"""

import sys
from pathlib import Path

# Make `_discover` importable when this file is run as
# `python3 discover_helper.py` from any cwd. When invoked as a module
# via the test's `sys.path.insert`, this is a no-op since the path is
# already present.
_LIB_DIR = str(Path(__file__).resolve().parent)
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _discover import main  # noqa: E402

# Re-exports for direct-import tests.
from _discover._state import (  # noqa: E402,F401
    MEMO_FILE_NAME,
    REPORT_FILE_NAME,
    RUBRIC_DIMENSIONS,
    _load_memo,
    _load_report,
    _state_transaction,
    default_memo_state,
    default_report_state,
)
from _discover._topic import derive_topic_slug  # noqa: E402,F401
from _discover._cli import (  # noqa: E402,F401
    EFFORT_ENUM,
    OVERALL_FIT_ENUM,
    PREFLIGHT_PREREQS,
    VERDICT_ENUM,
)


if __name__ == "__main__":
    sys.exit(main())
