"""_inputs.py — read-verification, parse-completion-notes, read-plan-decisions
verbs for summarize_helper.

Three pure parsers that consume real producer output:

  read_verification(path)
      Parse verification.md's "## Acceptance Criteria" table into a per-AC
      list + the "## Verdict" value.  The AC table shape (from
      _verify/_report.py render_report) is:
          | AC | Status | Evidence |
          |---|---|---|
          | AC-N | <status> | <evidence> |
      The Verdict block shape is:
          ## Verdict

          **APPROVED** | **NEEDS WORK** | **REJECTED**
      This is the AUTHORITATIVE AC status (D3) — /summarize does NOT re-derive
      ACs from the spec.

  parse_completion_notes(task_text)
      Parse ONE task file's "## Completion Notes" section (filled by
      implement_helper mark-complete/_cmds_complete._fill_completion_notes).
      Shape produced by _build_completion_notes_block:
          ## Completion Notes

          **Completed**: <timestamp>
          **Files changed**: <comma-separated paths or "(none)">
          **Contract**: Expects <X/Y> | Produces <X/Y>
          **Notes**: <text>
      Returns a dict: completed_at, files_changed (list), expects_met,
      produces_met, notes, has_unverified (bool — True when any Done-When
      box carries the "_unverified_" annotation).
      Assumes task file paths do not contain commas — the producer
      (_implement mark-complete) joins the Files-changed list with ', ',
      which is not escaped, so a comma in a path would mis-split.

  read_plan_decisions(path)
      Parse plan.md's key-decisions section.  /plan emits one of two shapes:
        a. "### Key Design Decisions" (current template, plan_handoff_fixture.md)
           Table columns: Decision | Chosen Approach | Why | Alternatives Rejected
        b. "## Architecture Decisions" (older fixture, 008-sample-feature/plan.md)
           Table columns: Decision | Choice | Rationale
      Both shapes are parsed into a uniform list of dicts:
        { "decision": str, "chosen": str, "rationale": str, "rejected": str }
      "rejected" is empty for shape (b) which has no "Alternatives Rejected" column.
      D9: reads plan.md, NOT plan-handoff.json.

CLI handlers (cmd_read_verification, cmd_parse_completion_notes,
cmd_read_plan_decisions) are wired via _cli.py _SUBCOMMAND_REGISTRY.

Stdlib only.  Python 3.8+.
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Status values the AC table may carry (from report-format.md + render_report).
AC_STATUS_VALUES = frozenset([
    "PASS", "FAIL", "PARTIAL", "MANUAL",
    "PASS (code)", "FAIL (code)", "PARTIAL (code)", "UNVERIFIED",
])

# Verdict values emitted by render_report.
VERDICT_VALUES = frozenset(["APPROVED", "NEEDS WORK", "REJECTED"])

# ---------------------------------------------------------------------------
# read_verification
# ---------------------------------------------------------------------------

# Regex to match the verdict bold line: **APPROVED** / **NEEDS WORK** / **REJECTED**
_VERDICT_RE = re.compile(r"^\*\*(APPROVED|NEEDS WORK|REJECTED)\*\*", re.MULTILINE)

# Heading that starts the AC table section.
_AC_HEADING_RE = re.compile(r"^##\s+Acceptance Criteria\s*$", re.MULTILINE)

# Heading that starts the Verdict section.
_VERDICT_HEADING_RE = re.compile(r"^##\s+Verdict\s*$", re.MULTILINE)

# Separator / header rows to skip (e.g. "|---|---|---|" and the "| AC | Status | Evidence |" header).
_TABLE_SKIP_RE = re.compile(r"^\|[-:\s|]+\|$")


def _split_table_row(line):
    # type: (str) -> List[str]
    """Split a markdown table row into cells, respecting escaped pipes (\\|).

    Standard str.split("|") over-splits when evidence contains a literal
    backslash-pipe sequence (\\|) — render_report uses this to escape pipes
    within table cells so they don't break the table structure.  This function
    treats \\| as a non-delimiter and splits only on bare |.

    Strategy: replace each \\| with a sentinel, split on |, then restore.
    The sentinel is a character that cannot appear in the content (we use \x00).
    """
    sentinel = "\x00"
    # Temporarily replace escaped pipes.
    working = line.replace("\\|", sentinel)
    parts = working.split("|")
    # Restore the escaped pipes in each part.
    return [p.replace(sentinel, "|") for p in parts]


def read_verification(path):
    # type: (str) -> Tuple[Dict, Optional[str]]
    """Parse verification.md and return (result_dict, error_message).

    result_dict keys:
      ac_list   list[dict]  — per-AC dicts with keys: id, status, evidence
      verdict   str         — "APPROVED", "NEEDS WORK", "REJECTED", or ""
      path      str         — the file path read

    On error returns ({}, error_message).
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        return {}, "read-verification: cannot open {0!r}: {1}".format(path, exc)

    # --- Parse AC table ---
    ac_list = []  # type: List[Dict]

    # Find the ## Acceptance Criteria section.
    ac_heading_match = _AC_HEADING_RE.search(text)
    if ac_heading_match:
        # Re-search from after the AC heading.
        section_start = ac_heading_match.end()
        next_match = re.search(r"^##\s+", text[section_start:], re.MULTILINE)
        if next_match:
            section_end = section_start + next_match.start()
        else:
            section_end = len(text)
        ac_section = text[section_start:section_end]
    else:
        ac_section = text  # Fallback: search whole document.

    for line in ac_section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        # Skip separator rows (e.g. |---|---|---|).
        if _TABLE_SKIP_RE.match(stripped):
            continue
        # Split respecting escaped pipes.
        # _split_table_row splits on bare | (sentinel-protecting \|), producing
        # leading and trailing empty strings for the row's outer pipes.
        # Slice parts[1:-1] to drop those two boundary elements; this preserves
        # an empty evidence cell (e.g. "| AC-8 | UNVERIFIED |  |" → 5 parts,
        # parts[1:-1] = [' AC-8 ', ' UNVERIFIED ', '  ']).
        parts = _split_table_row(stripped)
        cells = [c.strip() for c in parts[1:-1]]
        if not cells:
            continue
        first_cell = cells[0].strip()
        # Skip header row.
        if first_cell.lower() in ("ac", "status"):
            continue

        # Expect at least 3 cells: id | status | evidence
        if len(cells) < 3:
            continue

        # Match AC-N pattern in first cell.
        ac_id = first_cell
        if not re.match(r"^AC-\d+$", ac_id):
            continue

        status = cells[1].strip()
        evidence = cells[2].strip()

        ac_list.append({
            "id": ac_id,
            "status": status,
            "evidence": evidence,
        })

    # --- Parse Verdict ---
    verdict = ""
    verdict_heading = _VERDICT_HEADING_RE.search(text)
    search_start = verdict_heading.end() if verdict_heading else 0
    verdict_match = _VERDICT_RE.search(text, search_start)
    if verdict_match:
        verdict = verdict_match.group(1)

    result = {
        "ac_list": ac_list,
        "verdict": verdict,
        "path": path,
    }
    return result, None


