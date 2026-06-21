"""Markdown rendering for the generate_docs helper PackageDoc tier.

Renders a PackageDoc state record into a single markdown string in a
fixed section order. The same render is used by two subcommands:

- `render-package-skeleton` writes `docs/<package-path>/index.md.skeleton`.
  No validation gate — unset fields appear as `[TODO: ...]` slots so the
  LLM can see exactly which setters still need to fire.
- `render-package-doc` writes `docs/<package-path>/index.md`. Gated by
  `_validators_package.validate_package`; render-package-doc is gated by
  validate-package while render-package-skeleton is not. After the .md
  file is written, the .skeleton sibling (if present) is removed.

Render rules — fixed manual concatenation per the schema-anchored
generate-docs design (project_schema_anchored_generate_docs.md memory):

- No template engine, no jinja2; the helper owns shape, the LLM owns
  values. The render template here IS the public shape contract.
- Idempotent: a state record renders to byte-identical output on
  re-runs (sort orders are stable, no timestamps embedded).
- Section order is fixed (1..11 below). Section 7 (Types) is omitted
  entirely when empty rather than printed with a [TODO] — having no
  type exports is normal, not a missing-data signal.

Atomic file writes use `tempfile.mkstemp` + `os.replace` (anti-pattern
#4) so concurrent invocations and crash recovery are handled correctly.

Stdlib only. Targets Python 3.8+.
"""

import argparse
import os
import sys
import tempfile
from html import escape as _html_escape
from pathlib import Path
from typing import Any, Dict, List, Optional


def _esc(value: str) -> str:
    """HTML-escape a NARRATIVE prose value before substitution.

    Markdown renderers pass HTML-looking sequences through as raw HTML.
    Inline TypeScript generic syntax like ``DeepReadonly<Ref<S>>`` in
    a prose field embeds ``<S>`` — the deprecated HTML strikethrough
    tag — which makes everything until a (never-emitted) ``</s>`` render
    struck through. Escaping ``<``, ``>``, ``&`` at the substitution
    point converts those characters to entity references so the
    renderer treats them as literal text.

    Use this ONLY at narrative-prose substitution points (overview,
    hazard.description, dependency.purpose, export.description). Code
    contexts — fenced blocks (``` ... ```) and inline backtick spans —
    must pass through verbatim; escaping them would corrupt code.
    ``quote=False`` keeps quote characters intact (they have no special
    meaning in markdown and need not be escaped).
    """
    return _html_escape(value, quote=False)

from ._state import (
    StateLoadError,
    _die,
    _info,
    _load_state,
    _require_package,
)


_TODO_OVERVIEW = (
    "[TODO: 1-2 paragraphs describing what this package provides "
    "and who consumes it]"
)
_TODO_TREE = "[TODO: ascii tree of source layout]"
_TODO_SCRIPTS = (
    "[TODO: enumerate via add-package-script "
    "(or run extract-package-scripts)]"
)
_TODO_EXPORTS = "[TODO: enumerate package exports via add-package-export]"
_TODO_DEPENDENCIES = "[TODO: enumerate via add-package-dep]"
_TODO_HAZARDS = (
    "[TODO: list inline observations via add-package-hazard, or "
    "run with --skip-hazards if the package has no observable mislogic]"
)
_TODO_USAGE_EXAMPLE = (
    "[TODO: lift a real usage example via set-package-usage-example]"
)
_TODO_CONSUMER_PATTERN = (
    "[TODO: lift a representative consumer call via "
    "set-package-consumer-pattern]"
)
# Tech Stack uses two sentinels: a [TODO] for the required primary
# language (caught by the no-todo rule in validate-package), and an
# em-dash for the optional framework / build_tool (so an unset
# optional field doesn't masquerade as a missing-required-field TODO).
_TODO_TECH_REQUIRED = "[TODO]"
_OPTIONAL_UNSET_PLACEHOLDER = "—"


