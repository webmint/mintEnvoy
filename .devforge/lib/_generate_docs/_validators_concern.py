"""Concern-tier validation rules: required fields, public surface, CodeBlock
checks, enum paranoia, file-doc completeness, and render-dependent orchestration.

Owns all concern-tier validation including the render-coupled functions
(`_check_concern_no_todos`, `_check_concern_optional_render`,
`validate_concern`, `cmd_validate_concern`, `cmd_render_concern_doc`) that
reference `render_concern_skeleton` as a module-level name. Tests that
monkey-patch `render_concern_skeleton` must patch on THIS module (or
`_validators_concern` directly) for the patch to be in scope.

Imports shared helpers from `_validators_shared`.

Stdlib only. Targets Python 3.8+.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from generate_docs_schema import (
    DEPENDENCY_KINDS,
    EXPORT_KINDS,
    HAZARD_CATEGORIES,
)

from ._validators_shared import (
    _check_codeblock,
    _err,
    _print_errors,
)
from ._render import (
    CONCERN_OPTIONAL_SECTION_MARKERS,
    CONCERN_REQUIRED_FIELD_TODO_MARKERS,
    _atomic_write_text,
    _project_root,
    render_concern_skeleton,
)
from ._setters_concern import _load_index_files, _path_contains_trivial_dir
from ._state import (
    StateLoadError,
    _die,
    _load_state,
    _require_concern,
    _require_package,
    _state_file_path,
)

# Minimum file size (in bytes) for a per-source-file .md to be considered
# non-empty. Exactly at threshold (== FILE_DOC_MIN_SIZE_BYTES) fails; must
# exceed the threshold (> FILE_DOC_MIN_SIZE_BYTES). Locked at 50 per
# VALIDATOR-LOOP-B-PLAN.md §B.2 — allows future raise without compat break.
FILE_DOC_MIN_SIZE_BYTES = 50


def _check_concern_required_fields(
    concern: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """ConcernDoc required-field check: overview + directory_tree."""
    errors: List[Dict[str, Any]] = []
    for fname, setter in (
        ("overview", "set-concern-overview"),
        ("directory_tree", "set-concern-tree"),
    ):
        value = concern.get(fname)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            errors.append(_err(
                "required-fields", fname,
                "ConcernDoc.{0} is unset (call {1})".format(fname, setter),
            ))
    return errors


def _check_concern_at_least_one_public_surface(
    concern: Dict[str, Any],
) -> List[Dict[str, Any]]:
    if not (concern.get("public_surface") or []):
        return [_err(
            "public-surface-nonempty", "public_surface",
            "concern has no registered public surface; call "
            "add-concern-export at least once",
        )]
    return []


def _check_concern_codeblocks(
    concern: Dict[str, Any], project_root: Path,
) -> List[Dict[str, Any]]:
    """Per-CodeBlock filesystem + verbatim-match across the concern.

    Covers public_surface[].code, types[] (each CodeBlock directly), and
    the optional usage_example.
    """
    errors: List[Dict[str, Any]] = []
    for idx, export in enumerate(concern.get("public_surface") or []):
        code = export.get("code")
        field_label = "public_surface[{0}].code".format(idx)
        if not isinstance(code, dict):
            errors.append(_err(
                "export-code-malformed", field_label,
                "Export.code missing or not a dict",
            ))
            continue
        errors.extend(_check_codeblock(code, field_label, project_root))
    for idx, tb in enumerate(concern.get("types") or []):
        if not isinstance(tb, dict):
            errors.append(_err(
                "type-codeblock-malformed", "types[{0}]".format(idx),
                "ConcernDoc.types[{0}] must be a dict".format(idx),
            ))
            continue
        errors.extend(_check_codeblock(
            tb, "types[{0}]".format(idx), project_root,
        ))
    usage = concern.get("usage_example")
    if usage is not None:
        if not isinstance(usage, dict) or not usage:
            errors.append(_err(
                "usage-example-malformed", "usage_example",
                "usage_example is set but is not a non-empty dict (got "
                "{0!r})".format(usage),
            ))
        else:
            errors.extend(_check_codeblock(
                usage, "usage_example", project_root,
            ))
    return errors


def _check_file_docs_complete(
    package_path: str,
    concern_name: str,
    project_root: Path,
    devforge_dir: Path,
) -> List[Dict[str, Any]]:
    """Gate: every expected per-source-file .md must exist and exceed
    FILE_DOC_MIN_SIZE_BYTES.

    Expected set = index.json files filtered to src/<concern>/, trivial-leaf
    excluded, empty-suffix excluded. Each maps to:
      project_root/docs/<package>/<concern>/<suffix>.md

    Graceful degrade (return []) on missing/unreadable index.json or package
    not in index — validate-concern is a quality gate, not a structural
    prerequisite; the rest of the rule chain must still run.

    Returns a single error dict (aggregated) or empty list on pass.
    """
    files = _load_index_files(devforge_dir, package_path)
    if files is None:
        # Graceful degrade — see B.2 §plan. index.json is optional from
        # validate-concern's perspective; render-file-skeletons is the hard
        # gated command that requires it.
        sys.stderr.write(
            "validate-concern: file-docs-incomplete check skipped"
            " — index.json missing or package not in index\n"
        )
        return []

    subfolder_prefix = "src/{0}/".format(concern_name)

    expected_paths = []  # List of (expected_md_path, suffix) tuples
    for rel_path in files:
        if not rel_path.startswith(subfolder_prefix):
            continue
        if _path_contains_trivial_dir(rel_path):
            continue
        suffix = rel_path[len(subfolder_prefix):]
        if not suffix:
            continue
        expected_md = (
            project_root / "docs" / package_path / concern_name / (suffix + ".md")
        )
        expected_paths.append(expected_md)

    if not expected_paths:
        return []

    missing = []
    empty = []
    for md_path in expected_paths:
        if not md_path.exists():
            missing.append(md_path)
        elif os.path.getsize(str(md_path)) <= FILE_DOC_MIN_SIZE_BYTES:
            empty.append(md_path)

    if not missing and not empty:
        return []

    # Aggregate all offenders into a single error dict (single-error contract).
    total_bad = len(missing) + len(empty)
    total_expected = len(expected_paths)

    # Collect up to 5 representative offenders for the message.
    offenders = []
    for p in missing[:5]:
        try:
            rel = p.relative_to(project_root)
        except ValueError:
            rel = p
        offenders.append("MISSING: {0}".format(rel))
    remaining = 5 - len(offenders)
    if remaining > 0:
        for p in empty[:remaining]:
            try:
                rel = p.relative_to(project_root)
            except ValueError:
                rel = p
            offenders.append("EMPTY: {0}".format(rel))

    # Check whether any skeletons exist in docs/<P>/<C>/ at all.
    docs_concern_dir = project_root / "docs" / package_path / concern_name
    any_skeletons_on_disk = (
        docs_concern_dir.exists()
        and any(docs_concern_dir.rglob("*.md"))
    )

    parts = [
        "{0} of {1} file docs incomplete".format(total_bad, total_expected),
    ]
    # Prepend "no skeletons rendered" guidance when any offender is MISSING
    # and there are no .md files at all in the concern docs dir — indicates
    # render-file-skeletons was never run (vs. fill loop skipped).
    if missing and not any_skeletons_on_disk:
        parts.insert(0, "no skeletons rendered, run render-file-skeletons first")

    parts.append("first 5 offenders: " + "; ".join(offenders))
    parts.append(
        "run render-file-skeletons (skeletons missing) and the per-md fill"
        " loop (skeletons unfilled); see VALIDATOR-LOOP-B-PLAN.md §B.3"
    )

    return [_err(
        "file-docs-incomplete",
        "file_docs",
        " | ".join(parts),
    )]


def _check_concern_enums(concern: Dict[str, Any]) -> List[Dict[str, Any]]:
    errors: List[Dict[str, Any]] = []
    for idx, export in enumerate(concern.get("public_surface") or []):
        kind = export.get("kind")
        if kind not in EXPORT_KINDS:
            errors.append(_err(
                "export-kind-invalid",
                "public_surface[{0}].kind".format(idx),
                "Export.kind {0!r} is not one of {1}".format(
                    kind, list(EXPORT_KINDS),
                ),
            ))
    for idx, dep in enumerate(concern.get("dependencies") or []):
        kind = dep.get("kind")
        if kind not in DEPENDENCY_KINDS:
            errors.append(_err(
                "dep-kind-invalid", "dependencies[{0}].kind".format(idx),
                "Dependency.kind {0!r} is not one of {1}".format(
                    kind, list(DEPENDENCY_KINDS),
                ),
            ))
    for idx, hazard in enumerate(concern.get("hazards") or []):
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
# Render-dependent concern-tier helpers.
# `render_concern_skeleton` is a module-level name here; tests that patch
# this module's `render_concern_skeleton` attribute correctly intercept all
# calls below.
# ---------------------------------------------------------------------------


def _check_concern_no_todos(
    state: Dict[str, Any], package_path: str, concern_name: str,
) -> List[Dict[str, Any]]:
    """Render the concern skeleton in-memory and assert no required-field
    `[TODO]` markers remain."""
    try:
        markdown = render_concern_skeleton(state, package_path, concern_name)
    except KeyError:
        return []
    errors: List[Dict[str, Any]] = []
    for marker in CONCERN_REQUIRED_FIELD_TODO_MARKERS:
        if marker in markdown:
            errors.append(_err(
                "todo-marker-present", "rendered-skeleton",
                "rendered concern skeleton still contains a required-field "
                "[TODO] marker ({0!r}); one or more required setters has "
                "not been called".format(marker[:40]),
            ))
    return errors


def _check_concern_optional_render(
    state: Dict[str, Any],
    concern: Dict[str, Any],
    package_path: str,
    concern_name: str,
) -> List[Dict[str, Any]]:
    """Concern-tier counterpart of `_check_optional_render` (Phase 3.1
    defense-in-depth).

    A legitimate empty state -> rendered `[TODO]` is fine (the four
    concern-tier optional fields — types / dependencies / hazards /
    usage_example — are all explicitly optional in the schema). But
    state populated -> rendered `[TODO]` is a render bug: the data is
    there, the rendering is eating it. Without this check, the bug
    surfaces as a final concern doc that silently shows `[TODO]`
    placeholders next to populated state.

    Mirrors the package-tier check added 2026-04-30 after the
    testForge20 race-condition incident; the same failure mode applies
    to concerns and would silently ship without this guard.
    """
    try:
        markdown = render_concern_skeleton(state, package_path, concern_name)
    except KeyError:
        # Existence check is the caller's job; don't double-report.
        return []
    errors: List[Dict[str, Any]] = []
    for field, marker, is_empty_fn in CONCERN_OPTIONAL_SECTION_MARKERS:
        if marker not in markdown:
            continue
        if is_empty_fn(concern.get(field)):
            continue
        errors.append(_err(
            "concern-optional-render-mismatch", field,
            "rendered concern output shows the optional [{0}] placeholder "
            "but state has populated data — render is eating registered "
            "values".format(field),
        ))
    return errors


def validate_concern(
    state: Dict[str, Any],
    package_path: str,
    concern_name: str,
    project_root: Path,
) -> List[Dict[str, Any]]:
    """Return a list of error dicts for one concern (empty list = valid)."""
    if _require_package(state, package_path) is None:
        return [_err(
            "package-not-registered", "package",
            "package not registered at {0!r}; run add-package first".format(
                package_path,
            ),
        )]
    concern = _require_concern(state, package_path, concern_name)
    if concern is None:
        return [_err(
            "concern-not-registered", "concern",
            "concern {0!r} not registered under {1!r}; run add-concern "
            "first".format(concern_name, package_path),
        )]
    errors: List[Dict[str, Any]] = []
    errors.extend(_check_concern_required_fields(concern))
    errors.extend(_check_concern_at_least_one_public_surface(concern))
    errors.extend(_check_concern_codeblocks(concern, project_root))
    errors.extend(_check_concern_enums(concern))
    # _check_file_docs_complete is dormant (Part D revert, 2026-05-07).
    # Per-file md primitive proved overkill on testForge20 empirical; reverted
    # to concern-level fill with inline tree descriptions. Function kept
    # defined for future revival via batch dispatch over CBM query_graph.
    errors.extend(_check_concern_no_todos(state, package_path, concern_name))
    errors.extend(_check_concern_optional_render(
        state, concern, package_path, concern_name,
    ))
    return errors


def cmd_validate_concern(args: argparse.Namespace) -> int:
    try:
        state = _load_state()
    except StateLoadError as err:
        return _die(str(err), code=1)
    errors = validate_concern(
        state, args.package, args.concern, _project_root(),
    )
    if not errors:
        return 0
    _print_errors(errors)
    return _die(
        "validate-concern: {0} error(s) at {1}/{2}".format(
            len(errors), args.package, args.concern,
        ),
    )


def cmd_render_concern_doc(args: argparse.Namespace) -> int:
    """Render the FINAL concern doc to
    `docs/<package>/<concern>/index.md`, gated by validate-concern.

    Validation must pass with zero errors; on any error, the .md is
    NOT written and the existing .skeleton (if any) is retained. On
    success the .md is written atomically AND the .skeleton sibling
    is removed.
    """
    try:
        state = _load_state()
    except StateLoadError as err:
        return _die(str(err), code=1)
    if _require_package(state, args.package) is None:
        return _die(
            "package not registered at {0!r}; run add-package first".format(
                args.package,
            )
        )
    if _require_concern(state, args.package, args.concern) is None:
        return _die(
            "concern {0!r} not registered under {1}; run add-concern "
            "first".format(args.concern, args.package)
        )
    project_root = _project_root()
    errors = validate_concern(
        state, args.package, args.concern, project_root,
    )
    if errors:
        _print_errors(errors)
        return _die(
            "render-concern-doc: validation failed with {0} error(s) at "
            "{1}/{2}; .md NOT written".format(
                len(errors), args.package, args.concern,
            ),
        )
    markdown = render_concern_skeleton(state, args.package, args.concern, mode="final")
    out_path = (
        project_root / "docs" / args.package / args.concern / "index.md"
    )
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
