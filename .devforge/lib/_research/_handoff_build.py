"""Handoff.json construction — memo + report → Handoff dataclass.

_build_handoff_from_state is the orchestrator. The _build_* helpers map
each report state slice to its handoff_schema dataclass equivalent.
_resolve_cite_to_file_line walks fix_path_helpers / consumer_chain /
value_semantics / dead_siblings to find the file_line for a cite QN.
_asdict_handoff drops internal flag fields before JSON serialization.
"""

from __future__ import annotations

import dataclasses
import datetime
import re
from typing import Dict, List, Optional

from . import handoff_schema
from ._layer_package import _extract_package
from ._probe_tier import (
    _chrome_mcp_available,
    _classify_probe_tier,
    _read_test_infra_status,
)


def _to_snake_case(text):
    # type: (str) -> str
    """Convert arbitrary text to snake_case identifier. Strips/normalizes."""
    s = re.sub(r'[^A-Za-z0-9]+', '_', text.strip()).strip('_').lower()
    return s or "unnamed"


def _derive_scope(scope_text):
    # type: (Optional[str]) -> str
    """Best-effort enum derivation from free-text scope dimension."""
    if not scope_text:
        return "feature-wide"
    t = scope_text.lower()
    if "system" in t or "cross-package" in t or "monorepo" in t:
        return "system-wide"
    if "package" in t or "module" in t:
        return "package-local"
    if "file" in t or "function" in t or "line" in t:
        return "file-local"
    return "feature-wide"


_SPEC_TYPE_HINT_MAP = {
    "bug": "bug_fix",
    "enhancement": "feature_addition",  # research_helper MODE_ENUM uses "enhancement"
    "feature_addition": "feature_addition",
    "migration": "migration_tooling",
    "refactor": "refactor",
    "greenfield": "greenfield_feature",
}  # type: Dict[str, str]

# Map research_helper memo mode → handoff schema Handoff.mode value.
# Handoff schema _VALID_MODE = {bug, feature_addition, migration, refactor, greenfield}.
# research_helper MODE_ENUM = {bug, enhancement}.
# "enhancement" maps to "feature_addition" as the closest handoff schema equivalent.
_MEMO_MODE_TO_HANDOFF_MODE = {
    "bug": "bug",
    "enhancement": "feature_addition",
}  # type: Dict[str, str]


def _build_constraints(constitution_constraints):
    # type: (List[dict]) -> List[handoff_schema.Constraint]
    """Map report.constitution_constraints rows to Constraint dataclass list.

    State shape: {rule, impact}.
    The state has no anchor/rule_text — rule is the full text, no anchor field.
    All rows map to kind="follow" since the state has no anchor field.
    """
    result = []
    for row in constitution_constraints:
        rule_text = (row.get("rule") or "").strip()
        if not rule_text:
            continue
        result.append(handoff_schema.Constraint(kind="follow", content=rule_text))
    return result


def _build_affected_areas(fix_path_helpers, value_production_sites):
    # type: (List[dict], List[dict]) -> List[handoff_schema.AffectedArea]
    """Derive AffectedArea list by grouping file_lines by package.

    Sources: fix_path_helpers (each has file_line) and value_production_sites
    (each has file_line). Groups by package; each group becomes one AffectedArea.
    Empty both inputs → empty list.
    """
    # Collect (package, file_line) pairs from both sources.
    pkg_to_files = {}  # type: Dict[str, List[str]]
    for h in fix_path_helpers:
        fl = h.get("file_line") or ""
        if not fl:
            continue
        path_part = fl.rsplit(":", 1)[0] if ":" in fl else fl
        pkg = _extract_package(path_part)
        if not pkg:
            pkg = path_part
        pkg_to_files.setdefault(pkg, [])
        if fl not in pkg_to_files[pkg]:
            pkg_to_files[pkg].append(fl)
    for s in value_production_sites:
        fl = s.get("file_line") or ""
        if not fl:
            continue
        path_part = fl.rsplit(":", 1)[0] if ":" in fl else fl
        pkg = _extract_package(path_part)
        if not pkg:
            pkg = path_part
        pkg_to_files.setdefault(pkg, [])
        if fl not in pkg_to_files[pkg]:
            pkg_to_files[pkg].append(fl)
    if not pkg_to_files:
        return []
    return [
        handoff_schema.AffectedArea(area=pkg, files=files, impact="see findings")
        for pkg, files in sorted(pkg_to_files.items())
    ]


