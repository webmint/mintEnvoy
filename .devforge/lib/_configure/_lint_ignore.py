"""Lint-ignore handler: exclude framework folders from the consumer project's linters.

Public API
----------
run_lint_ignore(install_root, devforge_dir, apply) -> dict
    Detects linter/formatter configs under install_root, computes what needs
    to be added, and (when apply=True) writes the changes atomically.
    Returns a report dict: {"entries": [...], "summary": {...}}.

FRAMEWORK_FOLDERS: list[str]
    The canonical ordered list of framework-installed directories to exclude.
    Includes pre-emptive entries (not yet created at setup time) per plan.

Design
------
Each linter is a Handler: a namedtuple with detect/compute/apply logic grouped
by tool.  Handlers are collected in the REGISTRY list; run_lint_ignore iterates
the registry, calls detect(), and when a tool is found calls compute_entry() to
produce a report entry. apply() writes the change for auto-action entries.

Two action tiers:
  "auto"   — stdlib-safe write, idempotent, atomic.
  "manual" — detect + print instruction, no file edit.

Idempotency rule: every auto handler checks whether its contribution is already
present; if so, reports status="already-present" and apply() is a no-op.

TOML constraint: no stdlib TOML writer. AUTO only when the relevant table/key is
ABSENT: append a correctly-formatted block at end of file. When the table is
present but the key is absent: safe targeted append (add key under the header).
When both table AND key are present: manual (user's value preserved).

JSONC constraint: attempt json.loads; on failure → manual (never corrupt).

Python target: 3.8+. No third-party imports.
"""

from __future__ import annotations

import configparser
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Ordered list of framework-installed directories to exclude from all linters.
# Pre-emptive entries (specs/, bugs/, research/, discover/, audits/) are listed
# even though they do not exist at install time — they will be created later by
# workflow commands.
FRAMEWORK_FOLDERS: List[str] = [
    ".claude",
    ".devforge",
    "specs",
    "bugs",
    "research",
    "discover",
    "audits",
]

# Folders that exist at setup time (install.sh places them).
_SETUP_TIME_FOLDERS: Set[str] = {".claude", ".devforge"}


# ---------------------------------------------------------------------------
# Atomic write helpers (match _render.py conventions)
# ---------------------------------------------------------------------------


