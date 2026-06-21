"""Detects a package's build manifest and emits a default scripts dict.

`extract-package-scripts` is read-only — it never mutates state. The
LLM is expected to pipe each entry back through `add-package-script`
to record the discovered commands explicitly. The module owns the
detection priority registry (`_MANIFEST_PRIORITY`) and the per-
ecosystem extractors; the CLI layer wires it up.

Cross-cutting utilities (`_die` for stderr error formatting,
`_validate_string` for input validation) are imported from sibling
leaf modules so the error-reporting style stays consistent across
all subcommands. This module never reads or writes the helper's
state file.

Stdlib only. Targets Python 3.8+.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ._state import _die, _info
from ._validation import _validate_string


# Manifest detection priority — first match wins (per Plan Patch 8).
#
# Ruby ships TWO recognized manifests: `Gemfile` (dependency lock) and
# `Rakefile` (task definitions). Either one is sufficient to identify
# the package as Ruby. They're listed adjacently so detection priority
# stays deterministic; the extractor merges signals from both when both
# exist (see `_scripts_from_ruby`).
_MANIFEST_PRIORITY: Tuple[Tuple[str, str], ...] = (
    ("js_ts", "package.json"),
    ("rust", "Cargo.toml"),
    ("python", "pyproject.toml"),
    ("go", "go.mod"),
    ("maven", "pom.xml"),
    ("gradle", "build.gradle"),
    ("gradle_kts", "build.gradle.kts"),
    ("ruby", "Gemfile"),
    ("ruby", "Rakefile"),
    ("php", "composer.json"),
)


def _detect_csproj(path: Path) -> Optional[str]:
    """Return the first `*.csproj` file in `path`, or None."""
    try:
        for entry in sorted(path.iterdir()):
            if entry.is_file() and entry.name.endswith(".csproj"):
                return entry.name
    except OSError:
        return None
    return None


def _scripts_from_package_json(path: Path) -> Dict[str, str]:
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    scripts = data.get("scripts") if isinstance(data, dict) else None
    if not isinstance(scripts, dict):
        return {}
    out: Dict[str, str] = {}
    for k, v in scripts.items():
        if isinstance(k, str) and isinstance(v, str):
            out[k] = v
    return out


_PYPROJECT_SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")
# `key = "value"` or `key = 'value'`. Bare keys only — quoted keys (rare
# in scripts sections) are skipped. The regex deliberately does not
# handle multi-line values, inline arrays, or other TOML edge cases;
# real-world `[project.scripts]` and `[tool.poetry.scripts]` sections
# use this single-line `key = "value"` shape.
_PYPROJECT_KV_RE = re.compile(
    r"""^\s*([A-Za-z_][A-Za-z0-9_-]*)\s*=\s*(?:"([^"]*)"|'([^']*)')\s*$"""
)


def _scripts_from_pyproject_toml(path: Path) -> Dict[str, str]:
    """Best-effort static parse of `[project.scripts]` / `[tool.poetry.scripts]`.

    Stdlib 3.8/3.9 has no TOML support; `tomllib` is 3.11+. Real-world
    pyproject.toml `[project.scripts]` and `[tool.poetry.scripts]`
    sections use the `key = "value"` pattern which regex-parses
    cleanly. Multi-line values, inline arrays, and other TOML edge
    cases are not handled.

    Returns the merged scripts dict (later sections override earlier).
    Returns `{}` if neither section is present or the file is
    unreadable — the caller falls back to the stack defaults.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    out: Dict[str, str] = {}
    in_scripts_section = False
    for raw_line in text.splitlines():
        # Strip line-trailing comments. Skip empty / pure-comment lines.
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        section_match = _PYPROJECT_SECTION_RE.match(line)
        if section_match:
            section_name = section_match.group(1).strip()
            in_scripts_section = section_name in (
                "project.scripts", "tool.poetry.scripts",
            )
            continue
        if not in_scripts_section:
            continue
        kv_match = _PYPROJECT_KV_RE.match(line)
        if kv_match is None:
            continue
        key = kv_match.group(1)
        value = kv_match.group(2) if kv_match.group(2) is not None else kv_match.group(3)
        out[key] = value
    return out


# Top-level Rake task: `task :name`, `task "name"`, or `task 'name'`.
# Matches optional whitespace + `task` keyword + name token, with no
# attempt to parse dependencies (`task :foo => :bar`) — we still
# extract the head task name in that case because we anchor on the
# first whitespace token after `task`.
_RAKEFILE_TASK_RE = re.compile(
    r"""^\s*task\s+(?::([A-Za-z_][A-Za-z0-9_]*)|"([^"]+)"|'([^']+)')"""
)


