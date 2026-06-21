"""Thin entry-point shim — see src/devforge/lib/_configure/ for implementation.

This file exists so the POSIX launcher (`src/devforge/lib/configure_helper`)
continues to invoke a single Python file at a stable path, and so test
code that does `import configure_helper` continues to find the public
API. All logic lives in the `_configure` package alongside; this shim
only forwards.

Refactor lineage: prior to the split into `_configure/`, all logic was
in this file as a 3312-line monolith. The split was driven by Phase A2
of `REFACTOR-MONOLITHIC-HELPERS-PLAN.md`. Module shape mirrors
`_generate_docs/` precedent.

The constants + functions re-exported below keep the helper's public
import surface stable for direct-import tests
(`tests/lib/test_configure_helper.py` reaches for these attributes) and
for `constitute_helper` which imports `OUTPUT_FILE_NAME`,
`YamlParseError`, `parse_yaml`, `_parse_overview_md`, and
`_parse_architecture_md` directly from this module. Setter handlers
are intentionally NOT re-exported — they're internal CLI handlers and
should be invoked through `main`.
"""

import sys
from pathlib import Path

# Make `_configure` (and sibling helpers like `init_helper`) importable
# when this file is run as `python3 configure_helper.py` from any cwd.
# When invoked as a module via the test's `sys.path.insert`, this is a
# no-op since the path is already present.
_LIB_DIR = str(Path(__file__).resolve().parent)
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _configure import main  # noqa: E402

# Re-exports for direct-import tests and for cross-helper imports
# (constitute_helper reaches into configure_helper for OUTPUT_FILE_NAME,
# YamlParseError, parse_yaml, _parse_overview_md, _parse_architecture_md).
from _configure._schema import (  # noqa: E402,F401
    ENUM_FIELDS,
    FIELD_SCHEMA,
    OUTPUT_FILE_NAME,
)
from _configure._state import (  # noqa: E402,F401
    _dump,
    _load,
    _lock_file_path,
    _state_transaction,
    default_state,
)
from _configure._yaml import (  # noqa: E402,F401
    YamlParseError,
    emit_yaml,
    parse_yaml,
)
from _configure._validators import (  # noqa: E402,F401
    _validate_enum,
    _validate_path_value,
    _validate_scalar,
    _validate_string_array,
    _validate_verbatim,
)
from _configure._md_parsers import (  # noqa: E402,F401
    _extract_section,
    _parse_agent_frontmatter,
    _parse_architecture_md,
    _parse_md_bullets,
    _parse_md_table,
    _parse_module_map,
    _parse_overview_md,
)
from _configure._hints import (  # noqa: E402,F401
    _derive_build_tool_hint,
)
from _configure._render import (  # noqa: E402,F401
    _PROJECT_CONFIG_KEY_ORDER,
    _build_project_config,
    _build_substitution_map,
    _read_agent_list,
    _substitute_placeholders,
    _write_json,
)


if __name__ == "__main__":
    sys.exit(main())
