"""Render helpers: project-config.json build + substitution map + atomic file writes + agent decision."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Ordered list of keys in project-config.json.
# 29 from configure.yaml (FIELD_SCHEMA, uppercased) +
# 5 from init.yaml (WORKSPACE_MODE, PROJECT_ROOT, PROJECT_STATE,
#                   DEFAULT_BRANCH, PACKAGES_DETECTED) +
# 3 derived (WRAPPER_MODE_SECTION, COMMIT_ATTRIBUTION, AGENT_LIST).
# Total: 37 keys.
_PROJECT_CONFIG_KEY_ORDER = (
    # From configure.yaml (identity)
    "PROJECT_NAME",
    "PROJECT_DESCRIPTION",
    "PROJECT_TYPE",
    # From init.yaml
    "PROJECT_ROOT",
    "WORKSPACE_MODE",
    "PROJECT_STATE",
    "DEFAULT_BRANCH",
    # From configure.yaml (stack) — order matches testForge20 reference
    # (LANGUAGES + FRAMEWORKS before PRIMARY_LANGUAGE) for diff stability.
    "LANGUAGES",
    "FRAMEWORKS",
    "PRIMARY_LANGUAGE",
    "ARCHITECTURES",
    "PROJECT_NATURES",
    "ERROR_HANDLINGS",
    "API_LAYERS",
    "TESTINGS",
    "BUILD_TOOLS",
    # From configure.yaml (per-package)
    "BUILD_COMMANDS",
    "TYPE_CHECK_COMMANDS",
    "LINT_COMMANDS",
    "TEST_COMMANDS",
    # From init.yaml
    "PACKAGES_DETECTED",
    # From configure.yaml (per-package stacks + verbatim docs)
    "PACKAGE_STACKS",
    "PROJECT_STRUCTURE",
    "DEV_COMMANDS",
    "ARCHITECTURE_DETAILS",
    # Derived
    "WRAPPER_MODE_SECTION",
    "COMMIT_ATTRIBUTION",
    "AGENT_LIST",
    # From configure.yaml (user preferences)
    "WORKFLOW_ENFORCEMENT",
    "AI_ATTRIBUTION",
    "CLAUDE_TIER_THINK",
    "CLAUDE_TIER_DO",
    "CLAUDE_TIER_VERIFY",
    # From configure.yaml (AC verification)
    "AC_VERIFICATION_MODE",
    "AC_RUNTIME_URL",
    "AC_RUNTIME_API_BASE",
    "AC_RUNTIME_CLI_COMMAND",
)

# Template for WRAPPER_MODE_SECTION when workspace_mode == "wrapper".
_WRAPPER_MODE_TEMPLATE = (
    "## Wrapper Mode\n"
    "\n"
    "This project is configured as a wrapper workspace. Source code lives at\n"
    "`{project_root}/`. All `.devforge/`, `.claude/`, `CLAUDE.md`, and `specs/`\n"
    "artifacts live at the install root (alongside this folder)."
)

# COMMIT_ATTRIBUTION block when ai_attribution == "Yes".
# Trailing newline acts as separator when appended to a commit body.
_COMMIT_ATTRIBUTION_YES = (
    "\n\n"
    "Co-Authored-By: Claude <noreply@anthropic.com>"
)


def _write_json(data: dict, target_path: "os.PathLike[str]") -> None:
    """Atomically write `data` as indent=2 JSON to target_path.

    Uses tempfile.mkstemp in the same directory as the target (POSIX
    atomic rename guarantee). flush + fsync before os.replace for
    durability. On failure, unlinks the temp file and re-raises.
    """
    target = Path(target_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix="project-config-",
        suffix=".json.tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(data, indent=2))
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(target))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _build_project_config(
    cfg_state: dict,
    init_state: dict,
    agent_list_str: str,
) -> dict:
    """Build the project-config.json dict from configure + init state.

    Applies the mapping (lowercase configure.yaml / init.yaml keys →
    uppercase project-config.json keys). Computes the 3 derived fields.
    Returns an ordered dict whose keys follow _PROJECT_CONFIG_KEY_ORDER.

    configure.yaml fields: all 29 FIELD_SCHEMA entries.
    init.yaml fields: workspace_mode, project_root, project_state,
                      default_branch, packages_detected.
    Derived: WRAPPER_MODE_SECTION, COMMIT_ATTRIBUTION, AGENT_LIST.

    package_stack_array and package_record_array values pass through
    as-is (list of dicts with lowercase subkeys — the JSON consumer
    reads them with lowercase keys, matching the setter API).
    """
    # --- Derived: WRAPPER_MODE_SECTION ---
    workspace_mode = init_state.get("workspace_mode")
    project_root = init_state.get("project_root")
    if workspace_mode == "wrapper" and project_root:
        wrapper_section = _WRAPPER_MODE_TEMPLATE.format(project_root=project_root)
    else:
        wrapper_section = ""

    # --- Derived: COMMIT_ATTRIBUTION ---
    ai_attribution = cfg_state.get("ai_attribution")
    if ai_attribution == "Yes":
        commit_attribution = _COMMIT_ATTRIBUTION_YES
    else:
        commit_attribution = ""

    # --- Assemble ordered dict ---
    result = {}
    for key in _PROJECT_CONFIG_KEY_ORDER:
        lc = key.lower()
        if key == "WRAPPER_MODE_SECTION":
            result[key] = wrapper_section
        elif key == "COMMIT_ATTRIBUTION":
            result[key] = commit_attribution
        elif key == "AGENT_LIST":
            result[key] = agent_list_str
        elif lc in cfg_state:
            result[key] = cfg_state[lc]
        elif lc in init_state:
            result[key] = init_state[lc]
        else:
            result[key] = None
    return result


def _read_agent_list(install_root: "os.PathLike[str]") -> str:
    """Derive AGENT_LIST from .claude/agents/*.md filenames.

    Returns a markdown bullet list of agent basenames (without .md),
    sorted alphabetically. Returns empty string if the directory is
    absent or contains no .md files.
    """
    agents_dir = Path(install_root) / ".claude" / "agents"
    if not agents_dir.is_dir():
        return ""
    names = []
    try:
        for entry in agents_dir.iterdir():
            if entry.is_file() and entry.suffix == ".md":
                names.append(entry.stem)
    except OSError:
        return ""
    if not names:
        return ""
    names.sort()
    return "\n".join("- {0}".format(n) for n in names)


# Matches every {{UPPERCASE_KEY}} placeholder in a template file.
# Only UPPERCASE letters and underscores are matched so that lower-case
# or mixed-case text inside {{ }} is left untouched.
_PLACEHOLDER_RE = re.compile(r"\{\{([A-Z_]+)\}\}")

# Category B: singular alias → plural key in project_config.
# Each alias renders the corresponding plural array as a comma-joined string.
_SINGULAR_ALIASES = {
    "FRAMEWORK":          "FRAMEWORKS",
    "LANGUAGE":           "LANGUAGES",
    "BUILD_TOOL":         "BUILD_TOOLS",
    "BUILD_COMMAND":      "BUILD_COMMANDS",
    "TYPE_CHECK_COMMAND": "TYPE_CHECK_COMMANDS",
    "LINT_COMMAND":       "LINT_COMMANDS",
    "TEST_COMMAND":       "TEST_COMMANDS",
    "ERROR_HANDLING":     "ERROR_HANDLINGS",
    "API_LAYER":          "API_LAYERS",
    "TESTING":            "TESTINGS",
    "ARCHITECTURE":       "ARCHITECTURES",
}


def _comma_join(arr: object) -> str:
    """Render a list of strings as a comma-separated string.

    None or empty list → empty string. Non-list scalars passed through
    via str() as a safety fallback (should not occur for known array keys).
    """
    if arr is None:
        return ""
    if isinstance(arr, list):
        if not arr:
            return ""
        return ", ".join(str(item) for item in arr)
    return str(arr)


def _build_package_stacks_table(stacks: object) -> str:
    """Render package_stacks[] as a 5-column markdown table.

    Columns: Package (path), Language, Framework, Build Tool, Test Command.
    Empty list or None → empty string "".
    None cells in individual fields → empty cell.

    Table format:
        | Package | Language | Framework | Build Tool | Test Command |
        |---------|----------|-----------|------------|--------------|
        | path    | lang     | fw        | bt         | tc           |
    """
    if not stacks:
        return ""
    header = "| Package | Language | Framework | Build Tool | Test Command |"
    align  = "|---------|----------|-----------|------------|--------------|"
    rows = [header, align]
    for rec in stacks:
        path = rec.get("path") or ""
        lang = rec.get("language") or ""
        fw   = rec.get("framework") or ""
        bt   = rec.get("build_tool") or ""
        tc   = rec.get("test_command") or ""
        rows.append("| {0} | {1} | {2} | {3} | {4} |".format(path, lang, fw, bt, tc))
    return "\n".join(rows)


def _build_substitution_map(project_config: dict, packages_detected: object) -> dict:
    """Build the full substitution map from project-config.json + init.yaml.

    Returns dict: placeholder_key → string value covering all 5 categories:

    (A) Direct pass-through from project_config (all keys in
        _PROJECT_CONFIG_KEY_ORDER whose values are non-array scalars; array
        values are comma-joined). WRAPPER_MODE_SECTION, COMMIT_ATTRIBUTION,
        AGENT_LIST are already derived strings in project_config — used as-is.

    (B) Singular aliases: FRAMEWORK, LANGUAGE, BUILD_TOOL, BUILD_COMMAND,
        TYPE_CHECK_COMMAND, LINT_COMMAND, TEST_COMMAND, ERROR_HANDLING,
        API_LAYER, TESTING, ARCHITECTURE — each comma-joins its plural
        array from project_config.

    (C) Composed:
        PACKAGE_STACKS_SECTION — markdown table from PACKAGE_STACKS.
        PROJECT_PATHS — comma-joined path field from packages_detected[].

    (D) Identity passthrough:
        UPPERCASE → literal "{{UPPERCASE}}".

    Keys not in any category above are NOT in sub_map; callers treating
    an absent key as "missing" will return exit 2 (STATE_MANAGEMENT,
    STYLING, and any other unlisted key fall into this class).

    project_config is the dict loaded from project-config.json (uppercase
    keys). packages_detected is the list from init.yaml's packages_detected
    field (list of dicts with at least a "path" key), or None/[] if absent.
    """
    sub_map = {}

    # --- Category A: pass-through from project_config ---
    for key in _PROJECT_CONFIG_KEY_ORDER:
        val = project_config.get(key)
        if isinstance(val, list):
            # Array fields: comma-join for the template placeholder.
            sub_map[key] = _comma_join(val)
        elif val is None:
            sub_map[key] = ""
        else:
            sub_map[key] = str(val)

    # --- Category B: singular aliases of plural arrays ---
    for singular, plural in _SINGULAR_ALIASES.items():
        arr = project_config.get(plural)
        sub_map[singular] = _comma_join(arr)

    # --- Category C: composed values ---
    # PACKAGE_STACKS_SECTION — markdown table; source is the package_stacks
    # list stored under PACKAGE_STACKS key in project_config.
    stacks = project_config.get("PACKAGE_STACKS")
    sub_map["PACKAGE_STACKS_SECTION"] = _build_package_stacks_table(stacks)

    # PROJECT_PATHS — comma-join path field from packages_detected[].
    if packages_detected and isinstance(packages_detected, list):
        paths = [rec.get("path", "") for rec in packages_detected if rec.get("path")]
        sub_map["PROJECT_PATHS"] = ", ".join(paths) if paths else ""
    else:
        sub_map["PROJECT_PATHS"] = ""

    # --- Category D: identity passthrough ---
    sub_map["UPPERCASE"] = "{{UPPERCASE}}"

    return sub_map


def _substitute_placeholders(text: str, sub_map: dict) -> "Tuple[str, List[str]]":
    """Substitute every {{KEY}} in text from sub_map.

    Returns (new_text, missing_keys) where missing_keys is a sorted unique
    list of keys found in text but absent from sub_map. Caller is expected
    to surface unknown placeholders as a substitution failure.
    """
    missing = set()

    def _replacer(m: "re.Match") -> str:
        key = m.group(1)
        if key in sub_map:
            return sub_map[key]
        missing.add(key)
        # Leave placeholder unchanged so the caller can detect and report it.
        return m.group(0)

    new_text = _PLACEHOLDER_RE.sub(_replacer, text)
    return new_text, sorted(missing)


def _write_file_atomic(path: Path, content: str) -> None:
    """Atomically overwrite path with content (UTF-8).

    Uses tempfile.mkstemp in the same directory as path for POSIX atomic
    rename semantics (cross-directory rename is not atomic on most kernels).
    flush + fsync before os.replace. On failure, unlinks the temp file and
    re-raises so the original file is never corrupted.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=".substitute-",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _decide_agent(
    applies_to: Optional[List[str]],
    project_natures: List[str],
    agent_name: str,
) -> str:
    """Return 'keep' or 'drop' for one agent file.

    Rules (in order):
    1. applies_to is None (missing/unparseable) → keep (conservative).
    2. "all" in applies_to → keep (universal-fit agent).
    3. applies_to ∩ project_natures non-empty → keep.
    4. else → drop.
    """
    if applies_to is None:
        return "keep"
    if "all" in applies_to:
        return "keep"
    for nature in applies_to:
        if nature in project_natures:
            return "keep"
    return "drop"
