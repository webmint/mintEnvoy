"""Handoff.json construction -- memo + report -> Handoff dataclass.

_build_handoff_from_state is the orchestrator. The _build_* helpers map
each discover state slice to its handoff_schema dataclass equivalent.
_asdict_handoff drops internal flag fields before JSON serialization.

All functions are pure (no I/O). Side-effect: schema __post_init__ may
raise ValueError; callers catch and translate to _die.
"""

from __future__ import annotations

import dataclasses
import datetime
import re
from typing import Dict, List, Optional

from . import handoff_schema


# ---------------------------------------------------------------------------
# Intent builder.
# ---------------------------------------------------------------------------


def _build_intent(memo):
    # type: (dict) -> handoff_schema.Intent
    """Build Intent from memo.topic + topic_slug + dimensions.functional_scope + verbatim_prompt.

    verbatim_prompt (v1.1): read from memo.verbatim_prompt, persisted by
    set-verbatim-prompt at Phase 0.3. cmd_finalize_handoff guards on non-empty
    before calling _build_handoff_from_state, so None/empty here is only
    possible if called directly from tests (back-compat). Pass as None when
    absent so schema tolerates-missing-on-read for old state files.
    """
    topic = (memo.get("topic") or "").strip()
    topic_slug = (memo.get("topic_slug") or "").strip()
    dims = memo.get("dimensions") or {}
    fs = dims.get("functional_scope") or {}
    scope_summary = (fs.get("value") or "").strip() or None
    verbatim_prompt = (memo.get("verbatim_prompt") or "").strip() or None

    return handoff_schema.Intent(
        feature_concept=topic or "(not set)",
        topic=topic or "(not set)",
        topic_slug=topic_slug or "unknown",
        scope_summary=scope_summary,
        verbatim_prompt=verbatim_prompt,
    )


# ---------------------------------------------------------------------------
# Spec-seeds builders.
# ---------------------------------------------------------------------------


def _build_constraints(memo, report):
    # type: (dict, dict) -> List[handoff_schema.Constraint]
    """Build Constraint list from memo.dimensions.constraints + non_goals + report.constitution_constraints.

    memo.dimensions.constraints -> kind=nfr (quantifier from dimension text).
    memo.dimensions.non_goals -> kind=nfr (non-goal framing).
    report.constitution_constraints -> kind=constitution_anchor.
    """
    result = []  # type: List[handoff_schema.Constraint]
    dims = memo.get("dimensions") or {}

    # Memo constraints dimension -> nfr
    constraints_dim = dims.get("constraints") or {}
    constraints_val = (constraints_dim.get("value") or "").strip()
    if constraints_val and constraints_dim.get("state") != "Missing":
        result.append(handoff_schema.Constraint(
            kind="nfr",
            content=constraints_val,
            quantifier="see discovery report constraints dimension",
        ))

    # Memo non_goals dimension -> nfr (non-goal framing)
    non_goals_dim = dims.get("non_goals") or {}
    non_goals_val = (non_goals_dim.get("value") or "").strip()
    if non_goals_val and non_goals_dim.get("state") != "Missing":
        result.append(handoff_schema.Constraint(
            kind="nfr",
            content="Out of scope: " + non_goals_val,
            quantifier="non-goal boundary from scoping session",
        ))

    # Report constitution_constraints -> constitution_anchor
    for cc in (report.get("constitution_constraints") or []):
        rule = (cc.get("rule") or "").strip()
        if not rule:
            continue
        result.append(handoff_schema.Constraint(
            kind="constitution_anchor",
            content=rule,
            constitution_ref="constitution.md",
        ))

    return result


