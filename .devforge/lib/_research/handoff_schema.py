"""handoff_schema — dataclass schema for the research → specify → plan → /implement handoff artefact.

Single source of truth for the shape of `handoff.json` emitted by
`research_helper finalize-handoff` (Step 3) and consumed by
`specify_helper import-handoff` (Step 6).

Design notes:

- Dataclasses are pure records. No serialization (`to_dict` /
  `from_dict`), no rendering, no I/O. Those responsibilities live in the
  helper command layer so this schema stays small, importable, and
  independently testable.

- Schema-level validation runs in `__post_init__` and is mechanical:
    * Required string fields are non-empty after `.strip()`.
    * Enum-typed fields validated against module-level frozenset constants.
    * Conditional requireds enforced at construction (constraint kind rules,
      probe-tier interlocks, V2/V3 cross-field invariants).

- V2 fields: `DataFlowChain`, `ValueSemantics`, `ValueProductionSite`.
  Required gating: bug mode + presentation-layer symptom heuristic.
  Stability-axis gating: invariant classification + presentation-layer
  symptom. Production-site gating: stable_across_calls="false" requires
  a matching production site row.

- V3 fields: `LiteralArchaeology`, `proposed_call_shape`.
  literal_archaeology required when bug mode + literal-replacement
  recommended approach. proposed_call_shape required when bug mode +
  single-layer or literal-replacement approach. Argument-duplication
  detection with optional-chaining support; fail-soft on nested calls.

- Type-hint convention: explicit `typing.Optional` / `List` / `Dict`
  (no PEP 604 `X | None`, no PEP 585 `list[str]`). Targets Python 3.8+.
  `from __future__ import annotations` intentionally NOT used so
  `__post_init__` introspection sees real type objects.

Stdlib only. No third-party dependencies.
"""

import datetime
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Schema version constant.
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "1.1"


# ---------------------------------------------------------------------------
# Enum allow-sets (frozensets for O(1) membership, similar to
# generate_docs_schema.py's tuple approach but frozenset preferred for
# sets that are checked frequently at construction time).
# ---------------------------------------------------------------------------

_VALID_MODE = frozenset({"bug", "feature_addition", "migration", "refactor", "greenfield"})
_VALID_SCOPE = frozenset({"feature-wide", "file-local", "package-local", "system-wide"})
_VALID_SPEC_TYPE_HINT = frozenset({
    "migration_tooling", "feature_addition", "bug_fix", "refactor", "greenfield_feature"
})
_VALID_CONSTRAINT_KIND = frozenset({"nfr", "constitution_anchor", "external_system", "follow", "not_break"})
_VALID_LIKELIHOOD = frozenset({"Low", "Med", "High"})
_VALID_IMPACT = frozenset({"Low", "Med", "High"})
_VALID_COMPLEXITY = frozenset({"Low", "Med", "High"})
_VALID_TRACE_MODE = frozenset({"data_flow", "calls"})
_VALID_VALUE_CLASSIFICATION = frozenset({"preference", "invariant", "unclassified"})
_VALID_STABLE_ACROSS_CALLS = frozenset({"true", "false", "unknown"})
_VALID_LITERAL_INTENT = frozenset({
    "placeholder", "migrated", "deliberate", "forgotten", "inherited-refactor", "generated"
})
_VALID_PROBE_TIER = frozenset({"1", "1.5", "2", "3"})
_VALID_PROBE_ACTOR = frozenset({"llm", "user"})
_VALID_TEST_FRAMEWORK = frozenset({"vitest", "jest", "pytest", "go-test", "cargo-test", "rspec"})
_VALID_HYPOTHESIS_CONFIRMED = frozenset({"primary", "runner_up", "none", "inconclusive"})
_VALID_EVIDENCE_SOURCE = frozenset({"test-result", "llm-ui-session-log", "user-observation"})
_VALID_CONFIDENCE_GRADE = frozenset({"HIGH", "MEDIUM", "LOW"})

# V3 Patch 8 literal-replacement detector regex.
# Matches: "Replace X with Y" / "change X to Y" / "X -> Y" patterns.
_LITERAL_REPLACEMENT_RE = re.compile(
    r'(?:replace|change)\s+\S+\s+(?:with|to)\s+\S+|^\S+\s*->\s*\S+$',
    re.IGNORECASE | re.MULTILINE,
)

# V3 Patch 9 — proposed_call_shape first-gate regex: top-level function call.
_CALL_SHAPE_RE = re.compile(r'^[A-Za-z_][\w.]*\([^)]*\)$')

# Commit SHA format: 7-40 hex characters.
_COMMIT_SHA_RE = re.compile(r'^[0-9a-f]{7,40}$')

