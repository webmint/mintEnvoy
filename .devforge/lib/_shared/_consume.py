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
# Label-tolerance normalisation helpers (plan 46)
# ---------------------------------------------------------------------------

# Single-line field labels whose values should have surrounding backticks
# stripped (Severity, File, Line, Pattern, Confidence, Category).  NOT applied
# to Evidence / Why it's wrong / Remediation — those may contain legitimate
# backticks in prose or fenced code.
_SINGLE_LINE_LABEL_FIELDS = frozenset([
    'Severity', 'File', 'Line', 'Pattern', 'Confidence', 'Category',
])

# All known label names sorted longest-first so the alternation regex prefers
# the longest match and avoids ambiguous prefix matches.
_ALL_KNOWN_LABELS = sorted(
    [
        "Why it's wrong", 'Remediation', 'Evidence',
        'Severity', 'File', 'Line', 'Pattern', 'Confidence', 'Category',
    ],
    key=len,
    reverse=True,
)

# Matches a decorated known-label line OUTSIDE a fenced code block.
# Decoration tolerated:
#   - optional leading indent (spaces/tabs)
#   - ONE optional list bullet (-/*/+) followed by whitespace
#   - optional bold (**) around the label and/or the colon
# Groups: (1) the matched label, (2) the value after the colon (possibly "").
# A literal ':' is required immediately after the (optionally-bolded) label,
# so prose like "Severity is high" (no colon) does NOT match.
# The "## Finding N" header (starts with '#') also cannot match.
_RE_DECORATED_LABEL_LINE = re.compile(
    r'^'
    r'[ \t]*'                                                              # optional indent
    r'(?:[-*+][ \t]+)?'                                                    # optional bullet
    r'(?:\*\*)?'                                                           # optional opening **
    r'(' + '|'.join(re.escape(lbl) for lbl in _ALL_KNOWN_LABELS) + r')'   # label (captured)
    r'(?:\*\*)?'                                                           # optional closing ** (**Label**:)
    r':'                                                                   # required colon
    r'(?:\*\*)?'                                                           # optional closing ** (**Label:**)
    r'[ \t]*(.*)'                                                          # optional whitespace + value
    r'$'
)


def _strip_inline_code(value):
    # type: (str) -> str
    """Strip a matched surrounding backtick run from a single-line value.

    Examples::

        _strip_inline_code('`x`')    -> 'x'
        _strip_inline_code('``x``')  -> 'x'
        _strip_inline_code('x')      -> 'x'   (no backticks — unchanged)
        _strip_inline_code('`a`b`')  -> 'a`b' (interior backtick preserved)

    Only the outermost matched pair (equal run length at start and end) is
    stripped.  A value that does not end with a backtick is returned unchanged.
    """
    m = re.match(r'^(`+)(.*?)(`+)$', value)
    if m and m.group(1) == m.group(3):
        return m.group(2)
    return value


def _normalize_label_lines(block_text):
    # type: (str) -> str
    """Fence-aware pass: rewrite decorated label lines to bare 'Label: value' form.

    Walk the block line-by-line.  Toggle *in_fence* whenever a line's lstripped
    form starts with '```'.  Lines inside a fence pass through verbatim — so
    evidence code bodies that begin with '-'/'*' or contain '**' are never
    rewritten.  Outside-fence lines that match a decorated known-label pattern
    (leading indent / list bullet / bold **) are rewritten to the canonical bare
    form ``Label: value``.

    For the six single-line fields (Severity, File, Line, Pattern, Confidence,
    Category) the extracted value is also passed through ``_strip_inline_code``
    so that backtick-wrapped values like ``Line: `12``` become ``Line: 12``
    before the existing field regexes run.  The value for Evidence / Why it's
    wrong / Remediation is emitted as-is (those fields carry prose or fenced
    code that may contain legitimate backticks).

    Called once at the top of ``_parse_finding_block`` before any existing
    regex or startswith parsing runs — so all downstream logic is unchanged.
    """
    lines = block_text.splitlines()
    result = []
    in_fence = False
    for line in lines:
        if line.lstrip().startswith('```'):
            in_fence = not in_fence
            result.append(line)
            continue
        if in_fence:
            result.append(line)
            continue
        m = _RE_DECORATED_LABEL_LINE.match(line)
        if m:
            label = m.group(1)
            value = m.group(2)
            if label in _SINGLE_LINE_LABEL_FIELDS:
                value = _strip_inline_code(value)
            if value:
                result.append('{0}: {1}'.format(label, value))
            else:
                result.append('{0}:'.format(label))
        else:
            result.append(line)
    return '\n'.join(result)


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
    # Normalise label decoration (dash-bullets, bold **, backtick-wrapped
    # values) before any existing regex or startswith parsing runs.
    block_text = _normalize_label_lines(block_text)

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

    # Scope Why/Remediation extraction to the post-evidence tail when the
    # evidence regex matched.  A stray ``` inside an evidence code body toggles
    # _normalize_label_lines back to "outside fence", so a decorated label like
    # **Why it's wrong**: INSIDE CODE BODY would be normalised and then picked
    # up by _extract_section before the real post-evidence field.  Restricting
    # the search region to block_text[m_ev.end():] excludes everything inside
    # the evidence block regardless of stray ``` lines.  When the evidence
    # regex did not match (fallback path), use the full block as before.
    why_rem_text = block_text[m_ev.end():] if m_ev else block_text

    # Why it's wrong
    why = _extract_section(why_rem_text, "Why it's wrong:")

    # Remediation
    remediation = _extract_section(why_rem_text, "Remediation:")

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