def _build_risks(complexity):
    # type: (Optional[dict]) -> List[handoff_schema.Risk]
    """Derive Risk list from complexity record.

    One risk entry when risk != 'Low'; empty list when complexity is None or risk is Low.
    """
    if complexity is None:
        return []
    risk_level = complexity.get("risk") or "Low"
    if risk_level == "Low":
        return []
    risk_notes = (complexity.get("risk_notes") or "").strip() or "see complexity"
    return [
        handoff_schema.Risk(
            risk=risk_notes,
            likelihood=risk_level,
            impact=risk_level,
            mitigation="tbd via /plan",
        )
    ]


def _build_value_semantics(value_semantics_rows):
    # type: (List[dict]) -> List[handoff_schema.ValueSemantics]
    """Map report.value_semantics rows to ValueSemantics dataclass list.

    State shape: {value, classification, evidence} or with stable_across_calls.
    Drops 'evidence' field (not in schema).
    """
    result = []
    for row in value_semantics_rows:
        value = (row.get("value") or "").strip()
        classification = (row.get("classification") or "").strip()
        stable_across_calls = row.get("stable_across_calls")
        if not value or not classification:
            continue
        result.append(handoff_schema.ValueSemantics(
            value=value,
            classification=classification,
            stable_across_calls=stable_across_calls,
        ))
    return result


def _build_value_production_sites(vps_rows):
    # type: (List[dict]) -> List[handoff_schema.ValueProductionSite]
    """Map report.value_production_sites rows to ValueProductionSite dataclass list.

    State stores is_stable as string "true"/"false"; schema requires bool.
    """
    result = []
    for row in vps_rows:
        value = (row.get("value") or "").strip()
        file_line = (row.get("file_line") or "").strip()
        is_stable_raw = row.get("is_stable")
        if not value or not file_line:
            continue
        # Convert string "true"/"false" to bool.
        if isinstance(is_stable_raw, bool):
            is_stable = is_stable_raw
        elif isinstance(is_stable_raw, str):
            is_stable = is_stable_raw.lower() == "true"
        else:
            is_stable = True  # safe default
        result.append(handoff_schema.ValueProductionSite(
            value=value,
            file_line=file_line,
            is_stable=is_stable,
        ))
    return result


def _build_literal_archaeology(la_rows):
    # type: (List[dict]) -> List[handoff_schema.LiteralArchaeology]
    """Map report.literal_archaeology rows to LiteralArchaeology dataclass list.

    Passes through directly; schema validates each row.
    """
    result = []
    for row in la_rows:
        result.append(handoff_schema.LiteralArchaeology(
            literal=row.get("literal") or "",
            file_line=row.get("file_line") or "",
            introduced_by=row.get("introduced_by") or "",
            introduced_when=row.get("introduced_when") or "",
            commit_subject=row.get("commit_subject") or "",
            intent=row.get("intent") or "",
        ))
    return result


def _build_data_flow_chain(dfc):
    # type: (Optional[dict]) -> Optional[handoff_schema.DataFlowChain]
    """Map report.data_flow_chain dict to DataFlowChain dataclass.

    State shape: {handler_qn, write_boundary_qn, intermediate_qns}.
    trace_mode is not in state — default to "calls" (most common case).
    """
    if dfc is None:
        return None
    return handoff_schema.DataFlowChain(
        handler_qn=dfc.get("handler_qn") or "",
        write_boundary_qn=dfc.get("write_boundary_qn") or "",
        intermediate_qns=dfc.get("intermediate_qns") or [],
        trace_mode=dfc.get("trace_mode") or "calls",
    )