# ---------------------------------------------------------------------------
# cmd_read_verification
# ---------------------------------------------------------------------------


def cmd_read_verification(args):
    # type: (object) -> int
    """Handle the read-verification verb.

    Emits JSON to stdout on success (exit 0).
    Emits an error message to stderr on failure (exit 2).
    """
    path = getattr(args, "verification_path", "") or ""
    if not path:
        sys.stderr.write("read-verification: --path is required\n")
        return 2

    result, err = read_verification(path)
    if err:
        sys.stderr.write("{0}\n".format(err))
        return 2

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


# ---------------------------------------------------------------------------
# parse_completion_notes
# ---------------------------------------------------------------------------

# Heading that starts the Completion Notes section (from _cmds_complete.py).
_CN_HEADING_RE = re.compile(r"^##\s+Completion Notes\s*$", re.MULTILINE)
_NEXT_SECTION_RE = re.compile(r"^##\s+", re.MULTILINE)

# **Completed**: <value>
_COMPLETED_RE = re.compile(r"^\*\*Completed\*\*:\s*(.+)$", re.MULTILINE)

# **Files changed**: <value>
_FILES_CHANGED_RE = re.compile(r"^\*\*Files changed\*\*:\s*(.+)$", re.MULTILINE)

# **Contract**: Expects <X> | Produces <Y>
_CONTRACT_RE = re.compile(
    r"^\*\*Contract\*\*:\s*Expects\s+([^|]+?)\s*\|\s*Produces\s+(.+)$",
    re.MULTILINE,
)

