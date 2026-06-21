"""_rank -- force-rank and recurring-issues mapping for ParsedFinding records.

Implements §4.4 (recurring-issues mapping) and §4.5 (force-rank Top 10/5)
of the /audit spec.

Recurring-issues mapping (§4.4)
---------------------------------
For each past finding entry ``{file, fingerprint}``:
  - "fingerprint" is a 5-10 word key extracted from the past description.
  - Match rule (§4.4 step 2): EXACT substring on BOTH file_path AND pattern.
    No fuzzy matching.
  - Apply mapping:
      RESOLVED          — no match in working list + file_path unchanged
                          (caller determines "unchanged"; we just check no match)
      [RECURRING]       — match in working list at the SAME file path
                          → bump severity one level
      [RECURRING-SPREAD] — match in working list where fingerprint matches
                           pattern but at a DIFFERENT file path
                          → bump severity two levels

Force-rank (§4.5)
-----------------
score = severity_weight × confidence_weight × cross_agent_bonus × recurring_bonus

  severity_weight   = {Critical: 8, High: 4, Medium: 2, Info: 1}
  confidence_weight = {Certain: 3, Likely: 2, Speculative: 1}
  cross_agent_bonus = 1.5 if [CROSS-AGENT] in tags else 1.0
  recurring_bonus   = 2.0 if [RECURRING-SPREAD] in tags
                      1.5 if [RECURRING] in tags
                      1.0 otherwise

pass_count is retained as a descriptive field but does NOT multiply the score.
Correlated re-generation across passes is not independent corroboration.

Sort descending.  Ties broken by: file (alphabetical asc), then line (int asc),
then agent (alphabetical asc).  All tie-break keys are deterministic.

Stdlib only.  Python 3.8+.
"""

from __future__ import annotations

import copy
from typing import List

from _shared._consensus import _bump_severity  # type: ignore[import]

# ---------------------------------------------------------------------------
# Weight tables
# ---------------------------------------------------------------------------

_SEVERITY_WEIGHT = {
    "Critical": 8,
    "High": 4,
    "Medium": 2,
    "Info": 1,
}

_CONFIDENCE_WEIGHT = {
    "Certain": 3,
    "Likely": 2,
    "Speculative": 1,
}

# ---------------------------------------------------------------------------
# Recurring-issues mapping
# ---------------------------------------------------------------------------


def map_recurring_issues(findings, past_findings):
    # type: (List[dict], List[dict]) -> dict
    """Tag findings with [RECURRING] or [RECURRING-SPREAD] based on past findings.

    Parameters
    ----------
    findings:     List of current ParsedFinding dicts (post-consensus).
    past_findings: List of dicts with keys ``file`` and ``fingerprint``.
                   ``file``        — the past file path (exact substring match)
                   ``fingerprint`` — short description key (exact substring match
                                    on pattern field)

    Returns a dict with keys:
      findings         : updated list (copies; originals not mutated)
      recurring_status : [{past: <past_dict>, status: "RESOLVED"|"RECURRING"|"RECURRING-SPREAD"}]

    Matching rule (§4.4 step 2):
      A current finding matches a past entry when:
        past["fingerprint"] is a substring of current["pattern"]  AND
        one of:
          (a) past["file"] is empty/missing, OR past["file"] is a substring of
              current["file"]
              → [RECURRING] tag + bump 1 level
          (b) past["file"] is non-empty AND past["file"] is NOT a substring of
              current["file"]
              → [RECURRING-SPREAD] tag + bump 2 levels

    Empty/missing past["file"] always produces [RECURRING] (+1), never
    [RECURRING-SPREAD] (+2).  Only a non-empty past_file that differs from
    the current finding's file qualifies as spread.

    A past entry is RESOLVED when NO current finding matches its fingerprint.
    """
    findings = [copy.deepcopy(f) for f in findings]
    recurring_status = []

    for past in past_findings:
        past_file = past.get("file", "") or ""
        past_fp = past.get("fingerprint", "") or ""

        matched_same = []   # findings where fingerprint + same file
        matched_diff = []   # findings where fingerprint + different file

        for finding in findings:
            curr_pattern = finding.get("pattern", "") or ""
            curr_file = finding.get("file", "") or ""

            # fingerprint must be a substring of pattern
            if not past_fp or past_fp not in curr_pattern:
                continue

            # file match?  Empty past_file → cannot confirm spread;
            # treat as same-file (RECURRING, not RECURRING-SPREAD).
            if not past_file or past_file in curr_file:
                matched_same.append(finding)
            else:
                matched_diff.append(finding)

        if matched_same:
            # [RECURRING] — same file
            for finding in matched_same:
                tags = list(finding.get("tags", []) or [])
                if "[RECURRING]" not in tags and "[RECURRING-SPREAD]" not in tags:
                    tags.append("[RECURRING]")
                finding["tags"] = tags
                finding["severity"] = _bump_severity(
                    finding.get("severity", "Info"), 1
                )
            recurring_status.append({"past": past, "status": "RECURRING"})
        elif matched_diff:
            # [RECURRING-SPREAD] — different file
            for finding in matched_diff:
                tags = list(finding.get("tags", []) or [])
                if "[RECURRING-SPREAD]" not in tags:
                    tags.append("[RECURRING-SPREAD]")
                    # Remove weaker RECURRING tag if already set
                    if "[RECURRING]" in tags:
                        tags.remove("[RECURRING]")
                finding["tags"] = tags
                finding["severity"] = _bump_severity(
                    finding.get("severity", "Info"), 2
                )
            recurring_status.append({"past": past, "status": "RECURRING-SPREAD"})
        else:
            # No match — resolved
            recurring_status.append({"past": past, "status": "RESOLVED"})

    return {
        "findings": findings,
        "recurring_status": recurring_status,
    }


