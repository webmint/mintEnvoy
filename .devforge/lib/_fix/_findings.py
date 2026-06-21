"""_findings.py — parse review.md and verification.md into a unified working list.

OQ-1 decision: PERSISTED — reads on-disk artifacts (review.md and/or
verification.md) so /fix works in a fresh session after /review//verify ran
earlier, and so the parser can round-trip real producer output per the
test-immediately-after-write discipline.

Public surface
--------------
  read_findings(feature_dir, source) -> dict
      Parse specs/[feature]/review.md AND/OR specs/[feature]/verification.md
      NEEDS-WORK issues into one working list of remediation items.

      source: "review" | "verify" | "both" (default "both")
        "review"  — parse review.md only
        "verify"  — parse verification.md only (NEEDS-WORK issues)
        "both"    — parse both and union the lists

      Returns:
        {
          "items":   list[RemediationItem],   # the working list
          "sources": {"review": bool, "verify": bool},  # which files were found
        }

  A RemediationItem is a dict:
    {
      "title":       str,    # short description of the issue
      "severity":    str,    # "Critical" | "High" | "Medium" | "Info"
      "files_cited": list,   # file paths cited in the finding/issue
      "evidence":    str,    # quoted code or "" (review) / "" (verify issues)
      "source":      str,    # "review" | "verify"
    }

Parser notes
------------
review.md format (produced by _review._report.render_report):
  The ## Confirmed Findings section is re-parsed here using the same
  _verify._review_findings.read_review_findings function that /verify already
  uses — we import from the live producer module, NOT duplicate the parse logic.
  Each confirmed/contested finding → one RemediationItem.

verification.md format (produced by _verify._report.render_report):
  The ## Issues Found section lists issues like:
    ### <Severity>

    - [<Severity>] <file>:<line> — <pattern>  [<tag>]

  And the ## Verdict section contains **NEEDS WORK** or **APPROVED** etc.
  We only extract issues when the verdict is NEEDS WORK.
  The ## Reasons section lists plain prose reasons (one per "- " bullet).

Stdlib only.  Python 3.8+.  No side effects except file reads.
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Import the existing review.md parser (avoids duplication)
# ---------------------------------------------------------------------------

# _verify._review_findings is already shipped and tested; importing here
# keeps parse logic in one place (DRY) and ensures the parser round-trips
# against the real review.md producer.
# A missing _verify is a fatal deployment error that must fail loudly — no
# silent try/except fallback.
from _verify._review_findings import read_review_findings as _read_review_findings  # type: ignore[import]


# ---------------------------------------------------------------------------
# verification.md parser helpers
# ---------------------------------------------------------------------------

# Matches the ## Verdict section header.
_VERDICT_SECTION_RE = re.compile(r"^##\s+Verdict\s*$", re.IGNORECASE)

# Matches the ## Issues Found section header.
_ISSUES_SECTION_RE = re.compile(r"^##\s+Issues\s+Found\s*$", re.IGNORECASE)

# Matches any ## level-2 heading (to detect end of a section).
_LEVEL2_RE = re.compile(r"^##\s+")

# Matches an issue entry line:
#   - [<Severity>] <file>:<line> — <pattern>  [<optional-tag>]
# Also handles: - [<Severity>] <file> — <pattern>  (no line number)
_ISSUE_LINE_RE = re.compile(
    r"^-\s+\[([A-Za-z]+)\]\s+(.+?)\s+—\s+(.+?)\s*$"
)

# Matches **NEEDS WORK** / **APPROVED** / **REJECTED** in the ## Verdict section.
_VERDICT_LINE_RE = re.compile(r"\*\*([A-Z ]+)\*\*")

# Matches a reason line "- <text>" inside the ## Verdict / ## Reasons section.
_REASON_LINE_RE = re.compile(r"^-\s+(.+)")

# Matches a <file>:<line> location string.
_FILE_LINE_RE = re.compile(r"^(.+):(\d+)$")

# Known severity values from the verification.md producer.
_KNOWN_SEVERITIES = frozenset(["Critical", "High", "Medium", "Info"])


def _parse_verification_issues(text):
    # type: (str) -> Tuple[str, List[Dict]]
    """Parse the ## Issues Found section from verification.md text.

    Returns (verdict_str, issues_list).

    verdict_str: "NEEDS WORK" | "APPROVED" | "REJECTED" | "" (undetected)
    issues_list: list of dicts with keys:
      title, severity, files_cited, evidence, source="verify"

    Only returns issues when verdict is NEEDS WORK.
    """
    lines = text.splitlines()
    n = len(lines)

    verdict_str = ""
    raw_issues = []  # type: List[Dict]
    current_severity = ""

    i = 0
    while i < n:
        line = lines[i]

        # --- Detect ## Issues Found section ---
        if _ISSUES_SECTION_RE.match(line):
            i += 1
            while i < n:
                sec_line = lines[i]
                # End of section on next ## heading
                if _LEVEL2_RE.match(sec_line):
                    break
                # Severity subheading: ### High / ### Critical etc.
                stripped = sec_line.strip()
                if stripped.startswith("###") and not stripped.startswith("####"):
                    maybe_sev = stripped.lstrip("#").strip()
                    if maybe_sev in _KNOWN_SEVERITIES:
                        current_severity = maybe_sev
                else:
                    m = _ISSUE_LINE_RE.match(sec_line)
                    if m:
                        sev_in_brackets = m.group(1).strip()
                        loc = m.group(2).strip()
                        pattern = m.group(3).strip()
                        # Remove trailing tag annotations [CONTESTED] etc.
                        pattern = re.sub(r"\s+\[[A-Z\-]+\]\s*$", "", pattern).strip()
                        # Use severity from subheading if available, fallback to bracket.
                        sev = current_severity if current_severity else sev_in_brackets
                        # Extract file path from loc (may be "file:line" or just "file").
                        loc_m = _FILE_LINE_RE.match(loc)
                        if loc_m:
                            file_path = loc_m.group(1)
                        else:
                            file_path = loc
                        files_cited = [file_path] if file_path and file_path != "(unknown)" else []
                        raw_issues.append({
                            "title": pattern,
                            "severity": sev,
                            "files_cited": files_cited,
                            "evidence": "",
                            "source": "verify",
                        })
                i += 1
            continue

        # --- Detect ## Verdict section ---
        if _VERDICT_SECTION_RE.match(line):
            i += 1
            while i < n:
                sec_line = lines[i]
                if _LEVEL2_RE.match(sec_line):
                    break
                vm = _VERDICT_LINE_RE.search(sec_line)
                if vm and not verdict_str:
                    candidate = vm.group(1).strip()
                    if candidate in ("NEEDS WORK", "APPROVED", "REJECTED"):
                        verdict_str = candidate
                i += 1
            continue

        i += 1

    # Only return issues when the verdict is NEEDS WORK.
    if verdict_str == "NEEDS WORK":
        return verdict_str, raw_issues
    return verdict_str, []


# ---------------------------------------------------------------------------
# _review_finding_to_item
# ---------------------------------------------------------------------------


def _review_finding_to_item(finding):
    # type: (Dict) -> Dict
    """Convert a confirmed/contested finding from read_review_findings → RemediationItem."""
    file_path = finding.get("file") or ""
    files_cited = [file_path] if file_path and file_path != "(unknown file)" else []
    return {
        "title": finding.get("pattern") or "(no description)",
        "severity": finding.get("severity") or "Info",
        "files_cited": files_cited,
        "evidence": finding.get("evidence") or "",
        "source": "review",
    }


# ---------------------------------------------------------------------------
# read_findings (public)
# ---------------------------------------------------------------------------


def read_findings(feature_dir, source="both"):
    # type: (str, str) -> Dict
    """Parse review.md and/or verification.md into one unified working list.

    Parameters
    ----------
    feature_dir : str
        Path to the feature directory (e.g. "specs/001-auth/").
        review.md and verification.md are expected at <feature_dir>/review.md
        and <feature_dir>/verification.md respectively.
    source : str
        "review"  — parse review.md only
        "verify"  — parse verification.md NEEDS-WORK issues only
        "both"    — parse both (default)

    Returns
    -------
    dict:
      {
        "items":   list[dict],  # RemediationItem list (may be empty)
        "sources": {
          "review":             bool,  # review.md was found and parsed
          "verify":             bool,  # verification.md was found and parsed
          "verify_verdict":     str,   # the verification.md verdict string ("NEEDS WORK" | "APPROVED" | ... | "")
          "review_missing":     bool,  # True when review.md not found
          "verify_missing":     bool,  # True when verification.md not found
        }
      }
    """
    feature_dir = feature_dir.rstrip("/\\")

    items = []  # type: List[Dict]
    review_found = False
    review_missing = True
    verify_found = False
    verify_missing = True
    verify_verdict = ""

    # --- review.md ---
    if source in ("review", "both"):
        review_path = os.path.join(feature_dir, "review.md")
        if os.path.isfile(review_path):
            review_missing = False
            parsed = _read_review_findings(review_path)

            if not parsed.get("missing", True):
                review_found = True
                for f in (parsed.get("confirmed") or []):
                    items.append(_review_finding_to_item(f))
                for f in (parsed.get("contested") or []):
                    items.append(_review_finding_to_item(f))

    # --- verification.md ---
    if source in ("verify", "both"):
        verify_path = os.path.join(feature_dir, "verification.md")
        if os.path.isfile(verify_path):
            verify_missing = False
            try:
                with open(verify_path, "r", encoding="utf-8") as fh:
                    text = fh.read()
            except OSError:
                text = ""
            if text:
                verdict_str, verify_items = _parse_verification_issues(text)
                verify_verdict = verdict_str
                if verify_items:
                    verify_found = True
                    items.extend(verify_items)

    return {
        "items": items,
        "sources": {
            "review": review_found,
            "verify": verify_found,
            "verify_verdict": verify_verdict,
            "review_missing": review_missing,
            "verify_missing": verify_missing,
        },
    }
