"""_report -- render the final audit markdown report and write to disk.

Implements Phase 5 of /audit:
  - render_report(report_dict) -> str    full markdown per the draft format
  - compute_out_path(audits_dir, date_str) -> str   collision-safe path
  - write_report(audits_dir, date_str, content) -> str   atomic write
  - ensure_gitignore(audits_dir)         idempotent .gitignore creation

Bucketing rule for Findings by File
-------------------------------------
Each finding is placed in exactly ONE sub-group using the first matching
rule below (priority order):

  1. "[CONSTITUTION-VIOLATION]" in tags           -> constitution
     (cross-cutting override; orthogonal to the finding's declared category)
  2. finding.get("category") mapped via explicit dict:
       mislogic      -> mislogic
       system_design -> system_design
       best_practice -> best_practice
       duplication   -> duplication
       security      -> security
       blind_spot    -> mislogic  (shares display bucket)
  3. missing / unknown category                   -> mislogic

Rationale: category is producer-declared (an owned vocabulary field, like
severity); the renderer maps it to a bucket without inferring anything from
who produced the finding.  The agent-name heuristic (agent=="architect" ->
cross-module, agent=="security-reviewer" -> security) is retired: those
agents now declare category on the finding itself, and any agent that finds
a security or design problem can correctly categorise it.

Empty-section policy
--------------------
The findings body is rendered as a single "## Findings by File" section.
Files with findings appear as level-3 headers (### <path>), sorted by path
(tree order).  Within each file, sub-groups appear as level-4 headers
(#### <label>), in _BUCKET_ORDER order; empty sub-groups are omitted.
Within each sub-group, findings are sorted by severity (Critical->High->
Medium->Info), then by finding_id ascending.

A finding with a missing/empty file field is grouped under "(unknown file)",
sorted last.

If there are zero findings, "## Findings by File" is emitted with a
"(none)" line.

The ## Summary section always renders, even if all counts are zero.

Top-N selection
---------------
narrow mode -> Top 5 (shown in the ## Top 5 Priorities section header too).
all other modes -> Top 10.

Stdlib only.  Python 3.8+.
"""

import os
import tempfile
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Bucketing helpers
# ---------------------------------------------------------------------------

_BUCKET_MISLOGIC = "mislogic"
_BUCKET_SYSTEM_DESIGN = "system_design"
_BUCKET_BEST_PRACTICE = "best_practice"
_BUCKET_DUPLICATION = "duplication"
_BUCKET_SECURITY = "security"
_BUCKET_CONSTITUTION = "constitution"

_BUCKET_SHORT_LABELS = {
    _BUCKET_MISLOGIC: "Mislogic",
    _BUCKET_SYSTEM_DESIGN: "System Design",
    _BUCKET_BEST_PRACTICE: "Best Practices",
    _BUCKET_DUPLICATION: "Duplication",
    _BUCKET_SECURITY: "Security",
    _BUCKET_CONSTITUTION: "Constitution Violations",
}

_BUCKET_ORDER = [
    _BUCKET_MISLOGIC,
    _BUCKET_SYSTEM_DESIGN,
    _BUCKET_BEST_PRACTICE,
    _BUCKET_DUPLICATION,
    _BUCKET_SECURITY,
    _BUCKET_CONSTITUTION,
]

_SEVERITY_ORDER = ["Critical", "High", "Medium", "Info"]


_CATEGORY_TO_BUCKET = {
    "mislogic": _BUCKET_MISLOGIC,
    "system_design": _BUCKET_SYSTEM_DESIGN,
    "best_practice": _BUCKET_BEST_PRACTICE,
    "duplication": _BUCKET_DUPLICATION,
    "security": _BUCKET_SECURITY,
    "blind_spot": _BUCKET_MISLOGIC,  # shares the mislogic display bucket
}


def _bucket_finding(finding):
    # type: (dict) -> str
    """Return the bucket name for a single finding using the priority rules.

    Priority:
      1. "[CONSTITUTION-VIOLATION]" in tags -> constitution (cross-cutting override)
      2. finding.get("category") mapped via _CATEGORY_TO_BUCKET
      3. missing or unknown category -> mislogic (safe default)
    """
    tags = finding.get("tags") or []
    if "[CONSTITUTION-VIOLATION]" in tags:
        return _BUCKET_CONSTITUTION
    cat = finding.get("category")
    return _CATEGORY_TO_BUCKET.get(cat, _BUCKET_MISLOGIC)


