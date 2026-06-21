"""Consumer-source scanner for the any-leak detector (Phase 4).

Walks consumer TypeScript / Vue source files.  For each file that imports from
any declared generated_types_dir, scans source lines for explicit ``any``
annotations / casts / generics and emits a Finding per occurrence.

Public API
----------
scan_for_any_leak_violations(root, generated_types_dirs, allowlist_globs)
    Returns a list of ``Finding`` objects for every explicit ``any`` usage found
    in files that import from a declared generated-types directory.

Walk semantics
--------------
- Extensions scanned: ``*.ts``, ``*.tsx``, ``*.vue``.
- Files matching ``allowlist_globs`` are excluded via ``path_in_allowlist``
  from Phase 0 substrate.  Paths are relative to ``root``.
- Files under any ``generated_types_dirs`` subtree are excluded (the generated
  dirs themselves may legitimately use ``any`` internally).
- ``os.walk`` does NOT prune ``node_modules`` by default.  The consumer
  config's ``allowlist_paths`` should include ``node_modules/**`` and
  ``**/node_modules/**`` (paired-pattern convention) to skip that tree.

Import-classification heuristic (file-level filter)
----------------------------------------------------
A file "imports from generated types" when its source contains any
``import ... from '<path>'`` (or ``import '<path>'``) where ``<path>`` shares
a substring with any generated_types_dir.  Five pattern variants are built for
each declared generated_types_dir (e.g. ``packages/cse-types/src``):

  1. Full dir path:          ``packages/cse-types/src``
  2. Dir path with slash:    ``packages/cse-types/src/``
  3. Dir + ``/index`` suffix:  ``packages/cse-types/src/index``
  4. Package-name segment:   ``packages/cse-types``
  5. Last-segment only:      ``cse-types``  (covers ``@cse/types``-style aliases)

All five are checked via substring containment against each import specifier.
This is a heuristic: the last-segment-only variant may produce false positives
on package names that happen to be substrings of unrelated package specifiers
(e.g., ``cse-types`` matching ``@something-cse-types-other``).  Precision is
bounded by the same class of tradeoffs as Phase 3 relative-path resolution.
Phase 5 / future-work upgrade path: full TS module resolution via
``tsconfig.json`` ``paths`` + ``baseUrl`` parsing would replace the heuristic.

``any``-pattern detection (line-level, in qualifying files only)
----------------------------------------------------------------
Three patterns are matched per line (applied after stripping string-literal and
line-comment context):

  1. ``: any\\b``  — type annotation (``function foo(x: any)``, ``const y: any``,
                     ``let z: any[]``).
  2. ``\\bas any\\b`` — type cast (``obj as any``).
  3. generic-position ``any``  — ``any`` at any position inside angle brackets:
                       ``Array<any>``, ``<any>obj``, ``Set<any>``, ``Map<any, any>``
                       (2 findings, both slots), ``Record<string, any>``,
                       ``Map<string, any>``.  Lookbehind pattern; see the
                       inline comment block at ``_GENERIC_RE``.

Word-boundary rules:
  - ``Any`` (capitalized) is NOT matched — different identifier.
  - ``anyOther`` (word-boundary required) is NOT matched.
  - ``as anyhow`` is NOT matched — ``\\b`` after ``any`` prevents partial word match.

Out of scope (Phase 4)
-----------------------
- ``@ts-ignore`` / ``@ts-expect-error`` directives — different rule.
- Inferred ``any`` (no annotation present; TS infers ``any``) — static analysis
  of explicit-only annotations suffices for Phase 4.
- ``unknown`` type suggestions — future-work.
- Block comments (``/* ... */``) — inherited Phase 1/3 scope limitation.
- Multi-line string-literal context tracking — known false-positive source in
  rare multi-line template literals.

Multi-match per line
--------------------
If a single line contains multiple ``any`` occurrences (e.g.,
``function f(x: any, y: any)``), one Finding is emitted per occurrence, all at
the same 1-based line number.

Finding field values
--------------------
- ``rule``: ``"any_with_generated_available"``
- ``path``: project-relative (relative to ``root``), NOT absolute.
- ``line``: 1-based line number of the offending token.
- ``kind``: ``"VIOLATION"``
- ``summary``: fixed message directing the developer to use a generated type.
- ``fix_hint``: references the first generated_types_dir as a starting point.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Optional, Set

from .._shared import Finding, has_inline_escape, path_in_allowlist

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ELIGIBLE_EXTENSIONS: Set[str] = {".ts", ".tsx", ".vue"}

# ---------------------------------------------------------------------------
# any-pattern regexes (applied per-line after string/comment context walk)
# ---------------------------------------------------------------------------

# ": any" as a type annotation — colon followed by optional whitespace then
# the word "any" with a word boundary after so "anyOther" is not matched.
_ANNOT_RE = re.compile(r":\s*any\b")

# "as any" — type cast, word boundaries on both sides.
_CAST_RE = re.compile(r"\bas\s+any\b")

# `any` as a generic type parameter at any position inside angle brackets.
# Catches:
#   Array<any>              -- single-arg generic
#   Set<any>, Promise<any>  -- same shape
#   Map<any, any>           -- both positions caught (2 findings)
#   Record<string, any>     -- last-position any caught
#   Map<string, any>        -- same
#   <any>obj                -- angle-bracket cast
# Does NOT match `Any` (capitalized) or `anyOther` (the trailing lookahead
# requires `,` or `>` after `any`, so `anyOther` fails).
#
# Two zero-width lookbehinds joined by alternation cover the two boundary
# cases that delimit `any` inside angle brackets:
#   `(?<=<)\s*any` — `any` immediately after `<` (first/only generic arg)
#   `(?<=,)\s*any` — `any` immediately after `,` (subsequent generic arg)
# Common trailing lookahead `(?=\s*[,>])` requires `any` followed by `,`
# or `>` (the only valid generic-position terminators).
#
# Why lookbehinds (zero-width) rather than `[<,]\s*any\s*[,>]`: a consuming
# pattern with `finditer` cannot match overlapping inputs, so the comma in
# `Map<any, any>` would be eaten by the first match and the second `any`
# would be missed.  Zero-width lookbehinds avoid the overlap.
_GENERIC_RE = re.compile(r"(?:(?<=<)|(?<=,))\s*any(?=\s*[,>])")

# Combined list for iteration (order: annotation, cast, generic).
_ANY_PATTERNS: List[re.Pattern] = [_ANNOT_RE, _CAST_RE, _GENERIC_RE]

# Import specifier extraction: match any static import form and capture the
# module specifier (Group 1).  Applied line-by-line.
# Matches:
#   import { ... } from 'path'
#   import X from 'path'
#   import * as X from 'path'
#   import 'path'  (side-effect)
_IMPORT_RE = re.compile(
    r"""^[ \t]*import\b(?:[^'"]*?)['"]([^'"]+)['"]"""
)


