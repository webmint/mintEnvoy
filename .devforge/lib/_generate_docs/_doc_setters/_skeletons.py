"""Placeholders + tier constants + path resolution + per-tier skeleton builders.

Owns the markdown-skeleton shape per tier. No section-replacement logic
here (lives in `_blocks`) and no renderer logic (lives in `_renderers`).
The `_merge_project_skeleton` function which combines existing files
with fresh skeletons lives in `_cmds_package.py` alongside `cmd_init_doc`
to avoid a circular import on `_replace_or_substitute`.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .._md_frontmatter import render_frontmatter

_PURPOSE_PLACEHOLDER = "<!-- TODO: purpose -->"
_CONCERNS_PLACEHOLDER = "<!-- TODO: concerns -->"
_FILES_PLACEHOLDER = "<!-- TODO: files -->"
_LAYERS_PLACEHOLDER = "<!-- TODO: layers -->"
_PATTERNS_PLACEHOLDER = "<!-- TODO: patterns -->"
_PACKAGES_PLACEHOLDER = "<!-- TODO: packages -->"
_CROSS_CUTS_PLACEHOLDER = "<!-- TODO: cross-cuts -->"
_SUBCONCERNS_PLACEHOLDER = "<!-- TODO: sub-concerns -->"
# Track 4 Phase 1 — project-tier mechanical sections.
_TECH_STACK_PLACEHOLDER = "<!-- TODO: tech-stack -->"
_PROJECT_STRUCTURE_PLACEHOLDER = "<!-- TODO: project-structure -->"
_KEY_COMMANDS_PLACEHOLDER = "<!-- TODO: key-commands -->"
_TEST_FILES_PLACEHOLDER = "<!-- TODO: test-files -->"
_CROSS_MODULE_DEPS_PLACEHOLDER = "<!-- TODO: cross-module-dependencies -->"
# Track 4 Phase 2 — mixed mechanical+LLM sections (helper renders structure;
# LLM provides purpose/description/role text inside JSON input).
_ENTRY_POINTS_PLACEHOLDER = "<!-- TODO: entry-points -->"
_MODULE_MAP_PLACEHOLDER = "<!-- TODO: module-map -->"
_APPLICATION_ROUTES_PLACEHOLDER = "<!-- TODO: application-routes -->"
_NAVIGATION_GUARDS_PLACEHOLDER = "<!-- TODO: navigation-guards -->"
# Track 4 Phase 3 — architecture-tier sections (LLM-judgment heavy +
# code-snippet cite-back via CBM get_code_snippet).
_ARCH_OVERVIEW_NARRATIVE_PLACEHOLDER = "<!-- TODO: architecture-overview-narrative -->"
_MODULE_STRUCTURE_PLACEHOLDER = "<!-- TODO: module-structure -->"
_ARCH_PATTERNS_PLACEHOLDER = "<!-- TODO: architecture-patterns -->"
_CONVENTIONS_PLACEHOLDER = "<!-- TODO: conventions -->"
_DEP_DIRECTION_RULES_PLACEHOLDER = "<!-- TODO: dependency-direction-rules -->"
_DEP_OVERVIEW_MERMAID_PLACEHOLDER = "<!-- TODO: dependency-overview-mermaid -->"

_VALID_TIERS = (
    "concern",
    "package-overview",
    "package-architecture",
    "project-overview",
    "project-architecture",
)

_TIER_DOC_FILENAMES: Dict[str, str] = {
    "concern": "index.md",
    "package-overview": "overview.md",
    "package-architecture": "architecture.md",
    "project-overview": "overview.md",
    "project-architecture": "architecture.md",
}

_PROJECT_TIERS = ("project-overview", "project-architecture")


# ── Path resolution ─────────────────────────────────────────────────────────


def _doc_path_for(args: argparse.Namespace) -> Path:
    """Resolve the doc path.

    Concern + package tiers: docs/<target>/<tier-filename>.
    Project tiers: docs/<tier-filename> (no per-target subdir; target arg
    is treated as a label only for the H1 / frontmatter).
    """
    devforge_dir = Path(args.devforge_dir)
    project_root = devforge_dir.parent.resolve()
    filename = _TIER_DOC_FILENAMES.get(args.tier, "index.md")
    if args.tier in _PROJECT_TIERS:
        return project_root / "docs" / filename
    return project_root / "docs" / args.target / filename


def _skeleton_path(doc_path: Path) -> Path:
    return doc_path.with_suffix(doc_path.suffix + ".skeleton")


def _load_active(doc_path: Path) -> Tuple[Optional[Path], Optional[str]]:
    """Return (path, content) for whichever of <doc>.skeleton or <doc> exists."""
    skel = _skeleton_path(doc_path)
    if skel.is_file():
        return skel, skel.read_text(encoding="utf-8")
    if doc_path.is_file():
        return doc_path, doc_path.read_text(encoding="utf-8")
    return None, None


# ── Skeleton builders (per tier) ────────────────────────────────────────────


def _build_concern_skeleton(frontmatter: Dict[str, Any], tree_text: str) -> str:
    concern_name = frontmatter.get("concern") or frontmatter.get("package") or "doc"
    body = (
        f"# {concern_name}\n\n"
        f"## Purpose\n\n"
        f"{_PURPOSE_PLACEHOLDER}\n\n"
        f"## Structure\n\n"
        f"```text\n"
        f"{tree_text.rstrip(chr(10))}\n"
        f"```\n"
    )
    return render_frontmatter(dict(frontmatter), "\n" + body)


def _build_concern_split_skeleton(frontmatter: Dict[str, Any]) -> str:
    """Skeleton for a parent concern doc whose children were split-dispatched.

    Plan F 3a: parent has no `## Structure` (it's an aggregator, not a leaf).
    Sections: `## Purpose` (orchestrator-direct synthesis) + `## Sub-concerns`
    (bulleted list with links to child docs).
    """
    concern_name = frontmatter.get("concern") or frontmatter.get("package") or "doc"
    body = (
        f"# {concern_name}\n\n"
        f"## Purpose\n\n"
        f"{_PURPOSE_PLACEHOLDER}\n\n"
        f"## Sub-concerns\n\n"
        f"{_SUBCONCERNS_PLACEHOLDER}\n"
    )
    return render_frontmatter(dict(frontmatter), "\n" + body)


def _build_package_overview_skeleton(frontmatter: Dict[str, Any]) -> str:
    name = frontmatter.get("package", "package")
    body = (
        f"# {name}\n\n"
        f"## Purpose\n\n"
        f"{_PURPOSE_PLACEHOLDER}\n\n"
        f"## Concerns\n\n"
        f"{_CONCERNS_PLACEHOLDER}\n\n"
        f"## Files\n\n"
        f"{_FILES_PLACEHOLDER}\n"
    )
    return render_frontmatter(dict(frontmatter), "\n" + body)


def _build_package_architecture_skeleton(frontmatter: Dict[str, Any]) -> str:
    name = frontmatter.get("package", "package")
    body = (
        f"# {name} architecture\n\n"
        f"## Layers\n\n"
        f"{_LAYERS_PLACEHOLDER}\n\n"
        f"## Patterns\n\n"
        f"{_PATTERNS_PLACEHOLDER}\n"
    )
    return render_frontmatter(dict(frontmatter), "\n" + body)


# Project-tier section ownership. /generate-docs owns these 4 anchors;
# every other `## ` anchor in `docs/overview.md` or `docs/architecture.md`
# is preserved verbatim across init-doc re-runs (e.g. anchors written by
# `/constitute`: `## What this project is for`, `## How it's used`,
# `## Architectural Decisions`, `## Layer Boundaries & Dependency Rules`,
# `## Data Flow`, `## Cross-cutting Concerns` — or any future anchor a
# user/command adds).
_PROJECT_OVERVIEW_OWNED_ANCHORS: Tuple[Tuple[str, str], ...] = (
    ("Purpose", _PURPOSE_PLACEHOLDER),
    ("Tech Stack", _TECH_STACK_PLACEHOLDER),
    ("Project Structure", _PROJECT_STRUCTURE_PLACEHOLDER),
    ("Entry Points", _ENTRY_POINTS_PLACEHOLDER),
    ("Key Commands", _KEY_COMMANDS_PLACEHOLDER),
    ("Module Map", _MODULE_MAP_PLACEHOLDER),
    ("Cross-Module Dependencies", _CROSS_MODULE_DEPS_PLACEHOLDER),
    ("Application Routes", _APPLICATION_ROUTES_PLACEHOLDER),
    ("Navigation Guards", _NAVIGATION_GUARDS_PLACEHOLDER),
    ("Test Files", _TEST_FILES_PLACEHOLDER),
    ("Packages", _PACKAGES_PLACEHOLDER),
)
_PROJECT_ARCHITECTURE_OWNED_ANCHORS: Tuple[Tuple[str, str], ...] = (
    ("Architecture Overview", _ARCH_OVERVIEW_NARRATIVE_PLACEHOLDER),
    ("Module / Package Structure", _MODULE_STRUCTURE_PLACEHOLDER),
    ("Patterns", _ARCH_PATTERNS_PLACEHOLDER),
    ("Conventions", _CONVENTIONS_PLACEHOLDER),
    ("Layers", _LAYERS_PLACEHOLDER),
    ("Cross-Cuts", _CROSS_CUTS_PLACEHOLDER),
    ("Dependency Direction Rules", _DEP_DIRECTION_RULES_PLACEHOLDER),
    ("Dependency Overview", _DEP_OVERVIEW_MERMAID_PLACEHOLDER),
)


def _build_project_overview_skeleton(frontmatter: Dict[str, Any], target: str) -> str:
    name = frontmatter.get("project") or target or "project"
    body = (
        f"# {name}\n\n"
        f"## Purpose\n\n"
        f"{_PURPOSE_PLACEHOLDER}\n\n"
        f"## Tech Stack\n\n"
        f"{_TECH_STACK_PLACEHOLDER}\n\n"
        f"## Project Structure\n\n"
        f"{_PROJECT_STRUCTURE_PLACEHOLDER}\n\n"
        f"## Entry Points\n\n"
        f"{_ENTRY_POINTS_PLACEHOLDER}\n\n"
        f"## Key Commands\n\n"
        f"{_KEY_COMMANDS_PLACEHOLDER}\n\n"
        f"## Module Map\n\n"
        f"{_MODULE_MAP_PLACEHOLDER}\n\n"
        f"## Cross-Module Dependencies\n\n"
        f"{_CROSS_MODULE_DEPS_PLACEHOLDER}\n\n"
        f"## Application Routes\n\n"
        f"{_APPLICATION_ROUTES_PLACEHOLDER}\n\n"
        f"## Navigation Guards\n\n"
        f"{_NAVIGATION_GUARDS_PLACEHOLDER}\n\n"
        f"## Test Files\n\n"
        f"{_TEST_FILES_PLACEHOLDER}\n\n"
        f"## Packages\n\n"
        f"{_PACKAGES_PLACEHOLDER}\n"
    )
    return render_frontmatter(dict(frontmatter), "\n" + body)


def _build_project_architecture_skeleton(frontmatter: Dict[str, Any], target: str) -> str:
    name = frontmatter.get("project") or target or "project"
    body = (
        f"# {name} architecture\n\n"
        f"## Architecture Overview\n\n"
        f"{_ARCH_OVERVIEW_NARRATIVE_PLACEHOLDER}\n\n"
        f"## Module / Package Structure\n\n"
        f"{_MODULE_STRUCTURE_PLACEHOLDER}\n\n"
        f"## Patterns\n\n"
        f"{_ARCH_PATTERNS_PLACEHOLDER}\n\n"
        f"## Conventions\n\n"
        f"{_CONVENTIONS_PLACEHOLDER}\n\n"
        f"## Layers\n\n"
        f"{_LAYERS_PLACEHOLDER}\n\n"
        f"## Cross-Cuts\n\n"
        f"{_CROSS_CUTS_PLACEHOLDER}\n\n"
        f"## Dependency Direction Rules\n\n"
        f"{_DEP_DIRECTION_RULES_PLACEHOLDER}\n\n"
        f"## Dependency Overview\n\n"
        f"{_DEP_OVERVIEW_MERMAID_PLACEHOLDER}\n"
    )
    return render_frontmatter(dict(frontmatter), "\n" + body)


def _common_target_args(p: argparse.ArgumentParser, tiers: Tuple[str, ...]) -> None:
    p.add_argument("--tier", required=True, choices=tiers)
    p.add_argument("--target", required=True)
    p.add_argument("--devforge-dir", default=".devforge")
