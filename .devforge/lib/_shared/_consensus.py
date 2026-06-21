"""_consensus -- cross-agent consensus merge for ParsedFinding records.

Implements the dedup + corroboration stage of /audit (and any other command
that collects multi-agent findings lists).

WHY the key changed from (file, line, pattern) to (file, line, category)
-------------------------------------------------------------------------
The old key hashed (file, line, normalised_pattern) so two agents reporting
the same bug with different wording — e.g. "Missing return — silent path" vs
"Early-return omission" at the same file:line — landed in SEPARATE groups.
This inflated confirmed-finding counts (testForge20 e2e showed 3 findings for
the same bug) and made the corroboration signal meaningless.

The category field is a fixed enum (mislogic / system_design / best_practice /
duplication / security / blind_spot) declared by the producer.  Two findings at
the same (file, line, category) are the same bug-class at the same location;
wording differences are noise.  The key is mechanical (enum lookup, no semantic
or LLM matching).

Algorithm
---------
  1. Group key = (file_path, line_number, category)
     category defaults to "mislogic" when missing (matches FindingSchema default).
     line_number is exact (no tolerance — within a single pass, agents reading
     the same code cite the same line; exact-line keeps over-merge low).
  2. Group ALL findings by key (any agent, any wording).
  3. Each group collapses to exactly ONE representative:
     - "Best" = highest severity (lowest SEVERITY_ENUM index).
     - Tie-break: alphabetically first agent name (deterministic).
     - representative gets merged_count = total findings in the group (≥ 1).
  4. Corroboration is gated on ≥ 2 DISTINCT agent names in the group:
     - Tag [CROSS-AGENT] on the representative.
     - Bump severity one level (Info→Medium→High→Critical, capped at Critical).
     - Add the key to consensus_map (mapping key → sorted distinct agent list).
     A group with only same-agent duplicates is deduped (collapsed) but gets
     NO [CROSS-AGENT] tag, NO severity bump, and NO consensus_map entry.

Tie-break for "highest severity": SEVERITY_ENUM order (Critical=0, High=1,
Medium=2, Info=3) — lower index = higher severity.  When multiple findings
share the same highest severity, the one with alphabetically first agent
name is kept for determinism.

merged_count field
------------------
Each representative finding dict carries a merged_count int (≥ 1) equal to
the number of raw findings that collapsed into it.  For a true singleton it is
1.  Downstream consumers may surface this for auditability (e.g. "raised by N
agents/reports").  The field is additive and does not affect existing logic.

Stdlib only.  Python 3.8+.
"""

from __future__ import annotations

import copy
from typing import List

from _shared.findings_schema import SEVERITY_ENUM  # type: ignore[import]

# ---------------------------------------------------------------------------
# Severity helpers (shared with _rank.py via _bump_severity)
# ---------------------------------------------------------------------------

# SEVERITY_ENUM = ("Critical", "High", "Medium", "Info") — index 0 is highest.
_SEV_RANK = {s: i for i, s in enumerate(SEVERITY_ENUM)}  # Critical=0 .. Info=3

_DEFAULT_CATEGORY = "mislogic"


def _bump_severity(severity, levels=1):
    # type: (str, int) -> str
    """Return severity bumped up by ``levels`` steps, capped at Critical.

    "Up" means towards Critical (lower index in SEVERITY_ENUM).
    If severity is not in SEVERITY_ENUM, it is returned unchanged.

    Examples:
        _bump_severity("Info", 1) → "Medium"
        _bump_severity("High", 1) → "Critical"
        _bump_severity("Critical", 1) → "Critical"   (capped)
        _bump_severity("Medium", 2) → "Critical"     (capped)
    """
    if severity not in _SEV_RANK:
        return severity
    current_idx = _SEV_RANK[severity]
    new_idx = max(0, current_idx - levels)
    return SEVERITY_ENUM[new_idx]


# ---------------------------------------------------------------------------
# Group key
# ---------------------------------------------------------------------------

def _make_group_key(finding):
    # type: (dict) -> tuple
    """Return the grouping key tuple for a ParsedFinding dict.

    Key = (file_path, line_number, category).

    file_path and line_number are taken as-is (exact; no normalisation).
    category defaults to "mislogic" when absent or falsy, matching the
    FindingSchema field default.
    """
    file_path = finding.get("file", "") or ""
    line_no = finding.get("line", 0)
    category = finding.get("category") or _DEFAULT_CATEGORY
    return (file_path, line_no, category)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_consensus(findings):
    # type: (List[dict]) -> dict
    """Merge findings from multiple agents into a deduplicated list.

    Groups by (file, line, category) — see module docstring for rationale.

    Returns a dict with keys:
      findings      : list of ParsedFinding dicts (one per group, each with a
                      merged_count field indicating how many raw findings
                      collapsed into it)
      consensus_map : {group_key_str: [agent_name, ...]} for groups that had
                      ≥ 2 distinct agents (corroboration gate).
                      The key is "<file>:<line>:<category>" for readability.
    """
    # Build groups keyed by (file, line, category) tuple
    groups = {}   # type: dict
    order = []    # preserve insertion order for output stability

    for finding in findings:
        key = _make_group_key(finding)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(finding)

    result_findings = []
    consensus_map = {}

    for key in order:
        group = groups[key]
        distinct_agents = sorted(set(f.get("agent", "") for f in group))

        # Always collapse the group to the best representative
        merged = _merge_group(group)
        merged = dict(merged)
        merged["merged_count"] = len(group)

        if len(distinct_agents) >= 2:
            # Corroboration: tag, bump, and record in consensus_map
            tags = list(merged.get("tags", []) or [])
            if "[CROSS-AGENT]" not in tags:
                tags.append("[CROSS-AGENT]")
            merged["tags"] = tags
            merged["severity"] = _bump_severity(merged.get("severity", "Info"), 1)
            # Use a readable string as the consensus_map key
            key_str = "{0}:{1}:{2}".format(key[0], key[1], key[2])
            consensus_map[key_str] = distinct_agents

        result_findings.append(merged)

    return {
        "findings": result_findings,
        "consensus_map": consensus_map,
    }


def _merge_group(group):
    # type: (List[dict]) -> dict
    """Select the best representative finding from a group.

    "Best" = highest severity (lowest SEVERITY_ENUM index).
    Tie-break: alphabetically first agent name.
    Returns a deep copy of the selected finding.
    """

    def _sort_key(f):
        sev = f.get("severity", "Info")
        sev_idx = _SEV_RANK.get(sev, len(SEVERITY_ENUM))
        agent = f.get("agent", "")
        return (sev_idx, agent)

    best = min(group, key=_sort_key)
    return copy.deepcopy(best)
