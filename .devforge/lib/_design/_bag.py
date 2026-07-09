"""_bag.py -- Bag: the normalized measurement record shared by the html
intent-reader and the web built-reader JS collectors (plan 53 Phase 4).

Design (OQ-A resolution): the repo has no JS test infra and jsdom has no
layout engine (`scrollWidth`/`clientWidth`/`getBoundingClientRect` return 0
there) and no font loading, so a JS unit test cannot exercise geometry or
font-load logic. Resolution: ALL DECISION LOGIC lives in Python; the `.js`
`evaluate_script` assets (`js/built_reader.js`, `js/intent_reader.js`) are
THIN MEASUREMENT COLLECTORS that make no predicates -- they only measure and
return this normalized JSON "bag". Python (`_floor.py` + `_fidelity.py` +
`_comparator.py`) applies every predicate to the bag, fully unit-testable
against synthetic fixtures. The JS collectors themselves are verified at
Phase 9 e2e (real Chrome MCP), not unit-tested here.

Bag JSON contract (BOTH built_reader.js and intent_reader.js emit exactly
this shape -- the built/intent asymmetry is two legitimate empty defaults,
not a shape divergence: intent_reader.js always emits empty
overflow_candidates/clip_candidates (the anchor-free floor runs on the BUILT
side only, plan 53 D9) and an empty fonts dict (no font-LOAD check on the
intent side, plan 53 Phase 4 deliverable #2)):

{
  "region_found": bool,          -- REQUIRED. The container testid/selector
                                     resolves and is mounted. false is valid
                                     data (NOT-COVERED), not malformed.
  "elements": {                  -- REQUIRED (may be an empty object).
    "<key>": {                   -- key = built_testid (built bag) or
                                     anchor CSS selector (intent bag).
      "found": bool,             -- REQUIRED. false when this key's element
                                     did not resolve -- style/geometry/
                                     overflow_x/position are then OMITTED
                                     (nothing to measure).
      "style": {                 -- REQUIRED when found=true.
        "color": str, "background": str, "border": str,
        "border_radius": str, "padding": str, "margin": str, "gap": str,
        "font_family": str, "font_size": str, "line_height": str,
        "font_weight": str
      },
      "geometry": {               -- REQUIRED when found=true.
        "x": number, "y": number, "width": number, "height": number,
        "scroll_width": number, "client_width": number
      },
      "overflow_x": str,          -- REQUIRED when found=true.
      "position": str             -- REQUIRED when found=true.
    }, ...
  },
  "overflow_candidates": [        -- OPTIONAL (default []). BUILT-side only;
    {                                the anchor-free overflow floor (plan 53
      "label": str,                  D9) scans the built region's subtree.
      "scroll_width": number,
      "client_width": number,
      "overflow_x": str
    }, ...
  ],
  "clip_candidates": [             -- OPTIONAL (default []). BUILT-side only;
    {                                 the anchor-free clip floor (plan 53 D9).
      "label": str,
      "child_rect": {"x": number, "y": number, "width": number, "height": number},
      "parent_rect": {"x": number, "y": number, "width": number, "height": number},
      "parent_overflow": str,
      "child_position": str
    }, ...
  ],
  "fonts": {                       -- OPTIONAL (default {}). BUILT-side only;
    "<family-token>": bool           document.fonts.check() per declared
  }                                   family (plan 53 D10).
}

Public API
----------
Bag                 -- the parsed record (see class docstring for field list).
BagParseError        -- ValueError subclass; raised on malformed/missing-field
                        JSON. NEVER raised for a legitimately empty/negative
                        bag (e.g. region_found=false, or an element with
                        found=false) -- those are valid DATA, not errors
                        (plan 53 honesty invariant #4: NOT-COVERED is a
                        distinct, loud outcome from a silent pass, but it is
                        also distinct from a parse failure).
parse_bag(data)      -- validate an already-json.loads'd dict -> Bag.
load_bag(json_text)  -- json.loads + parse_bag in one call; JSON-decode
                        failure also raises BagParseError (loud, not silent).

Design notes
------------
- stdlib only; Python 3.8+
- No third-party deps
- helper-owns-shape: every required field is checked by name and type;
  the malformed-input path is a loud, descriptive BagParseError, never a
  silently-coerced default (audit anti-pattern discipline).
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class BagParseError(ValueError):
    """Raised when a probe's JSON output is malformed (missing/mistyped
    required field), or the payload is not valid JSON at all.

    A ValueError subclass so ordinary ``except (OSError, ValueError)`` catch
    sites keep working unmodified; callers that need to distinguish "this
    bag is malformed" from a generic error can catch this narrower type
    first.
    """


def _err(msg):
    # type: (str) -> None
    raise BagParseError("bag: {0}".format(msg))


# ---------------------------------------------------------------------------
# Field contracts
# ---------------------------------------------------------------------------

_REQUIRED_GEOMETRY_KEYS = ("x", "y", "width", "height", "scroll_width", "client_width")
_REQUIRED_STYLE_KEYS = (
    "color",
    "background",
    "border",
    "border_radius",
    "padding",
    "margin",
    "gap",
    "font_family",
    "font_size",
    "line_height",
    "font_weight",
)


def _is_number(value):
    # type: (object) -> bool
    """True for int/float, explicitly excluding bool (bool is an int subclass)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _require_number(value, label):
    # type: (object, str) -> None
    if not _is_number(value):
        _err("{0} must be a number, got {1}".format(label, type(value).__name__))


