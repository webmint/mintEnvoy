"""Consumer-source scanner for the cross-layer import detector (Phase 3).

Walks consumer TypeScript / Vue source files, classifies each file's layer,
resolves relative import targets, classifies the import target's layer, and
emits a Finding for every disallowed layer edge (source_layer -> target_layer
not in allowed_imports_map[source_layer]).

Public API
----------
scan_for_cross_layer_violations(root, allowed_imports_map, layer_dirs_map, allowlist_globs)
    Returns a list of ``Finding`` objects for every import that crosses a
    disallowed layer boundary.

Walk semantics
--------------
- Extensions scanned: ``*.ts``, ``*.tsx``, ``*.vue``.
- Files matching ``allowlist_globs`` are excluded via ``path_in_allowlist``
  from Phase 0 substrate.  Paths are relative to ``root``.
- ``os.walk`` does NOT prune ``node_modules`` by default.  The consumer
  config's ``allowlist_paths`` must include ``node_modules/**`` and
  ``**/node_modules/**`` (paired-pattern convention) to skip that tree.

Import detection scope (Phase 3)
---------------------------------
Only **relative imports** are resolved.  An import path is relative when it
starts with ``./`` or ``../``.

Out-of-scope import forms (Phase 3)
------------------------------------
- External package imports (``from 'lodash'``, ``from 'react'``).
- TypeScript path-alias imports (``from '@app/foo'``, ``from '@/utils'``).
  These cannot be resolved without parsing ``tsconfig.json``.
- Re-export statements (``export { X } from '...'``).  Only ``import``
  statements are scanned.
- Block comments (``/* ... */``).  Phase 3 inherits Phase 1's scope
  limitation: line comments (``//``) do suppress import lines, but block
  comments are not stripped before the regex search.

Import-target resolution
------------------------
Given a relative import path P (e.g., ``'../infra/bar'``), the scanner
resolves it relative to the importing file's directory and probes for the
following in order:

1. Exact path as given (P).
2. P + ``.ts``
3. P + ``.tsx``
4. P + ``.vue``
5. P + ``/index.ts``
6. P + ``/index.tsx``

The first filesystem-existing match wins.  If none exist, the import is
unresolvable and is skipped (not flagged).

Same-layer imports
------------------
``allowed_imports_map`` always includes the source layer itself (built by
``load_layer_graph``).  So ``domain -> domain`` imports are always allowed
via a single hard rule — no special-casing in the scanner.

Finding field values
--------------------
- ``rule``: ``"cross_layer_imports"``
- ``path``: project-relative (relative to ``root``), NOT absolute.
- ``line``: 1-based line of the import statement.
- ``kind``: ``"VIOLATION"``
- ``summary``: ``"layer '<src>' imports from layer '<tgt>' — not in allowed-imports list for '<src>'"``
- ``fix_hint``: guidance on how to fix or annotate the import.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set

from .._shared import Finding, has_inline_escape, path_in_allowlist
from ._graph import classify_path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ELIGIBLE_EXTENSIONS: Set[str] = {".ts", ".tsx", ".vue"}

# Suffix probe order for module resolution (Phase 3 scope).
_RESOLUTION_SUFFIXES: List[str] = [
    "",           # exact match first
    ".ts",
    ".tsx",
    ".vue",
    "/index.ts",
    "/index.tsx",
]

# ---------------------------------------------------------------------------
# Import-statement regex
# ---------------------------------------------------------------------------

# Matches all forms of static import that yield a module specifier:
#   import { ... } from '<path>'
#   import X from '<path>'
#   import * as X from '<path>'
#   import '<path>'   (side-effect import)
#
# Group 1 = the module specifier string (without quotes).
# Both single- and double-quoted specifiers are handled.
# This regex is line-oriented (applied line-by-line); multi-line imports
# (e.g., Prettier-wrapped `import {\n  A,\n  B,\n} from '../path'`) are
# NOT handled in Phase 3.  This is a KNOWN FALSE-NEGATIVE: any file
# importing 3+ named symbols from a cross-layer module is invisible to
# the detector when Prettier (or similar formatter) wraps the import
# across lines.  This pattern is common, not rare — the dominant style
# in formatter-using codebases.  Phase 4 (or a Phase 3.5 patch) should
# join continuation lines before regex matching: collect `import {`
# opener lines, accumulate until a `} from '...'` close-line, then
# apply detection on the joined text.  Tracked in plan §"Phase 3" /
# Phase 4 future-work.
_IMPORT_RE = re.compile(
    r"""^[ \t]*import\b(?:[^'"]*?)['"]([^'"]+)['"]"""
)


def _extract_relative_imports(source: str) -> List[tuple]:
    """Return list of (line_number_1based, module_specifier) for relative imports.

    Only lines whose module specifier starts with ``./`` or ``../`` are
    returned.  Line-comment detection: lines where the ``import`` keyword
    appears after a ``//`` token are skipped.  Block comments are NOT
    stripped (Phase 3 scope limitation; consistent with Phase 1).
    """
    results: List[tuple] = []
    for line_num, line in enumerate(source.splitlines(), start=1):
        # Skip lines where import comes after //
        comment_pos = _find_line_comment_start(line)
        import_match = _IMPORT_RE.match(line)
        if not import_match:
            continue
        # Check if the import keyword position is after a line comment.
        import_keyword_pos = line.index("import")
        if comment_pos is not None and import_keyword_pos >= comment_pos:
            continue
        specifier = import_match.group(1)
        if specifier.startswith("./") or specifier.startswith("../"):
            results.append((line_num, specifier))
    return results


