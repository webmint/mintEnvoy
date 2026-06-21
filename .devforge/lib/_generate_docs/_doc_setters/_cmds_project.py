"""Project-tier overview + architecture handlers + argparse builders.

Two clusters:
- `cmd_set_overview_*` — Track 4 Phase 1 + Phase 2 (project-overview tier).
- `cmd_set_architecture_*` — Track 4 Phase 3 (project-architecture tier).
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Dict, List

from ._blocks import (
    _interleave_dir_annotations,
    _replace_application_routes_block,
    _replace_arch_overview_narrative_block,
    _replace_arch_patterns_block,
    _replace_conventions_block,
    _replace_cross_cuts_block,
    _replace_cross_module_deps_block,
    _replace_dep_direction_rules_block,
    _replace_dep_overview_mermaid_block,
    _replace_entry_points_block,
    _replace_key_commands_block,
    _replace_module_map_block,
    _replace_module_structure_block,
    _replace_navigation_guards_block,
    _replace_project_structure_block,
    _replace_tech_stack_block,
    _replace_test_files_block,
    _TREE_FENCE_OPEN,
)
from ._renderers import (
    _decode_entry_list,
    _render_application_routes_table,
    _render_arch_patterns_subsections,
    _render_conventions_subsections,
    _render_cross_cuts_detailed_subsections,
    _render_dep_direction_rules_bullets,
    _render_entry_points_table,
    _render_fenced_text,
    _render_key_commands_table,
    _render_module_map_sections,
    _render_navigation_guards_list,
    _render_tech_stack_table,
    _render_test_files_bullets,
)
from ._skeletons import (
    _common_target_args,
    _doc_path_for,
    _load_active,
    _skeleton_path,
)


# ── Track 4 Phase 1 — project-overview mechanical handlers ─────────────────


def cmd_set_overview_tech_stack(args: argparse.Namespace) -> int:
    """Track 4 Phase 1 — write project-overview's `## Tech Stack` table."""
    if args.tier != "project-overview":
        print(
            f"set-overview-tech-stack supports tier=project-overview only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    entries = _decode_entry_list(args.tech_stack, "tech-stack")
    if entries is None:
        return 2
    table_text = _render_tech_stack_table(entries)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_tech_stack_block(content, table_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_overview_key_commands(args: argparse.Namespace) -> int:
    """Track 4 Phase 1 — write project-overview's `## Key Commands` table."""
    if args.tier != "project-overview":
        print(
            f"set-overview-key-commands supports tier=project-overview only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    entries = _decode_entry_list(args.key_commands, "key-commands")
    if entries is None:
        return 2
    table_text = _render_key_commands_table(entries)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_key_commands_block(content, table_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_overview_test_files(args: argparse.Namespace) -> int:
    """Track 4 Phase 1 — write project-overview's `## Test Files` bullets."""
    if args.tier != "project-overview":
        print(
            f"set-overview-test-files supports tier=project-overview only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    entries = _decode_entry_list(args.test_files, "test-files")
    if entries is None:
        return 2
    bullet_text = _render_test_files_bullets(entries)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_test_files_block(content, bullet_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_overview_cross_module_deps(args: argparse.Namespace) -> int:
    """Track 4 Phase 1 — write project-overview's `## Cross-Module Dependencies` fenced block."""
    if args.tier != "project-overview":
        print(
            f"set-overview-cross-module-deps supports tier=project-overview only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    fenced_text = _render_fenced_text(args.text)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_cross_module_deps_block(content, fenced_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_overview_project_structure_tree(args: argparse.Namespace) -> int:
    """Track 4 Phase 1 — write project-overview's `## Project Structure` fenced block.

    Phase 1 writes the bare tree only — no per-leaf annotations. Phase 2
    will add a separate annotations setter that interleaves descriptions
    onto leaves of an already-set tree (mirrors concern-tier two-step
    set-doc-structure pattern).
    """
    if args.tier != "project-overview":
        print(
            f"set-overview-project-structure-tree supports tier=project-overview only; "
            f"got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    fenced_text = _render_fenced_text(args.text)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_project_structure_block(content, fenced_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_overview_entry_points(args: argparse.Namespace) -> int:
    """Track 4 Phase 2 — write project-overview's `## Entry Points` table."""
    if args.tier != "project-overview":
        print(
            f"set-overview-entry-points supports tier=project-overview only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    entries = _decode_entry_list(args.entry_points, "entry-points")
    if entries is None:
        return 2
    table_text = _render_entry_points_table(entries)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_entry_points_block(content, table_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_overview_application_routes(args: argparse.Namespace) -> int:
    """Track 4 Phase 2 — write project-overview's `## Application Routes` table."""
    if args.tier != "project-overview":
        print(
            f"set-overview-application-routes supports tier=project-overview only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    entries = _decode_entry_list(args.routes, "routes")
    if entries is None:
        return 2
    table_text = _render_application_routes_table(entries)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_application_routes_block(content, table_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_overview_navigation_guards(args: argparse.Namespace) -> int:
    """Track 4 Phase 2 — write project-overview's `## Navigation Guards` numbered list."""
    if args.tier != "project-overview":
        print(
            f"set-overview-navigation-guards supports tier=project-overview only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    entries = _decode_entry_list(args.guards, "guards")
    if entries is None:
        return 2
    list_text = _render_navigation_guards_list(entries)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_navigation_guards_block(content, list_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_overview_module_map(args: argparse.Namespace) -> int:
    """Track 4 Phase 2 — write project-overview's `## Module Map` 3 sub-section tables."""
    if args.tier != "project-overview":
        print(
            f"set-overview-module-map supports tier=project-overview only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    try:
        decoded = json.loads(args.modules)
    except json.JSONDecodeError as exc:
        print(f"--modules must be valid JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(decoded, dict):
        print("--modules must decode to a JSON object", file=sys.stderr)
        return 2
    # Coerce inner lists; skip any non-list value.
    sections: Dict[str, List[Dict[str, str]]] = {}
    for key in ("infrastructure", "core", "domain"):
        items = decoded.get(key)
        if isinstance(items, list):
            sections[key] = [
                {k: str(v) for k, v in item.items()}
                for item in items if isinstance(item, dict)
            ]
        else:
            sections[key] = []
    body_text = _render_module_map_sections(sections)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_module_map_block(content, body_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_overview_project_structure_annotations(args: argparse.Namespace) -> int:
    """Track 4 Phase 2 — augment Phase 1 tree leaves with dir-level annotations.

    Mirrors concern-tier `set-doc-structure` mechanism but operates on
    directories (`<name>/` lines) not files. Phase 1 must have run first
    to plant the `## Project Structure` fenced tree; this setter walks
    the fence content and applies `<basename> → annotation` per leaf dir.
    Idempotent — re-applying overwrites any prior annotation when the
    annotation dict changes; lines not present in the dict are unchanged.
    """
    if args.tier != "project-overview":
        print(
            f"set-overview-project-structure-annotations supports tier=project-overview only; "
            f"got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    annotations: Dict[str, str] = {}
    if args.annotations:
        try:
            decoded = json.loads(args.annotations)
        except json.JSONDecodeError as exc:
            print(f"--annotations must be valid JSON: {exc}", file=sys.stderr)
            return 2
        if not isinstance(decoded, dict):
            print("--annotations must decode to a JSON object", file=sys.stderr)
            return 2
        annotations = {str(k): str(v) for k, v in decoded.items()}

    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    if _TREE_FENCE_OPEN not in content:
        print(
            f"no `{_TREE_FENCE_OPEN}` code fence in {path}; "
            f"run set-overview-project-structure-tree first",
            file=sys.stderr,
        )
        return 2
    path.write_text(_interleave_dir_annotations(content, annotations), encoding="utf-8")
    print(str(path))
    return 0


# ── Track 4 Phase 3 — architecture-tier handlers ───────────────────────────


def cmd_set_architecture_overview_narrative(args: argparse.Namespace) -> int:
    """Track 4 Phase 3 — write project-architecture's `## Architecture Overview`."""
    if args.tier != "project-architecture":
        print(
            f"set-architecture-overview-narrative supports tier=project-architecture only; "
            f"got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_arch_overview_narrative_block(content, args.text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_architecture_module_structure(args: argparse.Namespace) -> int:
    """Track 4 Phase 3 — write project-architecture's `## Module / Package Structure` fenced tree."""
    if args.tier != "project-architecture":
        print(
            f"set-architecture-module-structure supports tier=project-architecture only; "
            f"got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    fenced_text = _render_fenced_text(args.text)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_module_structure_block(content, fenced_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_architecture_patterns(args: argparse.Namespace) -> int:
    """Track 4 Phase 3 — write project-architecture's `## Patterns` subsections."""
    if args.tier != "project-architecture":
        print(
            f"set-architecture-patterns supports tier=project-architecture only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    entries = _decode_entry_list(args.patterns, "patterns")
    if entries is None:
        return 2
    body_text = _render_arch_patterns_subsections(entries)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_arch_patterns_block(content, body_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_architecture_conventions(args: argparse.Namespace) -> int:
    """Track 4 Phase 3 — write project-architecture's `## Conventions` 4 sub-sections.

    Note: this setter targets the project-architecture tier ONLY; do not
    confuse with the package-architecture tier's `set-doc-patterns`.
    """
    if args.tier != "project-architecture":
        print(
            f"set-architecture-conventions supports tier=project-architecture only; got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    try:
        decoded = json.loads(args.conventions)
    except json.JSONDecodeError as exc:
        print(f"--conventions must be valid JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(decoded, dict):
        print("--conventions must decode to a JSON object", file=sys.stderr)
        return 2
    sections: Dict[str, List[str]] = {}
    for key in ("naming", "file_organization", "import_style", "error_handling", "styling", "state_management"):
        items = decoded.get(key)
        if isinstance(items, list):
            sections[key] = [str(x) for x in items]
        else:
            sections[key] = []
    body_text = _render_conventions_subsections(sections)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_conventions_block(content, body_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_architecture_cross_cuts_detailed(args: argparse.Namespace) -> int:
    """Track 4 Phase 3 — write enriched `## Cross-Cuts` (subsections + code snippets).

    Replaces the existing `## Cross-Cuts` body. Phase 0 callers using the
    bullet-list `set-doc-cross-cuts` setter remain functional; this setter
    targets richer per-cross-cut subsections with cite-backed code samples.
    """
    if args.tier != "project-architecture":
        print(
            f"set-architecture-cross-cuts-detailed supports tier=project-architecture only; "
            f"got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    entries = _decode_entry_list(args.cross_cuts, "cross-cuts")
    if entries is None:
        return 2
    body_text = _render_cross_cuts_detailed_subsections(entries)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_cross_cuts_block(content, body_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_architecture_dependency_direction_rules(args: argparse.Namespace) -> int:
    """Track 4 Phase 3 — write `## Dependency Direction Rules` bullets."""
    if args.tier != "project-architecture":
        print(
            f"set-architecture-dependency-direction-rules supports tier=project-architecture only; "
            f"got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    try:
        decoded = json.loads(args.rules)
    except json.JSONDecodeError as exc:
        print(f"--rules must be valid JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(decoded, list):
        print("--rules must decode to a JSON array", file=sys.stderr)
        return 2
    body_text = _render_dep_direction_rules_bullets(decoded)
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_dep_direction_rules_block(content, body_text), encoding="utf-8")
    print(str(path))
    return 0


def cmd_set_architecture_dependency_overview_mermaid(args: argparse.Namespace) -> int:
    """Track 4 Phase 3 — write `## Dependency Overview` fenced ```mermaid block.

    Mechanical input — orchestrator passes either project-input's
    `dep_graph_mermaid` verbatim OR an LLM-curated mermaid graph. Helper
    wraps as fenced ```mermaid block; markdown viewers render the diagram
    natively. No Python mermaid renderer dep.
    """
    if args.tier != "project-architecture":
        print(
            f"set-architecture-dependency-overview-mermaid supports tier=project-architecture only; "
            f"got {args.tier!r}",
            file=sys.stderr,
        )
        return 2
    fenced_text = _render_fenced_text(args.text, language="mermaid")
    doc_path = _doc_path_for(args)
    path, content = _load_active(doc_path)
    if path is None:
        print(f"no skeleton at {_skeleton_path(doc_path)} — run init-doc first", file=sys.stderr)
        return 2
    path.write_text(_replace_dep_overview_mermaid_block(content, fenced_text), encoding="utf-8")
    print(str(path))
    return 0


# ── argparse factories ──────────────────────────────────────────────────────


def _build_set_overview_tech_stack(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-overview",))
    p.add_argument(
        "--tech-stack",
        dest="tech_stack",
        required=True,
        help='JSON array [{"layer": "Framework", "technology": "Vue 3"}]',
    )


def _build_set_overview_key_commands(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-overview",))
    p.add_argument(
        "--key-commands",
        dest="key_commands",
        required=True,
        help='JSON array [{"command": "npm run build", "description": "..."}]',
    )


def _build_set_overview_test_files(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-overview",))
    p.add_argument(
        "--test-files",
        dest="test_files",
        required=True,
        help='JSON array [{"path": "tests/", "description": "..."}]',
    )


def _build_set_overview_cross_module_deps(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-overview",))
    p.add_argument(
        "--text",
        required=True,
        help="ASCII tree text rendering the cross-package dependency graph",
    )


def _build_set_overview_project_structure_tree(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-overview",))
    p.add_argument(
        "--text",
        required=True,
        help="ASCII tree text of project structure (no annotations — Phase 1 bare tree)",
    )


def _build_set_overview_entry_points(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-overview",))
    p.add_argument(
        "--entry-points",
        dest="entry_points",
        required=True,
        help='JSON array [{"label": "App entry", "path": "src/main.ts", "purpose": "..."}]',
    )


def _build_set_overview_application_routes(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-overview",))
    p.add_argument(
        "--routes",
        required=True,
        help='JSON array [{"path": "/quote", "component": "PageQuote.vue", "description": "..."}]',
    )


def _build_set_overview_navigation_guards(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-overview",))
    p.add_argument(
        "--guards",
        required=True,
        help='JSON array [{"name": "oktaGuard", "role": "Checks Okta auth state"}]',
    )


def _build_set_overview_module_map(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-overview",))
    p.add_argument(
        "--modules",
        required=True,
        help=(
            'JSON object {"infrastructure": [{name, purpose}], '
            '"core": [...], "domain": [...]}'
        ),
    )


def _build_set_overview_project_structure_annotations(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-overview",))
    p.add_argument(
        "--annotations",
        default="",
        help='JSON object {dir_basename: annotation_text} — augments Phase 1 tree leaves',
    )


def _build_set_architecture_overview_narrative(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-architecture",))
    p.add_argument(
        "--text",
        required=True,
        help="Multi-paragraph narrative describing the architectural shape",
    )


def _build_set_architecture_module_structure(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-architecture",))
    p.add_argument(
        "--text",
        required=True,
        help="Annotated tree (project-architecture variant) — fenced text block",
    )


def _build_set_architecture_patterns(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-architecture",))
    p.add_argument(
        "--patterns",
        required=True,
        help=(
            'JSON array [{"name": "...", "applies_in": "...", "rule": "...", '
            '"language": "typescript", "code_snippet": "...", "cite": "<file>:<line>"}]'
        ),
    )


def _build_set_architecture_conventions(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-architecture",))
    p.add_argument(
        "--conventions",
        required=True,
        help=(
            'JSON object {"naming": [bullets], "file_organization": [bullets], '
            '"import_style": [bullets], "error_handling": [bullets], '
            '"styling": [bullets], "state_management": [bullets]}'
        ),
    )


def _build_set_architecture_cross_cuts_detailed(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-architecture",))
    p.add_argument(
        "--cross-cuts",
        dest="cross_cuts",
        required=True,
        help=(
            'JSON array [{"name": "...", "description": "...", '
            '"language": "...", "code_snippet": "...", "cite": "<file>:<line>"}]'
        ),
    )


def _build_set_architecture_dependency_direction_rules(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-architecture",))
    p.add_argument(
        "--rules",
        required=True,
        help='JSON array of bullet-point rule strings',
    )


def _build_set_architecture_dependency_overview_mermaid(p: argparse.ArgumentParser) -> None:
    _common_target_args(p, ("project-architecture",))
    p.add_argument(
        "--text",
        required=True,
        help='Mermaid graph syntax (e.g. `graph TD\\n  a-->b`); helper wraps in ```mermaid fence',
    )
