"""_reference.py — resolve-reference verb for design_helper.

Parses a reference.html and returns:
  - the list of elements carrying data-ref anchors
  - the declared visual values (inline styles + <style> block + linked stylesheet
    when resolvable on disk)
  - a gap-list of unresolvable classes/tokens (a class with no definition on disk,
    an undefined CSS custom property (no `--token: value` definition found in the
    collected CSS corpus))

The gap-list drives the D4 "escalate ASAP / never guess" rule: a non-empty
gap-list HALTS intake (validate-manifest returns non-zero naming each token).

Design decisions
----------------
- stdlib only (html.parser + re); Python 3.8+
- CSS parsing is intentionally minimal: we extract property: value declarations
  from rule blocks, not a full cascade resolver.  The goal is "can we resolve
  this class/token?" not "what is the final computed value?".
- Inline styles on a data-ref element are captured verbatim.
- <style> blocks are parsed for class/id/element rules; their property sets are
  collected.
- A linked <link rel="stylesheet" href="..."> pointing to a file RESOLVABLE on
  disk relative to the HTML file is also parsed.
- Custom properties (--token-name) found in values are checked for a definition
  in the same CSS corpus.  Undefined tokens → gap-list.
- Classes referenced on data-ref elements that appear in no collected rule →
  gap-list.

JSON emitted to stdout by the CLI verb:
  {
    "reference_html": str,
    "elements": [
      {
        "data_ref":     str,   # value of the data-ref attribute
        "tag":          str,   # lowercase HTML tag name
        "id":           str,   # id attribute or ""
        "classes":      list[str],  # class tokens
        "inline_style": str,   # verbatim style="" value or ""
      },
      ...
    ],
    "resolved_values": {
      "<selector>": {"<property>": "<value>", ...},
      ...
    },
    "custom_properties": {
      "<--token>": "<value>",  # all --* definitions found in CSS
      ...
    },
    "gap_list": [str, ...]     # unresolvable classes / undefined tokens
  }

Exit codes:
  0 — success
  2 — reference.html not found or not readable
"""

from __future__ import annotations

import os
import re
import sys
from html.parser import HTMLParser
from typing import Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# HTML parser — collects data-ref elements + linked stylesheets
# ---------------------------------------------------------------------------


class _DataRefCollector(HTMLParser):
    """Walk the HTML tree and collect:
    - self.elements: each tag that has a data-ref attribute
    - self.stylesheets: href values from <link rel="stylesheet"> tags
    - self.inline_style_blocks: text from <style> tags
    """

    def __init__(self):
        # type: () -> None
        super(_DataRefCollector, self).__init__()
        self.elements = []           # type: List[dict]
        self.stylesheets = []        # type: List[str]
        self.inline_style_blocks = []  # type: List[str]
        self._in_style = False
        self._style_buf = []         # type: List[str]

    def handle_starttag(self, tag, attrs):
        # type: (str, List[Tuple[str, Optional[str]]]) -> None
        attr_dict = {}
        for name, value in attrs:
            attr_dict[name.lower()] = value or ""

        # Collect <link rel="stylesheet" href="...">
        if tag.lower() == "link":
            if attr_dict.get("rel", "").lower() == "stylesheet":
                href = attr_dict.get("href", "")
                if href:
                    self.stylesheets.append(href)

        # Collect <style> open
        if tag.lower() == "style":
            self._in_style = True
            self._style_buf = []

        # Collect elements with data-ref
        data_ref = attr_dict.get("data-ref", "")
        if data_ref:
            classes_raw = attr_dict.get("class", "")
            classes = [c for c in classes_raw.split() if c]
            self.elements.append(
                {
                    "data_ref": data_ref,
                    "tag": tag.lower(),
                    "id": attr_dict.get("id", ""),
                    "classes": classes,
                    "inline_style": attr_dict.get("style", ""),
                }
            )

    def handle_endtag(self, tag):
        # type: (str) -> None
        if tag.lower() == "style" and self._in_style:
            self._in_style = False
            self.inline_style_blocks.append("".join(self._style_buf))

    def handle_data(self, data):
        # type: (str) -> None
        if self._in_style:
            self._style_buf.append(data)


