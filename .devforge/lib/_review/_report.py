"""_report -- render the final /review markdown report and write to disk.

Implements Phase 5 of /review:
  render_report(partition, feature, date_str, finders, refuters,
                source_root, framework, n_scope_files) -> str
      Full markdown per report-format.md.  Does NOT call datetime.now() —
      date_str is supplied by the caller for determinism.

  write_review_report(feature_dir, content) -> str
      Atomic write (mkstemp + os.replace) to <feature_dir>/review.md.
      Returns the path written.

  render_inline_summary(partition, feature, finders_skipped) -> str
      Count-first inline block for the orchestrator's final message.

Headline vs appendix partition rule
-------------------------------------
  The ``partition`` dict comes directly from ``_shared.apply_verdicts``:
    confirmed  — confirmed by a refuter (carry verify_confidence="confirmed")
    dismissed  — dismissed; NOT [CONSTITUTION-VIOLATION] (per D7)
    uncertain  — low-stakes uncertain (non-high-stakes, not [CONSTITUTION-VIOLATION])
    contested  — high-stakes uncertain + dismissed [CONSTITUTION-VIOLATION] findings;
                 ALL carry "[CONTESTED]" tag

  Headline = confirmed ∪ contested  (grouped by file → category, severity-sorted)
  Appendix = dismissed ∪ uncertain  (omitted when both are empty)

Category bucketing rule (same priority as audit, local copy — this module does
NOT depend on _audit):
  1. "[CONSTITUTION-VIOLATION]" in tags  → constitution (cross-cutting override)
  2. finding.get("category") via _CATEGORY_TO_BUCKET dict
  3. missing / unknown                   → mislogic (safe default)

The report is FINDINGS ONLY — no verdict line, no pass/fail, no approval.

Stdlib only.  Python 3.8+.  No I/O except write_review_report.
"""

import json
import os
import tempfile
from typing import Dict, List, Optional

from _shared.findings_schema import CATEGORY_ENUM  # noqa: E402

# ---------------------------------------------------------------------------
# Bucket constants (local to _review — do NOT import from _audit)
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

# Canonical display order within a file section.
_BUCKET_ORDER = [
    _BUCKET_SECURITY,
    _BUCKET_SYSTEM_DESIGN,
    _BUCKET_BEST_PRACTICE,
    _BUCKET_MISLOGIC,
    _BUCKET_DUPLICATION,
    _BUCKET_CONSTITUTION,
]

_SEVERITY_ORDER = ["Critical", "High", "Medium", "Info"]
_SEVERITY_RANK = {sev: i for i, sev in enumerate(_SEVERITY_ORDER)}

_CATEGORY_TO_BUCKET = {
    "mislogic": _BUCKET_MISLOGIC,
    "system_design": _BUCKET_SYSTEM_DESIGN,
    "best_practice": _BUCKET_BEST_PRACTICE,
    "duplication": _BUCKET_DUPLICATION,
    "security": _BUCKET_SECURITY,
    "blind_spot": _BUCKET_MISLOGIC,  # shares the mislogic display bucket
}

# Guard: every CATEGORY_ENUM value except blind_spot must have an explicit
# bucket mapping.  blind_spot intentionally aliases to the mislogic bucket
# (already mapped above) and is therefore excluded.  This assertion fires at
# module load time so a future category addition can't silently fall through
# to the mislogic default without a deliberate mapping decision.
assert set(CATEGORY_ENUM) - {"blind_spot"} <= set(_CATEGORY_TO_BUCKET), (
    "CATEGORY_ENUM has entries unmapped in _CATEGORY_TO_BUCKET: {0}".format(
        set(CATEGORY_ENUM) - {"blind_spot"} - set(_CATEGORY_TO_BUCKET)
    )
)

_UNKNOWN_FILE_SENTINEL = "(unknown file)"

# ---------------------------------------------------------------------------
# Bucketing helper
# ---------------------------------------------------------------------------


def _bucket_finding(finding):
    # type: (dict) -> str
    """Return the display bucket name for one finding.

    Priority:
      1. "[CONSTITUTION-VIOLATION]" in tags -> constitution (cross-cutting)
      2. finding.get("category") via _CATEGORY_TO_BUCKET
      3. missing / unknown                  -> mislogic
    """
    tags = finding.get("tags") or []
    if "[CONSTITUTION-VIOLATION]" in tags:
        return _BUCKET_CONSTITUTION
    cat = finding.get("category")
    return _CATEGORY_TO_BUCKET.get(cat, _BUCKET_MISLOGIC)


