"""Spec render: 9-section markdown composer + approval summary + plan-handoff block."""

from __future__ import annotations

from typing import Any, Dict, List

from ._schema import (
    AC_FRAMING_LINE,
    AC_SUBSECTION_ENUM,
    COVERAGE_RULE_BANNER,
    CONSTRAINT_KIND_ENUM,
    CONSTRAINT_KIND_LABEL,
    DESIGN_SOURCE_DEFAULT,
    DP_STATUS_ENUM,
    SPEC_STATUS_DEFAULT,
    SUBSECTION_HEADING_BY_KEY,
    _SUBSECTION_RENDER_ORDER,
)


def _render_section_acs(
    state: Dict[str, Any], subsection: str,
) -> List[str]:
    lines: List[str] = []
    acs = [
        a for a in state["acceptance_criteria"]
        if a.get("subsection") == subsection
    ]
    if acs:
        for a in acs:
            lines.append("- [ ] **{0}**: {1}".format(
                a.get("ac_id", ""), a.get("statement", ""),
            ))
            if a.get("verification_command"):
                lines.append(
                    "  > Verification: {0}".format(
                        a["verification_command"]
                    )
                )
            if a.get("test_anchor"):
                lines.append(
                    "  > Test: {0}".format(a["test_anchor"])
                )
    else:
        reason = state["ac_subsection_na"].get(subsection, "")
        if reason:
            lines.append("N/A — {0}".format(reason))
        else:
            lines.append("_(no AC recorded)_")
    return lines


def _render_open_questions_section(state: Dict[str, Any]) -> List[str]:
    """Compose §8 — explicit open questions + DP-derived entries."""
    resolutions_by_id: Dict[str, Dict[str, Any]] = {
        r["question_id"]: r
        for r in state.get("open_question_resolutions", [])
    }
    lines: List[str] = ["## 8. Open Questions", ""]
    has_entry = False

    for oq in state["open_questions"]:
        has_entry = True
        qid = oq.get("question_id", "")
        body = "**{0}**: {1}".format(qid, oq.get("content", ""))
        no_dp = (oq.get("category_no_dp_reason") or "").strip()
        if no_dp:
            body = body + " _(no-DP rationale: {0})_".format(no_dp)
        if qid in resolutions_by_id:
            r = resolutions_by_id[qid]
            lines.append(
                "- ~~{0}~~ — resolved in {1} on {2}: {3}".format(
                    body,
                    r.get("resolution_phase", ""),
                    r.get("resolution_timestamp", ""),
                    r.get("resolution_text", ""),
                )
            )
        else:
            lines.append("- " + body)

    for dp in state["decision_points"]:
        status = dp.get("status")
        if status == "default_applied":
            has_entry = True
            lines.append(
                "- **{0}** [default applied]: {1} → default: {2}".format(
                    dp.get("dp_id", ""),
                    dp.get("description", ""),
                    dp.get("default_applied", ""),
                )
            )
        elif status == "deferred_open_question":
            has_entry = True
            lines.append(
                "- **{0}** [deferred to open question]: {1} ({2})".format(
                    dp.get("dp_id", ""),
                    dp.get("description", ""),
                    dp.get("deferral_reason", ""),
                )
            )
        elif status == "no_DP_in_category":
            has_entry = True
            lines.append(
                "- **{0}** [no DP in category {1}]: {2}".format(
                    dp.get("dp_id", ""),
                    dp.get("category", ""),
                    dp.get("description", ""),
                )
            )

    if not has_entry:
        lines.append("_(no open questions recorded)_")
    lines.append("")
    return lines


