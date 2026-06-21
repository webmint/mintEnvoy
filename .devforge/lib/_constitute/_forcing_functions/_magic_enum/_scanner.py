"""Consumer-source scanner for the magic-enum duplication detector (Phase 1).

Walks consumer TypeScript / Vue source files, extracts string literals, and
cross-references them against the generated-enum inventory.  Files that are
under a ``generated_dirs`` root, or that match an ``allowlist_globs`` pattern,
or that already import the matching enum name and use it via member notation,
are excluded from findings.

Public API
----------
scan_for_magic_enum_violations(root, inventory, allowlist_globs, generated_dirs)
    Returns a list of ``Finding`` objects for every string literal that
    duplicates a generated enum member value without importing the enum.

Walk semantics
--------------
- Extensions scanned: ``*.ts``, ``*.tsx``, ``*.vue``.
- ``generated_dirs`` subtrees are excluded (consumer's own generated output).
- Files matching ``allowlist_globs`` are excluded (via ``path_in_allowlist``
  from Phase 0 substrate; paths are relative to ``root``).
- ``Finding.path`` is relative to ``root`` so downstream consumers see
  project-relative paths like ``src/foo.ts``.

Import-exemption rule (conservative, Phase 1)
---------------------------------------------
If a file contains a named import of an enum name **and** uses that name with
a member-access notation (``EnumName.``), all violations for that enum's
member values in the same file are suppressed.  This yields fewer false
positives at the cost of potentially missing real violations in files that
happen to import the enum for other reasons.  Raise precision in Phase 2 if
empirical verify shows under-detection.

Comment-skip rule (Phase 1)
---------------------------
Lines where the offending string literal is inside a ``//`` line comment
(either the whole line is a comment, or the literal appears after ``//``)
are skipped.  Block comments (``/* ... */``) are out of scope for Phase 1.

Out of scope (Phase 1)
-----------------------
- Multi-line template strings (backtick literals).
- Block comments (``/* ... */``).
- Aliased imports (``import { X as Y }``).
- Vue template-vs-script distinction (whole file is scanned for Phase 1).
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set

from .._shared import Finding, has_inline_escape, path_in_allowlist

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ELIGIBLE_EXTENSIONS = {".ts", ".tsx", ".vue"}

# ---------------------------------------------------------------------------
# String-literal tokenizer (single-line strings only)
# ---------------------------------------------------------------------------

# Matches 'value' or "value" — single-line, handles \' and \" escapes.
# Per-quote alternation so an opening ' is not closed by an embedded "
# (and vice versa).  Group 1 = single-quoted content; Group 2 = double-quoted
# content; exactly one of them is non-None per match.  Callers select whichever
# matched.  Phase 1 does NOT extract backtick template literals as inventory
# values (Phase 1 scope).
_STR_LIT_RE = re.compile(r"""'((?:[^'\\]|\\.)*?)'|"((?:[^"\\]|\\.)*?)\"""")

# ---------------------------------------------------------------------------
# Import detection
# ---------------------------------------------------------------------------

# Matches: import { A, B, C } from '...' or import { A, B, C } from "..."
# Group 1 = contents inside braces (may have whitespace/newlines for Phase 1
# simple named imports only).
_NAMED_IMPORT_RE = re.compile(
    r"""import\s*\{([^}]+)\}\s*from\s*(['"])[^'"]*\2"""
)

# Matches: import * as ns from '...'
# Group 1 = namespace alias.
_STAR_IMPORT_RE = re.compile(
    r"""import\s*\*\s*as\s+(\w+)\s+from\s*(['"])[^'"]*\2"""
)


def _extract_imported_names(source: str) -> Set[str]:
    """Return the set of named identifiers imported in this file."""
    names: Set[str] = set()
    for m in _NAMED_IMPORT_RE.finditer(source):
        for part in m.group(1).split(","):
            # Only take the first word (before "as" aliases — out of scope).
            token = part.strip().split()[0] if part.strip() else ""
            if token:
                names.add(token)
    return names


def _enum_used_via_member_access(source: str, enum_name: str) -> bool:
    """Return True if ``EnumName.`` appears in non-comment source.

    Line comments (``//`` to end-of-line) are stripped per line before the
    pattern search so a comment like ``// avoid Color.X`` does
    NOT spuriously trigger the exemption rule.  Block comments
    (``/* ... */``) are NOT stripped — Phase 1 spec marks those out of
    scope; they remain a known false-positive source for the exemption
    rule and will be addressed in Phase 2 if empirical use surfaces them.
    """
    pattern = re.compile(re.escape(enum_name) + r"\.")
    for raw_line in source.splitlines():
        # Inlined implementation, structurally identical to
        # _is_in_line_comment's walker: find the first `//` not inside a
        # string ('/'/"/`).  If Phase 2 extends _is_in_line_comment to
        # handle `/* */` block comments, this walker MUST receive the
        # same update — they must stay in sync.
        in_string: Optional[str] = None
        i = 0
        comment_start: Optional[int] = None
        while i < len(raw_line):
            ch = raw_line[i]
            if in_string:
                if ch == "\\" and i + 1 < len(raw_line):
                    i += 2
                    continue
                if ch == in_string:
                    in_string = None
            else:
                if ch in ('"', "'", "`"):
                    in_string = ch
                elif ch == "/" and i + 1 < len(raw_line) and raw_line[i + 1] == "/":
                    comment_start = i
                    break
            i += 1
        code = raw_line if comment_start is None else raw_line[:comment_start]
        if pattern.search(code):
            return True
    return False


# ---------------------------------------------------------------------------
# Comment detection
# ---------------------------------------------------------------------------