# ---------------------------------------------------------------------------
# Finding body renderer
# ---------------------------------------------------------------------------


def _render_finding_body(finding, finding_id, severity):
    # type: (dict, str, str) -> str
    """Render a single finding in the grouped-report format per report-format.md.

    The first line: "[<id>] [<severity>] :<line> — <description> [<confidence>] <tags>"
    Then the full detail block (Severity, File, Line, Pattern, Confidence,
    Category, Evidence, Why, Remediation).
    [CONTESTED] and [CROSS-AGENT] tags are preserved from the finding's tags list
    and shown in the first line.
    """
    line_ = finding.get("line", -1)
    if isinstance(line_, int) and line_ >= 1:
        location = ":{0}".format(line_)
    else:
        location = ""

    pattern = (finding.get("pattern") or "").strip()
    why = (finding.get("why") or finding.get("explanation") or "").strip()
    if pattern:
        title = pattern
    elif why:
        title = why.splitlines()[0][:120]
    else:
        title = "(no description)"

    evidence = (finding.get("evidence") or "").strip()
    confidence = finding.get("confidence") or "Speculative"
    remediation = (
        finding.get("remediation") or finding.get("suggested_fix") or ""
    ).strip()
    tags = finding.get("tags") or []
    tags_str = " ".join(tags) if tags else ""
    file_ = (finding.get("file") or "").strip()
    category = finding.get("category") or ""

    lines = []  # type: List[str]

    # First line: id, severity, location, description, confidence, tags
    id_prefix = "[{0}] ".format(finding_id) if finding_id else ""
    sev_prefix = "[{0}] ".format(severity)
    desc_line = "- {0}{1}{2} — {3}  [{4}]".format(
        id_prefix, sev_prefix, location, title, confidence
    )
    if tags_str:
        desc_line += "  {0}".format(tags_str)
    lines.append(desc_line)

    # Detail block (matches report-format.md skeleton)
    lines.append("  Severity: {0}".format(severity))
    if file_:
        lines.append("  File: {0}".format(file_))
    if isinstance(line_, int) and line_ >= 1:
        lines.append("  Line: {0}".format(line_))
    if pattern:
        lines.append("  Pattern: {0}".format(pattern))
    lines.append("  Confidence: {0}".format(confidence))
    if category:
        lines.append("  Category: {0}".format(category))
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

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Headline findings section (confirmed + contested, grouped by file → category)
# ---------------------------------------------------------------------------


def _render_confirmed_findings(headline_findings, out):
    # type: (List[tuple], List[str]) -> None
    """Render ## Confirmed Findings (with [CONTESTED] entries flagged).

    Parameters
    ----------
    headline_findings : list of (finding_id: str, finding: dict)
        The union of confirmed + contested findings, already numbered.
    out : list of str
        Output lines are appended here.
    """
    out.append("## Confirmed Findings")

    if not headline_findings:
        out.append("(none)")
        out.append("")
        return

    # Group by file path
    file_to_findings = {}  # type: Dict[str, List]
    for fid, f in headline_findings:
        file_key = (f.get("file") or "").strip() or _UNKNOWN_FILE_SENTINEL
        if file_key not in file_to_findings:
            file_to_findings[file_key] = []
        file_to_findings[file_key].append((fid, f))

    # Sort: normal paths alphabetically, unknown last
    def _file_sort_key(path):
        # type: (str) -> tuple
        return (1 if path == _UNKNOWN_FILE_SENTINEL else 0, path)

    for file_path in sorted(file_to_findings.keys(), key=_file_sort_key):
        file_findings = file_to_findings[file_path]
        out.append("")
        out.append("### {0}".format(file_path))
        out.append("")

        # Group by bucket within this file
        bucket_to_findings = {b: [] for b in _BUCKET_ORDER}  # type: Dict[str, List]
        for fid, f in file_findings:
            bucket = _bucket_finding(f)
            bucket_to_findings[bucket].append((fid, f))

        for bucket in _BUCKET_ORDER:
            findings_in_bucket = bucket_to_findings[bucket]
            if not findings_in_bucket:
                continue
            # Sort by severity then finding_id
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
# Appendix renderer
# ---------------------------------------------------------------------------