# Escalation prose tokens (any of these case-insensitively in summary = OK).
_ESCALATION_TOKENS = ("default", "wrapper", "caller", "escalat")

# Literal intent values that require escalation cite.
_INTENTS_REQUIRING_ESCALATION = frozenset({"placeholder", "forgotten", "inherited-refactor"})


# ---------------------------------------------------------------------------
# Validation helpers.
# ---------------------------------------------------------------------------


def _require_nonempty(value, field_name):
    """Raise ValueError if `value` is not a non-empty (post-strip) string."""
    if not isinstance(value, str):
        raise ValueError(
            f"{field_name} must be a string, got {type(value).__name__}"
        )
    if value.strip() == "":
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_in_enum(value, allowed, field_name):
    """Raise ValueError if `value` is not in `allowed`."""
    if value not in allowed:
        raise ValueError(
            f"{field_name} must be one of {sorted(allowed)}, got {value!r}"
        )


def _is_presentation_layer_symptom(affected_areas):
    """Return True if any affected_area file path matches a presentation-layer extension.

    Uses a structural heuristic matching file extensions .vue, .tsx?, .jsx?,
    .svelte, .html (with optional :line suffix). This is a schema-level sketch;
    the real research_helper.py performs richer detection. Acceptable here
    because the schema enforces shape structurally, not semantically.
    """
    pattern = re.compile(r'\.(vue|tsx?|jsx?|svelte|html)(:|$)')
    for area in affected_areas:
        for file_ref in area.files:
            if pattern.search(file_ref):
                return True
    return False


def _has_literal_replacement(summary):
    """Return True if the summary text matches the V3 literal-replacement regex."""
    return bool(_LITERAL_REPLACEMENT_RE.search(summary))


def _has_escalation_cite(summary):
    """Return True if the summary contains any escalation-direction token."""
    lower = summary.lower()
    return any(token in lower for token in _ESCALATION_TOKENS)


def _is_single_layer_fix(layer_justification):
    """Return True if layer_justification implies a single-layer fix."""
    lower = layer_justification.lower()
    return "single-layer" in lower or "single layer" in lower


def _parse_proposed_call_shape(proposed_call_shape):
    """Parse proposed_call_shape for argument duplication.

    Returns (parse_failed: bool, duplicate_identifier: Optional[str]).
    - parse_failed=True means the shape failed the first-gate regex (fail-soft).
    - duplicate_identifier non-None means a duplicate was detected (hard reject).
    """
    if not _CALL_SHAPE_RE.match(proposed_call_shape):
        return True, None  # fail-soft — nested call, spread, template literal, etc.

    # Extract argument list: everything between the outermost parens.
    inner_start = proposed_call_shape.index('(')
    inner = proposed_call_shape[inner_start + 1:-1]

    if not inner.strip():
        return False, None  # zero-arg call, no duplication possible

    # Split on top-level commas. Since the first-gate regex requires
    # [^)]* in the paren group (no nested parens), a simple split is safe.
    args = inner.split(',')

    # Collect identifier tokens per arg using optional-chaining-aware regex.
    ident_re = re.compile(r'[A-Za-z_]\w*(?:\??\.[A-Za-z_]\w*)*')
    # For duplication detection, we look at ROOT identifiers (the leading
    # name before any '.') since optional-chain variants of the same root
    # are semantically the same binding.
    root_re = re.compile(r'^([A-Za-z_]\w*)')

    seen_roots = {}  # root_identifier -> first arg index
    for arg_idx, arg in enumerate(args):
        tokens = ident_re.findall(arg.strip())
        for token in tokens:
            m = root_re.match(token)
            if not m:
                continue
            root = m.group(1)
            if root in seen_roots:
                return False, root
            seen_roots[root] = arg_idx

    return False, None


# ---------------------------------------------------------------------------
# Confidence grade derivation.
# ---------------------------------------------------------------------------


def compute_confidence_grade(
    tier,                    # type: str
    evidence_source,         # type: str
    hypothesis_confirmed,    # type: str
    has_production_site_check,  # type: bool
):
    # type: (...) -> str
    """Compute the expected confidence grade from a (tier, evidence_source, hypothesis_confirmed, has_production_site_check) tuple.

    This function is the single source of truth for grade derivation;
    `Outcome.__post_init__` asserts the stored `confidence_grade` matches.
    Exported for `append-outcome` (Step 7) to call directly.

    Grade rules (checked in priority order):
    - Tier 1 + test-result + confirmed in {primary, runner_up, none} → HIGH
    - Tier 1.5 + test-result → HIGH
    - production_site_check present + primary confirmed + non-test-result → MEDIUM
      (production-site bugs need executable evidence; observation is insufficient)
    - Tier 2 + llm-ui-session-log → MEDIUM
    - Tier 2 + user-observation → LOW
    - Tier 3 → LOW
    - fallback → LOW
    """
    if (tier == "1"
            and evidence_source == "test-result"
            and hypothesis_confirmed in {"primary", "runner_up", "none"}):
        return "HIGH"
    if tier == "1.5" and evidence_source == "test-result" and hypothesis_confirmed != "inconclusive":
        return "HIGH"
    if (has_production_site_check
            and hypothesis_confirmed == "primary"
            and evidence_source != "test-result"):
        return "MEDIUM"
    if tier == "2" and evidence_source == "llm-ui-session-log":
        return "MEDIUM"
    if tier in {"1", "1.5"} and evidence_source == "test-result" and hypothesis_confirmed == "inconclusive":
        return "MEDIUM"
    if tier == "2" and evidence_source == "user-observation":
        return "LOW"
    if tier == "3":
        return "LOW"
    return "LOW"