# ---------------------------------------------------------------------------
# Finding body formatter
# ---------------------------------------------------------------------------


def _merged_suffix(finding):
    # type: (dict) -> str
    """Return ' (raised by N)' when merged_count > 1, else empty string.

    Backward-compatible: missing key or non-int value -> no annotation.
    merged_count == 1 -> no annotation (single finding, no dedup occurred).
    """
    mc = finding.get("merged_count")
    if isinstance(mc, int) and not isinstance(mc, bool) and mc > 1:
        return " (raised by {0})".format(mc)
    return ""


def _render_finding_body(finding, finding_id, severity):
    # type: (dict, str, str) -> str
    """Render a single finding in the file-grouped report format.

    The first line includes the finding_id, severity (inline), line number,
    and title.  The file path is omitted — it is the enclosing ### header.
    The `:line` token is omitted entirely when line is -1 or unknown.

    When merged_count > 1 (consensus stage collapsed duplicates into this
    finding), a '(raised by N)' annotation is appended to the title line.

    Detail block (Evidence, Why, Remediation, Confidence+Tags) is unchanged
    from the previous format.
    """
    line_ = finding.get("line", -1)
    if isinstance(line_, int) and line_ >= 1:
        location = ":{0}".format(line_)
    else:
        location = ""

    # Title: use pattern if present, else fall back to why's first line
    pattern = (finding.get("pattern") or "").strip()
    why = (finding.get("why") or finding.get("explanation") or "").strip()
    if pattern:
        title = pattern
    elif why:
        title = why.splitlines()[0][:120]
    else:
        title = "(no description)"

    merged = _merged_suffix(finding)
    evidence = (finding.get("evidence") or "").strip()
    confidence = finding.get("confidence") or "Speculative"
    remediation = (
        finding.get("remediation") or finding.get("suggested_fix") or ""
    ).strip()
    tags = finding.get("tags") or []
    tags_str = " ".join(tags) if tags else ""

    lines = []
    id_prefix = "[{0}] ".format(finding_id) if finding_id else ""
    sev_prefix = "[{0}] ".format(severity) if severity else ""
    if location:
        lines.append(
            "- {0}{1}{2} — {3}{4}".format(id_prefix, sev_prefix, location, title, merged)
        )
    else:
        lines.append(
            "- {0}{1}— {2}{3}".format(id_prefix, sev_prefix, title, merged)
        )
    lines.append("  Evidence:")
    lines.append("  ```")
    if evidence:
        lines.append("  " + evidence.replace("\n", "\n  "))
    else:
        lines.append("  (no verbatim evidence recorded)")
    lines.append("  ```")
    if why:
        lines.append("  Why it's wrong: {0}".format(why))
    if remediation:
        lines.append("  Remediation: {0}".format(remediation))
    conf_line = "  Confidence: {0}".format(confidence)
    if tags_str:
        conf_line += "  Tags: {0}".format(tags_str)
    lines.append(conf_line)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# File-grouped findings section renderer
# ---------------------------------------------------------------------------

_SEVERITY_RANK = {sev: i for i, sev in enumerate(_SEVERITY_ORDER)}
_UNKNOWN_FILE_SENTINEL = "(unknown file)"