def _render_appendix(dismissed, uncertain, out):
    # type: (List[dict], List[dict], List[str]) -> None
    """Render ## Dismissed / Worth a Glance appendix.

    Omitted entirely (nothing appended) when both lists are empty.
    """
    if not dismissed and not uncertain:
        return

    out.append("## Dismissed / Worth a Glance")
    out.append(
        "These findings were reviewed but not confirmed. "
        "Dismissed findings had no demonstrable emergent defect at feature scope; "
        "uncertain findings could not be resolved from the code alone. "
        "A reviewer may want to glance at them before closing the review."
    )
    out.append("")

    if dismissed:
        out.append("### Dismissed")
        for i, f in enumerate(dismissed):
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
            out.append("- [{0}] [{1}] {2} — {3}".format(fid, severity, loc, desc))
        out.append("")

    if uncertain:
        out.append("### Uncertain (low-stakes)")
        for i, f in enumerate(uncertain):
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
            out.append("- [{0}] [{1}] {2} — {3}".format(fid, severity, loc, desc))
        out.append("")


# ---------------------------------------------------------------------------
# render_report
# ---------------------------------------------------------------------------


def render_report(
    partition,
    feature,
    date_str,
    finders,
    refuters,
    source_root,
    framework,
    n_scope_files,
    finders_skipped=None,
):
    # type: (dict, str, str, List[str], List[str], str, str, int, Optional[List[str]]) -> str
    """Render the full /review markdown report from the apply_verdicts partition.

    Parameters
    ----------
    partition : dict
        Output of apply_verdicts — keys: confirmed, dismissed, uncertain, contested.
        Each value is a list of finding dicts.
    feature : str
        Feature directory path (e.g. "specs/001-auth").  Written into the header.
    date_str : str
        "YYYY-MM-DD" date string.  Caller provides — no datetime call here.
    finders : list[str]
        Names of the finder agents invoked.
    refuters : list[str]
        Names of the refuter agents invoked.
    source_root : str
        Source-root value from CLAUDE.md / project-config.
    framework : str
        Framework / Language value from CLAUDE.md / project-config.
    n_scope_files : int
        Number of files in the assembled-feature diff scope.
    finders_skipped : list[str] or None
        Finder agent names that were not installed / skipped.

    Returns
    -------
    str  full markdown report (ends with newline).
    """
    finders_skipped = finders_skipped or []

    confirmed = partition.get("confirmed") or []
    dismissed = partition.get("dismissed") or []
    uncertain = partition.get("uncertain") or []
    contested = partition.get("contested") or []

    # Headline = confirmed ∪ contested (in that order for numbering)
    headline = list(confirmed) + list(contested)

    # Assign finding IDs across the headline set.
    numbered = []  # type: List[tuple]
    for i, f in enumerate(headline):
        fid = f.get("finding_id") or "F-{0:03d}".format(i + 1)
        numbered.append((fid, f))

    # -- Header block --------------------------------------------------------
    out = []  # type: List[str]
    feature_label = feature or "(unknown)"
    out.append("# Feature Review — {0} — {1}".format(feature_label, date_str))
    out.append("")

    finders_str = ", ".join(finders) if finders else "(none)"
    if finders_skipped:
        finders_str += " (skipped — not installed: {0})".format(
            ", ".join(finders_skipped)
        )
    refuters_str = ", ".join(refuters) if refuters else "(none)"

    out.append("**Feature**: {0}".format(feature_label))
    out.append(
        "**Scope**: assembled feature diff (all tasks together) — {0} files".format(
            n_scope_files
        )
    )
    out.append("**Finders invoked**: {0}".format(finders_str))
    out.append("**Refuters invoked**: {0}".format(refuters_str))
    out.append("**Source Root**: {0}".format(source_root or "(unset)"))
    out.append("**Framework / Language**: {0}".format(framework or "(unset)"))
    out.append("")

    # -- Top Priorities ------------------------------------------------------
    out.append("## Confirmed — Top Priorities")
    out.append("Force-ranked across the confirmed findings. Fix these first.")
    if numbered:
        # Sort by severity; contested findings rank after confirmed at same severity.
        def _priority_key(pair):
            # type: (tuple) -> tuple
            fid, f = pair
            sev_rank = _SEVERITY_RANK.get(f.get("severity") or "Info", 3)
            # contested = 1 (after confirmed = 0 at same severity)
            is_contested = 1 if "[CONTESTED]" in (f.get("tags") or []) else 0
            return (sev_rank, is_contested, fid)

        sorted_headline = sorted(numbered, key=_priority_key)
        for rank, (fid, f) in enumerate(sorted_headline, start=1):
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
            confidence = f.get("confidence") or "Speculative"
            tags = f.get("tags") or []
            tags_str = " ".join(tags) if tags else ""
            line_parts = "[{0}] {1} — {2} [{3}]".format(
                severity, location, desc, confidence
            )
            if tags_str:
                line_parts += " {0}".format(tags_str)
            out.append("{0}. {1}".format(rank, line_parts))
    else:
        out.append("(no confirmed findings)")
    out.append("")

    # -- Confirmed Findings (by file → category, severity-sorted) -----------
    _render_confirmed_findings(numbered, out)

    # -- Summary -------------------------------------------------------------
    counts = {sev: 0 for sev in _SEVERITY_ORDER}
    for _, f in numbered:
        sev = f.get("severity") or "Info"
        if sev in counts:
            counts[sev] += 1

    confirmed_count = len(confirmed)
    contested_count = len(contested)
    dismissed_count = len(dismissed)
    uncertain_count = len(uncertain)

    skipped_str = ", ".join(finders_skipped) if finders_skipped else "none"

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
    out.append("- Finders skipped (not installed): {0}".format(skipped_str))
    out.append("")

    # -- Dismissed / Worth a Glance appendix ---------------------------------
    _render_appendix(dismissed, uncertain, out)

    # -- Methodology ---------------------------------------------------------
    out.append("## Methodology")
    out.append(
        "Findings are grounded — every finding carries a verbatim quote from the actual"
    )
    out.append(
        "cross-task code, and validation discards ungrounded ones. A refutation stage"
    )
    out.append(
        "then cross-examines each grounded finding before it reaches the report: a"
    )
    out.append(
        "finding earns the headline only by surviving an adversary who default-dismisses"
    )
    out.append(
        "anything not demonstrable as emergent at feature scope. Confirmed findings reach"
    )
    out.append(
        "the headline; dismissed findings and low-stakes uncertain findings drop to the"
    )
    out.append(
        "Dismissed / Worth a Glance appendix; contested findings (a high-stakes `security`"
    )
    out.append(
        "/ `[CONSTITUTION-VIOLATION]` finding the refuter could not confirm, or a"
    )
    out.append(
        "`[CONSTITUTION-VIOLATION]` finding the refuter dismissed) are surfaced in the"
    )
    out.append(
        "headline, flagged `[CONTESTED]`, never buried. This report is findings only —"
    )
    out.append("the verdict is `/verify`'s.")

    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# write_review_report
