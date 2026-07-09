"""_schema.py — binding schema for design_helper (plan 53 Phase 3).

RETIRED: the data-ref / disposition-manifest schema (plan 40 Phase 2) —
`ElementRecord` (slots `data_ref` / `disposition` / `deviate_reason`), the
`DISPOSITION_*` constants + `VALID_DISPOSITIONS`, and `ManifestContainer`'s
element/gap-list shape.  Superseded by the BINDING schema below (plan 53
D4/D7).

The anchor (`specs/[feature]/design-anchor.json`, plan 53 Phase 2) captures
design INTENT once at intake: `{kind, file, selectors}`.  The BINDING is the
built-side wiring authored LATER at `/breakdown`, referencing the anchor: it
completes "where the feature renders + which built element corresponds to
which intent element."  The binding is the successor of plan 40's
`design-manifest.json` — same on-disk FILENAME, new schema.

Shape overview
--------------
BindingPair — one anchor-to-built correspondence:
  anchor_selector str — required; a CSS selector into the anchor (reference)
                        file.  MAY be brittle (e.g. a class) — the reference
                        is a static file that never changes (plan 53 D7
                        selector asymmetry).
  built_testid    str — required; a stable testid on the BUILT element.
                        Must be stable — it points at living, refactored code
                        (normal engineering practice to add a testid).

Binding — the full binding:
  version str               — schema version string "2" (the binding
                               schema; "1" was the retired disposition-
                               manifest schema).
  route   str                — required; the route where the feature renders
                               in the built app.
  pairs   list[BindingPair]  — required, >= 1.  The FIRST pair is the
                               mandatory container-floor pair (anchor
                               container <-> built container — catches the
                               inherited-default class across every child,
                               plan 53 D7); additional pairs are opt-in
                               precision for per-element overridden
                               properties.  A structural auto-walk
                               (nth-child / tag parallel walk) is explicitly
                               REJECTED (plan 40 OQ-5) — pairs are always
                               human-declared.

Validation helpers
------------------
validate_pair(pair, index) -> list[str]  — per-pair validation errors
validate_binding(binding) -> list[str]   — full-binding validation errors
  (empty list = valid).  An empty binding (no route, no pairs) fails on BOTH
  checks — the intake escalation (plan 53 honesty invariant #3): a binding
  must never validate as clean by omission.

Serialization
-------------
pair_to_dict(pair) -> dict
pair_from_dict(d) -> BindingPair
binding_to_dict(binding) -> dict
binding_from_dict(d) -> Binding
binding_to_json(binding, indent=2) -> str
binding_from_json(text) -> Binding

Retired-schema detection
------------------------
`binding_from_dict` raises `RetiredManifestSchemaError` (a `ValueError`
subclass) when handed a dict shaped like the retired plan-40 disposition
manifest (an `elements` or `gap_list` key present, or `version == "1"`)
instead of coercing it to an empty/incomplete `Binding` and letting it fail
`validate_binding` with the generic route/pairs message. This distinguishes
"this file is the retired format" from "you forgot to author a binding" for
every caller that deserializes a binding (`validate-binding`,
`verify-manifest-present`'s `finalize-handoff` chokepoint). A genuinely
empty-or-incomplete binding (no `elements`/`gap_list`/`version == "1"`, just
a missing/blank `route` or `pairs`) is NOT retired-shaped and stays on the
existing generic `validate_binding` error path.

Non-object-shape detection
--------------------------
`binding_from_dict` / `pair_from_dict` raise `BindingParseError` (a
`ValueError` subclass) when the payload is not a JSON object where one is
required — a `null`/list/scalar top-level binding, a non-list `pairs`
value, or a non-object `pairs` entry — instead of letting a bare `.get()`
call raise an uncaught `TypeError`/`AttributeError`. Checked BEFORE the
retired-schema detection so that check never runs its own membership/`.get`
calls against a non-dict.

On-disk home
------------
specs/[feature]/design-manifest.json — same FILENAME as plan 40's disposition
manifest (the binding is its successor, plan 53 D4); downstream call sites
that glob or assert on this filename (plan 42's `verify-manifest-present` /
`finalize-handoff` chokepoint) stay valid unchanged.

Design notes
------------
- stdlib only; Python 3.8+
- No third-party deps
- helper-owns-shape: callers supply values; this module owns structure/validation
- Control characters (< 0x20, except tab) are rejected at set-time in string
  fields to prevent silent YAML/JSON corruption (audit anti-pattern #1).
"""