def _build_open_questions(open_uncertainties):
    # type: (List[str]) -> List[handoff_schema.OpenQuestion]
    """Map open_uncertainties list of strings to OpenQuestion dataclass list."""
    result = []
    for item in open_uncertainties:
        if not isinstance(item, str):
            continue
        item = item.strip()
        if not item:
            continue
        result.append(handoff_schema.OpenQuestion(question=item, blocking=False))
    return result


def _resolve_cite_to_file_line(report, cite):
    # type: (dict, str) -> str
    """Resolve a cite QN token to a file_line via state lookup.

    Cites are QN tokens validated against fix_path_helpers / consumer_chain /
    value_semantics / dead_siblings. This walks each list in order looking
    for a token-match and returns the matched row's file_line. Falls back to
    the cite token if no match — Step 6 import-handoff surfaces unresolved
    entries.
    """
    for h in report.get("fix_path_helpers") or []:
        if isinstance(h, dict) and h.get("qn") == cite and h.get("file_line"):
            return h["file_line"]
    for c in report.get("consumer_chain") or []:
        if isinstance(c, dict) and c.get("consumer_qn") == cite and c.get("file_line"):
            return c["file_line"]
    for v in report.get("value_semantics") or []:
        if isinstance(v, dict) and v.get("value") == cite and v.get("file_line"):
            return v["file_line"]
    for d in report.get("dead_siblings") or []:
        if isinstance(d, dict) and d.get("method_qn") == cite and d.get("file_line"):
            return d["file_line"]
    return cite


def _build_cited_patterns(cites, report=None):
    # type: (List[str], Optional[dict]) -> List[handoff_schema.CitedPattern]
    """Map a list of cite tokens to CitedPattern dataclass list.

    When report is provided, resolves each cite token to a file_line via
    state lookup (_resolve_cite_to_file_line). Falls back to the cite token
    itself when no match is found.
    """
    if report is None:
        report = {}
    result = []
    for cite in cites:
        if not cite or not cite.strip():
            continue
        result.append(handoff_schema.CitedPattern(
            qn=cite.strip(),
            file_line=_resolve_cite_to_file_line(report, cite.strip()),
        ))
    return result


def _build_alternatives(approaches, recommended_name):
    # type: (List[dict], str) -> List[handoff_schema.Alternative]
    """Build alternatives list from all approaches excluding the recommended one."""
    result = []
    for ap in approaches:
        name = (ap.get("name") or "").strip()
        if name == recommended_name:
            continue
        summary = (ap.get("description") or "").strip() or "(no description)"
        result.append(handoff_schema.Alternative(
            id=_to_snake_case(name) if name else "unnamed",
            summary=summary,
            rejected_reason="not recommended; see /plan if needed",
        ))
    return result


def _find_unstable_production_site(vps_rows):
    # type: (List[handoff_schema.ValueProductionSite]) -> Optional[str]
    """Return the file_line of the first unstable production site, or None."""
    for vps in vps_rows:
        if not vps.is_stable:
            return vps.file_line
    return None


def _asdict_handoff(handoff):
    # type: (handoff_schema.Handoff) -> dict
    """Convert Handoff dataclass to dict for JSON serialization.

    Drops internal flag fields (e.g., _proposed_call_shape_parse_failed)
    before serialization. Uses dataclasses.asdict for recursive conversion.
    """
    raw = dataclasses.asdict(handoff)
    # Drop internal flag fields from plan_seeds.
    plan_seeds = raw.get("plan_seeds")
    if isinstance(plan_seeds, dict):
        plan_seeds.pop("_proposed_call_shape_parse_failed", None)
    return raw