# ---------------------------------------------------------------------------
# Nested record: Intent.
# ---------------------------------------------------------------------------


@dataclass
class Intent:
    """Research intent block — symptom, desired state, scope, and verbatim prompt.

    verbatim_prompt (added v1.1): the raw user prompt text, unmodified.

    Back-compat (OQ-1 RESOLVED): the field defaults to None so that pre-v1.1
    handoff.json records loaded via _dict_to_dataclass do not raise on
    construction (absent field -> None -> tolerate-missing-on-read branch).
    When non-None, it must be non-empty after strip (same _require_nonempty
    idiom as other optional string fields). New handoffs always supply a
    non-empty string via _build_handoff_from_state, which guards on the
    state value before constructing Intent.
    """

    symptom_summary: str
    desired_summary: str
    scope: str  # one of _VALID_SCOPE
    verbatim_prompt: Optional[str] = None

    def __post_init__(self):
        _require_nonempty(self.symptom_summary, "Intent.symptom_summary")
        _require_nonempty(self.desired_summary, "Intent.desired_summary")
        _require_in_enum(self.scope, _VALID_SCOPE, "Intent.scope")
        if self.verbatim_prompt is not None:
            _require_nonempty(self.verbatim_prompt, "Intent.verbatim_prompt")


# ---------------------------------------------------------------------------
# Nested records: spec_seeds sub-records.
# ---------------------------------------------------------------------------


@dataclass
class Constraint:
    """One spec constraint, using Gap-A taxonomy.

    kind `use` is hard-rejected with a migration message.
    kind `nfr` requires `quantifier`.
    kind `constitution_anchor` requires `constitution_ref`.
    kind `external_system` requires `protocol` OR `contract_doc_ref`.
    """

    kind: str
    content: str
    quantifier: Optional[str] = None
    constitution_ref: Optional[str] = None
    protocol: Optional[str] = None
    contract_doc_ref: Optional[str] = None

    def __post_init__(self):
        # Hard-reject legacy `use` kind before the enum check.
        if self.kind == "use":
            raise ValueError(
                "Constraint.kind='use' is rejected. Use one of: "
                "'nfr' (scale/latency NFRs), "
                "'constitution_anchor' (code-pattern rules), "
                "'external_system' (third-party protocol contracts)."
            )
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
    """One affected area in the codebase."""

    area: str
    files: List[str]  # list of "path:line" strings
    impact: str

    def __post_init__(self):
        _require_nonempty(self.area, "AffectedArea.area")
        _require_nonempty(self.impact, "AffectedArea.impact")
        if not isinstance(self.files, list):
            raise ValueError("AffectedArea.files must be a list")
        for f in self.files:
            if not isinstance(f, str):
                raise ValueError(
                    f"AffectedArea.files elements must be strings, got {type(f).__name__!r} in area {self.area!r}"
                )


@dataclass
class Risk:
    """One identified risk."""

    risk: str
    likelihood: str  # one of _VALID_LIKELIHOOD
    impact: str      # one of _VALID_IMPACT
    mitigation: str

    def __post_init__(self):
        _require_nonempty(self.risk, "Risk.risk")
        _require_in_enum(self.likelihood, _VALID_LIKELIHOOD, "Risk.likelihood")
        _require_in_enum(self.impact, _VALID_IMPACT, "Risk.impact")
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
class DataFlowChain:
    """V2 Patch 6 — data-flow chain from user-action handler to write-boundary.

    Required when mode=bug AND symptom is presentation-layer (enforced at
    SpecSeeds level). Null otherwise.
    """

    handler_qn: str
    write_boundary_qn: str
    intermediate_qns: List[str]
    trace_mode: str  # one of _VALID_TRACE_MODE

    def __post_init__(self):
        _require_nonempty(self.handler_qn, "DataFlowChain.handler_qn")
        _require_nonempty(self.write_boundary_qn, "DataFlowChain.write_boundary_qn")
        if not isinstance(self.intermediate_qns, list):
            raise ValueError("DataFlowChain.intermediate_qns must be a list")
        _require_in_enum(self.trace_mode, _VALID_TRACE_MODE, "DataFlowChain.trace_mode")


