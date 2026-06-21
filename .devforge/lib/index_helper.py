"""index_helper — language-agnostic workspace structural index for /generate-docs.

Reads `.devforge/init.yaml` (the bootstrap state file produced by
/init-forge) and builds two artifacts:

- `<DEVFORGE_DIR>/index.json` — machine-readable, per-package structural
  data: file listings (capped at 500), manifest scripts + dependencies.
- `<install_root>/docs/structure.md` — human-readable workspace map.
  In wrapper mode, install_root != project_root; structure.md lives at
  install_root (alongside .devforge/) per the wrapper-mode artifact
  convention from CLAUDE.md.
  rendered from the same data.

NO source-derived data (NO exports, NO type extraction, NO import
graph). The LLM contributes those during /generate-docs. Per Principle
5 ("ecosystem-agnostic"): per-language source extraction is an
explicit non-goal — the cost of building per-language extractors that
stay correct across the long tail of edge cases isn't worth the value
the LLM already provides.

Architecture:

- Single subcommand: `build-index`. No flags. Reads `init.yaml`,
  writes both artifacts atomically.
- Manifest detection by filename match against a bounded set
  (`_MANIFEST_REGISTRY`). The first matching manifest wins; remainder
  are surfaced via a stderr warning but do not block the run.
- Manifest parsing is best-effort. Unsupported / malformed manifests
  produce `manifest_parse_skipped: true` for that package, do NOT
  fail the whole `build-index` run, and emit a stderr warning.
- File listings are capped at 10000 per package; `files_truncated: true`
  is set when the cap is hit. A small set of common build-output dirs
  is hard-skipped (node_modules, dist, build, target, .git) plus any
  hidden dir starting with `.`.
- Atomic writes (tempfile.mkstemp + os.replace) for both artifacts.

Stdlib only. No third-party dependencies. Targets Python 3.8+.
"""

import argparse
import datetime
import json
import os
import re
import sys
import tempfile
from pathlib import Path

# Resolve siblings as importable when invoked as `python3 index_helper.py`.
_LIB_DIR = str(Path(__file__).resolve().parent)
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

import init_helper  # noqa: E402

# Output filenames.
INDEX_FILE_NAME = "index.json"
INDEX_VERSION = 1
STRUCTURE_DOC_REL = Path("docs") / "structure.md"

# Hard-skip directory names during the file walk. Mirrors the build /
# vendor cache dirs from `init_helper.NESTED_GIT_SKIP` plus a few extras
# common in JS/Java/.NET ecosystems.
_FILE_WALK_SKIP_DIRS = {
    "node_modules",
    "dist",
    "build",
    "target",
    "out",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    ".idea",
    ".vscode",
    ".next",
    ".nuxt",
    ".turbo",
    "bin",
    "obj",
}

# Maximum files listed per package. Above this, `files_truncated: true`.
# Bumped 500 → 10000 (2026-05-07): Plan F doc generation reads index.json
# as the canonical per-concern file list. Real Vue+TS monorepos hit the old
# 500 cap on app-level packages (testForge20 app + foo both
# truncated at 500), making concerns past the cut invisible to /generate-docs.
# 10000 covers any realistic monorepo package; the Linux kernel (75K files
# total) is the only structurally larger codebase and its packages still fit.
_MAX_FILES_PER_PACKAGE = 10000

# Manifest detection registry. First match wins per package. Includes the
# bounded set documented in the brief; `*.csproj` is a glob (handled
# specially in `_detect_manifest`).
_MANIFEST_REGISTRY = (
    "package.json",
    "Cargo.toml",
    "pyproject.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "composer.json",
    "Gemfile",
    "requirements.txt",
)


# ---------------------------------------------------------------------------
# Path resolution.
# ---------------------------------------------------------------------------


def _devforge_dir():
    """Resolve the `.devforge/` directory at call time.

    Honors `DEVFORGE_DIR` when set; otherwise derives from this file's
    location: `<install>/.devforge/lib/index_helper.py` -> parent is
    `<install>/.devforge/`.
    """
    env_dir = os.environ.get("DEVFORGE_DIR")
    if env_dir:
        return Path(env_dir)
    return Path(__file__).resolve().parent.parent