# ---------------------------------------------------------------------------
# Generated-dir match patterns
# ---------------------------------------------------------------------------

def _build_import_match_patterns(generated_types_dirs: List[Path], root: Path) -> List[str]:
    """Build the set of import-path substrings to look for in import specifiers.

    For each generated_types_dir, produce five variant strings:
      1. Full relative dir path (e.g., ``packages/cse-types/src``)
      2. Dir path with trailing slash (``packages/cse-types/src/``)
      3. Dir path + ``/index`` (``packages/cse-types/src/index``)
      4. Package-name segment — path up to the last component (``packages/cse-types``)
      5. Last-segment only (``cse-types``)

    The dir path used is relative to root (forward-slash-joined) so it matches
    typical TS import specifiers.

    Both ``root`` and ``gen_dir`` are resolved before computing relative paths
    so that symlinks and non-canonical paths don't cause false mismatches.
    """
    patterns: List[str] = []
    for gen_dir in generated_types_dirs:
        # Resolve both paths so relative_to works reliably.
        try:
            resolved_gen = gen_dir.resolve()
            resolved_root = root.resolve()
            rel = resolved_gen.relative_to(resolved_root)
            rel_str = str(rel).replace(os.sep, "/")
        except (ValueError, OSError):
            # gen_dir is not under root (unlikely in practice); use the
            # unresolved string representation with forward slashes.
            rel_str = str(gen_dir).replace(os.sep, "/")

        # 1. Full dir path.
        patterns.append(rel_str)
        # 2. Dir path + trailing slash.
        patterns.append(rel_str + "/")
        # 3. Dir path + /index.
        patterns.append(rel_str + "/index")
        # 4. Package-name segment (all but last path component, e.g.
        #    ``packages/cse-types/src`` -> ``packages/cse-types``).
        parts = rel_str.split("/")
        if len(parts) >= 2:
            pkg_segment = "/".join(parts[:-1])
            patterns.append(pkg_segment)
            # 5. Last-segment-only from the package-name segment (e.g.
            #    ``packages/cse-types`` -> ``cse-types``).  This covers
            #    TS path aliases like ``@cse/types`` or ``@org/cse-types``
            #    where the alias tail matches the package name.
            pkg_parts = pkg_segment.split("/")
            patterns.append(pkg_parts[-1])
        else:
            # rel_str is a single-component path (unusual); use it as-is for
            # the last-segment-only variant.
            patterns.append(rel_str)

    return patterns


