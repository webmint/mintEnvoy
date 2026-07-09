"""_finding.py -- DesignFinding: the design-fidelity finding record
(plan 53 Phase 4/5).

The deterministic comparator (`_floor.py` sanity-floor checks + `_fidelity.py`
anchor-gated checks, orchestrated by `_comparator.py`) emits `DesignFinding`
records. This is a NARROW, Design-fidelity-specific record shaped to align
field-for-field with `src/devforge/lib/_shared/findings_schema.Finding` (file,
severity, title/explanation/suggested_fix) -- it deliberately does NOT
construct a `Finding` instance directly, for one reason: `Finding.category`
is drawn from `CATEGORY_ENUM` (mislogic / system_design / best_practice /
duplication / security / blind_spot), and none of those six values is a
design-fidelity category. Which value (if any) a design-fidelity finding
maps to when rendered into the `## Finding N` report-text contract that
`_shared/_consume.py` parses is a decision for the `design-auditor` rewrite
(plan 53 Phase 6, out of scope here) -- that agent already renders its OWN
report format (see `src/agents/design-auditor.md`'s `## Output` section) and
is free to choose the category at render time. This module only guarantees
the fields Phase 6 needs are present, validated, and severity-enum-clean.

`severity` reuses `_shared.findings_schema.SEVERITY_ENUM` directly (that part
IS unambiguous -- Critical/High/Medium/Info is a universal vocabulary, not a
design-specific one) so a Phase-6 caller can drop this value straight into a
rendered `Severity:` field with no re-mapping.

`file` is polymorphic by design (an established, ratified pattern in this
codebase -- see plan 23's OQ-3, "polymorphic Finding.file"): for a
design-fidelity finding there is no source file in the traditional sense
(the defect is observed via runtime DOM inspection), so `file` carries the
built app's `route` (e.g. "/dashboard") -- the location a human or the
design-auditor's own report would point at.

`selector` carries whichever built_testid / anchor_selector / font-family
token is the direct subject of the finding -- NOT one of Finding's fields
(Finding has no selector concept), but Phase 6 can fold it into the
finding's title/explanation text or a report column.

Design notes
------------
- stdlib only; Python 3.8+
- No third-party deps
- helper-owns-shape: construction validates every field; a caller cannot
  build a DesignFinding with a blank title, an invalid severity, or an
  unknown kind.
"""

from __future__ import annotations

from typing import Optional

from _shared.findings_schema import SEVERITY_ENUM  # type: ignore[import]

# ---------------------------------------------------------------------------
# Kind enum -- what the finding IS (which check produced it).
# ---------------------------------------------------------------------------

FINDING_KINDS = (
    "overflow",
    "clip",
    "font_not_loaded",
    "value_mismatch",
    "geometry_mismatch",
)


def _require_in(value, allowed, field_name):
    # type: (object, tuple, str) -> None
    if value not in allowed:
        raise ValueError(
            "{0} must be one of {1}, got {2!r}".format(field_name, list(allowed), value)
        )


def _require_nonempty_str(value, field_name):
    # type: (object, str) -> None
    if not isinstance(value, str):
        raise ValueError(
            "{0} must be a string, got {1}".format(field_name, type(value).__name__)
        )
    if value.strip() == "":
        raise ValueError("{0} must be a non-empty string".format(field_name))


# ---------------------------------------------------------------------------
# DesignFinding
# ---------------------------------------------------------------------------


class DesignFinding(object):
    """One design-fidelity finding (overflow / clip / font-not-loaded /
    value-mismatch / geometry-mismatch).

    kind           str  -- one of FINDING_KINDS.
    severity       str  -- one of SEVERITY_ENUM (reused from _shared).
    file           str  -- the built app's route (polymorphic Finding.file
                            usage -- there is no source file for a runtime
                            DOM finding).
    selector       str  -- the built_testid / anchor_selector / font-family
                            token this finding is about.
    title          str  -- short one-line summary.
    explanation    str  -- why this is a defect.
    suggested_fix  str  -- what to change.
    property       Optional[str] -- the CSS property / axis in question
                            (e.g. "color", "width", "font-family"), when
                            applicable.
    expected       Optional[str] -- the expected value/number as a string.
    actual         Optional[str] -- the observed value/number as a string.
    """

    __slots__ = (
        "kind",
        "severity",
        "file",
        "selector",
        "title",
        "explanation",
        "suggested_fix",
        "property",
        "expected",
        "actual",
    )

    def __init__(
        self,
        kind,
        severity,
        file,
        selector,
        title,
        explanation,
        suggested_fix,
        property=None,
        expected=None,
        actual=None,
    ):
        # type: (str, str, str, str, str, str, str, Optional[str], Optional[str], Optional[str]) -> None
        _require_in(kind, FINDING_KINDS, "DesignFinding.kind")
        _require_in(severity, SEVERITY_ENUM, "DesignFinding.severity")
        _require_nonempty_str(file, "DesignFinding.file")
        _require_nonempty_str(selector, "DesignFinding.selector")
        _require_nonempty_str(title, "DesignFinding.title")
        _require_nonempty_str(explanation, "DesignFinding.explanation")
        _require_nonempty_str(suggested_fix, "DesignFinding.suggested_fix")

        self.kind = kind
        self.severity = severity
        self.file = file
        self.selector = selector
        self.title = title
        self.explanation = explanation
        self.suggested_fix = suggested_fix
        self.property = property
        self.expected = expected
        self.actual = actual

    def to_dict(self):
        # type: () -> dict
        """Serialize to a JSON-safe dict (used by the `compare` CLI verb)."""
        return {
            "kind": self.kind,
            "severity": self.severity,
            "file": self.file,
            "selector": self.selector,
            "title": self.title,
            "explanation": self.explanation,
            "suggested_fix": self.suggested_fix,
            "property": self.property,
            "expected": self.expected,
            "actual": self.actual,
        }