def _write_text_atomic(path: Path, content: str) -> None:
    """Atomically overwrite path with text content (UTF-8)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=".lint-ignore-",
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


def _write_json_atomic(path: Path, data: Any) -> None:
    """Atomically overwrite path with JSON content."""
    _write_text_atomic(path, json.dumps(data, indent=2) + "\n")


# ---------------------------------------------------------------------------
# Preemptive flag helper
# ---------------------------------------------------------------------------


def _any_preemptive(folders: List[str], install_root: Path) -> bool:
    """True if any folder in the list does not yet exist under install_root."""
    return any(not (install_root / f).exists() for f in folders)


# ---------------------------------------------------------------------------
# JSONC parse helper
# ---------------------------------------------------------------------------


def _parse_jsonc(text: str) -> Tuple[Any, bool]:
    """Attempt to parse text as JSON.  Returns (parsed, ok).

    Tries json.loads; on failure returns (None, False).  We do NOT strip
    comments — if the file has comments it will fail, and we fall back to
    manual mode rather than corrupting it.
    """
    try:
        return json.loads(text), True
    except (json.JSONDecodeError, ValueError):
        return None, False


# ---------------------------------------------------------------------------
# Gitignore-style line-append (used by prettier, eslint, markdownlint)
# ---------------------------------------------------------------------------


def _gitignore_lines_status(
    path: Path, folders: List[str]
) -> Tuple[str, List[str]]:
    """Return (status, missing_lines) for a gitignore-style file.

    status is one of: "already-present", "would-add", "would-create".
    missing_lines are the folder names NOT yet in the file.
    """
    if not path.exists():
        return "would-create", list(folders)
    content = path.read_text(encoding="utf-8")
    existing_lines = {line.strip() for line in content.splitlines()}
    missing = [f for f in folders if f not in existing_lines]
    if not missing:
        return "already-present", []
    return "would-add", missing


def _gitignore_apply(path: Path, folders: List[str]) -> bool:
    """Append missing folders to a gitignore-style file. Returns True if changed."""
    _, missing = _gitignore_lines_status(path, folders)
    if not missing:
        return False
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if not existing.endswith("\n") and existing:
            existing += "\n"
    else:
        existing = ""
    new_content = existing + "# AIDevTeamForge framework folders\n"
    for folder in missing:
        new_content += folder + "\n"
    _write_text_atomic(path, new_content)
    return True


# ---------------------------------------------------------------------------
# Handler result type
# ---------------------------------------------------------------------------

# An entry in the report:
# {
#   "tool": str,
#   "file": str (relative to install_root, or "n/a"),
#   "action": "auto" | "manual",
#   "status": "would-add"|"already-present"|"would-create"|"applied"|"pending-manual",
#   "lines": [...],          # for auto entries
#   "preemptive": bool,      # True if any target folder doesn't exist yet
#   "instruction": str,      # for manual entries
# }
Entry = Dict[str, Any]


# ---------------------------------------------------------------------------
# Prettier handler
# ---------------------------------------------------------------------------


def _detect_prettier(root: Path) -> bool:
    """Detect prettier config: .prettierrc*, .prettierignore, or prettier key in package.json."""
    for pattern in [".prettierrc", ".prettierrc.json", ".prettierrc.yaml",
                    ".prettierrc.yml", ".prettierrc.toml", ".prettierrc.js",
                    ".prettierrc.cjs", "prettier.config.js", "prettier.config.cjs",
                    ".prettierignore"]:
        if (root / pattern).exists():
            return True
    pkg = root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            if "prettier" in data:
                return True
        except Exception:
            pass
    return False


def _prettier_entry(root: Path, apply: bool) -> Optional[Entry]:
    if not _detect_prettier(root):
        return None
    ignore_path = root / ".prettierignore"
    status, missing = _gitignore_lines_status(ignore_path, FRAMEWORK_FOLDERS)
    if apply and status != "already-present":
        _gitignore_apply(ignore_path, FRAMEWORK_FOLDERS)
        status = "already-present"
        missing = []
    return {
        "tool": "prettier",
        "file": ".prettierignore",
        "action": "auto",
        "status": status,
        "lines": list(FRAMEWORK_FOLDERS) if status == "already-present" else missing,
        "preemptive": _any_preemptive(FRAMEWORK_FOLDERS, root),
    }


# ---------------------------------------------------------------------------
# ESLint handler
# ---------------------------------------------------------------------------


_ESLINT_LEGACY_PATTERNS = [
    ".eslintrc", ".eslintrc.json", ".eslintrc.yaml", ".eslintrc.yml",
    ".eslintrc.js", ".eslintrc.cjs",
]
_ESLINT_FLAT_PATTERNS = [
    "eslint.config.js", "eslint.config.mjs", "eslint.config.cjs",
    "eslint.config.ts",
]


def _eslint_entry(root: Path, apply: bool) -> Optional[Entry]:
    flat = any((root / p).exists() for p in _ESLINT_FLAT_PATTERNS)
    legacy = any((root / p).exists() for p in _ESLINT_LEGACY_PATTERNS)
    if flat:
        return {
            "tool": "eslint",
            "file": "eslint.config.*",
            "action": "manual",
            "status": "pending-manual",
            "preemptive": _any_preemptive(FRAMEWORK_FOLDERS, root),
            "instruction": (
                "Add the framework folders to the `ignores` array in your eslint.config file: "
                + ", ".join('"{0}"'.format(f) for f in FRAMEWORK_FOLDERS)
            ),
        }
    if legacy:
        ignore_path = root / ".eslintignore"
        status, missing = _gitignore_lines_status(ignore_path, FRAMEWORK_FOLDERS)
        if apply and status != "already-present":
            _gitignore_apply(ignore_path, FRAMEWORK_FOLDERS)
            status = "already-present"
            missing = []
        return {
            "tool": "eslint",
            "file": ".eslintignore",
            "action": "auto",
            "status": status,
            "lines": list(FRAMEWORK_FOLDERS) if status == "already-present" else missing,
            "preemptive": _any_preemptive(FRAMEWORK_FOLDERS, root),
        }
    return None


# ---------------------------------------------------------------------------
# Markdownlint handler
# ---------------------------------------------------------------------------


def _markdownlint_entry(root: Path, apply: bool) -> Optional[Entry]:
    """Handle both markdownlint-cli (.markdownlintignore) and markdownlint-cli2."""
    entries = []

    # markdownlint-cli: .markdownlintignore exists, OR .markdownlint.* config exists
    ignore_path = root / ".markdownlintignore"
    cli_config_exists = any(
        (root / p).exists()
        for p in [".markdownlint.json", ".markdownlint.yaml",
                  ".markdownlint.yml", ".markdownlint.jsonc"]
    )
    if ignore_path.exists() or cli_config_exists:
        status, missing = _gitignore_lines_status(ignore_path, FRAMEWORK_FOLDERS)
        if apply and status != "already-present":
            _gitignore_apply(ignore_path, FRAMEWORK_FOLDERS)
            status = "already-present"
            missing = []
        entries.append({
            "tool": "markdownlint",
            "file": ".markdownlintignore",
            "action": "auto",
            "status": status,
            "lines": list(FRAMEWORK_FOLDERS) if status == "already-present" else missing,
            "preemptive": _any_preemptive(FRAMEWORK_FOLDERS, root),
        })

    # markdownlint-cli2: .markdownlint-cli2.{jsonc,json,yaml,yml}
    cli2_json_patterns = [".markdownlint-cli2.jsonc", ".markdownlint-cli2.json"]
    cli2_yaml_patterns = [".markdownlint-cli2.yaml", ".markdownlint-cli2.yml"]
    for p in cli2_json_patterns:
        path = root / p
        if path.exists():
            entries.append(_markdownlint_cli2_json_entry(path, apply, root))
            break
    for p in cli2_yaml_patterns:
        path = root / p
        if path.exists():
            entries.append({
                "tool": "markdownlint-cli2",
                "file": p,
                "action": "manual",
                "status": "pending-manual",
                "preemptive": _any_preemptive(FRAMEWORK_FOLDERS, root),
                "instruction": (
                    "Add the framework folders to the `ignores` array in {0}: ".format(p)
                    + ", ".join('"{0}"'.format(f) for f in FRAMEWORK_FOLDERS)
                ),
            })
            break

    return entries  # type: ignore  # multiple entries possible


def _markdownlint_cli2_json_entry(path: Path, apply: bool, root: Path) -> Entry:
    text = path.read_text(encoding="utf-8")
    data, ok = _parse_jsonc(text)
    if not ok:
        return {
            "tool": "markdownlint-cli2",
            "file": path.name,
            "action": "manual",
            "status": "pending-manual",
            "preemptive": _any_preemptive(FRAMEWORK_FOLDERS, root),
            "instruction": (
                "Cannot safely parse {0} (JSONC/comments?). "
                "Add the framework folders to the `ignores` array manually: ".format(path.name)
                + ", ".join('"{0}"'.format(f) for f in FRAMEWORK_FOLDERS)
            ),
        }
    ignores = data.get("ignores") or []
    missing = [f for f in FRAMEWORK_FOLDERS if f not in ignores]
    if not missing:
        return {
            "tool": "markdownlint-cli2",
            "file": path.name,
            "action": "auto",
            "status": "already-present",
            "lines": list(FRAMEWORK_FOLDERS),
            "preemptive": _any_preemptive(FRAMEWORK_FOLDERS, root),
        }
    if apply:
        data["ignores"] = ignores + missing
        _write_json_atomic(path, data)
        return {
            "tool": "markdownlint-cli2",
            "file": path.name,
            "action": "auto",
            "status": "already-present",
            "lines": list(FRAMEWORK_FOLDERS),
            "preemptive": _any_preemptive(FRAMEWORK_FOLDERS, root),
        }
    return {
        "tool": "markdownlint-cli2",
        "file": path.name,
        "action": "auto",
        "status": "would-add",
        "lines": missing,
        "preemptive": _any_preemptive(FRAMEWORK_FOLDERS, root),
    }


# ---------------------------------------------------------------------------
# flake8 handler (configparser: .flake8 / setup.cfg / tox.ini)
# ---------------------------------------------------------------------------


def _flake8_entry(root: Path, apply: bool) -> Optional[Entry]:
    """Handle flake8 via configparser (extend-exclude, comma-separated globs)."""
    for filename in [".flake8", "setup.cfg", "tox.ini"]:
        path = root / filename
        if not path.exists():
            continue
        cp = configparser.ConfigParser()
        try:
            cp.read(str(path), encoding="utf-8")
        except Exception:
            continue
        if not cp.has_section("flake8"):
            continue
        # Found a flake8 section — check extend-exclude
        existing_str = cp.get("flake8", "extend-exclude", fallback="")
        existing = [x.strip() for x in existing_str.split(",") if x.strip()]
        missing = [f for f in FRAMEWORK_FOLDERS if f not in existing]
        if not missing:
            return {
                "tool": "flake8",
                "file": filename,
                "action": "auto",
                "status": "already-present",
                "lines": list(FRAMEWORK_FOLDERS),
                "preemptive": _any_preemptive(FRAMEWORK_FOLDERS, root),
            }
        if apply:
            _flake8_apply(path, cp, existing, missing)
            return {
                "tool": "flake8",
                "file": filename,
                "action": "auto",
                "status": "already-present",
                "lines": list(FRAMEWORK_FOLDERS),
                "preemptive": _any_preemptive(FRAMEWORK_FOLDERS, root),
            }
        return {
            "tool": "flake8",
            "file": filename,
            "action": "auto",
            "status": "would-add",
            "lines": missing,
            "preemptive": _any_preemptive(FRAMEWORK_FOLDERS, root),
        }
    return None


def _flake8_apply(path: Path, cp: configparser.ConfigParser,
                  existing: List[str], missing: List[str]) -> None:
    """Merge missing folders into extend-exclude in the config file atomically."""
    all_excludes = existing + missing
    # Read the raw file so we can do a targeted replacement preserving structure.
    raw = path.read_text(encoding="utf-8")
    new_val = ", ".join(all_excludes)
    if cp.has_option("flake8", "extend-exclude"):
        # Replace the key value in-place under [flake8] (handles present-but-empty too)
        raw = _replace_ini_key(raw, "flake8", "extend-exclude", new_val)
    else:
        # extend-exclude key absent — add it under [flake8]
        raw = _insert_ini_key(raw, "flake8", "extend-exclude", new_val)
    _write_text_atomic(path, raw)


def _replace_ini_key(text: str, section: str, key: str, new_val: str) -> str:
    """Replace the value of key under [section] in an INI text, preserving rest."""
    lines = text.splitlines(keepends=True)
    in_section = False
    result = []
    replaced = False
    for line in lines:
        if re.match(r'^\s*\[{0}\]'.format(re.escape(section)), line):
            in_section = True
            result.append(line)
            continue
        if in_section and re.match(r'^\s*\[', line):
            in_section = False
            result.append(line)
            continue
        if in_section and not replaced:
            # Use [^\S\n]* (horizontal whitespace only) around = so the newline
            # is never captured into group 1 — prevents corrupt output on empty values.
            m = re.match(
                r'^(\s*{0}[^\S\n]*=[^\S\n]*)(.*)$'.format(re.escape(key)), line
            )
            if m:
                result.append(m.group(1) + new_val + "\n")
                replaced = True
                continue
        result.append(line)
    return "".join(result)


def _insert_ini_key(text: str, section: str, key: str, val: str) -> str:
    """Insert key = val under [section] in an INI text (after the section header)."""
    lines = text.splitlines(keepends=True)
    result = []
    inserted = False
    for i, line in enumerate(lines):
        result.append(line)
        if not inserted and re.match(r'^\s*\[{0}\]'.format(re.escape(section)), line):
            result.append("{0} = {1}\n".format(key, val))
            inserted = True
    if not inserted:
        # Section not found — should not happen (we only call this when section exists)
        result.append("[{0}]\n{1} = {2}\n".format(section, key, val))
    return "".join(result)


# ---------------------------------------------------------------------------
# Biome handler (biome.json — stdlib json, JSONC fails to manual)
# ---------------------------------------------------------------------------


def _biome_entry(root: Path, apply: bool) -> Optional[Entry]:
    path = root / "biome.json"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    data, ok = _parse_jsonc(text)
    if not ok:
        return {
            "tool": "biome",
            "file": "biome.json",
            "action": "manual",
            "status": "pending-manual",
            "preemptive": _any_preemptive(FRAMEWORK_FOLDERS, root),
            "instruction": (
                "Cannot safely parse biome.json (JSONC/comments?). "
                "Add framework folder negations to `files.includes`: "
                + ", ".join('"!{0}"'.format(f) for f in FRAMEWORK_FOLDERS)
            ),
        }
    # Ensure files.includes exists with "**" plus negated folders
    files = data.get("files") or {}
    includes = files.get("includes") or []
    negated = ["!{0}".format(f) for f in FRAMEWORK_FOLDERS]
    missing = [n for n in negated if n not in includes]
    if not missing:
        return {
            "tool": "biome",
            "file": "biome.json",
            "action": "auto",
            "status": "already-present",
            "lines": negated,
            "preemptive": _any_preemptive(FRAMEWORK_FOLDERS, root),
        }
    if apply:
        # Ensure "**" is first, then append missing negations
        if "**" not in includes:
            includes = ["**"] + includes
        includes = includes + missing
        if "files" not in data:
            data["files"] = {}
        data["files"]["includes"] = includes
        _write_json_atomic(path, data)
        return {
            "tool": "biome",
            "file": "biome.json",
            "action": "auto",
            "status": "already-present",
            "lines": negated,
            "preemptive": _any_preemptive(FRAMEWORK_FOLDERS, root),
        }
    return {
        "tool": "biome",
        "file": "biome.json",
        "action": "auto",
        "status": "would-add",
        "lines": missing,
        "preemptive": _any_preemptive(FRAMEWORK_FOLDERS, root),
    }


# ---------------------------------------------------------------------------
# TOML helpers (no stdlib TOML writer — text manipulation only)
# ---------------------------------------------------------------------------


def _toml_has_table(text: str, table_header: str) -> bool:
    """Return True if a TOML table header (e.g. '[tool.ruff]') exists in text."""
    pattern = r'^\s*' + re.escape(table_header) + r'\s*$'
    return bool(re.search(pattern, text, re.MULTILINE))


def _toml_has_key_under_table(text: str, table_header: str, key: str) -> bool:
    """Return True if `key = ...` appears under the given table header (before next [table])."""
    lines = text.splitlines()
    in_table = False
    for line in lines:
        stripped = line.strip()
        if re.match(r'^\s*' + re.escape(table_header) + r'\s*$', line):
            in_table = True
            continue
        if in_table:
            if stripped.startswith("[") and not stripped.startswith("#"):
                break
            m = re.match(r'^\s*' + re.escape(key) + r'\s*=', line)
            if m:
                return True
    return False


def _toml_append_block(path: Path, block: str) -> None:
    """Append a TOML block to the file, separated by a blank line."""
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if existing and not existing.endswith("\n"):
        existing += "\n"
    sep = "\n" if existing else ""
    _write_text_atomic(path, existing + sep + block)


def _toml_append_key_under_table(path: Path, table_header: str, key: str, val: str) -> None:
    """Insert 'key = val' on the line immediately after the table header."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    result = []
    inserted = False
    for line in lines:
        result.append(line)
        if not inserted and re.match(r'^\s*' + re.escape(table_header) + r'\s*$', line):
            result.append("{0} = {1}\n".format(key, val))
            inserted = True
    _write_text_atomic(path, "".join(result))