def _project_root_from_init(init_state):
    """Resolve the project root from init.yaml.

    `project_root` in `init.yaml` is either `.` (standalone mode — root
    is the parent of `.devforge/`) or a relative path inside the
    install root (wrapper mode). We resolve absolute on disk so file
    walks have a known base.
    """
    install_root = _devforge_dir().parent
    raw = init_state.get("project_root")
    if raw is None or raw == "" or raw == ".":
        return install_root
    return install_root / raw


# ---------------------------------------------------------------------------
# Filesystem walker.
# ---------------------------------------------------------------------------


def _list_package_files(pkg_dir):
    """Return sorted list of relative file paths under `pkg_dir`.

    Skips directories in `_FILE_WALK_SKIP_DIRS` and any directory whose
    name starts with `.`. Returns the file paths relative to `pkg_dir`,
    POSIX-style, sorted lexicographically. Caps at `_MAX_FILES_PER_PACKAGE`;
    the second return value is True when truncation occurred.
    """
    files = []
    truncated = False
    for root, dirs, filenames in os.walk(str(pkg_dir)):
        # Mutate `dirs` in place so os.walk skips them. Filter hidden +
        # known-skip dirs.
        dirs[:] = [
            d for d in dirs
            if not d.startswith(".") and d not in _FILE_WALK_SKIP_DIRS
        ]
        # Sort for deterministic walk order.
        dirs.sort()
        for fname in sorted(filenames):
            if fname.startswith("."):
                # Hidden files (e.g., .DS_Store, .gitignore) are excluded
                # to keep the index focused on source files.
                continue
            full = Path(root) / fname
            try:
                rel = full.relative_to(pkg_dir)
            except ValueError:
                # Defensive: os.walk shouldn't yield anything outside
                # `pkg_dir`, but if it ever does, skip rather than crash.
                continue
            files.append(rel.as_posix())
            if len(files) >= _MAX_FILES_PER_PACKAGE:
                truncated = True
                return files, truncated
    return files, truncated


# ---------------------------------------------------------------------------
# Manifest detection.
# ---------------------------------------------------------------------------


def _detect_manifest(pkg_dir):
    """Return the manifest filename in `pkg_dir`, or None if absent.

    Uses `_MANIFEST_REGISTRY` for fixed names and a glob pass for
    `*.csproj` (handled separately because it's the only ecosystem
    with a wildcard manifest name). First-match-wins ordering matches
    the registry.
    """
    for name in _MANIFEST_REGISTRY:
        candidate = pkg_dir / name
        if candidate.is_file():
            return name
    # Glob pass for *.csproj (sorted alphabetically — deterministic).
    try:
        for entry in sorted(pkg_dir.iterdir()):
            if entry.is_file() and entry.name.endswith(".csproj"):
                return entry.name
    except OSError:
        pass
    return None


# ---------------------------------------------------------------------------
# Manifest parsers — each returns (scripts_dict, deps_list, parse_ok).
# parse_ok=False means the manifest was found but couldn't be parsed
# cleanly; the caller sets `manifest_parse_skipped: true`.
# ---------------------------------------------------------------------------


def _parse_package_json(path):
    """Parse package.json: scripts, dependencies + devDependencies.

    Returns (scripts, deps, parse_ok). On JSON-decode failure or wrong
    top-level type, parse_ok=False so the caller can flag it.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}, [], False
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}, [], False
    if not isinstance(data, dict):
        return {}, [], False
    scripts = {}
    raw_scripts = data.get("scripts")
    if isinstance(raw_scripts, dict):
        for k, v in raw_scripts.items():
            if isinstance(k, str) and isinstance(v, str):
                scripts[k] = v
    deps = []
    for key in ("dependencies", "devDependencies"):
        block = data.get(key)
        if isinstance(block, dict):
            for name, version in block.items():
                if isinstance(name, str) and isinstance(version, str):
                    deps.append({"name": name, "version": version})
    return scripts, deps, True


def _parse_composer_json(path):
    """Parse composer.json: scripts (string-form only), require + require-dev.

    composer.json scripts may also be lists; we only accept the string
    form for round-trip safety. List-form scripts are rare and the LLM
    can register them manually if needed.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}, [], False
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}, [], False
    if not isinstance(data, dict):
        return {}, [], False
    scripts = {}
    raw_scripts = data.get("scripts")
    if isinstance(raw_scripts, dict):
        for k, v in raw_scripts.items():
            if isinstance(k, str) and isinstance(v, str):
                scripts[k] = v
    deps = []
    for key in ("require", "require-dev"):
        block = data.get(key)
        if isinstance(block, dict):
            for name, version in block.items():
                if isinstance(name, str) and isinstance(version, str):
                    deps.append({"name": name, "version": version})
    return scripts, deps, True


