"""seed_schema -- re-entry seed schema for the /grill backward handoff.

Provides the ``ReEntrySeed`` frozen dataclass, ``SEED_SOURCE``,
``SEED_TARGET_STAGES``, and ``SEED_SCHEMA_VERSION`` constants for the
/grill → upstream (spec/discovery/research/plan) backward handoff artefact.

What this is: when a grill attack proves a plan defect is rooted UPSTREAM
(the design faithfully implements a flawed spec/discovery/research conclusion),
/grill emits a ReEntrySeed; /research, /discover, /specify, or /plan consume
it on re-entry so the re-run is DIRECTED -- it does not re-derive the same
flaw.  When ``target_stage="plan"`` the seed represents a same-stage revision
request (the plan itself is the re-entry point, not a prior upstream stage).
The seed also carries the bounded-compounding-loop state (cycle_count,
carried_findings) so upstream commands can detect and cap re-entry loops.

Design notes:

- Dataclasses are pure records. No serialization (to_dict / from_dict),
  no rendering, no I/O. Those responsibilities live in the helper command
  layer so this schema stays small and independently testable.

- Schema-level validation runs in __post_init__ and is mechanical:
    * Required string fields are non-empty after .strip().
    * source must equal the module constant SEED_SOURCE ("grill").
    * target_stage must be one of SEED_TARGET_STAGES.
    * cycle_count: strict int (no bool), must be >= 1.
    * carried_findings: list of str; may be empty.

- Type-hint convention: explicit typing.List
  (no PEP 604 X | None, no PEP 585 list[str]). Targets Python 3.8+.
  from __future__ import annotations intentionally NOT used so
  __post_init__ introspection sees real type objects.

Stdlib only. No third-party dependencies.
"""

from dataclasses import dataclass
from typing import List

# ---------------------------------------------------------------------------
# Schema version constant.
# ---------------------------------------------------------------------------

SEED_SCHEMA_VERSION = "1"

# ---------------------------------------------------------------------------
# Provenance and allowed enum values.
# ---------------------------------------------------------------------------

SEED_SOURCE = "grill"

SEED_TARGET_STAGES = ("spec", "discovery", "research", "plan")

# ---------------------------------------------------------------------------
# Validation helpers.
# (Self-contained so this schema is independently importable.)
# ---------------------------------------------------------------------------


def _require_nonempty(value, field_name):
    # type: (object, str) -> None
    """Raise ValueError if value is not a non-empty (post-strip) string."""
    if not isinstance(value, str):
        raise ValueError(
            "{0} must be a string, got {1}".format(field_name, type(value).__name__)
        )
    if value.strip() == "":
        raise ValueError("{0} must be a non-empty string".format(field_name))


def _require_in_enum(value, allowed, field_name):
    # type: (object, tuple, str) -> None
    """Raise ValueError if value is not in allowed."""
    if value not in allowed:
        raise ValueError(
            "{0} must be one of {1}, got {2!r}".format(
                field_name, list(allowed), value
            )
        )


# ---------------------------------------------------------------------------
# ReEntrySeed -- the /grill backward handoff record.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReEntrySeed:
    """Re-entry seed emitted by /grill when a plan defect is rooted upstream.

    seed_version is a non-empty string; callers should pass SEED_SCHEMA_VERSION
      ("1"); any non-empty string is accepted at the schema level.
    source must equal SEED_SOURCE ("grill") -- any other value is rejected.
    target_stage must be one of SEED_TARGET_STAGES ("spec", "discovery",
      "research", "plan") -- the re-entry target stage.
    feature is the feature slug/id; non-empty.
    prior_conclusion is what the upstream stage concluded (now invalidated);
      non-empty.
    invalidating_evidence is the grounded grill finding (quote/ref) that
      invalidates the prior_conclusion; non-empty.
    must_satisfy is what the re-run must additionally satisfy; non-empty.
    cycle_count is the bounded-compounding-loop counter; strict int (no bool),
      must be >= 1.
    carried_findings is prior findings carried forward (monotonic compounding);
      must be a list of str, may be empty.
    provenance is a pointer to the source grill.md / plan path; non-empty.
    """

    seed_version: str
    source: str
    target_stage: str
    feature: str
    prior_conclusion: str
    invalidating_evidence: str
    must_satisfy: str
    cycle_count: int
    carried_findings: List[str]
    provenance: str

    def __post_init__(self):
        # type: () -> None
        _require_nonempty(self.seed_version, "ReEntrySeed.seed_version")

        # source must be a non-empty string and must equal SEED_SOURCE.
        _require_nonempty(self.source, "ReEntrySeed.source")
        if self.source != SEED_SOURCE:
            raise ValueError(
                "ReEntrySeed.source must be {0!r}, got {1!r}".format(
                    SEED_SOURCE, self.source
                )
            )

        _require_in_enum(self.target_stage, SEED_TARGET_STAGES, "ReEntrySeed.target_stage")
        _require_nonempty(self.feature, "ReEntrySeed.feature")
        _require_nonempty(self.prior_conclusion, "ReEntrySeed.prior_conclusion")
        _require_nonempty(self.invalidating_evidence, "ReEntrySeed.invalidating_evidence")
        _require_nonempty(self.must_satisfy, "ReEntrySeed.must_satisfy")

        # cycle_count: strict int (no bool), >= 1.
        if isinstance(self.cycle_count, bool):
            raise ValueError(
                "ReEntrySeed.cycle_count must be an int, got bool"
            )
        if not isinstance(self.cycle_count, int):
            raise ValueError(
                "ReEntrySeed.cycle_count must be an int, got {0}".format(
                    type(self.cycle_count).__name__
                )
            )
        if self.cycle_count < 1:
            raise ValueError(
                "ReEntrySeed.cycle_count must be >= 1, got {0}".format(
                    self.cycle_count
                )
            )

        # carried_findings: list of str (may be empty).
        if not isinstance(self.carried_findings, list):
            raise ValueError("ReEntrySeed.carried_findings must be a list")
        for i, item in enumerate(self.carried_findings):
            if not isinstance(item, str):
                raise ValueError(
                    "ReEntrySeed.carried_findings[{0}] must be a str, "
                    "got {1}".format(i, type(item).__name__)
                )

        _require_nonempty(self.provenance, "ReEntrySeed.provenance")