def _glob_list_toml_value(folders: List[str]) -> str:
    """Format a list of folder strings as a TOML inline array value."""
    items = ", ".join('"{0}"'.format(f) for f in folders)
    return "[{0}]".format(items)


def _regex_value_for_folders(folders: List[str]) -> str:
    """Build a regex string matching the framework folders (for black/mypy/pylint).

    Pattern: (^|/)(\.devforge|\.claude|specs|...)/
    Dots in folder names are escaped with backslash.
    """
    parts = []
    for f in folders:
        escaped = f.replace(".", r"\.")
        parts.append(escaped)
    inner = "|".join(parts)
    return '"(^|/)({0})/"'.format(inner)


def _pylint_regex_list_value(folders: List[str]) -> str:
    """Build a TOML list of regex strings for pylint ignore-paths."""
    parts = []
    for f in folders:
        escaped = f.replace(".", r"\.")
        parts.append('"(^|/)({0})/"'.format(escaped))
    return "[{0}]".format(", ".join(parts))


def _toml_has_subtable_prefix(text: str, table_prefix: str) -> bool:
    """Return True if any TOML table header starting with table_prefix exists in text.

    Used to detect sub-tables (e.g. '[tool.ruff.lint]') when the parent table
    ('[tool.ruff]') is absent — appending the parent AFTER its sub-table produces
    confusing (though technically valid) TOML. When a sub-table is detected and
    the parent is absent, handlers emit a manual entry instead.

    table_prefix must include the opening bracket, e.g. '[tool.ruff.'.
    """
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(table_prefix):
            return True
    return False