# Final-mode placeholder for empty optional sections. Skeleton mode emits
# LLM-targeted setter-name TODOs (so the LLM knows which setter to call);
# final mode replaces those with this concise human-facing marker so the
# rendered doc reads as documentation, not as an unfilled form. Required-
# field TODOs are unchanged in either mode (validate would have caught
# those — render-final after validate means required fields cannot be
# empty in practice, but the TODO still surfaces as a defense-in-depth
# signal if they somehow are).
_FINAL_NONE = "_(none)_"


# The required-field TODO markers — every one of these in a rendered
# skeleton indicates a required setter that has not been called.
# `_validators_package._check_no_todos` matches against these to raise a
# todo-marker-present error. Optional-section TODOs (scripts,
# hazards, usage_example, consumer_pattern) are NOT in this list:
# the schema declares those fields optional and validate-package must
# not block on them.
REQUIRED_FIELD_TODO_MARKERS = (
    _TODO_OVERVIEW,
    _TODO_TREE,
    _TODO_TECH_REQUIRED,
    _TODO_EXPORTS,
    _TODO_DEPENDENCIES,
)


# Optional-section markers — consumed by `_validators_package._check_optional_render`
# as a defense-in-depth check: if any of these markers appear in the
# rendered output AND the corresponding state field is populated, that's
# a render bug (state has the data but the rendering produced [TODO]).
# The 4-tuple shape is (state-field, marker, "is-empty" predicate).
# `is-empty` returns True when the state field is missing/empty (i.e.,
# the [TODO] is a legitimate optional skip, not a render bug).
def _scripts_empty(value: Any) -> bool:
    return not value


def _hazards_empty(value: Any) -> bool:
    return not value


def _opt_codeblock_empty(value: Any) -> bool:
    return value is None


OPTIONAL_SECTION_MARKERS = (
    ("scripts", _TODO_SCRIPTS, _scripts_empty),
    ("hazards", _TODO_HAZARDS, _hazards_empty),
    ("usage_example", _TODO_USAGE_EXAMPLE, _opt_codeblock_empty),
    ("consumer_pattern", _TODO_CONSUMER_PATTERN, _opt_codeblock_empty),
)

# `CONCERN_OPTIONAL_SECTION_MARKERS` is the concern-tier counterpart;
# it lives further down (line ~445) where the `_TODO_CONCERN_*`
# constants are defined.


def _render_overview(pkg: Dict[str, Any]) -> str:
    overview = pkg.get("overview")
    # Prose substitution: HTML-escape (the [TODO] sentinel contains no
    # angle brackets and is safe to substitute either way; escaping it
    # is a no-op).
    body = _esc(overview) if overview else _TODO_OVERVIEW
    return "## Overview\n\n{0}\n".format(body)


def _render_directory_tree(pkg: Dict[str, Any]) -> str:
    tree = pkg.get("directory_tree")
    body = tree if tree else _TODO_TREE
    return "## Directory Structure\n\n```\n{0}\n```\n".format(body)


def _render_tech_stack(pkg: Dict[str, Any]) -> str:
    primary = pkg.get("primary_language") or _TODO_TECH_REQUIRED
    framework = pkg.get("framework") or _OPTIONAL_UNSET_PLACEHOLDER
    build_tool = pkg.get("build_tool") or _OPTIONAL_UNSET_PLACEHOLDER
    rows = [
        "| Field | Value |",
        "| --- | --- |",
        "| Primary Language | {0} |".format(primary),
        "| Framework | {0} |".format(framework),
        "| Build Tool | {0} |".format(build_tool),
    ]
    return "## Tech Stack\n\n" + "\n".join(rows) + "\n"


def _render_scripts(pkg: Dict[str, Any], mode: str = "skeleton") -> str:
    scripts = pkg.get("scripts") or {}
    if not scripts:
        placeholder = _FINAL_NONE if mode == "final" else _TODO_SCRIPTS
        return "## Scripts\n\n{0}\n".format(placeholder)
    rows = ["| Script | Command |", "| --- | --- |"]
    for name in sorted(scripts.keys()):
        rows.append("| `{0}` | `{1}` |".format(name, scripts[name]))
    return "## Scripts\n\n" + "\n".join(rows) + "\n"


