"""_fidelity.py -- anchor-gated value + geometry fidelity checks (plan 53 D9).

Needs BOTH the built bag and the intent bag, driven by the binding's pairs
(``_schema.Binding.pairs`` -- each a ``{anchor_selector, built_testid}``
correspondence, plan 53 D4/D7). A pair whose built element or anchor element
was not FOUND in its bag is NOT-COVERED for THAT PAIR ONLY -- it never
contributes a finding and never blocks the other pairs (plan 53 honesty
invariant #4, scoped per-pair, not a comparator-wide failure).

Two checks per covered pair:
  value fidelity    -- normalized string-compare of the paired elements'
                       computed style values (color / background / border /
                       border-radius / padding / margin / gap / font-family /
                       font-size / line-height / font-weight). font-family
                       mismatches are severity High (typography drift is the
                       plan's named motivating regression); every other
                       property is Medium.
  geometry fidelity -- numeric compare of rendered width/height, tolerant of
                       a small normalization band (``_GEOMETRY_TOLERANCE_PX``
                       floor + ``_GEOMETRY_TOLERANCE_RATIO`` relative) so
                       subpixel/reflow noise does not manufacture a finding.
                       Deliberately narrowed to width/height only (NOT x/y
                       page position) -- the intent side renders the anchor
                       file standalone in its own document, so absolute page
                       coordinates between intent and built have no shared
                       reference frame; box DIMENSIONS are the well-defined,
                       comparable geometry signal. Flagged as a scope note
                       in this phase's delivery report, not a silent gap.

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

from typing import List, Tuple

from ._bag import Bag
from ._finding import DesignFinding
from ._schema import Binding

# ---------------------------------------------------------------------------
# Value fidelity
# ---------------------------------------------------------------------------

# FIX F5 (clarification, no logic change): every pair -- including
# binding.pairs[0], the mandatory container-floor pair (plan 53 D7) -- is
# compared against this SAME full property list, incl. non-inherited
# properties like border/padding/margin/gap. This is INTENTIONAL: D7's
# "inherited properties" wording explains WHY comparing the container
# catches drift across every child (an inherited default class propagates
# to descendants), it is NOT a scope restriction that limits the container
# pair to inherited-only properties -- comparing the container's own full
# box model to intent is a valid, separate check.
#
# (style key, severity) -- font_family is the ONE High; every other property
# is Medium. Order is the order findings are emitted in for a given pair.
_VALUE_PROPERTIES = (
    ("color", "Medium"),
    ("background", "Medium"),
    ("border", "Medium"),
    ("border_radius", "Medium"),
    ("padding", "Medium"),
    ("margin", "Medium"),
    ("gap", "Medium"),
    ("font_family", "High"),
    ("font_size", "Medium"),
    ("line_height", "Medium"),
    ("font_weight", "Medium"),
)


def _normalize_value(v):
    # type: (str) -> str
    """Collapse internal whitespace runs and strip -- avoids false mismatches
    from purely cosmetic whitespace differences in computed-style strings."""
    return " ".join(v.split()).strip()


def compare_pair_values(pair, built_el, intent_el, route):
    # type: (object, dict, dict, str) -> List[DesignFinding]
    """Diff one pair's style dicts. Assumes both elements are found."""
    findings = []
    built_style = built_el["style"]
    intent_style = intent_el["style"]
    for prop, severity in _VALUE_PROPERTIES:
        built_val = _normalize_value(built_style.get(prop, ""))
        intent_val = _normalize_value(intent_style.get(prop, ""))
        if built_val == intent_val:
            continue
        findings.append(
            DesignFinding(
                kind="value_mismatch",
                severity=severity,
                file=route,
                selector=pair.built_testid,
                title="{0} mismatch on {1}".format(prop, pair.built_testid),
                explanation=(
                    "Computed {0} on built element '{1}' ({2!r}) does not "
                    "match the design anchor's computed value on '{3}' "
                    "({4!r})."
                ).format(
                    prop, pair.built_testid, built_val, pair.anchor_selector, intent_val
                ),
                suggested_fix="Update the built element's {0} to match the design anchor.".format(
                    prop
                ),
                property=prop,
                expected=intent_val,
                actual=built_val,
            )
        )
    return findings


# ---------------------------------------------------------------------------
# Geometry fidelity
# ---------------------------------------------------------------------------

_GEOMETRY_TOLERANCE_PX = 2.0
_GEOMETRY_TOLERANCE_RATIO = 0.02
_GEOMETRY_DIMENSIONS = ("width", "height")


def _tolerance_for(expected):
    # type: (float) -> float
    return max(_GEOMETRY_TOLERANCE_PX, abs(expected) * _GEOMETRY_TOLERANCE_RATIO)


def compare_pair_geometry(pair, built_el, intent_el, route):
    # type: (object, dict, dict, str) -> List[DesignFinding]
    """Diff one pair's box width/height. Assumes both elements are found."""
    findings = []
    built_geo = built_el["geometry"]
    intent_geo = intent_el["geometry"]
    for dim in _GEOMETRY_DIMENSIONS:
        expected = intent_geo[dim]
        actual = built_geo[dim]
        if abs(actual - expected) <= _tolerance_for(expected):
            continue
        findings.append(
            DesignFinding(
                kind="geometry_mismatch",
                severity="Medium",
                file=route,
                selector=pair.built_testid,
                title="{0} mismatch on {1}".format(dim, pair.built_testid),
                explanation=(
                    "Built element '{0}' {1} ({2}px) differs from the "
                    "design anchor's rendered {1} ({3}px) beyond the "
                    "normalization tolerance."
                ).format(pair.built_testid, dim, actual, expected),
                suggested_fix="Adjust the built element's {0} to match the design anchor.".format(
                    dim
                ),
                property=dim,
                expected=str(expected),
                actual=str(actual),
            )
        )
    return findings


# ---------------------------------------------------------------------------
# Combined per-binding fidelity run
# ---------------------------------------------------------------------------


def run_fidelity(built_bag, intent_bag, binding, route):
    # type: (Bag, Bag, Binding, str) -> Tuple[List[DesignFinding], List[str]]
    """Run value + geometry fidelity over every pair in the binding.

    Returns (findings, not_covered_built_testids). A pair whose built
    element or anchor element was not found contributes its built_testid to
    the not-covered list and no findings -- NOT-COVERED, never a defect.
    """
    findings = []
    not_covered = []
    for pair in binding.pairs:
        built_el = built_bag.elements.get(pair.built_testid)
        intent_el = intent_bag.elements.get(pair.anchor_selector)

        built_found = built_el is not None and built_el.get("found") is True
        intent_found = intent_el is not None and intent_el.get("found") is True

        if not built_found or not intent_found:
            not_covered.append(pair.built_testid)
            continue

        findings.extend(compare_pair_values(pair, built_el, intent_el, route))
        findings.extend(compare_pair_geometry(pair, built_el, intent_el, route))

    return findings, not_covered