# ---------------------------------------------------------------------------
# pyproject.toml / ruff.toml handlers
# ---------------------------------------------------------------------------


def _pyproject_ruff_entry(root: Path, apply: bool) -> Optional[Entry]:
    """Handle ruff in pyproject.toml OR ruff.toml."""
    # ruff.toml: top-level extend-exclude (no [tool.ruff] table — it's the root)
    ruff_toml = root / "ruff.toml"
    if ruff_toml.exists():
        return _ruff_toml_entry(ruff_toml, apply, root)
    # pyproject.toml
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return None
    text = pyproject.read_text(encoding="utf-8")
    table = "[tool.ruff]"
    key = "extend-exclude"
    if not _toml_has_table(text, table):
        # Sub-table present but parent absent — appending parent after sub-table is confusing
        if _toml_has_subtable_prefix(text, "[tool.ruff."):
            return _make_manual_entry(
                "ruff", "pyproject.toml",
                "Add extend-exclude to your existing [tool.ruff] section (above [tool.ruff.*] blocks) in pyproject.toml: "
                + _glob_list_toml_value(FRAMEWORK_FOLDERS),
                root,
            )
        # Table absent and no sub-table — safe to append clean block
        val = _glob_list_toml_value(FRAMEWORK_FOLDERS)
        block = "{table}\n{key} = {val}\n".format(table=table, key=key, val=val)
        if apply:
            _toml_append_block(pyproject, block)
            return _make_auto_entry("ruff", "pyproject.toml", "already-present", root)
        return _make_auto_entry("ruff", "pyproject.toml", "would-add", root)
    if not _toml_has_key_under_table(text, table, key):
        # Table present, key absent — safe to append key
        val = _glob_list_toml_value(FRAMEWORK_FOLDERS)
        if apply:
            _toml_append_key_under_table(pyproject, table, key, val)
            return _make_auto_entry("ruff", "pyproject.toml", "already-present", root)
        return _make_auto_entry("ruff", "pyproject.toml", "would-add", root)
    # Table AND key present — check if all folders already excluded
    if _toml_key_contains_all_folders(text, table, key, FRAMEWORK_FOLDERS):
        return _make_auto_entry("ruff", "pyproject.toml", "already-present", root)
    # Key present with different value — manual (preserve user's list)
    return _make_manual_entry(
        "ruff", "pyproject.toml",
        "Add the framework folders to [tool.ruff] extend-exclude in pyproject.toml: "
        + ", ".join('"{0}"'.format(f) for f in FRAMEWORK_FOLDERS),
        root,
    )


