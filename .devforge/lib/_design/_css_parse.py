"""_css_parse.py — shared, generic CSS-parsing utilities for design_helper.

Relocated out of the retired _reference.py (plan 53 Phase 3): the data-ref
HTML-anchor extraction (_DataRefCollector, resolve_reference,
cmd_resolve_reference) is retired along with the disposition-manifest schema
it fed, but these CSS-parsing utilities are generic (they operate on raw CSS
text, not on the retired data-ref/element concept) and are still imported by
_manifest.py::extract_spacing_scale.

Design notes
------------
- stdlib only (re); Python 3.8+
- CSS parsing is intentionally minimal: extracts property: value declarations
  from rule blocks (depth-aware, recursing into @media/@supports/@container/
  @layer wrapper blocks), not a full cascade resolver.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

# Matches a single CSS declaration:  property: value
_CSS_DECL_RE = re.compile(r"([\w-]+)\s*:\s*([^;]+?)(?:\s*;|$)", re.DOTALL)

# Matches a custom-property definition:  --name: value (as a declaration)
_CSS_CUSTOM_PROP_RE = re.compile(r"(--[\w-]+)\s*:\s*([^;]+?)(?:\s*;|$)", re.DOTALL)

# Detects whether a selector-like prefix looks like an at-rule block
# (e.g. @media, @supports, @container, @layer) — these wrap rule blocks
# inside their body and must be recursed into rather than treated as a selector.
_AT_RULE_BLOCK_RE = re.compile(r"^\s*@(?:media|supports|container|layer|document)\b")


def _extract_rule_blocks(css_text):
    # type: (str) -> List[Tuple[str, str]]
    """Depth-aware extraction of CSS rule blocks from css_text.

    Returns a list of (selector, declarations_body) pairs for every
    depth-1 `selector { ... }` block, recursing into at-rule wrapper blocks
    (@media, @supports, @container, @layer) so that rules defined only inside
    such blocks are collected correctly.
    """
    results = []  # type: List[Tuple[str, str]]
    i = 0
    n = len(css_text)

    while i < n:
        # Find the next '{'
        brace_open = css_text.find("{", i)
        if brace_open == -1:
            break

        selector_raw = css_text[i:brace_open]
        # Strip comments from the selector fragment
        selector = re.sub(r"/\*.*?\*/", "", selector_raw, flags=re.DOTALL).strip()

        # Walk forward from the '{' tracking depth to find the matching '}'
        depth = 0
        j = brace_open
        while j < n:
            if css_text[j] == "{":
                depth += 1
            elif css_text[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1

        body = css_text[brace_open + 1:j]
        i = j + 1  # advance past the closing '}'

        if not selector:
            continue

        if _AT_RULE_BLOCK_RE.match(selector):
            # This is an at-rule wrapper (e.g. @media screen { .foo { ... } }).
            # Recurse into its body to collect the inner rule blocks.
            results.extend(_extract_rule_blocks(body))
        else:
            # Regular rule block: yield (selector, declarations_body)
            results.append((selector, body))

    return results


def _parse_css_rules(css_text):
    # type: (str) -> Tuple[Dict[str, Dict[str, str]], Dict[str, str]]
    """Parse CSS text into (rules_dict, custom_properties).

    rules_dict maps selector → {property: value, ...} for non-custom properties.
    custom_properties maps --token-name → value.

    Uses _extract_rule_blocks for depth-aware parsing so classes defined
    inside @media/@supports/@container blocks are collected correctly.

    Only captures the last definition when a property appears multiple times.
    """
    rules = {}           # type: Dict[str, Dict[str, str]]
    custom_props = {}    # type: Dict[str, str]

    for selector, declarations_raw in _extract_rule_blocks(css_text):
        if not selector:
            continue

        decl_dict = {}  # type: Dict[str, str]

        # Extract custom property definitions first
        for cp_match in _CSS_CUSTOM_PROP_RE.finditer(declarations_raw):
            prop = cp_match.group(1).strip()
            val = cp_match.group(2).strip()
            custom_props[prop] = val

        # Extract regular declarations (skip custom-property lines)
        for decl_match in _CSS_DECL_RE.finditer(declarations_raw):
            prop = decl_match.group(1).strip()
            val = decl_match.group(2).strip()
            if prop.startswith("--"):
                continue  # handled above
            decl_dict[prop] = val

        if decl_dict:
            if selector in rules:
                rules[selector].update(decl_dict)
            else:
                rules[selector] = decl_dict

    return rules, custom_props