# ---------------------------------------------------------------------------
# Import-qualification check (file-level filter)
# ---------------------------------------------------------------------------

def _file_qualifies(source: str, import_match_patterns: List[str]) -> bool:
    """Return True if the file imports from any of the generated_types_dirs.

    Inspects each line with an import statement and checks whether its module
    specifier contains any of the generated-dir match patterns as a substring.
    Line-comment detection: lines where the import keyword appears after ``//``
    are skipped.  Block comments are NOT handled (Phase 4 scope).
    """
    for line in source.splitlines():
        m = _IMPORT_RE.match(line)
        if not m:
            continue
        # Skip line-commented imports (import keyword after //).
        comment_pos = _find_comment_start(line)
        if comment_pos is not None:
            import_pos = line.index("import") if "import" in line else -1
            if import_pos >= comment_pos:
                continue
        specifier = m.group(1)
        for pat in import_match_patterns:
            if pat and pat in specifier:
                return True
    return False


# ---------------------------------------------------------------------------
# String-literal and line-comment context walker
# ---------------------------------------------------------------------------

def _find_comment_start(line: str) -> Optional[int]:
    """Return the column of the first ``//`` not inside a string, or None.

    Tracks single-quote, double-quote, and backtick string contexts so
    ``//`` inside a URL (e.g., ``'http://x'``) does NOT trigger the detection.
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


def _positions_outside_strings_and_comments(
    line: str, pattern: re.Pattern
) -> List[int]:
    """Return the start positions of all ``pattern`` matches that are outside
    string literals and line comments.

    For each match found by ``pattern``, we verify that the match start
    position is:
      - Not inside a string (single-quote, double-quote, backtick).
      - Not inside a ``//`` line comment.

    The string-context walk is stateful (tracks open/close delimiters) so a
    ``//`` inside a string does NOT close the string context.
    """
    # Walk the line to map each character position to "inside string" or
    # "inside comment" status.
    in_string: Optional[str] = None
    comment_start: Optional[int] = None
    string_ranges: List[tuple] = []    # (start, end) inclusive of open/close quotes
    current_string_start: Optional[int] = None
    i = 0
    while i < len(line):
        ch = line[i]
        if comment_start is not None:
            # Rest of line is comment; stop.
            break
        if in_string:
            if ch == "\\" and i + 1 < len(line):
                i += 2
                continue
            if ch == in_string:
                # Close the string.
                if current_string_start is not None:
                    string_ranges.append((current_string_start, i))
                in_string = None
                current_string_start = None
        else:
            if ch in ('"', "'", "`"):
                in_string = ch
                current_string_start = i
            elif ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                comment_start = i
                break
        i += 1

    def _is_in_string(pos: int) -> bool:
        for start, end in string_ranges:
            if start <= pos <= end:
                return True
        return False

    def _is_in_comment(pos: int) -> bool:
        return comment_start is not None and pos >= comment_start

    result: List[int] = []
    for m in pattern.finditer(line):
        pos = m.start()
        if not _is_in_string(pos) and not _is_in_comment(pos):
            result.append(pos)
    return result


# ---------------------------------------------------------------------------
# Path utilities
# ---------------------------------------------------------------------------

def _is_under_generated(file_path: Path, generated_dirs: List[Path]) -> bool:
    """Return True if file_path is under any of the generated_dirs."""
    try:
        abs_file = file_path.resolve()
    except OSError:
        abs_file = file_path.absolute()

    for gen_dir in generated_dirs:
        try:
            abs_gen = gen_dir.resolve()
        except OSError:
            abs_gen = gen_dir.absolute()
        try:
            abs_file.relative_to(abs_gen)
            return True
        except ValueError:
            pass
    return False


# ---------------------------------------------------------------------------
# Main scanner
# ---------------------------------------------------------------------------

def scan_for_any_leak_violations(
    root: Path,
    generated_types_dirs: List[Path],
    allowlist_globs: List[str],
) -> List[Finding]:
    """Walk ``root`` for .ts/.tsx/.vue; for each file that imports from any
    declared generated_types_dir, scan for ``any``-leak patterns and emit
    Finding per occurrence.

    Parameters
    ----------
    root:
        Consumer project root.  ``Finding.path`` values are relative to this.
    generated_types_dirs:
        Absolute paths to the declared generated-types directories.  Files
        under these paths are excluded from scanning.  The first entry is also
        used as the ``fix_hint`` reference if violations are found.
    allowlist_globs:
        List of glob patterns (matched against project-relative paths via
        ``path_in_allowlist`` from Phase 0 substrate).  Files matching any
        pattern are excluded.

    Returns
    -------
    List of ``Finding`` objects.  ``Finding.path`` is relative to ``root``.
    ``Finding.rule`` is ``"any_with_generated_available"``.
    """
    findings: List[Finding] = []
    root = root.resolve()

    # Pre-compute match patterns for the import-qualification check.
    import_match_patterns = _build_import_match_patterns(generated_types_dirs, root)

    # Build fix_hint reference from the first declared dir.
    if generated_types_dirs:
        try:
            first_rel = generated_types_dirs[0].relative_to(root)
            gen_dir_hint = str(first_rel).replace(os.sep, "/")
        except ValueError:
            gen_dir_hint = str(generated_types_dirs[0])
    else:
        gen_dir_hint = "<generated-types-dir>"

    fix_hint = (
        "check {gen_dir} for a typed alternative; if no typed alternative "
        "exists, narrow with a specific union or interface.".format(
            gen_dir=gen_dir_hint,
        )
    )
    summary = (
        "`any` used in file importing from generated-types dir; "
        "replace with the appropriate generated type or narrow explicitly"
    )

    for dirpath, _dirs, files in os.walk(str(root)):
        for fname in files:
            fpath = Path(dirpath) / fname
            if fpath.suffix not in _ELIGIBLE_EXTENSIONS:
                continue

            # Exclude files under generated dirs.
            if _is_under_generated(fpath, generated_types_dirs):
                continue

            try:
                rel_path = fpath.relative_to(root)
            except ValueError:
                continue

            rel_str = str(rel_path)

            # Allowlist check (file-level).
            if path_in_allowlist(Path(rel_str), allowlist_globs):
                continue

            # Read the file.
            try:
                source = fpath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            # File-level qualification check: does this file import from
            # any declared generated-types dir?
            if not _file_qualifies(source, import_match_patterns):
                continue

            # Line-level any-pattern scan.
            for line_num, line in enumerate(source.splitlines(), start=1):
                for pattern in _ANY_PATTERNS:
                    positions = _positions_outside_strings_and_comments(line, pattern)
                    if not positions:
                        continue
                    # Check inline escape once per line (covers all matches on
                    # the same line — one escape marker exempts the whole line).
                    if has_inline_escape(fpath, line_num):
                        break  # skip all patterns on this line
                    for _pos in positions:
                        findings.append(
                            Finding(
                                rule="any_with_generated_available",
                                path=rel_str,
                                line=line_num,
                                kind="VIOLATION",
                                summary=summary,
                                fix_hint=fix_hint,
                            )
                        )

    return findings
