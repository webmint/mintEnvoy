"""_report -- render the final /grill markdown report and write to disk.

Implements Phase 4 of /grill:
  render_report(partition, feature, date_str, finders, refuters,
                source_root, framework, n_scope_files, disposition,
                rationale, re_entry_target=None, finders_skipped=None) -> str
      Full markdown per grill report format.  Does NOT call datetime.now() --
      date_str is supplied by the caller for determinism.

  write_grill_report(feature_dir, content) -> str
      Atomic write (mkstemp + os.replace) to <feature_dir>/grill.md.
      Returns the path written.

  build_seed(target_stage, feature, prior_conclusion, invalidating_evidence,
             must_satisfy, cycle_count, carried_findings, provenance) -> ReEntrySeed
      Construct a ReEntrySeed for the RE-ENTER-UPSTREAM backward handoff.
      Lets ReEntrySeed.__post_init__ enforce all validation -- surfaces a
      clear ValueError on invalid input.  Caller is responsible for calling
      this only when disposition == RE-ENTER-UPSTREAM.

  write_seed(feature_dir, seed) -> str
      Atomic write of ReEntrySeed as JSON to <feature_dir>/grill-seed.json.
      Uses dataclasses.asdict + json.  Returns path written.

Headline vs appendix partition rule (mirrors _review/_report):
  The ``partition`` dict comes directly from ``_shared.apply_verdicts``:
    confirmed  -- confirmed by a refuter (carry verify_confidence="confirmed")
    dismissed  -- dismissed; NOT [CONSTITUTION-VIOLATION] (per D7)
    uncertain  -- low-stakes uncertain (non-high-stakes, not [CONSTITUTION-VIOLATION])
    contested  -- high-stakes uncertain + dismissed [CONSTITUTION-VIOLATION] findings;
                 ALL carry "[CONTESTED]" tag

  Headline = confirmed union contested  (grouped by file -> category, severity-sorted)
  Appendix = dismissed union uncertain  (omitted when both are empty)

Disposition section (grill-specific -- /review does NOT have this):
  A ``## Disposition`` section renders the recommended 4-way verdict:
    PROCEED          -- attack found no disqualifying defect; plan is sound
    REVISE-PLAN      -- defects are real but fixable at plan level
    RE-ENTER-UPSTREAM -- defect is rooted upstream (spec/discovery/research);
                         requires re_entry_target to be one of SEED_TARGET_STAGES
    KILL             -- defect is fundamental; plan should be abandoned

  The disposition (verdict string + rationale, and for RE-ENTER-UPSTREAM the
  target stage) is an INPUT to render_report -- computed upstream by the
  orchestrator's CLASSIFY reasoning; this module RENDERS it, does not decide.

Seed producer (grill-specific -- /review does NOT have this):
  build_seed + write_seed produce the backward handoff artefact
  ``specs/[feature]/grill-seed.json`` that /research, /discover, or /specify
  consume on re-entry so the re-run is DIRECTED.

Category bucketing rule (same priority as _review/_report, local copy):
  1. "[CONSTITUTION-VIOLATION]" in tags  -> constitution (cross-cutting override)
  2. finding.get("category") via _CATEGORY_TO_BUCKET dict
  3. missing / unknown                   -> mislogic (safe default)

Stdlib only.  Python 3.8+.  No I/O except write_grill_report and write_seed.
"""

import dataclasses
import json
import os
import tempfile
from typing import Dict, List, Optional

from _shared.findings_schema import CATEGORY_ENUM  # noqa: E402
from _grill.seed_schema import (  # noqa: E402
    SEED_SCHEMA_VERSION,
    SEED_SOURCE,
    SEED_TARGET_STAGES,
    ReEntrySeed,
)

# ---------------------------------------------------------------------------
# Disposition constants.
# ---------------------------------------------------------------------------

DISPOSITION_VERDICTS = ("PROCEED", "REVISE-PLAN", "RE-ENTER-UPSTREAM", "KILL")

# Maps raw target_stage values (as stored in the seed) to the slash-command
# name the user should re-enter at.  Used ONLY for guidance text rendering --
# the seed's target_stage value is stored and validated without this mapping.
_STAGE_TO_CMD = {
    "spec": "specify",
    "discovery": "discover",
    "research": "research",
}

