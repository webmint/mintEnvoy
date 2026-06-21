"""_inline -- render the Phase 6 inline console summary block.

Implements the 'Audit Complete' console output block specified in
Phase 6 of the /audit command spec.

Design:
  - render_inline_summary(report_dict) -> str
      Produces the ## Audit Complete markdown/console block.
      - Count-first (counts on the first line after the header, per CLAUDE.md
        audit-format discipline).
      - Top 5 priorities listed by name.
      - Agents skipped rendered (or "none" if empty).
      - Discarded count with verbatim-quote-failures called out.
      - Report path present.
      - "Not committed" note.
      - Adversarial NOTE.

Stdlib only.  Python 3.8+.
"""

from typing import Dict, List

# ---------------------------------------------------------------------------
# Severity ordering (for counts line)
# ---------------------------------------------------------------------------

_SEVERITY_ORDER = ("Critical", "High", "Medium", "Info")


# ---------------------------------------------------------------------------
# render_inline_summary
# ---------------------------------------------------------------------------


def render_inline_summary(report_dict):
    # type: (dict) -> str
    """Render the ## Audit Complete inline console block.

    Parameters
    ----------
    report_dict : dict  same shape as accepted by render_report in _report.py.
        Keys used:
          mode                  : "narrow" | "hotspot" | "broad"
          scope_description     : str
          findings              : list of ParsedFinding-like dicts
                                  (the headline set: confirmed + contested)
          dismissed             : list of dismissed-bucket finding dicts (appendix)
          uncertain             : list of low-stakes uncertain finding dicts (appendix)
          top10                 : list[str]  finding_ids in priority order
          agents_skipped        : list[str]
          discard_counts        : dict (keys: file_missing, line_oob,
                                  quote_mismatch, evidence_empty, pattern_missing)
          consensus             : dict  finding_id -> list[str] agent names
          recurring_unresolved  : list[str | dict]
          out_path              : str  (path the report was written to)

    Returns
    -------
    str  the complete inline block (ends with a newline).
    """
    mode = report_dict.get("mode") or "broad"
    scope_description = report_dict.get("scope_description") or "(unset)"
    findings = report_dict.get("findings") or []
    dismissed_list = report_dict.get("dismissed") or []
    uncertain_list = report_dict.get("uncertain") or []
    top10_ids = report_dict.get("top10") or []
    agents_skipped = report_dict.get("agents_skipped") or []
    discard_counts = report_dict.get("discard_counts") or {}
    consensus = report_dict.get("consensus") or {}
    recurring_unresolved = report_dict.get("recurring_unresolved") or []
    out_path = report_dict.get("out_path") or ""

    # Assign finding_ids if not present (must match _report.py convention)
    numbered = []  # type: List[tuple]
    for i, f in enumerate(findings):
        fid = f.get("finding_id") or "F-{0:03d}".format(i + 1)
        numbered.append((fid, f))

    id_to_finding = {fid: f for fid, f in numbered}  # type: Dict[str, dict]

    # Count by severity
    counts = {sev: 0 for sev in _SEVERITY_ORDER}
    for _, f in numbered:
        sev = f.get("severity") or "Info"
        if sev in counts:
            counts[sev] += 1

    # Confidence-gate counts (plan 19 Change D).
    # contested = [CONTESTED]-tagged findings in the headline set.
    # confirmed = headline findings that are NOT [CONTESTED]-tagged.
    contested_count = sum(
        1 for _, f in numbered if "[CONTESTED]" in (f.get("tags") or [])
    )
    confirmed_count = len(numbered) - contested_count
    dismissed_count = len(dismissed_list)
    uncertain_count = len(uncertain_list)

    # Cross-agent consensus count
    consensus_count = sum(
        1 for fid, _ in numbered if fid in consensus and len(consensus[fid]) >= 2
    )

    # Discard totals
    total_discarded = sum(discard_counts.get(k, 0) for k in (
        "file_missing", "line_oob", "quote_mismatch", "evidence_empty", "pattern_missing"
    ))
    quote_fail = discard_counts.get("quote_mismatch", 0)

    # Top 5 priority list
    top_n = 5
    top_ids = list(top10_ids[:top_n])

    out = []  # type: List[str]
    out.append("## Audit Complete")
    out.append("")

    # Count-first line (CLAUDE.md audit-format discipline).
    # Reports confidence-gate split: confirmed / dismissed / uncertain / contested.
    out.append(
        "**Scope**: {0}".format(scope_description)
    )
    out.append(
        "**Findings**: {0} Critical, {1} High, {2} Medium, {3} Info".format(
            counts["Critical"], counts["High"], counts["Medium"], counts["Info"]
        )
    )
    out.append(
        "**Confirmed**: {0} | **Contested**: {1} | **Dismissed**: {2} | **Uncertain**: {3}".format(
            confirmed_count, contested_count, dismissed_count, uncertain_count
        )
    )
    out.append("**Cross-agent consensus**: {0}".format(consensus_count))
    out.append("**Recurring (unresolved)**: {0}".format(len(recurring_unresolved)))
    out.append(
        "**Agents skipped**: {0}".format(
            ", ".join(agents_skipped) if agents_skipped else "none"
        )
    )
    out.append(
        "**Findings discarded by validation**: {0} (verbatim-quote failures: {1})".format(
            total_discarded, quote_fail
        )
    )
    out.append("")

    out.append("### Top 5 Priorities")
    if top_ids:
        for rank, fid in enumerate(top_ids, start=1):
            f = id_to_finding.get(fid)
            if f is None:
                out.append("{0}. [{1}] (not in findings list)".format(rank, fid))
                continue
            file_ = f.get("file") or "(unknown)"
            line_ = f.get("line", -1)
            if isinstance(line_, int) and line_ >= 1:
                location = "{0}:{1}".format(file_, line_)
            else:
                location = file_
            pattern = (f.get("pattern") or "").strip()
            why = (f.get("why") or f.get("explanation") or "").strip()
            desc = pattern or (why.splitlines()[0][:100] if why else "(no description)")
            severity = f.get("severity") or "Info"
            out.append(
                "{0}. [{1}] {2} — {3}".format(rank, severity, location, desc)
            )
    else:
        out.append("(no findings)")
    out.append("")

    if out_path:
        out.append("Full report: {0}".format(out_path))
        out.append("")

    out.append(
        "Not committed — review, then commit if you want audit history in git, "
        "or delete."
    )
    out.append("")
    out.append(
        "NOTE: /audit is adversarial. Every finding is grounded in a verbatim"
    )
    out.append(
        "code quote and cross-examined before ranking. \"Speculative\" findings"
    )
    out.append(
        "are hypotheses, not verdicts. Dismissed findings are in the appendix."
    )

    return "\n".join(out) + "\n"