def _build_affected_areas(report):
    # type: (dict) -> List[handoff_schema.AffectedArea]
    """Build AffectedArea list from integration_touchpoints + internal prior_art entries.

    integration_touchpoints -> AffectedArea with is_internal_extension_candidate=False
    internal:<path> prior_art entries -> AffectedArea with is_internal_extension_candidate=True
    """
    result = []  # type: List[handoff_schema.AffectedArea]
    seen_areas = set()  # type: ignore

    # Integration touchpoints first.
    for tp in (report.get("integration_touchpoints") or []):
        name = (tp.get("name") or "").strip()
        module_path = (tp.get("module_path") or "").strip()
        reason = (tp.get("reason") or "").strip()
        if not name:
            continue
        if name in seen_areas:
            continue
        seen_areas.add(name)
        files = [module_path] if module_path else []
        result.append(handoff_schema.AffectedArea(
            area=name,
            files=files,
            impact=reason or "integration touchpoint identified during discovery",
            is_internal_extension_candidate=False,
        ))

    # Internal prior_art entries -> extension candidates.
    for pa in (report.get("prior_art") or []):
        source = (pa.get("source") or "")
        if not source.startswith("internal:"):
            continue
        path_part = source[len("internal:"):].strip()
        if not path_part:
            continue
        area_name = "internal:" + path_part
        if area_name in seen_areas:
            continue
        seen_areas.add(area_name)
        reference = (pa.get("reference") or path_part).strip()
        relevance = (pa.get("relevance") or "internal canonical pattern").strip()
        result.append(handoff_schema.AffectedArea(
            area=area_name,
            files=[path_part],
            impact=relevance,
            is_internal_extension_candidate=True,
        ))

    return result


def _build_risks(report):
    # type: (dict) -> List[handoff_schema.Risk]
    """Build Risk list from derisk_plan entries + fit_assessments blockers."""
    result = []  # type: List[handoff_schema.Risk]

    # From derisk_plan strings -- each string becomes a risk.
    for item in (report.get("derisk_plan") or []):
        if not isinstance(item, str):
            continue
        text = item.strip()
        if not text:
            continue
        result.append(handoff_schema.Risk(
            risk=text,
            likelihood="Med",
            impact="Med",
            mitigation="address before implementation; see derisk plan",
        ))

    # From fit_assessments blockers.
    for fa in (report.get("fit_assessments") or []):
        for blocker in (fa.get("blockers") or []):
            if not isinstance(blocker, str):
                continue
            text = blocker.strip()
            if not text:
                continue
            result.append(handoff_schema.Risk(
                risk=text,
                likelihood="High",
                impact="High",
                mitigation="must resolve before implementation",
            ))

    return result


def _build_open_questions(memo, report):
    # type: (dict, dict) -> List[handoff_schema.OpenQuestion]
    """Build OpenQuestion list from report.open_uncertainties + memo.gaps."""
    result = []  # type: List[handoff_schema.OpenQuestion]

    for item in (report.get("open_uncertainties") or []):
        if not isinstance(item, str):
            continue
        text = item.strip()
        if not text:
            continue
        result.append(handoff_schema.OpenQuestion(question=text, blocking=False))

    for gap in (memo.get("gaps") or []):
        if not isinstance(gap, dict):
            continue
        desc = (gap.get("description") or "").strip()
        if not desc:
            continue
        result.append(handoff_schema.OpenQuestion(question=desc, blocking=True))

    return result


# ---------------------------------------------------------------------------
# Plan-seeds builders.
# ---------------------------------------------------------------------------


_LETTERS = "ABCDEFGH"


def _build_design_options(report):
    # type: (dict) -> List[handoff_schema.DesignOption]
    """Build DesignOption list; auto-assign id A/B/C/... by insertion order."""
    result = []  # type: List[handoff_schema.DesignOption]
    for i, opt in enumerate(report.get("design_options") or []):
        if i >= len(_LETTERS):
            break
        letter = _LETTERS[i]
        name = (opt.get("name") or "").strip()
        if not name:
            continue
        # Strip any leading letter prefix the LLM may have injected.
        name = re.sub(r'^[A-H]\s*:\s*', '', name).strip()
        shape = (opt.get("shape") or "").strip()
        pros_raw = opt.get("pros") or []
        cons_raw = opt.get("cons") or []
        pros = [p.strip() for p in pros_raw if isinstance(p, str) and p.strip()]
        cons = [c.strip() for c in cons_raw if isinstance(c, str) and c.strip()]
        complexity_raw = (opt.get("complexity") or "Med").strip()
        # Normalize: "Medium" -> "Med" etc.
        complexity_map = {"low": "Low", "med": "Med", "medium": "Med", "high": "High"}
        complexity = complexity_map.get(complexity_raw.lower(), complexity_raw)
        result.append(handoff_schema.DesignOption(
            id=letter,
            name=name,
            shape=shape or "(see discovery report)",
            pros=pros if pros else ["see discovery report"],
            cons=cons if cons else ["see discovery report"],
            complexity=complexity,
        ))
    return result