@dataclass
class ValueSemantics:
    """V2 Patch 7 — id-stability axis classification for one value/symbol.

    stable_across_calls is required when classification=invariant AND symptom
    is presentation-layer (enforced at SpecSeeds level with the affected_areas
    heuristic). Accepted as None for domain-layer symptoms per V2 C4.
    """

    value: str
    classification: str           # one of _VALID_VALUE_CLASSIFICATION
    stable_across_calls: Optional[str]  # one of _VALID_STABLE_ACROSS_CALLS or None

    def __post_init__(self):
        _require_nonempty(self.value, "ValueSemantics.value")
        _require_in_enum(self.classification, _VALID_VALUE_CLASSIFICATION, "ValueSemantics.classification")
        if self.stable_across_calls is not None:
            _require_in_enum(
                self.stable_across_calls,
                _VALID_STABLE_ACROSS_CALLS,
                "ValueSemantics.stable_across_calls",
            )


@dataclass
class ValueProductionSite:
    """V2 Patch 7 — one site where a value is produced/assigned.

    file_line rejects the '(none)' sentinel — archaeology requires a real path.
    is_stable=False means the production site rewrites the value per call
    (Math.random / Date.now / uuid pattern).
    """

    value: str
    file_line: str
    is_stable: bool

    def __post_init__(self):
        _require_nonempty(self.value, "ValueProductionSite.value")
        _require_nonempty(self.file_line, "ValueProductionSite.file_line")
        if self.file_line.strip() == "(none)":
            raise ValueError(
                "ValueProductionSite.file_line rejects '(none)' sentinel — "
                "a real path:line is required"
            )
        if not isinstance(self.is_stable, bool):
            raise ValueError(
                f"ValueProductionSite.is_stable must be a bool, got {type(self.is_stable).__name__}"
            )


@dataclass
class LiteralArchaeology:
    """V3 Patch 8 — git-archaeology record for one hardcoded literal proposed for replacement.

    introduced_by must be a 7-40 char hex commit SHA.
    introduced_when must parse as an ISO date (YYYY-MM-DD).
    file_line rejects the '(none)' sentinel.
    intent must be one of the 6-value locked enum.
    """

    literal: str
    file_line: str
    introduced_by: str
    introduced_when: str   # ISO date string YYYY-MM-DD
    commit_subject: str
    intent: str            # one of _VALID_LITERAL_INTENT

    def __post_init__(self):
        _require_nonempty(self.literal, "LiteralArchaeology.literal")
        _require_nonempty(self.file_line, "LiteralArchaeology.file_line")
        if self.file_line.strip() == "(none)":
            raise ValueError(
                "LiteralArchaeology.file_line rejects '(none)' sentinel — "
                "a real path:line is required"
            )
        _require_nonempty(self.introduced_by, "LiteralArchaeology.introduced_by")
        if not _COMMIT_SHA_RE.match(self.introduced_by):
            raise ValueError(
                f"LiteralArchaeology.introduced_by must be a 7-40 char hex commit SHA, "
                f"got {self.introduced_by!r}"
            )
        _require_nonempty(self.introduced_when, "LiteralArchaeology.introduced_when")
        try:
            datetime.date.fromisoformat(self.introduced_when)
        except ValueError:
            raise ValueError(
                f"LiteralArchaeology.introduced_when must be an ISO date (YYYY-MM-DD), "
                f"got {self.introduced_when!r}"
            )
        _require_nonempty(self.commit_subject, "LiteralArchaeology.commit_subject")
        _require_in_enum(self.intent, _VALID_LITERAL_INTENT, "LiteralArchaeology.intent")


# ---------------------------------------------------------------------------
# Spec seeds aggregate.
# ---------------------------------------------------------------------------