def _ruff_toml_entry(path: Path, apply: bool, root: Path) -> Entry:
    """Handle ruff.toml (top-level extend-exclude, no table wrapper)."""
    text = path.read_text(encoding="utf-8")
    key = "extend-exclude"
    # ruff.toml has no [tool.X] table — extend-exclude is a top-level key
    m = re.search(r'^\s*extend-exclude\s*=', text, re.MULTILINE)
    if m:
        if _toml_top_key_contains_all_folders(text, key, FRAMEWORK_FOLDERS):
            return _make_auto_entry("ruff", "ruff.toml", "already-present", root)
        # Key present, missing some folders — manual to avoid corruption
        return _make_manual_entry(
            "ruff", "ruff.toml",
            "Add the framework folders to extend-exclude in ruff.toml: "
            + ", ".join('"{0}"'.format(f) for f in FRAMEWORK_FOLDERS),
            root,
        )
    # Key absent — safe to append
    val = _glob_list_toml_value(FRAMEWORK_FOLDERS)
    if apply:
        existing = text
        if existing and not existing.endswith("\n"):
            existing += "\n"
        _write_text_atomic(path, existing + "{0} = {1}\n".format(key, val))
        return _make_auto_entry("ruff", "ruff.toml", "already-present", root)
    return _make_auto_entry("ruff", "ruff.toml", "would-add", root)


def _toml_top_key_contains_all_folders(text: str, key: str, folders: List[str]) -> bool:
    """Check if a top-level TOML key's value contains all folders."""
    m = re.search(r'^\s*{0}\s*=\s*(.+)$'.format(re.escape(key)), text, re.MULTILINE)
    if not m:
        return False
    val = m.group(1)
    return all(f in val for f in folders)


def _toml_key_contains_all_folders(text: str, table: str, key: str, folders: List[str]) -> bool:
    """Check if a key under a TOML table contains all folder names."""
    lines = text.splitlines()
    in_table = False
    for line in lines:
        if re.match(r'^\s*' + re.escape(table) + r'\s*$', line):
            in_table = True
            continue
        if in_table:
            if line.strip().startswith("[") and not line.strip().startswith("#"):
                break
            m = re.match(r'^\s*' + re.escape(key) + r'\s*=\s*(.+)$', line)
            if m:
                val = m.group(1)
                return all(f in val for f in folders)
    return False


