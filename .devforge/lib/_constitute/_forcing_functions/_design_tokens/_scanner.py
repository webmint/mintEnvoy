"""Static provenance scanner for design tokens (plan 40 Phase 4).

Scans component style sources (CSS / styled-components / CSS-in-JS) for
five categories of provenance violations:

  Check 1 — No hardcoded color literals
      Hex short (#abc), hex full (#aabbcc), hex 8-digit (#aabbccff),
      rgb()/rgba()/hsl()/hsla() function calls, CSS named colors.
      Allowlist: transparent, currentColor, inherit, none.

  Check 2 — No var(--x, <literal>) fallbacks
      var(--token) is fine; var(--token, #fff) / var(--token, 8px) is a
      violation (the silent-guess failure in CSS form).

  Check 3 — Undefined token (fail-loud)
      var(--token) whose --token is defined in NO reachable token source →
      escalate (VIOLATION), never silently accept.
      When no token source is supplied, this check is skipped entirely
      (per OQ-6: absence of CSS → spacing check relaxes, but color/border
      literal checks remain hard regardless).

  Check 4 — Missing interactive-element state declarations
      button, a, input, select, textarea, and [role=button] must each
      declare BOTH :hover AND :focus-visible.  Missing either is a
      violation.

  Check 5 — MATCH-element token binding (manifest-keyed)
      For elements dispositioned MATCH (keyed by data-ref anchor), their
      bound visual values must reference tokens (var(--...)), not literals.
      Requires a design manifest (list of MATCH data-ref anchors); skipped
      when no manifest is provided.

Walk semantics
--------------
Extensions scanned: *.css, *.scss, *.less, *.ts, *.tsx, *.js, *.jsx, *.vue.

Files matching allowlist_globs are excluded.

OQ-6 relaxation (spacing)
--------------------------
When spacing_scale is supplied ({"available": True, "scale": [...]}) the
spacing token-binding sub-check inside Check 5 is active.  When spacing
scale is absent ({"available": False} or not supplied), spacing literal
violations are NOT raised under Check 5 — but color/border literal
violations (Check 1) remain hard regardless.

Escalation model (Check 3)
--------------------------
An UNDEFINED token is treated as a hard failure: it is reported with
kind="VIOLATION" and summary naming the undefined token.  This matches the
plan requirement "FAIL LOUDLY: a var(--token) whose --token is defined in
NO reachable token source → violation (escalate, never silently accept)."

Python 3.8+ compatible; stdlib only.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set

from .._shared import Finding, path_in_allowlist

# ---------------------------------------------------------------------------
# CSS named colors (subset: the 148 CSS Level 4 named colors that are NOT
# in the token-provenance allowlist).  These strings are matched
# case-insensitively as whole words inside property values.
# ---------------------------------------------------------------------------

_CSS_NAMED_COLORS: Set[str] = {
    "aliceblue", "antiquewhite", "aqua", "aquamarine", "azure",
    "beige", "bisque", "black", "blanchedalmond", "blue",
    "blueviolet", "brown", "burlywood", "cadetblue", "chartreuse",
    "chocolate", "coral", "cornflowerblue", "cornsilk", "crimson",
    "cyan", "darkblue", "darkcyan", "darkgoldenrod", "darkgray",
    "darkgreen", "darkgrey", "darkkhaki", "darkmagenta",
    "darkolivegreen", "darkorange", "darkorchid", "darkred",
    "darksalmon", "darkseagreen", "darkslateblue", "darkslategray",
    "darkslategrey", "darkturquoise", "darkviolet", "deeppink",
    "deepskyblue", "dimgray", "dimgrey", "dodgerblue", "firebrick",
    "floralwhite", "forestgreen", "fuchsia", "gainsboro",
    "ghostwhite", "gold", "goldenrod", "gray", "green",
    "greenyellow", "grey", "honeydew", "hotpink", "indianred",
    "indigo", "ivory", "khaki", "lavender", "lavenderblush",
    "lawngreen", "lemonchiffon", "lightblue", "lightcoral",
    "lightcyan", "lightgoldenrodyellow", "lightgray", "lightgreen",
    "lightgrey", "lightpink", "lightsalmon", "lightseagreen",
    "lightskyblue", "lightslategray", "lightslategrey",
    "lightsteelblue", "lightyellow", "lime", "limegreen", "linen",
    "magenta", "maroon", "mediumaquamarine", "mediumblue",
    "mediumorchid", "mediumpurple", "mediumseagreen",
    "mediumslateblue", "mediumspringgreen", "mediumturquoise",
    "mediumvioletred", "midnightblue", "mintcream", "mistyrose",
    "moccasin", "navajowhite", "navy", "oldlace", "olive",
    "olivedrab", "orange", "orangered", "orchid", "palegoldenrod",
    "palegreen", "paleturquoise", "palevioletred", "papayawhip",
    "peachpuff", "peru", "pink", "plum", "powderblue", "purple",
    "rebeccapurple", "red", "rosybrown", "royalblue", "saddlebrown",
    "salmon", "sandybrown", "seagreen", "seashell", "sienna",
    "silver", "skyblue", "slateblue", "slategray", "slategrey",
    "snow", "springgreen", "steelblue", "tan", "teal", "thistle",
    "tomato", "turquoise", "violet", "wheat", "white", "whitesmoke",
    "yellow", "yellowgreen",
}

# Allowlisted color keywords (never a violation).
_COLOR_ALLOWLIST: Set[str] = {"transparent", "currentcolor", "inherit", "none"}

# ---------------------------------------------------------------------------
# Interactive-element selector keywords.
# These are matched as substrings in selector text (lower-cased).
# ---------------------------------------------------------------------------

_INTERACTIVE_SELECTORS: List[str] = [
    "button",
    " a",
    ">a",
    ",a",
    ":a",
    "a[",
    "input",
    "select",
    "textarea",
    '[role="button"]',
    "[role=button]",
    "[role='button']",
]

# ---------------------------------------------------------------------------
# Eligible extensions
# ---------------------------------------------------------------------------

_STYLE_EXTENSIONS: Set[str] = {".css", ".scss", ".less"}
_JS_EXTENSIONS: Set[str] = {".ts", ".tsx", ".js", ".jsx", ".vue"}
_ELIGIBLE_EXTENSIONS: Set[str] = _STYLE_EXTENSIONS | _JS_EXTENSIONS

# ---------------------------------------------------------------------------
# Regex patterns for Check 1 (color literals)
# ---------------------------------------------------------------------------

# Hex color: #rgb, #rrggbb, #rrggbbaa (case-insensitive)
_HEX_RE = re.compile(r"#([0-9a-fA-F]{3,8})\b")

# Functional color notations
_FUNC_COLOR_RE = re.compile(
    r"\b(rgba?|hsla?)\s*\("
)

# CSS named color as a standalone word (word boundaries)
def _build_named_color_re() -> "re.Pattern[str]":
    # Sort longest first to avoid partial matches with shorter prefixes.
    sorted_colors = sorted(_CSS_NAMED_COLORS, key=len, reverse=True)
    pattern = r"\b(?:" + "|".join(re.escape(c) for c in sorted_colors) + r")\b"
    return re.compile(pattern, re.IGNORECASE)

_NAMED_COLOR_RE = _build_named_color_re()

# ---------------------------------------------------------------------------
# Regex patterns for Check 2 (var fallback)
# ---------------------------------------------------------------------------

# Matches var(--token, <anything>) — the fallback form.
# We use a simple approach: find var( then look for a comma before the closing ).
# We capture the fallback so we can report it.
_VAR_FALLBACK_RE = re.compile(
    r"var\s*\(\s*--[\w-]+\s*,\s*([^)]+)\)"
)

# ---------------------------------------------------------------------------
# Regex patterns for Check 3 (undefined token)
# ---------------------------------------------------------------------------

# Matches bare var(--token) without a fallback.
_VAR_NO_FALLBACK_RE = re.compile(
    r"var\s*\(\s*(--[\w-]+)\s*\)"
)

# CSS custom property definition: --token-name: value;
_TOKEN_DEF_RE = re.compile(r"(--[\w-]+)\s*:")

# ---------------------------------------------------------------------------
# Regex patterns for Check 4 (interactive element states)
# ---------------------------------------------------------------------------

# Selector lines containing :hover or :focus-visible
_HOVER_SEL_RE = re.compile(r":hover\b")
_FOCUS_VISIBLE_SEL_RE = re.compile(r":focus-visible\b")

# Match CSS rule blocks: selector { declarations }
# We use a depth-aware parser for this to handle nested rules.

# ---------------------------------------------------------------------------
# CSS block parser (depth-aware, reused for checks 1/3/4)
# ---------------------------------------------------------------------------

def _extract_css_blocks(css_text):
    # type: (str) -> List[tuple]
    """Extract (selector_str, declarations_str) pairs from CSS text.

    Handles nested @-rules (depth-aware brace counting).  Returns top-level
    and nested rule blocks.  Does NOT handle block comments spanning multiple
    lines perfectly, but strips single-line // comments (styled-components).

    Returns list of (selector, body) tuples where body is the text between
    the outermost { } for that rule.
    """
    blocks = []  # type: List[tuple]
    i = 0
    n = len(css_text)
    current_selector = []  # type: List[str]
    selector_start = 0
    depth = 0
    block_start = -1
    in_string = None  # type: Optional[str]
    in_comment = False  # block comment
    in_line_comment = False

    while i < n:
        ch = css_text[i]

        # Track block comments /* ... */
        if in_comment:
            if ch == "*" and i + 1 < n and css_text[i + 1] == "/":
                in_comment = False
                i += 2
                continue
            i += 1
            continue

        # Track line comments // ... (CSS-in-JS / SCSS)
        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue

        # Detect entering comments
        if not in_string:
            if ch == "/" and i + 1 < n and css_text[i + 1] == "*":
                in_comment = True
                i += 2
                continue
            if ch == "/" and i + 1 < n and css_text[i + 1] == "/":
                in_line_comment = True
                i += 2
                continue

        # Track string literals (template literals in JS)
        if in_string:
            if ch == "\\" and i + 1 < n:
                i += 2
                continue
            if ch == in_string:
                in_string = None
            i += 1
            continue

        if ch in ('"', "'", "`"):
            in_string = ch
            i += 1
            continue

        if ch == "{":
            if depth == 0:
                selector_text = css_text[selector_start:i]
                current_selector.append(selector_text)
                block_start = i + 1
            depth += 1
            i += 1
            continue

        if ch == "}":
            depth -= 1
            if depth == 0 and block_start >= 0:
                body = css_text[block_start:i]
                sel = "".join(current_selector).strip()
                blocks.append((sel, body))
                current_selector = []
                selector_start = i + 1
                block_start = -1
            i += 1
            continue

        i += 1

    return blocks


def _extract_defined_tokens(css_text):
    # type: (str) -> Set[str]
    """Return the set of CSS custom property names defined in css_text."""
    return set(_TOKEN_DEF_RE.findall(css_text))


# ---------------------------------------------------------------------------
# Value extraction from CSS/JS inline styles
# ---------------------------------------------------------------------------

def _strip_comments(line):
    # type: (str) -> str
    """Remove // line comments from a line (for JS/TS style scanning)."""
    # Only strip // that appears outside strings (simple heuristic).
    in_str = None  # type: Optional[str]
    for i, ch in enumerate(line):
        if in_str:
            if ch == "\\" and i + 1 < len(line):
                continue
            if ch == in_str:
                in_str = None
        else:
            if ch in ('"', "'", "`"):
                in_str = ch
            elif ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                return line[:i]
    return line


