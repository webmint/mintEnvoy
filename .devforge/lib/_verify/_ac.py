"""_ac.py — spec acceptance-criteria parser + AC-result merger for /verify.

Public surface
--------------
  parse_acs(source) -> list[dict]
      Parse ``- [ ] **AC-N**: …`` / ``- [x] **AC-N**: …`` lines from a spec
      text string or a path to a spec file.  Returns a list of AC dicts, one
      per AC found in the ## Acceptance Criteria section.

      Each dict has:
        id        str   — "AC-1", "AC-2", …
        text      str   — the EARS sentence (first line + any continuation)
        checked   bool  — True when the box is ``- [x]``
        subsection str  — the nearest ### subsection heading above this AC,
                          e.g. "5.1 Tooling / artifact presence and absence"

  merge_ac_results(acs, agent_report_text) -> list[dict]
      Merge the ac-verifier agent's ``### Results`` table into the structured
      AC list produced by ``parse_acs``.

      Parameters
      ----------
      acs : list[dict]
          The structured AC list from ``parse_acs``.  Modified by copy —
          the input list is not mutated.
      agent_report_text : str
          The full text of the ac-verifier's markdown report (the
          ``## AC Verification Report`` block).  The ``### Results`` table
          is extracted from this text.

      Returns a new list[dict], one dict per AC in ``acs``, each with the
      original four fields plus:
        status   str  — agent status string (e.g. "PASS", "FAIL", "PARTIAL",
                        "MANUAL", "PASS (code)", "FAIL (code)", "PARTIAL (code)")
                        or "UNVERIFIED" when the agent produced no row for this AC.
        evidence str  — the Evidence cell from the agent's table, stripped,
                        or "" when the AC is UNVERIFIED.

      Agent rows for AC ids not present in ``acs`` are silently ignored.

Behaviour (parse_acs)
---------------------
  - Only lines inside the ## Acceptance Criteria section are processed;
    other sections (## 6. Out of Scope, ## 7. Technical Constraints, …) are
    ignored.
  - Subsections (### 5.N …) are tracked and attached to every AC found below
    them.  An AC that appears before any subsection heading carries an empty
    subsection string.
  - "N/A — <reason>" subsections that contain no ACs are skipped silently.
  - Non-AC lines (narrative, tables, "> Verification:" hints) are skipped.
  - Multi-line ACs: the spec format allows a continuation line (e.g. the
    "> Verification: …" hint block) directly after the checkbox.  We capture
    only the first (checkbox) line as ``text`` because that line is the EARS
    sentence.  This matches the AC-verifier agent's contract — it reads the
    sentence, not the hint.
  - Duplicate AC ids are accepted and returned in encounter order.
  - If the source has no ## Acceptance Criteria section, an empty list is
    returned (not an error).

Behaviour (merge_ac_results)
-----------------------------
  - The ``### Results`` section is located by scanning for the heading
    ``### Results`` (case-insensitive).  The table header row and the
    separator row (``|---|---|---|``) are skipped.  Parsing stops at the next
    ``###`` or ``##`` heading.
  - Each data row is split on ``|``; the AC id is the second cell (stripped),
    the status is the third cell (stripped), the evidence is the fourth cell
    (stripped and joined when multiple pipes exist in the evidence cell).
  - Agent rows whose AC id does not appear in ``acs`` are ignored.
  - ACs with no corresponding agent row receive ``status="UNVERIFIED"`` and
    ``evidence=""``.

Stdlib only.  Python 3.8+.
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Matches the start of the Acceptance Criteria section.
# Handles both numbered ("## 5. Acceptance Criteria") and plain variants.
_SECTION_RE = re.compile(r"^##\s+\d*\.?\s*Acceptance Criteria", re.IGNORECASE)

# Matches any level-2 section heading that would end the AC section.
# We stop when we see a new ## heading (but NOT a ### subsection heading).
_NEXT_LEVEL2_RE = re.compile(r"^##\s+", re.IGNORECASE)

# Matches a ### subsection heading inside the AC section.
_SUBSECTION_RE = re.compile(r"^###\s+(.+)$")

# Matches an AC checkbox line:
#   - [ ] **AC-N**: <text>
#   - [x] **AC-N**: <text>   (checked variant)
# The checkbox may be lowercase x or uppercase X.
_AC_LINE_RE = re.compile(
    r"^- \[([xX ])\]\s+\*\*AC-(\d+)\*\*:\s+(.*)"
)


# ---------------------------------------------------------------------------
# parse_acs
# ---------------------------------------------------------------------------


def parse_acs(source):
    # type: (str) -> List[Dict]
    """Parse AC checkboxes from a spec text or path.

    Parameters
    ----------
    source : str
        Either a path to a spec file (checked via os.path.exists) or the raw
        spec text.  When it is a path, the file is read as UTF-8 text.

    Returns
    -------
    list of dict
        One dict per AC found, in encounter order.  Empty list if the AC
        section is absent or contains no AC checkboxes.

    Dict shape:
        {
            "id":         "AC-N",           # e.g. "AC-1"
            "text":       "<EARS sentence>", # stripped
            "checked":    bool,             # True when - [x]
            "subsection": "<### heading>",  # e.g. "5.1 Tooling / …"
        }
    """
    # Resolve source → text.
    if os.path.exists(source):
        try:
            with open(source, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            return []
    else:
        text = source

    lines = text.splitlines()
    acs = []  # type: List[Dict]

    # Locate the ## Acceptance Criteria section.
    in_section = False
    current_subsection = ""  # type: str

    for line in lines:
        # --- Section entry ---
        if not in_section:
            if _SECTION_RE.match(line):
                in_section = True
            continue

        # --- Section exit: a new ## heading ends the AC section ---
        if _NEXT_LEVEL2_RE.match(line):
            break

        # --- Track ### subsection headings ---
        sub_m = _SUBSECTION_RE.match(line)
        if sub_m:
            current_subsection = sub_m.group(1).strip()
            continue

        # --- Capture AC checkbox lines ---
        ac_m = _AC_LINE_RE.match(line)
        if ac_m:
            check_char = ac_m.group(1)
            ac_num = ac_m.group(2)
            ac_text = ac_m.group(3).strip()
            acs.append(
                {
                    "id": "AC-{0}".format(ac_num),
                    "text": ac_text,
                    "checked": check_char.lower() == "x",
                    "subsection": current_subsection,
                }
            )

    return acs


# ---------------------------------------------------------------------------
# merge_ac_results
# ---------------------------------------------------------------------------

# Matches the ### Results heading (case-insensitive, optional leading #s).
_RESULTS_HEADING_RE = re.compile(r"^###\s+Results\s*$", re.IGNORECASE)

# Matches any level-2 or level-3 heading — used to stop Results parsing.
_HEADING_23_RE = re.compile(r"^##")

# Matches the table separator row: lines like |---|---|---| (all dashes/pipes).
_TABLE_SEP_RE = re.compile(r"^\|[-| ]+\|$")

# Matches the table header row: | AC | Status | Evidence |
# We skip it by checking whether the first data cell looks like a header word.
_HEADER_CELL_RE = re.compile(r"^ac$", re.IGNORECASE)

# Known valid status values from ac-verifier.md Output contract.
# The (code) suffix variants are the code-reading fallback markers.
_KNOWN_STATUSES = frozenset([
    "PASS", "FAIL", "PARTIAL", "MANUAL",
    "PASS (code)", "FAIL (code)", "PARTIAL (code)",
])


def _parse_results_table(agent_report_text):
    # type: (str) -> Dict[str, Tuple[str, str]]
    """Extract per-AC status+evidence from the agent's ``### Results`` table.

    Returns a dict mapping AC id (e.g. "AC-1") → (status, evidence).
    Unknown / unparseable rows are skipped silently.
    """
    lines = agent_report_text.splitlines()
    in_results = False
    rows = {}  # type: Dict[str, Tuple[str, str]]

    for line in lines:
        stripped = line.strip()

        if not in_results:
            if _RESULTS_HEADING_RE.match(stripped):
                in_results = True
            continue

        # Stop at the next section heading (## or ###), but NOT at the first
        # line of the Results block itself (which we just passed above).
        if _HEADING_23_RE.match(stripped):
            break

        # Skip blank lines and separator rows.
        if not stripped or _TABLE_SEP_RE.match(stripped):
            continue

        # Parse a table data row: | AC | Status | Evidence |
        # Split on | to get cells between first and last pipe.
        # parts[0] = '' (before first |), parts[-1] = '' (after last |)
        # parts[1] = AC id, parts[2] = Status, parts[3..] = Evidence cells
        if not stripped.startswith("|"):
            continue
        parts = stripped.split("|")
        if len(parts) < 4:
            continue

        ac_id = parts[1].strip()
        status = parts[2].strip()
        # Evidence may contain pipes (rare but possible) — rejoin remaining cells.
        evidence = "|".join(parts[3:-1]).strip() if len(parts) > 4 else parts[3].strip()

        # Skip the header row: ac_id cell would be "AC" (the column name).
        if _HEADER_CELL_RE.match(ac_id):
            continue

        # Only accept rows with a recognisable AC id pattern.
        if not ac_id.startswith("AC-"):
            continue

        rows[ac_id] = (status, evidence)

    return rows


def merge_ac_results(acs, agent_report_text):
    # type: (List[Dict], str) -> List[Dict]
    """Merge the ac-verifier agent's per-AC results into the structured AC list.

    Parameters
    ----------
    acs : list[dict]
        The structured AC list from ``parse_acs``.  Not mutated.
    agent_report_text : str
        Full markdown text of the ac-verifier's report.  The ``### Results``
        table is extracted from this text.

    Returns
    -------
    list[dict]
        A new list.  Each dict has the original four keys (``id``, ``text``,
        ``checked``, ``subsection``) plus:
          ``status``   — from the agent's Status cell, or "UNVERIFIED".
          ``evidence`` — from the agent's Evidence cell, or "".

    Unknown agent rows (AC id not in ``acs``) are silently ignored.
    ACs with no agent row receive ``status="UNVERIFIED"`` and ``evidence=""``.
    """
    agent_rows = _parse_results_table(agent_report_text)

    merged = []  # type: List[Dict]
    for ac in acs:
        ac_id = ac["id"]
        if ac_id in agent_rows:
            status, evidence = agent_rows[ac_id]
        else:
            status = "UNVERIFIED"
            evidence = ""

        merged.append({
            "id": ac_id,
            "text": ac["text"],
            "checked": ac["checked"],
            "subsection": ac["subsection"],
            "status": status,
            "evidence": evidence,
        })

    return merged
