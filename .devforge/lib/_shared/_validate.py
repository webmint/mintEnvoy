"""_validate -- anti-hallucination guard for ParsedFinding records.

Implements the 5-check validation pipeline from §4.2 of the /audit spec.
Each finding from an agent's output is checked in order; if any check fails
the finding is discarded and tallied.

Checks (in order, exactly as §4.2 mandates):
  1. file_exists      — cited file path exists under source_root
  2. line_oob         — 1 <= line <= total file lines
  3. quote_mismatch   — evidence is a literal substring of the file content
                        (whitespace-normalised: runs of spaces collapsed,
                        trailing whitespace per line stripped).
                        Empty / whitespace-only / "..."-only evidence
                        normalises to "" which fails `not normalised_evidence`,
                        so it is also discarded here as quote_mismatch.
  4. evidence_empty   — evidence is "..." literal or whitespace-only after
                        stripping (defensive follow-up; rarely fires because
                        check 3 already rejects empty normalised evidence as
                        quote_mismatch, but kept for spec completeness and
                        accurate per-reason tallies in adversarial edge cases)
  5. pattern_missing  — pattern field is non-empty

Design note on checks 3 & 4:
  Check 3 runs FIRST per §4.2.  The guard `if not normalised_evidence` within
  check 3 means truly-empty or whitespace-only evidence is caught here and
  reported as quote_mismatch.  Check 4 is a defensive follow-up: it can only
  fire if evidence_stripped is "..." (which normalises to "..." — a non-empty
  token — so it passes the `not normalised_evidence` guard but is still
  semantically empty per the spec).  In practice "..." is unlikely to appear
  verbatim in any source file so it would fail the substring test in check 3
  anyway, making check 4 a belt-and-suspenders guard.

Whitespace normalisation rule (check 3):
  - Collapse runs of spaces (but not other whitespace chars) to a single space.
  - Strip leading/trailing whitespace from each token before collapsing.
  This allows evidence copied with slightly different indentation to still
  match.  Tabs and newlines are normalised by joining lines then re-splitting.

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Reason constants (used in discard_counts keys and discard reason strings)
# ---------------------------------------------------------------------------

REASON_FILE_MISSING = "file_missing"
REASON_LINE_OOB = "line_oob"
REASON_QUOTE_MISMATCH = "quote_mismatch"
REASON_EVIDENCE_EMPTY = "evidence_empty"
REASON_PATTERN_MISSING = "pattern_missing"

_ALL_REASONS = (
    REASON_FILE_MISSING,
    REASON_LINE_OOB,
    REASON_QUOTE_MISMATCH,
    REASON_EVIDENCE_EMPTY,
    REASON_PATTERN_MISSING,
)

# ---------------------------------------------------------------------------
# Normalisation helper
# ---------------------------------------------------------------------------


def _normalize_whitespace(text):
    # type: (str) -> str
    """Collapse runs of spaces to a single space and strip trailing whitespace
    from each line. Lines are joined with a single space so multi-line evidence
    can be compared as a flat string.

    Newlines and tabs are treated as whitespace boundaries: we split on
    whitespace tokens and rejoin with spaces so the comparison is
    order-of-tokens, not layout-dependent.
    """
    # Split on any whitespace (space, tab, newline) then rejoin
    tokens = text.split()
    return " ".join(tokens)


# ---------------------------------------------------------------------------
# File cache to avoid re-reading the same file for multiple findings
# ---------------------------------------------------------------------------


class _FileCache:
    """Lazy per-path cache of (content_str, line_count, normalised_content)."""

    def __init__(self):
        # type: () -> None
        self._cache = {}  # type: Dict[str, Optional[Tuple[str, int, str]]]

    def get(self, abs_path):
        # type: (str, ) -> Optional[Tuple[str, int, str]]
        """Return (raw_text, line_count, normalised_text) or None if unreadable."""
        if abs_path not in self._cache:
            try:
                with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
                    raw = fh.read()
                lines = raw.splitlines()
                line_count = len(lines)
                normalised = _normalize_whitespace(raw)
                self._cache[abs_path] = (raw, line_count, normalised)
            except OSError:
                self._cache[abs_path] = None
        return self._cache[abs_path]


# ---------------------------------------------------------------------------
# Core validation function
# ---------------------------------------------------------------------------


def validate_findings(findings, repo_root, source_root=""):
    # type: (List[dict], str, str) -> dict
    """Run the 5-check anti-hallucination pipeline on a list of ParsedFinding
    dicts.

    Parameters
    ----------
    findings:    List of ParsedFinding dicts (from parse_agent_tmp output).
    repo_root:   Absolute path to the repo root.  Relative file paths in
                 findings are resolved against this directory.  When a finding
                 cites a config file at the workspace root, this is also tried.
    source_root: Optional sub-path within repo_root (e.g. "src").  When
                 non-empty, <repo_root>/<source_root>/<file> is tried FIRST
                 before falling back to <repo_root>/<file>.

    Returns a dict with keys:
      passed         : list of finding dicts that passed all checks
      discarded      : list of {"finding": <dict>, "reason": <str>}
      discard_counts : {reason_key: int}  per-reason tally
    """
    cache = _FileCache()
    passed = []
    discarded = []
    counts = {r: 0 for r in _ALL_REASONS}

    for finding in findings:
        reason = _check_finding(finding, repo_root, source_root, cache)
        if reason is None:
            passed.append(finding)
        else:
            discarded.append({"finding": finding, "reason": reason})
            counts[reason] += 1

    return {
        "passed": passed,
        "discarded": discarded,
        "discard_counts": counts,
    }


def _resolve_path(file_path, repo_root, source_root):
    # type: (str, str, str) -> Optional[str]
    """Return an existing absolute path for file_path, or None.

    Resolution order:
      1. <repo_root>/<source_root>/<file_path>   (if source_root non-empty)
      2. <repo_root>/<file_path>
      3. file_path as-is (absolute path already)
    """
    candidates = []
    if source_root:
        candidates.append(
            os.path.join(repo_root, source_root, file_path)
        )
    candidates.append(os.path.join(repo_root, file_path))
    if os.path.isabs(file_path):
        candidates.append(file_path)

    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def _check_finding(finding, repo_root, source_root, cache):
    # type: (dict, str, str, _FileCache) -> Optional[str]
    """Return a reason string if the finding fails validation, else None.

    Checks are performed in the order mandated by §4.2.
    """
    file_path = finding.get("file", "")
    line_no = finding.get("line", 0)
    evidence = finding.get("evidence", "")
    pattern = finding.get("pattern", "")

    # Checks run in §4.2 order: file_exists → line_oob → quote → evidence → pattern

    # --- Check 1: file exists ---
    abs_path = _resolve_path(file_path, repo_root, source_root)
    if abs_path is None:
        return REASON_FILE_MISSING

    # --- Check 2: line number sanity ---
    file_data = cache.get(abs_path)
    if file_data is None:
        # File exists (check 1 passed) but is unreadable — treat as line OOB
        return REASON_LINE_OOB

    _raw_text, line_count, _norm = file_data
    if not isinstance(line_no, int) or isinstance(line_no, bool):
        return REASON_LINE_OOB
    if line_no < 1 or line_no > line_count:
        return REASON_LINE_OOB

    # --- Check 3: verbatim quote (literal substring, whitespace-normalised).
    # The `not normalised_evidence` guard also catches empty / whitespace-only
    # evidence (normalises to ""), reporting it as quote_mismatch per §4.2. ---
    evidence_stripped = evidence.strip() if evidence else ""
    _, _, normalised_file = file_data
    normalised_evidence = _normalize_whitespace(evidence_stripped)
    if not normalised_evidence or normalised_evidence not in normalised_file:
        return REASON_QUOTE_MISMATCH

    # --- Check 4: evidence not "..." / whitespace-only (defensive; check 3
    # already rejects truly-empty evidence, but "..." may survive as a
    # non-empty token that does not appear in the file — caught above — so
    # this check fires only in the rare case where "..." somehow passes the
    # substring test, which requires the literal string "..." to be present in
    # the source file). ---
    if not evidence_stripped or evidence_stripped == "...":
        return REASON_EVIDENCE_EMPTY

    # --- Check 5: pattern present ---
    if not pattern or not pattern.strip():
        return REASON_PATTERN_MISSING

    return None