def _render_code_block(code: Dict[str, Any]) -> str:
    """Render a CodeBlock dict as a fenced block with a cite comment.

    The cite comment is rendered ABOVE the fenced block (inside the
    markdown but visually grouped with the snippet) so a reader can
    trace any quoted snippet back to its source line range without
    polluting the snippet itself.
    """
    cite = code.get("cite") or {}
    cite_file = cite.get("file", "")
    cite_start = cite.get("start", "")
    cite_end = cite.get("end", "")
    language = code.get("language") or ""
    snippet = code.get("snippet") or ""
    return (
        "<!-- {0}:{1}-{2} -->\n"
        "```{3}\n"
        "{4}\n"
        "```\n"
    ).format(cite_file, cite_start, cite_end, language, snippet)


def _render_export_entry(export: Dict[str, Any]) -> str:
    """Render one export as a sub-section with header / signature /
    description / cite + fenced code."""
    parts: List[str] = []
    parts.append(
        "### `{0}` — {1}".format(export["name"], export["kind"])
    )
    parts.append("")
    if export.get("signature"):
        # Signature renders inside a fenced code block — code context,
        # NOT escaped (escaping would corrupt the displayed signature).
        parts.append("```")
        parts.append(export["signature"])
        parts.append("```")
        parts.append("")
    # Description is narrative prose — HTML-escape so generic-syntax
    # tokens like ``<S>`` do not get parsed as the HTML strikethrough
    # tag by markdown renderers.
    parts.append(_esc(export["description"]))
    parts.append("")
    parts.append(_render_code_block(export["code"]))
    return "\n".join(parts)


def _render_main_exports(pkg: Dict[str, Any]) -> str:
    exports = pkg.get("exports") or []
    # Filter out type-kind entries; types render in their own section.
    non_types = [e for e in exports if e.get("kind") != "type"]
    if not non_types:
        return "## Main Exports\n\n{0}\n".format(_TODO_EXPORTS)
    body_parts = ["## Main Exports", ""]
    for ex in non_types:
        body_parts.append(_render_export_entry(ex))
    return "\n".join(body_parts).rstrip() + "\n"


def _render_types(pkg: Dict[str, Any]) -> Optional[str]:
    """Render the Types section, or None if there are no type exports.

    Empty Types -> section omitted entirely (per spec): not having any
    type-kind exports is normal, not a missing-data signal.
    """
    exports = pkg.get("exports") or []
    types = [e for e in exports if e.get("kind") == "type"]
    if not types:
        return None
    body_parts = ["## Types", ""]
    for ex in types:
        body_parts.append(_render_export_entry(ex))
    return "\n".join(body_parts).rstrip() + "\n"


def _render_dependency_entry(dep: Dict[str, Any]) -> str:
    name = dep["name"]
    version = dep.get("version") or ""
    # Purpose is narrative prose — HTML-escape to keep angle-bracket
    # tokens from being parsed as raw HTML by markdown renderers.
    purpose = _esc(dep.get("purpose", ""))
    version_part = " ({0})".format(version) if version else ""
    locations = dep.get("consumer_locations") or []
    line = "- `{0}`{1} — {2}".format(name, version_part, purpose)
    if locations:
        loc_text = ", ".join("`{0}`".format(loc) for loc in locations)
        line = line + "  \n  consumers: {0}".format(loc_text)
    return line