from __future__ import annotations

import json
from typing import List, Optional

SCHEMA_VERSION = "2"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class BindingParseError(ValueError):
    """Raised by ``binding_from_dict`` / ``pair_from_dict`` when the JSON
    payload is not shaped as an object where one is required -- e.g. the
    top-level binding is ``null``/a list/a scalar, ``pairs`` is not a list,
    or a ``pairs`` entry is not an object (FIX F2).

    A ValueError subclass so existing ``except (OSError, ValueError)`` /
    ``except (RetiredManifestSchemaError, ValueError)`` catch sites (
    ``validate-binding``, the ``compare`` verb) keep working unmodified --
    they surface this error's message instead of an uncaught TypeError/
    AttributeError from a bare ``.get()`` call on a non-dict.
    """


# ---------------------------------------------------------------------------
# Control-character guard (audit anti-pattern #1)
# ---------------------------------------------------------------------------


def _has_control_chars(s):
    # type: (str) -> bool
    """Return True if s contains a control character (< 0x20 except tab)."""
    for ch in s:
        code = ord(ch)
        if code < 0x20 and code != 0x09:  # allow tab
            return True
    return False


def _require_clean_string(value, field_name):
    # type: (str, str) -> Optional[str]
    """Return an error string if value contains control chars; None if clean."""
    if not isinstance(value, str):
        return "{0}: expected str, got {1}".format(field_name, type(value).__name__)
    if _has_control_chars(value):
        return "{0}: contains control characters".format(field_name)
    return None


# ---------------------------------------------------------------------------
# BindingPair
# ---------------------------------------------------------------------------


class BindingPair(object):
    """One anchor-selector <-> built-testid correspondence."""

    __slots__ = ("anchor_selector", "built_testid")

    def __init__(self, anchor_selector="", built_testid=""):
        # type: (str, str) -> None
        self.anchor_selector = anchor_selector  # type: str
        self.built_testid = built_testid        # type: str


def validate_pair(pair, index):
    # type: (BindingPair, int) -> List[str]
    """Validate a single BindingPair.  Returns a list of error strings (empty = ok)."""
    errors = []  # type: List[str]
    label = "pairs[{0}]".format(index)

    err = _require_clean_string(pair.anchor_selector, "anchor_selector")
    if err:
        errors.append("{0}: {1}".format(label, err))
    elif not pair.anchor_selector.strip():
        errors.append("{0}: anchor_selector must be non-empty".format(label))

    err = _require_clean_string(pair.built_testid, "built_testid")
    if err:
        errors.append("{0}: {1}".format(label, err))
    elif not pair.built_testid.strip():
        errors.append("{0}: built_testid must be non-empty".format(label))

    return errors


# ---------------------------------------------------------------------------
# Binding
# ---------------------------------------------------------------------------


class Binding(object):
    """The full per-feature built-side binding: route + pairs."""

    __slots__ = ("version", "route", "pairs")

    def __init__(self, route="", pairs=None):
        # type: (str, Optional[List[BindingPair]]) -> None
        self.version = SCHEMA_VERSION   # type: str
        self.route = route              # type: str
        self.pairs = pairs or []        # type: List[BindingPair]


def validate_binding(binding):
    # type: (Binding) -> List[str]
    """Validate the full binding.

    Returns a list of error strings (empty list = valid / exit 0).

    Validation rules (plan 53 D4/D7):
    1. route must be non-empty (and control-char-clean).
    2. pairs must contain at least one entry (the container floor) —
       zero pairs is a validation error, not a silent pass.
    3. Every pair must pass validate_pair (missing anchor_selector or
       built_testid -> fail naming the pair index and field).

    An empty binding (route="" and pairs=[]) fails BOTH rule 1 and rule 2 —
    this is deliberate (plan 53 honesty invariant #3): the intake escalation
    must never validate clean by omission.
    """
    errors = []  # type: List[str]

    # Rule 1: route
    err = _require_clean_string(binding.route, "route")
    if err:
        errors.append(err)
    elif not binding.route.strip():
        errors.append("route: must be non-empty")

    # Rule 2 + 3: pairs
    if not binding.pairs:
        errors.append(
            "pairs: must contain at least one pair (the container floor) — "
            "an empty binding is not a valid intake"
        )
    else:
        for i, pair in enumerate(binding.pairs):
            errors.extend(validate_pair(pair, i))

    return errors


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def pair_to_dict(pair):
    # type: (BindingPair) -> dict
    """Serialize a BindingPair to a JSON-safe dict."""
    return {
        "anchor_selector": pair.anchor_selector,
        "built_testid": pair.built_testid,
    }


