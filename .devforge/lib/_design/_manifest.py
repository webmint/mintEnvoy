"""_manifest.py — init-manifest, validate-manifest, and spacing-scale verbs.

init-manifest
-------------
Given the output of resolve-reference (element list + gap_list), produces a
skeleton ManifestContainer JSON with every element set to disposition="" (unclassified).
The caller (the orchestrator / human) fills in the dispositions.

validate-manifest
-----------------
Reads a manifest JSON file and validates it (plan 40 D4):
  - every element must have a disposition (unclassified → fail, naming the element)
  - gap_list must be empty (non-empty → fail, naming each token)
  Exit 0 = valid; exit 1 = validation errors (messages on stderr + stdout JSON).

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
from typing import Dict, List, Optional, Set

from ._schema import (
    ManifestContainer,
    ElementRecord,
    manifest_from_json,
    manifest_to_dict,
    manifest_to_json,
    validate_manifest,
    DISPOSITION_UNCLASSIFIED,
)


# ---------------------------------------------------------------------------
# init-manifest
# ---------------------------------------------------------------------------

def init_manifest_from_reference(reference_result, reference_html_path=""):
    # type: (dict, str) -> ManifestContainer
    """Create a skeleton ManifestContainer from a resolve-reference result.

    Every element gets disposition="" (unclassified) so the user can fill in
    the dispositions before running validate-manifest.

    Parameters
    ----------
    reference_result : dict
        Output of resolve_reference() — must contain "elements" and "gap_list".
    reference_html_path : str
        Path stored in the manifest.  Defaults to reference_result["reference_html"].

    Returns
    -------
    ManifestContainer with unclassified elements and the gap_list copied in.
    """
    html_path = reference_html_path or reference_result.get("reference_html", "")
    elements = []  # type: List[ElementRecord]
    for elem in reference_result.get("elements", []):
        elements.append(
            ElementRecord(
                data_ref=elem.get("data_ref", ""),
                disposition=DISPOSITION_UNCLASSIFIED,
                deviate_reason="",
            )
        )
    gap_list = list(reference_result.get("gap_list", []))
    return ManifestContainer(
        reference_html=html_path,
        elements=elements,
        gap_list=gap_list,
    )


def cmd_init_manifest(args):
    # type: (object) -> int
    """CLI handler for the init-manifest verb.

    Reads the JSON output of resolve-reference from --reference-json,
    produces a skeleton manifest JSON to stdout (all elements unclassified).

    Exit codes:
      0 — success (JSON to stdout)
      2 — argument error or file not found
    """
    ref_json_path = getattr(args, "reference_json", None)
    if not ref_json_path:
        sys.stderr.write("design_helper init-manifest: --reference-json is required\n")
        return 2

    if not os.path.isfile(ref_json_path):
        sys.stderr.write(
            "design_helper init-manifest: file not found: {0}\n".format(ref_json_path)
        )
        return 2

    try:
        with open(ref_json_path, "r", encoding="utf-8") as fh:
            reference_result = json.loads(fh.read())
    except (OSError, ValueError) as exc:
        sys.stderr.write(
            "design_helper init-manifest: cannot read {0}: {1}\n".format(
                ref_json_path, exc
            )
        )
        return 2

    container = init_manifest_from_reference(reference_result)
    sys.stdout.write(manifest_to_json(container) + "\n")
    return 0


# ---------------------------------------------------------------------------
# validate-manifest
# ---------------------------------------------------------------------------

def cmd_validate_manifest(args):
    # type: (object) -> int
    """CLI handler for validate-manifest.

    Reads a manifest JSON from --manifest-path and validates it.

    Emits JSON to stdout:
      {"valid": bool, "errors": [str]}

    Exit codes:
      0 — manifest is valid (all elements classified, empty gap-list)
      1 — validation errors (errors listed on stderr + in stdout JSON)
      2 — argument error or file not found
    """
    manifest_path = getattr(args, "manifest_path", None)
    if not manifest_path:
        sys.stderr.write("design_helper validate-manifest: --manifest-path is required\n")
        return 2

    if not os.path.isfile(manifest_path):
        sys.stderr.write(
            "design_helper validate-manifest: file not found: {0}\n".format(manifest_path)
        )
        return 2

    try:
        with open(manifest_path, "r", encoding="utf-8") as fh:
            container = manifest_from_json(fh.read())
    except (OSError, ValueError) as exc:
        sys.stderr.write(
            "design_helper validate-manifest: cannot parse {0}: {1}\n".format(
                manifest_path, exc
            )
        )
        return 2

    errors = validate_manifest(container)
    result = {"valid": len(errors) == 0, "errors": errors}
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")

    if errors:
        for err in errors:
            sys.stderr.write("design_helper validate-manifest: {0}\n".format(err))
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
    blocks are collected correctly (F2 fix propagated from _reference.py).
    """
    from ._reference import _extract_rule_blocks, _CSS_DECL_RE  # local import avoids cycles

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