# ---------------------------------------------------------------------------
# Check 1: color literal detection
# ---------------------------------------------------------------------------

def _check1_color_literals(
    source,  # type: str
    rel_path,  # type: str
    rule,  # type: str
):
    # type: (...) -> List[Finding]
    """Scan source text for hardcoded color literals (Check 1)."""
    findings = []  # type: List[Finding]

    for line_num, line in enumerate(source.splitlines(), start=1):
        stripped = _strip_comments(line)

        # Skip lines that define a CSS custom property value anywhere on the line
        # (e.g., `--color-primary: #abc;` or `:root { --color-primary: #abc; }`
        # are TOKEN DEFINITIONS, not usages).  re.search (not re.match) so that
        # single-line `:root { --x: #abc; }` forms are also recognised.
        is_token_definition = bool(re.search(r"--[\w-]+\s*:", stripped))

        # Check hex colors
        for m in _HEX_RE.finditer(stripped):
            hex_val = m.group(1)
            # Only valid hex lengths: 3, 4, 6, 8
            if len(hex_val) not in (3, 4, 6, 8):
                continue
            # Skip if this is inside a var() reference (e.g. var(--color))
            # which won't produce hex — skip the standard allowlist check
            full_match = m.group(0).lower()
            if full_match in _COLOR_ALLOWLIST:
                continue
            if is_token_definition:
                continue
            findings.append(Finding(
                rule=rule,
                path=rel_path,
                line=line_num,
                kind="VIOLATION",
                summary=(
                    "hardcoded color literal {val!r} — use a design token "
                    "(var(--...)) instead".format(val=m.group(0))
                ),
                fix_hint="Replace {val!r} with the appropriate var(--color-token)".format(
                    val=m.group(0)
                ),
            ))

        # Check functional color notations rgb/rgba/hsl/hsla
        for m in _FUNC_COLOR_RE.finditer(stripped):
            if is_token_definition:
                continue
            findings.append(Finding(
                rule=rule,
                path=rel_path,
                line=line_num,
                kind="VIOLATION",
                summary=(
                    "hardcoded {fn}() color literal — use a design token "
                    "(var(--...)) instead".format(fn=m.group(1))
                ),
                fix_hint=(
                    "Replace {fn}(...) with the appropriate "
                    "var(--color-token)".format(fn=m.group(1))
                ),
            ))

        # Check CSS named colors — only in PROPERTY-VALUE positions, not class
        # names, identifiers, or token names.  Two guards:
        # 1. A `:` (property separator) must appear BEFORE the match position —
        #    so `color: red` fires but `.coral-button {}` does not.
        # 2. The character immediately before the match must not be `-`, which
        #    would mean the color word is part of a hyphenated compound name or
        #    CSS custom property name (e.g. `--color-teal`, `.btn-teal`).
        for m in _NAMED_COLOR_RE.finditer(stripped):
            color_word = m.group(0).lower()
            if color_word in _COLOR_ALLOWLIST:
                continue
            if is_token_definition:
                continue
            # Guard 1: require a colon before the match position.
            text_before = stripped[:m.start()]
            if ":" not in text_before:
                continue
            # Guard 2: skip if immediately preceded by `-` (part of a compound
            # name like `--color-teal` or `btn-teal`).
            if m.start() > 0 and stripped[m.start() - 1] == "-":
                continue
            findings.append(Finding(
                rule=rule,
                path=rel_path,
                line=line_num,
                kind="VIOLATION",
                summary=(
                    "hardcoded named color '{color}' — use a design token "
                    "(var(--...)) instead".format(color=m.group(0))
                ),
                fix_hint=(
                    "Replace '{color}' with var(--color-token)".format(
                        color=m.group(0)
                    )
                ),
            ))

    return findings