# ---------------------------------------------------------------------------
# Minimal CSS parser
# ---------------------------------------------------------------------------

# Matches a single CSS declaration:  property: value
_CSS_DECL_RE = re.compile(r"([\w-]+)\s*:\s*([^;]+?)(?:\s*;|$)", re.DOTALL)

# Matches a CSS custom-property reference in a value: var(--name) or var(--name, fallback)
_CSS_VAR_RE = re.compile(r"var\(\s*(--[\w-]+)")

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

    This replaces the old `_CSS_RULE_RE = r"([^{]+)\\{([^}]*)\\}"` regex,
    which could not handle nested braces and would mis-parse any class defined
    only inside an @media or @supports block (F2).
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
    inside @media/@supports/@container blocks are collected correctly (F2).

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


def _collect_referenced_classes(rules):
    # type: (Dict[str, Dict[str, str]]) -> Set[str]
    """Return the set of CSS class names referenced in rule selectors."""
    referenced = set()  # type: Set[str]
    class_token_re = re.compile(r"\.([a-zA-Z_-][\w-]*)")
    for selector in rules:
        for m in class_token_re.finditer(selector):
            referenced.add(m.group(1))
    return referenced


# ---------------------------------------------------------------------------
# Gap-list computation
# ---------------------------------------------------------------------------


def _selectors_for_element(elem, all_rules):
    # type: (dict, Dict[str, Dict[str, str]]) -> List[str]
    """Return the selectors from all_rules that match a data-ref element.

    A selector matches if it references at least one of the element's class
    tokens or its id.  This is used to narrow the var() scan (F1) so that
    undefined tokens in utility/helper rules that are NOT applied to any
    data-ref element never create false gap entries.
    """
    class_token_re = re.compile(r"\.([a-zA-Z_-][\w-]*)")
    id_token_re = re.compile(r"#([a-zA-Z_-][\w-]*)")

    elem_classes = set(elem.get("classes", []))
    elem_id = elem.get("id", "")

    matched = []  # type: List[str]
    for selector in all_rules:
        # Check id reference
        if elem_id:
            for m in id_token_re.finditer(selector):
                if m.group(1) == elem_id:
                    matched.append(selector)
                    break
            else:
                # Check class references
                for m in class_token_re.finditer(selector):
                    if m.group(1) in elem_classes:
                        matched.append(selector)
                        break
        else:
            # No id: check class references only
            for m in class_token_re.finditer(selector):
                if m.group(1) in elem_classes:
                    matched.append(selector)
                    break

    return matched


def _compute_gap_list(
    elements,       # type: List[dict]
    all_rules,      # type: Dict[str, Dict[str, str]]
    custom_props,   # type: Dict[str, str]
):
    # type: (...) -> List[str]
    """Compute the gap-list of unresolvable classes and undefined CSS tokens.

    For each data-ref element:
    1. Collect its class tokens.
    2. For each class token, check whether any rule selector references it.
       If no rule covers it → add "<class> (no CSS definition found)" to gap-list.
    3. Collect var(--token) references found in inline_style.
       Any --token not in custom_props → add "--token (undefined)" to gap-list.
    4. Collect var(--token) references found in the declarations of rules that
       APPLY to this data-ref element (i.e. whose selectors reference the
       element's classes or id).  Rules that do NOT apply to any data-ref
       element are excluded to avoid false gap entries from utility/helper
       classes (F1).

    Returns a deduplicated, sorted list of unresolvable identifiers.
    """
    gap_set = set()  # type: Set[str]
    css_classes = _collect_referenced_classes(all_rules)

    for elem in elements:
        # Step 1+2: Check class tokens against collected rule selectors.
        for cls in elem.get("classes", []):
            if cls not in css_classes:
                gap_set.add("{0} (no CSS definition found)".format(cls))

        # Step 3: Check var() references in inline_style.
        inline = elem.get("inline_style", "")
        for m in _CSS_VAR_RE.finditer(inline):
            token = m.group(1)
            if token not in custom_props:
                gap_set.add("{0} (undefined CSS custom property)".format(token))

        # Step 4: Check var() references in rules that apply to this element.
        # Narrowed to matching selectors only (F1) — avoids false positives from
        # utility/helper rules that are present in the CSS but not used by any
        # data-ref element in this reference.html.
        for selector in _selectors_for_element(elem, all_rules):
            for val in all_rules[selector].values():
                for m in _CSS_VAR_RE.finditer(val):
                    token = m.group(1)
                    if token not in custom_props:
                        gap_set.add("{0} (undefined CSS custom property)".format(token))

    return sorted(gap_set)