def _require_str(value, label):
    # type: (object, str) -> None
    if not isinstance(value, str):
        _err("{0} must be a string, got {1}".format(label, type(value).__name__))


def _validate_rect(rect, label):
    # type: (object, str) -> None
    if not isinstance(rect, dict):
        _err("{0} must be an object".format(label))
    for key in ("x", "y", "width", "height"):
        if key not in rect:
            _err("{0} missing '{1}'".format(label, key))
        _require_number(rect[key], "{0}.{1}".format(label, key))


def _validate_geometry(geo, label):
    # type: (object, str) -> None
    if not isinstance(geo, dict):
        _err("{0}.geometry must be an object".format(label))
    for key in _REQUIRED_GEOMETRY_KEYS:
        if key not in geo:
            _err("{0}.geometry missing '{1}'".format(label, key))
        _require_number(geo[key], "{0}.geometry.{1}".format(label, key))


def _validate_style(style, label):
    # type: (object, str) -> None
    if not isinstance(style, dict):
        _err("{0}.style must be an object".format(label))
    for key in _REQUIRED_STYLE_KEYS:
        if key not in style:
            _err("{0}.style missing '{1}'".format(label, key))
        _require_str(style[key], "{0}.style.{1}".format(label, key))


def _validate_element(el, key):
    # type: (object, str) -> None
    label = "elements[{0!r}]".format(key)
    if not isinstance(el, dict):
        _err("{0} must be an object".format(label))
    if "found" not in el:
        _err("{0} missing 'found'".format(label))
    found = el["found"]
    if not isinstance(found, bool):
        _err("{0}.found must be a bool".format(label))
    if not found:
        return
    if "style" not in el:
        _err("{0} missing 'style' (found=true)".format(label))
    _validate_style(el["style"], label)
    if "geometry" not in el:
        _err("{0} missing 'geometry' (found=true)".format(label))
    _validate_geometry(el["geometry"], label)
    if "overflow_x" not in el:
        _err("{0} missing 'overflow_x' (found=true)".format(label))
    _require_str(el["overflow_x"], "{0}.overflow_x".format(label))
    if "position" not in el:
        _err("{0} missing 'position' (found=true)".format(label))
    _require_str(el["position"], "{0}.position".format(label))


def _validate_overflow_candidate(cand, idx):
    # type: (object, int) -> None
    label = "overflow_candidates[{0}]".format(idx)
    if not isinstance(cand, dict):
        _err("{0} must be an object".format(label))
    for key in ("label", "overflow_x"):
        if key not in cand:
            _err("{0} missing '{1}'".format(label, key))
        _require_str(cand[key], "{0}.{1}".format(label, key))
    for key in ("scroll_width", "client_width"):
        if key not in cand:
            _err("{0} missing '{1}'".format(label, key))
        _require_number(cand[key], "{0}.{1}".format(label, key))


