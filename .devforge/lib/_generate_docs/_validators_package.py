"""Package-tier validation rules: required fields, exports, dependencies,
CodeBlock filesystem checks, internal-dep resolution, enum paranoia, and
render-dependent orchestration.

Owns all package-tier validation including the render-coupled functions
(`_check_no_todos`, `_check_optional_render`, `validate_package`,
`cmd_validate_package`, `cmd_render_package_doc`) that reference
`render_package_skeleton` as a module-level name. Tests that monkey-patch
`render_package_skeleton` must patch on THIS module (or `_validators_package`
directly) for the patch to be in scope.

Imports shared helpers from `_validators_shared` and the decomposition gate
from `_validators_decomposition`.

Stdlib only. Targets Python 3.8+.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from generate_docs_schema import (
    DEPENDENCY_KINDS,
    EXPORT_KINDS,
    HAZARD_CATEGORIES,
)

from ._validators_decomposition import _check_decomposition
from ._validators_shared import (
    _check_codeblock,
    _err,
    _print_errors,
)
from ._render import (
    OPTIONAL_SECTION_MARKERS,
    REQUIRED_FIELD_TODO_MARKERS,
    _atomic_write_text,
    _project_root,
    render_package_skeleton,
)
from ._state import (
    StateLoadError,
    _die,
    _load_state,
    _require_package,
    _state_file_path,
)


# Name of the bootstrap artifact written by /init-forge. Living next to
# the helper's own state file under `<devforge>/`. Read-only here — this
# module never writes to init.yaml; init_helper owns that artifact's shape.
INIT_YAML_FILE_NAME = "init.yaml"


# Regex-based path extractor for init.yaml's `packages_detected[]` block.
# Matches any line that looks like `  - path: <value>` regardless of
# indentation depth. Closed shape produced by init_helper's emitter
# always uses 2-space indentation, so this matches in practice; the
# regex is intentionally permissive on indentation so a future emit-
# style tweak (e.g., 4-space) does not silently break resolution.
#
# We deliberately do NOT parse the full YAML. Stdlib has no YAML
# parser and pulling init_helper's parser in would create a circular
# import and an unwanted coupling between the validator and a different
# helper's full schema. Best-effort path extraction is the contract:
# any malformed input simply yields an empty list, callers fall back
# to the existing checks (registered packages + on-disk directory).
_PACKAGES_DETECTED_PATH_RE = re.compile(
    r"^\s*-\s*path:\s*(.+?)\s*$", re.MULTILINE
)


def _check_required_fields(pkg: Dict[str, Any]) -> List[Dict[str, Any]]:
    errors: List[Dict[str, Any]] = []
    for fname, setter in (
        ("overview", "set-package-overview"),
        ("directory_tree", "set-package-tree"),
        ("primary_language", "set-package-language"),
    ):
        value = pkg.get(fname)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            errors.append(_err(
                "required-fields", fname,
                "PackageDoc.{0} is unset (call {1})".format(fname, setter),
            ))
    return errors


def _check_at_least_one_export(pkg: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not (pkg.get("exports") or []):
        return [_err(
            "exports-nonempty", "exports",
            "package has no registered exports; call add-package-export "
            "at least once",
        )]
    return []


def _check_at_least_one_dependency(pkg: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not (pkg.get("dependencies") or []):
        return [_err(
            "dependencies-nonempty", "dependencies",
            "package has no registered dependencies; call add-package-dep "
            "at least once",
        )]
    return []


def _check_all_codeblocks(
    pkg: Dict[str, Any],
    project_root: Path,
) -> List[Dict[str, Any]]:
    """Run filesystem + verbatim-match checks across every CodeBlock in
    the record (exports, usage_example, consumer_pattern).

    Optional CodeBlock fields (`usage_example`, `consumer_pattern`) are
    treated as "absent" only when the stored value is `None` (the schema
    default). A non-None value of any other shape is a corrupted record
    and surfaces an explicit `*-malformed` error instead of being
    silently skipped (anti-pattern #2: validation must NOT defer).
    """
    errors: List[Dict[str, Any]] = []
    for idx, export in enumerate(pkg.get("exports") or []):
        code = export.get("code")
        if not isinstance(code, dict):
            errors.append(_err(
                "export-code-malformed", "exports[{0}].code".format(idx),
                "Export.code missing or not a dict",
            ))
            continue
        errors.extend(_check_codeblock(
            code, "exports[{0}].code".format(idx), project_root,
        ))
    for field_name in ("usage_example", "consumer_pattern"):
        value = pkg.get(field_name)
        if value is None:
            continue
        if not isinstance(value, dict) or not value:
            errors.append(_err(
                "{0}-malformed".format(field_name.replace("_", "-")),
                field_name,
                "{0} is set but is not a non-empty dict (got {1!r})".format(
                    field_name, value,
                ),
            ))
            continue
        errors.extend(_check_codeblock(value, field_name, project_root))
    return errors


def _load_packages_detected_paths(devforge_dir: Path) -> List[str]:
    """Extract `packages_detected[].path` strings from init.yaml.

    Best-effort, regex-based. Returns `[]` when the file is missing,
    unreadable, or contains no recognizable `- path: <value>` lines.
    No exception is propagated to the caller — internal-dep resolution
    is a fall-back chain and a missing init.yaml is a normal state for
    standalone projects that never ran /init-forge.

    Why regex (not the init_helper YAML parser): pulling init_helper's
    parser into the validator would create a cross-helper coupling
    that is much heavier than the single check we need. The init.yaml
    shape is locked (init_helper owns it; emitter is deterministic),
    so a 1-line regex is safe in practice — and any input outside the
    closed shape simply yields `[]`, which falls through to the
    existing resolution checks.
    """
    init_path = devforge_dir / INIT_YAML_FILE_NAME
    if not init_path.exists():
        return []
    try:
        text = init_path.read_text(encoding="utf-8")
    except OSError:
        return []
    paths: List[str] = []
    for match in _PACKAGES_DETECTED_PATH_RE.finditer(text):
        raw = match.group(1).strip()
        if not raw:
            continue
        # Defensive: strip surrounding double-quotes if init_helper
        # had to quote the path (e.g., a path containing a special
        # char). The emitter only quotes when `_needs_quoting` returns
        # True, but the validator should accept either form. When the
        # value is double-quoted, the comment-stripping pass below is
        # skipped — `#` inside a double-quoted YAML string is a literal
        # character, not a comment introducer.
        if len(raw) >= 2 and raw[0] == '"' and raw[-1] == '"':
            raw = raw[1:-1]
        else:
            # Strip an unquoted YAML inline comment: `path/x # note`
            # -> `path/x`. The space-before-`#` rule is the YAML
            # convention; a bare `#` immediately after content is NOT
            # a comment in YAML. Skipping comment-strip when no leading
            # space exists keeps legitimate paths like `foo#bar`
            # (rare but legal) intact.
            comment_idx = raw.find(" #")
            if comment_idx >= 0:
                raw = raw[:comment_idx].rstrip()
        if not raw:
            continue
        paths.append(raw)
    return paths


def _resolve_internal_dep(
    dep_name: str,
    state: Dict[str, Any],
    project_root: Path,
    devforge_dir: Path,
) -> bool:
    """Return True if the internal dep name resolves via any of three
    checks; False otherwise.

    Resolution order (first match wins):

    1. Another registered package's `name` OR `path` (current state).
    2. A directory at `<project_root>/<dep_name>`.
    3. A `packages_detected[].path` entry in `<devforge>/init.yaml`,
       matched as either the full path string OR its basename.

    The third check exists for monorepos where /init-forge populated
    init.yaml with all package paths but the LLM is documenting only
    one package at a time — sibling packages aren't yet registered in
    current state, and the on-disk dir is nested below project_root
    inside a workspace folder rather than directly at
    `<project_root>/<dep_name>`. testForge20's
    `module/packages/foo` shape was the concrete
    case that motivated this check.
    """
    # Check 1: registered packages in current state.
    registered_names = {
        rec.get("name") for rec in state.get("packages", {}).values()
    }
    registered_paths = set(state.get("packages", {}).keys())
    if dep_name in registered_names or dep_name in registered_paths:
        return True
    # Check 2: directory at project_root/dep_name.
    candidate = project_root / dep_name
    if candidate.is_dir():
        return True
    # Check 3: init.yaml's packages_detected[].path. Match basename
    # (covers the common case: dep is the bare package name) AND the
    # full path string (covers the case where the dep was registered
    # using its workspace-relative path verbatim).
    for path in _load_packages_detected_paths(devforge_dir):
        if path == dep_name:
            return True
        # Path-style basename: split on either `/` or `\` for safety.
        # An absolute path (defensive — init_helper rejects them at
        # set-time but parser-tolerant matching is cheap) has its
        # leading slash stripped before basename extraction.
        stripped = path.lstrip("/\\")
        normalized = stripped.replace("\\", "/")
        # Trailing-slash-tolerant: `foo/bar/` -> basename `bar`.
        normalized = normalized.rstrip("/")
        if not normalized:
            continue
        basename = normalized.rsplit("/", 1)[-1]
        if basename == dep_name:
            return True
    return False


def _check_internal_deps(
    state: Dict[str, Any],
    pkg: Dict[str, Any],
    project_root: Path,
    devforge_dir: Path,
) -> List[Dict[str, Any]]:
    """Every internal dep must resolve to either another registered
    package, an on-disk directory under the project root, OR a
    `packages_detected[]` entry in `.devforge/init.yaml`."""
    errors: List[Dict[str, Any]] = []
    for idx, dep in enumerate(pkg.get("dependencies") or []):
        if dep.get("kind") != "internal":
            continue
        name = dep.get("name", "")
        if _resolve_internal_dep(name, state, project_root, devforge_dir):
            continue
        candidate = project_root / name
        errors.append(_err(
            "internal-dep-unresolved",
            "dependencies[{0}]".format(idx),
            "internal dependency {0!r} does not match any registered "
            "package name/path, no directory exists at {1}, and no "
            "packages_detected entry in {2}/init.yaml matches".format(
                name, candidate, devforge_dir,
            ),
        ))
    return errors


def _check_enums(pkg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Re-verify enum membership for exports / dependencies / hazards.

    Field-level setters check this at boundary; we re-check at
    validate-time as a state-file-corruption guard.
    """
    errors: List[Dict[str, Any]] = []
    for idx, export in enumerate(pkg.get("exports") or []):
        kind = export.get("kind")
        if kind not in EXPORT_KINDS:
            errors.append(_err(
                "export-kind-invalid", "exports[{0}].kind".format(idx),
                "Export.kind {0!r} is not one of {1}".format(
                    kind, list(EXPORT_KINDS),
                ),
            ))
    for idx, dep in enumerate(pkg.get("dependencies") or []):
        kind = dep.get("kind")
        if kind not in DEPENDENCY_KINDS:
            errors.append(_err(
                "dep-kind-invalid", "dependencies[{0}].kind".format(idx),
                "Dependency.kind {0!r} is not one of {1}".format(
                    kind, list(DEPENDENCY_KINDS),
                ),
            ))
    for idx, hazard in enumerate(pkg.get("hazards") or []):
        category = hazard.get("category")
        if category not in HAZARD_CATEGORIES:
            errors.append(_err(
                "hazard-category-invalid",
                "hazards[{0}].category".format(idx),
                "Hazard.category {0!r} is not one of {1}".format(
                    category, list(HAZARD_CATEGORIES),
                ),
            ))
    return errors


# ---------------------------------------------------------------------------
# Render-dependent package-tier helpers.
# `render_package_skeleton` is a module-level name here; tests that patch
# this module's `render_package_skeleton` attribute correctly intercept all
# calls below.
# ---------------------------------------------------------------------------


def _check_no_todos(
    state: Dict[str, Any],
    package_path: str,
) -> List[Dict[str, Any]]:
    """Render the skeleton in-memory and assert no required-field
    `[TODO]` markers remain.

    Optional-section TODOs (scripts / hazards / usage_example /
    consumer_pattern) are deliberately ignored — those fields are
    schema-optional and a doc that omits them is still valid. Only
    markers from `REQUIRED_FIELD_TODO_MARKERS` (overview / directory
    tree / primary_language / exports / dependencies) gate the doc.
    """
    try:
        markdown = render_package_skeleton(state, package_path)
    except KeyError:
        # Package-existence check is the caller's job; don't
        # double-report.
        return []
    errors: List[Dict[str, Any]] = []
    for marker in REQUIRED_FIELD_TODO_MARKERS:
        if marker in markdown:
            errors.append(_err(
                "todo-marker-present", "rendered-skeleton",
                "rendered skeleton still contains a required-field [TODO] "
                "marker ({0!r}); one or more required setters has not "
                "been called".format(marker[:40]),
            ))
    return errors


def _check_optional_render(
    state: Dict[str, Any],
    pkg: Dict[str, Any],
    package_path: str,
) -> List[Dict[str, Any]]:
    """Catch render bugs in OPTIONAL sections (scripts / hazards /
    usage_example / consumer_pattern).

    A legitimate empty state -> rendered `[TODO]` is fine (the schema
    declares those fields optional). But state populated -> rendered
    `[TODO]` is a render bug: the data is there, the rendering is
    eating it. Without this check, the bug surfaces as a final doc
    that silently shows `[TODO]` placeholders next to populated state.

    Encountered concretely on testForge20 2026-04-30: 11 add-package-script
    invocations were lost to a state-write race; the rendered doc showed
    the optional Scripts [TODO] instead of the populated table. The
    state-write race is fixed in `_state._state_transaction()`; this
    check catches future regressions in the same family.
    """
    try:
        markdown = render_package_skeleton(state, package_path)
    except KeyError:
        return []
    errors: List[Dict[str, Any]] = []
    for field, marker, is_empty_fn in OPTIONAL_SECTION_MARKERS:
        if marker not in markdown:
            continue
        if is_empty_fn(pkg.get(field)):
            continue
        errors.append(_err(
            "optional-section-render-bug", field,
            "rendered output shows the optional [{0}] placeholder but "
            "state has populated data — render is eating registered "
            "values".format(field),
        ))
    return errors


def validate_package(
    state: Dict[str, Any],
    package_path: str,
    project_root: Path,
    devforge_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Return a list of error dicts (empty list = valid).

    All rules run unconditionally; errors are collected so the LLM
    sees the full picture in one pass instead of fix-one-rerun-find-
    next loops.

    `devforge_dir` is optional: when omitted, derived from the live
    state-file location (`_state_file_path().parent`). The arg is in
    the signature so tests can pin it deterministically without
    relying on env-var ordering.
    """
    pkg = _require_package(state, package_path)
    if pkg is None:
        return [_err(
            "package-not-registered", "package",
            "package not registered at {0!r}; run add-package first".format(
                package_path,
            ),
        )]
    if devforge_dir is None:
        devforge_dir = _state_file_path().parent
    errors: List[Dict[str, Any]] = []
    errors.extend(_check_required_fields(pkg))
    errors.extend(_check_at_least_one_export(pkg))
    errors.extend(_check_at_least_one_dependency(pkg))
    errors.extend(_check_all_codeblocks(pkg, project_root))
    errors.extend(_check_internal_deps(state, pkg, project_root, devforge_dir))
    errors.extend(_check_enums(pkg))
    errors.extend(_check_no_todos(state, package_path))
    errors.extend(_check_optional_render(state, pkg, package_path))
    errors.extend(_check_decomposition(pkg, package_path, project_root))
    return errors


def cmd_validate_package(args: argparse.Namespace) -> int:
    try:
        state = _load_state()
    except StateLoadError as err:
        return _die(str(err), code=1)
    errors = validate_package(state, args.path, _project_root())
    if not errors:
        return 0
    _print_errors(errors)
    return _die(
        "validate-package: {0} error(s) at {1}".format(
            len(errors), args.path,
        ),
    )


def cmd_render_package_doc(args: argparse.Namespace) -> int:
    """Render the FINAL doc to `docs/<path>/index.md`, gated by validate.

    Validation must pass with zero errors; on any error, the .md is
    NOT written and the existing .skeleton (if any) is retained. On
    success the .md is written atomically AND the .skeleton sibling
    is removed.
    """
    try:
        state = _load_state()
    except StateLoadError as err:
        return _die(str(err), code=1)
    if _require_package(state, args.path) is None:
        return _die(
            "package not registered at {0!r}; run add-package first".format(
                args.path,
            )
        )
    project_root = _project_root()
    errors = validate_package(state, args.path, project_root)
    if errors:
        _print_errors(errors)
        return _die(
            "render-package-doc: validation failed with {0} error(s) at "
            "{1}; .md NOT written".format(len(errors), args.path),
        )
    markdown = render_package_skeleton(state, args.path, mode="final")
    out_path = project_root / "docs" / args.path / "index.md"
    try:
        _atomic_write_text(out_path, markdown)
    except OSError as err:
        return _die("cannot write {0}: {1}".format(out_path, err), code=1)
    skeleton_path = out_path.parent / "index.md.skeleton"
    if skeleton_path.exists():
        try:
            skeleton_path.unlink()
        except OSError as err:
            return _die(
                "wrote {0} but failed to remove stale {1}: {2}".format(
                    out_path, skeleton_path, err,
                ), code=1,
            )
    sys.stdout.write(str(out_path) + "\n")
    return 0
