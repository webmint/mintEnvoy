"""handoff_schema -- dataclass schema for the plan -> breakdown handoff artefact.

Single source of truth for the shape of ``specs/NNN-<slug>/plan-handoff.json``
emitted by ``plan_helper finalize-handoff`` and consumed by ``/breakdown``
(consumer not yet implemented; will conform to this schema).

Design notes:

- Dataclasses are pure records. No serialization (to_dict / from_dict),
  no rendering, no I/O. Those responsibilities live in the helper command
  layer (plan_helper.py) so this schema stays small and independently testable.

- Schema-level validation runs in __post_init__ and is mechanical:
    * Required string fields are non-empty after .strip().
    * Nested records receive isinstance checks at the Handoff level.
    * handoff_kind is a constant "plan" -- any other value is rejected.
    * Provenance co-vary invariant: upstream_handoff_path and
      upstream_handoff_kind must both be set or both be None.

- handoff_kind is a CONSTANT "plan" -- any other value is rejected.
  plan_helper.finalize-handoff is the only producer.

- Placeholder detection (rows with [path], [decision], _(none)_,
  (none)) is the producer's responsibility -- this schema only validates
  that delivered rows have non-empty required fields.

- Type-hint convention: explicit typing.Optional / List
  (no PEP 604 X | None, no PEP 585 list[str]). Targets Python 3.8+.
  from __future__ import annotations intentionally NOT used so
  __post_init__ introspection sees real type objects.

Stdlib only. No third-party dependencies.
"""

from dataclasses import dataclass
from typing import List, Optional

# ---------------------------------------------------------------------------
# Schema version constant.
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "1.0"
HANDOFF_KIND = "plan"

# ---------------------------------------------------------------------------
# Allowed values for Provenance.upstream_handoff_kind.
# ---------------------------------------------------------------------------

_VALID_UPSTREAM_HANDOFF_KIND = ("specify",)

# Allowed verdict values in ConsultRow.verdict.
VERDICT_ENUM = ("accepted", "modified", "rejected", "no-response")


# ---------------------------------------------------------------------------
# Validation helpers.
# (Self-contained so this schema is independently importable without
# cross-dependency on other schema modules.)
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
                field_name, sorted(allowed), value
            )
        )


# ---------------------------------------------------------------------------
# Row dataclasses for BreakdownSeeds lists.
# ---------------------------------------------------------------------------


@dataclass
class LayerRow:
    """One row from the ### Layer Map table.

    Columns: Layer | What | Files (existing or new).
    """

    layer: str
    what: str
    files: str

    def __post_init__(self):
        # type: () -> None
        _require_nonempty(self.layer, "LayerRow.layer")
        _require_nonempty(self.what, "LayerRow.what")
        if not isinstance(self.files, str):
            raise ValueError(
                "LayerRow.files must be a string, got {0}".format(
                    type(self.files).__name__
                )
            )


@dataclass
class DecisionRow:
    """One row from the ### Key Design Decisions table.

    Columns: Decision | Chosen Approach | Why | Alternatives Rejected.
    """

    decision: str
    chosen_approach: str
    why: str
    alternatives_rejected: str

    def __post_init__(self):
        # type: () -> None
        _require_nonempty(self.decision, "DecisionRow.decision")
        _require_nonempty(self.chosen_approach, "DecisionRow.chosen_approach")
        _require_nonempty(self.why, "DecisionRow.why")
        if not isinstance(self.alternatives_rejected, str):
            raise ValueError(
                "DecisionRow.alternatives_rejected must be a string, got {0}".format(
                    type(self.alternatives_rejected).__name__
                )
            )


@dataclass
class FileImpactRow:
    """One row from the ### File Impact table.

    Columns: File | Action | What Changes.
    """

    file: str
    action: str
    what_changes: str

    def __post_init__(self):
        # type: () -> None
        _require_nonempty(self.file, "FileImpactRow.file")
        _require_nonempty(self.action, "FileImpactRow.action")
        if not isinstance(self.what_changes, str):
            raise ValueError(
                "FileImpactRow.what_changes must be a string, got {0}".format(
                    type(self.what_changes).__name__
                )
            )


@dataclass
class DocImpactRow:
    """One row from the ### Documentation Impact table.

    Columns: Doc File | Action | What Changes.
    """

    doc_file: str
    action: str
    what_changes: str

    def __post_init__(self):
        # type: () -> None
        _require_nonempty(self.doc_file, "DocImpactRow.doc_file")
        _require_nonempty(self.action, "DocImpactRow.action")
        if not isinstance(self.what_changes, str):
            raise ValueError(
                "DocImpactRow.what_changes must be a string, got {0}".format(
                    type(self.what_changes).__name__
                )
            )


@dataclass
class RiskRow:
    """One row from the ## Risk Assessment table.

    Columns: Risk | Likelihood | Impact | Mitigation.
    """

    risk: str
    likelihood: str
    impact: str
    mitigation: str

    def __post_init__(self):
        # type: () -> None
        _require_nonempty(self.risk, "RiskRow.risk")
        _require_nonempty(self.likelihood, "RiskRow.likelihood")
        _require_nonempty(self.impact, "RiskRow.impact")
        _require_nonempty(self.mitigation, "RiskRow.mitigation")


