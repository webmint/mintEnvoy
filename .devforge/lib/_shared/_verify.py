"""_verify -- refutation/cross-examination stage for the /audit pipeline.

Implements the four pure helper functions that back the Step-1 refutation pass
(plan 19, Change A).  All four are stdlib-only, Python 3.8+, no I/O, no LLM.

Functions
---------
route_refutation(findings, present_finders)
    Deterministic cross-examination router.  Groups the working findings by
    author (each finding dict's ``agent`` field) and assigns each group a
    non-author refuter chosen from the fixed priority order
    [code-reviewer, architect, qa-reviewer, security-reviewer].  The refuter
    is the FIRST present finder in that order that is NOT the finding's author.
    Sole-finder edge case: when the finding's author is the ONLY present finder,
    the author self-refutes (the single named exception in the spec).
    Returns a routing map: list of {refuter, findings} dicts (pure, no LLM).

render_verify_brief(refuter, findings, references_dir, scope_block,
                    source_root, tmp_path=None)
    Assemble the refuter's prompt.  Mirrors render_agent_brief from _scope.py:
    reads refutation-preamble.md from references_dir, renders the assigned
    findings subset into a readable cross-examination block, and instructs
    the refuter to write its verdicts to tmp_path.

consume_verdicts(text)
    Parse ONE refuter's markdown verdict file (the refutation-preamble.md
    format) into a result dict.  Mirrors parse_agent_tmp from _consume.py:
    returns {status, reason, refuter, verdict_count, verdicts} where each
    verdict dict carries refuter, file, line, pattern, agent, verdict,
    justification, evidence.

apply_verdicts(findings, verdicts)
    Partition the full working findings list by the merged verdicts (across
    all refuters).  Keys each verdict to its finding by (file, line, pattern,
    agent).  Returns:
      confirmed    — confirmed by a refuter; given an extra "verify_confidence"
                     signal ("confirmed").  NOT tagged [CONTESTED].
      dismissed    — dismissed by a refuter (and NOT a [CONSTITUTION-VIOLATION]
                     finding, per the D7 constitution carve-out).
      uncertain    — low-stakes uncertain (category NOT in high-stakes set and
                     NOT tagged [CONSTITUTION-VIOLATION]).
      contested    — high-stakes uncertain (category == "security" OR tagged
                     [CONSTITUTION-VIOLATION]) + dismissed [CONSTITUTION-
                     VIOLATION] findings (the D7 constitution carve-out).
                     ALL contested findings carry a "[CONTESTED]" tag appended
                     to their tags list (a copy of the dict is returned — the
                     input dict is never mutated).
    No-verdict-match default: treated as uncertain and routed by category
    (high-stakes → contested; all others → uncertain).  This is the
    precision-safe default (do not silently confirm un-refuted findings).

Bucket key names (for Step 4 report consumer):
    "confirmed", "dismissed", "uncertain", "contested"

Contested findings carry the "[CONTESTED]" tag:
  Every finding in the ``contested`` bucket gets "[CONTESTED]" appended to
  its ``tags`` list (appended once; idempotent — not added if already present).
  The input dict is never mutated; a shallow copy is returned.

No-verdict-match default: uncertain routing by category.
  - high-stakes category ("security") or [CONSTITUTION-VIOLATION] tag → contested
  - all other categories → uncertain
  Rationale: a finding that no refuter judged is not confirmed — treat as
  unresolved rather than silently accepting it; the precision-safe default.

Stdlib only.  Python 3.8+.  No I/O, no LLM in the pure functions.
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Fixed priority order for refuter selection (spec D2).
_REFUTER_PRIORITY = [
    "code-reviewer",
    "architect",
    "qa-reviewer",
    "security-reviewer",
]

# High-stakes categories for D7 routing.
_HIGH_STAKES_CATEGORIES = frozenset(["security"])

# Constitution-violation tag (exact marker as used throughout the pipeline).
_CONSTITUTION_TAG = "[CONSTITUTION-VIOLATION]"

# Verdict vocabulary (lowercase, as specified in the preamble contract).
_VALID_VERDICTS = frozenset(["confirmed", "dismissed", "uncertain"])

# Verdict merge precedence: higher value = more favourable to surfacing.
# confirmed > uncertain > dismissed.
_VERDICT_PRECEDENCE = {"confirmed": 2, "uncertain": 1, "dismissed": 0}

# Tag added to every contested finding by apply_verdicts.
_CONTESTED_TAG = "[CONTESTED]"

# ---------------------------------------------------------------------------
# Status constants (mirror _consume.py)
# ---------------------------------------------------------------------------

VERDICT_STATUS_MISSING = "missing"
VERDICT_STATUS_FAILED = "failed"
VERDICT_STATUS_CLEAN = "clean"        # complete + verdict_count 0
VERDICT_STATUS_COMPLETE = "complete"  # complete + verdict_count > 0

# ---------------------------------------------------------------------------
# Regex patterns for consume_verdicts (mirror _consume.py _RE_* style)
# ---------------------------------------------------------------------------

_RE_REFUTER = re.compile(r'^#\s*Refuter:\s*(.+)$', re.MULTILINE)
_RE_STATUS = re.compile(r'^#\s*Status:\s*(.+)$', re.MULTILINE)
_RE_REASON = re.compile(r'^#\s*Reason:\s*(.+)$', re.MULTILINE)
_RE_VERDICT_COUNT = re.compile(r'^#\s*Verdict\s+count:\s*(\d+)$', re.MULTILINE)

# A verdict block starts at "## Verdict N"
_RE_VERDICT_HEADER = re.compile(r'^##\s+Verdict\s+\d+', re.MULTILINE)

# Fields within a verdict block (share some names with findings: File, Line, Pattern)
_RE_FILE = re.compile(r'^File:\s*(.+)$', re.MULTILINE)
_RE_LINE = re.compile(r'^Line:\s*(\d+)$', re.MULTILINE)
_RE_PATTERN = re.compile(r'^Pattern:\s*(.+)$', re.MULTILINE)
_RE_AGENT = re.compile(r'^Agent:\s*(.+)$', re.MULTILINE)
_RE_VERDICT = re.compile(r'^Verdict:\s*(.+)$', re.MULTILINE)
_RE_JUSTIFICATION = re.compile(r'^Justification:\s*(.+)$', re.MULTILINE)

# Evidence block: "Evidence:" followed by a fenced code block.
_RE_EVIDENCE_BLOCK = re.compile(
    r'Evidence:\s*\n```+[^\n]*\n(.*?)```+',
    re.DOTALL,
)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _is_high_stakes(finding):
    # type: (dict) -> bool
    """Return True when a finding is high-stakes per D7.

    High-stakes = category == "security" OR the finding carries the
    [CONSTITUTION-VIOLATION] tag in its tags list.
    """
    if finding.get("category") in _HIGH_STAKES_CATEGORIES:
        return True
    tags = finding.get("tags") or []
    return _CONSTITUTION_TAG in tags


def _has_constitution_tag(finding):
    # type: (dict) -> bool
    """Return True when the finding carries the [CONSTITUTION-VIOLATION] tag."""
    tags = finding.get("tags") or []
    return _CONSTITUTION_TAG in tags


def _parse_verdict_block(block_text, refuter_name):
    # type: (str, str) -> Optional[dict]
    """Parse a single ## Verdict N block into a verdict dict.

    Returns None if required fields are missing (file, line, pattern, agent,
    verdict).  Justification and evidence are tolerated as empty strings.
    """
    # File
    m = _RE_FILE.search(block_text)
    if not m:
        return None
    file_path = m.group(1).strip()

    # Line
    m = _RE_LINE.search(block_text)
    if not m:
        return None
    try:
        line_no = int(m.group(1).strip())
    except ValueError:
        return None

    # Pattern
    m = _RE_PATTERN.search(block_text)
    if not m:
        return None
    pattern = m.group(1).strip()

    # Agent (the authoring agent, copied verbatim from the finding)
    m = _RE_AGENT.search(block_text)
    if not m:
        return None
    agent = m.group(1).strip()

    # Verdict
    m = _RE_VERDICT.search(block_text)
    if not m:
        return None
    verdict_raw = m.group(1).strip().lower()
    if verdict_raw not in _VALID_VERDICTS:
        return None

    # Justification (optional — tolerate absence)
    justification = ""
    m = _RE_JUSTIFICATION.search(block_text)
    if m:
        justification = m.group(1).strip()

    # Evidence block — same regex as _consume.py; line-by-line fallback if needed
    evidence = ""
    m_ev = _RE_EVIDENCE_BLOCK.search(block_text)
    if m_ev:
        evidence = m_ev.group(1).strip()
    else:
        lines = block_text.splitlines()
        in_evidence_header = False
        in_fence = False
        ev_lines = []  # type: List[str]
        for ln in lines:
            stripped = ln.strip()
            if not in_fence and not in_evidence_header:
                if stripped.startswith('Evidence:'):
                    in_evidence_header = True
                continue
            if in_evidence_header and not in_fence:
                if stripped.startswith('```'):
                    in_fence = True
                continue
            if in_fence:
                if stripped.startswith('```'):
                    break
                ev_lines.append(ln)
        evidence = '\n'.join(ev_lines).strip()

    return {
        "refuter": refuter_name,
        "file": file_path,
        "line": line_no,
        "pattern": pattern,
        "agent": agent,
        "verdict": verdict_raw,
        "justification": justification,
        "evidence": evidence,
    }


def _verdict_key(verdict_or_finding):
    # type: (dict) -> tuple
    """Return the (file, line, pattern, agent) key for routing verdict→finding."""
    return (
        verdict_or_finding.get("file", ""),
        verdict_or_finding.get("line", -1),
        verdict_or_finding.get("pattern", ""),
        verdict_or_finding.get("agent", ""),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def route_refutation(findings, present_finders, priority=None):
    # type: (List[dict], List[str], Optional[List[str]]) -> List[dict]
    """Deterministic cross-examination router.

    Groups the working findings by author (the ``agent`` field of each finding)
    and assigns each group the FIRST present finder in the priority order
    that is NOT the finding's author.

    Sole-finder edge case: when no priority-list finder other than the finding's
    author is present in ``present_finders``, the author self-refutes (refuter ==
    author).  In the standard four-finder setup (all four priority-list members
    present) this simplifies to ``len(present_finders) == 1``, but it can also
    fire at ``len > 1`` if the only extra present finder is a non-priority agent
    (e.g. ``present_finders=["code-reviewer", "backend-engineer"]`` with author
    ``code-reviewer`` → self-refute, because ``backend-engineer`` is not in the
    priority list).  A finding whose ``agent`` is NOT in present_finders still
    gets a valid non-author refuter (the first present priority finder).

    Parameters
    ----------
    findings        : list of ParsedFinding dicts (the working list after
                      consensus/merge).
    present_finders : list of agent names that ran successfully (from the
                      Phase-1.2 agent-existence check).
    priority        : optional explicit priority list for refuter selection.
                      When None (the default), uses the module constant
                      ``_REFUTER_PRIORITY`` = [code-reviewer, architect,
                      qa-reviewer, security-reviewer].  Pass an explicit list
                      to override the default (e.g. for a different reviewer
                      roster in a future command).  The override must be a
                      list of agent-name strings; it is used as-is and not
                      validated against any roster.

    Returns
    -------
    A list of {refuter: <agent>, findings: [<finding dicts>]} groups.
    Groups are ordered by their first-appearance finding index in ``findings``.
    Empty findings input returns [].
    """
    if not findings:
        return []

    effective_priority = _REFUTER_PRIORITY if priority is None else priority
    present_set = set(present_finders)

    # Assign refuter for each finding independently, then group by refuter.
    # Groups ordered by first assignment to each refuter.
    refuter_order = []  # type: List[str]
    refuter_groups = {}  # type: Dict[str, List[dict]]

    for finding in findings:
        author = finding.get("agent", "")

        # Select refuter: first in priority that is present AND != author.
        chosen = None
        for candidate in effective_priority:
            if candidate in present_set and candidate != author:
                chosen = candidate
                break

        if chosen is None:
            # Sole-finder edge case: no valid non-author refuter exists.
            # Self-refute: the sole present finder judges its own finding.
            # This fires only when len(present_set) == 1 (or 0, degenerate).
            # Fall back to the first present finder in priority order,
            # then to author itself if no present finder matches priority.
            for candidate in effective_priority:
                if candidate in present_set:
                    chosen = candidate
                    break
            if chosen is None:
                # No present finder in the priority list; use author as fallback.
                chosen = author if author else "unknown"

        if chosen not in refuter_groups:
            refuter_order.append(chosen)
            refuter_groups[chosen] = []
        refuter_groups[chosen].append(finding)

    return [
        {"refuter": r, "findings": refuter_groups[r]}
        for r in refuter_order
    ]


def render_verify_brief(refuter, findings, references_dir, scope_block, source_root, tmp_path=None):
    # type: (str, List[dict], str, str, str, Optional[str]) -> str
    """Assemble the refuter's prompt for cross-examination.

    Mirrors render_agent_brief from _scope.py.  Assembly order (4 steps):
      1. Refutation Preamble + Output Contract  (refutation-preamble.md)
      2. Scope context block
      3. Findings to cross-examine (rendered from the assigned findings subset)
      4. Closing instruction (write verdicts to tmp_path)

    Parameters
    ----------
    refuter         : Agent name that will perform the cross-examination.
    findings        : List of ParsedFinding dicts assigned to this refuter.
    references_dir  : Directory containing refutation-preamble.md.
    scope_block     : Pre-rendered scope summary string (from render_scope_block).
    source_root     : Workspace / repo root label.
    tmp_path        : Path where the refuter should write its verdict file
                      (e.g. ``$WORKDIR/verdicts-<refuter>.md``).  When None,
                      defaults to ``$WORKDIR/verdicts-<refuter>.md`` with the
                      refuter name substituted.

    Returns
    -------
    Multi-line string forming the refuter instruction block.

    Raises
    ------
    ValueError : if refutation-preamble.md is missing or unreadable.
    """
    preamble_path = os.path.join(references_dir, "refutation-preamble.md")
    try:
        with open(preamble_path, "r", encoding="utf-8") as fh:
            preamble = fh.read()
    except OSError as exc:
        raise ValueError(
            "cannot read refutation-preamble.md from {0!r}: {1}".format(
                references_dir, exc
            )
        )

    # Build the findings cross-examination block.
    findings_lines = []  # type: List[str]
    findings_lines.append("=== FINDINGS TO CROSS-EXAMINE ===")
    findings_lines.append("")
    if not findings:
        findings_lines.append("(no findings assigned to this refuter)")
    else:
        for idx, f in enumerate(findings, 1):
            findings_lines.append("## Finding {0}".format(idx))
            findings_lines.append("File: {0}".format(f.get("file", "")))
            findings_lines.append("Line: {0}".format(f.get("line", "")))
            findings_lines.append("Pattern: {0}".format(f.get("pattern", "")))
            findings_lines.append("Agent: {0}".format(f.get("agent", "")))
            findings_lines.append("Severity: {0}".format(f.get("severity", "")))
            findings_lines.append("Category: {0}".format(f.get("category", "")))
            findings_lines.append("Evidence:")
            findings_lines.append("```")
            findings_lines.append(f.get("evidence", ""))
            findings_lines.append("```")
            why = f.get("why", "")
            if why:
                findings_lines.append("Why it's wrong: {0}".format(why))
            findings_lines.append("")

    findings_block = "\n".join(findings_lines)

    # Scope section
    scope_section = scope_block

    # Determine the verdict file path.
    if tmp_path is None:
        tmp_path = "$WORKDIR/verdicts-{0}.md".format(refuter)

    closing = (
        "Write your verdicts to: {0}\n"
        "Use the fixed format specified above (# Refuter: / # Status: / "
        "# Verdict count: / ## Verdict N blocks).  One verdict per finding, "
        "in the order the findings are listed above."
    ).format(tmp_path)

    parts = [
        preamble,
        scope_section,
        findings_block,
        closing,
    ]

    return "\n\n".join(parts)


def consume_verdicts(text):
    # type: (str) -> dict
    """Parse ONE refuter's markdown verdict file into a result dict.

    Mirrors parse_agent_tmp from _consume.py.

    Parameters
    ----------
    text : Full text content of the verdict file (already read by caller).

    Returns
    -------
    Dict with keys:
      status        : one of VERDICT_STATUS_* constants
      reason        : failure reason string (only when status == "failed")
      refuter       : refuter name from header (or "unknown" if header absent)
      verdict_count : always len(verdicts) -- actual parsed count wins over
                      declared header count
      verdicts      : list of verdict dicts, each carrying:
                        refuter, file, line, pattern, agent, verdict,
                        justification, evidence

    The "missing" status is NOT returned by this function; the caller detects
    a missing file before calling consume_verdicts.
    """
    text = text or ""

    # Refuter header
    m = _RE_REFUTER.search(text)
    refuter = m.group(1).strip() if m else "unknown"

    # Status header
    m_status = _RE_STATUS.search(text)
    raw_status = m_status.group(1).strip().lower() if m_status else ""

    # Reason (for failed status)
    m_reason = _RE_REASON.search(text)
    reason = m_reason.group(1).strip() if m_reason else ""

    # Verdict count header
    m_count = _RE_VERDICT_COUNT.search(text)
    declared_count = int(m_count.group(1)) if m_count else None

    # Failed status: return immediately
    if raw_status == "failed":
        return {
            "status": VERDICT_STATUS_FAILED,
            "reason": reason or "refuter reported failure",
            "refuter": refuter,
            "verdict_count": 0,
            "verdicts": [],
        }

    # Find all verdict block start positions
    block_starts = [m.start() for m in _RE_VERDICT_HEADER.finditer(text)]

    verdicts = []
    for i, start in enumerate(block_starts):
        end = block_starts[i + 1] if i + 1 < len(block_starts) else len(text)
        block = text[start:end]
        parsed = _parse_verdict_block(block, refuter)
        if parsed is not None:
            verdicts.append(parsed)

    # If declared count is 0 and no blocks found → clean
    if declared_count == 0 and not verdicts:
        return {
            "status": VERDICT_STATUS_CLEAN,
            "reason": "",
            "refuter": refuter,
            "verdict_count": 0,
            "verdicts": [],
        }

    count = len(verdicts)

    return {
        "status": VERDICT_STATUS_COMPLETE,
        "reason": "",
        "refuter": refuter,
        "verdict_count": count,
        "verdicts": verdicts,
    }


def _tag_contested(finding):
    # type: (dict) -> dict
    """Return a copy of *finding* with "[CONTESTED]" added to its tags list.

    Idempotent — does not add the tag twice.  Never mutates the input dict.
    """
    existing_tags = list(finding.get("tags") or [])
    if _CONTESTED_TAG not in existing_tags:
        existing_tags.append(_CONTESTED_TAG)
    enriched = dict(finding)
    enriched["tags"] = existing_tags
    return enriched


def apply_verdicts(findings, verdicts):
    # type: (List[dict], List[dict]) -> dict
    """Partition working findings by verdict + category per D7.

    Keys each verdict to its finding by the (file, line, pattern, agent) tuple
    (the same key Phase 4.5 uses).  Multiple verdicts matching the same finding
    key are merged: 'confirmed' beats 'uncertain' beats 'dismissed' (most
    favourable to surfacing).

    D7 partition rules:
      confirmed  → confirmed bucket; gets verify_confidence="confirmed".
                   NOT tagged [CONTESTED].
      dismissed  → dismissed bucket -- UNLESS the finding carries the
                   [CONSTITUTION-VIOLATION] tag → contested (the D7 carve-out).
      uncertain  → high-stakes (category == "security" OR [CONSTITUTION-VIOLATION]
                   tag) → contested; all other categories → uncertain bucket.
      no-match   → treated as uncertain and routed by category
                   (high-stakes → contested; others → uncertain).

    ALL findings routed to the contested bucket receive a "[CONTESTED]" tag
    appended to their tags list (via _tag_contested, which copies the dict and
    appends idempotently — input dicts are never mutated).

    Does NOT re-derive a verdict or enforce the evidence rule.  Partitions by
    declared verdict + category only.

    Parameters
    ----------
    findings : list of ParsedFinding dicts (the full working list from
               consensus/merge, i.e. consensus-findings.json or merged.json).
    verdicts : list of verdict dicts (merged across all refuters, from
               consume_verdicts calls).

    Returns
    -------
    Dict with keys: confirmed, dismissed, uncertain, contested.
    Each value is a list of finding dicts (not verdict dicts).
    Findings in the confirmed bucket carry an extra "verify_confidence" key.
    Findings in the contested bucket carry "[CONTESTED]" in their tags list.
    """
    # Build verdict index: (file, line, pattern, agent) → best verdict string.
    # "Best" = most favourable to surfacing: confirmed > uncertain > dismissed.
    verdict_index = {}  # type: Dict[tuple, str]
    for v in verdicts:
        key = _verdict_key(v)
        v_val = v.get("verdict", "")
        if v_val not in _VALID_VERDICTS:
            continue
        existing = verdict_index.get(key)
        if existing is None:
            verdict_index[key] = v_val
        else:
            # Keep the verdict with higher precedence (more favourable to surfacing).
            if _VERDICT_PRECEDENCE.get(v_val, -1) > _VERDICT_PRECEDENCE.get(existing, -1):
                verdict_index[key] = v_val

    confirmed = []   # type: List[dict]
    dismissed = []   # type: List[dict]
    uncertain = []   # type: List[dict]
    contested = []   # type: List[dict]

    for finding in findings:
        key = _verdict_key(finding)
        verdict = verdict_index.get(key)  # may be None if no verdict matched

        if verdict is None:
            # No-verdict-match default: treat as uncertain, route by category.
            # Precision-safe: do not silently confirm un-refuted findings.
            if _is_high_stakes(finding):
                contested.append(_tag_contested(finding))
            else:
                uncertain.append(finding)
            continue

        if verdict == "confirmed":
            enriched = dict(finding)
            enriched["verify_confidence"] = "confirmed"
            confirmed.append(enriched)

        elif verdict == "dismissed":
            if _has_constitution_tag(finding):
                # D7 constitution carve-out: a dismissed [CONSTITUTION-VIOLATION]
                # finding surfaces as contested rather than dropping to dismissed.
                contested.append(_tag_contested(finding))
            else:
                dismissed.append(finding)

        elif verdict == "uncertain":
            if _is_high_stakes(finding):
                # High-stakes uncertain → headline contested (D7).
                contested.append(_tag_contested(finding))
            else:
                # Low-stakes uncertain → appendix.
                uncertain.append(finding)

    return {
        "confirmed": confirmed,
        "dismissed": dismissed,
        "uncertain": uncertain,
        "contested": contested,
    }
