"""_report.py — render verification.md and inline summary for /verify.

Public surface
--------------
  render_report(verdict, ac_results, review_findings, hygiene,
                feature, date_str, mechanical_status,
                ac_verification_mode) -> str
      Build the full verification.md markdown.  Does NOT call the clock —
      date_str is REQUIRED and supplied by the caller for determinism.

  write_verification_report(feature_dir, content) -> str
      Atomic write (mkstemp + os.replace) to <feature_dir>/verification.md.
      Returns the path written.
      Mirrors _review._report.write_review_report exactly.

  render_inline_summary(verdict, ac_results, review_findings,
                        mechanical_status, feature) -> str
      Count-first inline console block (per the audit-format discipline).
      Verdict + AC pass/fail counts + mechanical result + folded-finding counts
      + next-step pointer.

Report sections (verification.md)
----------------------------------
  # Feature Verification — <feature> — <date>

  ## Acceptance Criteria

  | AC | Status | Evidence |
  |---|---|---|
  | AC-N | <status> | <evidence> |
  ...

  ## Code Quality

  **Mechanical checks**: <mechanical_status> (or N/A when not run)
  **Cross-task consistency**: see /review report at specs/[feature]/review.md
  **Scope creep**: N changed files outside the planned scope: <files>
  **Leftover artifacts**: N flagged

  ## Review Findings

  (Folded from review.md, or "no review report — run /review" when missing.)
  N confirmed | N contested | N dismissed | N uncertain

  ## Issues Found

  (Grouped by severity; only confirmed ∪ contested findings.)
  <severity> <pattern> <file>:<line>  ...

  ## Verdict

  **APPROVED** | **NEEDS WORK** | **REJECTED**

  Reasons:
  - <reason line 1>
  - ...

Stdlib only.  Python 3.8+.  No I/O except write_verification_report.
"""

from __future__ import annotations

import os
import tempfile
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Severity constants (mirror _review/_report.py)
# ---------------------------------------------------------------------------

_SEVERITY_ORDER = ["Critical", "High", "Medium", "Info"]

# Emoji-free severity prefix chars for the Issues Found table
_SEVERITY_LABELS = {
    "Critical": "Critical",
    "High": "High",
    "Medium": "Medium",
    "Info": "Info",
}

# Mechanical status display mapping
_MECH_DISPLAY = {
    "pass": "PASS",
    "": "not run",
    None: "not run",
    "self_repair": "SELF-REPAIR (warnings)",
    "failed": "FAILED",
    "isolation_failure": "ISOLATION FAILURE",
    "tooling_unavailable": "TOOLING UNAVAILABLE",
}

# AC status display colours (text-only, no colour codes)
_PASS_STATUSES = frozenset(["PASS", "PASS (code)"])


# ---------------------------------------------------------------------------
# render_report
# ---------------------------------------------------------------------------