def _render_dependencies(pkg: Dict[str, Any]) -> str:
    deps = pkg.get("dependencies") or []
    internal = [d for d in deps if d.get("kind") == "internal"]
    external = [d for d in deps if d.get("kind") == "external"]
    if not internal and not external:
        return "## Dependencies\n\n{0}\n".format(_TODO_DEPENDENCIES)
    parts = ["## Dependencies", ""]
    parts.append("### Workspace-internal")
    parts.append("")
    if internal:
        for dep in internal:
            parts.append(_render_dependency_entry(dep))
    else:
        parts.append("_None._")
    parts.append("")
    parts.append("### External")
    parts.append("")
    if external:
        for dep in external:
            parts.append(_render_dependency_entry(dep))
    else:
        parts.append("_None._")
    parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def _render_hazards(pkg: Dict[str, Any], mode: str = "skeleton") -> str:
    hazards = pkg.get("hazards") or []
    if not hazards:
        placeholder = _FINAL_NONE if mode == "final" else _TODO_HAZARDS
        return "## Hazards\n\n{0}\n".format(placeholder)
    parts = ["## Hazards", ""]
    for hazard in hazards:
        # Both fields are narrative prose — HTML-escape so generic-syntax
        # tokens (e.g. ``DeepReadonly<Ref<S>>``) do not turn into HTML
        # tags. ``<S>`` is the deprecated strikethrough tag and was the
        # original visible-symptom field for this fix.
        line = "- **{0}**: {1}".format(
            _esc(hazard["category"]), _esc(hazard["description"])
        )
        cite = hazard.get("cite")
        if cite:
            line = line + "  \n  cite: `{0}:{1}-{2}`".format(
                cite["file"], cite["start"], cite["end"]
            )
        parts.append(line)
    return "\n".join(parts) + "\n"


def _render_usage_example(pkg: Dict[str, Any], mode: str = "skeleton") -> str:
    ue = pkg.get("usage_example")
    if not ue:
        placeholder = _FINAL_NONE if mode == "final" else _TODO_USAGE_EXAMPLE
        return "## Usage Example\n\n{0}\n".format(placeholder)
    return "## Usage Example\n\n" + _render_code_block(ue)


def _render_consumer_pattern(pkg: Dict[str, Any], mode: str = "skeleton") -> str:
    cp = pkg.get("consumer_pattern")
    if not cp:
        placeholder = _FINAL_NONE if mode == "final" else _TODO_CONSUMER_PATTERN
        return "## Consumer Pattern\n\n{0}\n".format(placeholder)
    return "## Consumer Pattern\n\n" + _render_code_block(cp)


def render_package_skeleton(
    state: Dict[str, Any], package_path: str, mode: str = "skeleton",
) -> str:
    """Pure render function — assembles a markdown string from a state
    record. Does not touch the filesystem.

    Both `cmd_render_package_skeleton` and `cmd_render_package_doc` call
    this; the difference between the two is only the output path, whether
    validation gates the write, and the `mode` argument.

    `mode="skeleton"` (default): empty optional sections emit LLM-targeted
    setter-name [TODO] markers so the LLM knows which setter to call.
    `mode="final"`: empty optional sections emit `_(none)_` instead,
    so the rendered doc reads as documentation rather than an unfilled form.
    Required-field TODOs are unchanged in either mode.
    """
    pkg = _require_package(state, package_path)
    if pkg is None:
        raise KeyError(
            "package not registered at {0!r}".format(package_path)
        )
    sections: List[str] = []
    sections.append("# {0}".format(pkg["name"]))
    sections.append("")
    sections.append(_render_overview(pkg))
    sections.append(_render_directory_tree(pkg))
    sections.append(_render_tech_stack(pkg))
    sections.append(_render_scripts(pkg, mode))
    sections.append(_render_main_exports(pkg))
    types_section = _render_types(pkg)
    if types_section is not None:
        sections.append(types_section)
    sections.append(_render_dependencies(pkg))
    sections.append(_render_hazards(pkg, mode))
    sections.append(_render_usage_example(pkg, mode))
    sections.append(_render_consumer_pattern(pkg, mode))
    # Each section already ends with a newline; join with a blank line
    # in between so the markdown reads cleanly.
    return "\n".join(sections).rstrip() + "\n"


