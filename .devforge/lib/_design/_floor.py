"""_floor.py -- the always-on, anchor-FREE sanity floor (plan 53 D9/D10).

Three checks -- overflow, clip, font-not-loaded -- all self-evident defects
that need no design anchor / intent bag to evaluate. Runs on the BUILT bag
alone. Non-vacuousness is STRUCTURAL (plan 53 honesty invariants): this
floor runs whenever ``bag.region_found`` is True, regardless of whether the
feature captured a design anchor at all -- a feature with NO anchor still
gets a real PASS/FAIL from this floor (see ``_comparator.compare()``).

Rules (verbatim from the plan):
  overflow -- flag when scrollWidth > clientWidth AND computed
              overflow-x in {visible, hidden}; EXEMPT overflow-x in
              {auto, scroll}. Any other overflow-x value (e.g. "clip",
              an empty string) is also exempt -- only the two explicitly
              named FLAG values trigger a finding; this is a deliberate
              conservative default (never manufacture a finding on an
              overflow-x value the plan did not name).
  clip     -- flag when the child's rendered rect is NOT contained within
              its parent's rect AND the parent's computed overflow is in
              {hidden, clip, auto} AND the child's computed position is in
              {static, relative}; EXEMPT child position in
              {absolute, fixed}. Containment uses a small epsilon
              (_CLIP_EPSILON_PX) to absorb subpixel rendering noise, never
              to hide a real overflow.
  font-not-loaded -- flag when a declared font-family token's
              ``document.fonts.check()`` result (already measured by the
              JS collector -- see _bag.py's contract) is False, UNLESS the
              token is a generic/system keyword (those always resolve and
              are skipped, plan 53 D10). This is the ONE special case: a
              declared-but-unloaded font renders a fallback while its
              *value* still matches, so a value-compare (see _fidelity.py)
              passes vacuously -- only the load check catches it.

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

from typing import Dict, List

from ._bag import Bag
from ._finding import DesignFinding

# ---------------------------------------------------------------------------
# Overflow
# ---------------------------------------------------------------------------

_OVERFLOW_FLAG_VALUES = frozenset(["visible", "hidden"])


def check_overflow(overflow_candidates, route):
    # type: (List[dict], str) -> List[DesignFinding]
    """Flag unintended horizontal overflow across the region's subtree."""
    findings = []
    for cand in overflow_candidates:
        overflow_x = cand["overflow_x"]
        if overflow_x not in _OVERFLOW_FLAG_VALUES:
            # Covers both the explicit exempt set (auto/scroll) and any
            # other unlisted value -- only visible/hidden ever flag.
            continue
        if not (cand["scroll_width"] > cand["client_width"]):
            continue
        label = cand["label"]
        findings.append(
            DesignFinding(
                kind="overflow",
                severity="High",
                file=route,
                selector=label,
                title="Unintended horizontal overflow on {0}".format(label),
                explanation=(
                    "{0} has scrollWidth ({1}) > clientWidth ({2}) with "
                    "computed overflow-x: {3}, and is not a declared "
                    "scroll container (overflow-x: auto/scroll)."
                ).format(label, cand["scroll_width"], cand["client_width"], overflow_x),
                suggested_fix=(
                    "Constrain the element's width/content, or set "
                    "overflow-x: auto/scroll if horizontal scrolling is "
                    "intended."
                ),
                property="overflow-x",
                expected="scrollWidth <= clientWidth",
                actual="scrollWidth={0}, clientWidth={1}, overflow-x={2}".format(
                    cand["scroll_width"], cand["client_width"], overflow_x
                ),
            )
        )
    return findings


# ---------------------------------------------------------------------------
# Clip
# ---------------------------------------------------------------------------

_CLIP_FLAG_PARENT_OVERFLOW = frozenset(["hidden", "clip", "auto"])
_CLIP_FLAG_CHILD_POSITION = frozenset(["static", "relative"])
_CLIP_EXEMPT_CHILD_POSITION = frozenset(["absolute", "fixed"])
_CLIP_EPSILON_PX = 0.5


def _rect_contains(parent, child, epsilon=_CLIP_EPSILON_PX):
    # type: (dict, dict, float) -> bool
    """True if child's box is fully within parent's box (epsilon-tolerant)."""
    return (
        child["x"] >= parent["x"] - epsilon
        and child["y"] >= parent["y"] - epsilon
        and (child["x"] + child["width"]) <= (parent["x"] + parent["width"]) + epsilon
        and (child["y"] + child["height"]) <= (parent["y"] + parent["height"]) + epsilon
    )