def pair_from_dict(d):
    # type: (object) -> BindingPair
    """Deserialize a BindingPair from a dict (e.g. parsed from JSON).

    Raises BindingParseError (a ValueError subclass) when ``d`` is not a
    JSON object -- e.g. a string entry inside a ``pairs`` array (FIX F2).
    Existing ``except (OSError, ValueError)`` / ``except (...,
    RetiredManifestSchemaError, ValueError)`` catch sites keep working
    unmodified.
    """
    if not isinstance(d, dict):
        raise BindingParseError(
            "binding: pairs entry must be a JSON object, got {0}".format(
                type(d).__name__
            )
        )
    return BindingPair(
        anchor_selector=d.get("anchor_selector", ""),
        built_testid=d.get("built_testid", ""),
    )


def binding_to_dict(binding):
    # type: (Binding) -> dict
    """Serialize a Binding to a JSON-safe dict."""
    return {
        "version": binding.version,
        "route": binding.route,
        "pairs": [pair_to_dict(p) for p in binding.pairs],
    }


class RetiredManifestSchemaError(ValueError):
    """Raised by binding_from_dict when the dict is shaped like the retired
    plan-40 disposition-manifest schema (ElementRecord / gap_list) instead of
    the current binding schema (route + pairs).

    A ValueError subclass so existing (OSError, ValueError) catch sites in
    callers (validate-binding, verify-manifest-present) keep working without
    modification -- they surface this error's message instead of the generic
    route/pairs validation errors.
    """


_RETIRED_SCHEMA_MESSAGE = (
    "binding: this file uses the retired data-ref manifest schema "
    "(elements/gap_list) — re-author it as a route+pairs binding"
)


def _is_retired_manifest_shape(d):
    # type: (dict) -> bool
    """Return True if d looks like the retired plan-40 disposition-manifest shape.

    Detection (any one is sufficient):
      - an "elements" key present (the retired per-element list)
      - a "gap_list" key present (the retired unresolvable-token list)
      - version == "1" (the retired schema's version string; the current
        binding schema is SCHEMA_VERSION == "2")
    """
    return (
        "elements" in d
        or "gap_list" in d
        or d.get("version") == "1"
    )


def binding_from_dict(d):
    # type: (object) -> Binding
    """Deserialize a Binding from a dict (e.g. parsed from JSON).

    Raises BindingParseError (FIX F2) when ``d`` itself is not a JSON
    object (e.g. json.loads'd `null`/a list/a scalar), or when its
    ``pairs`` value is present but not a JSON array -- checked BEFORE
    ``_is_retired_manifest_shape`` so that check never runs its own
    ``"elements" in d`` / ``d.get(...)`` calls against a non-dict (which
    would themselves raise an uncaught TypeError/AttributeError for some
    shapes, e.g. ``d=None``).

    Raises RetiredManifestSchemaError when d is shaped like the retired
    plan-40 disposition manifest (see _is_retired_manifest_shape) rather than
    silently coercing it to an empty/incomplete Binding. A genuinely
    empty-or-incomplete binding (e.g. {"route": "", "pairs": []}) is NOT
    retired-shaped and deserializes normally, onto the existing
    validate_binding generic-error path.
    """
    if not isinstance(d, dict):
        raise BindingParseError(
            "binding: expected a JSON object at the top level, got {0}".format(
                type(d).__name__
            )
        )
    if _is_retired_manifest_shape(d):
        raise RetiredManifestSchemaError(_RETIRED_SCHEMA_MESSAGE)
    raw_pairs = d.get("pairs", [])
    if not isinstance(raw_pairs, list):
        raise BindingParseError(
            "binding: 'pairs' must be a JSON array, got {0}".format(
                type(raw_pairs).__name__
            )
        )
    pairs = [pair_from_dict(p) for p in raw_pairs]
    return Binding(route=d.get("route", ""), pairs=pairs)


def binding_to_json(binding, indent=2):
    # type: (Binding, int) -> str
    """Serialize a Binding to a JSON string."""
    return json.dumps(binding_to_dict(binding), indent=indent, sort_keys=True)


def binding_from_json(text):
    # type: (str) -> Binding
    """Deserialize a Binding from a JSON string."""
    return binding_from_dict(json.loads(text))
