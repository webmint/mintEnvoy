"""Verify + summary handlers."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

import init_helper  # type: ignore  # noqa: E402

from ._schema import FIELD_SCHEMA
from ._state import _load
from ._summary import _render_configure_summary
from ._yaml import YamlParseError


# AC runtime fields that are only required when ac_verification_mode ==
# "runtime-assisted". When mode differs, these may be None.
_AC_RUNTIME_FIELDS = {"ac_runtime_url", "ac_runtime_api_base", "ac_runtime_cli_command"}


def cmd_verify(args: argparse.Namespace) -> int:
    """Cross-check configure.yaml + project-config.json for correctness.

    Checks:
    1. All 29 configure.yaml fields populated (non-null scalars, non-empty
       arrays). AC runtime fields (3) are exempt when ac_verification_mode
       != "runtime-assisted". project_natures is required (empty → violation).
    2. project-config.json exists and is valid JSON.
    3. Round-trip identity: configure.yaml fields appear in project-config.json
       with matching values; init.yaml fields appear with matching values.

    Exit 0 = all checks pass ("verify: ok" on stderr).
    Exit 2 = at least one violation (each violation enumerated on stderr).
    """
    devforge_dir = Path(args.devforge_dir)
    violations = []

    # Load configure.yaml.
    try:
        cfg_state = _load(args.devforge_dir)
    except (OSError, YamlParseError) as err:
        sys.stderr.write(
            "configure_helper verify: cannot load configure.yaml: {0}\n".format(err)
        )
        return 2

    # Determine if ac_verification_mode requires AC runtime fields.
    ac_mode = cfg_state.get("ac_verification_mode")
    ac_runtime_required = (ac_mode == "runtime-assisted")

    # Check all 29 configure.yaml fields.
    for name, kind in FIELD_SCHEMA:
        value = cfg_state.get(name)
        if name in _AC_RUNTIME_FIELDS and not ac_runtime_required:
            # AC runtime fields are optional when mode != runtime-assisted.
            continue
        if kind == "scalar":
            if value is None:
                violations.append("required field {0} is null".format(name.upper()))
        elif kind == "string_array":
            if not value:
                violations.append("required field {0} is empty".format(name.upper()))
        elif kind == "package_stack_array":
            if not value:
                violations.append("required field {0} is empty".format(name.upper()))

    # Load init.yaml.
    init_yaml_path = devforge_dir / init_helper.OUTPUT_FILE_NAME
    init_state = None  # type: Optional[dict]
    if not init_yaml_path.exists():
        violations.append("init.yaml missing")
    else:
        try:
            init_text = init_yaml_path.read_text(encoding="utf-8")
            init_state = init_helper.parse_yaml(init_text)
        except (OSError, init_helper.YamlParseError) as err:
            violations.append("init.yaml unreadable: {0}".format(err))

    # Load project-config.json.
    config_path = devforge_dir / "project-config.json"
    pconfig = None  # type: Optional[dict]
    if not config_path.exists():
        violations.append("project-config.json missing")
    else:
        try:
            pconfig_text = config_path.read_text(encoding="utf-8")
        except OSError as err:
            violations.append("project-config.json unreadable: {0}".format(err))
        else:
            try:
                pconfig = json.loads(pconfig_text)
            except (json.JSONDecodeError, ValueError):
                violations.append("project-config.json malformed")

    # Round-trip check: configure.yaml fields vs project-config.json.
    if pconfig is not None:
        for name, kind in FIELD_SCHEMA:
            upper = name.upper()
            if upper not in pconfig:
                violations.append(
                    "project-config.json missing key {0}".format(upper)
                )
                continue
            cfg_val = cfg_state.get(name)
            pc_val = pconfig[upper]
            if cfg_val != pc_val:
                violations.append(
                    "round-trip mismatch: configure.yaml.{0}={1!r} but "
                    "project-config.json.{2}={3!r}".format(
                        name, cfg_val, upper, pc_val
                    )
                )

        # Round-trip check: init.yaml fields vs project-config.json.
        if init_state is not None:
            _INIT_KEYS = {
                "workspace_mode": "WORKSPACE_MODE",
                "project_root": "PROJECT_ROOT",
                "project_state": "PROJECT_STATE",
                "default_branch": "DEFAULT_BRANCH",
                "packages_detected": "PACKAGES_DETECTED",
            }
            for init_name, upper in _INIT_KEYS.items():
                if upper not in pconfig:
                    violations.append(
                        "project-config.json missing key {0}".format(upper)
                    )
                    continue
                init_val = init_state.get(init_name)
                pc_val = pconfig[upper]
                if init_val != pc_val:
                    violations.append(
                        "round-trip mismatch: init.yaml.{0}={1!r} but "
                        "project-config.json.{2}={3!r}".format(
                            init_name, init_val, upper, pc_val
                        )
                    )

        # Derived fields: present and type-correct (may be empty string).
        for derived_key in ("WRAPPER_MODE_SECTION", "COMMIT_ATTRIBUTION", "AGENT_LIST"):
            if derived_key not in pconfig:
                violations.append(
                    "project-config.json missing derived key {0}".format(derived_key)
                )
            elif pconfig[derived_key] is None:
                violations.append(
                    "project-config.json derived key {0} is null".format(derived_key)
                )

    if violations:
        for v in violations:
            sys.stderr.write("verify: {0}\n".format(v))
        return 2

    sys.stderr.write("verify: ok\n")
    return 0


def _derive_source_root(devforge_dir):
    # type: (object) -> Optional[str]
    """Derive the project source_root from .devforge/project-config.json.

    Reads PROJECT_ROOT from project-config.json (sibling to devforge_dir).
    Returns an absolute path string, or None if derivation fails (file
    missing, malformed JSON, PROJECT_ROOT absent or standalone).

    Best-effort only — callers must handle None gracefully.
    """
    import json as _json
    from pathlib import Path as _Path

    devforge = _Path(str(devforge_dir))
    # project-config.json lives INSIDE .devforge/.
    config_path = devforge / "project-config.json"
    if not config_path.exists():
        return None

    try:
        with open(str(config_path), "r", encoding="utf-8") as fh:
            pconfig = _json.load(fh)
    except (OSError, ValueError):
        return None

    if not isinstance(pconfig, dict):
        return None

    project_root = pconfig.get("PROJECT_ROOT", "")
    if not project_root or project_root == ".":
        # Standalone: source root IS the install root (parent of .devforge/).
        install_root = devforge.parent
        return str(install_root.resolve())

    # Wrapper: source root is install_root / PROJECT_ROOT.
    install_root = devforge.parent
    source_root = install_root / str(project_root)
    return str(source_root.resolve())


def cmd_summary(args: argparse.Namespace) -> int:
    """Render the configure report summary to stdout. Read-only, exit 0 always.

    Reads configure.yaml (defaults if missing). Output is deterministic
    across re-runs — suitable for piping and diffing.
    """
    try:
        state = _load(args.devforge_dir)
    except (OSError, YamlParseError) as err:
        sys.stderr.write(
            "configure_helper summary: cannot load configure.yaml: {0}\n".format(err)
        )
        return 1

    # Derive source_root for node_modules/.bin probe (best-effort; None on failure).
    source_root = _derive_source_root(args.devforge_dir)

    sys.stdout.write(_render_configure_summary(state, source_root=source_root))
    return 0