# Regex shared by Cargo / pyproject parsers. Anchors on a single-line
# `name = "value"` shape — multi-line + inline-table forms are deferred
# to a future enhancement.
_TOML_SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")
_TOML_KV_STR_RE = re.compile(
    r"""^\s*([A-Za-z_][A-Za-z0-9_-]*)\s*=\s*(?:"([^"]*)"|'([^']*)')\s*$"""
)
# `name = { version = "1.0", ... }` — capture the version, ignore the rest.
_TOML_KV_TABLE_RE = re.compile(
    r"""^\s*([A-Za-z_][A-Za-z0-9_-]*)\s*=\s*\{[^}]*?version\s*=\s*"([^"]*)"[^}]*?\}\s*$"""
)


def _parse_cargo_toml(path):
    """Parse Cargo.toml: no scripts, [dependencies] + [dev-dependencies].

    Targets the common `name = "1.0"` and `name = { version = "1.0" }`
    shapes in `[dependencies]` and `[dev-dependencies]` sections.
    Workspace tables and complex feature specs aren't fully covered;
    they fall through silently (manifest_parse_skipped stays false).
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}, [], False
    deps = []
    in_deps_section = False
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        section_match = _TOML_SECTION_RE.match(line)
        if section_match:
            section_name = section_match.group(1).strip()
            in_deps_section = section_name in (
                "dependencies", "dev-dependencies",
            )
            continue
        if not in_deps_section:
            continue
        m = _TOML_KV_STR_RE.match(line)
        if m:
            name = m.group(1)
            version = m.group(2) if m.group(2) is not None else m.group(3)
            deps.append({"name": name, "version": version})
            continue
        m = _TOML_KV_TABLE_RE.match(line)
        if m:
            deps.append({"name": m.group(1), "version": m.group(2)})
            continue
    return {}, deps, True


# PEP 508 spec extractor — captures any double- or single-quoted token
# inside a TOML array body. Used by `_parse_pyproject_toml` for
# `[project] dependencies = [...]`. Defined as `re.compile` rather than
# inline because PEP 8 / readability — the raw string with mixed quote
# delimiters confuses some readers and trips literal-string parsing
# when adjacent to triple-quoted blocks.
_PEP621_QUOTED_TOKEN_RE = re.compile(r'"([^"]*)"' + r"|'([^']*)'")


def _parse_pyproject_toml(path):
    """Parse pyproject.toml: poetry / PEP 621 deps + scripts.

    Recognized sections:
      [tool.poetry.dependencies]      poetry deps
      [tool.poetry.dev-dependencies]  poetry dev deps
      [project.dependencies]          PEP 621 deps (list, not table)
      [tool.poetry.scripts]           poetry scripts
      [project.scripts]               PEP 621 scripts

    PEP 621 `[project.dependencies]` is a TOML array of strings, not a
    table — handled separately. Other forms use the table-of-strings
    pattern.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}, [], False
    scripts = {}
    deps = []
    section = None
    pep621_deps_raw = []
    pep621_in_deps_array = False
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        section_match = _TOML_SECTION_RE.match(line)
        if section_match:
            section = section_match.group(1).strip()
            pep621_in_deps_array = (section == "project")
            continue
        # PEP 621: `dependencies = [...]` inside `[project]`.
        if pep621_in_deps_array and line.lstrip().startswith("dependencies"):
            # Single-line: `dependencies = ["foo>=1", "bar==2"]`.
            inline_match = re.match(
                r"""^\s*dependencies\s*=\s*\[(.*)\]\s*$""", line,
            )
            if inline_match:
                body = inline_match.group(1)
                for raw in re.findall(_PEP621_QUOTED_TOKEN_RE, body):
                    spec = raw[0] or raw[1]
                    if spec:
                        pep621_deps_raw.append(spec)
                continue
            # Multi-line: `dependencies = [` + items + `]`. Track via
            # a sentinel that captures every quoted token until `]`.
            multiline_match = re.match(
                r"""^\s*dependencies\s*=\s*\[\s*$""", line,
            )
            if multiline_match:
                section = "__pep621_deps_multiline__"
                continue
        if section == "__pep621_deps_multiline__":
            if line.strip().startswith("]"):
                section = "project"
                continue
            for raw in re.findall(_PEP621_QUOTED_TOKEN_RE, line):
                spec = raw[0] or raw[1]
                if spec:
                    pep621_deps_raw.append(spec)
            continue
        if section in ("tool.poetry.scripts", "project.scripts"):
            m = _TOML_KV_STR_RE.match(line)
            if m:
                key = m.group(1)
                val = m.group(2) if m.group(2) is not None else m.group(3)
                scripts[key] = val
            continue
        if section in ("tool.poetry.dependencies", "tool.poetry.dev-dependencies"):
            m = _TOML_KV_STR_RE.match(line)
            if m:
                name = m.group(1)
                version = m.group(2) if m.group(2) is not None else m.group(3)
                deps.append({"name": name, "version": version})
                continue
            m = _TOML_KV_TABLE_RE.match(line)
            if m:
                deps.append({"name": m.group(1), "version": m.group(2)})
                continue
    # Convert PEP 621 raw specs into name+version pairs.
    for spec in pep621_deps_raw:
        # PEP 508 spec: extract name (first identifier) and the version
        # constraint (everything after the first comparator). This is a
        # best-effort split — full PEP 508 grammar is out of scope.
        m = re.match(r"^\s*([A-Za-z0-9._-]+)\s*(.*?)\s*$", spec)
        if m:
            deps.append({"name": m.group(1), "version": m.group(2) or ""})
    return scripts, deps, True


