"""handoff_schema -- dataclass schema for the specify -> plan handoff artefact.

Single source of truth for the shape of ``specs/NNN-<slug>/handoff.json``
emitted by ``specify_helper finalize-handoff`` and consumed by
``plan_helper import-handoff``.

Design notes:

- Dataclasses are pure records. No serialization (to_dict / from_dict),
  no rendering, no I/O. Those responsibilities live in the helper command
  layer so this schema stays small, importable, and independently testable.

- Schema-level validation runs in __post_init__ and is mechanical:
    * Required string fields are non-empty after .strip().
    * Enum-typed fields validated against tuples imported from ._schema.
    * Nested records receive isinstance checks at the Handoff level.

- handoff_kind is a CONSTANT "specify" -- any other value is rejected.
- Classification.status is a point-in-time snapshot of the spec.md Status
  line, validated against SPEC_STATUS_ENUM. /specify does NOT flip status
  (it stays "Draft" through /specify; /plan owns the Draft->Approved flip),
  so the handoff is normally emitted with status "Draft". The "user approved
  the content" signal is the command spec calling finalize-handoff on the
  Phase 5.3 approve branch -- it is a runtime flow event, not a state field.

- Constraint conditional requireds (nfr -> quantifier etc.) are NOT
  re-implemented here. That validation already ran in specify's setter;
  re-running it here would create a second source of truth. Optional
  fields on Constraint are transported as-is.

- Type-hint convention: explicit typing.Optional / List / Dict
  (no PEP 604 X | None, no PEP 585 list[str]). Targets Python 3.8+.
  from __future__ import annotations intentionally NOT used so
  __post_init__ introspection sees real type objects.

Stdlib only. No third-party dependencies.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ._schema import (
    AC_SUBSECTION_ENUM,
    CONSTRAINT_KIND_ENUM,
    EARS_VARIANT_ENUM,
    IMPACT_ENUM,
    LIKELIHOOD_ENUM,
    SPEC_STATUS_ENUM,
    SPEC_TYPE_ENUM,
)

# ---------------------------------------------------------------------------
# Schema version constant.
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "1.0"
HANDOFF_KIND = "specify"

# ---------------------------------------------------------------------------
# Allowed values for Provenance.upstream_handoff_kind.
# ---------------------------------------------------------------------------

_VALID_UPSTREAM_HANDOFF_KIND = ("research", "discover")


# ---------------------------------------------------------------------------
# Validation helpers.
# (Copied verbatim from _discover/handoff_schema.py -- intentionally not
# shared across schema modules to keep each schema independently importable
# without cross-dependency.)
# ---------------------------------------------------------------------------


def _require_nonempty(value, field_name):
    """Raise ValueError if value is not a non-empty (post-strip) string."""
    if not isinstance(value, str):
        raise ValueError(
            "{0} must be a string, got {1}".format(field_name, type(value).__name__)
        )
    if value.strip() == "":
        raise ValueError("{0} must be a non-empty string".format(field_name))


def _require_in_enum(value, allowed, field_name):
    """Raise ValueError if value is not in allowed."""
    if value not in allowed:
        raise ValueError(
            "{0} must be one of {1}, got {2!r}".format(
                field_name, sorted(allowed), value
            )
        )


# ---------------------------------------------------------------------------
# Nested record: Classification.
# ---------------------------------------------------------------------------


@dataclass
class Classification:
    """Spec classification block -- number, name, type, status."""

    spec_number: str
    feature_name: str
    feature_slug: str
    spec_type: str
    spec_type_rationale: str
    status: str

    def __post_init__(self):
        _require_nonempty(self.spec_number, "Classification.spec_number")
        _require_nonempty(self.feature_name, "Classification.feature_name")
        _require_nonempty(self.feature_slug, "Classification.feature_slug")
        _require_in_enum(self.spec_type, SPEC_TYPE_ENUM, "Classification.spec_type")
        _require_nonempty(self.spec_type_rationale, "Classification.spec_type_rationale")
        # status is a point-in-time snapshot of the spec.md Status line at
        # handoff-emit time. /specify does NOT flip status -- it stays "Draft"
        # through /specify and is flipped to "Approved" later by a manual edit
        # or by /plan's entry gate. So the handoff is emitted with status
        # "Draft" in the normal flow; validate against the lifecycle enum, do
        # NOT lock to "Approved".
        _require_in_enum(self.status, SPEC_STATUS_ENUM, "Classification.status")


# ---------------------------------------------------------------------------
# Nested records: spec_seeds sub-records.
# ---------------------------------------------------------------------------


@dataclass
class AcceptanceCriterion:
    """One acceptance criterion -- transport shape, no EARS re-validation."""

    ac_id: str
    subsection: str
    ears_variant: str
    statement: str
    verification_command: str
    test_anchor: str
    n_a_reason: str

    def __post_init__(self):
        _require_nonempty(self.ac_id, "AcceptanceCriterion.ac_id")
        _require_in_enum(
            self.subsection, AC_SUBSECTION_ENUM, "AcceptanceCriterion.subsection"
        )
        _require_in_enum(
            self.ears_variant, EARS_VARIANT_ENUM, "AcceptanceCriterion.ears_variant"
        )
        _require_nonempty(self.statement, "AcceptanceCriterion.statement")
        if not isinstance(self.verification_command, str):
            raise ValueError(
                "AcceptanceCriterion.verification_command must be a string, "
                "got {0}".format(type(self.verification_command).__name__)
            )
        if not isinstance(self.test_anchor, str):
            raise ValueError(
                "AcceptanceCriterion.test_anchor must be a string, "
                "got {0}".format(type(self.test_anchor).__name__)
            )
        if not isinstance(self.n_a_reason, str):
            raise ValueError(
                "AcceptanceCriterion.n_a_reason must be a string, "
                "got {0}".format(type(self.n_a_reason).__name__)
            )


@dataclass
class Constraint:
    """One spec constraint.

    kind + content are required. Optional fields (quantifier,
    constitution_ref, protocol, contract_doc_ref) are transported as-is;
    per-kind conditional requireds were enforced by specify's setter and are
    NOT re-validated here (that would be a second source of truth).
    """

    kind: str
    content: str
    quantifier: Optional[str] = None
    constitution_ref: Optional[str] = None
    protocol: Optional[str] = None
    contract_doc_ref: Optional[str] = None

    def __post_init__(self):
        _require_in_enum(self.kind, CONSTRAINT_KIND_ENUM, "Constraint.kind")
        _require_nonempty(self.content, "Constraint.content")
        # Optional fields: if non-None, type-check they are strings.
        for fname in ("quantifier", "constitution_ref", "protocol", "contract_doc_ref"):
            val = getattr(self, fname)
            if val is not None and not isinstance(val, str):
                raise ValueError(
                    "Constraint.{0} must be a string or None, "
                    "got {1}".format(fname, type(val).__name__)
                )


@dataclass
class AffectedArea:
    """One affected area.

    NOTE: specify's shape has NO is_internal_extension_candidate field
    (that is discover-only).
    """

    area: str
    files: List[str]
    impact: str

    def __post_init__(self):
        _require_nonempty(self.area, "AffectedArea.area")
        if not isinstance(self.files, list):
            raise ValueError("AffectedArea.files must be a list")
        for f in self.files:
            if not isinstance(f, str):
                raise ValueError(
                    "AffectedArea.files elements must be strings, "
                    "got {0!r} in area {1!r}".format(type(f).__name__, self.area)
                )
        _require_nonempty(self.impact, "AffectedArea.impact")


@dataclass
class OutOfScopeItem:
    """One out-of-scope entry."""

    content: str
    finding_ref: str

    def __post_init__(self):
        _require_nonempty(self.content, "OutOfScopeItem.content")
        if not isinstance(self.finding_ref, str):
            raise ValueError(
                "OutOfScopeItem.finding_ref must be a string, "
                "got {0}".format(type(self.finding_ref).__name__)
            )


@dataclass
class OpenQuestion:
    """One open question.

    specify's shape: {question_id, content, category_no_dp_reason}.
    NOT discover's shape {question, blocking}.
    """

    question_id: str
    content: str
    category_no_dp_reason: str

    def __post_init__(self):
        _require_nonempty(self.question_id, "OpenQuestion.question_id")
        _require_nonempty(self.content, "OpenQuestion.content")
        if not isinstance(self.category_no_dp_reason, str):
            raise ValueError(
                "OpenQuestion.category_no_dp_reason must be a string, "
                "got {0}".format(type(self.category_no_dp_reason).__name__)
            )


@dataclass
class Risk:
    """One identified risk."""

    risk: str
    likelihood: str
    impact: str
    mitigation: str

    def __post_init__(self):
        _require_nonempty(self.risk, "Risk.risk")
        _require_in_enum(self.likelihood, LIKELIHOOD_ENUM, "Risk.likelihood")
        _require_in_enum(self.impact, IMPACT_ENUM, "Risk.impact")
        _require_nonempty(self.mitigation, "Risk.mitigation")


@dataclass
class SpecSeeds:
    """Spec seeds block -- all structured content /plan needs from /specify."""

    overview: str
    acceptance_criteria: List[AcceptanceCriterion]
    ac_subsection_na: Dict[str, str]
    constraints: List[Constraint]
    affected_areas: List[AffectedArea]
    out_of_scope: List[OutOfScopeItem]
    open_questions: List[OpenQuestion]
    risks: List[Risk]

    def __post_init__(self):
        _require_nonempty(self.overview, "SpecSeeds.overview")
        if not isinstance(self.acceptance_criteria, list):
            raise ValueError("SpecSeeds.acceptance_criteria must be a list")
        if not isinstance(self.ac_subsection_na, dict):
            raise ValueError("SpecSeeds.ac_subsection_na must be a dict")
        for key, val in self.ac_subsection_na.items():
            _require_in_enum(key, AC_SUBSECTION_ENUM, "SpecSeeds.ac_subsection_na key")
            if not isinstance(val, str) or val.strip() == "":
                raise ValueError(
                    "SpecSeeds.ac_subsection_na[{0!r}] must be a non-empty string, "
                    "got {1!r}".format(key, val)
                )
        if not isinstance(self.constraints, list):
            raise ValueError("SpecSeeds.constraints must be a list")
        if not isinstance(self.affected_areas, list):
            raise ValueError("SpecSeeds.affected_areas must be a list")
        if not isinstance(self.out_of_scope, list):
            raise ValueError("SpecSeeds.out_of_scope must be a list")
        if not isinstance(self.open_questions, list):
            raise ValueError("SpecSeeds.open_questions must be a list")
        if not isinstance(self.risks, list):
            raise ValueError("SpecSeeds.risks must be a list")


# ---------------------------------------------------------------------------
# Nested record: Provenance.
# ---------------------------------------------------------------------------


@dataclass
class Provenance:
    """Upstream handoff provenance -- all fields nullable.

    specify may have run without an upstream handoff (manual /specify
    invocation without a prior /discover or /research).
    Maps from specify state["source"].
    """

    upstream_handoff_path: Optional[str] = None
    upstream_handoff_kind: Optional[str] = None
    upstream_completed_at: Optional[str] = None

    def __post_init__(self):
        if self.upstream_handoff_path is not None:
            if not isinstance(self.upstream_handoff_path, str):
                raise ValueError(
                    "Provenance.upstream_handoff_path must be a string or None, "
                    "got {0}".format(type(self.upstream_handoff_path).__name__)
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
        if self.upstream_completed_at is not None:
            if not isinstance(self.upstream_completed_at, str):
                raise ValueError(
                    "Provenance.upstream_completed_at must be a string or None, "
                    "got {0}".format(type(self.upstream_completed_at).__name__)
                )
        # Cross-field: path and kind co-vary. specify's import-handoff sets
        # state["source"]["handoff_path"] and ["handoff_kind"] together (or
        # leaves both None for a manual /specify run). One set without the
        # other signals a producer bug; reject it at parse time.
        if (self.upstream_handoff_path is None) != (self.upstream_handoff_kind is None):
            raise ValueError(
                "Provenance.upstream_handoff_path and upstream_handoff_kind must "
                "both be set or both be None; got path={0!r}, kind={1!r}".format(
                    self.upstream_handoff_path, self.upstream_handoff_kind
                )
            )


# ---------------------------------------------------------------------------
# Nested record: DownstreamLinks.
# ---------------------------------------------------------------------------


@dataclass
class DownstreamLinks:
    """Back-references filled as the artefact flows through the pipeline.

    plan_path is filled by /plan; execute_task_commit_shas accumulates
    SHAs per /implement invocation.
    NOTE: spec_path is NOT duplicated here -- Handoff.spec_path is the
    canonical artifact location; duplication would create two sources.
    """

    plan_path: Optional[str] = None
    execute_task_commit_shas: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.plan_path is not None and not isinstance(self.plan_path, str):
            raise ValueError(
                "DownstreamLinks.plan_path must be a string or None, "
                "got {0}".format(type(self.plan_path).__name__)
            )
        if not isinstance(self.execute_task_commit_shas, list):
            raise ValueError(
                "DownstreamLinks.execute_task_commit_shas must be a list"
            )


# ---------------------------------------------------------------------------
# Top-level Handoff record.
# ---------------------------------------------------------------------------


@dataclass
class Handoff:
    """Top-level specify handoff.json record.

    handoff_kind is a constant 'specify' -- any other value is rejected.
    Classification.status is enum-validated (normally 'Draft' at emit time;
    /specify does not flip it).

    Owns isinstance checks for all nested record fields in __post_init__.
    No cross-field invariants beyond the constant locks (specify has no
    D-mirror / G-mirror / outcome complexity of the discover schema).
    """

    schema_version: str
    handoff_kind: str
    spec_path: str
    specify_completed_at: str
    classification: Classification
    spec_seeds: SpecSeeds
    provenance: Provenance
    downstream_links: DownstreamLinks

    def __post_init__(self):
        # schema_version lock.
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(
                "Handoff.schema_version must be {0!r}, "
                "got {1!r}".format(SCHEMA_VERSION, self.schema_version)
            )

        # handoff_kind constant.
        if self.handoff_kind != HANDOFF_KIND:
            raise ValueError(
                "Handoff.handoff_kind must be 'specify', "
                "got {0!r}".format(self.handoff_kind)
            )

        _require_nonempty(self.spec_path, "Handoff.spec_path")
        _require_nonempty(self.specify_completed_at, "Handoff.specify_completed_at")

        if not isinstance(self.classification, Classification):
            raise ValueError(
                "Handoff.classification must be a Classification, "
                "got {0}".format(type(self.classification).__name__)
            )
        if not isinstance(self.spec_seeds, SpecSeeds):
            raise ValueError(
                "Handoff.spec_seeds must be a SpecSeeds, "
                "got {0}".format(type(self.spec_seeds).__name__)
            )
        if not isinstance(self.provenance, Provenance):
            raise ValueError(
                "Handoff.provenance must be a Provenance, "
                "got {0}".format(type(self.provenance).__name__)
            )
        if not isinstance(self.downstream_links, DownstreamLinks):
            raise ValueError(
                "Handoff.downstream_links must be a DownstreamLinks, "
                "got {0}".format(type(self.downstream_links).__name__)
            )