def _render_findings_by_file(numbered, out):
    # type: (List, List) -> None
    """Render the ## Findings by File section into *out*.

    Parameters
    ----------
    numbered : list of (finding_id: str, finding: dict)
    out      : list of str  -- output lines are appended here
    """
    out.append("## Findings by File")

    if not numbered:
        out.append("(none)")
        out.append("")
        return

    # Group by file path
    file_to_findings = {}  # type: Dict[str, List]
    for fid, f in numbered:
        file_key = (f.get("file") or "").strip() or _UNKNOWN_FILE_SENTINEL
        if file_key not in file_to_findings:
            file_to_findings[file_key] = []
        file_to_findings[file_key].append((fid, f))

    # Sort files: normal paths first (alphabetically), unknown last
    def _file_sort_key(path):
        # type: (str) -> tuple
        return (1 if path == _UNKNOWN_FILE_SENTINEL else 0, path)

    sorted_files = sorted(file_to_findings.keys(), key=_file_sort_key)

    for file_path in sorted_files:
        file_findings = file_to_findings[file_path]
        out.append("")
        out.append("### {0}".format(file_path))
        out.append("")

        # Group by bucket within this file
        bucket_to_findings = {b: [] for b in _BUCKET_ORDER}  # type: Dict[str, List]
        for fid, f in file_findings:
            bucket = _bucket_finding(f)
            bucket_to_findings[bucket].append((fid, f))

        # Within each bucket, sort by severity then finding_id
        for bucket in _BUCKET_ORDER:
            findings_in_bucket = bucket_to_findings[bucket]
            if not findings_in_bucket:
                continue

            findings_in_bucket.sort(
                key=lambda pair: (
                    _SEVERITY_RANK.get(pair[1].get("severity") or "Info", 3),
                    pair[0],
                )
            )

            label = _BUCKET_SHORT_LABELS[bucket]
            out.append("#### {0}".format(label))
            for fid, f in findings_in_bucket:
                severity = f.get("severity") or "Info"
                out.append(_render_finding_body(f, fid, severity))
                out.append("")

    out.append("")


# ---------------------------------------------------------------------------
# render_report
# ---------------------------------------------------------------------------


