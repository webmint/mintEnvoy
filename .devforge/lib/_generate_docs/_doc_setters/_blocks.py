"""Section replacers + annotation interleavers.

`_replace_or_substitute` accepts either a placeholder marker (init-doc
emits these) OR an already-filled section body (idempotent re-runs).
"""

from __future__ import annotations

import re
from typing import Dict, List

from ._skeletons import (
    _APPLICATION_ROUTES_PLACEHOLDER,
    _ARCH_OVERVIEW_NARRATIVE_PLACEHOLDER,
    _ARCH_PATTERNS_PLACEHOLDER,
    _CONCERNS_PLACEHOLDER,
    _CONVENTIONS_PLACEHOLDER,
    _CROSS_CUTS_PLACEHOLDER,
    _CROSS_MODULE_DEPS_PLACEHOLDER,
    _DEP_DIRECTION_RULES_PLACEHOLDER,
    _DEP_OVERVIEW_MERMAID_PLACEHOLDER,
    _ENTRY_POINTS_PLACEHOLDER,
    _FILES_PLACEHOLDER,
    _KEY_COMMANDS_PLACEHOLDER,
    _LAYERS_PLACEHOLDER,
    _MODULE_MAP_PLACEHOLDER,
    _MODULE_STRUCTURE_PLACEHOLDER,
    _NAVIGATION_GUARDS_PLACEHOLDER,
    _PACKAGES_PLACEHOLDER,
    _PATTERNS_PLACEHOLDER,
    _PROJECT_STRUCTURE_PLACEHOLDER,
    _PURPOSE_PLACEHOLDER,
    _SUBCONCERNS_PLACEHOLDER,
    _TECH_STACK_PLACEHOLDER,
    _TEST_FILES_PLACEHOLDER,
)

_TREE_FENCE_OPEN = "```text"
_TREE_FENCE_CLOSE = "```"
_ANNOTATION_SEPARATOR = "  # "
_LEAF_CONNECTORS = ("├── ", "└── ")
_CANONICAL_AGGREGATORS = (
    "mod.rs",
    "lib.rs",
    "__init__.py",
    "index.ts",
    "index.js",
    "doc.go",
    "index.tsx",
    "index.jsx",
)


def _replace_or_substitute(content: str, placeholder: str, anchor: str, new_text: str) -> str:
    """Replace either the placeholder OR an already-filled section body.

    Section body = lines between `## <anchor>\n\n` and the next `## ` (or EOF).

    Regex path (re-render): when a following heading exists, group 3 captures
    `\\n## ` (a single newline).  We emit `\\n\\n## ` instead so markdown
    always has a blank line before the next heading.  When group 3 is `` (EOF
    sentinel), the suffix is left unchanged.  Empty new_text does not produce
    an extra blank line — the separator logic only fires when new_text is
    non-empty.

    Known limitation: `new_text` must not contain a `\\n## ` sequence (a `## `
    heading at line-start inside the body).  The non-greedy `.*?` in the regex
    stops at the first inner `\\n## `, truncating the replacement and corrupting
    output on re-render.
    """
    new_text = new_text.rstrip()
    if placeholder in content:
        return content.replace(placeholder, new_text, 1)
    pattern = re.compile(
        rf"(## {re.escape(anchor)}\n\n)(.*?)(\n## |\Z)",
        flags=re.DOTALL,
    )

    def _repl(m: "re.Match[str]") -> str:
        heading = m.group(1)
        sep = m.group(3)
        # Normalise \n## → \n\n## only when there is body text; an empty body
        # should not produce a doubled blank line (## A\n\n\n\n## B).
        if sep == "\n## " and new_text:
            sep = "\n\n## "
        return heading + new_text + sep

    return pattern.sub(_repl, content, count=1)


def _replace_purpose_block(content: str, new_text: str) -> str:
    return _replace_or_substitute(content, _PURPOSE_PLACEHOLDER, "Purpose", new_text)