def _atomic_write_text(path: Path, text: str) -> None:
    """Write `text` to `path` atomically (mkstemp + os.replace).

    Per anti-pattern #4: never use a fixed-name temp file. Failure
    paths unlink the temp file before re-raising so partial writes
    don't accumulate alongside the target.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        prefix=".{0}.".format(path.name),
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Concern-tier render (Phase 3.1).
#
# Concern docs use the heading `## Public Surface` instead of
# `## Main Exports` (per ConcernDoc schema rename); fewer sections than
# package-tier (no Tech Stack, no Scripts, no Consumer Pattern). The
# Types section is always rendered (with `[TODO]` when empty) — concerns
# explicitly carry a `types: List[CodeBlock]` field whose intent is to
# surface type-shape contracts, so an unset slot needs a visible
# placeholder rather than silent omission. Required-field markers
# overlap with the package-tier list (REQUIRED_FIELD_TODO_MARKERS) and
# are reused; the Public Surface and Types sections share the
# `[TODO: ...]` shape with their package-tier counterparts where the
# wording makes sense, and use distinct concern-specific markers
# otherwise so validate-concern can distinguish them.
# ---------------------------------------------------------------------------


_TODO_PUBLIC_SURFACE = (
    "[TODO: enumerate concern's public surface via add-concern-export]"
)
_TODO_CONCERN_TYPES = (
    "[TODO: register concern types via add-concern-type, or leave empty "
    "if the concern surfaces no types]"
)
# Concern-tier shared-section TODOs reuse the package-tier prose where the
# guidance applies verbatim (e.g., dependency-internal-vs-external split is
# the same across tiers); only the CLI command name differs. The shared
# package-tier `_TODO_DEPENDENCIES` etc. cite package-tier setters which
# would mislead an LLM in concern context. Concern-specific copies below
# point at the right commands.
_TODO_CONCERN_DEPENDENCIES = (
    "[TODO: enumerate via add-concern-dep, or leave empty if the concern "
    "imports nothing]"
)
_TODO_CONCERN_HAZARDS = (
    "[TODO: list inline observations via add-concern-hazard, or leave "
    "empty if the concern has no observable mislogic]"
)
_TODO_CONCERN_USAGE_EXAMPLE = (
    "[TODO: lift a real usage example via set-concern-usage-example]"
)


# Required-field TODO markers for concerns. `_TODO_OVERVIEW` and
# `_TODO_TREE` are reused verbatim from the package tier (same shape,
# same prose); `_TODO_PUBLIC_SURFACE` is concern-specific. Public
# surface is a required field in `validate-concern`; types are
# explicitly optional.
CONCERN_REQUIRED_FIELD_TODO_MARKERS = (
    _TODO_OVERVIEW,
    _TODO_TREE,
    _TODO_PUBLIC_SURFACE,
)


# Concern-tier counterpart to OPTIONAL_SECTION_MARKERS (Phase 3.1
# defense-in-depth). The concern record has four optional sections —
# `types`, `dependencies`, `hazards`, `usage_example` — that exhibit
# the same render-bug failure mode the package-tier check guards
# against: state populated -> rendered `[TODO]` is a render bug, not
# a legitimate skip. Each tuple is (field, marker, is-empty-fn);
# `is_empty_fn` returns True when the state field is missing/empty
# (i.e., the [TODO] is a legitimate optional skip, not a render bug).
CONCERN_OPTIONAL_SECTION_MARKERS = (
    ("types", _TODO_CONCERN_TYPES, lambda v: not v),
    ("dependencies", _TODO_CONCERN_DEPENDENCIES, lambda v: not v),
    ("hazards", _TODO_CONCERN_HAZARDS, lambda v: not v),
    ("usage_example", _TODO_CONCERN_USAGE_EXAMPLE, lambda v: v is None),
)


def _render_concern_overview(concern: Dict[str, Any]) -> str:
    overview = concern.get("overview")
    body = _esc(overview) if overview else _TODO_OVERVIEW
    return "## Overview\n\n{0}\n".format(body)


def _render_concern_directory_tree(concern: Dict[str, Any]) -> str:
    tree = concern.get("directory_tree")
    body = tree if tree else _TODO_TREE
    return "## Directory Structure\n\n```\n{0}\n```\n".format(body)


def _render_concern_public_surface(concern: Dict[str, Any]) -> str:
    """Render `## Public Surface` (concern-tier counterpart of `## Main
    Exports`).

    Same Export-entry rendering as the package tier — a concern's
    `public_surface` field stores the same Export shape.
    """
    exports = concern.get("public_surface") or []
    if not exports:
        return "## Public Surface\n\n{0}\n".format(_TODO_PUBLIC_SURFACE)
    body_parts = ["## Public Surface", ""]
    for ex in exports:
        body_parts.append(_render_export_entry(ex))
    return "\n".join(body_parts).rstrip() + "\n"


def _render_concern_types(concern: Dict[str, Any], mode: str = "skeleton") -> str:
    """Render `## Types` for a concern.

    Unlike the package-tier Types section (which is omitted when empty
    because type-kind exports are normally absent), the concern-tier
    Types is a first-class field — render an explicit `[TODO]` slot
    when empty so the LLM sees the field exists. Validate-concern does
    NOT block on missing types (the [TODO] is in the optional list).
    In final mode, the empty slot becomes `_(none)_` instead.
    """
    types = concern.get("types") or []
    if not types:
        placeholder = _FINAL_NONE if mode == "final" else _TODO_CONCERN_TYPES
        return "## Types\n\n{0}\n".format(placeholder)
    body_parts = ["## Types", ""]
    for tb in types:
        body_parts.append(_render_code_block(tb))
    return "\n".join(body_parts).rstrip() + "\n"


def _render_concern_dependencies(concern: Dict[str, Any], mode: str = "skeleton") -> str:
    """Render `## Dependencies` — same internal/external split as
    package tier."""
    deps = concern.get("dependencies") or []
    internal = [d for d in deps if d.get("kind") == "internal"]
    external = [d for d in deps if d.get("kind") == "external"]
    if not internal and not external:
        placeholder = (
            _FINAL_NONE if mode == "final" else _TODO_CONCERN_DEPENDENCIES
        )
        return "## Dependencies\n\n{0}\n".format(placeholder)
    parts = ["## Dependencies", ""]
    parts.append("### Workspace-internal")
    parts.append("")
    if internal:
        for dep in internal:
            parts.append(_render_dependency_entry(dep))
    else:
        parts.append("_None._")
    parts.append("")
    parts.append("### External")
    parts.append("")
    if external:
        for dep in external:
            parts.append(_render_dependency_entry(dep))
    else:
        parts.append("_None._")
    parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def _render_concern_hazards(concern: Dict[str, Any], mode: str = "skeleton") -> str:
    hazards = concern.get("hazards") or []
    if not hazards:
        placeholder = _FINAL_NONE if mode == "final" else _TODO_CONCERN_HAZARDS
        return "## Hazards\n\n{0}\n".format(placeholder)
    parts = ["## Hazards", ""]
    for hazard in hazards:
        line = "- **{0}**: {1}".format(
            _esc(hazard["category"]), _esc(hazard["description"])
        )
        cite = hazard.get("cite")
        if cite:
            line = line + "  \n  cite: `{0}:{1}-{2}`".format(
                cite["file"], cite["start"], cite["end"]
            )
        parts.append(line)
    return "\n".join(parts) + "\n"


def _render_concern_usage_example(concern: Dict[str, Any], mode: str = "skeleton") -> str:
    ue = concern.get("usage_example")
    if not ue:
        placeholder = (
            _FINAL_NONE if mode == "final" else _TODO_CONCERN_USAGE_EXAMPLE
        )
        return "## Usage Example\n\n{0}\n".format(placeholder)
    return "## Usage Example\n\n" + _render_code_block(ue)


def render_concern_skeleton(
    state: Dict[str, Any],
    package_path: str,
    concern_name: str,
    mode: str = "skeleton",
) -> str:
    """Pure render function for ConcernDoc — returns a markdown string.

    Both `cmd_render_concern_skeleton` and `cmd_render_concern_doc` call
    this; the difference between the two is only the output path, whether
    validation gates the write, and the `mode` argument.

    `mode="skeleton"` (default): empty optional sections emit LLM-targeted
    setter-name [TODO] markers so the LLM knows which setter to call.
    `mode="final"`: empty optional sections emit `_(none)_` instead,
    so the rendered doc reads as documentation rather than an unfilled form.
    Required-field TODOs are unchanged in either mode.

    Output sections: H1 (concern name) -> Overview -> Directory ->
    Public Surface -> Types -> Dependencies -> Hazards -> Usage
    Example. No Tech Stack / Scripts / Consumer Pattern (those are
    package-tier only).
    """
    pkg = state["packages"].get(package_path)
    if pkg is None:
        raise KeyError(
            "package not registered at {0!r}".format(package_path)
        )
    concerns = pkg.get("concerns") or {}
    concern = concerns.get(concern_name)
    if concern is None:
        raise KeyError(
            "concern {0!r} not registered under {1!r}".format(
                concern_name, package_path,
            )
        )
    sections: List[str] = []
    sections.append("# {0}".format(concern_name))
    sections.append("")
    sections.append(_render_concern_overview(concern))
    sections.append(_render_concern_directory_tree(concern))
    sections.append(_render_concern_public_surface(concern))
    sections.append(_render_concern_types(concern, mode))
    sections.append(_render_concern_dependencies(concern, mode))
    sections.append(_render_concern_hazards(concern, mode))
    sections.append(_render_concern_usage_example(concern, mode))
    return "\n".join(sections).rstrip() + "\n"


def _project_root() -> Path:
    """Return the project root (parent of `.devforge`).

    Honors `DEVFORGE_PROJECT_ROOT` (test override) when set; otherwise
    derives from `DEVFORGE_DIR` (parent of state file). When neither is
    set, falls back to cwd.
    """
    root_env = os.environ.get("DEVFORGE_PROJECT_ROOT")
    if root_env:
        return Path(root_env)
    devforge_dir = os.environ.get("DEVFORGE_DIR")
    if devforge_dir:
        return Path(devforge_dir).parent
    return Path.cwd()


def cmd_render_package_skeleton(args: argparse.Namespace) -> int:
    """Render the skeleton (with [TODO] slots) to
    `docs/<path>/index.md.skeleton`."""
    try:
        state = _load_state()
    except StateLoadError as err:
        return _die(str(err), code=1)
    pkg = _require_package(state, args.path)
    if pkg is None:
        return _die(
            "package not registered at {0!r}; run add-package first".format(
                args.path
            )
        )
    try:
        markdown = render_package_skeleton(state, args.path)
    except KeyError as err:
        return _die(str(err))
    out_path = _project_root() / "docs" / args.path / "index.md.skeleton"
    try:
        _atomic_write_text(out_path, markdown)
    except OSError as err:
        return _die("cannot write {0}: {1}".format(out_path, err), code=1)
    _info(
        "render-package-skeleton at {0} -> {1}".format(args.path, out_path)
    )
    sys.stdout.write(str(out_path) + "\n")
    return 0


def cmd_render_concern_skeleton(args: argparse.Namespace) -> int:
    """Render the concern skeleton to
    `docs/<package_path>/<concern_name>/index.md.skeleton`.

    Output path choice: nest concern docs one directory level under the
    package so a single workspace can ship per-concern files alongside
    a package's `index.md`. The trailing component is always
    `index.md.skeleton` (vs. `<concern>.md.skeleton`) so the path-shape
    is a generalization of the package-tier convention rather than a
    cousin shape — file shape stays consistent across tiers.
    """
    try:
        state = _load_state()
    except StateLoadError as err:
        return _die(str(err), code=1)
    pkg = _require_package(state, args.package)
    if pkg is None:
        return _die(
            "package not registered at {0!r}; run add-package first".format(
                args.package
            )
        )
    concerns = pkg.get("concerns") or {}
    if args.concern not in concerns:
        return _die(
            "concern {0!r} not registered under {1}; run add-concern "
            "first".format(args.concern, args.package)
        )
    try:
        markdown = render_concern_skeleton(state, args.package, args.concern)
    except KeyError as err:
        return _die(str(err))
    out_path = (
        _project_root() / "docs" / args.package / args.concern
        / "index.md.skeleton"
    )
    try:
        _atomic_write_text(out_path, markdown)
    except OSError as err:
        return _die("cannot write {0}: {1}".format(out_path, err), code=1)
    _info(
        "render-concern-skeleton at {0}/{1} -> {2}".format(
            args.package, args.concern, out_path,
        )
    )
    sys.stdout.write(str(out_path) + "\n")
    return 0