def check_clip(clip_candidates, route):
    # type: (List[dict], str) -> List[DesignFinding]
    """Flag a child clipped by an overflow-hidden/clip/auto ancestor."""
    findings = []
    for cand in clip_candidates:
        child_position = cand["child_position"]
        if child_position in _CLIP_EXEMPT_CHILD_POSITION:
            continue
        if child_position not in _CLIP_FLAG_CHILD_POSITION:
            continue
        if cand["parent_overflow"] not in _CLIP_FLAG_PARENT_OVERFLOW:
            continue
        if _rect_contains(cand["parent_rect"], cand["child_rect"]):
            continue
        label = cand["label"]
        findings.append(
            DesignFinding(
                kind="clip",
                severity="High",
                file=route,
                selector=label,
                title="{0} is clipped by an overflow-{1} ancestor".format(
                    label, cand["parent_overflow"]
                ),
                explanation=(
                    "{0}'s rendered box extends outside its parent's box "
                    "while the parent computes overflow: {1} and the child "
                    "is position: {2} (not taken out of normal flow), so "
                    "the overflow is clipped rather than intentionally "
                    "escaping its container."
                ).format(label, cand["parent_overflow"], child_position),
                suggested_fix=(
                    "Resize the child to fit its container, relax the "
                    "parent's overflow, or give the child "
                    "position: absolute/fixed if it is meant to escape."
                ),
                property="position",
                expected="child rect contained within parent rect",
                actual="child={0}, parent={1}".format(
                    cand["child_rect"], cand["parent_rect"]
                ),
            )
        )
    return findings


# ---------------------------------------------------------------------------
# Font-not-loaded
# ---------------------------------------------------------------------------

# Generic/system font keywords that always resolve -- SKIPPED regardless of
# the measured document.fonts.check() result (plan 53 D10).
_GENERIC_FONT_KEYWORDS = frozenset(
    [
        "-apple-system",
        "blinkmacsystemfont",
        "system-ui",
        "sans-serif",
        "serif",
        "monospace",
        "cursive",
        "fantasy",
        "ui-sans-serif",
        "ui-serif",
        "ui-monospace",
        "ui-rounded",
        "emoji",
        "math",
        "fangsong",
        "inherit",
        "initial",
        "unset",
    ]
)


def _strip_family_token(name):
    # type: (str) -> str
    return name.strip().strip('"').strip("'").strip().lower()


def _is_generic_family(name):
    # type: (str) -> bool
    return _strip_family_token(name) in _GENERIC_FONT_KEYWORDS


def check_fonts(fonts, route):
    # type: (Dict[str, bool], str) -> List[DesignFinding]
    """Flag a declared-but-unloaded custom/quoted font family.

    Generic/system keywords (sans-serif, system-ui, ...) always resolve and
    are skipped even if the measured bool happens to be False.
    """
    findings = []
    for family in sorted(fonts.keys()):
        loaded = fonts[family]
        if _is_generic_family(family):
            continue
        if loaded:
            continue
        findings.append(
            DesignFinding(
                kind="font_not_loaded",
                severity="High",
                file=route,
                selector=family,
                title="Declared font family '{0}' is not loaded".format(family),
                explanation=(
                    "document.fonts.check() reports '{0}' as NOT loaded. "
                    "The declaration still names the right family, so a "
                    "plain value-compare against the design anchor would "
                    "pass vacuously (it renders a fallback font while "
                    "looking correct on paper) -- only the load check "
                    "catches this (plan 53 D10)."
                ).format(family),
                suggested_fix=(
                    "Verify the font file is referenced correctly "
                    "(@font-face src / preload / package install) and "
                    "actually ships with the build."
                ),
                property="font-family",
                expected="document.fonts.check() == true",
                actual="false",
            )
        )
    return findings


# ---------------------------------------------------------------------------
# Combined floor
# ---------------------------------------------------------------------------


def run_floor(bag, route):
    # type: (Bag, str) -> List[DesignFinding]
    """Run the full always-on sanity floor over a BUILT bag.

    Callers gate this on ``bag.region_found`` being True upstream (see
    ``_comparator.compare()`` -- a not-found region never reaches here).
    Returns the concatenated overflow + clip + font-not-loaded findings.
    """
    findings = []
    findings.extend(check_overflow(bag.overflow_candidates, route))
    findings.extend(check_clip(bag.clip_candidates, route))
    findings.extend(check_fonts(bag.fonts, route))
    return findings
