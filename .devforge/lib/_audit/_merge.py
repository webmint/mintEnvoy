"""_merge -- tolerant multi-pass union merge for ParsedFinding records.

Implements the multi-pass union merge used when /audit runs the pipeline K
times and needs ONE merged result across both the 4 agents AND the K passes.

Unlike compute_consensus (which keys on exact (file, line, category)),
this merge is location-only: it groups by file then clusters by line proximity
(tolerance TOL=3).  Pattern differences within a cluster are intentionally
ignored -- that is the point of a tolerant cross-pass union.

Algorithm summary (see merge_passes docstring for full spec):
  1. Flatten pools into (pass_idx, finding) pairs.
  2. Group by file (exact match; file order = first appearance order).
  3. Within a file, cluster by greedy anchor with TOL=3.
     - -1 sentinel members form their own cluster per file (never merge with
       real lines).
  4. Collapse each cluster: pick representative by deterministic tie-break.
  5. Annotate representative with corroboration signals:
     - agent_count >= 2 → [CROSS-AGENT] tag only (severity NOT bumped here;
       location-tolerant clustering is too permissive for a severity signal).
     - pass_count >= 2  → [MULTI-PASS:{k}] tag; confidence is NOT raised
       (correlated re-generation is not independent corroboration).
     - rep["pass_count"] always set (even when 1).
  6. Output order: file first-appearance order; within file, anchor-line
     ascending; -1 sentinel clusters last within each file.

Stdlib only.  Python 3.8+.
No I/O, no LLM, no network, no argparse.
"""

from typing import Dict, List, Tuple

from _shared.findings_schema import SEVERITY_ENUM  # type: ignore[import]

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

TOL = 3  # Line-proximity clustering tolerance (line - anchor <= TOL merges, line - anchor > TOL splits)

# Confidence rank: lower index = higher confidence.
_CONF_RANK = {"Certain": 0, "Likely": 1, "Speculative": 2}

# Severity rank: lower index = higher severity (Critical=0 .. Info=3)
_SEV_RANK = {s: i for i, s in enumerate(SEVERITY_ENUM)}

# Sentinel value for "unspecified" line number
_LINE_SENTINEL = -1

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _sev_rank(f):
    # type: (dict) -> int
    """Severity rank of a finding dict; unknowns sort last."""
    return _SEV_RANK.get(f.get("severity", ""), len(SEVERITY_ENUM))


def _conf_rank(f):
    # type: (dict) -> int
    """Confidence rank of a finding dict; unknowns sort last."""
    return _CONF_RANK.get(f.get("confidence", ""), len(_CONF_RANK))


def _pick_representative(members):
    # type: (List[dict]) -> dict
    """Select the best representative from a cluster using the deterministic
    tie-break chain:
      1. highest severity (lowest _SEV_RANK index)
      2. highest confidence (lowest _CONF_RANK index)
      3. longest evidence string
      4. alphabetically-first agent
      5. smallest line number
      6. insertion order within the cluster (lowest index wins)

    Returns a shallow copy of the chosen dict. The caller must replace
    rep['tags'] entirely (not append in-place) to avoid mutating the
    original finding's tag list.
    """
    def sort_key(idx_f):
        # type: (tuple) -> tuple
        idx, f = idx_f
        evidence_len = len(f.get("evidence", "") or "")
        agent = f.get("agent", "")
        line = f.get("line", 0)
        # Negate evidence_len so longest sorts first (smallest key wins)
        return (_sev_rank(f), _conf_rank(f), -evidence_len, agent, line, idx)

    _, best = min(enumerate(members), key=sort_key)
    return dict(best)


def _dedup_tags(tags):
    # type: (List[str]) -> List[str]
    """Return a new list with duplicates removed, preserving first-seen order."""
    seen = set()  # type: set
    result = []   # type: List[str]
    for t in tags:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result


def _union_tags(members):
    # type: (List[dict]) -> List[str]
    """Return the union of all members' tag lists, preserving stable order
    (first-seen across members in iteration order, deduped).
    """
    seen = set()  # type: set
    result = []   # type: List[str]
    for f in members:
        for t in (f.get("tags") or []):
            if t not in seen:
                seen.add(t)
                result.append(t)
    return result