def _scripts_from_rakefile(path: Path) -> Dict[str, str]:
    """Static-parse top-level `task :name` declarations from a Rakefile.

    Does NOT shell out to `rake -T`; static parsing keeps the helper
    side-effect-free and avoids requiring a Ruby toolchain. Each
    discovered task is mapped to `bundle exec rake <task-name>`.

    Returns `{}` if the file is unreadable or no tasks match.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    out: Dict[str, str] = {}
    for raw_line in text.splitlines():
        match = _RAKEFILE_TASK_RE.match(raw_line)
        if match is None:
            continue
        name = match.group(1) or match.group(2) or match.group(3)
        if name:
            out[name] = "bundle exec rake {0}".format(name)
    return out


def _scripts_from_ruby(pkg_dir: Path) -> Dict[str, str]:
    """Merge Gemfile defaults + Rakefile-detected tasks for Ruby packages.

    Always includes `bundle install` and `bundle exec` defaults — these
    are useful regardless of Rakefile presence. Rakefile-detected tasks
    are layered on top so they override only when names collide
    (defaults are reserved names; collisions are rare).
    """
    out: Dict[str, str] = {
        "install": "bundle install",
        "exec": "bundle exec",
    }
    rakefile = pkg_dir / "Rakefile"
    if rakefile.is_file():
        out.update(_scripts_from_rakefile(rakefile))
    return out


def _scripts_from_composer_json(path: Path) -> Dict[str, str]:
    # composer.json scripts may be either str or list[str]; we only
    # accept the str form for round-trip safety. List-form scripts are
    # rare and the LLM can register them manually if needed.
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    scripts = data.get("scripts") if isinstance(data, dict) else None
    if not isinstance(scripts, dict):
        return {}
    out: Dict[str, str] = {}
    for k, v in scripts.items():
        if isinstance(k, str) and isinstance(v, str):
            out[k] = v
    return out


def cmd_extract_package_scripts(args: argparse.Namespace) -> int:
    """Detect a package's manifest and emit a scripts dict to stdout.

    Does NOT mutate state. The LLM is expected to feed each entry back
    through `add-package-script`.
    """
    try:
        _validate_string(args.path, "extract-package-scripts --path")
    except ValueError as err:
        return _die(str(err))
    pkg_dir = Path(args.path)
    if not pkg_dir.is_dir():
        return _die(
            "extract-package-scripts: path {0!r} is not a directory".format(
                args.path
            )
        )

    detected: List[Tuple[str, str]] = []
    for kind, manifest_name in _MANIFEST_PRIORITY:
        if (pkg_dir / manifest_name).is_file():
            detected.append((kind, manifest_name))
    csproj = _detect_csproj(pkg_dir)
    if csproj:
        detected.append(("dotnet", csproj))

    if not detected:
        manifests_checked = [m for _, m in _MANIFEST_PRIORITY] + ["*.csproj"]
        return _die(
            "extract-package-scripts: no manifest found at {0!r} (checked "
            "{1})".format(args.path, ", ".join(manifests_checked))
        )

    primary_kind, primary_name = detected[0]
    # Same-kind co-manifests (e.g., Ruby's Gemfile + Rakefile) are NOT
    # surprising and should not emit a "multiple manifests" warning.
    # Only warn when a different language's manifest also matched.
    cross_kind_others = [
        (k, m) for k, m in detected[1:] if k != primary_kind
    ]
    if cross_kind_others:
        secondary = ", ".join(
            "{0} ({1})".format(m, k) for k, m in cross_kind_others
        )
        _info(
            "extract-package-scripts: multiple manifests detected at {0}; "
            "using {1} (also found: {2})".format(
                args.path, primary_name, secondary
            )
        )

    scripts: Dict[str, str]
    if primary_kind == "js_ts":
        scripts = _scripts_from_package_json(pkg_dir / primary_name)
    elif primary_kind == "rust":
        scripts = {
            "build": "cargo build",
            "test": "cargo test",
            "run": "cargo run",
            "fmt": "cargo fmt",
            "clippy": "cargo clippy",
        }
    elif primary_kind == "python":
        # Best-effort static parse of `[project.scripts]` and
        # `[tool.poetry.scripts]`. Stdlib 3.8/3.9 has no TOML parser;
        # the regex-based extractor handles the common single-line
        # `key = "value"` shape (see `_scripts_from_pyproject_toml`).
        # Empty result -> fall back to stack defaults so the LLM still
        # has a starting point.
        scripts = _scripts_from_pyproject_toml(pkg_dir / primary_name)
        if not scripts:
            scripts = {
                "install": "pip install -e .",
                "test": "pytest",
            }
    elif primary_kind == "go":
        scripts = {
            "build": "go build ./...",
            "test": "go test ./...",
            "run": "go run ./...",
            "vet": "go vet ./...",
        }
    elif primary_kind == "maven":
        scripts = {
            "compile": "mvn compile",
            "test": "mvn test",
            "package": "mvn package",
            "install": "mvn install",
        }
    elif primary_kind in ("gradle", "gradle_kts"):
        scripts = {
            "build": "./gradlew build",
            "test": "./gradlew test",
            "assemble": "./gradlew assemble",
        }
    elif primary_kind == "dotnet":
        scripts = {
            "build": "dotnet build",
            "test": "dotnet test",
            "run": "dotnet run",
        }
    elif primary_kind == "ruby":
        # Merge Gemfile defaults with any Rakefile-detected tasks.
        # `_scripts_from_ruby` checks for Rakefile presence itself, so
        # the same path works whether Gemfile, Rakefile, or both are
        # the detected manifest.
        scripts = _scripts_from_ruby(pkg_dir)
    elif primary_kind == "php":
        scripts = _scripts_from_composer_json(pkg_dir / primary_name)
    else:
        # Unreachable — `_MANIFEST_PRIORITY` and `_detect_csproj` are
        # the only sources of `primary_kind`.
        return _die(
            "extract-package-scripts: internal error — unknown manifest "
            "kind {0!r}".format(primary_kind),
            code=1,
        )

    sys.stdout.write(json.dumps(scripts, sort_keys=True) + "\n")
    return 0