# ---------------------------------------------------------------------------
# Check 2: var(--x, <literal>) fallback
# ---------------------------------------------------------------------------

def _check2_var_fallbacks(
    source,  # type: str
    rel_path,  # type: str
    rule,  # type: str
):
    # type: (...) -> List[Finding]
    """Scan for var(--token, <literal>) fallback patterns (Check 2)."""
    findings = []  # type: List[Finding]

    for line_num, line in enumerate(source.splitlines(), start=1):
        stripped = _strip_comments(line)
        for m in _VAR_FALLBACK_RE.finditer(stripped):
            fallback_val = m.group(1).strip()
            # Empty fallback is fine (var(--x, )) — only flag non-empty literals
            if not fallback_val:
                continue
            # A fallback that is itself another var() is a chained token — fine
            if fallback_val.startswith("var("):
                continue
            findings.append(Finding(
                rule=rule,
                path=rel_path,
                line=line_num,
                kind="VIOLATION",
                summary=(
                    "var() fallback literal '{val}' — the silent-guess failure; "
                    "define the token or remove the fallback".format(val=fallback_val)
                ),
                fix_hint=(
                    "Remove the fallback or define the token properly so "
                    "no fallback is needed: var(--token) without a second argument"
                ),
            ))

    return findings


# ---------------------------------------------------------------------------
# Check 3: undefined token (fail-loud)
# ---------------------------------------------------------------------------