def _resolve_recommended_option_id(report, design_options):
    # type: (dict, List[handoff_schema.DesignOption]) -> Optional[str]
    """Find the letter-id of the recommended option by name-matching.

    report.recommended_option.name must match one of design_options[*].name.
    Returns None when there's no recommended_option or no match.
    """
    rec = report.get("recommended_option")
    if not rec or not isinstance(rec, dict):
        return None
    rec_name = re.sub(r'^[A-H]\s*:\s*', '', (rec.get("name") or "").strip()).strip()
    if not rec_name:
        return None
    for opt in design_options:
        if opt.name == rec_name:
            return opt.id
    # Partial match fallback: case-insensitive prefix.
    rec_lower = rec_name.lower()
    for opt in design_options:
        if opt.name.lower().startswith(rec_lower[:20]):
            return opt.id
    return None


def _build_build_vs_buy(report):
    # type: (dict) -> Optional[handoff_schema.BuildVsBuy]
    """Build BuildVsBuy from report.build_vs_buy dict."""
    bvb = report.get("build_vs_buy")
    if not bvb or not isinstance(bvb, dict):
        return None
    recommendation = (bvb.get("recommendation") or "").strip()
    build_path = (bvb.get("build") or "").strip()
    buy_path = (bvb.get("buy") or "").strip()
    reasoning = (bvb.get("reasoning") or "").strip()
    if not recommendation or not build_path or not buy_path or not reasoning:
        return None
    if recommendation not in {"Build", "Buy", "Hybrid"}:
        return None
    return handoff_schema.BuildVsBuy(
        recommendation=recommendation,
        build_path=build_path,
        buy_path=buy_path,
        reasoning=reasoning,
    )


def _build_cited_patterns(report):
    # type: (dict) -> List[handoff_schema.CitedPattern]
    """Build CitedPattern list from report.prior_art.

    Sets is_internal=True for entries with source.startswith("internal:").
    """
    result = []  # type: List[handoff_schema.CitedPattern]
    for pa in (report.get("prior_art") or []):
        reference = (pa.get("reference") or "").strip()
        kind_raw = (pa.get("kind") or "pattern").strip()
        source = (pa.get("source") or "").strip()
        relevance = (pa.get("relevance") or "").strip()
        if not reference or not relevance:
            continue
        # Validate kind; default to "pattern" on unknown.
        if kind_raw not in {"library", "product", "pattern"}:
            kind_raw = "pattern"
        is_internal = source.startswith("internal:")
        result.append(handoff_schema.CitedPattern(
            reference=reference,
            kind=kind_raw,
            source=source if source else "see discovery report",
            relevance=relevance,
            is_internal=is_internal,
        ))
    return result


def _build_fit_assessments(report):
    # type: (dict) -> List[handoff_schema.FitAssessment]
    """Build FitAssessment list from report.fit_assessments."""
    result = []  # type: List[handoff_schema.FitAssessment]
    _valid_effort = {"Low", "Medium", "High", "Major refactor required"}
    for fa in (report.get("fit_assessments") or []):
        touchpoint = (fa.get("touchpoint") or "").strip()
        user_expected = (fa.get("user_expected") or "").strip()
        reality = (fa.get("reality") or "").strip()
        effort = (fa.get("effort") or "Low").strip()
        blockers = fa.get("blockers") or []
        if not touchpoint or not user_expected or not reality:
            continue
        if effort not in _valid_effort:
            effort = "Low"
        blockers_clean = [b.strip() for b in blockers if isinstance(b, str) and b.strip()]
        result.append(handoff_schema.FitAssessment(
            touchpoint=touchpoint,
            user_expected=user_expected,
            reality=reality,
            effort=effort,
            blockers=blockers_clean,
        ))
    return result


# ---------------------------------------------------------------------------
# MemoDimensions + DiscoveryBlock builders.
# ---------------------------------------------------------------------------


def _build_dimension_record(dim_dict):
    # type: (dict) -> handoff_schema.DimensionRecord
    """Build a DimensionRecord from a dimension dict {value, state, turns}."""
    state = (dim_dict.get("state") or "Missing").strip()
    if state not in {"Clear", "Partial", "Missing"}:
        state = "Missing"
    turns = dim_dict.get("turns") or 0
    if not isinstance(turns, int) or turns < 0:
        turns = 0
    value = (dim_dict.get("value") or None)
    if isinstance(value, str):
        value = value.strip() or None
    # DimensionRecord requires value when state != Missing.
    if state != "Missing" and not value:
        value = "(not recorded)"
    return handoff_schema.DimensionRecord(state=state, turns=turns, value=value)


