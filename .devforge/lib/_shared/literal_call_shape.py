"""Patch 8 (V3) literal-replacement detection + Patch 9 call-shape parser.

LITERAL_TOKEN_RE matches primitive literals. LITERAL_REPLACEMENT_RE scans
prose for replacement patterns ("replace X with Y" / "X -> Y") and extracts
the source literal. CALL_SHAPE_RE + IDENT_CHAIN_RE drive arg-duplication
detection in proposed function-call shapes.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple


# Patch 8 (V3) — literal-token regex. Matches recognizable primitive literals
# as they appear in source code. Used by record-literal-archaeology's --literal
# validation AND by LITERAL_REPLACEMENT_RE to extract the <X> target from
# recommended-approach prose. Array / object / regex / function literals are
# OUT OF SCOPE (rarely surface as the "bug literal" in /research practice).
LITERAL_TOKEN_RE = re.compile(
    r"""
    (?:
        true | false | True | False        # JS/TS + Python booleans
      | null | undefined | None             # null-likes
      | -?0x[0-9a-fA-F]+                   # hex int (must come before decimal — share '-' prefix)
      | -?\d+n                              # BigInt
      | -?\d+(?:\.\d+)?[eE][+-]?\d+        # scientific
      | -?\d+(?:\.\d+)?                    # decimal int/float
      | "[^"]*"                             # double-quoted string
      | '[^']*'                             # single-quoted string
      | `[^`]*`                             # backtick template (no ${} interpolation)
    )
    """,
    re.VERBOSE,
)

# Literal-replacement prose patterns. Used by check 17 + Patch 9's
# proposed-call-shape gate. Anchors on LITERAL_TOKEN_RE to extract <X>.
# Three pattern forms (case-insensitive on the verb):
#   - "replace <X> with <Y>"
#   - "change <X> to <Y>"
#   - "<X> -> <Y>"  (also "<X> => <Y>")
# Captures <X> in group 1; <Y> capture not required for check 17 (only need
# the source literal to look up its archaeology row).
LITERAL_REPLACEMENT_RE = re.compile(
    r"""
    (?:
        (?:replace|change|swap) \s+ (?:the\s+literal\s+)? .*? (?P<src1>{LITERAL}) [^,\n]*? \s+ (?:with|to|for) \s+
      |
        (?P<src2>{LITERAL}) \s* (?:->|=>) \s*
    )
    """.replace("{LITERAL}", LITERAL_TOKEN_RE.pattern),
    re.VERBOSE | re.IGNORECASE,
)


def _detect_literal_replacement(text: str) -> Optional[str]:
    """Scan prose for a literal-replacement pattern. Returns the source
    literal (the <X> being replaced) if found, else None.

    Used by check 17 to decide whether literal-archaeology is required.
    Over-matching (false positives) is acceptable per plan §Patch 8 notes —
    better to require archaeology on a few non-literal fixes than miss
    actual literal-replacement cases.
    """
    if not text:
        return None
    m = LITERAL_REPLACEMENT_RE.search(text)
    if not m:
        return None
    return m.group("src1") or m.group("src2")


# Patch 9 (V3) — function-call-shape parser. Matches an identifier (with
# optional dotted member access) followed by a parenthesized arg list.
# Multi-line collapsed via whitespace-normalize before matching.
#
# Limitation: the inner arg-list match `[^)]*` stops at the first `)`,
# so any shape containing a nested function call in its arg list
# (e.g. `loadData(makeId(user), value, value)`) fails to match and
# `_detect_arg_duplication` returns None (fail-soft, no block). The
# `_split_top_level_args` helper tracks `([{` depth correctly, but it
# is unreachable for nested-call shapes — CALL_SHAPE_RE rejects them
# first. This is by-design per plan §Patch 9 "fragile by design"
# clause; documented to prevent future-session confusion.
CALL_SHAPE_RE = re.compile(r"^[A-Za-z_][\w.]*\(([^)]*)\)$")

# Identifier-with-optional-chaining regex. Matches:
#   - bare identifier `x`
#   - dotted member access `a.b.c`
#   - optional chaining `a?.b?.c` (modern JS/TS)
# Does NOT match: function calls `f()`, bracket access `a[0]`, literals,
# arithmetic expressions. These appear in arg lists but are not the
# "duplicate identifier" pattern Patch 9 targets.
IDENT_CHAIN_RE = re.compile(r"^[A-Za-z_]\w*(?:\??\.[A-Za-z_]\w*)*$")


def _normalize_call_shape(text):
    # type: (Optional[str]) -> str
    """Collapse multi-line whitespace + strip surrounding whitespace.

    Patch 9 supports multi-line call shapes (LLM may format the proposed
    fix as multiline for readability). Normalize before regex match.
    """
    if text is None:
        return ""
    return " ".join(text.split())


def _split_top_level_args(arg_list_text):
    # type: (Optional[str]) -> Optional[List[str]]
    """Split an arg-list string on top-level commas (commas outside
    nested parens / brackets / braces). Returns list of trimmed arg
    strings, OR None on imbalanced delimiters (parser failure — caller
    should fail-soft per plan §Patch 9 'fragile by design' note).

    Empty input returns []. Single arg returns [arg]. Whitespace-only
    args are kept (caller decides if they signify a parser bug).
    """
    if arg_list_text is None:
        return []
    text = arg_list_text.strip()
    if not text:
        return []
    args = []  # type: List[str]
    depth = 0
    buf = []  # type: List[str]
    for ch in text:
        if ch in "([{":
            depth += 1
            buf.append(ch)
        elif ch in ")]}":
            depth -= 1
            if depth < 0:
                return None
            buf.append(ch)
        elif ch == "," and depth == 0:
            args.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if depth != 0:
        return None
    args.append("".join(buf).strip())
    return args


def _detect_arg_duplication(call_shape):
    # type: (str) -> Optional[Tuple[str, int]]
    """Parse a function-call shape string + detect identifier
    duplication. Returns (duplicated_identifier, count) on duplication
    found; None on no duplication OR parser-failure (fail-soft —
    caller treats None as "no block").

    Steps:
      1. Normalize whitespace.
      2. Match top-level CALL_SHAPE_RE (function-name + paren arg list).
         On no match -> parser failure -> return None. Shapes containing
         nested function calls (e.g. `f(g(x), y)`) fail at this step
         because CALL_SHAPE_RE's inner `[^)]*` stops at the first `)` —
         documented limitation per CALL_SHAPE_RE comment block.
      3. Split arg list on top-level commas.
      4. For each arg, test against IDENT_CHAIN_RE. Args that don't
         match are ignored (not pure identifiers — won't count as
         duplicates even if textually identical, since they may be
         literals, function calls, expressions, etc.).
      5. Among identifier args, find any whose count > 1.
      6. Return (first_duplicated, count) or None.
    """
    if not call_shape or not call_shape.strip():
        return None
    normalized = _normalize_call_shape(call_shape)
    m = CALL_SHAPE_RE.match(normalized)
    if not m:
        return None
    arg_list_text = m.group(1)
    args = _split_top_level_args(arg_list_text)
    if args is None:
        return None
    identifiers = [a for a in args if IDENT_CHAIN_RE.match(a)]
    seen = {}  # type: Dict[str, int]
    for ident in identifiers:
        seen[ident] = seen.get(ident, 0) + 1
    for ident, count in seen.items():
        if count > 1:
            return (ident, count)
    return None
