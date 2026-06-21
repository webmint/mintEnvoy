"""Thin entry-point shim — see src/devforge/lib/_specify/ for implementation.

This file exists so the POSIX launcher (`src/devforge/lib/specify_helper`)
continues to invoke a single Python file at a stable path, and so test
code that does `import specify_helper` continues to find the public
API. All logic lives in the `_specify` package alongside; this shim
only forwards.

Refactor lineage: prior to the split into `_specify/`, all logic was
in this file as a 3020-line monolith. The split was driven by Phase C2
of `REFACTOR-MONOLITHIC-HELPERS-PLAN.md`. Module shape mirrors
`_generate_docs/` precedent.

The constants + functions re-exported below keep the helper's public
import surface stable for direct-import tests
(`tests/lib/test_specify_helper.py` reaches for these attributes).
Setter handlers are intentionally NOT re-exported — they're internal
CLI handlers and should be invoked through `main`.
"""

import sys
from pathlib import Path

_LIB_DIR = str(Path(__file__).resolve().parent)
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _specify import main  # noqa: E402

# Re-exports for direct-import tests.
from _specify._schema import (  # noqa: E402,F401
    AC_FRAMING_LINE,
    AC_SUBSECTION_ENUM,
    AC_UBIQUITOUS_ONLY_SUBSECTIONS,
    AUTO_MODE_ENV_VAR,
    AUTO_MODE_REMINDER_SUBSTRINGS,
    CONFLICT_TYPE_ENUM,
    CONSTITUTION_POPULATE_GUARD,
    CONSTRAINT_KIND_ENUM,
    COVERAGE_RULE_BANNER,
    DP_CATEGORY_ENUM,
    DP_COVERAGE_STATE_ENUM,
    DP_STATUS_ENUM,
    DP_TURN_CAP,
    DP_TURN_CAP_REASON,
    EARS_REGEX,
    EARS_VARIANT_ENUM,
    IMPACT_ENUM,
    LANDED_IN_DEFAULT,
    LANDED_IN_ENUM,
    LIKELIHOOD_ENUM,
    MANDATORY_READS_BY_TYPE,
    PHASE1_MANDATORY_READS,
    PREFLIGHT_PREREQS,
    SOURCE_ORIGIN_ENUM,
    SPEC_STATUS_DEFAULT,
    SPEC_STATUS_ENUM,
    SPEC_TYPE_ENUM,
)
from _specify._state import (  # noqa: E402,F401
    _state_transaction,
    default_state,
)
from _specify._topic import (  # noqa: E402,F401
    filename_matches_topic,
    source_origin_for_path,
)
from _specify._cmds_phase01 import detect_mode  # noqa: E402,F401


if __name__ == "__main__":
    sys.exit(main())