_GO_REQUIRE_LINE_RE = re.compile(
    r"""^\s*([A-Za-z0-9._/~-]+)\s+(v[\w.+-]+)\s*(?://.*)?$"""
)


def _parse_go_mod(path):
    """Parse go.mod: deps from `require (...)` block + single-line `require`.

    No scripts. `require` lines may be in a block (`require ( ... )`) or
    standalone (`require module/path v1.2.3`). Replace / exclude / retract
    directives are skipped.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}, [], False
    deps = []
    in_block = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        if in_block:
            if stripped == ")":
                in_block = False
                continue
            m = _GO_REQUIRE_LINE_RE.match(line)
            if m:
                deps.append({"name": m.group(1), "version": m.group(2)})
            continue
        if stripped.startswith("require ("):
            in_block = True
            continue
        if stripped.startswith("require "):
            # Single-line require: `require module/path v1.2.3`.
            rest = stripped[len("require "):]
            m = _GO_REQUIRE_LINE_RE.match(rest)
            if m:
                deps.append({"name": m.group(1), "version": m.group(2)})
            continue
    return {}, deps, True


_PIP_REQ_LINE_RE = re.compile(
    r"^\s*([A-Za-z0-9._-]+)\s*([<>=!~].*)?\s*$"
)


def _parse_requirements_txt(path):
    """Parse requirements.txt: name + optional version-constraint per line.

    Skips comments, blank lines, and `-r ...` / `-e ...` directives.
    Inline comments after the spec are stripped.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}, [], False
    deps = []
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("-"):
            # Skip pip-style directives (`-r other.txt`, `-e .`, etc.).
            continue
        m = _PIP_REQ_LINE_RE.match(line)
        if not m:
            continue
        name = m.group(1)
        version = (m.group(2) or "").strip()
        deps.append({"name": name, "version": version})
    return {}, deps, True


_POM_DEP_RE = re.compile(
    r"<dependency>\s*"
    r"<groupId>([^<]+)</groupId>\s*"
    r"<artifactId>([^<]+)</artifactId>\s*"
    r"(?:<version>([^<]+)</version>\s*)?"
    r".*?"
    r"</dependency>",
    re.DOTALL,
)