def _check3_undefined_tokens(
    source,  # type: str
    rel_path,  # type: str
    rule,  # type: str
    defined_tokens,  # type: Set[str]
):
    # type: (...) -> List[Finding]
    """Scan for var(--token) where --token is NOT in defined_tokens (Check 3).

    Only runs when defined_tokens is non-empty (i.e. a token source was supplied).
    When defined_tokens is empty, this check is a no-op (skipped per OQ-6 relaxation).
    """
    if not defined_tokens:
        # No token source → skip this check entirely (OQ-6: absent CSS relaxes)
        return []

    findings = []  # type: List[Finding]

    for line_num, line in enumerate(source.splitlines(), start=1):
        stripped = _strip_comments(line)
        # Skip token definition lines anywhere on the line (--foo: value or
        # :root { --foo: value }) — these define tokens, not use them.
        if re.search(r"--[\w-]+\s*:", stripped):
            continue
        for m in _VAR_NO_FALLBACK_RE.finditer(stripped):
            token_name = m.group(1)
            if token_name not in defined_tokens:
                findings.append(Finding(
                    rule=rule,
                    path=rel_path,
                    line=line_num,
                    kind="VIOLATION",
                    summary=(
                        "undefined token {tok!r} — not defined in any reachable "
                        "token source; escalate or define the token".format(
                            tok=token_name
                        )
                    ),
                    fix_hint=(
                        "Define {tok} in the token source file (e.g., "
                        "design/styles.css) or remove the usage".format(tok=token_name)
                    ),
                ))

    return findings