# **Notes**: <value>
_NOTES_RE = re.compile(r"^\*\*Notes\*\*:\s*(.+)$", re.MULTILINE)

# Done-When unverified annotation (from _cmds_complete._UNVERIFIED_ANNOTATION).
_UNVERIFIED_BOX_RE = re.compile(
    r"^- \[ \].*_\(unverified",
    re.MULTILINE,
)


def parse_completion_notes(task_text):
    # type: (str) -> Dict
    """Parse the ## Completion Notes section from a task file.

    Returns a dict:
      completed_at    str         — timestamp string, or ""
      files_changed   list[str]   — parsed file list (split on ", "), or []
      expects_met     str         — e.g. "2/2", or ""
      produces_met    str         — e.g. "2/2", or ""
      notes           str         — deviation / observation text, or ""
      has_unverified  bool        — True when any Done-When box is annotated
                                    as unverified (left unticked by mark-complete)
      has_notes       bool        — True when a ## Completion Notes section exists

    Assumes task file paths do not contain commas — the producer
    (_implement mark-complete) joins the Files-changed list with ', ',
    which is not escaped, so a comma in a path would mis-split.
    """
    result = {
        "completed_at": "",
        "files_changed": [],
        "expects_met": "",
        "produces_met": "",
        "notes": "",
        "has_unverified": False,
        "has_notes": False,
    }  # type: Dict

    # Detect unverified boxes anywhere in the file (Done-When section).
    if _UNVERIFIED_BOX_RE.search(task_text):
        result["has_unverified"] = True

    # Find ## Completion Notes section.
    cn_match = _CN_HEADING_RE.search(task_text)
    if cn_match is None:
        return result

    result["has_notes"] = True
    section_start = cn_match.end()

    # Bound the section to the next ## heading (or EOF).
    next_match = _NEXT_SECTION_RE.search(task_text, section_start)
    section_end = next_match.start() if next_match else len(task_text)
    section = task_text[section_start:section_end]

    # Parse **Completed**:
    m = _COMPLETED_RE.search(section)
    if m:
        result["completed_at"] = m.group(1).strip()

    # Parse **Files changed**:
    m = _FILES_CHANGED_RE.search(section)
    if m:
        raw = m.group(1).strip()
        if raw and raw != "(none)":
            # Split on ", " to recover the list (mirrors _cmds_complete._cmd_mark_complete
            # which joins with ", " before writing).
            result["files_changed"] = [f.strip() for f in raw.split(",") if f.strip()]
        else:
            result["files_changed"] = []

    # Parse **Contract**: Expects X | Produces Y
    m = _CONTRACT_RE.search(section)
    if m:
        result["expects_met"] = m.group(1).strip()
        result["produces_met"] = m.group(2).strip()

    # Parse **Notes**:
    m = _NOTES_RE.search(section)
    if m:
        notes_val = m.group(1).strip()
        result["notes"] = notes_val if notes_val != "(none)" else ""

    return result


# ---------------------------------------------------------------------------
# cmd_parse_completion_notes
# ---------------------------------------------------------------------------


def cmd_parse_completion_notes(args):
    # type: (object) -> int
    """Handle the parse-completion-notes verb.

    Reads one or more task files and emits JSON to stdout (exit 0).
    On error, writes to stderr and exits 2.
    """
    task_files = getattr(args, "task_files", []) or []
    if not task_files:
        sys.stderr.write("parse-completion-notes: at least one --task-file is required\n")
        return 2

    results = []
    for path in task_files:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
        except OSError as exc:
            sys.stderr.write(
                "parse-completion-notes: cannot read {0!r}: {1}\n".format(path, exc)
            )
            return 2

        notes = parse_completion_notes(text)
        notes["task_file"] = path
        results.append(notes)

    sys.stdout.write(json.dumps(results, indent=2, sort_keys=True) + "\n")
    return 0


# ---------------------------------------------------------------------------
# read_plan_decisions
# ---------------------------------------------------------------------------

# Two heading shapes /plan emits:
#   Shape A (current template):  "### Key Design Decisions"
#   Shape B (older fixture):     "## Architecture Decisions"
#
# Both are table-based; the columns differ.  We parse both and normalize to
# a uniform schema: decision, chosen, rationale, rejected.
_PLAN_DECISIONS_HEADINGS = [
    # (regex_pattern, shape_label)
    (re.compile(r"^###\s+Key Design Decisions\s*$", re.MULTILINE), "A"),
    (re.compile(r"^##\s+Architecture Decisions\s*$", re.MULTILINE), "B"),
]