def _build_dimension_records(memo):
    # type: (dict) -> handoff_schema.MemoDimensions
    """Build MemoDimensions from memo.dimensions (all 8 rubric axes)."""
    dims = memo.get("dimensions") or {}
    dim_names = [
        "functional_scope", "users", "inputs_outputs", "integration_points",
        "constraints", "non_goals", "success_criteria", "edge_cases",
    ]
    records = {}  # type: Dict[str, handoff_schema.DimensionRecord]
    for name in dim_names:
        raw = dims.get(name) or {}
        records[name] = _build_dimension_record(raw)
    return handoff_schema.MemoDimensions(
        functional_scope=records["functional_scope"],
        users=records["users"],
        inputs_outputs=records["inputs_outputs"],
        integration_points=records["integration_points"],
        constraints=records["constraints"],
        non_goals=records["non_goals"],
        success_criteria=records["success_criteria"],
        edge_cases=records["edge_cases"],
    )


def _build_discovery_block(memo, report):
    # type: (dict, dict) -> handoff_schema.DiscoveryBlock
    """Build DiscoveryBlock from report overall_fit + effort_estimate + verdict + memo dims."""
    overall_fit = (report.get("overall_fit") or "Good").strip()
    if overall_fit not in {"Good", "Acceptable", "Strained", "Misfit"}:
        overall_fit = "Good"
    effort_estimate = (report.get("effort_estimate") or "Low").strip()
    if effort_estimate not in {"Low", "Medium", "High", "Major refactor required"}:
        effort_estimate = "Low"
    fit_rationale = (report.get("fit_rationale") or "see discovery report").strip()
    verdict = (report.get("verdict") or "Reconsider").strip()
    if verdict not in {"Worth pursuing", "Promising with caveats", "Reconsider"}:
        verdict = "Reconsider"
    override_recorded = bool(memo.get("override_recorded") or False)
    memo_dimensions = _build_dimension_records(memo)
    references = [r for r in (memo.get("references") or []) if isinstance(r, str) and r.strip()]
    fit_assessments = _build_fit_assessments(report)

    # Gaps from memo.
    gap_records = []  # type: List[handoff_schema.Gap]
    for gap in (memo.get("gaps") or []):
        if not isinstance(gap, dict):
            continue
        dimension = (gap.get("dimension") or "").strip()
        description = (gap.get("description") or "").strip()
        if not dimension or not description:
            continue
        gap_records.append(handoff_schema.Gap(dimension=dimension, description=description))

    return handoff_schema.DiscoveryBlock(
        overall_fit=overall_fit,
        effort_estimate=effort_estimate,
        fit_rationale=fit_rationale,
        fit_assessments=fit_assessments,
        verdict=verdict,
        override_recorded=override_recorded,
        memo_dimensions=memo_dimensions,
        references=references,
        gaps=gap_records,
    )


# ---------------------------------------------------------------------------
# _asdict_handoff -- strips internal underscore-prefixed fields.
# ---------------------------------------------------------------------------


def _asdict_handoff(handoff):
    # type: (handoff_schema.Handoff) -> dict
    """Convert Handoff dataclass to dict for JSON serialization.

    Strips PlanSeeds internal source fields (_effort_estimate, _overall_fit,
    _derisk_count) before returning. These are schema-internal and must not
    appear in the serialized artefact.
    """
    raw = dataclasses.asdict(handoff)
    plan_seeds = raw.get("plan_seeds")
    if isinstance(plan_seeds, dict):
        plan_seeds.pop("_effort_estimate", None)
        plan_seeds.pop("_overall_fit", None)
        plan_seeds.pop("_derisk_count", None)
    return raw


# ---------------------------------------------------------------------------
# Orchestrator.
# ---------------------------------------------------------------------------