def _replace_concerns_block(content: str, bullet_text: str) -> str:
    return _replace_or_substitute(content, _CONCERNS_PLACEHOLDER, "Concerns", bullet_text)


def _replace_files_block(content: str, bullet_text: str) -> str:
    return _replace_or_substitute(content, _FILES_PLACEHOLDER, "Files", bullet_text)


def _replace_packages_block(content: str, bullet_text: str) -> str:
    return _replace_or_substitute(content, _PACKAGES_PLACEHOLDER, "Packages", bullet_text)


def _replace_cross_cuts_block(content: str, bullet_text: str) -> str:
    return _replace_or_substitute(content, _CROSS_CUTS_PLACEHOLDER, "Cross-Cuts", bullet_text)


def _replace_layers_block(content: str, bullet_text: str) -> str:
    return _replace_or_substitute(content, _LAYERS_PLACEHOLDER, "Layers", bullet_text)


def _replace_patterns_block(content: str, bullet_text: str) -> str:
    return _replace_or_substitute(content, _PATTERNS_PLACEHOLDER, "Patterns", bullet_text)


def _replace_subconcerns_block(content: str, bullet_text: str) -> str:
    return _replace_or_substitute(
        content, _SUBCONCERNS_PLACEHOLDER, "Sub-concerns", bullet_text
    )


def _replace_tech_stack_block(content: str, table_text: str) -> str:
    return _replace_or_substitute(
        content, _TECH_STACK_PLACEHOLDER, "Tech Stack", table_text
    )


def _replace_project_structure_block(content: str, fenced_text: str) -> str:
    return _replace_or_substitute(
        content, _PROJECT_STRUCTURE_PLACEHOLDER, "Project Structure", fenced_text
    )


def _replace_key_commands_block(content: str, table_text: str) -> str:
    return _replace_or_substitute(
        content, _KEY_COMMANDS_PLACEHOLDER, "Key Commands", table_text
    )


def _replace_test_files_block(content: str, bullet_text: str) -> str:
    return _replace_or_substitute(
        content, _TEST_FILES_PLACEHOLDER, "Test Files", bullet_text
    )


def _replace_cross_module_deps_block(content: str, fenced_text: str) -> str:
    return _replace_or_substitute(
        content, _CROSS_MODULE_DEPS_PLACEHOLDER, "Cross-Module Dependencies", fenced_text
    )


def _replace_entry_points_block(content: str, table_text: str) -> str:
    return _replace_or_substitute(
        content, _ENTRY_POINTS_PLACEHOLDER, "Entry Points", table_text
    )


def _replace_module_map_block(content: str, body_text: str) -> str:
    return _replace_or_substitute(
        content, _MODULE_MAP_PLACEHOLDER, "Module Map", body_text
    )


def _replace_application_routes_block(content: str, table_text: str) -> str:
    return _replace_or_substitute(
        content, _APPLICATION_ROUTES_PLACEHOLDER, "Application Routes", table_text
    )


def _replace_navigation_guards_block(content: str, list_text: str) -> str:
    return _replace_or_substitute(
        content, _NAVIGATION_GUARDS_PLACEHOLDER, "Navigation Guards", list_text
    )


def _replace_arch_overview_narrative_block(content: str, prose: str) -> str:
    return _replace_or_substitute(
        content, _ARCH_OVERVIEW_NARRATIVE_PLACEHOLDER, "Architecture Overview", prose
    )


def _replace_module_structure_block(content: str, fenced_text: str) -> str:
    return _replace_or_substitute(
        content, _MODULE_STRUCTURE_PLACEHOLDER, "Module / Package Structure", fenced_text
    )


def _replace_arch_patterns_block(content: str, body_text: str) -> str:
    return _replace_or_substitute(
        content, _ARCH_PATTERNS_PLACEHOLDER, "Patterns", body_text
    )