def _build_handoff_from_state(memo, report, research_md_path, devforge_dir=None):
    # type: (dict, dict, Optional[str], Optional[str]) -> handoff_schema.Handoff
    """Orchestrate memo + report → Handoff dataclass construction.

    Raises ValueError from schema validators if any field fails validation.

    Mode translation: research_helper uses "bug" / "enhancement"; handoff
    schema uses {bug, feature_addition, migration, refactor, greenfield}.
    "enhancement" maps to "feature_addition" as the closest schema equivalent.
    """
    memo_mode = memo["mode"]
    # Translate memo mode to handoff schema mode.
    handoff_mode = _MEMO_MODE_TO_HANDOFF_MODE.get(memo_mode, memo_mode)
    topic_slug = memo["topic_slug"]
    date = report["date"]

    # research_path
    if research_md_path:
        research_path = research_md_path
    else:
        research_path = "research/{0}-{1}.md".format(date, topic_slug)

    # intent block
    dims = memo.get("dimensions") or {}
    symptom_snap = report.get("symptom_snapshot") or {}

    symptom_text = (
        (dims.get("symptom") or {}).get("text")
        or (dims.get("symptom") or {}).get("value")
        or symptom_snap.get("symptom")
        or ""
    ).strip()
    desired_text = (
        (dims.get("desired_behavior") or {}).get("text")
        or (dims.get("desired") or {}).get("value")
        or symptom_snap.get("desired")
        or ""
    ).strip()
    scope_text = (
        (dims.get("scope") or {}).get("text")
        or (dims.get("scope") or {}).get("value")
        or symptom_snap.get("scope")
        or ""
    ).strip()

    # verbatim_prompt: persisted by set-verbatim-prompt at Phase 0.3.
    # Caller (cmd_finalize_handoff) already guards on non-empty; read here
    # for schema construction. None-safe: schema field is Optional, but
    # the finalize guard ensures this is always a non-empty string for new
    # handoffs. Back-compat: old state files without this key return None;
    # finalize guard prevents None from reaching here for new writes.
    verbatim_prompt = (memo.get("verbatim_prompt") or "").strip() or None

    intent = handoff_schema.Intent(
        symptom_summary=symptom_text or "(not set)",
        desired_summary=desired_text or "(not set)",
        scope=_derive_scope(scope_text),
        verbatim_prompt=verbatim_prompt,
    )

    # spec_seeds block
    # Use memo_mode for hint lookup (has "enhancement"); handoff_mode for schema.
    spec_type_hint = _SPEC_TYPE_HINT_MAP.get(memo_mode, _SPEC_TYPE_HINT_MAP.get(handoff_mode, "bug_fix"))
    constraints = _build_constraints(report.get("constitution_constraints") or [])
    value_production_sites_schema = _build_value_production_sites(
        report.get("value_production_sites") or []
    )
    affected_areas = _build_affected_areas(
        report.get("fix_path_helpers") or [],
        report.get("value_production_sites") or [],
    )
    risks = _build_risks(report.get("complexity"))
    open_questions = _build_open_questions(report.get("open_uncertainties") or [])
    data_flow_chain_schema = _build_data_flow_chain(report.get("data_flow_chain"))
    value_semantics_schema = _build_value_semantics(report.get("value_semantics") or [])
    literal_archaeology_schema = _build_literal_archaeology(
        report.get("literal_archaeology") or []
    )

    spec_seeds = handoff_schema.SpecSeeds(
        spec_type_hint=spec_type_hint,
        constraints=constraints,
        affected_areas=affected_areas,
        risks=risks,
        open_questions=open_questions,
        data_flow_chain=data_flow_chain_schema,
        value_semantics=value_semantics_schema,
        value_production_sites=value_production_sites_schema,
        literal_archaeology=literal_archaeology_schema,
    )

    # plan_seeds block
    rec = report["recommended_approach"]  # caller already validated non-None
    rec_name = (rec.get("name") or "").strip()
    rec_rationale = (rec.get("rationale") or "").strip()
    if not rec_name or not rec_rationale:
        raise ValueError(
            "recommended_approach record is missing 'name' or 'rationale' "
            "(rerun set-recommended-approach with complete args)"
        )
    complexity_raw = report["complexity"]  # caller already validated non-None
    complexity_schema = handoff_schema.Complexity(
        changes=complexity_raw.get("codebase_changes") or "Low",
        risk=complexity_raw.get("risk") or "Low",
        verify_cost=complexity_raw.get("verify_cost") or "Low",
    )

    cites = rec.get("cites") or []
    cited_patterns = _build_cited_patterns(cites, report)
    layer_dest = "tbd"
    if cites:
        first_cite = cites[0]
        path_part = first_cite.rsplit(":", 1)[0] if ":" in first_cite else first_cite
        pkg = _extract_package(path_part)
        if pkg:
            layer_dest = pkg

    plan_seeds = handoff_schema.PlanSeeds(
        recommended_approach_id=_to_snake_case(rec_name),
        recommended_approach_summary=rec_rationale,
        layer_destination=layer_dest,
        layer_justification=rec.get("single_layer_justification") or "multi-layer",
        complexity=complexity_schema,
        cited_canonical_patterns=cited_patterns,
        alternatives_considered=_build_alternatives(
            report.get("approaches") or [], rec_name
        ),
        proposed_call_shape=rec.get("proposed_call_shape"),
    )

    # probe block — Step 4 smart classifier (replaces Step 3 tier=3 stub).
    unstable_site = _find_unstable_production_site(value_production_sites_schema)
    verify_step = report.get("verify_step") or {}
    # discriminator is the PASS/FAIL criterion (what result confirms primary).
    # probe is the ACTION (what to do). primary_confirms_if matches discriminator semantics.
    primary_confirms_if = (verify_step.get("discriminator") or "").strip()
    if not primary_confirms_if:
        primary_confirms_if = "tbd — populated by Step 4 probe-tier classifier"

    # Run feasibility classifier.
    feasibility_raw = report.get("probe_feasibility") or {}
    # Read test_infra from .devforge/init.yaml (init_helper.parse_yaml).
    # devforge_dir is passed in by cmd_finalize_handoff; falls back to cwd-relative
    # ".devforge" when called directly (e.g., from tests that set up state inline).
    _classifier_devforge_dir = devforge_dir if devforge_dir else ".devforge"
    test_infra_status, test_infra = _read_test_infra_status(_classifier_devforge_dir)

    classified = _classify_probe_tier(
        feasibility=feasibility_raw,
        test_infra_status=test_infra_status,
        chrome_mcp=_chrome_mcp_available(),
        test_infra=test_infra,
        topic_slug=topic_slug,
        research_date=date,
    )

    # Step 5 — override script_path when tier=1.5 and probe_scripts recorded.
    # record-probe-script is the source-of-truth for the actual script path;
    # the deterministic default from _classify_probe_tier is only a fallback.
    effective_script_path = classified["script_path"]
    if classified["tier"] == "1.5":
        probe_scripts = report.get("probe_scripts") or []
        if probe_scripts:
            effective_script_path = probe_scripts[-1]["script_path"]

    discriminator = handoff_schema.Discriminator(
        primary_confirms_if=primary_confirms_if,
        runner_up_confirms_if=classified["runner_up_confirms_if"],
        both_disproved_if=classified["both_disproved_if"],
        production_site_check=unstable_site,
    )
    feasibility_check = handoff_schema.FeasibilityCheck(
        data_shape_only=bool(feasibility_raw.get("data_shape_only")),
        auth_required=bool(feasibility_raw.get("auth_required")),
        network_dependent=bool(feasibility_raw.get("network_dependent")),
        timing_dependent=bool(feasibility_raw.get("timing_dependent")),
        is_test_code=bool(feasibility_raw.get("is_test_code")),
    )
    probe = handoff_schema.Probe(
        tier=classified["tier"],
        actor=classified["actor"],
        discriminator=discriminator,
        feasibility_check=feasibility_check,
        test_framework=classified["test_framework"],
        test_path=classified["test_path"],
        script_path=effective_script_path,
        is_first_test_for_file=classified["is_first_test_for_file"],
    )

    # downstream_links
    downstream_links = handoff_schema.DownstreamLinks(
        spec_path=None,
        plan_path=None,
        execute_task_commit_shas=[],
    )

    return handoff_schema.Handoff(
        schema_version=handoff_schema.SCHEMA_VERSION,
        research_path=research_path,
        research_completed_at=datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(timespec="seconds"),
        mode=handoff_mode,
        intent=intent,
        spec_seeds=spec_seeds,
        plan_seeds=plan_seeds,
        probe=probe,
        downstream_links=downstream_links,
        outcome=None,
    )