@dataclass
class SpecSeeds:
    """Spec-seeds block — all inputs /specify needs from /research.

    Cross-field validators enforced in __post_init__:
    - data_flow_chain required when mode=bug + presentation-layer symptom.
    - stable_across_calls required when invariant + presentation-layer symptom.
    - stable_across_calls="false" requires at least one matching value_production_sites row.
    - value_production_sites distinct (value, file_line) pairs.
    - literal_archaeology required when mode=bug + literal-replacement approach
      (checked at Handoff level since it needs plan_seeds context).
    - literal_archaeology distinct (literal, file_line) pairs.

    Note: mode is passed in from the Handoff constructor for cross-field checks.
    """

    spec_type_hint: str
    constraints: List[Constraint]
    affected_areas: List[AffectedArea]
    risks: List[Risk]
    open_questions: List[OpenQuestion]
    value_semantics: List[ValueSemantics] = field(default_factory=list)
    value_production_sites: List[ValueProductionSite] = field(default_factory=list)
    literal_archaeology: List[LiteralArchaeology] = field(default_factory=list)
    data_flow_chain: Optional[DataFlowChain] = None

    def __post_init__(self):
        _require_in_enum(self.spec_type_hint, _VALID_SPEC_TYPE_HINT, "SpecSeeds.spec_type_hint")
        if not isinstance(self.constraints, list):
            raise ValueError("SpecSeeds.constraints must be a list")
        if not isinstance(self.affected_areas, list):
            raise ValueError("SpecSeeds.affected_areas must be a list")
        if not isinstance(self.risks, list):
            raise ValueError("SpecSeeds.risks must be a list")
        if not isinstance(self.open_questions, list):
            raise ValueError("SpecSeeds.open_questions must be a list")
        if not isinstance(self.value_semantics, list):
            raise ValueError("SpecSeeds.value_semantics must be a list")
        if not isinstance(self.value_production_sites, list):
            raise ValueError("SpecSeeds.value_production_sites must be a list")
        if not isinstance(self.literal_archaeology, list):
            raise ValueError("SpecSeeds.literal_archaeology must be a list")

        # V2: distinct (value, file_line) tuples for value_production_sites.
        seen_prod = set()  # type: ignore
        for vps in self.value_production_sites:
            key = (vps.value, vps.file_line)
            if key in seen_prod:
                raise ValueError(
                    f"SpecSeeds.value_production_sites duplicate row: "
                    f"(value={vps.value!r}, file_line={vps.file_line!r})"
                )
            seen_prod.add(key)

        # V3: distinct (literal, file_line) tuples for literal_archaeology.
        seen_arch = set()  # type: ignore
        for la in self.literal_archaeology:
            key = (la.literal, la.file_line)
            if key in seen_arch:
                raise ValueError(
                    f"SpecSeeds.literal_archaeology duplicate row: "
                    f"(literal={la.literal!r}, file_line={la.file_line!r})"
                )
            seen_arch.add(key)

    def _validate_cross_field(self, mode):
        # type: (str) -> None
        """Cross-field validators that need mode from the parent Handoff.

        Called by Handoff.__post_init__ after setting mode.
        """
        is_presentation = _is_presentation_layer_symptom(self.affected_areas)

        # V2: data_flow_chain required when bug + presentation-layer.
        if mode == "bug" and is_presentation and self.data_flow_chain is None:
            raise ValueError(
                "SpecSeeds.data_flow_chain is required when mode='bug' and "
                "affected_areas contain a presentation-layer file "
                "(.vue, .tsx, .jsx, .svelte, .html)"
            )

        # V2: stable_across_calls rules per value_semantics row.
        for vs in self.value_semantics:
            if vs.classification == "invariant" and is_presentation:
                if vs.stable_across_calls is None:
                    raise ValueError(
                        f"ValueSemantics.stable_across_calls is required when "
                        f"classification='invariant' and symptom is presentation-layer "
                        f"(value={vs.value!r})"
                    )

            # V2: stable_across_calls="false" requires a matching production site.
            if vs.stable_across_calls == "false":
                matching = [
                    vps for vps in self.value_production_sites
                    if vps.value == vs.value
                ]
                if not matching:
                    raise ValueError(
                        f"ValueSemantics stable_across_calls='false' requires at least "
                        f"one ValueProductionSite row with value={vs.value!r}"
                    )


# ---------------------------------------------------------------------------
# Plan seeds.
# ---------------------------------------------------------------------------


@dataclass
class CitedPattern:
    """One cited canonical pattern from CBM."""

    qn: str
    file_line: str

    def __post_init__(self):
        _require_nonempty(self.qn, "CitedPattern.qn")
        _require_nonempty(self.file_line, "CitedPattern.file_line")


@dataclass
class Alternative:
    """One alternative approach that was considered and rejected."""

    id: str
    summary: str
    rejected_reason: str

    def __post_init__(self):
        _require_nonempty(self.id, "Alternative.id")
        _require_nonempty(self.summary, "Alternative.summary")
        _require_nonempty(self.rejected_reason, "Alternative.rejected_reason")


@dataclass
class Complexity:
    """Complexity assessment for a recommended approach."""

    changes: str    # one of _VALID_COMPLEXITY
    risk: str       # one of _VALID_COMPLEXITY
    verify_cost: str  # one of _VALID_COMPLEXITY

    def __post_init__(self):
        _require_in_enum(self.changes, _VALID_COMPLEXITY, "Complexity.changes")
        _require_in_enum(self.risk, _VALID_COMPLEXITY, "Complexity.risk")
        _require_in_enum(self.verify_cost, _VALID_COMPLEXITY, "Complexity.verify_cost")