def render_report(
    verdict,              # type: Dict
    ac_results,           # type: List[Dict]
    review_findings,      # type: Dict
    hygiene,              # type: Dict
    feature,              # type: str
    date_str,             # type: str
    mechanical_status,    # type: Optional[str]
    ac_verification_mode="code-only",  # type: str
):
    # type: (...) -> str
    """Build the full verification.md markdown.

    Parameters
    ----------
    verdict : dict
        Output of compute_verdict: {verdict, reasons, blockers}.
    ac_results : list[dict]
        Output of merge_ac_results: per-AC status + evidence.
    review_findings : dict
        Output of read_review_findings: confirmed, contested, missing, summary.
    hygiene : dict
        Output of check_hygiene: scope_creep, leftover_artifacts, etc.
    feature : str
        Feature directory name (e.g. "specs/001-auth").
    date_str : str
        Date string in YYYY-MM-DD format. REQUIRED — never call the clock here.
    mechanical_status : str or None
        verify-touched status string.
    ac_verification_mode : str
        ac_verification_mode value for display.

    Returns
    -------
    str  the complete verification.md content (ends with newline).
    """
    out = []  # type: List[str]

    feature_name = os.path.basename(feature.rstrip("/\\")) if feature else "(unknown)"

    # --- Header ----------------------------------------------------------------
    out.append("# Feature Verification — {0} — {1}".format(feature_name, date_str))
    out.append("")
    out.append("**Feature**: {0}".format(feature or "(unknown)"))
    out.append("**Date**: {0}".format(date_str))
    out.append("**AC Verification Mode**: {0}".format(ac_verification_mode or "code-only"))
    out.append("")

    # --- Acceptance Criteria table --------------------------------------------
    out.append("## Acceptance Criteria")
    out.append("")
    if ac_results:
        out.append("| AC | Status | Evidence |")
        out.append("|---|---|---|")
        for ac in ac_results:
            ac_id = ac.get("id", "?")
            status = ac.get("status", "UNVERIFIED")
            evidence = ac.get("evidence", "").replace("|", "\\|")
            out.append("| {0} | {1} | {2} |".format(ac_id, status, evidence))
    else:
        out.append("_No ACs defined in spec._")
    out.append("")

    # --- Code Quality ---------------------------------------------------------
    out.append("## Code Quality")
    out.append("")
    mech_norm = (mechanical_status or "").strip()
    mech_display = _MECH_DISPLAY.get(mech_norm or None, mech_norm)
    out.append("**Mechanical checks**: {0}".format(mech_display))
    out.append(
        "**Cross-task consistency**: see /review report at "
        "{0}/review.md".format(feature or "specs/[feature]")
    )

    scope_creep = (hygiene or {}).get("scope_creep") or []
    leftover_artifacts = (hygiene or {}).get("leftover_artifacts") or []
    scope_checked = (hygiene or {}).get("scope_creep_checked", False)

    if scope_checked:
        if scope_creep:
            out.append(
                "**Scope creep**: {0} changed file(s) outside the planned scope: "
                "{1}".format(len(scope_creep), ", ".join(scope_creep[:5]))
            )
            if len(scope_creep) > 5:
                out[-1] += " (+ {0} more)".format(len(scope_creep) - 5)
        else:
            out.append("**Scope creep**: none detected")
    else:
        out.append("**Scope creep**: not checked (no breakdown-handoff.json baseline)")

    if leftover_artifacts:
        out.append(
            "**Leftover artifacts**: {0} flagged (debug prints / bare TODOs / "
            "commented-out code)".format(len(leftover_artifacts))
        )
    else:
        out.append("**Leftover artifacts**: none detected")
    out.append("")

    # --- Review Findings -------------------------------------------------------
    out.append("## Review Findings")
    out.append("")
    review_missing = (review_findings or {}).get("missing", True)
    if review_missing:
        out.append(
            "_No review report found — run `/review` before `/verify` to fold "
            "cross-task findings into this verdict._"
        )
    else:
        summary = (review_findings or {}).get("summary") or {}
        confirmed_count = summary.get("confirmed_count", 0)
        contested_count = summary.get("contested_count", 0)
        dismissed_count = summary.get("dismissed_count", 0)
        uncertain_count = summary.get("uncertain_count", 0)
        out.append(
            "{0} confirmed | {1} contested | {2} dismissed | "
            "{3} uncertain".format(
                confirmed_count, contested_count, dismissed_count, uncertain_count
            )
        )
        crit = summary.get("critical", 0)
        high = summary.get("high", 0)
        med = summary.get("medium", 0)
        info = summary.get("info", 0)
        out.append(
            "Severity breakdown: {0} Critical, {1} High, {2} Medium, {3} Info".format(
                crit, high, med, info
            )
        )
    out.append("")

    # --- Issues Found ---------------------------------------------------------
    out.append("## Issues Found")
    out.append("")

    confirmed_findings = (review_findings or {}).get("confirmed") or []
    contested_findings = (review_findings or {}).get("contested") or []
    headline_findings = list(confirmed_findings) + list(contested_findings)

    if not headline_findings:
        if review_missing:
            out.append("_No review report — run /review to identify issues._")
        else:
            out.append("_No confirmed or contested findings in the review report._")
    else:
        # Group by severity
        by_severity = {sev: [] for sev in _SEVERITY_ORDER}  # type: Dict[str, List[Dict]]
        for f in headline_findings:
            sev = f.get("severity") or "Info"
            if sev in by_severity:
                by_severity[sev].append(f)

        for sev in _SEVERITY_ORDER:
            findings_in_sev = by_severity[sev]
            if not findings_in_sev:
                continue
            out.append("### {0}".format(sev))
            out.append("")
            for f in findings_in_sev:
                file_ = f.get("file") or "(unknown)"
                line_ = f.get("line", -1)
                loc = "{0}:{1}".format(file_, line_) if isinstance(line_, int) and line_ >= 1 else file_
                pattern = f.get("pattern") or "(no description)"
                tags = f.get("tags") or []
                tag_str = " ".join(tags) if tags else ""
                entry = "- [{0}] {1} — {2}".format(sev, loc, pattern)
                if tag_str:
                    entry += "  {0}".format(tag_str)
                out.append(entry)
            out.append("")

    # --- Verdict --------------------------------------------------------------
    out.append("## Verdict")
    out.append("")
    verdict_str = verdict.get("verdict", "NEEDS WORK")
    out.append("**{0}**".format(verdict_str))
    out.append("")

    reasons = verdict.get("reasons") or []
    if reasons:
        out.append("**Reasons**:")
        out.append("")
        for reason in reasons:
            out.append("- {0}".format(reason))
    else:
        if verdict_str == "APPROVED":
            out.append(
                "All acceptance criteria satisfied, no blocking issues found."
            )

    out.append("")

    # Next-step guidance based on verdict
    if verdict_str == "APPROVED":
        out.append("**Next step**: run `/summarize` then `/finalize`.")
    elif verdict_str == "NEEDS WORK":
        out.append(
            "**Next step**: address the issues above, then re-run `/verify`. "
            "Run `/implement` for code fixes."
        )
    else:
        out.append(
            "**Next step**: revise the spec via `/specify` → `/plan` → `/breakdown`, "
            "then re-implement."
        )
    out.append("")

    return "\n".join(out)