def render_spec(state: Dict[str, Any]) -> str:
    """Compose the 9-section spec markdown.

    Determinism: byte-identical input state → byte-identical output. No
    timestamps, no environment-dependent values.
    """
    out: List[str] = []
    name = state.get("feature_name") or "Feature"
    date = state.get("date") or ""
    status = state.get("status") or SPEC_STATUS_DEFAULT

    out.append("# Spec: {0}".format(name))
    out.append("")
    design_source = state.get("design_source", DESIGN_SOURCE_DEFAULT) or DESIGN_SOURCE_DEFAULT
    out.append("**Date**: {0}".format(date))
    out.append("**Status**: {0}".format(status))
    out.append("**Design source**: {0}".format(design_source))
    out.append("**Author**: Claude + User")
    out.append("")

    out.append("## 1. Overview")
    out.append("")
    out.append(state.get("overview") or "_(no overview recorded)_")
    out.append("")

    out.append("## 2. Current State")
    out.append("")
    out.append(state.get("current_state") or "_(no current state recorded)_")
    out.append("")

    out.append("## 3. Desired Behavior")
    out.append("")
    out.append(
        state.get("desired_behavior") or "_(no desired behavior recorded)_"
    )
    out.append("")

    out.append("## 4. Affected Areas")
    out.append("")
    out.append("| Area | Files | Impact |")
    out.append("|------|-------|--------|")
    if state["affected_areas"]:
        for a in state["affected_areas"]:
            out.append("| {0} | {1} | {2} |".format(
                a.get("area", ""),
                ", ".join(a.get("files", [])),
                a.get("impact", ""),
            ))
    else:
        out.append("| _(none)_ | _(none)_ | _(none)_ |")
    out.append("")

    out.append("## 5. Acceptance Criteria")
    out.append("")
    out.append(AC_FRAMING_LINE)
    out.append("")
    for subsection in AC_SUBSECTION_ENUM:
        heading_num, heading_text = SUBSECTION_HEADING_BY_KEY[subsection]
        out.append("### {0} {1}".format(heading_num, heading_text))
        out.append("")
        out.extend(_render_section_acs(state, subsection))
        out.append("")

    out.append("## 6. Out of Scope")
    out.append("")
    out.append(COVERAGE_RULE_BANNER)
    out.append("")
    if state["out_of_scope"]:
        for o in state["out_of_scope"]:
            ref = (o.get("finding_ref") or "").strip()
            suffix = " — {0}".format(ref) if ref else ""
            out.append("- NOT included: {0}{1}".format(
                o.get("content", ""), suffix,
            ))
    else:
        out.append("- NOT included: _(none recorded)_")
    out.append("")

    out.append("## 7. Technical Constraints")
    out.append("")
    has_constraint = False
    for kind in CONSTRAINT_KIND_ENUM:
        for c in state["constraints"]:
            if c.get("kind") != kind:
                continue
            has_constraint = True
            label = CONSTRAINT_KIND_LABEL[kind]
            content = c.get("content", "")
            if kind == "nfr":
                quant = c.get("quantifier", "")
                if quant:
                    out.append("- {0} ({1}): {2}".format(label, quant, content))
                else:
                    out.append("- {0}: {1}".format(label, content))
            elif kind == "constitution_anchor":
                ref = c.get("constitution_ref", "")
                if ref:
                    out.append("- {0} §{1}: {2}".format(
                        label, ref.lstrip("§"), content,
                    ))
                else:
                    out.append("- {0}: {1}".format(label, content))
            elif kind == "external_system":
                via = c.get("protocol") or c.get("contract_doc_ref") or ""
                if via:
                    out.append("- {0} ({1}): {2}".format(label, via, content))
                else:
                    out.append("- {0}: {1}".format(label, content))
            else:
                out.append("- {0}: {1}".format(label, content))
    if not has_constraint:
        out.append("- _(no constraints recorded)_")
    out.append("")

    out.extend(_render_open_questions_section(state))

    out.append("## 9. Risks")
    out.append("")
    out.append("| Risk | Likelihood | Impact | Mitigation |")
    out.append("|------|-----------|--------|------------|")
    if state["risks"]:
        for r in state["risks"]:
            out.append("| {0} | {1} | {2} | {3} |".format(
                r.get("risk", ""),
                r.get("likelihood", ""),
                r.get("impact", ""),
                r.get("mitigation", ""),
            ))
    else:
        out.append("| _(none)_ | _(none)_ | _(none)_ | _(none)_ |")
    out.append("")

    return "\n".join(out).rstrip() + "\n"


def _canonicalize_for_compare(b: bytes) -> bytes:
    """Normalize rendered bytes for tamper-detection comparison.

    Normalization rules (cosmetic-only):
    - CRLF / CR line endings collapsed to LF.
    - Trailing whitespace stripped from each line.
    - Single trailing newline at EOF (no extra blank lines beyond).

    Content changes (added/removed lines, character substitutions inside
    a line) survive normalization and surface as drift.
    """
    text = b.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines).rstrip("\n") + "\n"
    return text.encode("utf-8")