def _parse_pom_xml(path):
    """Parse pom.xml: <dependency> elements.

    Regex-based extraction of the common `<dependency><groupId>...</groupId>
    <artifactId>...</artifactId><version>...</version></dependency>`
    shape. Property substitution (`${project.version}`) is preserved
    verbatim. Complex parent / dependencyManagement / profile blocks
    are not fully covered.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}, [], False
    deps = []
    for m in _POM_DEP_RE.finditer(text):
        group_id = m.group(1).strip()
        artifact_id = m.group(2).strip()
        version = (m.group(3) or "").strip()
        deps.append({
            "name": "{0}:{1}".format(group_id, artifact_id),
            "version": version,
        })
    return {}, deps, True


_GRADLE_DEP_RE = re.compile(
    r"""^\s*(?:implementation|api|compileOnly|runtimeOnly|testImplementation|"""
    r"""testRuntimeOnly|compile|testCompile|annotationProcessor)"""
    r"""\s*[\(]?\s*(?:["']([^"']+)["']|group\s*:\s*["']([^"']+)["']\s*,"""
    r"""\s*name\s*:\s*["']([^"']+)["']\s*(?:,\s*version\s*:\s*["']([^"']*)["'])?)"""
)


def _parse_build_gradle(path):
    """Parse build.gradle / build.gradle.kts: dependency declarations.

    Recognizes the common Groovy/Kotlin DSL forms:
      implementation 'com.example:lib:1.0'
      implementation group: 'com.example', name: 'lib', version: '1.0'
    plus the api / compileOnly / testImplementation variants.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}, [], False
    deps = []
    for raw_line in text.splitlines():
        m = _GRADLE_DEP_RE.match(raw_line)
        if not m:
            continue
        coord = m.group(1)
        if coord:
            # `group:artifact:version` form.
            parts = coord.split(":")
            if len(parts) >= 2:
                name = "{0}:{1}".format(parts[0], parts[1])
                version = parts[2] if len(parts) >= 3 else ""
                deps.append({"name": name, "version": version})
            continue
        # Map form: group / name / version captured separately.
        group = m.group(2)
        name = m.group(3)
        version = m.group(4) or ""
        if group and name:
            deps.append({
                "name": "{0}:{1}".format(group, name),
                "version": version,
            })
    return {}, deps, True


_CSPROJ_PKG_RE = re.compile(
    r"""<PackageReference\s+Include=["']([^"']+)["']\s+Version=["']([^"']*)["']"""
)


def _parse_csproj(path):
    """Parse *.csproj: <PackageReference Include="..." Version="..."/>.

    Single-line attribute form (the dominant shape from `dotnet add
    package`). Multi-line attribute forms aren't covered; complex
    project import + condition / Choose blocks are out of scope.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}, [], False
    deps = []
    for m in _CSPROJ_PKG_RE.finditer(text):
        deps.append({"name": m.group(1), "version": m.group(2)})
    return {}, deps, True


_GEMFILE_GEM_RE = re.compile(
    r"""^\s*gem\s+["']([^"']+)["']\s*(?:,\s*["']([^"']+)["'])?"""
)


def _parse_gemfile(path):
    """Parse Gemfile: `gem "name"` and `gem "name", "version"`.

    Source / git / group blocks are skipped silently. The version slot
    captures only the second positional string argument; named-arg
    forms (`gem "name", git: "..."`) leave version empty.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}, [], False
    deps = []
    for raw_line in text.splitlines():
        # Strip line comments before regex.
        line = raw_line.split("#", 1)[0]
        m = _GEMFILE_GEM_RE.match(line)
        if not m:
            continue
        name = m.group(1)
        version = m.group(2) or ""
        deps.append({"name": name, "version": version})
    return {}, deps, True


# Manifest -> parser dispatch. Names match `_MANIFEST_REGISTRY` plus
# `*.csproj` keyed under "csproj" (special-cased in `_parse_manifest`).
_MANIFEST_PARSERS = {
    "package.json": _parse_package_json,
    "Cargo.toml": _parse_cargo_toml,
    "pyproject.toml": _parse_pyproject_toml,
    "go.mod": _parse_go_mod,
    "pom.xml": _parse_pom_xml,
    "build.gradle": _parse_build_gradle,
    "build.gradle.kts": _parse_build_gradle,
    "composer.json": _parse_composer_json,
    "Gemfile": _parse_gemfile,
    "requirements.txt": _parse_requirements_txt,
}