# ---------------------------------------------------------------------------
# write_verification_report
# ---------------------------------------------------------------------------


def write_verification_report(feature_dir, content):
    # type: (str, str) -> str
    """Atomic write of content to <feature_dir>/verification.md.

    Uses mkstemp + os.replace for crash safety.
    Creates feature_dir if it does not exist.
    Returns the path written.

    On failure, unlinks the temp file and re-raises.
    Mirrors _review._report.write_review_report exactly.
    """
    os.makedirs(feature_dir, exist_ok=True)
    out_path = os.path.join(feature_dir, "verification.md")

    tmp_fd, tmp_path = tempfile.mkstemp(
        prefix=".tmp-verify-",
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


def render_inline_summary(
    verdict,              # type: Dict
    ac_results,           # type: List[Dict]
    review_findings,      # type: Dict
    mechanical_status,    # type: Optional[str]
    feature,              # type: str
):
    # type: (...) -> str
    """Render the ## Verification Complete inline console block.

    Count-first format per CLAUDE.md audit-format discipline:
      - verdict first
      - AC pass/fail counts
      - mechanical result
      - folded-findings counts
      - next-step pointer

    Parameters
    ----------
    verdict : dict
        compute_verdict output: {verdict, reasons, blockers}.
    ac_results : list[dict]
        merge_ac_results output.
    review_findings : dict
        read_review_findings output.
    mechanical_status : str or None
        verify-touched status string.
    feature : str
        Feature directory path.

    Returns
    -------
    str  the complete inline block (ends with newline).
    """
    verdict_str = verdict.get("verdict", "NEEDS WORK")
    reasons = verdict.get("reasons") or []

    # AC counts
    ac_list = ac_results or []
    ac_pass = sum(1 for a in ac_list if a.get("status", "") in _PASS_STATUSES)
    ac_fail = sum(
        1 for a in ac_list
        if a.get("status", "") in frozenset(
            ["FAIL", "PARTIAL", "FAIL (code)", "PARTIAL (code)"]
        )
    )
    ac_unverified = sum(
        1 for a in ac_list
        if a.get("status", "UNVERIFIED") in frozenset(["UNVERIFIED", "MANUAL"])
    )
    ac_total = len(ac_list)

    # Review findings counts
    review_missing = (review_findings or {}).get("missing", True)
    summary = (review_findings or {}).get("summary") or {}
    confirmed_count = summary.get("confirmed_count", 0)
    contested_count = summary.get("contested_count", 0)

    # Mechanical display
    mech_norm = (mechanical_status or "").strip()
    mech_display = _MECH_DISPLAY.get(mech_norm or None, mech_norm)

    out = []  # type: List[str]
    out.append("## Verification Complete")
    out.append("")
    out.append("**Feature**: {0}".format(feature or "(unknown)"))
    out.append("**Verdict**: **{0}**".format(verdict_str))
    out.append("")
    out.append(
        "**AC results**: {0}/{1} passed, {2} failed/partial, "
        "{3} unverified/manual".format(
            ac_pass, ac_total, ac_fail, ac_unverified
        )
    )
    out.append("**Mechanical checks**: {0}".format(mech_display))
    if review_missing:
        out.append("**Review findings**: not available (run /review first)")
    else:
        out.append(
            "**Review findings**: {0} confirmed, {1} contested".format(
                confirmed_count, contested_count
            )
        )
    out.append("")

    if reasons:
        out.append("**Key reasons**:")
        for r in reasons[:4]:  # cap at 4 for inline block brevity
            # Wrap long reasons at 100 chars for readability
            wrapped = r[:100] + "…" if len(r) > 100 else r
            out.append("  - {0}".format(wrapped))
        if len(reasons) > 4:
            out.append("  - (+ {0} more — see verification.md)".format(len(reasons) - 4))
    out.append("")

    # Next-step pointer
    if verdict_str == "APPROVED":
        out.append("**Next step**: `/summarize` → `/finalize`")
    elif verdict_str == "NEEDS WORK":
        out.append("**Next step**: address blockers → re-run `/verify`")
    else:
        out.append(
            "**Next step**: revise spec → `/specify` → `/plan` → `/breakdown` → re-implement"
        )

    return "\n".join(out) + "\n"
