"""Read-only status reporter — prints per-package field-population progress.

The `status` subcommand is the only consumer of the helper that does
not mutate state, so it intentionally lives apart from the setters.
It loads the state via `_state._load_state` and renders a tree-shaped
plain-text summary to stdout (stderr is reserved for `_info` /
`_die`); when the state file is absent, it prints a one-liner saying
so and exits 0.

Stdlib only. Targets Python 3.8+.
"""

import argparse
import sys
from typing import Any

from ._state import StateLoadError, _die, _load_state, _state_file_path


def _render_field_status(value: Any) -> str:
    """Render a tristate field as SET / UNSET / explicit-null for status."""
    if value is None:
        return "UNSET"
    return "SET"


def _render_optional_field_status(value: Any) -> str:
    """For optional scalars (framework, build_tool): differentiate between
    UNSET (still None and never touched) and SET (any string assigned).

    Passing an exact empty string (`--value ""`) clears the field;
    whitespace-only input is rejected by the non-empty validator. A
    cleared field is indistinguishable in the persisted JSON from
    "never set." That ambiguity is a known shortcoming the brief
    accepts (it's explicitly approved in the brief's "Exception to
    non-empty rule" clause). We mirror that ambiguity here rather than
    add a separate "explicitly_cleared" flag.
    """
    if value is None:
        return "UNSET"
    return "SET ({0})".format(value)


def cmd_status(args: argparse.Namespace) -> int:
    """Print human-readable progress for every registered package."""
    path = _state_file_path()
    if not path.exists():
        sys.stdout.write(
            "state-file: {0} (missing — no packages registered)\n".format(path)
        )
        return 0
    try:
        state = _load_state()
    except StateLoadError as err:
        return _die(str(err), code=1)
    sys.stdout.write("state-file: {0}\n".format(path))
    sys.stdout.write("version: {0}\n".format(state.get("version", "?")))
    packages = state.get("packages", {})
    sys.stdout.write("packages: {0}\n".format(len(packages)))
    for pkg_path in sorted(packages.keys()):
        pkg = packages[pkg_path]
        sys.stdout.write("  {0}:\n".format(pkg_path))
        sys.stdout.write(
            "    overview: {0}\n".format(_render_field_status(pkg.get("overview")))
        )
        sys.stdout.write(
            "    directory_tree: {0}\n".format(
                _render_field_status(pkg.get("directory_tree"))
            )
        )
        sys.stdout.write(
            "    primary_language: {0}\n".format(
                _render_field_status(pkg.get("primary_language"))
            )
        )
        sys.stdout.write(
            "    framework: {0}\n".format(
                _render_optional_field_status(pkg.get("framework"))
            )
        )
        sys.stdout.write(
            "    build_tool: {0}\n".format(
                _render_optional_field_status(pkg.get("build_tool"))
            )
        )
        sys.stdout.write(
            "    scripts: {0}\n".format(len(pkg.get("scripts", {})))
        )
        sys.stdout.write(
            "    exports: {0}\n".format(len(pkg.get("exports", [])))
        )
        sys.stdout.write(
            "    dependencies: {0}\n".format(len(pkg.get("dependencies", [])))
        )
        sys.stdout.write(
            "    hazards: {0}\n".format(len(pkg.get("hazards", [])))
        )
        sys.stdout.write(
            "    usage_example: {0}\n".format(
                _render_field_status(pkg.get("usage_example"))
            )
        )
        sys.stdout.write(
            "    concerns: {0}\n".format(len(pkg.get("concerns") or {}))
        )
    return 0
