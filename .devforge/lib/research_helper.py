"""Thin entry-point shim — see src/devforge/lib/_research/ for implementation.

This file exists so the POSIX launcher (`src/devforge/lib/research_helper`)
continues to invoke a single Python file at a stable path, and so test
code that does `import research_helper` continues to find the public
API. All logic lives in the `_research` package alongside; this shim
only forwards.

Refactor lineage: prior to the split into `_research/`, all logic was
in this file as a 5333-line monolith. The split was driven by Phase D
of `REFACTOR-MONOLITHIC-HELPERS-PLAN.md`. Module shape mirrors
`_specify/` precedent.

The constants + functions re-exported below keep the helper's public
import surface stable for direct-import tests
(`tests/lib/test_research_helper.py` reaches for these attributes).
Setter handlers are intentionally NOT re-exported — they're internal
CLI handlers and should be invoked through `main`.
"""

import sys
from pathlib import Path

# Make `_research` and sibling helpers (`init_helper`) importable when
# this file is run as `python3 research_helper.py` from any cwd. When
# invoked as a module via the test's `sys.path.insert`, this is a no-op
# since the path is already present.
_LIB_DIR = str(Path(__file__).resolve().parent)
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _research import main  # noqa: E402

# Re-exports for direct-import tests.
from _research._constants import (  # noqa: E402,F401
    MODE_ENUM,
    PREFLIGHT_PREREQS,
    RUBRIC_DIMENSIONS,
    TURN_CAP,
    VERDICT_ENUM,
)
from _research._state import (  # noqa: E402,F401
    default_memo_state,
    default_report_state,
)
from _research._validators import (  # noqa: E402,F401
    _has_anchor_finding,
    _split_path_line,
    _validate_enum,
    _validate_file_line,
    _validate_scalar,
    _validate_string_array_json,
    _validate_verbatim,
)
from _shared.literal_call_shape import (  # noqa: E402,F401
    _detect_arg_duplication,
    _detect_literal_replacement,
    _split_top_level_args,
)
from _research._layer_package import (  # noqa: E402,F401
    _extract_package,
    _is_presentation_layer,
)
from _research._topic_conflicts import (  # noqa: E402,F401
    derive_topic_slug,
    detect_direct_conflicts,
    detect_mode_from_symptom,
)
from _research._probe_tier import _classify_probe_tier  # noqa: E402,F401


if __name__ == "__main__":
    sys.exit(main())