def _pyproject_black_entry(root: Path, apply: bool) -> Optional[Entry]:
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return None
    text = pyproject.read_text(encoding="utf-8")
    table = "[tool.black]"
    key = "extend-exclude"
    if not _toml_has_table(text, table):
        if _toml_has_subtable_prefix(text, "[tool.black."):
            return _make_manual_entry(
                "black", "pyproject.toml",
                "Add extend-exclude to your existing [tool.black] section (above [tool.black.*] blocks) in pyproject.toml. "
                "Suggested pattern: " + _regex_value_for_folders(FRAMEWORK_FOLDERS),
                root,
            )
        val = _regex_value_for_folders(FRAMEWORK_FOLDERS)
        block = "{table}\n{key} = {val}\n".format(table=table, key=key, val=val)
        if apply:
            _toml_append_block(pyproject, block)
            return _make_auto_entry("black", "pyproject.toml", "already-present", root)
        return _make_auto_entry("black", "pyproject.toml", "would-add", root)
    if not _toml_has_key_under_table(text, table, key):
        val = _regex_value_for_folders(FRAMEWORK_FOLDERS)
        if apply:
            _toml_append_key_under_table(pyproject, table, key, val)
            return _make_auto_entry("black", "pyproject.toml", "already-present", root)
        return _make_auto_entry("black", "pyproject.toml", "would-add", root)
    # Key present — check idempotency first (all folders already in the regex value)
    if _toml_key_contains_all_folders(text, table, key, FRAMEWORK_FOLDERS):
        return _make_auto_entry("black", "pyproject.toml", "already-present", root)
    # Key present with different/partial value — manual (regex merging is complex and fragile)
    return _make_manual_entry(
        "black", "pyproject.toml",
        "Merge the framework folders into [tool.black] extend-exclude regex in pyproject.toml. "
        "Suggested pattern: " + _regex_value_for_folders(FRAMEWORK_FOLDERS),
        root,
    )


def _pyproject_isort_entry(root: Path, apply: bool) -> Optional[Entry]:
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return None
    text = pyproject.read_text(encoding="utf-8")
    table = "[tool.isort]"
    key = "extend_skip_glob"  # Note: underscored key
    if not _toml_has_table(text, table):
        if _toml_has_subtable_prefix(text, "[tool.isort."):
            return _make_manual_entry(
                "isort", "pyproject.toml",
                "Add extend_skip_glob to your existing [tool.isort] section (above [tool.isort.*] blocks) in pyproject.toml: "
                + _glob_list_toml_value(FRAMEWORK_FOLDERS),
                root,
            )
        val = _glob_list_toml_value(FRAMEWORK_FOLDERS)
        block = "{table}\n{key} = {val}\n".format(table=table, key=key, val=val)
        if apply:
            _toml_append_block(pyproject, block)
            return _make_auto_entry("isort", "pyproject.toml", "already-present", root)
        return _make_auto_entry("isort", "pyproject.toml", "would-add", root)
    if not _toml_has_key_under_table(text, table, key):
        val = _glob_list_toml_value(FRAMEWORK_FOLDERS)
        if apply:
            _toml_append_key_under_table(pyproject, table, key, val)
            return _make_auto_entry("isort", "pyproject.toml", "already-present", root)
        return _make_auto_entry("isort", "pyproject.toml", "would-add", root)
    if _toml_key_contains_all_folders(text, table, key, FRAMEWORK_FOLDERS):
        return _make_auto_entry("isort", "pyproject.toml", "already-present", root)
    return _make_manual_entry(
        "isort", "pyproject.toml",
        "Add the framework folders to [tool.isort] extend_skip_glob in pyproject.toml: "
        + _glob_list_toml_value(FRAMEWORK_FOLDERS),
        root,
    )


def _pyproject_mypy_entry(root: Path, apply: bool) -> Optional[Entry]:
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return None
    text = pyproject.read_text(encoding="utf-8")
    table = "[tool.mypy]"
    key = "exclude"
    if not _toml_has_table(text, table):
        if _toml_has_subtable_prefix(text, "[tool.mypy."):
            return _make_manual_entry(
                "mypy", "pyproject.toml",
                "Add exclude to your existing [tool.mypy] section (above [tool.mypy.*] blocks) in pyproject.toml. "
                "Suggested pattern: " + _regex_value_for_folders(FRAMEWORK_FOLDERS),
                root,
            )
        val = _regex_value_for_folders(FRAMEWORK_FOLDERS)
        block = "{table}\n{key} = {val}\n".format(table=table, key=key, val=val)
        if apply:
            _toml_append_block(pyproject, block)
            return _make_auto_entry("mypy", "pyproject.toml", "already-present", root)
        return _make_auto_entry("mypy", "pyproject.toml", "would-add", root)
    if not _toml_has_key_under_table(text, table, key):
        val = _regex_value_for_folders(FRAMEWORK_FOLDERS)
        if apply:
            _toml_append_key_under_table(pyproject, table, key, val)
            return _make_auto_entry("mypy", "pyproject.toml", "already-present", root)
        return _make_auto_entry("mypy", "pyproject.toml", "would-add", root)
    if _toml_key_contains_all_folders(text, table, key, FRAMEWORK_FOLDERS):
        return _make_auto_entry("mypy", "pyproject.toml", "already-present", root)
    return _make_manual_entry(
        "mypy", "pyproject.toml",
        "Merge the framework folders into [tool.mypy] exclude regex in pyproject.toml. "
        "Suggested pattern: " + _regex_value_for_folders(FRAMEWORK_FOLDERS),
        root,
    )