@dataclass
class PlanSeeds:
    """Plan-seeds block — recommended approach + layer + complexity + V3 call shape.

    Cross-field validators enforced at Handoff level (needs mode context).
    """

    recommended_approach_id: str
    recommended_approach_summary: str
    layer_destination: str
    layer_justification: str
    complexity: Complexity
    cited_canonical_patterns: List[CitedPattern] = field(default_factory=list)
    alternatives_considered: List[Alternative] = field(default_factory=list)
    proposed_call_shape: Optional[str] = None

    # Internal flag set by parser when proposed_call_shape fails first-gate regex.
    # Exposed for tests to assert fail-soft behavior.
    _proposed_call_shape_parse_failed: bool = field(default=False, init=False, repr=False, compare=False)

    def __post_init__(self):
        _require_nonempty(self.recommended_approach_id, "PlanSeeds.recommended_approach_id")
        _require_nonempty(self.recommended_approach_summary, "PlanSeeds.recommended_approach_summary")
        _require_nonempty(self.layer_destination, "PlanSeeds.layer_destination")
        _require_nonempty(self.layer_justification, "PlanSeeds.layer_justification")
        if not isinstance(self.complexity, Complexity):
            raise ValueError(
                f"PlanSeeds.complexity must be a Complexity, got {type(self.complexity).__name__}"
            )
        if not isinstance(self.cited_canonical_patterns, list):
            raise ValueError("PlanSeeds.cited_canonical_patterns must be a list")
        if not isinstance(self.alternatives_considered, list):
            raise ValueError("PlanSeeds.alternatives_considered must be a list")

        # Validate and parse proposed_call_shape when non-None.
        if self.proposed_call_shape is not None:
            _require_nonempty(self.proposed_call_shape, "PlanSeeds.proposed_call_shape")
            parse_failed, duplicate = _parse_proposed_call_shape(self.proposed_call_shape)
            if parse_failed:
                # Fail-soft: accept value but set advisory flag.
                object.__setattr__(self, '_proposed_call_shape_parse_failed', True)
            elif duplicate is not None:
                raise ValueError(
                    f"PlanSeeds.proposed_call_shape contains duplicate identifier "
                    f"{duplicate!r} across argument positions"
                )

    def _validate_cross_field(self, mode, spec_seeds):
        # type: (str, SpecSeeds) -> None
        """Cross-field validators that need mode + spec_seeds from Handoff.

        Called by Handoff.__post_init__. Checks are ordered so that the
        most-fundamental missing-data errors fire before secondary derived errors:
        1. literal_archaeology presence (required before we can check its rows).
        2. escalation cite per intent (requires non-empty literal_archaeology).
        3. proposed_call_shape presence (requires literal-replacement confirmed).
        """
        summary = self.recommended_approach_summary
        is_literal_replacement = _has_literal_replacement(summary)
        is_single_layer = _is_single_layer_fix(self.layer_justification)

        # V3: literal_archaeology required when bug + literal-replacement approach.
        # Check this FIRST so the error names the missing collection, not the
        # secondary requirement (proposed_call_shape) that depends on it.
        if mode == "bug" and is_literal_replacement:
            if not spec_seeds.literal_archaeology:
                raise ValueError(
                    "SpecSeeds.literal_archaeology must be non-empty when mode='bug' "
                    "and recommended_approach_summary matches a literal-replacement pattern"
                )

        # V3: escalation cite required for certain literal_archaeology intents.
        for la in spec_seeds.literal_archaeology:
            if la.intent in _INTENTS_REQUIRING_ESCALATION:
                if not _has_escalation_cite(summary):
                    raise ValueError(
                        f"PlanSeeds.recommended_approach_summary must cite escalation "
                        f"of default-source (contain 'default', 'wrapper', 'caller', or "
                        f"'escalat') when literal_archaeology intent={la.intent!r}. "
                        f"Intent 'deliberate', 'generated', 'migrated' do not require this."
                    )

        # V3: proposed_call_shape required when bug + (single-layer OR literal-replacement).
        if mode == "bug" and (is_single_layer or is_literal_replacement):
            if self.proposed_call_shape is None:
                raise ValueError(
                    "PlanSeeds.proposed_call_shape is required when mode='bug' and "
                    "(layer_justification implies single-layer fix OR "
                    "recommended_approach_summary matches literal-replacement pattern)"
                )


# ---------------------------------------------------------------------------
# Probe block.
# ---------------------------------------------------------------------------