# ---------------------------------------------------------------------------
# Bucket constants (local to _grill -- do NOT import from _audit or _review).
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
# bucket mapping.  blind_spot IS mapped (to the mislogic bucket above); it is
# excluded from this check because the assert validates UNMAPPED values only.
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
    """Render a single finding in the grouped-report format.

    The first line: "[<id>] [<severity>] :<line> -- <description> [<confidence>] <tags>"
    Then the full detail block.
    [CONTESTED] and [CROSS-AGENT] tags are preserved from the finding's tags list.
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
    desc_line = "- {0}{1}{2} -- {3}  [{4}]".format(
        id_prefix, sev_prefix, location, title, confidence
    )
    if tags_str:
        desc_line += "  {0}".format(tags_str)
    lines.append(desc_line)

    # Detail block
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
# Headline findings section (confirmed + contested, grouped by file -> category)
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
        "Dismissed findings had no demonstrable plan-level defect; "
        "uncertain findings could not be resolved from the plan alone. "
        "A reviewer may want to glance at them before accepting the verdict."
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
            out.append("- [{0}] [{1}] {2} -- {3}".format(fid, severity, loc, desc))
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
            out.append("- [{0}] [{1}] {2} -- {3}".format(fid, severity, loc, desc))
        out.append("")


# ---------------------------------------------------------------------------
# Disposition section renderer
# ---------------------------------------------------------------------------


def _render_disposition(disposition, rationale, re_entry_target, out):
    # type: (str, str, Optional[str], List[str]) -> None
    """Render the ## Disposition section.

    For RE-ENTER-UPSTREAM the target stage (re_entry_target) is included.
    Validation is enforced before this helper is called (by render_report).
    """
    out.append("## Disposition")
    out.append("")

    if disposition == "RE-ENTER-UPSTREAM":
        out.append(
            "**Verdict**: {0} (target: `{1}`)".format(disposition, re_entry_target)
        )
    else:
        out.append("**Verdict**: {0}".format(disposition))

    out.append("")
    out.append("**Rationale**:")
    out.append("")

    # Indent the rationale block under the heading.
    for line in rationale.splitlines():
        out.append(line)

    out.append("")

    # Verdict-specific guidance.
    if disposition == "PROCEED":
        out.append(
            "> The grill attack found no disqualifying plan-level defect. "
            "The plan is sound to execute."
        )
    elif disposition == "REVISE-PLAN":
        out.append(
            "> The defects are real but correctable at the plan level. "
            "Revise `plan.md` to address the confirmed findings, then re-run `/plan` "
            "(or hand-patch `plan.md`), and optionally re-run `/grill` before proceeding "
            "to `/breakdown`."
        )
    elif disposition == "RE-ENTER-UPSTREAM":
        cmd_name = _STAGE_TO_CMD.get(re_entry_target, re_entry_target)
        out.append(
            "> The defect is rooted upstream -- the plan faithfully implements a flawed "
            "{0} conclusion. Re-enter at `/{1}` with the emitted `grill-seed.json` "
            "so the re-run is directed, not a repeat.".format(
                re_entry_target, cmd_name
            )
        )
    elif disposition == "KILL":
        out.append(
            "> The defect is fundamental. The plan should be abandoned. "
            "Raise the issue with the team before proceeding."
        )

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
    disposition,
    rationale,
    re_entry_target=None,
    finders_skipped=None,
):
    # type: (dict, str, str, List[str], List[str], str, str, int, str, str, Optional[str], Optional[List[str]]) -> str
    """Render the full /grill markdown report from the apply_verdicts partition.

    Parameters
    ----------
    partition : dict
        Output of apply_verdicts -- keys: confirmed, dismissed, uncertain, contested.
        Each value is a list of finding dicts.
    feature : str
        Feature directory path (e.g. "specs/001-auth").  Written into the header.
    date_str : str
        "YYYY-MM-DD" date string.  Caller provides -- no datetime call here.
    finders : list[str]
        Names of the finder agents invoked.
    refuters : list[str]
        Names of the refuter agents invoked.
    source_root : str
        Source-root value from CLAUDE.md / project-config.
    framework : str
        Framework / Language value from CLAUDE.md / project-config.
    n_scope_files : int
        Number of files in the plan scope.
    disposition : str
        One of DISPOSITION_VERDICTS: "PROCEED", "REVISE-PLAN",
        "RE-ENTER-UPSTREAM", "KILL".
    rationale : str
        Human-readable rationale for the disposition (non-empty).
    re_entry_target : str or None
        Required when disposition == "RE-ENTER-UPSTREAM".
        Must be one of SEED_TARGET_STAGES: "spec", "discovery", "research".
        Must be None (or omitted) for other verdicts.
    finders_skipped : list[str] or None
        Finder agent names that were not installed / skipped.

    Returns
    -------
    str  full markdown report (ends with newline).

    Raises
    ------
    ValueError  if disposition is not one of DISPOSITION_VERDICTS.
    ValueError  if disposition == "RE-ENTER-UPSTREAM" and re_entry_target is
                not one of SEED_TARGET_STAGES.
    ValueError  if disposition != "RE-ENTER-UPSTREAM" and re_entry_target is
                not None.
    """
    # --- Input validation ---
    if disposition not in DISPOSITION_VERDICTS:
        raise ValueError(
            "disposition must be one of {0}, got {1!r}".format(
                list(DISPOSITION_VERDICTS), disposition
            )
        )

    if disposition == "RE-ENTER-UPSTREAM":
        if re_entry_target not in SEED_TARGET_STAGES:
            raise ValueError(
                "re_entry_target must be one of {0} when disposition is "
                "RE-ENTER-UPSTREAM, got {1!r}".format(
                    list(SEED_TARGET_STAGES), re_entry_target
                )
            )
    else:
        if re_entry_target is not None:
            raise ValueError(
                "re_entry_target must be None when disposition is {0!r}, "
                "got {1!r}".format(disposition, re_entry_target)
            )

    finders_skipped = finders_skipped or []

    confirmed = partition.get("confirmed") or []
    dismissed = partition.get("dismissed") or []
    uncertain = partition.get("uncertain") or []
    contested = partition.get("contested") or []

    # Headline = confirmed union contested (in that order for numbering)
    headline = list(confirmed) + list(contested)

    # Assign finding IDs across the headline set.
    numbered = []  # type: List[tuple]
    for i, f in enumerate(headline):
        fid = f.get("finding_id") or "F-{0:03d}".format(i + 1)
        numbered.append((fid, f))

    # -- Header block -----------------------------------------------------------
    out = []  # type: List[str]
    feature_label = feature or "(unknown)"
    out.append("# Plan Grill -- {0} -- {1}".format(feature_label, date_str))
    out.append("")

    finders_str = ", ".join(finders) if finders else "(none)"
    if finders_skipped:
        finders_str += " (skipped -- not installed: {0})".format(
            ", ".join(finders_skipped)
        )
    refuters_str = ", ".join(refuters) if refuters else "(none)"

    out.append("**Feature**: {0}".format(feature_label))
    out.append(
        "**Scope**: plan.md + referenced specs -- {0} files".format(n_scope_files)
    )
    out.append("**Finders invoked**: {0}".format(finders_str))
    out.append("**Refuters invoked**: {0}".format(refuters_str))
    out.append("**Source Root**: {0}".format(source_root or "(unset)"))
    out.append("**Framework / Language**: {0}".format(framework or "(unset)"))
    out.append("")

    # -- Disposition section (grill-specific) -----------------------------------
    _render_disposition(disposition, rationale, re_entry_target, out)

    # -- Top Priorities ---------------------------------------------------------
    out.append("## Confirmed -- Top Priorities")
    out.append("Force-ranked across the confirmed findings. Fix these first.")
    if numbered:
        def _priority_key(pair):
            # type: (tuple) -> tuple
            fid, f = pair
            sev_rank = _SEVERITY_RANK.get(f.get("severity") or "Info", 3)
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
            line_parts = "[{0}] {1} -- {2} [{3}]".format(
                severity, location, desc, confidence
            )
            if tags_str:
                line_parts += " {0}".format(tags_str)
            out.append("{0}. {1}".format(rank, line_parts))
    else:
        out.append("(no confirmed findings)")
    out.append("")

    # -- Confirmed Findings (by file -> category, severity-sorted) -------------
    _render_confirmed_findings(numbered, out)

    # -- Summary ----------------------------------------------------------------
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
    out.append("- Disposition: {0}".format(disposition))
    out.append("- Finders skipped (not installed): {0}".format(skipped_str))
    out.append("")

    # -- Dismissed / Worth a Glance appendix ------------------------------------
    _render_appendix(dismissed, uncertain, out)

    # -- Methodology ------------------------------------------------------------
    out.append("## Methodology")
    out.append(
        "Findings are grounded -- every finding carries a verbatim quote from the"
    )
    out.append(
        "actual plan/spec/research artefacts. A refutation stage cross-examines each"
    )
    out.append(
        "grounded finding before it reaches the report: a finding earns the headline"
    )
    out.append(
        "only by surviving an adversary who default-dismisses anything not"
    )
    out.append(
        "demonstrable as a real plan-level defect. Confirmed findings reach the"
    )
    out.append(
        "headline; dismissed and low-stakes uncertain findings drop to the"
    )
    out.append(
        "Dismissed / Worth a Glance appendix; high-stakes [CONTESTED] findings"
    )
    out.append(
        "(security / [CONSTITUTION-VIOLATION] the refuter could not confirm) are"
    )
    out.append(
        "surfaced in the headline, flagged [CONTESTED], never buried."
    )

    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# write_grill_report
# ---------------------------------------------------------------------------


def write_grill_report(feature_dir, content):
    # type: (str, str) -> str
    """Atomic write of content to <feature_dir>/grill.md.

    Uses mkstemp + os.replace for crash safety.
    Creates feature_dir if it does not exist.
    Returns the path written.

    On failure, unlinks the temp file and re-raises.
    """
    os.makedirs(feature_dir, exist_ok=True)
    out_path = os.path.join(feature_dir, "grill.md")

    tmp_fd, tmp_path = tempfile.mkstemp(
        prefix=".tmp-grill-",
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
# build_seed
# ---------------------------------------------------------------------------


def build_seed(
    target_stage,
    feature,
    prior_conclusion,
    invalidating_evidence,
    must_satisfy,
    cycle_count,
    carried_findings,
    provenance,
):
    # type: (str, str, str, str, str, int, List[str], str) -> ReEntrySeed
    """Construct a ReEntrySeed for the RE-ENTER-UPSTREAM backward handoff.

    Delegates all validation to ReEntrySeed.__post_init__ -- surfaces a
    clear ValueError on invalid input.

    Parameters
    ----------
    target_stage : str
        One of SEED_TARGET_STAGES: "spec", "discovery", "research".
    feature : str
        Feature slug / id (non-empty).
    prior_conclusion : str
        What the upstream stage concluded that is now invalidated (non-empty).
    invalidating_evidence : str
        The grounded grill finding (verbatim quote / ref) that invalidates the
        prior_conclusion (non-empty).
    must_satisfy : str
        What the re-run must additionally satisfy (non-empty).
    cycle_count : int
        Bounded-compounding-loop counter; strict int (no bool), >= 1.
    carried_findings : list[str]
        Prior findings carried forward (monotonic compounding); may be empty.
    provenance : str
        Pointer to the source grill.md / plan path (non-empty).

    Returns
    -------
    ReEntrySeed  fully validated seed ready for serialization.

    Raises
    ------
    ValueError  if any field fails ReEntrySeed.__post_init__ validation.
    """
    return ReEntrySeed(
        seed_version=SEED_SCHEMA_VERSION,
        source=SEED_SOURCE,
        target_stage=target_stage,
        feature=feature,
        prior_conclusion=prior_conclusion,
        invalidating_evidence=invalidating_evidence,
        must_satisfy=must_satisfy,
        cycle_count=cycle_count,
        carried_findings=carried_findings,
        provenance=provenance,
    )


# ---------------------------------------------------------------------------
# write_seed
# ---------------------------------------------------------------------------


def write_seed(feature_dir, seed):
    # type: (str, ReEntrySeed) -> str
    """Atomic write of a ReEntrySeed as JSON to <feature_dir>/grill-seed.json.

    Serializes via dataclasses.asdict + json.dumps (stdlib only).
    Uses mkstemp + os.replace for crash safety.
    Creates feature_dir if it does not exist.
    Returns the path written.

    On failure, unlinks the temp file and re-raises.
    """
    os.makedirs(feature_dir, exist_ok=True)
    out_path = os.path.join(feature_dir, "grill-seed.json")

    payload = json.dumps(dataclasses.asdict(seed), indent=2, ensure_ascii=False)

    tmp_fd, tmp_path = tempfile.mkstemp(
        prefix=".tmp-grill-seed-",
        suffix=".json",
        dir=feature_dir,
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.write("\n")
        os.replace(tmp_path, out_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    return out_path