def _pyproject_pylint_entry(root: Path, apply: bool) -> Optional[Entry]:
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return None
    text = pyproject.read_text(encoding="utf-8")
    table = "[tool.pylint.main]"
    key = "ignore-paths"
    if not _toml_has_table(text, table):
        if _toml_has_subtable_prefix(text, "[tool.pylint."):
            return _make_manual_entry(
                "pylint", "pyproject.toml",
                "Add ignore-paths to your existing [tool.pylint.main] section in pyproject.toml: "
                + _pylint_regex_list_value(FRAMEWORK_FOLDERS),
                root,
            )
        val = _pylint_regex_list_value(FRAMEWORK_FOLDERS)
        block = "{table}\n{key} = {val}\n".format(table=table, key=key, val=val)
        if apply:
            _toml_append_block(pyproject, block)
            return _make_auto_entry("pylint", "pyproject.toml", "already-present", root)
        return _make_auto_entry("pylint", "pyproject.toml", "would-add", root)
    if not _toml_has_key_under_table(text, table, key):
        val = _pylint_regex_list_value(FRAMEWORK_FOLDERS)
        if apply:
            _toml_append_key_under_table(pyproject, table, key, val)
            return _make_auto_entry("pylint", "pyproject.toml", "already-present", root)
        return _make_auto_entry("pylint", "pyproject.toml", "would-add", root)
    if _toml_key_contains_all_folders(text, table, key, FRAMEWORK_FOLDERS):
        return _make_auto_entry("pylint", "pyproject.toml", "already-present", root)
    return _make_manual_entry(
        "pylint", "pyproject.toml",
        "Add the framework folders to [tool.pylint.main] ignore-paths in pyproject.toml: "
        + _pylint_regex_list_value(FRAMEWORK_FOLDERS),
        root,
    )


# ---------------------------------------------------------------------------
# rustfmt handler (rustfmt.toml — top-level ignore = [...])
# ---------------------------------------------------------------------------


def _rustfmt_entry(root: Path, apply: bool) -> Optional[Entry]:
    path = root / "rustfmt.toml"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    # top-level key: ignore = [...]
    key = "ignore"
    m = re.search(r'^\s*ignore\s*=', text, re.MULTILINE)
    if m:
        # Key present — check if all folders are listed in the key's value
        if _toml_top_key_contains_all_folders(text, key, FRAMEWORK_FOLDERS):
            return _make_auto_entry("rustfmt", "rustfmt.toml", "already-present", root)
        return _make_manual_entry(
            "rustfmt", "rustfmt.toml",
            "Add the framework folders to `ignore` in rustfmt.toml: "
            + _glob_list_toml_value(FRAMEWORK_FOLDERS),
            root,
        )
    # Key absent — safe to append
    val = _glob_list_toml_value(FRAMEWORK_FOLDERS)
    if apply:
        existing = text
        if existing and not existing.endswith("\n"):
            existing += "\n"
        _write_text_atomic(path, existing + "{0} = {1}\n".format(key, val))
        return _make_auto_entry("rustfmt", "rustfmt.toml", "already-present", root)
    return _make_auto_entry("rustfmt", "rustfmt.toml", "would-add", root)


# ---------------------------------------------------------------------------
# rubocop handler (external YAML → manual)
# ---------------------------------------------------------------------------


def _rubocop_entry(root: Path, apply: bool) -> Optional[Entry]:
    path = root / ".rubocop.yml"
    if not path.exists():
        return None
    return _make_manual_entry(
        "rubocop", ".rubocop.yml",
        "Add the framework folders to `AllCops/Exclude` in .rubocop.yml: "
        + ", ".join('"{0}/**/*"'.format(f) for f in FRAMEWORK_FOLDERS),
        root,
    )


# ---------------------------------------------------------------------------
# golangci-lint handler (external YAML → manual)
# ---------------------------------------------------------------------------


def _golangci_entry(root: Path, apply: bool) -> Optional[Entry]:
    path = root / ".golangci.yml"
    if not path.exists():
        return None
    return _make_manual_entry(
        "golangci-lint", ".golangci.yml",
        "Add the framework folders to `linters.exclusions.paths` (v2) or "
        "`issues.exclude-dirs` (v1) in .golangci.yml: "
        + ", ".join('"{0}"'.format(f) for f in FRAMEWORK_FOLDERS),
        root,
    )


# ---------------------------------------------------------------------------
# VS Code handler (.vscode/settings.json)
# ---------------------------------------------------------------------------


def _vscode_entry(root: Path, apply: bool) -> Optional[Entry]:
    vscode_dir = root / ".vscode"
    if not vscode_dir.is_dir():
        return None
    settings_path = vscode_dir / "settings.json"
    if not settings_path.exists():
        # Create the file on apply
        if apply:
            new_settings = _build_vscode_settings({}, FRAMEWORK_FOLDERS)
            _write_json_atomic(settings_path, new_settings)
            return _make_auto_entry("vscode", ".vscode/settings.json", "already-present", root)
        return _make_auto_entry("vscode", ".vscode/settings.json", "would-create", root)
    text = settings_path.read_text(encoding="utf-8")
    data, ok = _parse_jsonc(text)
    if not ok:
        return _make_manual_entry(
            "vscode", ".vscode/settings.json",
            "Cannot safely parse settings.json (JSONC/comments?). "
            "Add the framework folders to search.exclude and files.watcherExclude manually: "
            + ", ".join('"{0}/**": true'.format(f) for f in FRAMEWORK_FOLDERS),
            root,
        )
    # Check if all folders already present
    search_ex = data.get("search.exclude") or {}
    watcher_ex = data.get("files.watcherExclude") or {}
    missing_search = [f for f in FRAMEWORK_FOLDERS if "{0}/**".format(f) not in search_ex]
    missing_watcher = [f for f in FRAMEWORK_FOLDERS if "{0}/**".format(f) not in watcher_ex]
    if not missing_search and not missing_watcher:
        return _make_auto_entry("vscode", ".vscode/settings.json", "already-present", root)
    if apply:
        updated = _build_vscode_settings(data, FRAMEWORK_FOLDERS)
        _write_json_atomic(settings_path, updated)
        return _make_auto_entry("vscode", ".vscode/settings.json", "already-present", root)
    folders_to_add = list(dict.fromkeys(missing_search + missing_watcher))
    return {
        "tool": "vscode",
        "file": ".vscode/settings.json",
        "action": "auto",
        "status": "would-add",
        "lines": ["{0}/**".format(f) for f in folders_to_add],
        "preemptive": _any_preemptive(FRAMEWORK_FOLDERS, root),
    }