@dataclass
class ConsultRow:
    """One row from the ## Specialist Consultation table.

    Columns: Specialist | Sub-question | Input summary | Verdict | Cites.
    Verdict must be one of: accepted / modified / rejected / no-response.
    """

    specialist: str
    sub_question: str
    input_summary: str
    verdict: str
    cites: str

    def __post_init__(self):
        # type: () -> None
        _require_nonempty(self.specialist, "ConsultRow.specialist")
        _require_nonempty(self.sub_question, "ConsultRow.sub_question")
        if not isinstance(self.input_summary, str):
            raise ValueError(
                "ConsultRow.input_summary must be a string, got {0}".format(
                    type(self.input_summary).__name__
                )
            )
        _require_in_enum(self.verdict, VERDICT_ENUM, "ConsultRow.verdict")
        if not isinstance(self.cites, str):
            raise ValueError(
                "ConsultRow.cites must be a string, got {0}".format(
                    type(self.cites).__name__
                )
            )


# ---------------------------------------------------------------------------
# BreakdownSeeds -- all structured content /breakdown needs from /plan.
# ---------------------------------------------------------------------------


@dataclass
class BreakdownSeeds:
    """Structured seeds extracted from plan.md for /breakdown.

    All list fields are empty when the corresponding section is absent or
    contains only placeholder rows. dependencies is a list of non-blank
    non-heading lines from the ## Dependencies section.
    """

    layer_map: List[LayerRow]
    key_design_decisions: List[DecisionRow]
    file_impact: List[FileImpactRow]
    doc_impact: List[DocImpactRow]
    risks: List[RiskRow]
    specialist_consultation: List[ConsultRow]
    dependencies: List[str]

    def __post_init__(self):
        # type: () -> None
        for fname in (
            "layer_map",
            "key_design_decisions",
            "file_impact",
            "doc_impact",
            "risks",
            "specialist_consultation",
            "dependencies",
        ):
            val = getattr(self, fname)
            if not isinstance(val, list):
                raise ValueError(
                    "BreakdownSeeds.{0} must be a list".format(fname)
                )


# ---------------------------------------------------------------------------
# Nested record: Provenance.
# ---------------------------------------------------------------------------


@dataclass
class Provenance:
    """Upstream handoff provenance for the plan-handoff artefact.

    Upstream refers to the sibling specify handoff (specs/NNN/handoff.json).
    Both upstream_handoff_path and upstream_handoff_kind must be set or
    both must be None (co-vary invariant). spec_path points to the spec.md
    (best-effort, may be None when no sibling spec.md exists).
    """

    upstream_handoff_path: Optional[str] = None
    upstream_handoff_kind: Optional[str] = None
    spec_path: Optional[str] = None

    def __post_init__(self):
        # type: () -> None
        if self.upstream_handoff_path is not None:
            if not isinstance(self.upstream_handoff_path, str):
                raise ValueError(
                    "Provenance.upstream_handoff_path must be a string or None, "
                    "got {0}".format(type(self.upstream_handoff_path).__name__)
                )
            _require_nonempty(
                self.upstream_handoff_path, "Provenance.upstream_handoff_path"
            )

        if self.upstream_handoff_kind is not None:
            if not isinstance(self.upstream_handoff_kind, str):
                raise ValueError(
                    "Provenance.upstream_handoff_kind must be a string or None, "
                    "got {0}".format(type(self.upstream_handoff_kind).__name__)
                )
            _require_in_enum(
                self.upstream_handoff_kind,
                _VALID_UPSTREAM_HANDOFF_KIND,
                "Provenance.upstream_handoff_kind",
            )

        if self.spec_path is not None and not isinstance(self.spec_path, str):
            raise ValueError(
                "Provenance.spec_path must be a string or None, "
                "got {0}".format(type(self.spec_path).__name__)
            )

        # Co-vary invariant: path and kind must both be set or both be None.
        if (self.upstream_handoff_path is None) != (self.upstream_handoff_kind is None):
            raise ValueError(
                "Provenance.upstream_handoff_path and upstream_handoff_kind must "
                "both be set or both be None; got path={0!r}, kind={1!r}".format(
                    self.upstream_handoff_path, self.upstream_handoff_kind
                )
            )


# ---------------------------------------------------------------------------
# Top-level Handoff record.
# ---------------------------------------------------------------------------


@dataclass
class Handoff:
    """Top-level plan-handoff.json record.

    handoff_kind is a constant 'plan' -- any other value is rejected.
    plan_path and plan_completed_at are required non-empty strings.
    breakdown_seeds carries all structured content parsed from plan.md.
    provenance points at the sibling specify handoff (both-set-or-both-null).
    """

    schema_version: str
    handoff_kind: str
    plan_path: str
    plan_completed_at: str
    provenance: Provenance
    breakdown_seeds: BreakdownSeeds

    def __post_init__(self):
        # type: () -> None
        # schema_version lock.
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(
                "Handoff.schema_version must be {0!r}, "
                "got {1!r}".format(SCHEMA_VERSION, self.schema_version)
            )

        # handoff_kind constant.
        if self.handoff_kind != HANDOFF_KIND:
            raise ValueError(
                "Handoff.handoff_kind must be 'plan', "
                "got {0!r}".format(self.handoff_kind)
            )

        _require_nonempty(self.plan_path, "Handoff.plan_path")
        _require_nonempty(self.plan_completed_at, "Handoff.plan_completed_at")

        if not isinstance(self.provenance, Provenance):
            raise ValueError(
                "Handoff.provenance must be a Provenance, "
                "got {0}".format(type(self.provenance).__name__)
            )
        if not isinstance(self.breakdown_seeds, BreakdownSeeds):
            raise ValueError(
                "Handoff.breakdown_seeds must be a BreakdownSeeds, "
                "got {0}".format(type(self.breakdown_seeds).__name__)
            )
