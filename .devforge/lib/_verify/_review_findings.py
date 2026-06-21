"""_review_findings.py — parse specs/[feature]/review.md into folded findings.

Public surface
--------------
  read_review_findings(review_md_path) -> dict
      Parse the review.md produced by ``review_helper render-report`` and
      return a folded-findings summary dict for use by the /verify verdict.

      When review_md_path is a *directory* (e.g. the feature dir), the
      function appends "/review.md" automatically.

      When the file is absent, returns a dict with ``missing=True`` and
      empty findings lists.

Result dict shape
-----------------
  {
    "missing":    bool,         # True when review.md was not found
    "confirmed":  list[dict],   # confirmed findings (from ## Confirmed Findings)
    "contested":  list[dict],   # [CONTESTED] findings (tagged in the headline)
    "summary": {
        "critical": int,
        "high":     int,
        "medium":   int,
        "info":     int,
        "confirmed_count": int,
        "contested_count": int,
        "dismissed_count": int,
        "uncertain_count": int,
    }
  }

Each finding dict (confirmed or contested)
  {
    "severity":  str,   # "Critical" | "High" | "Medium" | "Info"
    "file":      str,   # file path from "  File: …" detail line
    "line":      int,   # -1 when absent
    "pattern":   str,   # description from "  Pattern: …" or first-line title
    "category":  str,   # "  Category: …" detail line, empty str when absent
    "tags":      list,  # e.g. ["[CONTESTED]"] when present in first line
    "confidence": str,  # from "  Confidence: …" detail line
  }

Parser notes
------------
The review.md structure (produced by _review/_report.py ``render_report``) is:

    # Feature Review — <feature> — <date>
    ...
    ## Confirmed — Top Priorities
    1. [High] src/a.py:10 — <desc> [Likely] [CONTESTED]
    ...

    ## Confirmed Findings
    ### <file-path>
    #### <Category Label>
    - [F-001] [High] :10 — <desc>  [Likely]  [CONTESTED]
      Severity: High
      File: src/a.py
      Line: 10
      Pattern: <pattern>
      Confidence: Likely
      Category: mislogic
      Evidence:
      ```
      ...
      ```
      Why it's wrong: ...
      Remediation: ...

    ## Summary
    - Critical: 0 | High: 1 | Medium: 0 | Info: 0
    - Confirmed: N | Contested: N | Dismissed: N | Uncertain: N

    ## Dismissed / Worth a Glance
    ...

    ## Methodology
    ...

This parser extracts:
  - The ## Confirmed Findings block (confirmed + [CONTESTED] entries).
  - The ## Summary counts.
  - The ``missing`` flag when the file is absent.

Stdlib only.  Python 3.8+.
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Matches the "## Confirmed Findings" section header.
_CONFIRMED_SECTION_RE = re.compile(r"^##\s+Confirmed\s+Findings\s*$", re.IGNORECASE)

# Matches a level-2 heading that would end the Confirmed Findings section
# (any ## heading that is NOT "## Confirmed Findings").
_LEVEL2_RE = re.compile(r"^##\s+")

# Matches a finding first-line inside the grouped block:
#   - [<id>] [<severity>] :<line> — <desc>  [<confidence>]  [CONTESTED]
# The leading "- " is required; everything after is captured loosely.
_FINDING_FIRST_LINE_RE = re.compile(
    r"^- (?:\[([A-Z0-9\-]+)\]\s+)?\[([A-Za-z]+)\]\s*(:[0-9]+)?\s*—\s*(.+?)\s*$"
)

# Matches a detail line ("  Key: value") inside a finding body.
_DETAIL_LINE_RE = re.compile(r"^  ([A-Za-z ]+):\s*(.*)")

# Matches the Summary section counts line:
#   - Critical: 0 | High: 1 | Medium: 0 | Info: 0
_SUMMARY_COUNTS_RE = re.compile(
    r"Critical:\s*(\d+)\s*\|\s*High:\s*(\d+)\s*\|\s*Medium:\s*(\d+)\s*\|\s*Info:\s*(\d+)"
)

# Matches the confirmed/dismissed/uncertain/contested counts line:
#   - Confirmed: N | Contested: N | Dismissed: N | Uncertain: N
_SUMMARY_PARTITION_RE = re.compile(
    r"Confirmed:\s*(\d+)\s*\|\s*Contested:\s*(\d+)\s*\|\s*Dismissed:\s*(\d+)\s*\|\s*Uncertain:\s*(\d+)"
)

# Matches [CONTESTED] tag in the first line of a finding.
_CONTESTED_TAG_RE = re.compile(r"\[CONTESTED\]")

# Matches [CONSTITUTION-VIOLATION] tag in the first line of a finding.
_CONSTITUTION_TAG_RE = re.compile(r"\[CONSTITUTION-VIOLATION\]")

# Matches a confidence string in the finding first line: [Certain], [Likely], [Speculative]
_CONFIDENCE_IN_FIRSTLINE_RE = re.compile(r"\[(Certain|Likely|Speculative)\]")


# ---------------------------------------------------------------------------
# _resolve_path helper
# ---------------------------------------------------------------------------


def _resolve_path(review_md_path):
    # type: (str) -> str
    """Return the review.md path.

    If review_md_path is a directory, append /review.md.
    """
    if os.path.isdir(review_md_path):
        return os.path.join(review_md_path, "review.md")
    return review_md_path


# ---------------------------------------------------------------------------
# _parse_confirmed_findings
# ---------------------------------------------------------------------------


def _parse_confirmed_findings(lines, start_idx):
    # type: (List[str], int) -> Tuple[List[dict], int]
    """Parse from the ## Confirmed Findings line onward.

    Returns (findings_list, next_line_idx) where next_line_idx is the first
    line past the section (a new ## heading or end of file).

    Each finding dict has the shape described in the module docstring.
    """
    findings = []  # type: List[dict]
    i = start_idx + 1  # skip the ## Confirmed Findings line itself
    n = len(lines)

    current = None  # type: Optional[dict]
    in_evidence_block = False

    while i < n:
        line = lines[i]

        # --- End of section ---
        if _LEVEL2_RE.match(line):
            if current is not None:
                findings.append(current)
                current = None
            break

        # --- Evidence block fence ---
        stripped = line.strip()
        if stripped == "```":
            in_evidence_block = not in_evidence_block
            i += 1
            continue

        if in_evidence_block:
            i += 1
            continue

        # --- Finding first line ---
        m = _FINDING_FIRST_LINE_RE.match(line)
        if m:
            # Flush previous finding.
            if current is not None:
                findings.append(current)

            finding_id = (m.group(1) or "").strip()
            severity = (m.group(2) or "Info").strip()
            first_line_text = (m.group(4) or "").strip()

            # Extract tags from the rest of the first-line text.
            tags = []  # type: List[str]
            if _CONTESTED_TAG_RE.search(first_line_text):
                tags.append("[CONTESTED]")
            if _CONSTITUTION_TAG_RE.search(first_line_text):
                tags.append("[CONSTITUTION-VIOLATION]")

            # Extract confidence from first-line brackets at end.
            conf_m = _CONFIDENCE_IN_FIRSTLINE_RE.search(first_line_text)
            confidence_from_first = conf_m.group(1) if conf_m else "Speculative"

            # Strip the confidence + tag brackets from the description.
            desc = _CONFIDENCE_IN_FIRSTLINE_RE.sub("", first_line_text)
            desc = _CONTESTED_TAG_RE.sub("", desc).strip()
            # Also strip trailing [CROSS-AGENT] etc.
            desc = re.sub(r"\[[A-Z\-]+\]", "", desc).strip()

            current = {
                "finding_id": finding_id,
                "severity": severity,
                "file": "",
                "line": -1,
                "pattern": desc,
                "category": "",
                "tags": tags,
                "confidence": confidence_from_first,
            }
            i += 1
            continue

        # --- Detail lines (only meaningful if we are inside a finding) ---
        if current is not None:
            dm = _DETAIL_LINE_RE.match(line)
            if dm:
                key = dm.group(1).strip().lower()
                val = dm.group(2).strip()
                if key == "severity":
                    current["severity"] = val
                elif key == "file":
                    current["file"] = val
                elif key == "line":
                    try:
                        current["line"] = int(val)
                    except (ValueError, TypeError):
                        pass
                elif key == "pattern":
                    current["pattern"] = val
                elif key == "confidence":
                    current["confidence"] = val
                elif key == "category":
                    current["category"] = val

        i += 1

    # Flush last finding if we hit end-of-file.
    if current is not None:
        findings.append(current)

    return findings, i


# ---------------------------------------------------------------------------
# _parse_summary
# ---------------------------------------------------------------------------


def _parse_summary(lines, start_idx):
    # type: (List[str], int) -> dict
    """Extract counts from the ## Summary section.

    Returns a dict with keys: critical, high, medium, info,
    confirmed_count, contested_count, dismissed_count, uncertain_count.
    All default to 0 if not found.
    """
    result = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "info": 0,
        "confirmed_count": 0,
        "contested_count": 0,
        "dismissed_count": 0,
        "uncertain_count": 0,
    }  # type: dict

    i = start_idx + 1
    n = len(lines)

    while i < n:
        line = lines[i]
        if _LEVEL2_RE.match(line):
            break

        m = _SUMMARY_COUNTS_RE.search(line)
        if m:
            result["critical"] = int(m.group(1))
            result["high"] = int(m.group(2))
            result["medium"] = int(m.group(3))
            result["info"] = int(m.group(4))

        pm = _SUMMARY_PARTITION_RE.search(line)
        if pm:
            result["confirmed_count"] = int(pm.group(1))
            result["contested_count"] = int(pm.group(2))
            result["dismissed_count"] = int(pm.group(3))
            result["uncertain_count"] = int(pm.group(4))

        i += 1

    return result


# ---------------------------------------------------------------------------
# read_review_findings (public)
# ---------------------------------------------------------------------------


def read_review_findings(review_md_path):
    # type: (str) -> dict
    """Parse review.md and return a folded-findings dict for /verify verdict.

    Parameters
    ----------
    review_md_path : str
        Path to review.md, OR to the feature directory (review.md appended).

    Returns
    -------
    dict with keys:
        missing   bool        — True when the file does not exist
        confirmed list[dict]  — confirmed findings from ## Confirmed Findings
        contested list[dict]  — [CONTESTED]-tagged findings from the same section
        summary   dict        — severity + partition counts from ## Summary
    """
    path = _resolve_path(review_md_path)

    if not os.path.isfile(path):
        return {
            "missing": True,
            "confirmed": [],
            "contested": [],
            "summary": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "info": 0,
                "confirmed_count": 0,
                "contested_count": 0,
                "dismissed_count": 0,
                "uncertain_count": 0,
            },
        }

    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return {
            "missing": True,
            "confirmed": [],
            "contested": [],
            "summary": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "info": 0,
                "confirmed_count": 0,
                "contested_count": 0,
                "dismissed_count": 0,
                "uncertain_count": 0,
            },
        }

    lines = text.splitlines()
    n = len(lines)

    all_findings = []  # type: List[dict]
    summary = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "info": 0,
        "confirmed_count": 0,
        "contested_count": 0,
        "dismissed_count": 0,
        "uncertain_count": 0,
    }  # type: dict

    # Locate sections.
    _SUMMARY_SECTION_RE = re.compile(r"^##\s+Summary\s*$", re.IGNORECASE)

    i = 0
    while i < n:
        line = lines[i]

        if _CONFIRMED_SECTION_RE.match(line):
            parsed, i = _parse_confirmed_findings(lines, i)
            all_findings = parsed
            continue

        if _SUMMARY_SECTION_RE.match(line):
            summary = _parse_summary(lines, i)
            # _parse_summary does not advance i past the section; we just move on.

        i += 1

    # Split findings into confirmed vs contested by [CONTESTED] tag.
    confirmed = []  # type: List[dict]
    contested = []  # type: List[dict]
    for f in all_findings:
        if "[CONTESTED]" in f.get("tags", []):
            contested.append(f)
        else:
            confirmed.append(f)

    return {
        "missing": False,
        "confirmed": confirmed,
        "contested": contested,
        "summary": summary,
    }