def _approval_summary(state: Dict[str, Any]) -> str:
    """Compose v3 4-bullet summary (Variance rule #9, verbatim shape)."""
    number = state.get("spec_number") or "NNN"
    name = state.get("feature_name") or "feature"
    overview = (state.get("overview") or "_(no overview)_").strip()
    if len(overview) > 240:
        overview = overview[:237] + "..."
    file_count = sum(
        len(a.get("files", [])) for a in state["affected_areas"]
    )
    area_count = len(state["affected_areas"])
    ac_count = len(state["acceptance_criteria"])
    subsection_set = {
        a.get("subsection") for a in state["acceptance_criteria"]
        if a.get("subsection")
    }
    subsection_count = len(subsection_set)
    if state["out_of_scope"]:
        oos_short = "; ".join(
            (o.get("content", "") or "").strip()[:80]
            for o in state["out_of_scope"][:3]
        )
        if len(state["out_of_scope"]) > 3:
            oos_short += "; …"
    else:
        oos_short = "_(none)_"
    return (
        "I've created the specification at "
        "`specs/{n}-{f}/spec.md`. Key points:\n"
        "- **What changes**: {ov}\n"
        "- **Files affected**: {fc} files across {ac} areas\n"
        "- **Acceptance criteria**: {acc} testable criteria across "
        "{sc} AC categories\n"
        "- **Out of scope**: {oos}\n"
        "\n"
        "Please review and either approve or request changes. Once "
        "approved, run `/plan` to create the technical implementation "
        "plan."
    ).format(
        n=number, f=name, ov=overview, fc=file_count, ac=area_count,
        acc=ac_count, sc=subsection_count, oos=oos_short,
    )


def _plan_handoff_block(state: Dict[str, Any]) -> str:
    number = state.get("spec_number") or "NNN"
    name = state.get("feature_name") or "feature"
    spec_type = state.get("spec_type") or "<unset>"
    status = state.get("status") or "Draft"
    acs = state["acceptance_criteria"]
    ac_count = len(acs)
    sub_counts: Dict[str, int] = {sub: 0 for sub in AC_SUBSECTION_ENUM}
    for ac in acs:
        s = ac.get("subsection")
        if s in sub_counts:
            sub_counts[s] += 1
    sub_active = sum(1 for v in sub_counts.values() if v > 0)
    sub_count_strs = ", ".join(
        "{0}: {1}".format(label, sub_counts[sub])
        for sub, label in zip(
            AC_SUBSECTION_ENUM, _SUBSECTION_RENDER_ORDER,
        )
    )
    dp_by_status: Dict[str, int] = {s: 0 for s in DP_STATUS_ENUM}
    for d in state["decision_points"]:
        st = d.get("status")
        if st in dp_by_status:
            dp_by_status[st] += 1
    aff_count = len(state["affected_areas"])
    packages: List[str] = []
    seen: set = set()
    for a in state["affected_areas"]:
        for f in a.get("files", []):
            parts = (f or "").split("/")
            if len(parts) >= 2:
                pkg = parts[0]
                if pkg and pkg not in seen:
                    seen.add(pkg)
                    packages.append(pkg)
    pkg_list = ", ".join(packages) if packages else "(none)"
    return (
        "## Manual next step — run /plan\n"
        "\n"
        "A structured handoff (specs/{n}-{f}/handoff.json) is written for "
        "/plan. /plan auto-discovers it on its first run and reads the "
        "upstream plan-seeds — but you still launch /plan manually (there is "
        "no auto-dispatch from /specify). Restart Claude Code (exit and "
        "relaunch the CLI/app so the newly installed command is picked up), "
        "then run the command below in this repo. The spec path is explicit "
        "so /plan does not need most-recent-spec discovery:\n"
        "\n"
        "~~~\n"
        "/plan specs/{n}-{f}/spec.md\n"
        "~~~\n"
        "\n"
        "Minimum handoff data:\n"
        "- Spec status: {status}\n"
        "- Spec type: {st}\n"
        "- AC count: {acc} across {sca} subsections ({sub_counts})\n"
        "- Decision-point coverage: {ans} answered, {da} default-applied, "
        "{do} deferred-OOS, {dq} deferred-open-question\n"
        "- Affected areas: {aa} across {pk}\n"
        "- Out-of-scope items: {oos}\n"
        "- Open questions: {oq}\n"
        "- Constraints: {cn}\n"
        "- Risks: {rk}\n"
        "- Phase 1.5 finding coverage: 100% (all findings landed)\n"
        "\n"
        "Reference: specs/{n}-{f}/spec.md"
    ).format(
        n=number, f=name, status=status, st=spec_type,
        acc=ac_count, sca=sub_active, sub_counts=sub_count_strs,
        ans=dp_by_status["answered"],
        da=dp_by_status["default_applied"],
        do=dp_by_status["deferred_OOS"],
        dq=dp_by_status["deferred_open_question"],
        aa=aff_count, pk=pkg_list,
        oos=len(state["out_of_scope"]),
        oq=len(state["open_questions"]),
        cn=len(state["constraints"]),
        rk=len(state["risks"]),
    )