@dataclass
class FeasibilityCheck:
    """Feasibility flags for the probe."""

    data_shape_only: bool
    auth_required: bool
    network_dependent: bool
    timing_dependent: bool
    is_test_code: bool

    def __post_init__(self):
        for fname in ("data_shape_only", "auth_required", "network_dependent",
                      "timing_dependent", "is_test_code"):
            v = getattr(self, fname)
            if not isinstance(v, bool):
                raise ValueError(
                    f"FeasibilityCheck.{fname} must be a bool, got {type(v).__name__}"
                )


@dataclass
class Discriminator:
    """Discriminator conditions for the probe."""

    primary_confirms_if: str
    runner_up_confirms_if: str
    both_disproved_if: str
    production_site_check: Optional[str]  # non-None when any is_stable=False in value_production_sites

    def __post_init__(self):
        _require_nonempty(self.primary_confirms_if, "Discriminator.primary_confirms_if")
        _require_nonempty(self.runner_up_confirms_if, "Discriminator.runner_up_confirms_if")
        _require_nonempty(self.both_disproved_if, "Discriminator.both_disproved_if")
        if self.production_site_check is not None:
            if not isinstance(self.production_site_check, str) or not self.production_site_check.strip():
                raise ValueError(
                    "Discriminator.production_site_check must be a non-empty string or None"
                )


@dataclass
class Probe:
    """Probe-tier classification block.

    Tier interlocks enforced in __post_init__:
    - feasibility_check.is_test_code=True AND tier='1' → rejected (circular).
    - tier='1' → test_framework non-None AND test_path non-empty.
    - tier='1.5' → script_path non-empty AND test_framework is None.
    """

    tier: str            # one of _VALID_PROBE_TIER
    actor: str           # one of _VALID_PROBE_ACTOR
    discriminator: Discriminator
    feasibility_check: FeasibilityCheck
    test_framework: Optional[str]   # one of _VALID_TEST_FRAMEWORK or None
    test_path: Optional[str]
    script_path: Optional[str]
    is_first_test_for_file: bool

    def __post_init__(self):
        _require_in_enum(self.tier, _VALID_PROBE_TIER, "Probe.tier")
        _require_in_enum(self.actor, _VALID_PROBE_ACTOR, "Probe.actor")
        if not isinstance(self.discriminator, Discriminator):
            raise ValueError(
                f"Probe.discriminator must be a Discriminator, got {type(self.discriminator).__name__}"
            )
        if not isinstance(self.feasibility_check, FeasibilityCheck):
            raise ValueError(
                f"Probe.feasibility_check must be a FeasibilityCheck, got {type(self.feasibility_check).__name__}"
            )
        if not isinstance(self.is_first_test_for_file, bool):
            raise ValueError(
                f"Probe.is_first_test_for_file must be a bool, got {type(self.is_first_test_for_file).__name__}"
            )

        # Validate test_framework enum when present.
        if self.test_framework is not None:
            _require_in_enum(self.test_framework, _VALID_TEST_FRAMEWORK, "Probe.test_framework")

        # Tier interlocks.
        if self.feasibility_check.is_test_code and self.tier == "1":
            raise ValueError(
                "Probe.tier='1' is rejected when feasibility_check.is_test_code=True "
                "(circular: tier-1 probe of test code is meaningless)"
            )

        if self.tier == "1":
            if self.test_framework is None:
                raise ValueError(
                    "Probe.test_framework must be non-None when tier='1'"
                )
            if not self.test_path or not self.test_path.strip():
                raise ValueError(
                    "Probe.test_path must be non-empty when tier='1'"
                )

        if self.tier == "1.5":
            if not self.script_path or not self.script_path.strip():
                raise ValueError(
                    "Probe.script_path must be non-empty when tier='1.5'"
                )
            if self.test_framework is not None:
                raise ValueError(
                    "Probe.test_framework must be None when tier='1.5' "
                    "(tier-1.5 uses a script, not a test suite)"
                )


# ---------------------------------------------------------------------------
# Outcome block.
# ---------------------------------------------------------------------------