# ---------------------------------------------------------------------------
# Check 4: interactive element missing :hover / :focus-visible
# ---------------------------------------------------------------------------

def _selector_matches_interactive(selector_text):
    # type: (str) -> bool
    """Return True if selector_text targets an interactive element type.

    Checks for: button, a (anchor), input, select, textarea, [role=button].
    Uses heuristic substring matching on the lower-cased selector.
    """
    lower = selector_text.lower()
    # Strip the state suffix (e.g., ":hover", ":focus-visible") so we're
    # testing the base element, not the state.
    base = re.sub(r":+[\w-]+", "", lower)

    patterns = [
        r"\bbutton\b",
        r"\ba\b",
        r"\binput\b",
        r"\bselect\b",
        r"\btextarea\b",
        r'\[role\s*=\s*["\']?button["\']?\]',
    ]
    for pat in patterns:
        if re.search(pat, base):
            return True
    return False


def _check4_interactive_states(
    source,  # type: str
    rel_path,  # type: str
    rule,  # type: str
):
    # type: (...) -> List[Finding]
    """Scan CSS blocks for interactive elements missing :hover or :focus-visible.

    Builds a selector set from the CSS blocks, then for each interactive
    selector finds whether its :hover and :focus-visible counterparts both exist.
    Reports violations at the line where the rule block opener is found.
    """
    findings = []  # type: List[Finding]

    blocks = _extract_css_blocks(source)
    if not blocks:
        return findings

    # Build a set of all declared selectors (lowercased) for state lookup.
    # Also detect SCSS-style nested `&:hover` / `&:focus-visible` inside a
    # parent block body and credit them as state rules on the parent selector.
    all_selectors = set()  # type: Set[str]
    for sel, body in blocks:
        # Handle comma-split multi-selectors
        for part in sel.split(","):
            all_selectors.add(part.strip().lower())
        # Detect SCSS nested `&:hover { ... }` and `&:focus-visible { ... }` in body.
        # We do a simple text scan rather than recursing into the block parser to
        # keep the logic O(n) and dependency-free.
        for part in sel.split(","):
            part_lower = part.strip().lower()
            if "&:hover" in body.lower():
                # Synthesise the resolved selector: replace `&` with the parent
                # (strip trailing pseudo-class from parent first to avoid doubling)
                base_for_synth = re.sub(r"::?[\w-]+(\([^)]*\))?", "", part_lower).strip()
                all_selectors.add(base_for_synth + ":hover")
            if "&:focus-visible" in body.lower():
                base_for_synth = re.sub(r"::?[\w-]+(\([^)]*\))?", "", part_lower).strip()
                all_selectors.add(base_for_synth + ":focus-visible")

    # For each interactive selector found, check that both states are present.
    seen_bases = set()  # type: Set[str]
    lines = source.splitlines()

    for sel, _body in blocks:
        for part in sel.split(","):
            part_stripped = part.strip()
            lower = part_stripped.lower()
            # Skip state selectors (already a :hover or :focus-visible rule)
            if ":hover" in lower or ":focus-visible" in lower:
                continue
            if not _selector_matches_interactive(lower):
                continue
            # Normalize the base selector (strip pseudo-classes for base lookup)
            base_sel = re.sub(r"::?[\w-]+(\([^)]*\))?", "", lower).strip()
            if base_sel in seen_bases:
                continue
            seen_bases.add(base_sel)

            has_hover = False
            has_focus_visible = False
            for candidate in all_selectors:
                candidate_base = re.sub(
                    r"::?[\w-]+(\([^)]*\))?", "", candidate
                ).strip()
                if candidate_base != base_sel:
                    continue
                if ":hover" in candidate:
                    has_hover = True
                if ":focus-visible" in candidate:
                    has_focus_visible = True

            # Find the line number of this selector in the source
            line_num = 1
            search_fragment = part_stripped[:40]  # first 40 chars of selector
            for idx, raw_line in enumerate(lines, start=1):
                if search_fragment and search_fragment in raw_line:
                    line_num = idx
                    break

            if not has_hover:
                findings.append(Finding(
                    rule=rule,
                    path=rel_path,
                    line=line_num,
                    kind="VIOLATION",
                    summary=(
                        "interactive element '{sel}' missing :hover state — "
                        "required for all interactive elements".format(
                            sel=part_stripped
                        )
                    ),
                    fix_hint=(
                        "Add a {sel}:hover rule with the appropriate "
                        "token-bound hover style".format(sel=part_stripped)
                    ),
                ))
            if not has_focus_visible:
                findings.append(Finding(
                    rule=rule,
                    path=rel_path,
                    line=line_num,
                    kind="VIOLATION",
                    summary=(
                        "interactive element '{sel}' missing :focus-visible state — "
                        "required for accessibility".format(sel=part_stripped)
                    ),
                    fix_hint=(
                        "Add a {sel}:focus-visible rule with the appropriate "
                        "token-bound focus style".format(sel=part_stripped)
                    ),
                ))

    return findings