def _parse_manifest(pkg_dir, manifest_name):
    """Dispatch to the right parser for `manifest_name`.

    Returns (scripts, deps, parse_ok). Special-cases `*.csproj`
    because the registry uses fixed names but .NET is glob-detected.
    """
    if manifest_name and manifest_name.endswith(".csproj"):
        return _parse_csproj(pkg_dir / manifest_name)
    parser = _MANIFEST_PARSERS.get(manifest_name)
    if parser is None:
        return {}, [], False
    return parser(pkg_dir / manifest_name)


# ---------------------------------------------------------------------------
# Build-index orchestrator.
# ---------------------------------------------------------------------------


def _utc_iso_now():
    """Return the current UTC time as an ISO 8601 'Z' string."""
    # `datetime.datetime.utcnow()` is naive; format explicitly so the
    # output is always `YYYY-MM-DDTHH:MM:SSZ` regardless of locale.
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_package_record(pkg_path, pkg_dir):
    """Compose the per-package index record.

    `pkg_path` is the relative path from the project root (matches the
    `init.yaml` `packages_detected[].path` value). `pkg_dir` is the
    absolute filesystem path.

    No `language` field: init-forge today doesn't capture per-package
    language, and /generate-docs's Phase 1 does its own per-package
    language detection from manifest + tsconfig signals. Adding a
    placeholder field here was YAGNI — removed.
    """
    record = {
        "name": Path(pkg_path).name or pkg_path,
        "manifest_file": None,
        "manifest_parse_skipped": False,
        "scripts": {},
        "manifest_deps": [],
        "files": [],
        "files_truncated": False,
    }
    if not pkg_dir.is_dir():
        # Defensive: if init.yaml referenced a path that no longer
        # exists on disk, surface as a parse-skip rather than crashing.
        record["manifest_parse_skipped"] = True
        sys.stderr.write(
            "index_helper: package path {0!r} does not exist; skipping\n".format(
                str(pkg_dir)
            )
        )
        return record
    manifest_name = _detect_manifest(pkg_dir)
    if manifest_name is not None:
        record["manifest_file"] = manifest_name
        scripts, deps, parse_ok = _parse_manifest(pkg_dir, manifest_name)
        if parse_ok:
            record["scripts"] = dict(scripts)
            record["manifest_deps"] = list(deps)
        else:
            record["manifest_parse_skipped"] = True
            sys.stderr.write(
                "index_helper: failed to parse manifest {0} at {1}; "
                "scripts/deps left empty\n".format(manifest_name, pkg_path)
            )
    files, truncated = _list_package_files(pkg_dir)
    record["files"] = files
    record["files_truncated"] = truncated
    return record


def _render_structure_md(index, generated_at):
    """Render the human-readable workspace map as Markdown.

    Pure function so tests can pin the output shape without going
    through the full build-index path. Format (locked):

        # Workspace Structure

        Generated by `index_helper build-index` on <ISO date>.

        ## Packages

        | Package | Manifest | Files | Scripts | Manifest deps |
        |---|---|---|---|---|
        | <path> | <manifest|none> | <count> | <count> | <count> |
    """
    lines = []
    lines.append("# Workspace Structure")
    lines.append("")
    lines.append(
        "Generated by `index_helper build-index` on {0}.".format(generated_at)
    )
    lines.append("")
    lines.append("## Packages")
    lines.append("")
    lines.append(
        "| Package | Manifest | Files | Scripts | Manifest deps |"
    )
    lines.append("|---|---|---|---|---|")
    packages = index.get("packages", {})
    for pkg_path in sorted(packages.keys()):
        rec = packages[pkg_path]
        manifest_cell = rec.get("manifest_file") or "none"
        file_count = len(rec.get("files", []))
        if rec.get("files_truncated"):
            file_count_cell = "{0}+".format(file_count)
        else:
            file_count_cell = str(file_count)
        lines.append(
            "| {0} | {1} | {2} | {3} | {4} |".format(
                pkg_path,
                manifest_cell,
                file_count_cell,
                len(rec.get("scripts", {})),
                len(rec.get("manifest_deps", [])),
            )
        )
    return "\n".join(lines) + "\n"


