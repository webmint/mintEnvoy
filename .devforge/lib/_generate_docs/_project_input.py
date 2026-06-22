"""project-input helper.

Walks `<project_root>/` and the project's already-rendered package
overview docs, emits batch JSON consumed by the /generate-docs
orchestrator's project-tier compose step (Phase 4).

Output shape:
    {
      "project": "<project-root-basename>",
      "package_seeds": [
        {"package": "<pkg-path>", "frontmatter": {...},
         "purpose_text": "<verbatim ## Purpose section content>"},
        ...
      ],
      "project_root_files": [
        {"path": "<file>", "comment_rich_span": "..."},
        ...
      ],
      "source_stamp": "<sha256-prefix-16>"
    }

`package_seeds` is the list the orchestrator uses to compose the
project overview's `## Packages` section AND inform the project
architecture's `## Layers` / `## Cross-Cuts` derivation.

Mirrors F.7a's shape one tier up: concern_seeds → package_seeds,
package_root_files → project_root_files, src_root_files dropped (not
relevant at project tier).

Stdlib only. Targets Python 3.8+.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ._concern_input import _extract_comment_rich_span
from ._md_frontmatter import FrontmatterParseError, parse_frontmatter

_PER_FILE_SPAN_CAP = 6 * 1024
_BATCH_SPAN_CAP = 60 * 1024
_PROJECT_ROOT_FILES = (
    "README.md",
    "README.txt",
    "README",
    "CHANGELOG.md",
    "CHANGELOG.txt",
    "package.json",
    "pyproject.toml",
    "Cargo.toml",
    "go.mod",
)
_DOCS_DIR = "docs"

# Track 4 Phase 1 — directories ignored when walking project structure.
_TREE_IGNORE_DIRS = frozenset({
    "node_modules", ".git", ".hg", ".svn",
    "dist", "build", "out", "target",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".venv", "venv", ".env",
    ".idea", ".vscode",
    "coverage", ".coverage",
    ".turbo", ".next", ".nuxt", ".cache",
})
_TREE_DEFAULT_DEPTH = 3
_TREE_DEFAULT_FANOUT = 30  # max children per directory in emitted tree

# Track 4 Phase 1 — Tech Stack detection: package.json dep-name → (layer, technology).
# Order matters: first-match wins per (layer). Extending: append, don't reorder.
_TECH_STACK_RULES: Tuple[Tuple[str, str, str], ...] = (
    # (dep_name, layer, technology)
    ("vue", "Framework", "Vue"),
    ("react", "Framework", "React"),
    ("next", "Framework", "Next.js"),
    ("svelte", "Framework", "Svelte"),
    ("@angular/core", "Framework", "Angular"),
    ("express", "Framework", "Express"),
    ("fastify", "Framework", "Fastify"),
    ("typescript", "Language", "TypeScript"),
    ("vite", "Build Tool", "Vite"),
    ("webpack", "Build Tool", "Webpack"),
    ("rollup", "Build Tool", "Rollup"),
    ("turbo", "Monorepo", "Turborepo"),
    ("nx", "Monorepo", "Nx"),
    ("lerna", "Monorepo", "Lerna"),
    ("vitest", "Testing", "Vitest"),
    ("jest", "Testing", "Jest"),
    ("mocha", "Testing", "Mocha"),
    ("playwright", "Testing", "Playwright"),
    ("cypress", "Testing", "Cypress"),
    ("tailwindcss", "Styling", "Tailwind CSS"),
    ("sass", "Styling", "Sass/SCSS"),
    ("pinia", "State Management", "Pinia"),
    ("redux", "State Management", "Redux"),
    ("mobx", "State Management", "MobX"),
    ("@tanstack/react-query", "State Management", "TanStack Query"),
    ("@apollo/client", "API Layer", "Apollo Client (GraphQL)"),
    ("graphql", "API Layer", "GraphQL"),
    ("axios", "API Layer", "Axios"),
    ("vue-i18n", "i18n", "vue-i18n"),
    ("react-i18next", "i18n", "react-i18next"),
)

# Test directory names + file glob patterns. Returned paths are relative to project_root.
_TEST_DIR_NAMES = ("test", "tests", "__tests__", "spec", "specs")
_TEST_FILE_SUFFIXES = (".test.ts", ".test.tsx", ".test.js", ".test.jsx",
                       ".spec.ts", ".spec.tsx", ".spec.js", ".spec.jsx")
_TEST_PY_PREFIX = "test_"
_TEST_PY_SUFFIX = "_test.py"

# Track 4 Phase 2 — entry-point candidate filename heuristics.
# Filenames examined when walking effective_root for app entry candidates.
_ENTRY_POINT_FILENAMES = ("main.ts", "main.js", "main.tsx", "main.jsx",
                          "index.ts", "index.js", "App.vue", "app.tsx", "app.jsx")
_ENTRY_POINT_DIRS = ("router", "plugins", "store")  # also walked for entry-like files

# Track 4 Phase 2 — router-route + nav-guard discovery globs.
_ROUTE_DIR_NAMES = ("routes",)
_GUARD_DIR_NAMES = ("router-guards", "guards", "navigation-guards")

# Track 4 Phase 2 — package classification hints. Mechanical pattern matcher.
# Maps name-substring → category. First-match wins per package; packages
# matching no rule fall through to "domain" (the residual category).
_PACKAGE_CLASSIFICATION_RULES: Tuple[Tuple[str, str], ...] = (
    ("common", "infrastructure"),
    ("types", "infrastructure"),
    ("client", "infrastructure"),
    ("notifications", "infrastructure"),
    ("test", "infrastructure"),
    ("starter", "infrastructure"),
    ("util", "infrastructure"),
    ("shared", "infrastructure"),
    ("core", "core"),
)


def _enumerate_packages_with_overviews(project_root: Path) -> List[str]:
    """List packages whose overview doc exists at docs/<pkg>/overview.md.

    Walks docs/ recursively for any `overview.md` file (excluding the
    project-tier docs/overview.md). Returns project-relative package
    paths (the dir under docs/ containing overview.md).
    """
    project_root = project_root.resolve()
    docs_dir = (project_root / _DOCS_DIR).resolve()
    if not docs_dir.is_dir():
        return []
    out: List[str] = []
    project_overview = docs_dir / "overview.md"
    for path in sorted(docs_dir.rglob("overview.md")):
        try:
            if path.resolve() == project_overview.resolve():
                continue
        except OSError:
            pass
        try:
            rel_dir = path.parent.resolve().relative_to(docs_dir).as_posix()
        except ValueError:
            continue
        if rel_dir and rel_dir != ".":
            out.append(rel_dir)
    return out


def _read_seed_doc(
    doc_path: Path, label: str
) -> Optional[Dict[str, Any]]:
    """Parse frontmatter + Purpose section from an already-resolved doc path.

    Returns ``{"package": label, "frontmatter": record, "purpose_text": text}``
    or None when the file is missing, unreadable, or has malformed frontmatter.
    The "package" key name is kept for downstream compatibility — callers fill
    it with whatever logical label (package path or concern dir name) applies.
    """
    if not doc_path.is_file():
        return None
    try:
        text = doc_path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        record, body = parse_frontmatter(text)
    except FrontmatterParseError:
        return None
    purpose_lines: List[str] = []
    in_purpose = False
    for line in body.split("\n"):
        if line.startswith("## Purpose"):
            in_purpose = True
            continue
        if in_purpose and line.startswith("## "):
            break
        if in_purpose:
            purpose_lines.append(line)
    return {
        "package": label,
        "frontmatter": record,
        "purpose_text": "\n".join(purpose_lines).strip(),
    }


def _read_package_seed(
    project_root: Path, pkg: str
) -> Optional[Dict[str, Any]]:
    """Read frontmatter + Purpose section from a rendered package overview doc."""
    project_root = project_root.resolve()
    doc_path = project_root / _DOCS_DIR / pkg / "overview.md"
    return _read_seed_doc(doc_path, pkg)


def _enumerate_concern_docs(project_root: Path) -> List[str]:
    """List depth-1 concern dirs under docs/ that contain an index.md.

    Only examines immediate subdirectories of docs/ (depth-1). A nested
    layout such as docs/<pkg>/<concern>/index.md does NOT register the
    grandparent pkg — only docs/<concern>/index.md at depth-1 counts.

    Returns sorted concern dir names (relative to docs/).
    """
    project_root = project_root.resolve()
    docs_dir = (project_root / _DOCS_DIR).resolve()
    if not docs_dir.is_dir():
        return []
    out: List[str] = []
    try:
        entries = sorted(docs_dir.iterdir())
    except OSError:
        return []
    for entry in entries:
        if not entry.is_dir():
            continue
        if (entry / "index.md").is_file():
            out.append(entry.name)
    return out


def _read_concern_seed(
    project_root: Path, concern: str
) -> Optional[Dict[str, Any]]:
    """Read frontmatter + Purpose section from a rendered concern index doc.

    Reads docs/<concern>/index.md — the concern-tier output format — and
    returns the same shape as _read_package_seed so that downstream code
    can consume concern seeds without change.
    """
    project_root = project_root.resolve()
    doc_path = project_root / _DOCS_DIR / concern / "index.md"
    return _read_seed_doc(doc_path, concern)


def _collect_project_root_files(
    project_root: Path,
) -> Tuple[List[Dict[str, str]], List[Tuple[str, str]]]:
    """Read top-level files at project_root (README, CHANGELOG, package.json, etc.)."""
    project_root = project_root.resolve()
    records: List[Dict[str, str]] = []
    hash_pairs: List[Tuple[str, str]] = []
    if not project_root.is_dir():
        return records, hash_pairs
    total_span_bytes = 0
    for filename in _PROJECT_ROOT_FILES:
        candidate = project_root / filename
        if not candidate.is_file():
            continue
        try:
            content = candidate.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        try:
            rel = candidate.resolve().relative_to(project_root).as_posix()
        except ValueError:
            rel = candidate.as_posix()
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        hash_pairs.append((rel, content_hash))
        if total_span_bytes >= _BATCH_SPAN_CAP:
            records.append(
                {"path": rel, "comment_rich_span": "<...batch cap reached, span omitted...>"}
            )
            continue
        span = _extract_comment_rich_span(content, _PER_FILE_SPAN_CAP)
        total_span_bytes += len(span.encode("utf-8"))
        records.append({"path": rel, "comment_rich_span": span})
    return records, hash_pairs


def _read_project_name_from_config(devforge_dir: Path) -> Optional[str]:
    """Read PROJECT_NAME from `.devforge/project-config.json` if non-null/non-empty."""
    cfg_path = devforge_dir / "project-config.json"
    if not cfg_path.is_file():
        return None
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    name = cfg.get("PROJECT_NAME")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return None


def _read_project_root_from_init_yaml(devforge_dir: Path) -> Optional[str]:
    """Extract `project_root:` value from `.devforge/init.yaml`.

    `/init-forge` writes init.yaml with `project_root: <inner-monorepo-dir>`
    in wrapper mode; in standalone mode the value is `.` (uninformative).
    Returns the basename of the value when it's a non-trivial path; None
    when the file is missing, the field is absent, or the value is `.`.

    Plain regex parse — avoids a YAML dependency and the file format is
    flat key:value at this level.
    """
    yaml_path = devforge_dir / "init.yaml"
    if not yaml_path.is_file():
        return None
    try:
        text = yaml_path.read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.split("\n"):
        if line.startswith("project_root:"):
            value = line.split(":", 1)[1].strip().strip('"').strip("'")
            if not value or value == ".":
                return None
            # Last path segment — handles both bare names and rare nested paths.
            return value.rstrip("/").split("/")[-1]
    return None


def _read_project_root_relpath_from_init_yaml(devforge_dir: Path) -> Optional[str]:
    """Like `_read_project_root_from_init_yaml` but returns the full relpath.

    Where `_read_project_root_from_init_yaml` returns just the basename (used
    for project label fallback), this returns the verbatim `project_root:`
    value as written in init.yaml — necessary for resolving the inner
    monorepo's filesystem location in wrapper mode.

    Returns None for missing file, missing field, or the standalone-mode
    value `.`.
    """
    yaml_path = devforge_dir / "init.yaml"
    if not yaml_path.is_file():
        return None
    try:
        text = yaml_path.read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.split("\n"):
        if line.startswith("project_root:"):
            value = line.split(":", 1)[1].strip().strip('"').strip("'")
            if not value or value == ".":
                return None
            return value.rstrip("/")
    return None


def _resolve_effective_project_root(
    project_root: Path, devforge_dir: Path, package_paths: List[str]
) -> Path:
    """Return the directory where mechanical extraction should look for package.json.

    Wrapper mode: testForge20-style layout where the framework's `.devforge/`
    sits at the wrapper root, but the actual monorepo (with package.json,
    workspaces config, source tree) lives at `<wrapper>/<inner>/`. Mechanical
    helpers (tech stack, key commands, cross-package deps, structure tree,
    test files) must operate on the inner monorepo, not the wrapper.

    Priority:
      1. `<project_root>/package.json` exists → standalone mode, use project_root.
      2. `init.yaml project_root:` value → use that as relpath under project_root.
      3. Common first-segment across package_paths (when 2+ packages share
         a parent dir, e.g. `module/apps/app` and
         `module/packages/foo` share `module`).
      4. Fallback: project_root.
    """
    project_root = project_root.resolve()
    if (project_root / "package.json").is_file():
        return project_root
    init_relpath = _read_project_root_relpath_from_init_yaml(devforge_dir)
    if init_relpath:
        candidate = (project_root / init_relpath).resolve()
        if candidate.is_dir():
            return candidate
    common = _common_path_prefix(package_paths)
    if common:
        candidate = (project_root / common).resolve()
        if candidate.is_dir():
            return candidate
    return project_root


def _common_path_prefix(packages: List[str]) -> Optional[str]:
    """Return the deepest common parent directory across all package paths.

    `packages` are project-relative paths like `module/apps/app`
    or `foo`. The returned value is the first path segment shared by
    every entry — used as a fall-back project label in wrapper-mode setups
    where the wrapper folder is structurally meaningless and every package
    sits under a single inner monorepo dir.

    Returns None when fewer than 2 packages OR no shared first segment.
    """
    if len(packages) < 2:
        return None
    first_segments = []
    for pkg in packages:
        if not pkg:
            return None
        head = pkg.split("/", 1)[0]
        if not head:
            return None
        first_segments.append(head)
    candidate = first_segments[0]
    for seg in first_segments[1:]:
        if seg != candidate:
            return None
    return candidate


def _resolve_project_label(
    cli_arg: str,
    devforge_dir: Path,
    project_root: Path,
    package_paths: List[str],
) -> str:
    """Pick the most informative project label given current state.

    Priority:
      1. `--project` CLI arg (explicit override).
      2. `PROJECT_NAME` in `.devforge/project-config.json` (populated by
         a future `/configure` command — null until then).
      3. `project_root` in `.devforge/init.yaml` (populated by `/init-forge`;
         in wrapper mode this is the inner monorepo dir, e.g. `module`;
         in standalone mode it's `.` and skipped).
      4. Common first-path-segment across all package paths (wrapper-mode
         monorepos: every package lives under the same inner dir).
      5. `project_root.name` (the wrapper folder's basename — the legacy default).
    """
    if cli_arg:
        return cli_arg
    cfg_name = _read_project_name_from_config(devforge_dir)
    if cfg_name:
        return cfg_name
    init_root = _read_project_root_from_init_yaml(devforge_dir)
    if init_root:
        return init_root
    common = _common_path_prefix(package_paths)
    if common and common != project_root.name:
        return common
    return project_root.name


def _compute_source_stamp(
    package_seeds: List[Dict[str, Any]],
    project_root_hashes: List[Tuple[str, str]],
) -> str:
    """Aggregate stamp over package source_stamps + project-root file hashes."""
    parts: List[str] = []
    for seed in package_seeds:
        fm = seed.get("frontmatter") or {}
        p = seed.get("package", "")
        s = fm.get("source_stamp", "")
        parts.append(f"package\t{p}\t{s}")
    for path, h in project_root_hashes:
        parts.append(f"root\t{path}\t{h}")
    parts.sort()
    blob = "\n".join(parts)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


# ── Track 4 Phase 1 — mechanical extraction helpers ─────────────────────────


def _read_root_package_json(project_root: Path) -> Optional[Dict[str, Any]]:
    """Return parsed package.json at project_root, or None if missing/invalid."""
    pkg_path = project_root / "package.json"
    if not pkg_path.is_file():
        return None
    try:
        return json.loads(pkg_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _gather_all_deps(pkg: Dict[str, Any]) -> Dict[str, str]:
    """Collect dependencies + devDependencies + peerDependencies into one flat map."""
    out: Dict[str, str] = {}
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        section = pkg.get(key)
        if isinstance(section, dict):
            for name, version in section.items():
                if isinstance(name, str) and name and name not in out:
                    out[name] = str(version) if version is not None else ""
    return out


def _gather_workspace_deps(pkg: Dict[str, Any], project_root: Path) -> Dict[str, str]:
    """Aggregate deps + devDeps + peerDeps across every workspace package.json.

    Monorepo orchestration-root package.jsons typically declare only
    build-tooling (turbo, lerna, eslint), not application-layer deps. Tech
    stack detection must walk into each workspace to see Vue/TS/Pinia/Apollo
    which are the load-bearing tech for a real project. Returns a flat
    {dep_name: version} map across all workspaces, first-version wins on
    conflict.
    """
    raw_workspaces = pkg.get("workspaces")
    if isinstance(raw_workspaces, dict):
        raw_workspaces = raw_workspaces.get("packages")
    if not isinstance(raw_workspaces, list):
        return {}
    aggregate: Dict[str, str] = {}
    for glob_pat in raw_workspaces:
        if not isinstance(glob_pat, str):
            continue
        for path in sorted(project_root.glob(glob_pat)):
            if not path.is_dir():
                continue
            ws_pkg = path / "package.json"
            if not ws_pkg.is_file():
                continue
            try:
                ws_data = json.loads(ws_pkg.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            for name, version in _gather_all_deps(ws_data).items():
                aggregate.setdefault(name, version)
    return aggregate


def _detect_tech_stack(project_root: Path) -> List[Dict[str, str]]:
    """Detect tech-stack candidates from package.json + manifest presence.

    Strategy: walk `_TECH_STACK_RULES`; for each (dep_name, layer, tech),
    if dep_name appears in deps map, add entry. Returns list deduplicated
    by layer (first match per layer wins). Also surfaces non-JS languages
    when their manifest exists at project_root (pyproject.toml, Cargo.toml,
    go.mod).

    For monorepos: aggregates deps across the root package.json AND every
    workspace package.json. Monorepo orchestration roots typically declare
    only tooling deps; the real tech (Vue, TypeScript, Apollo, Pinia, etc.)
    lives in workspace packages.
    """
    project_root = project_root.resolve()
    out: List[Dict[str, str]] = []
    seen_layers: set = set()

    pkg = _read_root_package_json(project_root)
    if pkg is not None:
        deps = _gather_all_deps(pkg)
        # Merge workspace deps when monorepo. Root deps win on conflict.
        for name, version in _gather_workspace_deps(pkg, project_root).items():
            deps.setdefault(name, version)
        for dep_name, layer, technology in _TECH_STACK_RULES:
            if dep_name in deps and layer not in seen_layers:
                out.append({"layer": layer, "technology": technology})
                seen_layers.add(layer)
        if "Language" not in seen_layers:
            out.append({"layer": "Language", "technology": "JavaScript"})
            seen_layers.add("Language")

    if (project_root / "pyproject.toml").is_file() and "Language" not in seen_layers:
        out.append({"layer": "Language", "technology": "Python"})
        seen_layers.add("Language")
    if (project_root / "Cargo.toml").is_file() and "Language" not in seen_layers:
        out.append({"layer": "Language", "technology": "Rust"})
        seen_layers.add("Language")
    if (project_root / "go.mod").is_file() and "Language" not in seen_layers:
        out.append({"layer": "Language", "technology": "Go"})
        seen_layers.add("Language")

    return out


def _extract_key_commands(project_root: Path) -> List[Dict[str, str]]:
    """Read package.json `scripts` block; emit list of {command, description}.

    Command renders as `npm run <script-name>` (Phase 1 npm convention; Phase 2
    LLM judgment can rewrite for yarn/pnpm/bun). Description is the verbatim
    script value — Phase 2 may replace with prose.
    """
    pkg = _read_root_package_json(project_root)
    if pkg is None:
        return []
    scripts = pkg.get("scripts")
    if not isinstance(scripts, dict):
        return []
    out: List[Dict[str, str]] = []
    for name, value in scripts.items():
        if not isinstance(name, str) or not name:
            continue
        out.append({
            "command": f"npm run {name}",
            "description": str(value) if value is not None else "",
        })
    return out


def _walk_test_file_paths(project_root: Path) -> List[Dict[str, str]]:
    """Filesystem walk for test directories + test file suffixes.

    Returns deduplicated list of {path, description}; paths are project-relative
    POSIX strings. Two output kinds:
      - test directories (`test/`, `tests/`, `__tests__/`) — directory paths
      - individual test file globs collapsed to nearest containing directory

    Phase 1 emits directory-level paths only — file-level granularity is
    excessive for the project-tier overview's Test Files section.
    """
    project_root = project_root.resolve()
    if not project_root.is_dir():
        return []
    found_dirs: Dict[str, str] = {}

    for current, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in _TREE_IGNORE_DIRS and not d.startswith(".")]
        current_path = Path(current)
        try:
            rel_dir = current_path.relative_to(project_root).as_posix()
        except ValueError:
            continue
        for d in list(dirs):
            if d in _TEST_DIR_NAMES:
                key = (Path(rel_dir) / d).as_posix() if rel_dir else d
                found_dirs.setdefault(key, "test directory")
        for f in files:
            if any(f.endswith(suf) for suf in _TEST_FILE_SUFFIXES) or (
                f.startswith(_TEST_PY_PREFIX) and f.endswith(".py")
            ) or f.endswith(_TEST_PY_SUFFIX):
                # Collapse to containing directory.
                key = rel_dir or "."
                found_dirs.setdefault(key, "tests collocated with source")

    return [
        {"path": path, "description": desc}
        for path, desc in sorted(found_dirs.items())
    ]


def _enumerate_workspace_packages(pkg: Dict[str, Any], project_root: Path) -> List[str]:
    """Return list of workspace-internal package names from npm-workspaces config.

    Reads `workspaces` (array or {packages: array}); each entry is a glob like
    `packages/*`. Resolves each glob to existing dirs containing package.json
    and returns their `name` field.
    """
    raw_workspaces = pkg.get("workspaces")
    if isinstance(raw_workspaces, dict):
        raw_workspaces = raw_workspaces.get("packages")
    if not isinstance(raw_workspaces, list):
        return []
    package_names: List[str] = []
    for glob_pat in raw_workspaces:
        if not isinstance(glob_pat, str):
            continue
        for path in sorted(project_root.glob(glob_pat)):
            if not path.is_dir():
                continue
            ws_pkg = path / "package.json"
            if not ws_pkg.is_file():
                continue
            try:
                ws_data = json.loads(ws_pkg.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            ws_name = ws_data.get("name")
            if isinstance(ws_name, str) and ws_name:
                package_names.append(ws_name)
    return package_names


def _build_cross_module_deps_tree(project_root: Path) -> str:
    """Render an ASCII tree of cross-workspace internal deps.

    For npm-workspaces monorepos: walk each workspace package, for each
    workspace package P enumerate its dependencies that are themselves
    workspace packages, and render `P\\n  +-- internal_dep_1\\n  +-- ...`.

    For non-monorepo projects (no `workspaces` field): emit the root
    package's name + flat list of its non-dev dependencies.

    Empty string when no package.json or no dependencies to report.
    """
    project_root = project_root.resolve()
    pkg = _read_root_package_json(project_root)
    if pkg is None:
        return ""
    workspace_names = set(_enumerate_workspace_packages(pkg, project_root))
    if not workspace_names:
        # Non-monorepo: list root package + its prod deps.
        root_name = pkg.get("name") or project_root.name
        deps = pkg.get("dependencies")
        if not isinstance(deps, dict) or not deps:
            return ""
        lines = [str(root_name)]
        sorted_deps = sorted(d for d in deps if isinstance(d, str))
        for dep in sorted_deps:
            lines.append(f"  +-- {dep}")
        return "\n".join(lines)

    # Monorepo: per-package internal-dep block.
    blocks: List[str] = []
    raw_workspaces = pkg.get("workspaces")
    if isinstance(raw_workspaces, dict):
        raw_workspaces = raw_workspaces.get("packages")
    if not isinstance(raw_workspaces, list):
        raw_workspaces = []
    seen_pkg_paths: List[Path] = []
    for glob_pat in raw_workspaces:
        if not isinstance(glob_pat, str):
            continue
        for path in sorted(project_root.glob(glob_pat)):
            if path.is_dir() and path not in seen_pkg_paths:
                seen_pkg_paths.append(path)

    for path in seen_pkg_paths:
        ws_pkg_path = path / "package.json"
        if not ws_pkg_path.is_file():
            continue
        try:
            ws_data = json.loads(ws_pkg_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        ws_name = ws_data.get("name")
        if not isinstance(ws_name, str) or not ws_name:
            continue
        ws_deps = _gather_all_deps(ws_data)
        internal = sorted(d for d in ws_deps if d in workspace_names and d != ws_name)
        if not internal:
            blocks.append(ws_name)
            continue
        block_lines = [ws_name]
        for dep in internal:
            block_lines.append(f"  +-- {dep}")
        blocks.append("\n".join(block_lines))
    return "\n\n".join(blocks)


def _build_project_structure_tree(
    project_root: Path,
    max_depth: int = _TREE_DEFAULT_DEPTH,
    max_fanout: int = _TREE_DEFAULT_FANOUT,
) -> str:
    """ASCII directory tree of project_root, depth-limited and ignore-filtered.

    Format mirrors `_concern_input` tree style: ├──/└── connectors. Cap
    children per dir at `max_fanout` (truncated indicator added when reached).
    Hidden dirs (`.x`) and entries in `_TREE_IGNORE_DIRS` are excluded.

    Returns "" when project_root is missing.
    """
    project_root = project_root.resolve()
    if not project_root.is_dir():
        return ""
    lines: List[str] = [f"{project_root.name}/"]

    def walk(dir_path: Path, prefix: str, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            entries = sorted(dir_path.iterdir(), key=lambda p: (not p.is_dir(), p.name))
        except OSError:
            return
        kept = [
            e for e in entries
            if not (e.name.startswith(".") or e.name in _TREE_IGNORE_DIRS)
        ]
        truncated = False
        if len(kept) > max_fanout:
            kept = kept[:max_fanout]
            truncated = True
        for i, entry in enumerate(kept):
            is_last = (i == len(kept) - 1) and not truncated
            connector = "└── " if is_last else "├── "
            display = entry.name + ("/" if entry.is_dir() else "")
            lines.append(f"{prefix}{connector}{display}")
            if entry.is_dir() and depth < max_depth:
                next_prefix = prefix + ("    " if is_last else "│   ")
                walk(entry, next_prefix, depth + 1)
        if truncated:
            lines.append(f"{prefix}└── ... ({len(entries) - max_fanout} more)")

    walk(project_root, "", 1)
    return "\n".join(lines)


# ── Track 4 Phase 2 — mixed mechanical+LLM candidate helpers ───────────────


def _walk_entry_point_candidates(project_root: Path) -> List[Dict[str, str]]:
    """Filesystem walk for app entry candidate files.

    Returns list of `{label, path}` (no `purpose` — LLM fills downstream).
    Heuristic:
      - emit `main.*` / `App.*` / `app.*` files unconditionally (always entry-like)
      - emit `index.*` files ONLY when inside an entry-point dir (`router/`,
        `plugins/`, `store/`) — bare `index.ts` files at arbitrary depth
        (e.g., `locales/en/index.ts`) are i18n / module barrels, not app
        entries; including them as candidates pollutes the orchestrator's
        Phase 2 entry-points compose
      - emit any `.ts`/`.js`/`.vue` file inside an entry-point dir (catches
        `plugins/okta.ts`, `router/index.ts`, etc.)

    Walk depth capped at 6 + ignore-filtered. `label` is a short hint based
    on filename + containing dir; `path` is project-relative POSIX. LLM
    owns the human-readable Purpose.
    """
    project_root = project_root.resolve()
    if not project_root.is_dir():
        return []
    out: List[Dict[str, str]] = []
    seen: set = set()

    for current, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in _TREE_IGNORE_DIRS and not d.startswith(".")]
        current_path = Path(current).resolve()
        try:
            rel_parts = current_path.relative_to(project_root).parts
        except ValueError:
            continue
        if len(rel_parts) > 6:
            dirs[:] = []
            continue
        rel_dir = "/".join(rel_parts) if rel_parts else ""
        in_entry_dir = any(seg in _ENTRY_POINT_DIRS for seg in rel_parts)
        for f in files:
            base = f.lower()
            is_index_file = base.startswith("index.") and f in _ENTRY_POINT_FILENAMES
            is_unconditional = (
                f in _ENTRY_POINT_FILENAMES and not is_index_file
            )
            include = False
            if is_unconditional:
                include = True
            elif is_index_file and in_entry_dir:
                include = True
            elif in_entry_dir and f.endswith((".ts", ".js", ".tsx", ".jsx", ".vue")):
                include = True
            if not include:
                continue
            rel_path = (Path(rel_dir) / f).as_posix() if rel_dir else f
            if rel_path in seen:
                continue
            seen.add(rel_path)
            out.append({"label": _entry_point_label(f, rel_dir), "path": rel_path})

    out.sort(key=lambda e: e["path"])
    return out


def _entry_point_label(filename: str, rel_dir: str) -> str:
    """Cheap label heuristic for an entry-point candidate file.

    Mechanical only — LLM Phase 2 can rewrite for prose. Maps common
    entry-point shapes to human-readable hints; falls back to filename.
    """
    base = filename.lower()
    if base.startswith("main."):
        return "App entry"
    if base.startswith("index."):
        if "router" in rel_dir:
            return "Router"
        if "plugins" in rel_dir:
            return "Plugin"
        if "store" in rel_dir:
            return "Store"
        return "Module index"
    if base.startswith("app."):
        return "Root component"
    if "router" in rel_dir:
        return "Router config"
    if "plugins" in rel_dir:
        return "Plugin"
    if "store" in rel_dir:
        return "Store module"
    return filename


def _walk_router_route_files(project_root: Path) -> List[str]:
    """Walk for `router/routes/**/*.{ts,js,tsx,jsx}` route definition files.

    Returns project-relative POSIX paths. Mechanical extraction stops at
    file enumeration — actual route-string parsing is text-heavy and
    deferred to the orchestrator-LLM (which Reads each file + extracts
    `path: '/foo'` literals and component identifiers).
    """
    project_root = project_root.resolve()
    if not project_root.is_dir():
        return []
    out: List[str] = []
    for current, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in _TREE_IGNORE_DIRS and not d.startswith(".")]
        current_path = Path(current)
        parts = current_path.relative_to(project_root).parts if current_path != project_root else ()
        # Match when the path contains a `routes` segment whose parent is `router`.
        if not (len(parts) >= 2 and parts[-1] in _ROUTE_DIR_NAMES and parts[-2] == "router"):
            continue
        for f in files:
            if f.endswith((".ts", ".js", ".tsx", ".jsx")):
                rel_path = (current_path / f).relative_to(project_root).as_posix()
                out.append(rel_path)
    return sorted(out)


def _walk_nav_guard_files(project_root: Path) -> List[str]:
    """Walk for navigation-guard files in `**/router-guards/`, `**/guards/`,
    `**/navigation-guards/` directories.

    Returns project-relative POSIX paths sorted alphabetically. Guard order
    in the chain is NOT inferable from filesystem alone (depends on
    `addBeforeEach` call order in router setup); LLM resolves order by
    reading the router config.
    """
    project_root = project_root.resolve()
    if not project_root.is_dir():
        return []
    out: List[str] = []
    for current, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in _TREE_IGNORE_DIRS and not d.startswith(".")]
        current_path = Path(current)
        if current_path.name not in _GUARD_DIR_NAMES:
            continue
        for f in files:
            if f.endswith((".ts", ".js", ".tsx", ".jsx")):
                rel_path = (current_path / f).relative_to(project_root).as_posix()
                out.append(rel_path)
    return sorted(out)


def _classify_packages(package_names: List[str]) -> Dict[str, List[str]]:
    """Bucket workspace package names into infrastructure / core / domain.

    First-match-wins on `_PACKAGE_CLASSIFICATION_RULES`; anything matching
    no rule lands in `domain` (residual). This is a HINT — LLM may regroup
    based on actual package contents (the pattern matcher only sees names).
    """
    out: Dict[str, List[str]] = {"infrastructure": [], "core": [], "domain": []}
    for name in package_names:
        lowered = name.lower()
        category = "domain"
        for substring, target in _PACKAGE_CLASSIFICATION_RULES:
            if substring in lowered:
                category = target
                break
        out[category].append(name)
    for key in out:
        out[key].sort()
    return out


def _extract_workspace_package_names(project_root: Path) -> List[str]:
    """Return all workspace package names (npm-workspaces only; empty otherwise)."""
    pkg = _read_root_package_json(project_root)
    if pkg is None:
        return []
    return _enumerate_workspace_packages(pkg, project_root)


def _build_dep_graph_mermaid(project_root: Path) -> str:
    """Render `graph TD` mermaid syntax of cross-workspace internal deps.

    Format mirrors the reference bar reference:
      graph TD
          a[pkg-a]
          b[pkg-b]
          a --> b

    Each workspace package gets a node (lowercased + sanitized id, original
    name as label). Edges added per internal dependency. Non-workspace deps
    (npm registry packages) are excluded — graph is structural-internal only.

    Empty string when project_root has no `workspaces` config or no packages.
    LLM may pass this verbatim to set-architecture-dependency-overview-mermaid
    OR substitute a curated/grouped variant.
    """
    project_root = project_root.resolve()
    pkg = _read_root_package_json(project_root)
    if pkg is None:
        return ""
    workspace_names = set(_enumerate_workspace_packages(pkg, project_root))
    if not workspace_names:
        return ""

    raw_workspaces = pkg.get("workspaces")
    if isinstance(raw_workspaces, dict):
        raw_workspaces = raw_workspaces.get("packages")
    if not isinstance(raw_workspaces, list):
        raw_workspaces = []
    nodes: List[Tuple[str, str]] = []  # (id, label)
    edges: List[Tuple[str, str]] = []  # (from_id, to_id)
    seen_ids: Dict[str, str] = {}

    def make_node_id(name: str) -> str:
        # Mermaid node ids: alphanumeric only — strip non-[A-Za-z0-9] +
        # lowercase. Collision-resistant via numeric suffix on duplicate.
        base = "".join(c for c in name if c.isalnum()) or "node"
        node_id = base[0].lower() + base[1:] if base else "node"
        if node_id in seen_ids and seen_ids[node_id] != name:
            suffix = 2
            while f"{node_id}{suffix}" in seen_ids:
                suffix += 1
            node_id = f"{node_id}{suffix}"
        seen_ids[node_id] = name
        return node_id

    pkg_to_id: Dict[str, str] = {}
    for glob_pat in raw_workspaces:
        if not isinstance(glob_pat, str):
            continue
        for path in sorted(project_root.glob(glob_pat)):
            ws_pkg_path = path / "package.json"
            if not ws_pkg_path.is_file():
                continue
            try:
                ws_data = json.loads(ws_pkg_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            ws_name = ws_data.get("name")
            if not isinstance(ws_name, str) or not ws_name:
                continue
            if ws_name in pkg_to_id:
                continue
            node_id = make_node_id(ws_name)
            pkg_to_id[ws_name] = node_id
            nodes.append((node_id, ws_name))

    for ws_name, node_id in pkg_to_id.items():
        # Re-resolve workspace path → package.json to read its deps. We
        # iterate again (rather than caching) to keep the function
        # self-contained; n^2 over workspace count is fine at typical scale.
        for glob_pat in raw_workspaces:
            if not isinstance(glob_pat, str):
                continue
            for path in sorted(project_root.glob(glob_pat)):
                ws_pkg_path = path / "package.json"
                if not ws_pkg_path.is_file():
                    continue
                try:
                    ws_data = json.loads(ws_pkg_path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                if ws_data.get("name") != ws_name:
                    continue
                ws_deps = _gather_all_deps(ws_data)
                for dep_name in sorted(ws_deps):
                    if dep_name in pkg_to_id and dep_name != ws_name:
                        edges.append((node_id, pkg_to_id[dep_name]))

    if not nodes:
        return ""

    lines = ["graph TD"]
    for node_id, label in nodes:
        lines.append(f"    {node_id}[{label}]")
    if edges:
        lines.append("")
        for from_id, to_id in edges:
            lines.append(f"    {from_id} --> {to_id}")
    return "\n".join(lines)


def cmd_project_input(args: argparse.Namespace) -> int:
    """Handler for `project-input` subcommand. Returns CLI exit code."""
    devforge_dir = Path(args.devforge_dir)
    project_root = devforge_dir.parent.resolve()

    pkg_paths = _enumerate_packages_with_overviews(project_root)
    using_concern_fallback = False
    if not pkg_paths:
        concern_paths = _enumerate_concern_docs(project_root)
        if not concern_paths:
            print(
                f"no package overviews or concern docs found under "
                f"{project_root / 'docs'} — run /generate-docs through the "
                f"concern/package tier first",
                file=sys.stderr,
            )
            return 2
        pkg_paths = concern_paths
        using_concern_fallback = True

    package_seeds: List[Dict[str, Any]] = []
    missing: List[str] = []
    for pkg in pkg_paths:
        if using_concern_fallback:
            seed = _read_concern_seed(project_root, pkg)
        else:
            seed = _read_package_seed(project_root, pkg)
        if seed is None:
            missing.append(pkg)
            continue
        package_seeds.append(seed)

    if not package_seeds:
        if using_concern_fallback:
            print(
                f"no readable concern docs under {project_root / 'docs'} "
                f"(every concern index.md frontmatter parse failed)",
                file=sys.stderr,
            )
        else:
            print(
                f"no readable package overviews under {project_root / 'docs'} "
                f"(every overview frontmatter parse failed)",
                file=sys.stderr,
            )
        return 2

    root_records, root_hashes = _collect_project_root_files(project_root)
    source_stamp = _compute_source_stamp(package_seeds, root_hashes)

    project_label = _resolve_project_label(
        args.project, devforge_dir, project_root, pkg_paths
    )
    # Track 4 Phase 1 — mechanical extraction. Each helper degrades to empty
    # output when its source is absent (no package.json, no test dirs, etc.),
    # so the orchestrator can render a partial overview rather than failing.
    # In wrapper mode the inner monorepo holds the manifests + source tree;
    # `_resolve_effective_project_root` returns that dir so extraction looks
    # in the right place. In standalone mode it returns project_root unchanged.
    effective_root = _resolve_effective_project_root(
        project_root, devforge_dir, pkg_paths
    )
    workspace_packages = _extract_workspace_package_names(effective_root)
    output: Dict[str, Any] = {
        "project": project_label,
        "package_seeds": package_seeds,
        "project_root_files": root_records,
        "source_stamp": source_stamp,
        # Track 4 Phase 1 — purely mechanical fields.
        "tech_stack_candidates": _detect_tech_stack(effective_root),
        "key_commands": _extract_key_commands(effective_root),
        "test_file_paths": _walk_test_file_paths(effective_root),
        "cross_module_deps_tree": _build_cross_module_deps_tree(effective_root),
        "project_structure_tree": _build_project_structure_tree(effective_root),
        # Track 4 Phase 2 — mixed mechanical+LLM. Helper provides candidate
        # locations + classifications; orchestrator-LLM provides purpose /
        # description / role text + may regroup packages based on contents.
        "entry_point_candidates": _walk_entry_point_candidates(effective_root),
        "router_route_files": _walk_router_route_files(effective_root),
        "nav_guard_files": _walk_nav_guard_files(effective_root),
        "package_classification_hints": _classify_packages(workspace_packages),
        # Track 4 Phase 3 — architecture-tier mechanical input. LLM may
        # substitute a curated mermaid variant; default is mechanical render
        # of the same workspace deps walk that produces cross_module_deps_tree.
        "dep_graph_mermaid": _build_dep_graph_mermaid(effective_root),
    }
    if missing:
        output["missing_package_overviews"] = missing
    print(json.dumps(output, indent=2))
    return 0


def _build_project_input(p: argparse.ArgumentParser) -> None:
    """argparse factory for the `project-input` subcommand."""
    p.add_argument(
        "--project",
        default="",
        help="Optional project label (defaults to project_root basename)",
    )
    p.add_argument("--devforge-dir", default=".devforge")