@dataclass
class Outcome:
    """Outcome block — filled by `append-outcome` after probe runs.

    confidence_grade is derived from (tier, evidence_source, hypothesis_confirmed,
    has_production_site_check) via compute_confidence_grade(); __post_init__
    validates that the stored value matches.
    """

    hypothesis_confirmed: str    # one of _VALID_HYPOTHESIS_CONFIRMED
    evidence_source: str         # one of _VALID_EVIDENCE_SOURCE
    evidence_cite: str
    actual_fix_path: str
    confirmed_date: str          # ISO-8601
    confidence_grade: str        # one of _VALID_CONFIDENCE_GRADE
    delta_from_recommendation: Optional[str] = None
    confirmed_commit_sha: Optional[str] = None

    def __post_init__(self):
        _require_in_enum(self.hypothesis_confirmed, _VALID_HYPOTHESIS_CONFIRMED, "Outcome.hypothesis_confirmed")
        _require_in_enum(self.evidence_source, _VALID_EVIDENCE_SOURCE, "Outcome.evidence_source")
        _require_nonempty(self.evidence_cite, "Outcome.evidence_cite")
        _require_nonempty(self.actual_fix_path, "Outcome.actual_fix_path")
        _require_nonempty(self.confirmed_date, "Outcome.confirmed_date")
        _require_in_enum(self.confidence_grade, _VALID_CONFIDENCE_GRADE, "Outcome.confidence_grade")
        # ISO-8601 date parse check.
        try:
            datetime.date.fromisoformat(self.confirmed_date[:10])
        except ValueError:
            raise ValueError(
                f"Outcome.confirmed_date must be an ISO-8601 date, got {self.confirmed_date!r}"
            )
        # Commit SHA format: 7-40 hex chars, lowercase only.
        if self.confirmed_commit_sha is not None:
            if not _COMMIT_SHA_RE.match(self.confirmed_commit_sha):
                raise ValueError(
                    f"Outcome.confirmed_commit_sha must be 7-40 lowercase hex chars, "
                    f"got {self.confirmed_commit_sha!r}"
                )

    def _validate_grade(self, tier, has_production_site_check):
        # type: (str, bool) -> None
        """Validate confidence_grade against the derivation function.

        Called by Handoff.__post_init__ with probe context.
        """
        expected = compute_confidence_grade(
            tier=tier,
            evidence_source=self.evidence_source,
            hypothesis_confirmed=self.hypothesis_confirmed,
            has_production_site_check=has_production_site_check,
        )
        if self.confidence_grade != expected:
            raise ValueError(
                f"Outcome.confidence_grade={self.confidence_grade!r} does not match "
                f"derived grade={expected!r} for "
                f"(tier={tier!r}, evidence_source={self.evidence_source!r}, "
                f"hypothesis_confirmed={self.hypothesis_confirmed!r}, "
                f"has_production_site_check={has_production_site_check})"
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
    """Top-level handoff.json record.

    Owns all cross-field invariant validation in __post_init__:
    - schema_version must equal SCHEMA_VERSION.
    - All sub-record cross-field checks (data_flow_chain, stable_across_calls,
      literal_archaeology, proposed_call_shape, production_site_check,
      confidence_grade) are delegated to sub-record _validate_cross_field()
      methods with the mode context they need.
    """

    schema_version: str
    research_path: str
    research_completed_at: str
    mode: str              # one of _VALID_MODE
    intent: Intent
    spec_seeds: SpecSeeds
    plan_seeds: PlanSeeds
    probe: Probe
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

        _require_nonempty(self.research_path, "Handoff.research_path")
        _require_nonempty(self.research_completed_at, "Handoff.research_completed_at")
        _require_in_enum(self.mode, _VALID_MODE, "Handoff.mode")

        if not isinstance(self.intent, Intent):
            raise ValueError(f"Handoff.intent must be an Intent, got {type(self.intent).__name__}")
        if not isinstance(self.spec_seeds, SpecSeeds):
            raise ValueError(f"Handoff.spec_seeds must be a SpecSeeds, got {type(self.spec_seeds).__name__}")
        if not isinstance(self.plan_seeds, PlanSeeds):
            raise ValueError(f"Handoff.plan_seeds must be a PlanSeeds, got {type(self.plan_seeds).__name__}")
        if not isinstance(self.probe, Probe):
            raise ValueError(f"Handoff.probe must be a Probe, got {type(self.probe).__name__}")
        if not isinstance(self.downstream_links, DownstreamLinks):
            raise ValueError(
                f"Handoff.downstream_links must be a DownstreamLinks, "
                f"got {type(self.downstream_links).__name__}"
            )

        # Cross-field validation requiring mode context.
        self.spec_seeds._validate_cross_field(self.mode)
        self.plan_seeds._validate_cross_field(self.mode, self.spec_seeds)

        # V2: probe.discriminator.production_site_check required when any is_stable=False.
        has_unstable = any(
            not vps.is_stable for vps in self.spec_seeds.value_production_sites
        )
        if has_unstable and self.probe.discriminator.production_site_check is None:
            raise ValueError(
                "Probe.discriminator.production_site_check must be non-None when "
                "any SpecSeeds.value_production_sites[*].is_stable is False"
            )

        # Outcome cross-field validation.
        if self.outcome is not None:
            has_production_site_check = (
                self.probe.discriminator.production_site_check is not None
            )
            self.outcome._validate_grade(
                tier=self.probe.tier,
                has_production_site_check=has_production_site_check,
            )