# ---------------------------------------------------------------------------


def write_review_report(feature_dir, content):
    # type: (str, str) -> str
    """Atomic write of content to <feature_dir>/review.md.

    Uses mkstemp + os.replace for crash safety.
    Creates feature_dir if it does not exist.
    Returns the path written.

    On failure, unlinks the temp file and re-raises.
    """
    os.makedirs(feature_dir, exist_ok=True)
    out_path = os.path.join(feature_dir, "review.md")

    tmp_fd, tmp_path = tempfile.mkstemp(
        prefix=".tmp-review-",
        suffix=".md",
        dir=feature_dir,
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


# ---------------------------------------------------------------------------
# render_inline_summary
# ---------------------------------------------------------------------------


def render_inline_summary(partition, feature, finders_skipped=None):
    # type: (dict, str, Optional[List[str]]) -> str
    """Render the ## Review Complete inline console block.

    Count-first format per CLAUDE.md audit-format discipline.

    Parameters
    ----------
    partition : dict
        Output of apply_verdicts — keys: confirmed, dismissed, uncertain, contested.
    feature : str
        Feature directory path.
    finders_skipped : list[str] or None
        Finder names that were not installed.

    Returns
    -------
    str  the complete inline block (ends with newline).
    """
    finders_skipped = finders_skipped or []

    confirmed = partition.get("confirmed") or []
    dismissed = partition.get("dismissed") or []
    uncertain = partition.get("uncertain") or []
    contested = partition.get("contested") or []

    # Headline = confirmed ∪ contested (for severity counts)
    headline = list(confirmed) + list(contested)

    counts = {sev: 0 for sev in _SEVERITY_ORDER}
    for f in headline:
        sev = f.get("severity") or "Info"
        if sev in counts:
            counts[sev] += 1

    confirmed_count = len(confirmed)
    contested_count = len(contested)
    dismissed_count = len(dismissed)
    uncertain_count = len(uncertain)

    out = []  # type: List[str]
    out.append("## Review Complete")
    out.append("")
    out.append("**Feature**: {0}".format(feature or "(unknown)"))
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
    out.append(
        "**Finders skipped**: {0}".format(
            ", ".join(finders_skipped) if finders_skipped else "none"
        )
    )
    out.append("")
    out.append(
        "NOTE: /review is findings only — no verdict. The verdict is `/verify`'s."
    )

    return "\n".join(out) + "\n"