# Regex to match a markdown table row (starts and ends with pipe).
_TABLE_ROW_RE = re.compile(r"^\|(.+)\|$")

# Separator row (e.g. |---|---|---|).
_TABLE_SEP_RE = re.compile(r"^\|[-:\s|]+\|$")


def _parse_table_rows(text, section_start, section_end):
    # type: (str, int, int) -> List[List[str]]
    """Extract data rows (non-separator, non-header) from a markdown table."""
    section = text[section_start:section_end]
    rows = []  # type: List[List[str]]
    header_seen = False
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if _TABLE_SEP_RE.match(stripped):
            header_seen = True
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not header_seen:
            # This is the header row — skip it.
            header_seen = True
            continue
        # Skip placeholder rows (all cells are [placeholder] or empty).
        if all(not c or c.startswith("[") for c in cells):
            continue
        rows.append(cells)
    return rows


def _normalize_decision_row(cells, shape):
    # type: (List[str], str) -> Dict
    """Normalize a parsed row to the uniform decision schema.

    Shape A columns: Decision | Chosen Approach | Why | Alternatives Rejected
    Shape B columns: Decision | Choice | Rationale
    """
    def _safe(lst, idx, default=""):
        # type: (List[str], int, str) -> str
        return lst[idx] if idx < len(lst) else default

    if shape == "A":
        return {
            "decision": _safe(cells, 0),
            "chosen":   _safe(cells, 1),
            "rationale": _safe(cells, 2),
            "rejected": _safe(cells, 3),
        }
    else:
        # Shape B: Decision | Choice | Rationale (no Alternatives Rejected column)
        return {
            "decision": _safe(cells, 0),
            "chosen":   _safe(cells, 1),
            "rationale": _safe(cells, 2),
            "rejected": "",
        }


def read_plan_decisions(path):
    # type: (str) -> Tuple[Dict, Optional[str]]
    """Parse plan.md's key-decisions section.

    Supports two heading shapes:
      - "### Key Design Decisions" (current template — triple-hash)
      - "## Architecture Decisions" (older plans)

    Returns (result_dict, None) on success; ({}, error_message) on failure.

    result_dict keys:
      decisions   list[dict]  — per-decision dicts (decision, chosen, rationale, rejected)
      heading     str         — the matched heading text (for diagnostics)
      shape       str         — "A" or "B"
      path        str         — the file path read
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        return {}, "read-plan-decisions: cannot open {0!r}: {1}".format(path, exc)

    # Try each heading pattern in priority order.
    for heading_re, shape in _PLAN_DECISIONS_HEADINGS:
        match = heading_re.search(text)
        if match is None:
            continue

        heading_text = match.group(0).strip()
        section_start = match.end()

        # Bound the section to the next heading of the same or higher level.
        # For shape A (###), bound to the next ## or ###.
        # For shape B (##), bound to the next ##.
        if shape == "A":
            next_re = re.compile(r"^#{2,3}\s+", re.MULTILINE)
        else:
            next_re = re.compile(r"^##\s+", re.MULTILINE)
        next_match = next_re.search(text, section_start)
        section_end = next_match.start() if next_match else len(text)

        rows = _parse_table_rows(text, section_start, section_end)
        decisions = [_normalize_decision_row(row, shape) for row in rows
                     if any(c for c in row)]

        return {
            "decisions": decisions,
            "heading":   heading_text,
            "shape":     shape,
            "path":      path,
        }, None

    # No recognized heading found.
    return {
        "decisions": [],
        "heading":   "",
        "shape":     "",
        "path":      path,
    }, None


# ---------------------------------------------------------------------------
# cmd_read_plan_decisions
# ---------------------------------------------------------------------------


def cmd_read_plan_decisions(args):
    # type: (object) -> int
    """Handle the read-plan-decisions verb.

    Emits JSON to stdout on success (exit 0).
    Emits an error message to stderr on failure (exit 2).
    """
    path = getattr(args, "plan_path", "") or ""
    if not path:
        sys.stderr.write("read-plan-decisions: --path is required\n")
        return 2

    result, err = read_plan_decisions(path)
    if err:
        sys.stderr.write("{0}\n".format(err))
        return 2

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0