def _cluster_file_members(members_with_pass):
    # type: (List[Tuple[int, dict]]) -> List[List[Tuple[int, dict]]]
    """Partition (pass_idx, finding) pairs for one file into clusters by line
    proximity using greedy anchor clustering with TOL.

    Sentinel (-1) members are collected into a single cluster placed LAST.
    Real-line members are sorted by line ascending (stable; tie-break by agent
    then by position in the input list for stability).

    Algorithm for real-line members:
      - Sort ascending by line, then agent, then input order.
      - Open first cluster at the first member (anchor = that member's line).
      - Each subsequent member: if line - anchor <= TOL, add to current cluster.
        Else open a new cluster (this member becomes the new anchor).

    Returns list of clusters in output order: real-line clusters (anchor-line
    ascending) followed by the sentinel cluster (if non-empty).
    """
    sentinel_members = []   # type: List[Tuple[int, dict]]
    real_members = []       # type: List[Tuple[int, dict]]

    for idx, (pass_idx, f) in enumerate(members_with_pass):
        if f.get("line", _LINE_SENTINEL) == _LINE_SENTINEL:
            sentinel_members.append((pass_idx, f))
        else:
            real_members.append((idx, pass_idx, f))

    # Sort real members: primary = line, secondary = agent, tertiary = input order
    real_members.sort(key=lambda t: (t[2].get("line", 0), t[2].get("agent", ""), t[0]))

    # Greedy anchor clustering
    clusters = []  # type: List[List[Tuple[int, dict]]]
    current_cluster = []  # type: List[Tuple[int, dict]]
    anchor_line = None  # type: object

    for _, pass_idx, f in real_members:
        line = f.get("line", 0)
        if anchor_line is None:
            # Open first cluster
            anchor_line = line
            current_cluster = [(pass_idx, f)]
        elif line - anchor_line <= TOL:  # type: ignore[operator]
            current_cluster.append((pass_idx, f))
        else:
            # Close current cluster, open new one
            clusters.append(current_cluster)
            anchor_line = line
            current_cluster = [(pass_idx, f)]

    if current_cluster:
        clusters.append(current_cluster)

    # Append sentinel cluster last (if any)
    if sentinel_members:
        clusters.append(sentinel_members)

    return clusters


def _annotate_representative(rep, cluster_members_with_pass):
    # type: (dict, List[Tuple[int, dict]]) -> dict
    """Compute corroboration signals and annotate the representative dict.

    Mutates and returns rep (which is already a copy from _pick_representative).

    Signals:
      agent_count = distinct agent values in cluster.
        >= 2 → append [CROSS-AGENT] to tags (severity NOT bumped; location-
        tolerant clustering is too permissive to justify a severity escalation).
      pass_count = distinct pass indices in cluster.
        Set rep["pass_count"] = pass_count (always).
        >= 2 → append [MULTI-PASS:{k}] to tags only; confidence is NOT raised
        (correlated re-generation across passes is not independent corroboration).

    Tags: union of all members' existing tags (stable order, deduped) plus
    new computed tags appended at the end.
    """
    findings_only = [f for _, f in cluster_members_with_pass]
    pass_indices = [p for p, _ in cluster_members_with_pass]

    # Build base tag union from all members
    base_tags = _union_tags(findings_only)

    # Compute signals
    distinct_agents = set(f.get("agent", "") for f in findings_only)
    agent_count = len(distinct_agents)

    distinct_passes = set(pass_indices)
    pass_count = len(distinct_passes)

    # Always record pass_count
    rep["pass_count"] = pass_count

    # Cross-agent corroboration: tag only, no severity bump.
    # Location-tolerant clustering (TOL=3) is too permissive to justify
    # a severity escalation; the [CROSS-AGENT] tag already conveys corroboration.
    new_tags = list(base_tags)  # start from union of members' tags
    if agent_count >= 2:
        if "[CROSS-AGENT]" not in new_tags:
            new_tags.append("[CROSS-AGENT]")

    # Multi-pass corroboration: tag only; confidence is NOT raised here.
    # Re-generating the same finding across passes reflects correlated error
    # from the same model reading the same code — not independent confirmation.
    if pass_count >= 2:
        mp_tag = "[MULTI-PASS:{k}]".format(k=pass_count)
        if mp_tag not in new_tags:
            new_tags.append(mp_tag)

    rep["tags"] = _dedup_tags(new_tags)
    return rep


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def merge_passes(pools):
    # type: (List[List[dict]]) -> List[dict]
    """Tolerant multi-pass union merge.

    Parameters
    ----------
    pools : list of lists
        pools[i] is the validated ParsedFinding dict list from pass i (0-based).
        Each finding dict has keys: agent, severity, file, line, pattern,
        confidence, evidence, why, remediation, category, tags.

    Returns
    -------
    list of dict
        One merged list of finding dicts.  Pure function: inputs are never
        mutated.  Output dicts carry an extra "pass_count" key (int).

    Algorithm
    ---------
    See module docstring.
    """
    if not pools:
        return []

    # --- Step 1: Flatten with pass index ---
    # Each element: (pass_idx, finding_dict)
    flat = []  # type: List[Tuple[int, dict]]
    for pass_idx, pool in enumerate(pools):
        for f in pool:
            flat.append((pass_idx, f))

    if not flat:
        return []

    # --- Step 2: Group by file, preserving first-appearance order ---
    # file_order tracks insertion order; groups maps file → list of (pass_idx, f)
    file_order = []   # type: List[str]
    groups = {}       # type: Dict[str, List[Tuple[int, dict]]]
    for pass_idx, f in flat:
        file_key = f.get("file", "")
        if file_key not in groups:
            groups[file_key] = []
            file_order.append(file_key)
        groups[file_key].append((pass_idx, f))

    # --- Steps 3-5: Cluster, collapse, annotate ---
    result = []  # type: List[dict]
    for file_key in file_order:
        members_with_pass = groups[file_key]
        clusters = _cluster_file_members(members_with_pass)
        for cluster in clusters:
            findings_only = [f for _, f in cluster]
            rep = _pick_representative(findings_only)
            rep = _annotate_representative(rep, cluster)
            result.append(rep)

    return result
