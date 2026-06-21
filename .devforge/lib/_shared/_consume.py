"""_consume -- parse agent tmp files into ParsedFinding records.

Reads a single ``audits/.tmp-{agent}.md`` file written by an audit agent
following the Output Contract in §3.2 of the /audit command spec.

Design note — ParsedFinding vs Finding
---------------------------------------
The schema ``Finding`` dataclass (findings_schema.py) is the FINAL output
shape for report boundaries.  During the consolidation pipeline
(consume → validate → consensus → recurring → rank), the processing
layers need fields that Finding does not carry:
  - pattern   (§3.2 Pattern: field; used as consensus hash input)
  - confidence (§3.2 Confidence: field; used in force-rank score)
  - evidence   (§3.2 fenced Evidence block; used in anti-hallucination validation)
  - why        (§3.2 "Why it's wrong:" narrative; maps to Finding.explanation)
  - remediation (§3.2 Remediation:; maps to Finding.suggested_fix)
  - tags       (mutable list: [CROSS-AGENT], [RECURRING], [RECURRING-SPREAD])
  - agent      (producing agent name)

Rather than mutate Finding (frozen dataclass) or stuff extras into
references[], we define ParsedFinding here and convert to Finding at the
report boundary (Phase 4 report, not built in this module).

The conversion is 1:1 for most fields:
  title        ← pattern (falls back to first line of why if pattern empty)
  explanation  ← why
  suggested_fix ← remediation
  finding_id   ← assigned by report layer ("F-001", "F-002", …)
  source_pass  ← agent name  (set by report layer from agent field)

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from _shared.findings_schema import CATEGORY_ENUM  # type: ignore[import]

# ---------------------------------------------------------------------------
# ParsedFinding dataclass
# ---------------------------------------------------------------------------

CONFIDENCE_VALUES = ("Certain", "Likely", "Speculative")


@dataclass
class ParsedFinding:
    """Internal finding record produced by parse_agent_tmp().

    All string fields are stripped.  tags is an empty list by default and
    is mutated in-place by consensus/recurring stages.
    """

    agent: str
    severity: str               # one of SEVERITY_ENUM values
    file: str                   # relative path as written by the agent
    line: int                   # 1-based line number
    pattern: str                # §3.2 Pattern field
    confidence: str             # Certain | Likely | Speculative
    evidence: str               # verbatim quoted block (fenced code stripped)
    why: str                    # "Why it's wrong:" paragraph
    remediation: str            # Remediation paragraph
    category: str = "mislogic"  # one of CATEGORY_ENUM values; defaults to mislogic
    tags: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Status constants
# ---------------------------------------------------------------------------

STATUS_MISSING = "missing"
STATUS_FAILED = "failed"
STATUS_CLEAN = "clean"          # complete + count 0
STATUS_COMPLETE = "complete"    # complete + count > 0

# ---------------------------------------------------------------------------
# Internal regex patterns
# ---------------------------------------------------------------------------

_RE_AGENT = re.compile(r'^#\s*Agent:\s*(.+)$', re.MULTILINE)
_RE_STATUS = re.compile(r'^#\s*Status:\s*(.+)$', re.MULTILINE)
_RE_REASON = re.compile(r'^#\s*Reason:\s*(.+)$', re.MULTILINE)
_RE_COUNT = re.compile(r'^#\s*Finding\s+count:\s*(\d+)$', re.MULTILINE)

# A finding block starts at "## Finding N"
_RE_FINDING_HEADER = re.compile(r'^##\s+Finding\s+\d+', re.MULTILINE)

# Top-5 priorities trailer starts here; everything from this point is ignored
_RE_TOP5_HEADER = re.compile(r'^##\s+Top\s+\d+\s+Priorities', re.MULTILINE)

# Fields within a finding block
_RE_SEVERITY = re.compile(r'^Severity:\s*(.+)$', re.MULTILINE)
_RE_FILE = re.compile(r'^File:\s*(.+)$', re.MULTILINE)
_RE_LINE = re.compile(r'^Line:\s*(\d+)$', re.MULTILINE)
_RE_PATTERN = re.compile(r'^Pattern:\s*(.+)$', re.MULTILINE)
_RE_CONFIDENCE = re.compile(r'^Confidence:\s*(.+)$', re.MULTILINE)
_RE_CATEGORY = re.compile(r'^Category:\s*(.+)$', re.MULTILINE)

# Evidence block: "Evidence:" followed by a fenced code block.
# The fence uses ``` (three or more backticks).  We capture the content
# between the opening and closing fence.
_RE_EVIDENCE_BLOCK = re.compile(
    r'Evidence:\s*\n```+[^\n]*\n(.*?)```+',
    re.DOTALL,
)

# "Why it's wrong:" — capture to next known heading or end-of-block.
# We'll extract this with a line-by-line pass below.

# "Remediation:" — similar.


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _extract_section(text, section_label):
    # type: (str, str) -> str
    """Extract text following a 'Label:' line up to the next field heading.

    Known field headings: Severity, File, Line, Pattern, Confidence,
    Evidence, Why it's wrong, Remediation, and ## headings.

    Returns the extracted text stripped of leading/trailing whitespace, or
    empty string if the section_label is not found.
    """
    _KNOWN_HEADINGS = (
        'Severity:', 'File:', 'Line:', 'Pattern:', 'Confidence:', 'Category:',
        'Evidence:', "Why it's wrong:", 'Remediation:', '##',
    )
    lines = text.splitlines()
    started = False
    collected = []
    for line in lines:
        if not started:
            if line.startswith(section_label):
                # Inline content on the same line (after the label+colon)
                rest = line[len(section_label):].strip()
                if rest:
                    collected.append(rest)
                started = True
            continue
        # Stop at the next known heading
        stripped = line.strip()
        if any(stripped.startswith(h) for h in _KNOWN_HEADINGS):
            break
        collected.append(line)
    return '\n'.join(collected).strip()


def _parse_finding_block(block_text, agent_name):
    # type: (str, str) -> Optional[ParsedFinding]
    """Parse a single ## Finding N block into a ParsedFinding.

    Returns None if the block is missing one or more required fields
    (severity, file, line, pattern, confidence, evidence).  Missing why/
    remediation are tolerated with empty strings (they fail the later
    anti-hallucination checks only if evidence is also absent).
    """
    # Severity
    m = _RE_SEVERITY.search(block_text)
    if not m:
        return None
    severity = m.group(1).strip()

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

    # Confidence
    m = _RE_CONFIDENCE.search(block_text)
    if not m:
        return None
    confidence = m.group(1).strip()

    # Category — optional; default to "mislogic" on missing or invalid value.
    category = "mislogic"
    m_cat = _RE_CATEGORY.search(block_text)
    if m_cat:
        raw_cat = m_cat.group(1).strip()
        if raw_cat in CATEGORY_ENUM:
            category = raw_cat

    # Evidence block — fenced code.  Try the regex first; if the block uses
    # nested fences (``` inside ```) we fall back to a line-by-line approach.
    evidence = ""
    m_ev = _RE_EVIDENCE_BLOCK.search(block_text)
    if m_ev:
        evidence = m_ev.group(1).strip()
    else:
        # Line-by-line fallback: find "Evidence:" then collect lines between
        # opening ``` and closing ```.
        lines = block_text.splitlines()
        in_evidence_header = False
        in_fence = False
        ev_lines = []
        for ln in lines:
            stripped = ln.strip()
            if not in_fence and not in_evidence_header:
                if stripped == 'Evidence:' or stripped.startswith('Evidence:'):
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

    # Why it's wrong
    why = _extract_section(block_text, "Why it's wrong:")

    # Remediation
    remediation = _extract_section(block_text, "Remediation:")

    # Lift the [CONSTITUTION-VIOLATION] marker into the structured tags list.
    # Agents have no structured Tags field in the output contract (§3.2), so
    # they embed the bracketed marker in the Pattern one-liner or Why text.
    # We detect the exact token here — case-sensitive, brackets required — so
    # that prose like "this is not a constitution violation" (no brackets)
    # does NOT match.  Evidence is intentionally excluded from the scan: it
    # contains verbatim source code, where the literal token would be
    # coincidental rather than a deliberate marker.
    _CONSTITUTION_MARKER = "[CONSTITUTION-VIOLATION]"
    tags = []
    if _CONSTITUTION_MARKER in pattern or _CONSTITUTION_MARKER in why:
        tags = [_CONSTITUTION_MARKER]

    return ParsedFinding(
        agent=agent_name,
        severity=severity,
        file=file_path,
        line=line_no,
        pattern=pattern,
        confidence=confidence,
        evidence=evidence,
        why=why,
        remediation=remediation,
        category=category,
        tags=tags,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_agent_tmp(text, agent_name="unknown"):
    # type: (str, str) -> dict
    """Parse the content of an agent tmp file into a status dict.

    Parameters
    ----------
    text:       Full text content of the tmp file (already read by caller).
    agent_name: The agent name hint (used when header is missing).

    Returns a dict with keys:
      status        : one of STATUS_* constants ("complete", "clean", "failed")
      reason        : failure reason string (only when status == "failed")
      agent         : agent name from header (falls back to agent_name param)
      finding_count : always len(findings) — actual parsed count wins over the
                      declared header count to prevent self-contradictory dicts
                      (e.g. header says 0 but real blocks were parsed)
      findings      : list of ParsedFinding dicts (dataclasses.asdict format)

    The "missing" status is NOT returned by this function; it is the caller's
    responsibility to detect a missing file before calling parse_agent_tmp.
    """
    import dataclasses

    text = text or ""

    # Agent header
    m = _RE_AGENT.search(text)
    agent = m.group(1).strip() if m else agent_name

    # Status header
    m_status = _RE_STATUS.search(text)
    raw_status = m_status.group(1).strip().lower() if m_status else ""

    # Reason (for failed status)
    m_reason = _RE_REASON.search(text)
    reason = m_reason.group(1).strip() if m_reason else ""

    # Finding count header
    m_count = _RE_COUNT.search(text)
    declared_count = int(m_count.group(1)) if m_count else None

    # If status is failed, return immediately
    if raw_status == "failed":
        return {
            "status": STATUS_FAILED,
            "reason": reason or "agent reported failure",
            "agent": agent,
            "finding_count": 0,
            "findings": [],
        }

    # Truncate at Top-5 Priorities trailer before parsing findings
    text_for_findings = text
    m_top5 = _RE_TOP5_HEADER.search(text)
    if m_top5:
        text_for_findings = text[:m_top5.start()]

    # Find all finding block start positions
    block_starts = [m.start() for m in _RE_FINDING_HEADER.finditer(text_for_findings)]

    findings = []
    for i, start in enumerate(block_starts):
        end = block_starts[i + 1] if i + 1 < len(block_starts) else len(text_for_findings)
        block = text_for_findings[start:end]
        parsed = _parse_finding_block(block, agent)
        if parsed is not None:
            findings.append(dataclasses.asdict(parsed))

    # If declared count is 0 (regardless of whether blocks were found), it's clean
    if declared_count == 0 and not findings:
        return {
            "status": STATUS_CLEAN,
            "reason": "",
            "agent": agent,
            "finding_count": 0,
            "findings": [],
        }

    # finding_count always reflects actual parsed count (actual wins over
    # declared when they differ — a header saying 0 but real blocks present
    # would produce a self-contradictory dict; len(findings) is the truth).
    count = len(findings)

    return {
        "status": STATUS_COMPLETE,
        "reason": "",
        "agent": agent,
        "finding_count": count,
        "findings": findings,
    }