def _build_vscode_settings(existing: dict, folders: List[str]) -> dict:
    """Return a new settings dict with all existing keys plus framework folder excludes."""
    result = dict(existing)
    search_ex = dict(result.get("search.exclude") or {})
    watcher_ex = dict(result.get("files.watcherExclude") or {})
    for folder in folders:
        key = "{0}/**".format(folder)
        search_ex[key] = True
        watcher_ex[key] = True
    result["search.exclude"] = search_ex
    result["files.watcherExclude"] = watcher_ex
    return result


# ---------------------------------------------------------------------------
# JetBrains handler (.idea/ → manual)
# ---------------------------------------------------------------------------


def _jetbrains_entry(root: Path, apply: bool) -> Optional[Entry]:
    if not (root / ".idea").is_dir():
        return None
    return _make_manual_entry(
        "jetbrains", ".idea/",
        "Add the framework folders as Excluded in your JetBrains IDE: "
        "right-click each folder → Mark Directory as → Excluded. "
        "Folders: " + ", ".join(FRAMEWORK_FOLDERS),
        root,
    )


# ---------------------------------------------------------------------------
# Entry factory helpers
# ---------------------------------------------------------------------------


def _make_auto_entry(tool: str, file: str, status: str, root: Path) -> Entry:
    return {
        "tool": tool,
        "file": file,
        "action": "auto",
        "status": status,
        "lines": list(FRAMEWORK_FOLDERS),
        "preemptive": _any_preemptive(FRAMEWORK_FOLDERS, root),
    }


def _make_manual_entry(tool: str, file: str, instruction: str, root: Path) -> Entry:
    return {
        "tool": tool,
        "file": file,
        "action": "manual",
        "status": "pending-manual",
        "preemptive": _any_preemptive(FRAMEWORK_FOLDERS, root),
        "instruction": instruction,
    }


# ---------------------------------------------------------------------------
# Registry + main run_lint_ignore
# ---------------------------------------------------------------------------


# Each handler function has signature: (root: Path, apply: bool) -> Optional[Entry]
# Handlers that can return multiple entries return a list; the runner handles both.
# NOTE: ruff.toml is handled inside _pyproject_ruff_entry (which checks ruff.toml first).
_HANDLER_REGISTRY: List[Callable[[Path, bool], Any]] = [
    _prettier_entry,
    _eslint_entry,
    _markdownlint_entry,  # returns a list
    _flake8_entry,
    _biome_entry,
    _pyproject_ruff_entry,     # also handles ruff.toml via _ruff_toml_entry
    _pyproject_black_entry,
    _pyproject_isort_entry,
    _pyproject_mypy_entry,
    _pyproject_pylint_entry,
    _rustfmt_entry,
    _rubocop_entry,
    _golangci_entry,
    _vscode_entry,
    _jetbrains_entry,
]


def run_lint_ignore(
    install_root: str,
    devforge_dir: str,
    apply: bool = False,
) -> dict:
    """Main entry point for the lint-ignore verb.

    Scans install_root for linter configs, computes what needs to change,
    and (when apply=True) writes the changes atomically.

    Returns a report dict:
    {
      "entries": [...],   # per-tool entries (see module docstring)
      "summary": {
        "auto_count": int,
        "manual_count": int,
        "already_present_count": int,
        "applied_count": int,
      }
    }
    """
    root = Path(install_root)

    def _run_handlers(do_apply: bool) -> List[Entry]:
        results: List[Entry] = []
        for handler in _HANDLER_REGISTRY:
            try:
                result = handler(root, do_apply)
            except Exception as exc:
                results.append({
                    "tool": getattr(handler, "__name__", "unknown"),
                    "file": "n/a",
                    "action": "manual",
                    "status": "error",
                    "preemptive": False,
                    "instruction": "Handler error: {0}".format(exc),
                })
                continue
            if result is None:
                continue
            if isinstance(result, list):
                results.extend(result)
            else:
                results.append(result)
        return results

    if apply:
        # Dry-run first to capture pre-apply status for accurate applied_count.
        dry_entries = _run_handlers(False)
        # Count entries that will actually change (would-add or would-create).
        _PENDING_STATUSES = {"would-add", "would-create"}
        applied_count = sum(
            1 for e in dry_entries
            if e.get("action") == "auto" and e.get("status") in _PENDING_STATUSES
        )
        # Now run with apply=True to write changes.
        entries = _run_handlers(True)
        already_present_count = sum(
            1 for e in entries if e.get("status") == "already-present"
        )
    else:
        entries = _run_handlers(False)
        applied_count = 0
        already_present_count = sum(
            1 for e in entries if e.get("status") == "already-present"
        )

    auto_count = sum(1 for e in entries if e.get("action") == "auto")
    manual_count = sum(1 for e in entries if e.get("action") == "manual")

    return {
        "entries": entries,
        "summary": {
            "auto_count": auto_count,
            "manual_count": manual_count,
            "already_present_count": already_present_count,
            "applied_count": applied_count,
        },
    }
