"""Shared substrate for the forcing-functions detector family.

Exports:
  EXIT_CLEAN     -- exit code for a clean run (no findings).
  EXIT_FINDINGS  -- exit code for a run with violations.
  Finding        -- frozen dataclass representing one violation.
  emit_findings  -- serialize findings to stderr (one per line) and stdout
                    (JSON report); return the appropriate exit code.
  has_inline_escape -- check whether a source line carries a forcing-fn-ok
                       escape comment with mandatory reason text.
  path_in_allowlist -- check whether a file path matches any glob in a
                       caller-supplied allowlist.
"""

from __future__ import annotations

import dataclasses
import fnmatch
import json
import sys
from pathlib import Path
from typing import List, Optional

# Python 3.8+ ships typing.Literal; no third-party dep needed.
from typing import Literal

# ---------------------------------------------------------------------------
# Exit-code constants (exit 0 = clean, exit 2 = findings present).
# ---------------------------------------------------------------------------

EXIT_CLEAN: int = 0
EXIT_FINDINGS: int = 2


# ---------------------------------------------------------------------------
# Finding dataclass.
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class Finding:
    """A single forcing-function violation.

    Fields
    ------
    rule      : Detector identifier, e.g. ``"magic_enum_duplication"``.
    path      : File path where the violation was found (as given by scanner).
    line      : 1-based line number of the offending token.
    kind      : Always ``"VIOLATION"`` for this family.  Not merged with the
                drift-detector ``DRIFT``/``MISSING`` kinds.
    summary   : One-line human-readable description of the violation.
    fix_hint  : Optional suggestion for how to fix the violation.  None when
                no mechanical fix can be stated.
    """

    rule: str
    path: str
    line: int
    kind: Literal["VIOLATION"]
    summary: str
    fix_hint: Optional[str] = None


# ---------------------------------------------------------------------------
# emit_findings
# ---------------------------------------------------------------------------

def emit_findings(rule: str, findings: List[Finding]) -> int:
    """Emit findings to stderr and stdout, return appropriate exit code.

    Empty findings list
    -------------------
    Returns EXIT_CLEAN immediately; produces no stderr or stdout output.

    Non-empty findings list
    -----------------------
    For each finding, writes one line to stderr:
        <path>:<line>: <KIND> [<rule>] <summary>

    Then writes a single JSON object to stdout:
        {"rule": "<rule>", "findings": [{"path": ..., "line": ...,
         "kind": ..., "summary": ..., "fix_hint": ...}, ...]}

    Returns EXIT_FINDINGS.

    Parameters
    ----------
    rule     : The detector rule name (used as the top-level JSON key).
    findings : List of Finding objects.  Must all share the same rule name
               (callers are responsible for coherence; emit_findings does not
               enforce this to keep the function simple).

    Known limitations
    -----------------
    * The stderr ``path:line: KIND [rule] summary`` format is ambiguous when
      ``Finding.path`` contains ``:`` (e.g., Windows drive letters
      ``C:\\src\\foo.ts``).  Naive ``:`` splitters in editor / hook
      consumers may misparse the prefix.  Downstream surfaces
      (/implement gate relay; pre-commit hook output) MUST consume the
      stdout JSON for programmatic finding extraction; stderr is for human
      eyeballing only.
    * Multi-line ``Finding.summary`` would break the one-line-per-finding
      stderr contract.  Scanners are responsible for keeping summaries
      single-line; ``emit_findings`` does not sanitize embedded newlines.
    """
    if not findings:
        return EXIT_CLEAN

    for f in findings:
        sys.stderr.write(
            "{path}:{line}: {kind} [{rule}] {summary}\n".format(
                path=f.path,
                line=f.line,
                kind=f.kind,
                rule=f.rule,
                summary=f.summary,
            )
        )

    report = {
        "rule": rule,
        "findings": [
            {
                "path": f.path,
                "line": f.line,
                "kind": f.kind,
                "summary": f.summary,
                "fix_hint": f.fix_hint,
            }
            for f in findings
        ],
    }
    sys.stdout.write(json.dumps(report, indent=2))
    sys.stdout.write("\n")

    return EXIT_FINDINGS


# ---------------------------------------------------------------------------
# has_inline_escape
# ---------------------------------------------------------------------------

# Markers accepted on either side of a language boundary.
_TS_ESCAPE_PREFIX = "// forcing-fn-ok:"
_PY_ESCAPE_PREFIX = "# forcing-fn-ok:"


def has_inline_escape(file_path: Path, line_number: int) -> bool:
    """Return True if the source line carries a valid forcing-fn-ok escape.

    Rules
    -----
    * The line must contain ``// forcing-fn-ok:`` (TypeScript / JS style) or
      ``# forcing-fn-ok:`` (Python style).
    * Mandatory free-text must appear after the colon.  A naked marker with
      nothing (or only whitespace) after the colon is NOT a valid escape and
      returns False — escapes must carry an audit-trail reason.
    * ``line_number`` is 1-based.  Out-of-range → False (no exception).
    * File not readable / not found → False (no exception).

    Parameters
    ----------
    file_path   : Path to the source file.
    line_number : 1-based line number to inspect.
    """
    try:
        lines = Path(file_path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return False

    idx = line_number - 1  # convert to 0-based
    if idx < 0 or idx >= len(lines):
        return False

    line = lines[idx]

    for prefix in (_TS_ESCAPE_PREFIX, _PY_ESCAPE_PREFIX):
        pos = line.find(prefix)
        if pos == -1:
            continue
        # Everything after the colon (which is part of the prefix).
        after_colon = line[pos + len(prefix):]
        if after_colon.strip():
            return True
        # Marker found but no reason text — naked escape, reject.
        return False

    return False


# ---------------------------------------------------------------------------
# path_in_allowlist
# ---------------------------------------------------------------------------

def path_in_allowlist(file_path: Path, allowlist_globs: List[str]) -> bool:
    """Return True if file_path matches any glob in allowlist_globs.

    Uses ``fnmatch.fnmatch`` applied to the string representation of
    ``file_path`` as given (no absolute-path resolution).  Returns False
    for an empty allowlist.

    Glob limitation
    ---------------
    ``fnmatch.fnmatch`` does NOT expand ``**`` recursively across directory
    separators (unlike shell-glob ``**`` or ``pathlib.Path.match`` in
    Python 3.13+).  Pattern ``**/scripts/**`` matches ``a/scripts/b`` but
    NOT top-level ``scripts/b``.  Callers should pair each ``**/<x>``
    glob with its top-level twin (``<x>`` or ``<x>/**``).  Example:
    to exempt all ``*.fixture.ts`` files at any depth, pass
    ``["*.fixture.ts", "**/*.fixture.ts"]``.

    Parameters
    ----------
    file_path       : Path object (evaluated as-given, not resolved).
    allowlist_globs : List of glob patterns, e.g.
                      ``["*.fixture.ts", "**/*.fixture.ts"]``.
    """
    path_str = str(file_path)
    for glob in allowlist_globs:
        if fnmatch.fnmatch(path_str, glob):
            return True
    return False