# ---------------------------------------------------------------------------
# Score computation
# ---------------------------------------------------------------------------


def _score_finding(finding):
    # type: (dict) -> float
    """Compute the force-rank score for a single finding.

    score = severity_weight × confidence_weight × cross_agent_bonus
            × recurring_bonus

    pass_count is retained as a descriptive field on the finding dict but
    does NOT inflate the score.  Correlated re-generation across passes is
    not independent corroboration; only the refutation stage (Change A) may
    raise confidence/score on a multi-pass finding.
    """
    severity = finding.get("severity", "Info")
    confidence = finding.get("confidence", "Speculative")
    tags = finding.get("tags", []) or []

    sev_w = _SEVERITY_WEIGHT.get(severity, 1)
    conf_w = _CONFIDENCE_WEIGHT.get(confidence, 1)
    cross_bonus = 1.5 if "[CROSS-AGENT]" in tags else 1.0
    if "[RECURRING-SPREAD]" in tags:
        rec_bonus = 2.0
    elif "[RECURRING]" in tags:
        rec_bonus = 1.5
    else:
        rec_bonus = 1.0

    return sev_w * conf_w * cross_bonus * rec_bonus


# ---------------------------------------------------------------------------
# Force-rank
# ---------------------------------------------------------------------------


def force_rank(findings, narrow=False):
    # type: (List[dict], bool) -> dict
    """Rank findings by score and return the top N.

    Parameters
    ----------
    findings: List of ParsedFinding dicts (post-consensus, post-recurring).
    narrow:   If True, return top 5; else top 10.

    Returns a dict with keys:
      top : list of {"finding": <dict>, "score": <float>} in descending order
    """
    top_n = 5 if narrow else 10

    scored = []
    for finding in findings:
        score = _score_finding(finding)
        scored.append((score, finding))

    # Sort: descending score, then tie-break deterministically
    def _sort_key(item):
        score, finding = item
        file_ = finding.get("file", "") or ""
        raw_line = finding.get("line")
        # -1 is the "unspecified" sentinel (findings_schema); treat it and any
        # non-1-based value as 0 so unspecified lines sort behind real ones.
        line_ = raw_line if (isinstance(raw_line, int)
                             and not isinstance(raw_line, bool)
                             and raw_line >= 1) else 0
        agent_ = finding.get("agent", "") or ""
        return (-score, file_, line_, agent_)

    scored.sort(key=_sort_key)

    # Deduplicate by (file, line): when both are present, keep only the
    # highest-scored finding per location (which is the first encountered
    # after sorting).  Findings missing file or line each occupy their own
    # slot — do not collapse them.
    top = []
    seen_locations = set()  # type: set
    for score, finding in scored:
        if len(top) >= top_n:
            break
        file_ = finding.get("file")
        line_ = finding.get("line")
        # -1 is the "unspecified" sentinel — treat it like a missing line:
        # two findings at the same file with unknown lines are not confirmed
        # co-located, so each keeps its own slot.
        if file_ is not None and line_ is not None and line_ != -1:
            loc = (file_, line_)
            if loc in seen_locations:
                continue
            seen_locations.add(loc)
        top.append({"finding": finding, "score": score})

    return {"top": top}