def _validate_clip_candidate(cand, idx):
    # type: (object, int) -> None
    label = "clip_candidates[{0}]".format(idx)
    if not isinstance(cand, dict):
        _err("{0} must be an object".format(label))
    for key in ("label", "parent_overflow", "child_position"):
        if key not in cand:
            _err("{0} missing '{1}'".format(label, key))
        _require_str(cand[key], "{0}.{1}".format(label, key))
    if "child_rect" not in cand:
        _err("{0} missing 'child_rect'".format(label))
    _validate_rect(cand["child_rect"], label + ".child_rect")
    if "parent_rect" not in cand:
        _err("{0} missing 'parent_rect'".format(label))
    _validate_rect(cand["parent_rect"], label + ".parent_rect")


# ---------------------------------------------------------------------------
# Bag
# ---------------------------------------------------------------------------


class Bag(object):
    """A normalized measurement bag -- the same shape produced by both the
    built (web DOM) reader and the html intent reader.

    region_found          bool             -- see module docstring.
    elements              Dict[str, dict]  -- keyed by built_testid (built
                                               bag) or anchor selector
                                               (intent bag).
    overflow_candidates   List[dict]       -- built-side only; [] on intent.
    clip_candidates       List[dict]       -- built-side only; [] on intent.
    fonts                 Dict[str, bool]  -- built-side only; {} on intent.
    """

    __slots__ = ("region_found", "elements", "overflow_candidates", "clip_candidates", "fonts")

    def __init__(self, region_found, elements, overflow_candidates=None, clip_candidates=None, fonts=None):
        # type: (bool, Dict[str, dict], Optional[List[dict]], Optional[List[dict]], Optional[Dict[str, bool]]) -> None
        self.region_found = region_found
        self.elements = elements
        self.overflow_candidates = overflow_candidates if overflow_candidates is not None else []
        self.clip_candidates = clip_candidates if clip_candidates is not None else []
        self.fonts = fonts if fonts is not None else {}


def parse_bag(data):
    # type: (object) -> Bag
    """Parse + validate an already-``json.loads``'d payload into a Bag.

    Raises BagParseError on any malformed/missing-field shape. A bag with
    ``region_found=False`` is NOT malformed -- it is valid data meaning the
    caller should treat this as NOT-COVERED (see ``_comparator.compare()``),
    never a parse error and never a silent pass.
    """
    if not isinstance(data, dict):
        _err("top-level payload must be an object, got {0}".format(type(data).__name__))

    if "region_found" not in data:
        _err("missing 'region_found'")
    region_found = data["region_found"]
    if not isinstance(region_found, bool):
        _err("region_found must be a bool, got {0}".format(type(region_found).__name__))

    if "elements" not in data:
        _err("missing 'elements'")
    elements = data["elements"]
    if not isinstance(elements, dict):
        _err("elements must be an object, got {0}".format(type(elements).__name__))
    for key, el in elements.items():
        _validate_element(el, key)

    overflow_candidates = data.get("overflow_candidates", [])
    if not isinstance(overflow_candidates, list):
        _err("overflow_candidates must be a list")
    for i, cand in enumerate(overflow_candidates):
        _validate_overflow_candidate(cand, i)

    clip_candidates = data.get("clip_candidates", [])
    if not isinstance(clip_candidates, list):
        _err("clip_candidates must be a list")
    for i, cand in enumerate(clip_candidates):
        _validate_clip_candidate(cand, i)

    fonts = data.get("fonts", {})
    if not isinstance(fonts, dict):
        _err("fonts must be an object")
    for family, loaded in fonts.items():
        if not isinstance(loaded, bool):
            _err("fonts[{0!r}] must be a bool".format(family))

    return Bag(
        region_found=region_found,
        elements=elements,
        overflow_candidates=overflow_candidates,
        clip_candidates=clip_candidates,
        fonts=fonts,
    )


def load_bag(json_text):
    # type: (str) -> Bag
    """Parse a JSON string (a collector's stdout / a scratch-file's
    contents) into a Bag.

    Raises BagParseError on JSON-decode failure OR any malformed shape (see
    parse_bag) -- both are LOUD, never a silently-returned partial Bag.
    """
    try:
        data = json.loads(json_text)
    except (ValueError, TypeError) as exc:
        raise BagParseError("bag: invalid JSON: {0}".format(exc))
    return parse_bag(data)