def _build_handoff_from_state(memo, report, report_md_path=None):
    # type: (dict, dict, Optional[str]) -> handoff_schema.Handoff
    """Orchestrate memo + report -> Handoff dataclass construction.

    Raises ValueError from schema validators on any field failure.
    report_md_path is the path to the parallel .md artefact; when None,
    the helper computes the canonical name from report.date + memo.topic_slug.
    """
    topic_slug = (memo.get("topic_slug") or "unknown").strip()
    date = (report.get("date") or datetime.date.today().isoformat()).strip()

    # report_path: path to the parallel markdown artefact.
    if report_md_path:
        report_path = report_md_path
    else:
        report_path = "discover/{0}-{1}.md".format(date, topic_slug)

    # intent
    intent = _build_intent(memo)

    # spec_seeds
    constraints = _build_constraints(memo, report)
    affected_areas = _build_affected_areas(report)
    risks = _build_risks(report)
    open_questions = _build_open_questions(memo, report)
    spec_seeds = handoff_schema.SpecSeeds(
        spec_type_hint="greenfield_feature",
        constraints=constraints,
        affected_areas=affected_areas,
        risks=risks,
        open_questions=open_questions,
    )

    # plan_seeds -- design_options auto-assign letter ids.
    design_options = _build_design_options(report)
    recommended_option_id = _resolve_recommended_option_id(report, design_options)
    rec = report.get("recommended_option") or {}
    rec_rationale = (rec.get("rationale") or "see discovery report").strip()
    build_vs_buy = _build_build_vs_buy(report)
    cited_patterns = _build_cited_patterns(report)
    derisk_count = len(report.get("derisk_plan") or [])

    # Complexity is derived from effort_estimate + overall_fit + derisk_count.
    effort_estimate = (report.get("effort_estimate") or "Low").strip()
    overall_fit = (report.get("overall_fit") or "Good").strip()
    complexity = handoff_schema.Complexity(
        changes=handoff_schema._compute_complexity_changes(
            effort_estimate if effort_estimate in {
                "Low", "Medium", "High", "Major refactor required"
            } else "Low"
        ),
        risk=handoff_schema._compute_complexity_risk(
            overall_fit if overall_fit in {"Good", "Acceptable", "Strained", "Misfit"} else "Good"
        ),
        verify_cost=handoff_schema._compute_complexity_verify_cost(derisk_count),
    )

    # G-mirror: when internal prior_art exists, the rationale must already cite
    # the full "internal:<path>" source string (schema checks cp.source in rationale).
    # This is NOT auto-fixed here; the LLM must supply a rationale that passes
    # G-mirror via verify before finalize-handoff is called. Schema validation
    # in PlanSeeds.__post_init__ will raise ValueError if the G-mirror rule is
    # violated; cmd_finalize_handoff catches it and exits 2.
    # (No auto-append; faithful pass-through of state.)

    # build_vs_buy is required by PlanSeeds but can be absent in report;
    # provide a stub when missing so schema validates.
    if build_vs_buy is None:
        build_vs_buy = handoff_schema.BuildVsBuy(
            recommendation="Build",
            build_path="to be determined in /plan",
            buy_path="no known off-the-shelf replacement",
            reasoning="no explicit build-vs-buy analysis recorded during discovery",
        )

    plan_seeds = handoff_schema.PlanSeeds(
        design_options=design_options,
        build_vs_buy=build_vs_buy,
        cited_canonical_patterns=cited_patterns,
        complexity=complexity,
        recommended_option_id=recommended_option_id,
        recommended_option_rationale=rec_rationale,
        _effort_estimate=effort_estimate if effort_estimate in {
            "Low", "Medium", "High", "Major refactor required"
        } else "Low",
        _overall_fit=overall_fit if overall_fit in {
            "Good", "Acceptable", "Strained", "Misfit"
        } else "Good",
        _derisk_count=derisk_count,
    )

    # discovery_block
    discovery_block = _build_discovery_block(memo, report)

    # downstream_links
    downstream_links = handoff_schema.DownstreamLinks(
        spec_path=None,
        plan_path=None,
        execute_task_commit_shas=[],
    )

    discover_completed_at = datetime.datetime.now(
        datetime.timezone.utc
    ).isoformat(timespec="seconds")

    return handoff_schema.Handoff(
        schema_version=handoff_schema.SCHEMA_VERSION,
        handoff_kind=handoff_schema.HANDOFF_KIND,
        report_path=report_path,
        discover_completed_at=discover_completed_at,
        intent=intent,
        spec_seeds=spec_seeds,
        plan_seeds=plan_seeds,
        discovery_block=discovery_block,
        downstream_links=downstream_links,
        outcome=None,
    )
