"""Generated-enum value inventory parser for the magic-enum detector (Phase 1).

Scans TypeScript ``*.ts``, ``*.d.ts``, and ``*.tsx`` files under a list of
generated-types directories and extracts the string-literal values exported
from enum declarations, string-literal union type aliases, and typed
const-object patterns.

Public API
----------
extract_enum_inventory(generated_dirs)
    Walk each dir in ``generated_dirs``, parse each eligible file, merge
    results into ``{enum_or_union_name: [member_string_values]}``.

Recognized shapes
-----------------
1. TypeScript string enum::

       enum X { A = 'a', B = 'b' }

   Members with non-string RHS (numeric, computed, no ``=``) are skipped.

2. String-literal union type alias::

       type X = 'a' | 'b' | 'c'

   Single-line and multi-line variants. Non-literal members (e.g.,
   ``string``, ``number``) within the union are skipped; only
   string-literal members are recorded.

3. Const-object typed with ``as const``::

       const X = { A: 'a' as const, B: 'b' as const } as const

   The trailing ``as const`` on BOTH each member value AND the whole
   object is required. Plain ``const X = { A: 'a' }`` (no ``as const``)
   is NOT recorded — it is a regular object, not a typed enum-equivalent.

Out of scope (Phase 1)
----------------------
- Numeric enums (no string values to match downstream).
- Computed enum values (e.g., ``A = someFn()``).
- Re-exports (``export { X } from './other'``) — only defining files are
  scanned.
- Mapped types, conditional types, intersection types.
- Template literal types (``${X}_FOO``).
- Multi-file inheritance / namespace declarations.

Name collision
--------------
If two files in ``generated_dirs`` define an enum with the same name, the
last file processed wins (last-wins for Phase 1).  Upgrade to tree-sitter
in Phase 2 if precision requires first-wins or merge semantics.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Match a string literal token: either 'value' or "value" (single-line only).
# Per-quote alternation so an opening ' is not closed by an embedded "
# (and vice versa).  Group 1 = single-quoted content; Group 2 = double-quoted
# content; exactly one is non-None per match.
_STRING_LIT_RE = re.compile(r"""'((?:[^'\\]|\\.)*)'|"((?:[^"\\]|\\.)*)\"""")

# ---------------------------------------------------------------------------
# TypeScript enum parser
# ---------------------------------------------------------------------------

# Captures enum body across possible multi-line spans.
# Group 1 = enum name; Group 2 = full body between { and }.
_ENUM_RE = re.compile(
    r"""(?:export\s+)?(?:const\s+)?enum\s+(\w+)\s*\{([^}]*)\}""",
    re.DOTALL,
)

# One member inside an enum body: name = 'value'  or  name = "value"
# Per-quote alternation prevents cross-quote leakage (an opening ' cannot be
# closed by a stray "). Group 2 = single-quoted value; Group 3 = double-quoted.
_ENUM_MEMBER_RE = re.compile(
    r"""(\w+)\s*=\s*(?:'((?:[^'\\]|\\.)*)'|"((?:[^"\\]|\\.)*)")""",
)


def _parse_ts_enums(source: str) -> Dict[str, List[str]]:
    """Extract string-valued enum members from TypeScript source.

    Returns ``{EnumName: [string_values]}``.  Enums with no string members
    produce no entry.
    """
    result: Dict[str, List[str]] = {}
    for m in _ENUM_RE.finditer(source):
        name = m.group(1)
        body = m.group(2)
        values: List[str] = []
        for mem in _ENUM_MEMBER_RE.finditer(body):
            # Group 2 = single-quoted value; Group 3 = double-quoted value.
            # Exactly one is non-None per match (per-quote alternation).
            val = mem.group(2) if mem.group(2) is not None else mem.group(3)
            if val is not None:
                values.append(val)
        if values:
            result[name] = values
    return result


# ---------------------------------------------------------------------------
# String-literal union type parser
# ---------------------------------------------------------------------------

# Two-phase approach:
# Phase A: locate "type X = ..." declarations (possibly multi-line, ending
#           when the next non-continuation line is found).
# Phase B: from the RHS, collect string literal tokens.

# Match "type Name = " with optional export prefix.
_TYPE_ALIAS_START_RE = re.compile(
    r"""(?:export\s+)?type\s+(\w+)\s*=(.*)""",
)

# Detect a line that looks like a continuation of a multi-line union:
# starts with optional whitespace then | or ends with |.
_CONTINUATION_RE = re.compile(r"""^\s*\|""")


