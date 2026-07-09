"""_comparator.py -- intent-reader x built-reader x comparator engine
(plan 53 Phase 4/5).

Combines the always-on anchor-FREE sanity floor (``_floor.run_floor``) with
the anchor-gated fidelity layer (``_fidelity.run_fidelity``) and returns a
``ComparisonResult`` distinguishing three outcomes (plan 53 honesty
invariants):

  NOT_COVERED -- the built region itself was not found. Nothing ran.
                 Never a PASS, never a FAIL.
  CLEAN       -- the region WAS found, the floor ran, and (when an intent
                 bag + binding were supplied) fidelity ran too -- and
                 produced zero findings. A REAL pass, distinct from
                 NOT_COVERED (plan 53 honesty invariant #6: "PASS is
                 emittable ONLY when a probe actually executed against a
                 found region").
  DEFECT      -- one or more real findings (overflow / clip /
                 font-not-loaded / value-mismatch / geometry-mismatch).

Two tiers, only one needs the anchor (plan 53 D9): the floor runs whenever
the region is found, with or without an intent bag / binding -- so a feature
with NO captured design anchor still gets a structurally non-vacuous
PASS/FAIL from the floor alone. Fidelity is separately marked
``fidelity_covered`` so a caller can tell "fidelity didn't run because there
is no anchor" apart from "fidelity ran and was clean".

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

from typing import List, Optional

from ._bag import Bag
from ._fidelity import run_fidelity
from ._finding import DesignFinding
from ._floor import run_floor
from ._schema import Binding

STATUS_NOT_COVERED = "NOT_COVERED"
STATUS_CLEAN = "CLEAN"
STATUS_DEFECT = "DEFECT"

_STATUS_ENUM = (STATUS_NOT_COVERED, STATUS_CLEAN, STATUS_DEFECT)


class ComparisonResult(object):
    """The comparator's structured output.

    status                      str   -- one of STATUS_NOT_COVERED /
                                          STATUS_CLEAN / STATUS_DEFECT.
    region_found                bool  -- mirrors built_bag.region_found.
    not_covered_reason           Optional[str] -- set only when
                                          status == STATUS_NOT_COVERED.
    floor_findings               List[DesignFinding] -- always [] when
                                          status == STATUS_NOT_COVERED.
    fidelity_covered              bool -- True iff an intent bag AND a
                                          non-empty binding were supplied
                                          (fidelity actually ran, even if it
                                          found zero pairs it could cover).
    fidelity_findings              List[DesignFinding].
    fidelity_not_covered_pairs     List[str] -- built_testids of pairs whose
                                          built or anchor element was not
                                          found (NOT-COVERED per-pair, never
                                          a defect).
    """

    __slots__ = (
        "status",
        "region_found",
        "not_covered_reason",
        "floor_findings",
        "fidelity_covered",
        "fidelity_findings",
        "fidelity_not_covered_pairs",
    )

    def __init__(
        self,
        status,
        region_found,
        floor_findings,
        fidelity_covered,
        fidelity_findings,
        fidelity_not_covered_pairs,
        not_covered_reason=None,
    ):
        if status not in _STATUS_ENUM:
            raise ValueError(
                "ComparisonResult.status must be one of {0}, got {1!r}".format(
                    list(_STATUS_ENUM), status
                )
            )
        self.status = status
        self.region_found = region_found
        self.not_covered_reason = not_covered_reason
        self.floor_findings = floor_findings
        self.fidelity_covered = fidelity_covered
        self.fidelity_findings = fidelity_findings
        self.fidelity_not_covered_pairs = fidelity_not_covered_pairs

    @property
    def findings(self):
        # type: () -> List[DesignFinding]
        """All real defect findings, floor + fidelity combined."""
        return list(self.floor_findings) + list(self.fidelity_findings)

    def to_dict(self):
        # type: () -> dict
        """Serialize to a JSON-safe dict (used by the `compare` CLI verb)."""
        return {
            "status": self.status,
            "region_found": self.region_found,
            "not_covered_reason": self.not_covered_reason,
            "floor_findings": [f.to_dict() for f in self.floor_findings],
            "fidelity_covered": self.fidelity_covered,
            "fidelity_findings": [f.to_dict() for f in self.fidelity_findings],
            "fidelity_not_covered_pairs": list(self.fidelity_not_covered_pairs),
        }


def compare(built_bag, intent_bag, binding, route):
    # type: (Bag, Optional[Bag], Optional[Binding], str) -> ComparisonResult
    """Run the full engine: floor (always, if region found) + fidelity
    (only when both an intent bag and a non-empty binding are supplied).

    Args:
        built_bag:  the web built-reader's parsed Bag. Required.
        intent_bag: the html intent-reader's parsed Bag, or None when no
                    design anchor was captured for this feature (plan 53
                    honesty invariant #5 -- fidelity is NOT-COVERED, the
                    floor still runs).
        binding:    the feature's Binding (route + pairs), or None. A
                    binding with zero pairs behaves identically to None
                    for fidelity purposes (nothing to compare pairwise).
        route:      the built app's route -- carried into every emitted
                    DesignFinding.file (polymorphic Finding.file usage,
                    see _finding.py).
    """
    if not built_bag.region_found:
        return ComparisonResult(
            status=STATUS_NOT_COVERED,
            region_found=False,
            floor_findings=[],
            fidelity_covered=False,
            fidelity_findings=[],
            fidelity_not_covered_pairs=[],
            not_covered_reason="region not found in built bag",
        )

    floor_findings = run_floor(built_bag, route)

    if intent_bag is not None and binding is not None and binding.pairs:
        fidelity_findings, not_covered_pairs = run_fidelity(built_bag, intent_bag, binding, route)
        fidelity_covered = True
    else:
        fidelity_findings, not_covered_pairs = [], []
        fidelity_covered = False

    status = STATUS_DEFECT if (floor_findings or fidelity_findings) else STATUS_CLEAN

    return ComparisonResult(
        status=status,
        region_found=True,
        floor_findings=floor_findings,
        fidelity_covered=fidelity_covered,
        fidelity_findings=fidelity_findings,
        fidelity_not_covered_pairs=not_covered_pairs,
        not_covered_reason=None,
    )