def render_report(report_dict):
    # type: (dict) -> str
    """Render the full audit markdown report from the pipeline output dict.

    Parameters
    ----------
    report_dict : dict with keys:
        mode                      : "narrow" | "hotspot" | "broad"
        audit_date                : "YYYY-MM-DD"
        scope_description         : str
        scope_files               : list[str]
        agents_run                : list[str]
        agents_skipped            : list[str]
        agents_failed             : list[dict {name, reason}]  (may be absent)
        findings                  : list of ParsedFinding-like dicts
            each dict has: agent, severity, file, line, pattern, confidence,
            evidence, why, remediation, tags, (optional) finding_id,
            (optional) score, (optional) pass_count.
            This must be the confirmed ∪ contested union (findings whose
            [CONTESTED] tag marks them as high-stakes-uncertain are included
            here; they are NOT passed via a separate report_dict key).
        top10                     : list[str]  finding_ids in priority order
        source_root               : str
        framework                 : str
        language                  : str
        recurring_resolved        : list[str]   (descriptions of resolved issues)
        recurring_unresolved      : list[str]   (descriptions of unresolved issues)
        recurring_reviews_consulted : list[str]
        discard_counts            : dict keys: file_missing, line_oob,
                                    quote_mismatch, evidence_empty, pattern_missing
        consensus                 : dict (finding_id -> [agent names]);
                                    multi-pass passes {} — the Summary cross-agent
                                    count now derives from [CROSS-AGENT] tags, not
                                    this dict
        next_candidates           : list[dict]  (hotspot mode only)
        passes_run                : int  (optional, default 1).  When >= 2, a
                                    "Passes run" line is added to the ## Summary
                                    block.  When absent or 1 (single-pass), the
                                    Summary is byte-identical to pre-multipass output.

    Returns
    -------
    str  full markdown report.
    """
    mode = report_dict.get("mode") or "broad"
    audit_date = report_dict.get("audit_date") or ""
    scope_description = report_dict.get("scope_description") or ""
    scope_files = report_dict.get("scope_files") or []
    agents_run = report_dict.get("agents_run") or []
    agents_skipped = report_dict.get("agents_skipped") or []
    agents_failed = report_dict.get("agents_failed") or []
    findings = report_dict.get("findings") or []
    top10_ids = report_dict.get("top10") or []
    source_root = report_dict.get("source_root") or "(unset)"
    framework = report_dict.get("framework") or "(unset)"
    language = report_dict.get("language") or "(unset)"
    recurring_resolved = report_dict.get("recurring_resolved") or []
    recurring_unresolved = report_dict.get("recurring_unresolved") or []
    recurring_reviews_consulted = report_dict.get("recurring_reviews_consulted") or []
    discard_counts = report_dict.get("discard_counts") or {}
    next_candidates = report_dict.get("next_candidates") or []
    # passes_run: optional int, default 1.  Values <= 1 are treated as single-pass
    # and produce no extra output — preserving byte-identical single-pass reports.
    raw_passes_run = report_dict.get("passes_run", 1)
    passes_run = int(raw_passes_run) if isinstance(raw_passes_run, int) and not isinstance(raw_passes_run, bool) else 1

    # Assign finding_ids if not already present (F-001, F-002, ...)
    numbered = []
    for i, f in enumerate(findings):
        fid = f.get("finding_id") or "F-{0:03d}".format(i + 1)
        numbered.append((fid, f))

    # Build finding_id -> finding dict for top10 lookup
    id_to_finding = {fid: f for fid, f in numbered}  # type: Dict[str, dict]

    top_n = 5 if mode == "narrow" else 10
    top10_label = "Top 5 Priorities" if mode == "narrow" else "Top 10 Priorities"

    # -- Header block --------------------------------------------------------
    out = []  # type: List[str]
    out.append("# Audit Report — {0}".format(audit_date))
    out.append("")

    # Format agents_run list (skipped agents noted inline)
    agents_run_str = ", ".join(agents_run) if agents_run else "(none)"
    if agents_skipped:
        agents_run_str += " (skipped — not installed: {0})".format(
            ", ".join(agents_skipped)
        )

    recurring_consulted_str = (
        ", ".join(recurring_reviews_consulted)
        if recurring_reviews_consulted
        else "none"
    )

    out.append("**Scope**: {0}".format(scope_description))
    out.append("**Files audited**: {0}".format(len(scope_files)))
    out.append("**Agents invoked**: {0}".format(agents_run_str))
    out.append(
        "**Recurring-issue reviews consulted**: {0}".format(recurring_consulted_str)
    )
    out.append("**Source Root**: {0}".format(source_root))
    out.append("**Framework / Language**: {0} / {1}".format(framework, language))
    out.append("")

    # Dismissed and uncertain appendix lists (plan 19 Change D).
    # Both may be absent from older report dicts → default to [].
    dismissed_list = report_dict.get("dismissed") or []
    uncertain_list = report_dict.get("uncertain") or []

    # -- Top N Priorities ----------------------------------------------------
    out.append("## {0}".format(top10_label))
    out.append("Force-ranked across all buckets. Fix these first.")
    if top10_ids:
        for rank, fid in enumerate(top10_ids[:top_n], start=1):
            f = id_to_finding.get(fid)
            if f is None:
                out.append(
                    "{0}. [{1}] (finding not in report)".format(rank, fid)
                )
                continue
            severity = f.get("severity") or "Info"
            file_ = f.get("file") or "(unknown)"
            line_ = f.get("line", -1)
            if isinstance(line_, int) and line_ >= 1:
                location = "{0}:{1}".format(file_, line_)
            else:
                location = file_
            pattern = (f.get("pattern") or "").strip()
            why = (f.get("why") or f.get("explanation") or "").strip()
            desc = pattern or (why.splitlines()[0][:120] if why else "(no description)")
            desc = desc + _merged_suffix(f)
            confidence = f.get("confidence") or "Speculative"
            tags = f.get("tags") or []
            tags_str = " ".join(tags) if tags else ""
            score = f.get("score")
            score_str = " score={0:.1f}".format(score) if isinstance(score, (int, float)) else ""
            line_parts = [
                "{0}. [{1}] {2} —".format(rank, severity, location),
                desc,
                "[{0}]{1}".format(confidence, score_str),
            ]
            if tags_str:
                line_parts.append(tags_str)
            out.append(" ".join(line_parts))
            # Note: [CONTESTED]-tagged findings render in the headline (D7).
            # Their [CONTESTED] tag is already embedded in tags_str above.
    else:
        out.append("(no findings)")
    out.append("")

    # -- Findings by File ----------------------------------------------------
    _render_findings_by_file(numbered, out)

    # -- Dismissed / Worth a Glance ------------------------------------------
    # Appendix for dismissed + low-stakes uncertain findings (plan 19 Change D).
    # Rendered after the headline findings; omitted when both lists are empty.
    if dismissed_list or uncertain_list:
        out.append("## Dismissed / Worth a Glance")
        out.append(
            "These findings were reviewed but not confirmed. "
            "Dismissed findings had no demonstrable defect; "
            "uncertain findings could not be resolved from the code alone. "
            "A reviewer may want to glance at them before closing the audit."
        )
        out.append("")

        if dismissed_list:
            out.append("### Dismissed")
            for i, f in enumerate(dismissed_list):
                fid = f.get("finding_id") or "D-{0:03d}".format(i + 1)
                severity = f.get("severity") or "Info"
                file_ = f.get("file") or "(unknown)"
                line_ = f.get("line", -1)
                if isinstance(line_, int) and line_ >= 1:
                    loc = "{0}:{1}".format(file_, line_)
                else:
                    loc = file_
                pattern = (f.get("pattern") or "").strip()
                why = (f.get("why") or f.get("explanation") or "").strip()
                desc = pattern or (why.splitlines()[0][:120] if why else "(no description)")
                out.append(
                    "- [{0}] [{1}] {2} — {3}".format(fid, severity, loc, desc)
                )
            out.append("")

        if uncertain_list:
            out.append("### Uncertain (low-stakes)")
            for i, f in enumerate(uncertain_list):
                fid = f.get("finding_id") or "U-{0:03d}".format(i + 1)
                severity = f.get("severity") or "Info"
                file_ = f.get("file") or "(unknown)"
                line_ = f.get("line", -1)
                if isinstance(line_, int) and line_ >= 1:
                    loc = "{0}:{1}".format(file_, line_)
                else:
                    loc = file_
                pattern = (f.get("pattern") or "").strip()
                why = (f.get("why") or f.get("explanation") or "").strip()
                desc = pattern or (why.splitlines()[0][:120] if why else "(no description)")
                out.append(
                    "- [{0}] [{1}] {2} — {3}".format(fid, severity, loc, desc)
                )
            out.append("")

    # -- Logic Blind Spots ---------------------------------------------------
    # qa-reviewer findings that reference untested branches are rendered here.
    # We collect findings from qa-reviewer agent that are in Info tier or have
    # a pattern suggesting untested branches. In practice the orchestrator may
    # put these in the regular findings list; we render all qa-reviewer findings
    # that appear in the Info bucket separately under this heading IF the
    # report_dict has an explicit "blind_spots" key, otherwise we emit the
    # section header with a "(none identified)" note.
    blind_spots = report_dict.get("blind_spots") or []
    out.append("## Logic Blind Spots (Untested Branches)")
    if blind_spots:
        for item in blind_spots:
            out.append("- {0}".format(item))
    else:
        out.append("(none identified)")
    out.append("")

    # -- Recurring Issues Status table ---------------------------------------
    out.append("## Recurring Issues Status")
    if recurring_resolved or recurring_unresolved:
        out.append("| Past Review | Finding | Status |")
        out.append("|---|---|---|")
        for row in recurring_unresolved:
            # row is a string: "review_path | description | STATUS"
            # or a dict with keys: review, description, status
            if isinstance(row, dict):
                review = row.get("review") or ""
                desc = row.get("description") or ""
                status = row.get("status") or "STILL PRESENT"
            else:
                parts = str(row).split("|")
                review = parts[0].strip() if len(parts) > 0 else str(row)
                desc = parts[1].strip() if len(parts) > 1 else ""
                status = parts[2].strip() if len(parts) > 2 else "STILL PRESENT"
            out.append("| {0} | {1} | {2} |".format(review, desc, status))
        for row in recurring_resolved:
            if isinstance(row, dict):
                review = row.get("review") or ""
                desc = row.get("description") or ""
                status = "RESOLVED"
            else:
                parts = str(row).split("|")
                review = parts[0].strip() if len(parts) > 0 else str(row)
                desc = parts[1].strip() if len(parts) > 1 else ""
                status = "RESOLVED"
            out.append("| {0} | {1} | {2} |".format(review, desc, status))
    else:
        out.append("(no recurring issues tracked in this audit)")
    out.append("")

    # -- Not Audited ---------------------------------------------------------
    out.append("## Not Audited")
    out.append("- Runtime behavior (no dynamic analysis)")
    out.append("- Dependency CVEs (run `npm audit` / `pip audit` separately)")
    out.append("- Runtime performance profiling (out of scope — use /review); static performance-idiom smells are in scope")
    out.append("- UI/design consistency (out of scope)")
    out.append("- Infrastructure / deployment config")
    out.append("")

    # -- Summary -------------------------------------------------------------
    counts = {sev: 0 for sev in _SEVERITY_ORDER}
    for _, f in numbered:
        sev = f.get("severity") or "Info"
        if sev in counts:
            counts[sev] += 1
    total_discarded = sum(discard_counts.get(k, 0) for k in (
        "file_missing", "line_oob", "quote_mismatch", "evidence_empty", "pattern_missing"
    ))
    consensus_count = sum(
        1 for _, f in numbered if "[CROSS-AGENT]" in (f.get("tags") or [])
    )
    unresolved_count = len(recurring_unresolved)
    skipped_str = ", ".join(agents_skipped) if agents_skipped else "none"
    failed_str = (
        ", ".join(
            "{0} ({1})".format(a.get("name", "?"), a.get("reason", "?"))
            for a in agents_failed
        )
        if agents_failed
        else "none"
    )

    # Confidence-gate counts (plan 19 Change D).
    # contested = [CONTESTED]-tagged findings in the headline set (findings).
    # confirmed = headline findings that are NOT [CONTESTED]-tagged.
    contested_count = sum(
        1 for _, f in numbered if "[CONTESTED]" in (f.get("tags") or [])
    )
    confirmed_count = len(numbered) - contested_count
    dismissed_count = len(dismissed_list)
    uncertain_count = len(uncertain_list)

    out.append("## Summary")
    out.append(
        "- Critical: {0} | High: {1} | Medium: {2} | Info: {3}".format(
            counts["Critical"], counts["High"], counts["Medium"], counts["Info"]
        )
    )
    out.append(
        "- Confirmed: {0} | Contested: {1} | Dismissed: {2} | Uncertain: {3}".format(
            confirmed_count, contested_count, dismissed_count, uncertain_count
        )
    )
    out.append("- Cross-agent consensus findings: {0}".format(consensus_count))
    out.append("- Recurring (unresolved): {0}".format(unresolved_count))
    # Multi-pass summary line: only when passes_run >= 2 (guard preserves
    # byte-identical output for single-pass runs).
    if passes_run >= 2:
        multipass_count = sum(
            1 for _, f in numbered
            if (f.get("pass_count") or 1) >= 2
        )
        out.append(
            "- Passes run: {0} | Multi-pass-confirmed findings: {1}".format(
                passes_run, multipass_count
            )
        )
    out.append("- Agents skipped (not installed): {0}".format(skipped_str))
    out.append("- Agents failed (ran but errored): {0}".format(failed_str))
    out.append(
        "- **Findings discarded by validation**: {0} total".format(total_discarded)
    )
    out.append(
        "  - Failed file-exists check: {0}".format(
            discard_counts.get("file_missing", 0)
        )
    )
    out.append(
        "  - Failed line-number sanity: {0}".format(
            discard_counts.get("line_oob", 0)
        )
    )
    out.append(
        "  - Failed verbatim-quote check: {0} (likely hallucination)".format(
            discard_counts.get("quote_mismatch", 0)
        )
    )
    out.append(
        "  - Failed evidence-non-empty check: {0}".format(
            discard_counts.get("evidence_empty", 0)
        )
    )
    out.append(
        "  - Failed pattern-field check: {0}".format(
            discard_counts.get("pattern_missing", 0)
        )
    )
    out.append("")

    # Warn if hallucination signal is high
    quote_fail = discard_counts.get("quote_mismatch", 0)
    if quote_fail > 5:
        out.append(
            "> **Warning**: {0} findings failed the verbatim-quote check — "
            "agents may be hallucinating evidence. Review agent prompts for "
            "tone drift.".format(quote_fail)
        )
        out.append("")

    # -- Methodology ---------------------------------------------------------
    out.append("## Methodology")
    out.append(
        "Every finding is grounded in a verbatim quote from the actual code."
    )
    out.append(
        "A refutation stage cross-examines findings after grounding validation:"
    )
    out.append(
        "confirmed findings appear in the headline (Top-N + Findings by File);"
    )
    out.append(
        "dismissed findings and low-stakes uncertain findings move to the"
    )
    out.append(
        "\"Dismissed / Worth a Glance\" appendix; high-stakes uncertain findings"
    )
    out.append(
        "(security / [CONSTITUTION-VIOLATION]) appear in the headline flagged"
    )
    out.append(
        "[CONTESTED] — surfaced for human review, never buried."
    )
    out.append(
        "Confidence tiers indicate certainty. \"Speculative\" findings are "
        "hypotheses, not verdicts."
    )
    out.append("")
    out.append(
        "If \"Failed verbatim-quote check\" count is high (>5), the agents are"
    )
    out.append(
        "hallucinating evidence — review the agent prompts for tone drift."
    )

    # -- Next Candidates (hotspot mode only) ---------------------------------
    if mode == "hotspot" and next_candidates:
        out.append("")
        out.append("## Next Candidates (Hotspot)")
        out.append(
            "Files ranked just outside the top hotspots — consider for next run:"
        )
        for item in next_candidates:
            if isinstance(item, dict):
                rank = item.get("rank", "?")
                file_ = item.get("file", "?")
                score = item.get("score", 0)
                out.append(
                    "{0}. {1} · score={2:.2f}".format(rank, file_, float(score))
                )
            else:
                # FileScore dataclass — access via attributes
                try:
                    out.append(
                        "{0}. {1} · score={2:.2f}".format(
                            item.rank, item.file, float(item.score)
                        )
                    )
                except AttributeError:
                    out.append("- {0}".format(str(item)))

    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# compute_out_path
