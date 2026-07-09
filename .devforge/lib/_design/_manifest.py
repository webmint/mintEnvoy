"""_manifest.py — validate-binding and extract-spacing-scale verbs.

validate-binding
-----------------
Reads a binding JSON file (specs/[feature]/design-manifest.json — same
on-disk filename as plan 40's retired disposition manifest, plan 53 D4) and
validates it:
  - route must be non-empty
  - pairs must contain at least one entry (the container floor)
  - every pair must have both anchor_selector and built_testid
  Exit 0 = valid; exit 1 = validation errors (messages on stderr + stdout JSON).

RETIRED (plan 53 Phase 3): init-manifest (the resolve-reference-derived
skeleton generator) has no mechanical replacement now that data-ref HTML
extraction is retired — a binding's route + pairs are always human/LLM
authored (there is no walkable element list to seed a skeleton from), so no
init-binding verb is introduced.  The binding is authored directly wherever
`/breakdown` PHASE 2.5 writes `design-manifest.json`.

extract-spacing-scale
---------------------
Parses design/styles.css (OQ-6): collects the distinct declared values for
margin / padding / gap / inset properties and returns them as a named scale.
When styles.css is ABSENT, returns {"available": false, "scale": []}.
When present, returns {"available": true, "scale": [<values>]}.

The absent-CSS relaxation is intentional per OQ-6: when no styles.css is
present the spacing PROVENANCE check relaxes (there is no token to bind to).
This function surfaces the "no scale available" fact; it does NOT enforce.

stdlib only; Python 3.8+.
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import List, Set

from ._schema import (
    binding_from_json,
    validate_binding,
)


# ---------------------------------------------------------------------------
# validate-binding
# ---------------------------------------------------------------------------

def cmd_validate_binding(args):
    # type: (object) -> int
    """CLI handler for validate-binding.

    Reads a binding JSON from --binding-path and validates it.

    Emits JSON to stdout:
      {"valid": bool, "errors": [str]}

    Exit codes:
      0 — binding is valid (non-empty route, >=1 fully-specified pair)
      1 — validation errors (errors listed on stderr + in stdout JSON)
      2 — argument error or file not found
    """
    binding_path = getattr(args, "binding_path", None)
    if not binding_path:
        sys.stderr.write("design_helper validate-binding: --binding-path is required\n")
        return 2

    if not os.path.isfile(binding_path):
        sys.stderr.write(
            "design_helper validate-binding: file not found: {0}\n".format(binding_path)
        )
        return 2

    try:
        with open(binding_path, "r", encoding="utf-8") as fh:
            binding = binding_from_json(fh.read())
    except (OSError, ValueError) as exc:
        sys.stderr.write(
            "design_helper validate-binding: cannot parse {0}: {1}\n".format(
                binding_path, exc
            )
        )
        return 2

    errors = validate_binding(binding)
    result = {"valid": len(errors) == 0, "errors": errors}
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")

    if errors:
        for err in errors:
            sys.stderr.write("design_helper validate-binding: {0}\n".format(err))
        return 1

    return 0


# ---------------------------------------------------------------------------
# Spacing-scale extraction
# ---------------------------------------------------------------------------

# Properties whose values we treat as spacing values.
_SPACING_PROPERTIES = frozenset(
    [
        "margin", "margin-top", "margin-right", "margin-bottom", "margin-left",
        "padding", "padding-top", "padding-right", "padding-bottom", "padding-left",
        "gap", "row-gap", "column-gap",
        "inset", "inset-block", "inset-inline",
        "inset-block-start", "inset-block-end",
        "inset-inline-start", "inset-inline-end",
        "top", "right", "bottom", "left",
    ]
)

# Pattern that picks a spacing value: px / rem / em / vh / vw / % / fr / 0
_SPACING_VALUE_TOKEN_RE = re.compile(
    r"(?:^|[ ,])(\d*\.?\d+(?:px|rem|em|vh|vw|%|fr)|0)(?=[ ,;]|$)"
)


def _parse_spacing_from_css(css_text):
    # type: (str) -> List[str]
    """Extract distinct spacing values from CSS text.

    Returns a sorted list of unique value tokens (e.g. "4px", "1rem", "0").
    Uses _extract_rule_blocks (depth-aware) so spacing values inside @media
    blocks are collected correctly (F2 fix propagated from the retired
    _reference.py, now living in _css_parse.py).
    """
    from ._css_parse import _extract_rule_blocks, _CSS_DECL_RE  # local import avoids cycles

    values = set()  # type: Set[str]

    for _selector, declarations_raw in _extract_rule_blocks(css_text):
        for decl_match in _CSS_DECL_RE.finditer(declarations_raw):
            prop = decl_match.group(1).strip().lower()
            if prop.startswith("--"):
                continue
            if prop not in _SPACING_PROPERTIES:
                continue
            val = decl_match.group(2).strip()
            # Extract individual length tokens from shorthand values
            for tok_match in _SPACING_VALUE_TOKEN_RE.finditer(" " + val + " "):
                values.add(tok_match.group(1))

    return sorted(values, key=_sort_key_for_spacing)


def _sort_key_for_spacing(val):
    # type: (str) -> tuple
    """Sort spacing values numerically.  "0" < "4px" < "1rem" (by number then unit)."""
    m = re.match(r"^(\d*\.?\d+)(.*)", val)
    if m:
        return (float(m.group(1)), m.group(2))
    return (0.0, val)


def extract_spacing_scale(css_path):
    # type: (str) -> dict
    """Extract the spacing scale from a CSS file.

    Returns:
      {"available": True,  "scale": [str, ...], "source": css_path}
        when css_path exists and is readable.
      {"available": False, "scale": [], "source": None}
        when css_path does not exist (OQ-6 relaxation — absent CSS ≠ error).

    Raises OSError if the file exists but cannot be read.
    """
    if not os.path.isfile(css_path):
        return {"available": False, "scale": [], "source": None}

    with open(css_path, "r", encoding="utf-8", errors="replace") as fh:
        css_text = fh.read()

    scale = _parse_spacing_from_css(css_text)
    return {"available": True, "scale": scale, "source": css_path}


def cmd_extract_spacing_scale(args):
    # type: (object) -> int
    """CLI handler for extract-spacing-scale verb.

    Reads --css-path (design/styles.css).  When absent, emits the relaxed
    {"available": false} result and exits 0.

    Exit codes:
      0 — success (JSON to stdout, available true or false)
      2 — argument error or file read error
    """
    css_path = getattr(args, "css_path", None)
    if not css_path:
        sys.stderr.write(
            "design_helper extract-spacing-scale: --css-path is required\n"
        )
        return 2

    try:
        result = extract_spacing_scale(css_path)
    except OSError as exc:
        sys.stderr.write(
            "design_helper extract-spacing-scale: cannot read {0}: {1}\n".format(
                css_path, exc
            )
        )
        return 2

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0
