"""Thin entry-point shim — see src/devforge/lib/_generate_docs/ for implementation.

This file exists so the POSIX launcher (`src/devforge/lib/generate_docs_helper`)
continues to invoke a single Python file at a stable path, and so test
code that does `import generate_docs_helper` continues to find the
public API. All logic lives in the `_generate_docs` package alongside;
this shim only forwards.

Refactor lineage: prior to the split into `_generate_docs/`, all logic
was in this file as a 1144-line monolith. The split was driven by the
"Design discipline" section of `python-engineer.md` plus the
GENERATE-DOCS-PLAN scope; module thresholds are documented there.

The non-setter symbols re-exported below (`STATE_FILE_NAME`,
`default_state`, `default_package_record`, `_state_file_path`, the
`_validate_*` helpers, and `EXPORT_KINDS`) keep the helper's public
import surface stable for direct-import tests. Setter handlers are
intentionally NOT re-exported — they're internal CLI handlers and
should be invoked through `main`.
"""

import sys
from pathlib import Path

# Make `_generate_docs` (and its sibling `generate_docs_schema`)
# importable when this file is run as `python3 generate_docs_helper.py`
# from any cwd. When invoked as a module via the test's
# `sys.path.insert`, this is a no-op since the path is already present.
_LIB_DIR = str(Path(__file__).resolve().parent)
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _generate_docs import main  # noqa: E402

# Re-exports for direct-import tests. None of these are setters.
from _generate_docs._state import (  # noqa: E402,F401
    STATE_FILE_NAME,
    _state_file_path,
    default_concern_record,
    default_package_record,
    default_state,
)
from _generate_docs._validation import (  # noqa: E402,F401
    _validate_in_enum,
    _validate_line_range,
    _validate_optional_string,
    _validate_string,
)
from generate_docs_schema import EXPORT_KINDS  # noqa: E402,F401


if __name__ == "__main__":
    sys.exit(main())
