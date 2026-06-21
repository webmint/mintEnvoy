"""Research report markdown renderer.

_render_report_md composes the report from memo + report state dicts.
Section order is locked — caller (cmd_render) walks once and emits to
stdout. _md_escape_cell + _derive_topic_for_render are local helpers.
"""

from __future__ import annotations

from typing import List


def _render_report_md(memo: dict, report: dict) -> str:
    """Compose the research report markdown.

    Section order (locked):
      1. Title + frontmatter (Date, Topic, Mode, Verdict)
      2. Summary
      3. Symptom (5-dim table)
      4. Codebase Findings (with Framing column)
      5. Root Cause Hypothesis
      6. Structured root cause (bug-mode + confidence ≥ Hypothesis)
      6b. Runner-up framing (when runner_up_framing is set)
      7. Hypothesis Enumeration
      8. Recommended Verify Step (when present)
      9. Approaches
      10. Constitution Constraints
      11. Complexity Assessment
      12. Value Semantics (when present)
      13. Value Production Sites (when present)
      14. Literal Archaeology (when present)
      15. Open Uncertainties (when gaps present)
      16. Next step (when verdict proceeds)
    """
    out = []  # type: List[str]
    topic = report.get("topic") or _derive_topic_for_render(memo, report)
    date = report.get("date") or "YYYY-MM-DD"
    mode = report.get("mode") or memo.get("mode") or "(unset)"
    mode_label = "Bug" if mode == "bug" else ("Enhancement" if mode == "enhancement" else "(unset)")
    verdict = report.get("verdict") or "(unset)"

    out.append("# Research: {0}\n".format(topic))
    out.append("")
    out.append("**Date**: {0}".format(date))
    out.append("**Topic**: {0}".format(topic))
    out.append("**Mode**: {0}".format(mode_label))
    out.append("**Verdict**: {0}".format(verdict))
    out.append("")

    out.append("## Summary")
    out.append("")
    out.append(report.get("summary") or "(summary unset)")
    out.append("")

    # Symptom table — 5 dims (drop unchanged_behavior from render per Plan;
    # it's used for verify cross-check, not user-facing report).
    out.append("## Symptom")
    out.append("")
    out.append("| Dimension | Value |")
    out.append("|---|---|")
    dim_map = memo.get("dimensions", {})
    for d, label in (
        ("symptom", "Symptom"),
        ("affected_area", "Affected area"),
        ("repro_or_current", "Repro / Current"),
        ("desired", "Desired"),
        ("scope", "Scope"),
    ):
        rec = dim_map.get(d, {})
        v = rec.get("value") or "(unset)"
        # Append evidence annotation for scope narrow-framing (evidence field
        # is set only when --value == "one place" was passed with --evidence).
        if d == "scope":
            scope_evidence = rec.get("evidence")
            if scope_evidence:
                v = "{0} (evidence: {1})".format(v, scope_evidence)
        out.append("| {0} | {1} |".format(label, _md_escape_cell(v)))
    out.append("")

    out.append("## Codebase Findings (WHERE)")
    out.append("")
    findings = report.get("findings", []) or []
    if findings:
        out.append("| Surface | File:line | Relevance | Framing |")
        out.append("|---|---|---|---|")
        for f in findings:
            out.append("| {0} | {1} | {2} | {3} |".format(
                _md_escape_cell(f.get("surface", "")),
                _md_escape_cell(f.get("file_line", "")),
                _md_escape_cell(f.get("relevance", "")),
                _md_escape_cell(f.get("framing", "primary")),
            ))
    else:
        out.append("(no findings recorded)")
    out.append("")

    out.append("## Root Cause Hypothesis (WHY)")
    out.append("")
    rch = report.get("root_cause_hypothesis") or "(unset)"
    out.append("**Primary hypothesis**: {0}".format(rch))
    out.append("")
    confidence = report.get("confidence") or "(unset)"
    out.append("**Confidence**: {0}".format(confidence))
    out.append("")

    src = report.get("structured_root_cause")
    if (
        mode == "bug"
        and confidence in ("Confirmed", "Hypothesis")
        and src is not None
    ):
        out.append("### Structured root cause")
        out.append("")
        out.append("| Field | Value |")
        out.append("|---|---|")
        out.append("| trigger | {0} |".format(_md_escape_cell(src.get("trigger") or "(unset)")))
        out.append("| root_cause | {0} |".format(_md_escape_cell(src.get("root_cause_systemic") or "(unset)")))
        factors = src.get("contributing_factors") or []
        if factors:
            joined = " ".join("{0}. {1}".format(i + 1, f) for i, f in enumerate(factors))
        else:
            joined = "(none)"
        out.append("| contributing_factors | {0} |".format(_md_escape_cell(joined)))
        out.append("")

    runner_up = report.get("runner_up_framing")
    if runner_up is not None:
        out.append("## Runner-up framing")
        out.append("")
        out.append("| Field | Value |")
        out.append("|---|---|")
        out.append("| Frame | {0} |".format(_md_escape_cell(runner_up.get("frame") or "(unset)")))
        out.append("| Falsifier | {0} |".format(_md_escape_cell(runner_up.get("falsifier") or "(unset)")))
        out.append("| Confidence vs primary | {0} |".format(
            _md_escape_cell(runner_up.get("confidence_vs_primary") or "(unset)")
        ))
        out.append("")

    out.append("## Hypothesis Enumeration")
    out.append("")
    hypotheses = report.get("hypotheses", []) or []
    if hypotheses:
        out.append("| Hypothesis | Falsifier (what would disprove it) | Runtime probe needed? |")
        out.append("|---|---|---|")
        for h in hypotheses:
            out.append("| {0} | {1} | {2} |".format(
                _md_escape_cell(h.get("cause", "")),
                _md_escape_cell(h.get("falsifier", "")),
                "yes" if h.get("runtime_probe_needed") else "no",
            ))
    else:
        out.append("(no hypotheses recorded — verify will fail)")
    out.append("")

    vstep = report.get("verify_step")
    if vstep is not None:
        out.append("## Recommended Verify Step")
        out.append("")
        out.append("| Sub-field | Value |")
        out.append("|---|---|")
        out.append("| probe | {0} |".format(_md_escape_cell(vstep.get("probe") or "(unset)")))
        out.append("| reproduction | {0} |".format(_md_escape_cell(vstep.get("reproduction") or "(unset)")))
        out.append("| discriminator | {0} |".format(_md_escape_cell(vstep.get("discriminator") or "(unset)")))
        out.append("")

    out.append("## Approaches (HOW to change)")
    out.append("")
    approaches = report.get("approaches", []) or []
    rec = report.get("recommended_approach") or {}
    rec_name = rec.get("name")
    if approaches:
        for ap in approaches:
            out.append("### {0}".format(ap.get("name") or "(unnamed)"))
            out.append("- **Description**: {0}".format(ap.get("description") or "(unset)"))
            out.append("- **Addresses hypothesis**: {0}".format(
                ", ".join(ap.get("addresses_hypotheses") or []) or "(none)"
            ))
            out.append("- **Does NOT cover**: {0}".format(
                ", ".join(ap.get("does_not_cover") or []) or "(none)"
            ))
            pros = ap.get("pros") or []
            cons = ap.get("cons") or []
            out.append("- **Pros**: {0}".format("; ".join(pros) or "(none)"))
            out.append("- **Cons**: {0}".format("; ".join(cons) or "(none)"))
            out.append("- **Complexity**: {0}".format(ap.get("complexity") or "(unset)"))
            out.append("")
        if rec_name:
            out.append("**Recommended approach**: {0} — {1}".format(
                rec_name, rec.get("rationale") or "(no rationale)"
            ))
            # Single-layer justification sub-section (only when present).
            single_layer_just = rec.get("single_layer_justification")
            if single_layer_just:
                out.append("")
                out.append("**Single-layer justification:**")
                out.append(single_layer_just.strip())
                cites_list = rec.get("cites") or []
                if cites_list:
                    out.append("")
                    out.append("**Cites:**")
                    for cite in cites_list:
                        out.append("- {0}".format(cite))
            # Patch 9 (V3): surface proposed_call_shape under the
            # recommended-approach section when present.
            proposed_shape_render = rec.get("proposed_call_shape")
            if proposed_shape_render:
                out.append("")
                out.append("**Proposed call shape:**")
                out.append("```")
                out.append(proposed_shape_render)
                out.append("```")
            out.append("")
    else:
        out.append("(no approaches recorded)")
        out.append("")

    out.append("## Constitution Constraints")
    out.append("")
    cc = report.get("constitution_constraints", []) or []
    if cc:
        out.append("| Rule | Impact on this change |")
        out.append("|---|---|")
        for c in cc:
            out.append("| {0} | {1} |".format(
                _md_escape_cell(c.get("rule", "")),
                _md_escape_cell(c.get("impact", "")),
            ))
    else:
        out.append("(no constitution constraints recorded)")
    out.append("")

    out.append("## Complexity Assessment")
    out.append("")
    cx = report.get("complexity")
    if cx:
        out.append("| Dimension | Rating | Notes |")
        out.append("|---|---|---|")
        out.append("| Codebase changes | {0} | {1} |".format(
            cx.get("codebase_changes") or "(unset)",
            _md_escape_cell(cx.get("codebase_notes") or ""),
        ))
        out.append("| Risk | {0} | {1} |".format(
            cx.get("risk") or "(unset)",
            _md_escape_cell(cx.get("risk_notes") or ""),
        ))
        out.append("| Verify cost | {0} | {1} |".format(
            cx.get("verify_cost") or "(unset)",
            _md_escape_cell(cx.get("verify_notes") or ""),
        ))
    else:
        out.append("(complexity unset)")
    out.append("")

    # Value Semantics (Patch 7: stability column for invariant rows).
    value_semantics = report.get("value_semantics") or []
    if value_semantics:
        out.append("## Value Semantics")
        out.append("")
        out.append("| Value | Classification | Evidence | Stability |")
        out.append("|---|---|---|---|")
        for vs in value_semantics:
            # Non-invariant rows have no stability axis — render "—". Invariant rows
            # show the stable_across_calls value (or "—" if missing, which should
            # not occur post-Patch-7 but stays defensive).
            if vs.get("classification") == "invariant":
                stability = vs.get("stable_across_calls") or "—"
            else:
                stability = "—"
            out.append("| {0} | {1} | {2} | {3} |".format(
                _md_escape_cell(vs.get("value") or ""),
                _md_escape_cell(vs.get("classification") or ""),
                _md_escape_cell(vs.get("evidence") or ""),
                _md_escape_cell(stability),
            ))
        out.append("")

    # Value Production Sites (Patch 7: where values are randomized/rewritten).
    value_production_sites = report.get("value_production_sites") or []
    if value_production_sites:
        out.append("## Value Production Sites")
        out.append("")
        out.append("| Value | File:line | Is Stable |")
        out.append("|---|---|---|")
        for site in value_production_sites:
            is_stable_str = site.get("is_stable") or "false"
            out.append("| {0} | {1} | {2} |".format(
                _md_escape_cell(site.get("value") or ""),
                _md_escape_cell(site.get("file_line") or ""),
                is_stable_str,
            ))
        out.append("")

    # Literal Archaeology (Patch 8 V3: historical-intent classification for
    # hardcoded literals the recommended approach proposes to replace).
    literal_archaeology = report.get("literal_archaeology") or []
    if literal_archaeology:
        out.append("## Literal Archaeology")
        out.append("")
        out.append("| Literal | File:line | Introduced by | When | Commit subject | Intent |")
        out.append("|---|---|---|---|---|---|")
        for row in literal_archaeology:
            out.append("| {0} | {1} | {2} | {3} | {4} | {5} |".format(
                _md_escape_cell(row.get("literal") or ""),
                _md_escape_cell(row.get("file_line") or ""),
                _md_escape_cell(row.get("introduced_by") or ""),
                _md_escape_cell(row.get("introduced_when") or ""),
                _md_escape_cell(row.get("commit_subject") or ""),
                _md_escape_cell(row.get("intent") or ""),
            ))
        out.append("")

    gaps = memo.get("gaps") or []
    if gaps:
        out.append("## Open Uncertainties")
        out.append("")
        for g in gaps:
            out.append("- [NEEDS CLARIFICATION: {0} — {1}]".format(
                g.get("dimension", ""), g.get("description", "")
            ))
        out.append("")

    next_step = report.get("next_step_text")
    if next_step:
        out.append(next_step.rstrip("\n"))
        out.append("")

    return "\n".join(out).rstrip() + "\n"


def _md_escape_cell(text: str) -> str:
    """Escape pipe + newline so the value survives a markdown table cell."""
    if text is None:
        return ""
    return text.replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def _derive_topic_for_render(memo: dict, report: dict) -> str:
    """Best-effort topic for the rendered title.

    Prefers report.topic; falls back to memo.dimensions.symptom.value;
    final fallback is "(untitled)".
    """
    t = report.get("topic")
    if t:
        return t
    sym = memo.get("dimensions", {}).get("symptom", {}).get("value")
    if sym:
        return sym
    return "(untitled)"