def _atomic_write(target_path, text):
    """Write `text` to `target_path` atomically.

    Uses tempfile.mkstemp + os.replace in the same directory so the
    rename is atomic on the same filesystem. Cleans the temp file on
    any failure and re-raises the underlying exception.
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=".{0}-".format(target_path.name),
        suffix=".tmp",
        dir=str(target_path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp_path, str(target_path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _die(message, code=2):
    """Print error to stderr and return `code`."""
    sys.stderr.write("index_helper: {0}\n".format(message))
    return code


def cmd_build_index(args):
    """Build `index.json` + `docs/structure.md` from `init.yaml`.

    Exit codes:
      0 — both artifacts written successfully.
      2 — init.yaml missing or malformed; nothing written.
    """
    devforge_dir = _devforge_dir()
    init_yaml_path = devforge_dir / init_helper.OUTPUT_FILE_NAME
    if not init_yaml_path.exists():
        return _die(
            "init.yaml not found at {0}; run /init-forge first".format(
                init_yaml_path
            )
        )
    try:
        init_text = init_yaml_path.read_text(encoding="utf-8")
    except OSError as err:
        return _die(
            "cannot read init.yaml at {0}: {1}".format(init_yaml_path, err)
        )
    try:
        init_state = init_helper.parse_yaml(init_text)
    except init_helper.YamlParseError as err:
        return _die(
            "cannot parse init.yaml at {0}: {1}".format(init_yaml_path, err)
        )

    project_root = _project_root_from_init(init_state)
    generated_at = _utc_iso_now()
    index = {
        "version": INDEX_VERSION,
        "generated_at": generated_at,
        "project_root": str(project_root.resolve()),
        "packages": {},
    }
    for record in init_state.get("packages_detected", []) or []:
        pkg_path = record.get("path")
        if not isinstance(pkg_path, str) or pkg_path == "":
            # Defensive — shouldn't reach here because init_helper
            # validates packages_detected at set-time, but skip rather
            # than crash if state is corrupted.
            sys.stderr.write(
                "index_helper: skipping packages_detected record with empty "
                "path: {0!r}\n".format(record)
            )
            continue
        pkg_dir = (project_root / pkg_path).resolve() if pkg_path != "." else project_root.resolve()
        index["packages"][pkg_path] = _build_package_record(pkg_path, pkg_dir)

    # Write index.json.
    index_path = devforge_dir / INDEX_FILE_NAME
    try:
        _atomic_write(
            index_path,
            json.dumps(index, indent=2, sort_keys=True) + "\n",
        )
    except OSError as err:
        return _die(
            "cannot write index.json at {0}: {1}".format(index_path, err),
            code=1,
        )

    # Write docs/structure.md at the INSTALL root (the wrapper root), NOT
    # inside project_root. In wrapper mode, project_root points at the inner
    # workspace, but per CLAUDE.md's wrapper-mode convention all artifacts
    # (specs/, docs/, constitution.md) live at the install root alongside
    # .devforge/. Using install_root here keeps the location consistent
    # across standalone and wrapper modes.
    install_root = _devforge_dir().parent
    structure_path = install_root / STRUCTURE_DOC_REL
    try:
        _atomic_write(structure_path, _render_structure_md(index, generated_at))
    except OSError as err:
        return _die(
            "cannot write structure.md at {0}: {1}".format(structure_path, err),
            code=1,
        )

    sys.stderr.write(
        "index_helper: wrote {0} ({1} package(s))\n".format(
            index_path, len(index["packages"])
        )
    )
    sys.stderr.write(
        "index_helper: wrote {0}\n".format(structure_path)
    )
    return 0


# ---------------------------------------------------------------------------
# CLI wiring.
# ---------------------------------------------------------------------------


def build_parser():
    parser = argparse.ArgumentParser(
        prog="index_helper",
        description=(
            "Build the language-agnostic workspace structural index "
            "(`.devforge/index.json` + `docs/structure.md`) from "
            "`.devforge/init.yaml`."
        ),
    )
    sub = parser.add_subparsers(dest="subcommand")

    sp = sub.add_parser(
        "build-index",
        help="Build index.json + docs/structure.md from init.yaml.",
    )
    sp.set_defaults(func=cmd_build_index)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "func", None) is None:
        parser.print_help(sys.stderr)
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
