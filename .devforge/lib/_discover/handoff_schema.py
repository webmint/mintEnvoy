"""handoff_schema -- dataclass schema for the discover -> specify -> plan -> /implement handoff artefact.

Single source of truth for the shape of `<topic-slug>.handoff.json` emitted by
`discover_helper finalize-handoff` (Step 3) and consumed by
`specify_helper import-handoff` (Step 4).

Design notes:

- Dataclasses are pure records. No serialization (to_dict / from_dict),
  no rendering, no I/O. Those responsibilities live in the helper command
  layer so this schema stays small, importable, and independently testable.

- Schema-level validation runs in __post_init__ and is mechanical:
    * Required string fields are non-empty after .strip().
    * Enum-typed fields validated against module-level frozenset constants.
    * Conditional requireds enforced at construction (Constraint kind rules,
      D-mirror verdict-flip, G-mirror internal-cite, Outcome cross-field
      invariants).

- handoff_kind is a CONSTANT "discover" -- any other value is rejected.
- spec_seeds.spec_type_hint is a CONSTANT "greenfield_feature".

- Complexity axes are DERIVED from source fields (effort_estimate,
  overall_fit, derisk_count) and validated against any manually-set value.
  PlanSeeds.__post_init__ computes and validates; caller may not supply
  arbitrary values.

- Type-hint convention: explicit typing.Optional / List / Dict
  (no PEP 604 X | None, no PEP 585 list[str]). Targets Python 3.8+.
  from __future__ import annotations intentionally NOT used so
  __post_init__ introspection sees real type objects.

Stdlib only. No third-party dependencies.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional

# ---------------------------------------------------------------------------
# Schema version constant.
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "1.1"
HANDOFF_KIND = "discover"

# ---------------------------------------------------------------------------
# Enum allow-sets.
# ---------------------------------------------------------------------------

_VALID_CONSTRAINT_KIND = frozenset({"nfr", "constitution_anchor", "external_system"})
_VALID_LIKELIHOOD = frozenset({"Low", "Med", "High"})
_VALID_IMPACT_LMH = frozenset({"Low", "Med", "High"})
_VALID_COMPLEXITY = frozenset({"Low", "Med", "High"})
_VALID_DESIGN_OPTION_ID = frozenset({"A", "B", "C", "D", "E", "F", "G", "H"})
_VALID_BVB_RECOMMENDATION = frozenset({"Build", "Buy", "Hybrid"})
_VALID_CITED_PATTERN_KIND = frozenset({"library", "product", "pattern"})
_VALID_OVERALL_FIT = frozenset({"Good", "Acceptable", "Strained", "Misfit"})
_VALID_EFFORT_ESTIMATE = frozenset({"Low", "Medium", "High", "Major refactor required"})
_VALID_VERDICT = frozenset({"Worth pursuing", "Promising with caveats", "Reconsider"})
_VALID_DIMENSION_STATE = frozenset({"Clear", "Partial", "Missing"})
_VALID_DESIGN_OPTION_SHIPPED_ID = frozenset({"A", "B", "C", "D", "E", "F", "G", "H", "hybrid", "none"})
_VALID_BUILD_VS_BUY_ACTUAL = frozenset({"Build", "Buy", "Hybrid", "none"})
_VALID_CONFIDENCE_GRADE = frozenset({"HIGH", "MEDIUM", "LOW"})

# Regex: letter prefix like "A:" or "B:" at start of name (reject).
_LETTER_PREFIX_RE = re.compile(r'^[A-H]\s*:')

# Commit SHA format: 7-40 hex chars.
_COMMIT_SHA_RE = re.compile(r'^[0-9a-f]{7,40}$')


# ---------------------------------------------------------------------------
# Validation helpers.
# ---------------------------------------------------------------------------


def _require_nonempty(value, field_name):
    """Raise ValueError if value is not a non-empty (post-strip) string."""
    if not isinstance(value, str):
        raise ValueError(
            f"{field_name} must be a string, got {type(value).__name__}"
        )
    if value.strip() == "":
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_in_enum(value, allowed, field_name):
    """Raise ValueError if value is not in allowed."""
    if value not in allowed:
        raise ValueError(
            f"{field_name} must be one of {sorted(allowed)}, got {value!r}"
        )


# ---------------------------------------------------------------------------
# Discover-specific module-level predicates.
# ---------------------------------------------------------------------------


def _has_internal_prior_art(cited_patterns):
    # type: (List) -> bool
    """Return True when any CitedPattern.is_internal is True."""
    return any(cp.is_internal for cp in cited_patterns)


def _rationale_cites_internal(rationale, cited_patterns):
    # type: (str, List) -> bool
    """Return True when rationale contains at least one internal: path from cited_patterns.

    G-mirror check: when any prior-art entry is internal, the recommended
    rationale must cite that path so the 'extend existing' framing is forced.
    """
    for cp in cited_patterns:
        if cp.is_internal and cp.source in rationale:
            return True
    return False


def _is_strained_or_misfit(overall_fit, effort_estimate):
    # type: (str, str) -> bool
    """Return True when fit is Strained/Misfit OR effort is Major refactor required.

    D-mirror gating predicate. When True, verdict MUST be Reconsider unless
    override_recorded is True.
    """
    return overall_fit in {"Strained", "Misfit"} or effort_estimate == "Major refactor required"


def _compute_complexity_changes(effort_estimate):
    # type: (str) -> str
    """Map effort_estimate (Low/Medium/High/Major refactor required) to complexity axis value.

    Low -> Low, Medium -> Med, High -> High, Major refactor required -> High.
    Note the intentional mismatch: effort_estimate uses 'Medium'; complexity uses 'Med'.
    """
    mapping = {
        "Low": "Low",
        "Medium": "Med",
        "High": "High",
        "Major refactor required": "High",
    }
    return mapping[effort_estimate]


def _compute_complexity_risk(overall_fit):
    # type: (str) -> str
    """Map overall_fit to complexity risk axis value.

    Good -> Low, Acceptable -> Med, Strained -> High, Misfit -> High.
    """
    mapping = {
        "Good": "Low",
        "Acceptable": "Med",
        "Strained": "High",
        "Misfit": "High",
    }
    return mapping[overall_fit]


def _compute_complexity_verify_cost(derisk_count):
    # type: (int) -> str
    """Map derisk_count to complexity verify_cost axis value.

    <=2 -> Low, 3-5 -> Med, >5 -> High.
    """
    if derisk_count <= 2:
        return "Low"
    if derisk_count <= 5:
        return "Med"
    return "High"


def compute_confidence_grade(
    verdict_held,               # type: bool
    matches_recommendation,     # type: bool
    matches_build_vs_buy_recommendation,  # type: bool
    internal_extension_followed,  # type: Optional[bool]
):
    # type: (...) -> str
    """Compute the expected confidence grade from outcome match flags.

    This is the single source of truth for grade derivation; Outcome.__post_init__
    asserts the stored confidence_grade matches. Exported for append-outcome to call.

    Grade rules (checked in priority order):
    - verdict_held AND matches_recommendation AND matches_build_vs_buy_recommendation
      AND internal_extension_followed in {True, None} -> HIGH
    - verdict_held AND any one of the three match flags is false -> MEDIUM
    - verdict_held is False -> LOW
    """
    if not verdict_held:
        return "LOW"
    all_match = (
        matches_recommendation
        and matches_build_vs_buy_recommendation
        and internal_extension_followed in (True, None)
    )
    if all_match:
        return "HIGH"
    return "MEDIUM"


# ---------------------------------------------------------------------------
# Nested record: Intent.
# ---------------------------------------------------------------------------


@dataclass
class Intent:
    """Discover intent block -- feature concept, topic, topic slug, scope summary, and verbatim prompt.

    verbatim_prompt (added v1.1): the raw user prompt text, unmodified.

    Back-compat (OQ-1 RESOLVED): the field defaults to None so that pre-v1.1
    handoff.json records loaded via _dict_to_dataclass do not raise on
    construction (absent field -> None -> tolerate-missing-on-read branch).
    When non-None, it must be non-empty after strip (same _require_nonempty
    idiom as scope_summary). New handoffs always supply a non-empty string via
    _build_handoff_from_state, which guards on the state value before
    constructing Intent.
    """

    feature_concept: str
    topic: str
    topic_slug: str
    scope_summary: Optional[str] = None
    verbatim_prompt: Optional[str] = None

    def __post_init__(self):
        _require_nonempty(self.feature_concept, "Intent.feature_concept")
        _require_nonempty(self.topic, "Intent.topic")
        _require_nonempty(self.topic_slug, "Intent.topic_slug")
        if self.scope_summary is not None:
            _require_nonempty(self.scope_summary, "Intent.scope_summary")
        if self.verbatim_prompt is not None:
            _require_nonempty(self.verbatim_prompt, "Intent.verbatim_prompt")


# ---------------------------------------------------------------------------
# Nested records: spec_seeds sub-records.
# ---------------------------------------------------------------------------


@dataclass
class Constraint:
    """One spec constraint, using Gap-A taxonomy.

    kind nfr requires quantifier.
    kind constitution_anchor requires constitution_ref.
    kind external_system requires protocol OR contract_doc_ref.
    """

    kind: str
    content: str
    quantifier: Optional[str] = None
    constitution_ref: Optional[str] = None
    protocol: Optional[str] = None
    contract_doc_ref: Optional[str] = None

    def __post_init__(self):
        _require_in_enum(self.kind, _VALID_CONSTRAINT_KIND, "Constraint.kind")
        _require_nonempty(self.content, "Constraint.content")

        if self.kind == "nfr":
            if not self.quantifier or not self.quantifier.strip():
                raise ValueError(
                    "Constraint.quantifier is required when kind='nfr'"
                )

        if self.kind == "constitution_anchor":
            if not self.constitution_ref or not self.constitution_ref.strip():
                raise ValueError(
                    "Constraint.constitution_ref is required when kind='constitution_anchor'"
                )

        if self.kind == "external_system":
            proto_ok = self.protocol and self.protocol.strip()
            ref_ok = self.contract_doc_ref and self.contract_doc_ref.strip()
            if not proto_ok and not ref_ok:
                raise ValueError(
                    "Constraint.protocol OR Constraint.contract_doc_ref is required "
                    "when kind='external_system'"
                )


@dataclass
class AffectedArea:
    """One affected area -- may flag an internal extension candidate."""

    area: str
    files: List[str]
    impact: str
    is_internal_extension_candidate: bool = False

    def __post_init__(self):
        _require_nonempty(self.area, "AffectedArea.area")
        _require_nonempty(self.impact, "AffectedArea.impact")
        if not isinstance(self.files, list):
            raise ValueError("AffectedArea.files must be a list")
        for f in self.files:
            if not isinstance(f, str):
                raise ValueError(
                    f"AffectedArea.files elements must be strings, "
                    f"got {type(f).__name__!r} in area {self.area!r}"
                )
        if not isinstance(self.is_internal_extension_candidate, bool):
            raise ValueError(
                f"AffectedArea.is_internal_extension_candidate must be a bool, "
                f"got {type(self.is_internal_extension_candidate).__name__}"
            )


@dataclass
class Risk:
    """One identified risk."""

    risk: str
    likelihood: str   # one of _VALID_LIKELIHOOD
    impact: str       # one of _VALID_IMPACT_LMH
    mitigation: str

    def __post_init__(self):
        _require_nonempty(self.risk, "Risk.risk")
        _require_in_enum(self.likelihood, _VALID_LIKELIHOOD, "Risk.likelihood")
        _require_in_enum(self.impact, _VALID_IMPACT_LMH, "Risk.impact")
        _require_nonempty(self.mitigation, "Risk.mitigation")


@dataclass
class OpenQuestion:
    """One open question that may block progress."""

    question: str
    blocking: bool

    def __post_init__(self):
        _require_nonempty(self.question, "OpenQuestion.question")
        if not isinstance(self.blocking, bool):
            raise ValueError(
                f"OpenQuestion.blocking must be a bool, got {type(self.blocking).__name__}"
            )


@dataclass
class SpecSeeds:
    """Spec-seeds block -- all inputs /specify needs from /discover.

    spec_type_hint is a constant 'greenfield_feature'; any other value is rejected.
    """

    spec_type_hint: str
    constraints: List[Constraint]
    affected_areas: List[AffectedArea]
    risks: List[Risk]
    open_questions: List[OpenQuestion]

    def __post_init__(self):
        if self.spec_type_hint != "greenfield_feature":
            raise ValueError(
                f"SpecSeeds.spec_type_hint must be 'greenfield_feature', "
                f"got {self.spec_type_hint!r}"
            )
        if not isinstance(self.constraints, list):
            raise ValueError("SpecSeeds.constraints must be a list")
        if not isinstance(self.affected_areas, list):
            raise ValueError("SpecSeeds.affected_areas must be a list")
        if not isinstance(self.risks, list):
            raise ValueError("SpecSeeds.risks must be a list")
        if not isinstance(self.open_questions, list):
            raise ValueError("SpecSeeds.open_questions must be a list")


# ---------------------------------------------------------------------------
# Plan seeds sub-records.
# ---------------------------------------------------------------------------


@dataclass
class DesignOption:
    """One design option considered during discovery.

    id must be one of A-H (auto-assigned by helper, 8-cap).
    name must NOT start with a letter prefix like 'A:' or 'B:' (helper assigns letter).
    complexity uses Med (not Medium) -- matches existing setter enum.
    """

    id: str                    # one of _VALID_DESIGN_OPTION_ID
    name: str
    shape: str
    pros: List[str]
    cons: List[str]
    complexity: str            # one of _VALID_COMPLEXITY

    def __post_init__(self):
        _require_in_enum(self.id, _VALID_DESIGN_OPTION_ID, "DesignOption.id")
        _require_nonempty(self.name, "DesignOption.name")
        if _LETTER_PREFIX_RE.match(self.name):
            raise ValueError(
                f"DesignOption.name must not start with a letter prefix like 'A:' "
                f"(helper auto-assigns the letter); got {self.name!r}"
            )
        _require_nonempty(self.shape, "DesignOption.shape")
        if not isinstance(self.pros, list):
            raise ValueError("DesignOption.pros must be a list")
        if not isinstance(self.cons, list):
            raise ValueError("DesignOption.cons must be a list")
        _require_in_enum(self.complexity, _VALID_COMPLEXITY, "DesignOption.complexity")


@dataclass
class BuildVsBuy:
    """Build-vs-buy analysis block."""

    recommendation: str   # one of _VALID_BVB_RECOMMENDATION
    build_path: str
    buy_path: str
    reasoning: str

    def __post_init__(self):
        _require_in_enum(self.recommendation, _VALID_BVB_RECOMMENDATION, "BuildVsBuy.recommendation")
        _require_nonempty(self.build_path, "BuildVsBuy.build_path")
        _require_nonempty(self.buy_path, "BuildVsBuy.buy_path")
        _require_nonempty(self.reasoning, "BuildVsBuy.reasoning")


@dataclass
class CitedPattern:
    """One cited canonical pattern -- internal or external.

    is_internal equivalence: is_internal == True iff source starts with 'internal:'.
    """

    reference: str
    kind: str             # one of _VALID_CITED_PATTERN_KIND
    source: str
    relevance: str
    is_internal: bool

    def __post_init__(self):
        _require_nonempty(self.reference, "CitedPattern.reference")
        _require_in_enum(self.kind, _VALID_CITED_PATTERN_KIND, "CitedPattern.kind")
        _require_nonempty(self.source, "CitedPattern.source")
        _require_nonempty(self.relevance, "CitedPattern.relevance")
        if not isinstance(self.is_internal, bool):
            raise ValueError(
                f"CitedPattern.is_internal must be a bool, got {type(self.is_internal).__name__}"
            )
        # Equivalence check: is_internal must match whether source starts with 'internal:'.
        source_is_internal = self.source.startswith("internal:")
        if self.is_internal != source_is_internal:
            raise ValueError(
                f"CitedPattern.is_internal={self.is_internal!r} does not match "
                f"source prefix (source={self.source!r}); "
                f"is_internal must be True iff source starts with 'internal:'"
            )


@dataclass
class Complexity:
    """Complexity assessment with three axes -- all deterministically derived."""

    changes: str       # one of _VALID_COMPLEXITY
    risk: str          # one of _VALID_COMPLEXITY
    verify_cost: str   # one of _VALID_COMPLEXITY

    def __post_init__(self):
        _require_in_enum(self.changes, _VALID_COMPLEXITY, "Complexity.changes")
        _require_in_enum(self.risk, _VALID_COMPLEXITY, "Complexity.risk")
        _require_in_enum(self.verify_cost, _VALID_COMPLEXITY, "Complexity.verify_cost")


@dataclass
class PlanSeeds:
    """Plan-seeds block -- design options, build-vs-buy, complexity, cited patterns.

    Complexity axes are validated against deterministic derivation from
    overall_fit + effort_estimate + derisk_count (passed as constructor args).
    These three source fields are stored for auditability but the derived
    Complexity object is validated against them in __post_init__.

    G-mirror: when any cited_canonical_patterns[].is_internal is True,
    recommended_option_rationale must contain at least one of those internal: paths.

    D-mirror verdict gate is enforced at Handoff level (needs discovery_block context).
    """

    design_options: List[DesignOption]
    build_vs_buy: BuildVsBuy
    cited_canonical_patterns: List[CitedPattern]
    complexity: Complexity
    recommended_option_id: Optional[str]
    recommended_option_rationale: str

    # Source fields used to validate complexity derivation.
    # These are the original values from DiscoveryBlock.
    # No defaults: callers MUST supply these so the derivation check is unconditional.
    _effort_estimate: str = field(repr=False)
    _overall_fit: str = field(repr=False)
    _derisk_count: int = field(repr=False)

    def __post_init__(self):
        if not isinstance(self.design_options, list):
            raise ValueError("PlanSeeds.design_options must be a list")
        if not isinstance(self.cited_canonical_patterns, list):
            raise ValueError("PlanSeeds.cited_canonical_patterns must be a list")

        # Distinct design option ids.
        seen_ids = set()  # type: ignore
        for opt in self.design_options:
            if opt.id in seen_ids:
                raise ValueError(
                    f"PlanSeeds.design_options contains duplicate id={opt.id!r}"
                )
            seen_ids.add(opt.id)

        _require_nonempty(self.recommended_option_rationale, "PlanSeeds.recommended_option_rationale")

        # Complexity derivation check (unconditional -- source fields are required).
        expected_changes = _compute_complexity_changes(self._effort_estimate)
        expected_risk = _compute_complexity_risk(self._overall_fit)
        expected_verify_cost = _compute_complexity_verify_cost(self._derisk_count)
        if self.complexity.changes != expected_changes:
            raise ValueError(
                f"PlanSeeds.complexity.changes={self.complexity.changes!r} does not match "
                f"derived value={expected_changes!r} for effort_estimate={self._effort_estimate!r}"
            )
        if self.complexity.risk != expected_risk:
            raise ValueError(
                f"PlanSeeds.complexity.risk={self.complexity.risk!r} does not match "
                f"derived value={expected_risk!r} for overall_fit={self._overall_fit!r}"
            )
        if self.complexity.verify_cost != expected_verify_cost:
            raise ValueError(
                f"PlanSeeds.complexity.verify_cost={self.complexity.verify_cost!r} does not match "
                f"derived value={expected_verify_cost!r} for derisk_count={self._derisk_count}"
            )

        # G-mirror: rationale must cite internal paths when internal prior art exists.
        if _has_internal_prior_art(self.cited_canonical_patterns):
            if not _rationale_cites_internal(
                self.recommended_option_rationale, self.cited_canonical_patterns
            ):
                internal_sources = [
                    cp.source for cp in self.cited_canonical_patterns if cp.is_internal
                ]
                raise ValueError(
                    f"PlanSeeds.recommended_option_rationale must cite at least one internal: "
                    f"path when cited_canonical_patterns contains internal entries. "
                    f"Internal sources: {internal_sources!r}. "
                    f"Rationale={self.recommended_option_rationale!r}"
                )

    def _validate_recommended_option(self, verdict):
        # type: (str) -> None
        """Validate recommended_option_id against design_options and verdict.

        Called by Handoff.__post_init__ with verdict context.
        """
        if verdict in {"Worth pursuing", "Promising with caveats"}:
            if not self.design_options:
                raise ValueError(
                    f"PlanSeeds.design_options must be non-empty when verdict={verdict!r}"
                )
            if self.recommended_option_id is None:
                raise ValueError(
                    f"PlanSeeds.recommended_option_id must be non-None when verdict={verdict!r}"
                )
            option_ids = {opt.id for opt in self.design_options}
            if self.recommended_option_id not in option_ids:
                raise ValueError(
                    f"PlanSeeds.recommended_option_id={self.recommended_option_id!r} "
                    f"does not match any design_options[].id. "
                    f"Available ids: {sorted(option_ids)!r}"
                )
        # When verdict is Reconsider: recommended_option_id may be None.


# ---------------------------------------------------------------------------
# Discovery block sub-records.
# ---------------------------------------------------------------------------


@dataclass
class DimensionRecord:
    """Per-dimension scoping record from memo.dimensions."""

    state: str              # one of _VALID_DIMENSION_STATE
    turns: int
    value: Optional[str] = None

    def __post_init__(self):
        _require_in_enum(self.state, _VALID_DIMENSION_STATE, "DimensionRecord.state")
        if not isinstance(self.turns, int):
            raise ValueError(
                f"DimensionRecord.turns must be an int, got {type(self.turns).__name__}"
            )
        if self.turns < 0:
            raise ValueError(f"DimensionRecord.turns must be >= 0, got {self.turns}")
        # value may be None only when state is Missing.
        if self.state != "Missing" and self.value is None:
            raise ValueError(
                f"DimensionRecord.value must be non-None when state={self.state!r}"
            )
        if self.value is not None:
            _require_nonempty(self.value, "DimensionRecord.value")


@dataclass
class MemoDimensions:
    """Verbatim memo.dimensions block -- 8 scoping dimensions."""

    functional_scope: DimensionRecord
    users: DimensionRecord
    inputs_outputs: DimensionRecord
    integration_points: DimensionRecord
    constraints: DimensionRecord
    non_goals: DimensionRecord
    success_criteria: DimensionRecord
    edge_cases: DimensionRecord

    def __post_init__(self):
        expected_types = [
            ("functional_scope", self.functional_scope),
            ("users", self.users),
            ("inputs_outputs", self.inputs_outputs),
            ("integration_points", self.integration_points),
            ("constraints", self.constraints),
            ("non_goals", self.non_goals),
            ("success_criteria", self.success_criteria),
            ("edge_cases", self.edge_cases),
        ]
        for fname, fval in expected_types:
            if not isinstance(fval, DimensionRecord):
                raise ValueError(
                    f"MemoDimensions.{fname} must be a DimensionRecord, "
                    f"got {type(fval).__name__}"
                )


@dataclass
class Gap:
    """One gap recorded from memo.gaps or Phase 1 partial exit."""

    dimension: str
    description: str

    def __post_init__(self):
        _require_nonempty(self.dimension, "Gap.dimension")
        _require_nonempty(self.description, "Gap.description")


@dataclass
class FitAssessment:
    """Per-touchpoint fit assessment from Phase 2.2."""

    touchpoint: str
    user_expected: str
    reality: str
    effort: str             # one of _VALID_EFFORT_ESTIMATE
    blockers: List[str]

    def __post_init__(self):
        _require_nonempty(self.touchpoint, "FitAssessment.touchpoint")
        _require_nonempty(self.user_expected, "FitAssessment.user_expected")
        _require_nonempty(self.reality, "FitAssessment.reality")
        _require_in_enum(self.effort, _VALID_EFFORT_ESTIMATE, "FitAssessment.effort")
        if not isinstance(self.blockers, list):
            raise ValueError("FitAssessment.blockers must be a list")


@dataclass
class DiscoveryBlock:
    """Discover-only fields preserved for downstream auditability.

    overall_fit + effort_estimate drive D-mirror verdict gate (checked at
    Handoff level). memo_dimensions preserves verbatim 8-dim scoping context.
    """

    overall_fit: str             # one of _VALID_OVERALL_FIT
    effort_estimate: str         # one of _VALID_EFFORT_ESTIMATE
    fit_rationale: str
    fit_assessments: List[FitAssessment]
    verdict: str                 # one of _VALID_VERDICT
    override_recorded: bool
    memo_dimensions: MemoDimensions
    references: List[str]
    gaps: List[Gap]

    def __post_init__(self):
        _require_in_enum(self.overall_fit, _VALID_OVERALL_FIT, "DiscoveryBlock.overall_fit")
        _require_in_enum(self.effort_estimate, _VALID_EFFORT_ESTIMATE, "DiscoveryBlock.effort_estimate")
        _require_nonempty(self.fit_rationale, "DiscoveryBlock.fit_rationale")
        if not isinstance(self.fit_assessments, list):
            raise ValueError("DiscoveryBlock.fit_assessments must be a list")
        _require_in_enum(self.verdict, _VALID_VERDICT, "DiscoveryBlock.verdict")
        if not isinstance(self.override_recorded, bool):
            raise ValueError(
                f"DiscoveryBlock.override_recorded must be a bool, "
                f"got {type(self.override_recorded).__name__}"
            )
        if not isinstance(self.memo_dimensions, MemoDimensions):
            raise ValueError(
                f"DiscoveryBlock.memo_dimensions must be a MemoDimensions, "
                f"got {type(self.memo_dimensions).__name__}"
            )
        if not isinstance(self.references, list):
            raise ValueError("DiscoveryBlock.references must be a list")
        if not isinstance(self.gaps, list):
            raise ValueError("DiscoveryBlock.gaps must be a list")

        # D-mirror: strained/misfit or major-refactor requires Reconsider unless
        # override_recorded is True.
        if _is_strained_or_misfit(self.overall_fit, self.effort_estimate):
            if self.verdict != "Reconsider" and not self.override_recorded:
                raise ValueError(
                    f"DiscoveryBlock.verdict must be 'Reconsider' when overall_fit="
                    f"{self.overall_fit!r} or effort_estimate={self.effort_estimate!r} "
                    f"(D-mirror invariant). Set override_recorded=True to permit other verdicts."
                )


# ---------------------------------------------------------------------------
# Outcome block.
# ---------------------------------------------------------------------------


@dataclass
class Outcome:
    """Outcome block -- filled by append-outcome after feature ships.

    matches_recommendation and matches_build_vs_buy_recommendation are
    helper-computed from (design_option_shipped_id, recommended_option_id,
    build_vs_buy_actual, build_vs_buy.recommendation). The stored values are
    validated against those computations.

    verdict_held is helper-computed. confidence_grade is derived from the
    combination of verdict_held and match flags via compute_confidence_grade().
    """

    design_option_shipped_id: str   # one of _VALID_DESIGN_OPTION_SHIPPED_ID
    design_option_shipped_summary: str
    matches_recommendation: bool
    build_vs_buy_actual: str        # one of _VALID_BUILD_VS_BUY_ACTUAL
    matches_build_vs_buy_recommendation: bool
    internal_extension_followed: Optional[bool]
    verdict_held: bool
    shipped_commit_sha: Optional[str]
    shipped_date: str               # ISO-8601
    confidence_grade: str           # one of _VALID_CONFIDENCE_GRADE
    delta_from_recommendation: Optional[str] = None

    def __post_init__(self):
        _require_in_enum(
            self.design_option_shipped_id,
            _VALID_DESIGN_OPTION_SHIPPED_ID,
            "Outcome.design_option_shipped_id",
        )
        _require_nonempty(self.design_option_shipped_summary, "Outcome.design_option_shipped_summary")
        if not isinstance(self.matches_recommendation, bool):
            raise ValueError(
                f"Outcome.matches_recommendation must be a bool, "
                f"got {type(self.matches_recommendation).__name__}"
            )
        _require_in_enum(self.build_vs_buy_actual, _VALID_BUILD_VS_BUY_ACTUAL, "Outcome.build_vs_buy_actual")
        if not isinstance(self.matches_build_vs_buy_recommendation, bool):
            raise ValueError(
                f"Outcome.matches_build_vs_buy_recommendation must be a bool, "
                f"got {type(self.matches_build_vs_buy_recommendation).__name__}"
            )
        if self.internal_extension_followed is not None and not isinstance(
            self.internal_extension_followed, bool
        ):
            raise ValueError(
                f"Outcome.internal_extension_followed must be bool or None, "
                f"got {type(self.internal_extension_followed).__name__}"
            )
        if not isinstance(self.verdict_held, bool):
            raise ValueError(
                f"Outcome.verdict_held must be a bool, got {type(self.verdict_held).__name__}"
            )
        if self.shipped_commit_sha is not None:
            if not _COMMIT_SHA_RE.match(self.shipped_commit_sha):
                raise ValueError(
                    f"Outcome.shipped_commit_sha must be 7-40 lowercase hex chars, "
                    f"got {self.shipped_commit_sha!r}"
                )
        if self.design_option_shipped_id == "none" and self.shipped_commit_sha is not None:
            raise ValueError(
                "Outcome.shipped_commit_sha must be None when design_option_shipped_id='none' "
                "(nothing shipped — a SHA is contradictory)"
            )
        _require_nonempty(self.shipped_date, "Outcome.shipped_date")
        _require_in_enum(self.confidence_grade, _VALID_CONFIDENCE_GRADE, "Outcome.confidence_grade")

        # delta_from_recommendation required when any match flag is False.
        needs_delta = (
            not self.matches_recommendation
            or not self.matches_build_vs_buy_recommendation
            or self.internal_extension_followed is False
        )
        if needs_delta and (
            self.delta_from_recommendation is None
            or not self.delta_from_recommendation.strip()
        ):
            raise ValueError(
                "Outcome.delta_from_recommendation must be non-empty when any of "
                "(matches_recommendation, matches_build_vs_buy_recommendation, "
                "internal_extension_followed) is False"
            )

    def _validate_computed_fields(self, plan_seeds, discovery_block):
        # type: (PlanSeeds, DiscoveryBlock) -> None
        """Validate helper-computed fields against their derivation sources.

        Called by Handoff.__post_init__ with plan_seeds and discovery_block context.
        """
        # Validate matches_recommendation.
        expected_matches = (
            self.design_option_shipped_id == plan_seeds.recommended_option_id
        )
        if self.matches_recommendation != expected_matches:
            raise ValueError(
                f"Outcome.matches_recommendation={self.matches_recommendation!r} does not match "
                f"derived value={expected_matches!r} "
                f"(design_option_shipped_id={self.design_option_shipped_id!r}, "
                f"recommended_option_id={plan_seeds.recommended_option_id!r})"
            )

        # Validate matches_build_vs_buy_recommendation.
        expected_bvb_match = (
            self.build_vs_buy_actual == plan_seeds.build_vs_buy.recommendation
        )
        if self.matches_build_vs_buy_recommendation != expected_bvb_match:
            raise ValueError(
                f"Outcome.matches_build_vs_buy_recommendation={self.matches_build_vs_buy_recommendation!r} "
                f"does not match derived value={expected_bvb_match!r} "
                f"(build_vs_buy_actual={self.build_vs_buy_actual!r}, "
                f"recommendation={plan_seeds.build_vs_buy.recommendation!r})"
            )

        # Validate internal_extension_followed conditional.
        has_internal = _has_internal_prior_art(plan_seeds.cited_canonical_patterns)
        if not has_internal and self.internal_extension_followed is not None:
            raise ValueError(
                "Outcome.internal_extension_followed must be None when "
                "plan_seeds.cited_canonical_patterns has no internal entries"
            )
        if has_internal and self.internal_extension_followed is None:
            raise ValueError(
                "Outcome.internal_extension_followed must be True or False (not None) when "
                "plan_seeds.cited_canonical_patterns has >= 1 internal entry"
            )

        # Validate verdict_held: False when verdict was Reconsider and shipped_commit_sha
        # is non-None, OR when verdict was Worth pursuing and shipped_id is 'none'.
        verdict = discovery_block.verdict
        expected_verdict_held = True
        if verdict == "Reconsider" and self.shipped_commit_sha is not None:
            expected_verdict_held = False
        elif verdict in {"Worth pursuing", "Promising with caveats"} and self.design_option_shipped_id == "none":
            expected_verdict_held = False
        if self.verdict_held != expected_verdict_held:
            raise ValueError(
                f"Outcome.verdict_held={self.verdict_held!r} does not match "
                f"derived value={expected_verdict_held!r} "
                f"(verdict={verdict!r}, "
                f"design_option_shipped_id={self.design_option_shipped_id!r}, "
                f"shipped_commit_sha={self.shipped_commit_sha!r})"
            )

        # Validate confidence_grade.
        expected_grade = compute_confidence_grade(
            verdict_held=self.verdict_held,
            matches_recommendation=self.matches_recommendation,
            matches_build_vs_buy_recommendation=self.matches_build_vs_buy_recommendation,
            internal_extension_followed=self.internal_extension_followed,
        )
        if self.confidence_grade != expected_grade:
            raise ValueError(
                f"Outcome.confidence_grade={self.confidence_grade!r} does not match "
                f"derived grade={expected_grade!r} for "
                f"(verdict_held={self.verdict_held!r}, "
                f"matches_recommendation={self.matches_recommendation!r}, "
                f"matches_build_vs_buy_recommendation={self.matches_build_vs_buy_recommendation!r}, "
                f"internal_extension_followed={self.internal_extension_followed!r})"
            )


# ---------------------------------------------------------------------------
# Downstream links.
# ---------------------------------------------------------------------------


@dataclass
class DownstreamLinks:
    """Back-references filled as the artefact flows through the pipeline."""

    spec_path: Optional[str] = None
    plan_path: Optional[str] = None
    execute_task_commit_shas: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not isinstance(self.execute_task_commit_shas, list):
            raise ValueError("DownstreamLinks.execute_task_commit_shas must be a list")


# ---------------------------------------------------------------------------
# Top-level Handoff record.
# ---------------------------------------------------------------------------


@dataclass
class Handoff:
    """Top-level discover handoff.json record.

    handoff_kind is a constant 'discover' -- any other value is rejected.

    Owns all cross-field invariant validation in __post_init__:
    - D-mirror enforced at DiscoveryBlock level (verdict gate).
    - G-mirror enforced at PlanSeeds level (rationale cites internal).
    - recommended_option_id vs design_options vs verdict validated here
      (requires both plan_seeds and discovery_block.verdict).
    - Outcome computed-field validation (matches_recommendation,
      matches_build_vs_buy_recommendation, internal_extension_followed,
      verdict_held, confidence_grade) validated here.
    """

    schema_version: str
    handoff_kind: str
    report_path: str
    discover_completed_at: str
    intent: Intent
    spec_seeds: SpecSeeds
    plan_seeds: PlanSeeds
    discovery_block: DiscoveryBlock
    downstream_links: DownstreamLinks
    outcome: Optional[Outcome] = None

    def __post_init__(self):
        # schema_version check: accept all shipped versions:
        # 1.0 (original) and 1.1 (added verbatim_prompt).
        _ACCEPTED_SCHEMA_VERSIONS = frozenset({"1.0", "1.1"})
        if self.schema_version not in _ACCEPTED_SCHEMA_VERSIONS:
            raise ValueError(
                f"Handoff.schema_version must be one of {sorted(_ACCEPTED_SCHEMA_VERSIONS)!r}, "
                f"got {self.schema_version!r}"
            )

        # handoff_kind constant.
        if self.handoff_kind != HANDOFF_KIND:
            raise ValueError(
                f"Handoff.handoff_kind must be 'discover', got {self.handoff_kind!r}"
            )

        _require_nonempty(self.report_path, "Handoff.report_path")
        _require_nonempty(self.discover_completed_at, "Handoff.discover_completed_at")

        if not isinstance(self.intent, Intent):
            raise ValueError(
                f"Handoff.intent must be an Intent, got {type(self.intent).__name__}"
            )
        if not isinstance(self.spec_seeds, SpecSeeds):
            raise ValueError(
                f"Handoff.spec_seeds must be a SpecSeeds, got {type(self.spec_seeds).__name__}"
            )
        if not isinstance(self.plan_seeds, PlanSeeds):
            raise ValueError(
                f"Handoff.plan_seeds must be a PlanSeeds, got {type(self.plan_seeds).__name__}"
            )
        if not isinstance(self.discovery_block, DiscoveryBlock):
            raise ValueError(
                f"Handoff.discovery_block must be a DiscoveryBlock, "
                f"got {type(self.discovery_block).__name__}"
            )
        if not isinstance(self.downstream_links, DownstreamLinks):
            raise ValueError(
                f"Handoff.downstream_links must be a DownstreamLinks, "
                f"got {type(self.downstream_links).__name__}"
            )

        # Cross-field: recommended_option_id vs design_options vs verdict.
        self.plan_seeds._validate_recommended_option(self.discovery_block.verdict)

        # Cross-field: Outcome computed-field validation.
        if self.outcome is not None:
            self.outcome._validate_computed_fields(self.plan_seeds, self.discovery_block)