def _parse_type_unions(source: str) -> Dict[str, List[str]]:
    """Extract string-literal members from TypeScript union type aliases.

    Handles both single-line and multi-line variants.  Non-literal union
    members (bare type names like ``string``, ``number``) are skipped.

    Returns ``{TypeName: [string_values]}``.  Type aliases whose RHS
    contains no string literals produce no entry.
    """
    result: Dict[str, List[str]] = {}
    lines = source.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = _TYPE_ALIAS_START_RE.match(line.strip())
        if m:
            type_name = m.group(1)
            # Accumulate the RHS — may span multiple lines joined by |.
            rhs_parts = [m.group(2)]
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                if _CONTINUATION_RE.match(next_line):
                    rhs_parts.append(next_line)
                    j += 1
                else:
                    break
            i = j  # advance past the consumed lines
            rhs = " ".join(rhs_parts)
            # A true string-literal union has RHS made of literal alternatives
            # joined by `|` (optionally interspersed with bare type names like
            # ``string`` or ``number``).  Reject object-typed aliases (RHS
            # contains `{` — object/property type), function types (contains
            # `=>`), and generic / array / index types.  Phase 2 empirical
            # verify on testForge20 surfaced GraphQL codegen pattern
            # ``type X = { __typename: 'Y' }`` flooding the inventory with
            # property-typed string literals that should NOT be treated as
            # enum members.  Reject any RHS that looks like an object/function
            # type so only bona-fide string-literal unions land in inventory.
            if "{" in rhs or "=>" in rhs:
                # Skip this alias entirely; i already advanced to j above.
                continue
            # Per-quote alternation: group(1) = single-quoted; group(2) =
            # double-quoted.  Exactly one is non-None per match.
            values = [
                (mm.group(1) if mm.group(1) is not None else mm.group(2))
                for mm in _STRING_LIT_RE.finditer(rhs)
            ]
            if values:
                result[type_name] = values
        else:
            i += 1
    return result


# ---------------------------------------------------------------------------
# Const-object as const parser
# ---------------------------------------------------------------------------

# Matches: (export )? const NAME = { ... } as const
# The body must close with "} as const" on the same or a subsequent line.
# We accept the whole block and then validate that EVERY value member has
# "as const" after its string literal.

_CONST_OBJ_RE = re.compile(
    r"""(?:export\s+)?const\s+(\w+)\s*=\s*\{([^}]*)\}\s*as\s+const""",
    re.DOTALL,
)

# One value member with "as const": key: 'value' as const  or key: "value" as const
# Per-quote alternation. Group 2 = single-quoted; Group 3 = double-quoted.
_CONST_MEMBER_RE = re.compile(
    r"""(\w+)\s*:\s*(?:'((?:[^'\\]|\\.)*)'|"((?:[^"\\]|\\.)*)")\s+as\s+const""",
)


def _parse_const_as_const(source: str) -> Dict[str, List[str]]:
    """Extract values from ``const X = { A: 'a' as const, ... } as const``.

    Only records entries where every value member follows the ``'x' as const``
    form.  Members without ``as const`` are skipped individually; if no
    members pass the filter, the object is not recorded.

    Returns ``{ConstName: [string_values]}``.
    """
    result: Dict[str, List[str]] = {}
    for m in _CONST_OBJ_RE.finditer(source):
        name = m.group(1)
        body = m.group(2)
        values: List[str] = []
        for mem in _CONST_MEMBER_RE.finditer(body):
            # Group 2 = single-quoted value; Group 3 = double-quoted value.
            # Exactly one is non-None per match (per-quote alternation).
            val = mem.group(2) if mem.group(2) is not None else mem.group(3)
            if val is not None:
                values.append(val)
        if values:
            result[name] = values
    return result


# ---------------------------------------------------------------------------
# File-level parser dispatcher
# ---------------------------------------------------------------------------

def _parse_file(source: str) -> Dict[str, List[str]]:
    """Parse one TypeScript file's source and return all recognized inventories."""
    result: Dict[str, List[str]] = {}
    # Order matters for last-wins merge within one file (rare).
    result.update(_parse_type_unions(source))
    result.update(_parse_ts_enums(source))
    result.update(_parse_const_as_const(source))
    return result


# ---------------------------------------------------------------------------
# Directory walker
# ---------------------------------------------------------------------------

_ELIGIBLE_EXTENSIONS = {".ts", ".tsx"}  # .d.ts is caught by .ts suffix


def extract_enum_inventory(generated_dirs: List[Path]) -> Dict[str, List[str]]:
    """Walk each dir in generated_dirs and extract all recognizable enum inventories.

    Parameters
    ----------
    generated_dirs:
        Absolute paths to directories containing generated TypeScript type
        definitions (e.g., ``packages/cse-types/src``).  Non-existent dirs
        are silently skipped.

    Returns
    -------
    Dict mapping ``EnumOrUnionName -> [member_string_values]``.  Across
    multiple files, last-wins applies when two files define the same name.

    File extensions walked: ``.ts``, ``.d.ts``, ``.tsx``.
    """
    inventory: Dict[str, List[str]] = {}
    for gen_dir in generated_dirs:
        gen_path = Path(gen_dir)
        if not gen_path.is_dir():
            continue
        for root, _dirs, files in os.walk(str(gen_path)):
            for fname in files:
                fpath = Path(root) / fname
                # Catch .d.ts via the .ts suffix check.
                if fpath.suffix not in _ELIGIBLE_EXTENSIONS:
                    continue
                try:
                    source = fpath.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                inventory.update(_parse_file(source))
    return inventory