# ---------------------------------------------------------------------------
# Check 5: MATCH-element token binding (manifest-keyed)
# ---------------------------------------------------------------------------

def _check5_match_token_binding(
    source,  # type: str
    rel_path,  # type: str
    rule,  # type: str
    match_refs,  # type: Set[str]
    spacing_scale_available,  # type: bool
):
    # type: (...) -> List[Finding]
    """Scan for MATCH elements whose bound visual values are literal, not tokens.

    For each block whose selector contains a data-ref from match_refs, check
    that color/border values use var(--token) not literal values.  When
    spacing_scale_available is False, spacing-literal violations are skipped
    (OQ-6 relaxation).

    This check uses a heuristic: it looks for 'data-ref="<id>"' or
    '[data-ref=<id>]' patterns in the selector to identify bound elements,
    then scans the block body for literal values.
    """
    if not match_refs:
        return []

    findings = []  # type: List[Finding]
    blocks = _extract_css_blocks(source)
    lines = source.splitlines()

    # Color-like literal patterns (shared with Check 1 but applied per-block)
    for sel, body in blocks:
        # Find which data-ref this selector targets (if any)
        matched_ref = None  # type: Optional[str]
        for ref in match_refs:
            # Match [data-ref="ref"] or [data-ref='ref'] or [data-ref=ref]
            pat = r'\[data-ref\s*=\s*["\']?' + re.escape(ref) + r'["\']?\]'
            if re.search(pat, sel):
                matched_ref = ref
                break

        if matched_ref is None:
            continue

        # Determine approximate line number of the selector
        line_num = 1
        search_fragment = sel.strip()[:40]
        for idx, raw_line in enumerate(lines, start=1):
            if search_fragment and search_fragment in raw_line:
                line_num = idx
                break

        # Scan the block body for literal color values
        for body_line_offset, body_line in enumerate(body.splitlines()):
            body_line_stripped = _strip_comments(body_line).strip()
            # Skip token definitions and var() references
            if re.match(r"--[\w-]+\s*:", body_line_stripped):
                continue
            if "var(--" in body_line_stripped:
                # This line already uses a token — Check 1 already handles the
                # fallback case; here we skip (token binding is present)
                continue

            # body starts immediately after the `{` on the selector line.
            # body.splitlines()[0] is still on selector line (line_num),
            # body.splitlines()[1] is line_num+1, etc.
            body_line_num = line_num + body_line_offset

            # Check hex color in the body
            for m in _HEX_RE.finditer(body_line_stripped):
                hex_val = m.group(1)
                if len(hex_val) not in (3, 4, 6, 8):
                    continue
                findings.append(Finding(
                    rule=rule,
                    path=rel_path,
                    line=body_line_num,
                    kind="VIOLATION",
                    summary=(
                        "MATCH element [data-ref={ref}] uses hardcoded color "
                        "{val!r} — must bind to a token".format(
                            ref=matched_ref, val=m.group(0)
                        )
                    ),
                    fix_hint=(
                        "Replace {val!r} with var(--color-token) in the "
                        "[data-ref={ref}] rule".format(
                            val=m.group(0), ref=matched_ref
                        )
                    ),
                ))

            # Check functional color in the body
            for m in _FUNC_COLOR_RE.finditer(body_line_stripped):
                findings.append(Finding(
                    rule=rule,
                    path=rel_path,
                    line=body_line_num,
                    kind="VIOLATION",
                    summary=(
                        "MATCH element [data-ref={ref}] uses hardcoded "
                        "{fn}() color — must bind to a token".format(
                            ref=matched_ref, fn=m.group(1)
                        )
                    ),
                    fix_hint=(
                        "Replace {fn}() with var(--color-token) in the "
                        "[data-ref={ref}] rule".format(
                            fn=m.group(1), ref=matched_ref
                        )
                    ),
                ))

            # Check spacing literals (only when spacing_scale_available)
            if spacing_scale_available:
                # Match px/rem/em values in property positions that are
                # spacing-related (margin/padding/gap)
                spacing_prop_match = re.match(
                    r"(margin|padding|gap|inset|top|right|bottom|left)"
                    r"[\w-]*\s*:\s*(.+)",
                    body_line_stripped,
                    re.IGNORECASE,
                )
                if spacing_prop_match:
                    val_text = spacing_prop_match.group(2)
                    # Check for numeric px/rem/em values (not tokens)
                    if re.search(r"\d+(?:px|rem|em)\b", val_text):
                        findings.append(Finding(
                            rule=rule,
                            path=rel_path,
                            line=body_line_num,
                            kind="VIOLATION",
                            summary=(
                                "MATCH element [data-ref={ref}] uses hardcoded "
                                "spacing value — must bind to a spacing token".format(
                                    ref=matched_ref
                                )
                            ),
                            fix_hint=(
                                "Replace the spacing literal with "
                                "var(--spacing-token) in the "
                                "[data-ref={ref}] rule".format(ref=matched_ref)
                            ),
                        ))

    return findings