def _find_line_comment_start(line: str) -> Optional[int]:
    """Return the column of the first ``//`` not inside a string, or ``None``.

    Tracks single-quote, double-quote, and backtick string context so
    ``//`` inside a URL like ``'http://x'`` does not trigger a false positive.
    """
    in_string: Optional[str] = None
    i = 0
    while i < len(line):
        ch = line[i]
        if in_string:
            if ch == "\\" and i + 1 < len(line):
                i += 2
                continue
            if ch == in_string:
                in_string = None
        else:
            if ch in ('"', "'", "`"):
                in_string = ch
            elif ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                return i
        i += 1
    return None


# ---------------------------------------------------------------------------
# Import-target resolution
# ---------------------------------------------------------------------------

def _resolve_import_target(importing_file: Path, specifier: str) -> Optional[Path]:
    """Return the resolved absolute Path for a relative import specifier.

    Parameters
    ----------
    importing_file:
        Absolute path of the file containing the import.
    specifier:
        Relative module specifier (starts with ``./`` or ``../``).

    Returns
    -------
    Absolute Path of the resolved file, or ``None`` if unresolvable.
    """
    base_dir = importing_file.parent
    candidate_base = (base_dir / specifier).resolve()

    for suffix in _RESOLUTION_SUFFIXES:
        candidate = Path(str(candidate_base) + suffix)
        if candidate.is_file():
            return candidate
    return None


# ---------------------------------------------------------------------------
# Main scanner
# ---------------------------------------------------------------------------

def scan_for_cross_layer_violations(
    root: Path,
    allowed_imports_map: Dict[str, Set[str]],
    layer_dirs_map: Dict[str, List[str]],
    allowlist_globs: List[str],
) -> List[Finding]:
    """Walk ``root`` and return cross-layer import violations.

    Parameters
    ----------
    root:
        Consumer project root.  ``Finding.path`` values are relative to this.
    allowed_imports_map:
        ``{layer_name: set of layer names that layer_name may import from}``.
        Built by ``load_layer_graph``; already includes each layer itself so
        same-layer imports are implicitly allowed.
    layer_dirs_map:
        ``{layer_name: [glob_string, ...]}``.  Used by ``classify_path`` to
        determine which layer a file belongs to.
    allowlist_globs:
        List of glob patterns (matched against project-relative paths via
        ``path_in_allowlist`` from Phase 0 substrate).  Files matching any
        pattern are excluded from scanning.

    Returns
    -------
    List of ``Finding`` objects.  ``Finding.path`` is relative to ``root``.
    ``Finding.rule`` is ``"cross_layer_imports"``.
    """
    findings: List[Finding] = []
    root = root.resolve()

    for dirpath, _dirs, files in os.walk(str(root)):
        for fname in files:
            fpath = Path(dirpath) / fname
            if fpath.suffix not in _ELIGIBLE_EXTENSIONS:
                continue

            try:
                rel_path = fpath.relative_to(root)
            except ValueError:
                continue

            rel_str = str(rel_path)

            # Allowlist check (file-level).
            if path_in_allowlist(Path(rel_str), allowlist_globs):
                continue

            # Classify source file's layer.
            source_layer = classify_path(rel_path, layer_dirs_map)
            if source_layer is None:
                # File is outside any declared layer; skip entirely.
                continue

            # Read the file.
            try:
                source = fpath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            # Extract relative imports.
            relative_imports = _extract_relative_imports(source)

            for import_line, specifier in relative_imports:
                # Resolve the import target.
                resolved = _resolve_import_target(fpath, specifier)
                if resolved is None:
                    # Unresolvable (target file does not exist); skip.
                    continue

                # Get project-relative path for the target.
                try:
                    target_rel = resolved.relative_to(root)
                except ValueError:
                    # Target is outside root (e.g., a symlink pointing elsewhere); skip.
                    continue

                # Classify the target's layer.
                target_layer = classify_path(target_rel, layer_dirs_map)
                if target_layer is None:
                    # Target is out-of-layer source (config, generated file, etc.); skip.
                    continue

                # Check the edge.
                allowed = allowed_imports_map.get(source_layer, {source_layer})
                if target_layer in allowed:
                    continue

                # Check inline escape on the import line.
                if has_inline_escape(fpath, import_line):
                    continue

                findings.append(
                    Finding(
                        rule="cross_layer_imports",
                        path=rel_str,
                        line=import_line,
                        kind="VIOLATION",
                        summary=(
                            "layer '{src}' imports from layer '{tgt}' "
                            "— not in allowed-imports list for '{src}'".format(
                                src=source_layer,
                                tgt=target_layer,
                            )
                        ),
                        fix_hint=(
                            "either move the imported symbol to a layer that "
                            "'{src}' is allowed to depend on, or add '{tgt}' to "
                            "the layer_graph['{src}'] config if the dependency is "
                            "intentional".format(
                                src=source_layer,
                                tgt=target_layer,
                            )
                        ),
                    )
                )

    return findings
