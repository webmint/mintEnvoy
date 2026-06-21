"""Thin entry-point shim — see src/devforge/lib/_constitute/ for implementation.

This file exists so the POSIX launcher (`src/devforge/lib/constitute_helper`)
continues to invoke a single Python file at a stable path, and so test
code that does `import constitute_helper` continues to find the public
API. All logic lives in the `_constitute` package alongside; this shim
only forwards.

Refactor lineage: prior to the split into `_constitute/`, all logic was
in this file as a 3105-line monolith. The split was driven by Phase C1
of `REFACTOR-MONOLITHIC-HELPERS-PLAN.md`. Module shape mirrors
`_generate_docs/` precedent.

The constants + functions re-exported below keep the helper's public
import surface stable for direct-import tests
(`tests/lib/test_constitute_helper.py` reaches for these attributes).
Setter handlers are intentionally NOT re-exported — they're internal
CLI handlers and should be invoked through `main`.
"""

import sys
from pathlib import Path

# Make `_constitute` and sibling helpers (`init_helper`, `configure_helper`)
# importable when this file is run as `python3 constitute_helper.py` from
# any cwd. When invoked as a module via the test's `sys.path.insert`, this
# is a no-op since the path is already present.
_LIB_DIR = str(Path(__file__).resolve().parent)
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _constitute import main  # noqa: E402

# Re-exports for direct-import tests.
from _constitute._schema import (  # noqa: E402,F401
    ENUM_FIELDS,
    FIELD_SCHEMA,
)
from _constitute._state import (  # noqa: E402,F401
    _empty_section,
    _find_section,
    _load,
    _state_transaction,
    default_state,
)
from _constitute._validators import (  # noqa: E402,F401
    _validate_enum,
    _validate_path_value,
    _validate_scalar,
    _validate_string_array,
    _validate_verbatim,
)
from _constitute._universal import (  # noqa: E402,F401
    _extract_universal_rules_from_state,
    _parse_universal_blocks,
)
from _constitute._md_parsers import (  # noqa: E402,F401
    _parse_glossary_md,
    _parse_related_line,
    _parse_used_in_line,
)
from _constitute._validate_metrics import (  # noqa: E402,F401
    _build_package_name_map,
    _check_balanced_braces,
    _check_code_example_syntax,
    _check_json_syntax,
    _check_python_syntax,
    _compute_composite,
    _count_citations,
    _count_code_syntax,
    _count_rule_tags,
    _count_slot_fill,
)


if __name__ == "__main__":
    sys.exit(main())