# ---------------------------------------------------------------------------
# Main public scanner
# ---------------------------------------------------------------------------

def scan_for_design_token_violations(
    root,                      # type: Path
    allowlist_globs,           # type: List[str]
    defined_tokens=None,       # type: Optional[Set[str]]
    match_refs=None,           # type: Optional[Set[str]]
    spacing_scale_available=False,  # type: bool
    file_paths=None,           # type: Optional[List[Path]]
):
    # type: (...) -> List[Finding]
    """Walk root (or the given file_paths) for style sources and scan for violations.

    Parameters
    ----------
    root:
        Consumer project root.  Finding.path values are relative to this.
    allowlist_globs:
        Glob patterns for file/dir exclusions.
    defined_tokens:
        Set of CSS custom property names (e.g. {\"--color-primary\", ...})
        defined in reachable token sources.  When empty/None, Check 3 is
        skipped entirely (OQ-6: absent token source → skip undefined-token
        check).
    match_refs:
        Set of data-ref anchor strings for MATCH elements from the
        disposition manifest.  When empty/None, Check 5 is skipped.
    spacing_scale_available:
        True when a spacing scale was extracted from design/styles.css
        (OQ-6: when False, spacing token-binding sub-check is relaxed).
    file_paths:
        If provided, scan only these files instead of walking root.
        Used for targeted scanning from --files argument.

    Returns
    -------
    List of Finding objects (relative paths, 1-based line numbers).
    """
    findings = []  # type: List[Finding]
    root_resolved = root.resolve()
    rule = "design_token_provenance"

    _defined = defined_tokens or set()  # type: Set[str]
    _match_refs = match_refs or set()  # type: Set[str]

    if file_paths is not None:
        # Targeted scan mode — only scan the given files
        candidates = []
        for fp in file_paths:
            fp_path = Path(fp)
            if fp_path.suffix not in _ELIGIBLE_EXTENSIONS:
                continue
            candidates.append(fp_path)
    else:
        # Walk mode — scan everything under root
        candidates = []
        for dirpath, _dirs, files in os.walk(str(root_resolved)):
            for fname in files:
                fpath = Path(dirpath) / fname
                if fpath.suffix not in _ELIGIBLE_EXTENSIONS:
                    continue
                candidates.append(fpath)

    for fpath in candidates:
        try:
            abs_path = fpath.resolve()
        except OSError:
            abs_path = fpath.absolute()

        try:
            rel_path_obj = abs_path.relative_to(root_resolved)
        except ValueError:
            # File outside root — use the given path string as-is
            rel_path_obj = fpath

        rel_str = str(rel_path_obj)

        # Allowlist check
        if path_in_allowlist(Path(rel_str), allowlist_globs):
            continue

        try:
            source = abs_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        # Run checks
        findings.extend(_check1_color_literals(source, rel_str, rule))
        findings.extend(_check2_var_fallbacks(source, rel_str, rule))
        findings.extend(_check3_undefined_tokens(source, rel_str, rule, _defined))

        # Check 4 and 5 are most meaningful for CSS/SCSS/LESS files
        if fpath.suffix in _STYLE_EXTENSIONS:
            findings.extend(_check4_interactive_states(source, rel_str, rule))
            findings.extend(
                _check5_match_token_binding(
                    source, rel_str, rule, _match_refs, spacing_scale_available
                )
            )

    return findings
