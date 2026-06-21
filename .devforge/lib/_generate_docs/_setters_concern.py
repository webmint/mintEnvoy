"""Concern-tier field setters (Phase 3.1).

Mirrors `_setters.py` shape for the ConcernDoc schema (see
`generate_docs_schema.ConcernDoc`). Each handler reads state, locates
the (package, concern) target, validates input field-by-field via
`_validation`, mutates the concern record, and writes state atomically
through `_state_transaction`.

Why a sibling module rather than appending to `_setters.py`: the prior
file sat at ~580 lines (in the documented "plan-a-split" zone, hard
threshold 600). Adding ~400 lines of concern-tier setters would push
it well past the threshold, so per its own splitting plan we land
concern-tier code here. Package-tier setters keep their home in
`_setters.py`; the two modules are siblings of equal status.

Split status (2026-05-06): Fix B added ~241 lines of tree-coverage helpers
(`_load_index_files`, `_path_contains_trivial_dir`,
`_build_expected_entry_set`, `_count_rendered_tree_entries`,
`_check_tree_entry_coverage`) to satisfy `set-concern-tree`'s coverage
gate. Module is now 828 lines, past the 600 threshold by 38%. Planned
next split: extract the 5 coverage helpers into
`_setters_concern_coverage.py`. The NEXT addition to this module must
execute that split first — do not add another setter or helper without
splitting.

Idempotency policy mirrors the package tier:

- `add-concern` for an already-registered (package, concern_name) pair
  is rejected (exit 2).
- Single-field setters (`set-concern-overview`, `set-concern-tree`,
  `set-concern-usage-example`) ARE idempotent — latest value wins.
- Append-shaped setters (`add-concern-export`, `add-concern-type`,
  `add-concern-dep`, `add-concern-hazard`) reject duplicates by their
  natural key:
    - export: `(name, cite_file, cite_start)`
    - type:   `(cite_file, cite_start)`
    - dep:    `name`
    - hazard: `(category, description, cite_file, cite_start)`.

  Note: this hazard-dedup policy diverges INTENTIONALLY from package-tier
  `add-package-hazard`, which always appends (no dedup) — see
  `_setters.py` docstring. Concern-tier dedup was added because per-
  concern hazard lists tend to be smaller and an accidental
  re-invocation duplicates a single bullet visibly; package-tier hazard
  lists span the full package and treat repeated observations as
  separate findings. Two hazards with the same 4-tuple are dedup'd
  here; two with the same prose but different cites remain distinct.

Stdlib only. Targets Python 3.8+.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from generate_docs_schema import (
    DEPENDENCY_KINDS,
    EXPORT_KINDS,
    HAZARD_CATEGORIES,
)

from ._state import (
    StateLoadError,
    _AbortTransaction,
    _die,
    _info,
    _require_concern,
    _require_package,
    _state_file_path,
    _state_transaction,
    default_concern_record,
)
from ._validation import (
    _validate_in_enum,
    _validate_line_range,
    _validate_optional_string,
    _validate_string,
)


# ---------------------------------------------------------------------------
# Tree-entry coverage check constants for set-concern-tree --text.
#
# TREE_ENTRY_COVERAGE_THRESHOLD: minimum ratio of rendered entries to
#   expected entries (from index.json) below which set-concern-tree rejects
#   the text. Locked at 0.80 — allows 20% slack for legitimate skip-rule
#   exemptions beyond the explicit list.
#
# _TRIVIAL_LEAF_DIRS: directory components that indicate a trivial/generated
#   subtree. Any file path containing one of these as a path component is
#   excluded from the expected-entry count.
#
# _CANONICAL_AGGREGATORS: filenames that are counted as tree entries (NOT
#   excluded from expected count) even though the annotation loop skips them
#   for per-entry description. They are legitimate tree members.
# ---------------------------------------------------------------------------

TREE_ENTRY_COVERAGE_THRESHOLD = 0.80  # 80% — locked constant; do NOT tune via flag

_TRIVIAL_LEAF_DIRS = frozenset({
    "assets", "dist", "target", "bin", "obj", "node_modules",
    "__pycache__", ".venv", "vendor", "locales", "__generated__",
    "fixtures", "i18n", "static", "build",
})

_CANONICAL_AGGREGATORS = frozenset({
    "mod.rs", "lib.rs", "__init__.py", "index.ts", "index.js", "doc.go",
})

_INDEX_FILE_NAME = "index.json"

# Glyphs used in ASCII tree output — each entry line contains at least one.
_TREE_GLYPHS = ("├", "└", "│")


def _load_index_files(devforge_dir: Path, pkg_path: str) -> Optional[List[str]]:
    """Load files list for pkg_path from index.json. Return None on failure.

    Returns None (degrade gracefully) when:
      - index.json is missing
      - index.json is malformed JSON
      - pkg_path not in index.json["packages"] (after progressive-suffix match)

    Progressive-suffix match: state may register a package with a monorepo
    prefix (e.g., `module/apps/app`) while index.json keys
    are package-relative (e.g., `apps/app`). Try the literal path
    first, then strip leading path components one at a time until a hit
    or exhaustion. First match wins.
    """
    index_path = devforge_dir / _INDEX_FILE_NAME
    if not index_path.exists():
        return None
    try:
        text = index_path.read_text(encoding="utf-8")
        index = json.loads(text)
    except (OSError, json.JSONDecodeError):
        return None
    packages = index.get("packages")
    if not isinstance(packages, dict):
        return None
    pkg_record = None
    parts = pkg_path.split("/")
    for start in range(len(parts)):
        candidate = "/".join(parts[start:])
        candidate_record = packages.get(candidate)
        if isinstance(candidate_record, dict):
            pkg_record = candidate_record
            break
    if pkg_record is None:
        return None
    files = pkg_record.get("files")
    if not isinstance(files, list):
        return None
    return files


def _path_contains_trivial_dir(rel_path: str) -> bool:
    """Return True if any path component of rel_path is a trivial-leaf dir."""
    parts = Path(rel_path).parts
    for part in parts:
        if part in _TRIVIAL_LEAF_DIRS:
            return True
    return False


def _build_expected_entry_set(files: List[str], subfolder_prefix: str) -> int:
    """Count expected tree entries for files under subfolder_prefix.

    For each file under subfolder_prefix (excluding trivial-leaf paths),
    enumerate both the file itself AND all intermediate directory components
    between the subfolder root and the file. Returns the count of the union
    set (files + intermediate dirs), capped: trivial-leaf paths fully excluded.

    subfolder_prefix must end with "/" for unambiguous prefix matching.
    """
    entry_set = set()
    for rel_path in files:
        # Must start with the subfolder prefix to be in scope.
        if not rel_path.startswith(subfolder_prefix):
            continue
        # Exclude any path that passes through a trivial-leaf directory.
        if _path_contains_trivial_dir(rel_path):
            continue
        # Enumerate the file itself and intermediate directories between the
        # subfolder root and the file.
        suffix = rel_path[len(subfolder_prefix):]  # strip the subfolder prefix
        parts = suffix.split("/")
        for i in range(1, len(parts) + 1):
            component = "/".join(parts[:i])
            entry_set.add(component)
    return len(entry_set)


def _count_rendered_tree_entries(tree_text: str) -> int:
    """Count non-header lines in tree_text that contain a tree glyph.

    Each annotated tree entry is on a line containing at least one of
    ├, └, or │. Header lines (e.g., "src/components/") do not contain
    these glyphs and are naturally excluded.
    """
    count = 0
    for line in tree_text.splitlines():
        if any(glyph in line for glyph in _TREE_GLYPHS):
            count += 1
    return count


def _check_tree_entry_coverage(
    tree_text: str,
    pkg_path: str,
    concern_name: str,
    devforge_dir: Path,
) -> Optional[str]:
    """Return an error message if tree coverage is below threshold, or None on pass.

    Derives the expected subfolder as "src/<concern_name>" relative to the
    package. Degrades gracefully (returns None with a warning to stderr) when:
      - index.json is missing
      - pkg_path not found in index.json
      - subfolder lookup yields zero files (path mismatch or unregistered)
      - expected_count <= 5 (small concern — ratio is noisy)

    Never raises; all failure paths return None (allow the setter to proceed).
    """
    files = _load_index_files(devforge_dir, pkg_path)
    if files is None:
        sys.stderr.write(
            "set-concern-tree: tree-entry coverage check skipped"
            " — index.json missing or subfolder lookup empty\n"
        )
        return None

    # Convention: concern subfolder = src/<concern_name>/ relative to pkg.
    subfolder_prefix = "src/{0}/".format(concern_name)
    expected_count = _build_expected_entry_set(files, subfolder_prefix)

    if expected_count == 0:
        sys.stderr.write(
            "set-concern-tree: tree-entry coverage check skipped"
            " — no files found under {0} in index.json"
            " (concern name / subfolder convention mismatch?)\n".format(
                subfolder_prefix
            )
        )
        return None

    # Small-concern guard: don't apply ratio gate when expected is tiny.
    if expected_count <= 5:
        return None

    rendered_count = _count_rendered_tree_entries(tree_text)
    coverage = rendered_count / expected_count

    if coverage < TREE_ENTRY_COVERAGE_THRESHOLD:
        pct = round(coverage * 100, 1)
        threshold_pct = round(TREE_ENTRY_COVERAGE_THRESHOLD * 100, 1)
        return (
            "set-concern-tree: tree coverage {pct}% below threshold"
            " {threshold_pct}% — rendered {rendered} entries, expected"
            " {expected} (concern={concern}, subfolder=src/{concern})."
            " The strict spec mandate \"EVERY entry at EVERY depth\" was not"
            " satisfied; recurse into subfolders or document missing"
            " entries.".format(
                pct=pct,
                threshold_pct=threshold_pct,
                rendered=rendered_count,
                expected=expected_count,
                concern=concern_name,
            )
        )
    return None


def _devforge_dir_from_state_path() -> Path:
    """Return the .devforge directory by resolving the state file path."""
    return _state_file_path().parent


# ---------------------------------------------------------------------------
# Subcommand: add-concern.
# ---------------------------------------------------------------------------


def cmd_add_concern(args: argparse.Namespace) -> int:
    """Register a concern under a package. Idempotency: re-adding the
    same (package, concern_name) is rejected (exit 2)."""
    try:
        _validate_string(args.package, "add-concern --package")
        _validate_string(args.concern, "add-concern --concern")
    except ValueError as err:
        return _die(str(err))
    try:
        with _state_transaction() as state:
            pkg = _require_package(state, args.package)
            if pkg is None:
                raise _AbortTransaction(_die(
                    "package not registered at {0!r}; run add-package "
                    "first".format(args.package)
                ))
            # Phase 3.1 migration: defensive backfill for any in-memory
            # state that hasn't gone through `_load_state` yet.
            if "concerns" not in pkg or pkg["concerns"] is None:
                pkg["concerns"] = {}
            if args.concern in pkg["concerns"]:
                raise _AbortTransaction(_die(
                    "concern {0!r} already registered under {1}; use a "
                    "different name or reset".format(
                        args.concern, args.package,
                    )
                ))
            pkg["concerns"][args.concern] = default_concern_record(args.concern)
    except _AbortTransaction as ab:
        return ab.code
    except StateLoadError as err:
        return _die(str(err), code=1)
    except OSError as err:
        return _die("cannot write state: {0}".format(err), code=1)
    _info("add-concern {0} under {1}".format(args.concern, args.package))
    return 0


# ---------------------------------------------------------------------------
# Per-concern scalar setters.
# ---------------------------------------------------------------------------


def _set_concern_scalar(
    args: argparse.Namespace,
    field_name: str,
    field_label: str,
    multiline: bool,
) -> int:
    """Common path for scalar concern setters (overview, directory_tree).

    Both fields are required (no optional/empty-clears variant — the
    schema declares them required). Multi-line is `True` for both.
    """
    try:
        _validate_string(args.text, field_label, multiline=multiline)
    except ValueError as err:
        return _die(str(err))
    try:
        with _state_transaction() as state:
            pkg = _require_package(state, args.package)
            if pkg is None:
                raise _AbortTransaction(_die(
                    "package not registered at {0!r}; run add-package "
                    "first".format(args.package)
                ))
            concerns = pkg.get("concerns") or {}
            concern = concerns.get(args.concern)
            if concern is None:
                raise _AbortTransaction(_die(
                    "concern {0!r} not registered under {1}; run "
                    "add-concern first".format(args.concern, args.package)
                ))
            concern[field_name] = args.text
    except _AbortTransaction as ab:
        return ab.code
    except StateLoadError as err:
        return _die(str(err), code=1)
    except OSError as err:
        return _die("cannot write state: {0}".format(err), code=1)
    _info(
        "{0} {1}/{2} ({3} chars)".format(
            field_label.split(" ")[0], args.package, args.concern,
            len(args.text),
        )
    )
    return 0


def cmd_set_concern_overview(args: argparse.Namespace) -> int:
    return _set_concern_scalar(
        args, "overview", "set-concern-overview --text", multiline=True,
    )


def cmd_set_concern_tree(args: argparse.Namespace) -> int:
    """Set the directory_tree field on a concern.

    Extends the base scalar setter with a tree-entry coverage check:
    after character-class validation passes, the rendered entry count is
    compared against the expected count derived from index.json. If
    coverage is below TREE_ENTRY_COVERAGE_THRESHOLD AND the concern has
    more than 5 expected entries, the setter rejects the text with exit 2.

    Degrades gracefully when index.json is absent or the concern's
    subfolder is not found in the index — the coverage check is skipped
    and a warning is emitted to stderr. This preserves the existing
    behavior for projects without `init-forge build-index` history.
    """
    # Step 1: character-class validation (multiline allowed, no other control chars).
    try:
        _validate_string(args.text, "set-concern-tree --text", multiline=True)
    except ValueError as err:
        return _die(str(err))

    # Step 2: tree-entry coverage check against index.json.
    devforge_dir = _devforge_dir_from_state_path()
    coverage_err = _check_tree_entry_coverage(
        args.text, args.package, args.concern, devforge_dir,
    )
    if coverage_err is not None:
        sys.stderr.write("generate_docs_helper: {0}\n".format(coverage_err))
        return 2

    # Step 3: write to state (same as _set_concern_scalar).
    try:
        with _state_transaction() as state:
            pkg = _require_package(state, args.package)
            if pkg is None:
                raise _AbortTransaction(_die(
                    "package not registered at {0!r}; run add-package "
                    "first".format(args.package)
                ))
            concerns = pkg.get("concerns") or {}
            concern = concerns.get(args.concern)
            if concern is None:
                raise _AbortTransaction(_die(
                    "concern {0!r} not registered under {1}; run "
                    "add-concern first".format(args.concern, args.package)
                ))
            concern["directory_tree"] = args.text
    except _AbortTransaction as ab:
        return ab.code
    except StateLoadError as err:
        return _die(str(err), code=1)
    except OSError as err:
        return _die("cannot write state: {0}".format(err), code=1)
    _info(
        "set-concern-tree {0}/{1} ({2} chars)".format(
            args.package, args.concern, len(args.text),
        )
    )
    return 0


# ---------------------------------------------------------------------------
# Subcommand: add-concern-export.
# ---------------------------------------------------------------------------


def cmd_add_concern_export(args: argparse.Namespace) -> int:
    try:
        _validate_string(args.package, "add-concern-export --package")
        _validate_string(args.concern, "add-concern-export --concern")
        _validate_string(args.name, "add-concern-export --name")
        _validate_string(args.kind, "add-concern-export --kind")
        _validate_in_enum(
            args.kind, EXPORT_KINDS, "add-concern-export --kind",
        )
        signature = _validate_optional_string(
            args.signature, "add-concern-export --signature"
        )
        _validate_string(
            args.description, "add-concern-export --description",
            multiline=True,
        )
        _validate_string(args.language, "add-concern-export --language")
        _validate_string(
            args.code_snippet, "add-concern-export --code-snippet",
            multiline=True,
        )
        _validate_string(args.cite_file, "add-concern-export --cite-file")
        _validate_line_range(
            args.cite_start, args.cite_end, "add-concern-export cite",
        )
    except ValueError as err:
        return _die(str(err))
    try:
        with _state_transaction() as state:
            concern = _require_concern(state, args.package, args.concern)
            if concern is None:
                # Distinguish package-missing vs concern-missing for the
                # operator — same dual-message strategy as the scalar
                # setters above.
                if _require_package(state, args.package) is None:
                    raise _AbortTransaction(_die(
                        "package not registered at {0!r}; run add-package "
                        "first".format(args.package)
                    ))
                raise _AbortTransaction(_die(
                    "concern {0!r} not registered under {1}; run "
                    "add-concern first".format(args.concern, args.package)
                ))
            for existing in concern["public_surface"]:
                if (
                    existing["name"] == args.name
                    and existing["code"]["cite"]["file"] == args.cite_file
                    and existing["code"]["cite"]["start"] == args.cite_start
                ):
                    raise _AbortTransaction(_die(
                        "export {0!r} at {1}:{2} already registered under "
                        "{3}/{4}; use a different name or different "
                        "cite".format(
                            args.name, args.cite_file, args.cite_start,
                            args.package, args.concern,
                        )
                    ))
            concern["public_surface"].append(
                {
                    "name": args.name,
                    "kind": args.kind,
                    "signature": signature,
                    "description": args.description,
                    "code": {
                        "language": args.language,
                        "snippet": args.code_snippet,
                        "cite": {
                            "file": args.cite_file,
                            "start": args.cite_start,
                            "end": args.cite_end,
                        },
                    },
                }
            )
    except _AbortTransaction as ab:
        return ab.code
    except StateLoadError as err:
        return _die(str(err), code=1)
    except OSError as err:
        return _die("cannot write state: {0}".format(err), code=1)
    _info(
        "add-concern-export {0} under {1}/{2} (cite={3}:{4}-{5})".format(
            args.name, args.package, args.concern,
            args.cite_file, args.cite_start, args.cite_end,
        )
    )
    return 0


# ---------------------------------------------------------------------------
# Subcommand: add-concern-type.
#
# Concern-tier types are bare CodeBlocks (per schema:
# `ConcernDoc.types: List[CodeBlock]`) — no name/kind/signature like
# Export. Dedup by `(cite_file, cite_start)` — there is no `name` to
# include in the natural key.
# ---------------------------------------------------------------------------


def cmd_add_concern_type(args: argparse.Namespace) -> int:
    try:
        _validate_string(args.package, "add-concern-type --package")
        _validate_string(args.concern, "add-concern-type --concern")
        _validate_string(args.language, "add-concern-type --language")
        _validate_string(
            args.code_snippet, "add-concern-type --code-snippet",
            multiline=True,
        )
        _validate_string(args.cite_file, "add-concern-type --cite-file")
        _validate_line_range(
            args.cite_start, args.cite_end, "add-concern-type cite",
        )
    except ValueError as err:
        return _die(str(err))
    try:
        with _state_transaction() as state:
            concern = _require_concern(state, args.package, args.concern)
            if concern is None:
                if _require_package(state, args.package) is None:
                    raise _AbortTransaction(_die(
                        "package not registered at {0!r}; run add-package "
                        "first".format(args.package)
                    ))
                raise _AbortTransaction(_die(
                    "concern {0!r} not registered under {1}; run "
                    "add-concern first".format(args.concern, args.package)
                ))
            for existing in concern["types"]:
                cite = existing.get("cite") or {}
                if (
                    cite.get("file") == args.cite_file
                    and cite.get("start") == args.cite_start
                ):
                    raise _AbortTransaction(_die(
                        "type at {0}:{1} already registered under {2}/{3}; "
                        "use a different cite".format(
                            args.cite_file, args.cite_start,
                            args.package, args.concern,
                        )
                    ))
            concern["types"].append(
                {
                    "language": args.language,
                    "snippet": args.code_snippet,
                    "cite": {
                        "file": args.cite_file,
                        "start": args.cite_start,
                        "end": args.cite_end,
                    },
                }
            )
    except _AbortTransaction as ab:
        return ab.code
    except StateLoadError as err:
        return _die(str(err), code=1)
    except OSError as err:
        return _die("cannot write state: {0}".format(err), code=1)
    _info(
        "add-concern-type under {0}/{1} (cite={2}:{3}-{4})".format(
            args.package, args.concern,
            args.cite_file, args.cite_start, args.cite_end,
        )
    )
    return 0


# ---------------------------------------------------------------------------
# Subcommand: add-concern-dep.
# ---------------------------------------------------------------------------


def cmd_add_concern_dep(args: argparse.Namespace) -> int:
    try:
        _validate_string(args.package, "add-concern-dep --package")
        _validate_string(args.concern, "add-concern-dep --concern")
        _validate_string(args.name, "add-concern-dep --name")
        _validate_string(args.kind, "add-concern-dep --kind")
        _validate_in_enum(
            args.kind, DEPENDENCY_KINDS, "add-concern-dep --kind",
        )
        version = _validate_optional_string(
            args.version, "add-concern-dep --version"
        )
        _validate_string(
            args.purpose, "add-concern-dep --purpose", multiline=True,
        )
        consumer_locations: List[str] = []
        for idx, loc in enumerate(args.consumer_location or []):
            _validate_string(
                loc,
                "add-concern-dep --consumer-location[{0}]".format(idx),
            )
            consumer_locations.append(loc)
    except ValueError as err:
        return _die(str(err))
    try:
        with _state_transaction() as state:
            concern = _require_concern(state, args.package, args.concern)
            if concern is None:
                if _require_package(state, args.package) is None:
                    raise _AbortTransaction(_die(
                        "package not registered at {0!r}; run add-package "
                        "first".format(args.package)
                    ))
                raise _AbortTransaction(_die(
                    "concern {0!r} not registered under {1}; run "
                    "add-concern first".format(args.concern, args.package)
                ))
            for existing in concern["dependencies"]:
                if existing["name"] == args.name:
                    raise _AbortTransaction(_die(
                        "dependency {0!r} already registered under {1}/{2}; "
                        "use a different name or reset".format(
                            args.name, args.package, args.concern,
                        )
                    ))
            concern["dependencies"].append(
                {
                    "name": args.name,
                    "kind": args.kind,
                    "version": version,
                    "purpose": args.purpose,
                    "consumer_locations": consumer_locations,
                }
            )
    except _AbortTransaction as ab:
        return ab.code
    except StateLoadError as err:
        return _die(str(err), code=1)
    except OSError as err:
        return _die("cannot write state: {0}".format(err), code=1)
    _info(
        "add-concern-dep {0} under {1}/{2} (kind={3})".format(
            args.name, args.package, args.concern, args.kind,
        )
    )
    return 0


# ---------------------------------------------------------------------------
# Subcommand: add-concern-hazard.
# ---------------------------------------------------------------------------


def cmd_add_concern_hazard(args: argparse.Namespace) -> int:
    try:
        _validate_string(args.package, "add-concern-hazard --package")
        _validate_string(args.concern, "add-concern-hazard --concern")
        _validate_string(args.category, "add-concern-hazard --category")
        _validate_in_enum(
            args.category, HAZARD_CATEGORIES,
            "add-concern-hazard --category",
        )
        _validate_string(
            args.description, "add-concern-hazard --description",
            multiline=True,
        )
    except ValueError as err:
        return _die(str(err))
    cite_present = (
        args.cite_file is not None
        or args.cite_start is not None
        or args.cite_end is not None
    )
    cite_complete = (
        args.cite_file is not None
        and args.cite_start is not None
        and args.cite_end is not None
    )
    if cite_present and not cite_complete:
        return _die(
            "hazard cite requires --cite-file + --cite-start + --cite-end "
            "together, or none"
        )
    cite: Optional[Dict[str, Any]] = None
    if cite_complete:
        try:
            _validate_string(
                args.cite_file, "add-concern-hazard --cite-file"
            )
            _validate_line_range(
                args.cite_start, args.cite_end, "add-concern-hazard cite"
            )
        except ValueError as err:
            return _die(str(err))
        cite = {
            "file": args.cite_file,
            "start": args.cite_start,
            "end": args.cite_end,
        }
    try:
        with _state_transaction() as state:
            concern = _require_concern(state, args.package, args.concern)
            if concern is None:
                if _require_package(state, args.package) is None:
                    raise _AbortTransaction(_die(
                        "package not registered at {0!r}; run add-package "
                        "first".format(args.package)
                    ))
                raise _AbortTransaction(_die(
                    "concern {0!r} not registered under {1}; run "
                    "add-concern first".format(args.concern, args.package)
                ))
            # Dedup natural key: (category, description, cite-file,
            # cite-start). Same-prose hazards with different cites are
            # treated as distinct observations (matches the package-tier
            # philosophy that a hazard's identity includes WHERE it was
            # observed, not just what it says).
            cite_file = cite["file"] if cite else None
            cite_start = cite["start"] if cite else None
            for existing in concern["hazards"]:
                ex_cite = existing.get("cite") or {}
                ex_file = ex_cite.get("file") if existing.get("cite") else None
                ex_start = ex_cite.get("start") if existing.get("cite") else None
                if (
                    existing["category"] == args.category
                    and existing["description"] == args.description
                    and ex_file == cite_file
                    and ex_start == cite_start
                ):
                    raise _AbortTransaction(_die(
                        "hazard ({0!r}, same description, same cite) already "
                        "registered under {1}/{2}".format(
                            args.category, args.package, args.concern,
                        )
                    ))
            concern["hazards"].append(
                {
                    "category": args.category,
                    "description": args.description,
                    "cite": cite,
                }
            )
    except _AbortTransaction as ab:
        return ab.code
    except StateLoadError as err:
        return _die(str(err), code=1)
    except OSError as err:
        return _die("cannot write state: {0}".format(err), code=1)
    _info(
        "add-concern-hazard {0} under {1}/{2}".format(
            args.category, args.package, args.concern,
        )
    )
    return 0


# ---------------------------------------------------------------------------
# Subcommand: set-concern-usage-example.
# ---------------------------------------------------------------------------


def cmd_set_concern_usage_example(args: argparse.Namespace) -> int:
    try:
        _validate_string(args.package, "set-concern-usage-example --package")
        _validate_string(args.concern, "set-concern-usage-example --concern")
        _validate_string(
            args.language, "set-concern-usage-example --language",
        )
        _validate_string(
            args.code_snippet,
            "set-concern-usage-example --code-snippet",
            multiline=True,
        )
        _validate_string(
            args.cite_file, "set-concern-usage-example --cite-file",
        )
        _validate_line_range(
            args.cite_start, args.cite_end,
            "set-concern-usage-example cite",
        )
    except ValueError as err:
        return _die(str(err))
    try:
        with _state_transaction() as state:
            concern = _require_concern(state, args.package, args.concern)
            if concern is None:
                if _require_package(state, args.package) is None:
                    raise _AbortTransaction(_die(
                        "package not registered at {0!r}; run add-package "
                        "first".format(args.package)
                    ))
                raise _AbortTransaction(_die(
                    "concern {0!r} not registered under {1}; run "
                    "add-concern first".format(args.concern, args.package)
                ))
            concern["usage_example"] = {
                "language": args.language,
                "snippet": args.code_snippet,
                "cite": {
                    "file": args.cite_file,
                    "start": args.cite_start,
                    "end": args.cite_end,
                },
            }
    except _AbortTransaction as ab:
        return ab.code
    except StateLoadError as err:
        return _die(str(err), code=1)
    except OSError as err:
        return _die("cannot write state: {0}".format(err), code=1)
    _info(
        "set-concern-usage-example under {0}/{1} (cite={2}:{3}-{4})".format(
            args.package, args.concern,
            args.cite_file, args.cite_start, args.cite_end,
        )
    )
    return 0