def _is_in_line_comment(line: str, col: int) -> bool:
    """Return True if position ``col`` is inside a ``//`` line comment.

    Scans for the first ``//`` not inside a string literal.  Tracks single
    quotes ('), double quotes ("), AND backticks (`) as string-context
    openers so a URL like ``http://x`` inside a backtick template literal
    does NOT spuriously trigger comment detection on the embedded ``//``.
    Phase 1 does NOT handle block comments.
    """
    # Walk the line up to col, tracking whether we're in a string.
    in_string: Optional[str] = None
    i = 0
    while i < len(line):
        ch = line[i]
        if in_string:
            if ch == "\\" and i + 1 < len(line):
                i += 2  # skip escaped char
                continue
            if ch == in_string:
                in_string = None
        else:
            if ch in ('"', "'", "`"):
                in_string = ch
            elif ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                # Found a // comment start.  If col >= i, the position is
                # within the comment.
                return col >= i
        i += 1
    return False


# ---------------------------------------------------------------------------
# Per-file literal extraction
# ---------------------------------------------------------------------------

def _extract_literals(source: str) -> Dict[str, List[int]]:
    """Build {literal_value: [1-based line numbers]} from all string tokens.

    Skips literals on lines that are entirely comments (start with optional
    whitespace then ``//``).  Backtick template literals are out of scope.
    """
    result: Dict[str, List[int]] = {}
    lines = source.splitlines()

    for m in _STR_LIT_RE.finditer(source):
        # Group 1 = single-quoted content; Group 2 = double-quoted content.
        # Exactly one is non-None per match (per-quote alternation).
        value = m.group(1) if m.group(1) is not None else m.group(2)
        # Compute line number (1-based).
        start = m.start()
        line_num = source[:start].count("\n") + 1
        col = start - source[:start].rfind("\n") - 1 if "\n" in source[:start] else start

        line_text = lines[line_num - 1] if line_num - 1 < len(lines) else ""

        # Skip if the literal is inside a line comment.
        if _is_in_line_comment(line_text, col):
            continue

        if value not in result:
            result[value] = []
        result[value].append(line_num)

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
# Inventory membership lookup
# ---------------------------------------------------------------------------

def _find_enums_for_value(value: str, inventory: Dict[str, List[str]]) -> List[str]:
    """Return a list of enum names whose member values contain ``value``."""
    return [name for name, vals in inventory.items() if value in vals]


# ---------------------------------------------------------------------------
# Main scanner
# ---------------------------------------------------------------------------

def scan_for_magic_enum_violations(
    root: Path,
    inventory: Dict[str, List[str]],
    allowlist_globs: List[str],
    generated_dirs: List[Path],
) -> List[Finding]:
    """Scan consumer source under ``root`` for magic-enum duplication violations.

    Parameters
    ----------
    root:
        Consumer project root.  File paths in returned ``Finding`` objects are
        relative to this directory.
    inventory:
        ``{EnumName: [member_string_values]}`` as returned by
        ``extract_enum_inventory``.
    allowlist_globs:
        List of glob patterns (matched against project-relative paths).
        Files matching any pattern are excluded from scanning.
    generated_dirs:
        Absolute paths of generated-types directories.  Files under these
        paths are excluded from scanning (they are the source-of-truth, not
        the consumer layer).

    Returns
    -------
    List of ``Finding`` objects.  ``Finding.path`` is relative to ``root``.
    ``Finding.rule`` is ``"magic_enum_duplication"``.
    """
    if not inventory:
        return []

    findings: List[Finding] = []
    root = root.resolve()

    for dirpath, _dirs, files in os.walk(str(root)):
        for fname in files:
            fpath = Path(dirpath) / fname
            if fpath.suffix not in _ELIGIBLE_EXTENSIONS:
                continue

            # Exclude files under generated dirs.
            if _is_under_generated(fpath, generated_dirs):
                continue

            try:
                rel_path = fpath.relative_to(root)
            except ValueError:
                continue

            rel_str = str(rel_path)

            # Exclude allowlisted paths.
            if path_in_allowlist(Path(rel_str), allowlist_globs):
                continue

            try:
                source = fpath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            # Determine which enum names this file imports AND uses via member access.
            imported_names = _extract_imported_names(source)
            exempted_enums: Set[str] = set()
            for enum_name in list(inventory.keys()):
                if enum_name in imported_names and _enum_used_via_member_access(source, enum_name):
                    exempted_enums.add(enum_name)

            # Extract all string literals with their line numbers.
            literals = _extract_literals(source)

            for value, line_numbers in literals.items():
                matching_enums = _find_enums_for_value(value, inventory)
                if not matching_enums:
                    continue

                # Filter out exempted enums.
                active_enums = [e for e in matching_enums if e not in exempted_enums]
                if not active_enums:
                    continue

                for line_num in line_numbers:
                    # Check inline escape.
                    if has_inline_escape(fpath, line_num):
                        continue

                    if len(active_enums) == 1:
                        enum_label = active_enums[0]
                        summary = (
                            "literal {value!r} matches generated enum member; "
                            "import {enum} and reference the member".format(
                                value=value,
                                enum=enum_label,
                            )
                        )
                    else:
                        enum_label = ", ".join(active_enums)
                        summary = (
                            "literal {value!r} matches generated enum members "
                            "({enums}); import the appropriate enum and reference "
                            "the member".format(
                                value=value,
                                enums=enum_label,
                            )
                        )

                    fix_hint = (
                        "import the appropriate enum from the generated-types dir "
                        "and replace the string literal with the enum member reference"
                    )

                    findings.append(
                        Finding(
                            rule="magic_enum_duplication",
                            path=rel_str,
                            line=line_num,
                            kind="VIOLATION",
                            summary=summary,
                            fix_hint=fix_hint,
                        )
                    )

    return findings