# ---------------------------------------------------------------------------
# Public API: resolve_reference
# ---------------------------------------------------------------------------


def resolve_reference(html_path, base_dir=None):
    # type: (str, Optional[str]) -> dict
    """Parse reference.html and return the analysis dict.

    Parameters
    ----------
    html_path : str
        Path to the reference.html file.
    base_dir : str or None
        Directory used to resolve linked stylesheets.  Defaults to
        os.path.dirname(html_path).

    Returns
    -------
    dict with keys:
      reference_html, elements, resolved_values, custom_properties, gap_list

    Raises
    ------
    OSError if the file cannot be read.
    """
    if base_dir is None:
        base_dir = os.path.dirname(os.path.abspath(html_path))

    with open(html_path, "r", encoding="utf-8", errors="replace") as fh:
        html_text = fh.read()

    collector = _DataRefCollector()
    collector.feed(html_text)
    collector.close()

    # Accumulate CSS text from all sources
    css_corpus_parts = []  # type: List[str]
    for block in collector.inline_style_blocks:
        css_corpus_parts.append(block)

    linked_resolved = []  # type: List[str]
    linked_unresolvable = []  # type: List[str]
    for href in collector.stylesheets:
        if href.startswith("http://") or href.startswith("https://") or href.startswith("//"):
            # Remote stylesheet — cannot resolve on disk
            linked_unresolvable.append(href)
            continue
        candidate = os.path.join(base_dir, href)
        if os.path.isfile(candidate):
            try:
                with open(candidate, "r", encoding="utf-8", errors="replace") as fh:
                    css_corpus_parts.append(fh.read())
                linked_resolved.append(href)
            except OSError:
                linked_unresolvable.append(href)
        else:
            linked_unresolvable.append(href)

    full_css = "\n".join(css_corpus_parts)
    all_rules, custom_props = _parse_css_rules(full_css)

    gap_list = _compute_gap_list(collector.elements, all_rules, custom_props)

    return {
        "reference_html": html_path,
        "elements": collector.elements,
        "resolved_values": all_rules,
        "custom_properties": custom_props,
        "gap_list": gap_list,
    }


# ---------------------------------------------------------------------------
# CLI handler
# ---------------------------------------------------------------------------


def cmd_resolve_reference(args):
    # type: (object) -> int
    """CLI handler for the resolve-reference verb."""
    import json
    import argparse

    html_path = getattr(args, "html_path", None)
    if not html_path:
        sys.stderr.write(
            "design_helper resolve-reference: --html-path is required\n"
        )
        return 2

    if not os.path.isfile(html_path):
        sys.stderr.write(
            "design_helper resolve-reference: reference.html not found: {0}\n".format(
                html_path
            )
        )
        return 2

    try:
        result = resolve_reference(html_path)
    except OSError as exc:
        sys.stderr.write(
            "design_helper resolve-reference: cannot read {0}: {1}\n".format(
                html_path, exc
            )
        )
        return 2

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0