# ---------------------------------------------------------------------------


def compute_out_path(audits_dir, date_str):
    # type: (str, str) -> str
    """Compute a collision-free output path for the audit report.

    Base: <audits_dir>/YYYY-MM-DD-audit.md
    If the base path exists, tries <audits_dir>/YYYY-MM-DD-audit-2.md,
    YYYY-MM-DD-audit-3.md, ... until a free path is found.

    Parameters
    ----------
    audits_dir : str   path to the audits directory (need not exist yet)
    date_str   : str   "YYYY-MM-DD" date string (caller provides — no datetime)

    Returns
    -------
    str  the first free path (no guarantee the file is created atomically
         — use write_report for the atomic create).
    """
    base = os.path.join(audits_dir, "{0}-audit.md".format(date_str))
    if not os.path.exists(base):
        return base
    suffix = 2
    while True:
        candidate = os.path.join(
            audits_dir, "{0}-audit-{1}.md".format(date_str, suffix)
        )
        if not os.path.exists(candidate):
            return candidate
        suffix += 1


# ---------------------------------------------------------------------------
# ensure_gitignore
# ---------------------------------------------------------------------------


def ensure_gitignore(audits_dir):
    # type: (str) -> None
    """Create audits/.gitignore with '.tmp-*.md' if it does not exist.

    Idempotent — does NOT clobber an existing .gitignore.
    Creates audits_dir if needed.
    """
    os.makedirs(audits_dir, exist_ok=True)
    gi_path = os.path.join(audits_dir, ".gitignore")
    if not os.path.exists(gi_path):
        fd, tmp_path = tempfile.mkstemp(
            prefix="audit-gi-",
            suffix=".tmp",
            dir=audits_dir,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(".tmp-*.md\n")
            os.replace(tmp_path, gi_path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise


# ---------------------------------------------------------------------------
# write_report
# ---------------------------------------------------------------------------


def write_report(audits_dir, date_str, content):
    # type: (str, str, str) -> str
    """Write content to a collision-free path under audits_dir.

    Steps:
      1. os.makedirs(audits_dir, exist_ok=True)
      2. ensure_gitignore(audits_dir)      (first-run only; idempotent)
      3. compute_out_path(audits_dir, date_str)
      4. Atomic write via mkstemp + os.replace
      5. Returns the path written.

    Does NOT git-add or git-commit.
    """
    os.makedirs(audits_dir, exist_ok=True)
    ensure_gitignore(audits_dir)
    out_path = compute_out_path(audits_dir, date_str)

    tmp_fd, tmp_path = tempfile.mkstemp(
        prefix=".tmp-report-",
        suffix=".md",
        dir=audits_dir,
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmp_path, out_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    return out_path