def _replace_conventions_block(content: str, body_text: str) -> str:
    return _replace_or_substitute(
        content, _CONVENTIONS_PLACEHOLDER, "Conventions", body_text
    )


def _replace_dep_direction_rules_block(content: str, body_text: str) -> str:
    return _replace_or_substitute(
        content, _DEP_DIRECTION_RULES_PLACEHOLDER, "Dependency Direction Rules", body_text
    )


def _replace_dep_overview_mermaid_block(content: str, fenced_text: str) -> str:
    return _replace_or_substitute(
        content, _DEP_OVERVIEW_MERMAID_PLACEHOLDER, "Dependency Overview", fenced_text
    )


# ── Concern-tier annotation interleaving ───────────────────────────────────


def _annotate_leaf_line(line: str, annotations: Dict[str, str]) -> str:
    if _ANNOTATION_SEPARATOR in line:
        return line
    for connector in _LEAF_CONNECTORS:
        idx = line.rfind(connector)
        if idx < 0:
            continue
        tail = line[idx + len(connector):].rstrip()
        if not tail or tail in _CANONICAL_AGGREGATORS:
            return line
        if "." not in tail:
            return line
        annotation = annotations.get(tail)
        if not annotation:
            return line
        return f"{line.rstrip()}{_ANNOTATION_SEPARATOR}{annotation.strip()}"
    return line


def _interleave_annotations(content: str, annotations: Dict[str, str]) -> str:
    out: List[str] = []
    in_fence = False
    for line in content.split("\n"):
        if not in_fence and line.strip() == _TREE_FENCE_OPEN:
            in_fence = True
            out.append(line)
            continue
        if in_fence and line.strip() == _TREE_FENCE_CLOSE:
            in_fence = False
            out.append(line)
            continue
        if in_fence:
            out.append(_annotate_leaf_line(line, annotations))
        else:
            out.append(line)
    return "\n".join(out)


def _annotate_dir_line(line: str, annotations: Dict[str, str]) -> str:
    """Augment a project-structure tree line with an annotation comment.

    Matches lines ending with `<dirname>/` (project tree dirs) — a project-
    structure tree annotates DIRECTORIES (e.g. `apps/` → "Vue 3 SPA shell"),
    where concern-tier `_annotate_leaf_line` annotates FILES. Returns the
    line unchanged when:
      - it already has an annotation (`  # ` separator present)
      - no `├──` / `└──` connector
      - the entry doesn't end with `/` (skip files in mixed trees)
      - no annotation registered for the dir basename
    """
    if _ANNOTATION_SEPARATOR in line:
        return line
    for connector in _LEAF_CONNECTORS:
        idx = line.rfind(connector)
        if idx < 0:
            continue
        tail = line[idx + len(connector):].rstrip()
        if not tail or not tail.endswith("/"):
            return line
        # Strip trailing "/" for annotations dict lookup; users register by
        # directory basename, not the rendered "name/" form.
        basename = tail.rstrip("/")
        if not basename:
            return line
        annotation = annotations.get(basename)
        if not annotation:
            return line
        return f"{line.rstrip()}{_ANNOTATION_SEPARATOR}{annotation.strip()}"
    return line


def _interleave_dir_annotations(content: str, annotations: Dict[str, str]) -> str:
    """Walk the fenced ```text block and apply `_annotate_dir_line` per line.

    Same fenced-block boundary logic as `_interleave_annotations` but uses
    the dir variant for project structure (annotates directories, not files).
    """
    out: List[str] = []
    in_fence = False
    for line in content.split("\n"):
        if not in_fence and line.strip() == _TREE_FENCE_OPEN:
            in_fence = True
            out.append(line)
            continue
        if in_fence and line.strip() == _TREE_FENCE_CLOSE:
            in_fence = False
            out.append(line)
            continue
        if in_fence:
            out.append(_annotate_dir_line(line, annotations))
        else:
            out.append(line)
    return "\n".join(out)
