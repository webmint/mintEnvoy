"""Configure-report summary rendering."""

from __future__ import annotations

from typing import List

from ._schema import FIELD_SCHEMA
from ._validators import collect_executability_warnings


# Field groupings for summary output (locked order).
_SUMMARY_GROUPS = (
    ("Identity", ("project_name", "project_description", "project_type")),
    (
        "Stack",
        (
            "primary_language",
            "languages",
            "frameworks",
            "architectures",
            "project_natures",
            "error_handlings",
            "api_layers",
            "testings",
            "build_tools",
        ),
    ),
    (
        "Per-package",
        (
            "build_commands",
            "type_check_commands",
            "lint_commands",
            "test_commands",
            "package_stacks",
        ),
    ),
    (
        "Verbatim docs",
        ("project_structure", "dev_commands", "architecture_details"),
    ),
    (
        "Preferences",
        (
            "workflow_enforcement",
            "ai_attribution",
            "claude_tier_think",
            "claude_tier_do",
            "claude_tier_verify",
        ),
    ),
    (
        "AC verification",
        (
            "ac_verification_mode",
            "ac_runtime_url",
            "ac_runtime_api_base",
            "ac_runtime_cli_command",
        ),
    ),
)

# Maximum rendered value width before truncation (chars).
_SUMMARY_MAX_WIDTH = 80


def _truncate_str(s: str, max_width: int = _SUMMARY_MAX_WIDTH) -> str:
    """Truncate string to max_width chars, appending '...' if longer."""
    if len(s) <= max_width:
        return s
    return s[: max_width - 3] + "..."


def _render_field_for_summary(name: str, kind: str, value: object) -> str:
    """Render one field's summary line(s).

    Scalars render as a single indented line. Arrays render as either a
    comma-joined single line (string_array) or one 'path | language |
    framework' row per record (package_stack_array).

    Returns a string ending in a newline.
    """
    pad_name = "  {0:<26}".format(name)

    if kind == "scalar":
        if value is None:
            return "{0}  (unset)\n".format(pad_name)
        rendered = _truncate_str(str(value))
        return "{0}  {1}\n".format(pad_name, rendered)

    if kind == "string_array":
        if not value:
            return "{0}  (empty)\n".format(pad_name)
        joined = ", ".join(str(v) for v in value)
        return "{0}  {1}\n".format(pad_name, _truncate_str(joined))

    if kind == "package_stack_array":
        if not value:
            return "{0}  (empty)\n".format(pad_name)
        lines = ["{0}\n".format(pad_name)]
        for rec in value:
            path = rec.get("path", "")
            lang = rec.get("language", "")
            fw = rec.get("framework") or ""
            lines.append("    {0} | {1} | {2}\n".format(path, lang, fw))
        return "".join(lines)

    # Unknown kind — should not occur since we walk FIELD_SCHEMA.
    return "{0}  ?\n".format(pad_name)


def _render_executability_warnings(warnings: List[dict]) -> str:
    """Render the executability WARNING block for `warnings`.

    Each warning becomes one line:
        WARNING  <scope>: '<command>' — '<missing_token>' not found on PATH
                  (verify may fail at /implement time)

    Returns an empty string when `warnings` is empty.
    """
    if not warnings:
        return ""
    lines = ["\n### Command Executability Warnings\n"]
    for w in warnings:
        lines.append(
            "  WARNING  {scope}: '{command}' — '{missing_token}' not found on PATH"
            " (verify may fail at /implement time)\n".format(**w)
        )
    return "".join(lines)


def _render_configure_summary(state, source_root=None):
    # type: (dict, object) -> str
    """Build the deterministic configure-report summary string from `state`.

    Groups fields by _SUMMARY_GROUPS. Appends a WARNING block for any
    configured command whose leading executable is not resolvable via
    shutil.which (best-effort PATH probe; see probe_command_executability
    docstring for the accepted npm/npx indirection limitation).

    source_root: optional absolute path to the project source root.  When
        provided, locally-installed tools in `node_modules/.bin` suppress
        false "not found" warnings.  Threaded to collect_executability_warnings.

    Output ends with exactly one trailing newline. Stable across re-runs
    (deterministic).
    """
    field_kinds = dict(FIELD_SCHEMA)
    lines = []
    lines.append("## Configure Report\n")

    for group_name, field_names in _SUMMARY_GROUPS:
        lines.append("\n### {0}\n".format(group_name))
        for name in field_names:
            kind = field_kinds.get(name, "scalar")
            value = state.get(name)
            lines.append(_render_field_for_summary(name, kind, value))

    warnings = collect_executability_warnings(state, source_root=source_root)
    lines.append(_render_executability_warnings(warnings))

    return "".join(lines)
