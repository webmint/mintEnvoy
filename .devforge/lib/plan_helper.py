"""plan_helper — structural emission helper for the /plan slash command.

Subcommands:

  pick-spec [path]
      Resolve which spec to plan against.
      With path: validate the file exists and has the 9-section shape,
                 print its absolute path.
      No path:   glob specs/*/spec.md under cwd, pick highest mtime,
                 print its absolute path.
      Exit 0 on success; exit 2 if no valid spec found or path invalid.

  render-pick-summary <spec-path>
      Print a deterministic 5-line preview block the LLM copies verbatim
      into its AskUserQuestion context.
      Lines emitted:
        **Spec**: <path>
        **Type**: <spec-type or "unknown">
        **AC count**: <N> criteria across <M> subsections
        **Status**: <Draft|Approved|Complete|unknown>
        **Last modified**: <YYYY-MM-DD>
      Exit 0; exit 2 if file missing.

  list-specs
      List all specs/*/spec.md under cwd sorted by mtime desc.
      One line per spec: <index>) <relative-path> [Status: <X>] (<N> ACs)
      Exit 0 (even if empty); exit 2 if specs/ dir missing.

  check-status-and-flip <spec-path>
      Read the **Status**: line from spec frontmatter and act:
        Draft     -> rewrite to Approved, print "flipped"
        Approved  -> no change, print "already-approved"
        Complete  -> no change, print "complete"
        missing   -> insert after **Date**: line, print "inserted"
        unknown   -> no change, print "unknown-status:<value>" (surfaces anomaly to LLM)
        malformed -> exit 2 (no Date or Status line at all)
      Writes are atomic (tempfile.mkstemp + os.replace).
      Exit 0 on all success paths.

  render-findings-from-spec <spec-path>
      Emit a Phase 1.5 skeleton enumerating every spec §3-§9 finding.
      LLM fills [PLAN COVERAGE: ?] markers.
      Exit 0; exit 2 if spec missing or lacks expected sections.

  render-breakdown-handoff <spec-path> <plan-path>
      Emit the Phase 4 manual handoff block targeting /breakdown.
      Reads AC count from spec, file-impact + risk counts from plan.
      Exit 0; exit 2 if either file missing.

  read-specify-handoff <spec-path>
      Resolve and validate the sibling specify handoff.json for a spec.md.
      The sibling is spec_path.parent / "handoff.json".
      Success (sibling valid): print a 4-line block —
        spec-handoff: <absolute-path-to-handoff.json>
        spec_seeds: present
        upstream_handoff_path: <path or "none">
        upstream_handoff_kind: <kind or "none">
      No sibling: print "no-handoff", exit 0.
      Malformed or schema-invalid sibling: exit 2.
      spec-path is a directory or does not exist: exit 2.

  render-consultation-block
      Emit the content under the '## Specialist Consultation' heading —
      the intro paragraph, the five-column table, and the verdict-enum rule.
      The heading itself is NOT emitted (the template owns it); output starts
      with the intro paragraph. Takes no arguments. Helper owns the five
      column names (Specialist, Sub-question, Input summary, Verdict, Cites)
      and the verdict enum (accepted / modified / rejected / no-response);
      the LLM fills values. Includes an example placeholder row and the
      empty-state (none) row. Exit 0 always.

  render-plan-seeds <specify-handoff-path>
      Render a structured plan-seeds block from the upstream research/discover
      handoff referenced by a specify-handoff.json.
      Reads provenance.upstream_handoff_path from the specify handoff, loads
      the upstream file, dispatches on upstream_handoff_kind ('research' or
      'discover'), and emits a deterministic multi-line block.
      Success: print the rendered block, exit 0.
      Null upstream_handoff_path (cold path): print "cold-no-plan-seeds", exit 0.
      upstream file missing or upstream_handoff_kind unknown: exit 2.

  finalize-handoff <plan-path> [--completed-at ISO]
      Parse plan.md into structured breakdown_seeds and write
      <plan-dir>/plan-handoff.json (sibling to plan.md).
      Sections parsed: Layer Map, Key Design Decisions, File Impact,
      Documentation Impact, Risk Assessment, Specialist Consultation,
      Dependencies. Placeholder rows are skipped.
      Provenance: resolves the sibling specify handoff.json (handoff.json
      in the same directory) if present and valid; sets upstream_handoff_path
      + upstream_handoff_kind = "specify". Also resolves spec_path from the
      sibling spec.md if present.
      --completed-at: optional UTC ISO timestamp; defaults to now.
      On success: prints the written path to stdout, exit 0.
      Missing plan-path: exit 2.
      Schema validation failure: exit 2 with message on stderr.
      Idempotent: re-running overwrites the previous plan-handoff.json.

Exit codes:
  0 — success
  1 — reserved for I/O failures (write errors)
  2 — usage error / not-found / malformed input

Stdout is the canonical channel for output tokens; stderr for errors.
No state file — every subcommand re-reads input files.
Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants.
# ---------------------------------------------------------------------------

# Expected section headings in order (index = section number - 1).
_SECTION_TITLES = [
    "Overview",
    "Current State",
    "Desired Behavior",
    "Affected Areas",
    "Acceptance Criteria",
    "Out of Scope",
    "Technical Constraints",
    "Open Questions",
    "Risks",
]

_REQUIRED_SECTION_PATTERN = re.compile(
    r"^##\s+(\d+)\.\s+", re.MULTILINE
)

# AC line pattern: "- [x] **AC-N**: ..." or "- [ ] **AC-N**: ..."
_AC_LINE_PATTERN = re.compile(r"^\s*-\s+\[[xX ]\]\s+\*\*AC-\d+\*\*", re.MULTILINE)

# Subsection heading pattern (e.g. "### 5.1 Tooling / artifact presence...")
_AC_SUBSECTION_PATTERN = re.compile(r"^###\s+5\.\d+\s+", re.MULTILINE)

# Frontmatter field patterns.
#
# IMPORTANT: _STATUS_PATTERN uses [ \t]* (horizontal whitespace only), NOT
# \s*.  The status value MUST appear on the same line as the **Status**:
# marker.  Using \s* would allow the match to bleed across a blank line and
# capture a value from the next non-empty line in a malformed spec (e.g.
# "**Status**:\n\nDraft\n" would wrongly yield "Draft").
_STATUS_PATTERN = re.compile(r"^\*\*Status\*\*:[ \t]*(.+)$", re.MULTILINE)
_DATE_PATTERN = re.compile(r"^\*\*Date\*\*:\s*(.+)$", re.MULTILINE)
_SPEC_TYPE_PATTERN = re.compile(r"^\*\*Spec type\*\*:\s*(.+)$", re.MULTILINE)


# ---------------------------------------------------------------------------
# Spec parsing utilities.
# ---------------------------------------------------------------------------


def _read_file(path: str) -> Optional[str]:
    """Return file contents as string, or None if unreadable."""
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, IOError):
        return None


def _has_nine_sections(content: str) -> bool:
    """Return True if content contains headings ## 1. through ## 9."""
    found = set()
    for m in _REQUIRED_SECTION_PATTERN.finditer(content):
        found.add(int(m.group(1)))
    return all(i in found for i in range(1, 10))


def _extract_section(content: str, section_num: int) -> str:
    """Extract text of section N (between ## N. heading and ## N+1. heading or EOF)."""
    # Build pattern matching the exact section heading.
    start_pat = re.compile(
        r"^##\s+" + str(section_num) + r"\.\s+", re.MULTILINE
    )
    m_start = start_pat.search(content)
    if not m_start:
        return ""
    start = m_start.start()
    # Find next ## heading at the same or higher level.
    next_h2 = re.compile(r"^##\s+", re.MULTILINE)
    m_next = next_h2.search(content, m_start.end())
    if m_next:
        return content[start:m_next.start()]
    return content[start:]


def _parse_frontmatter_field(content: str, pattern: re.Pattern) -> Optional[str]:
    """Extract the value of a frontmatter field."""
    m = pattern.search(content)
    if not m:
        return None
    return m.group(1).strip()


def _count_acs(content: str) -> Tuple[int, int]:
    """Return (total_ac_count, subsections_with_acs).

    Counts AC lines matching ``- [x/X/ ] **AC-N**`` in section 5 only,
    and counts the number of ### 5.x subsections that contain at least
    one such line.
    """
    sec5 = _extract_section(content, 5)
    total = len(_AC_LINE_PATTERN.findall(sec5))

    # Count subsections with ≥1 AC.
    subsections_with_acs = 0
    for sub_m in _AC_SUBSECTION_PATTERN.finditer(sec5):
        sub_start = sub_m.start()
        # Find next ### heading or end of section.
        next_sub = _AC_SUBSECTION_PATTERN.search(sec5, sub_m.end())
        sub_text = sec5[sub_start:(next_sub.start() if next_sub else len(sec5))]
        if _AC_LINE_PATTERN.search(sub_text):
            subsections_with_acs += 1

    return total, subsections_with_acs


def _file_mtime_iso(path: str) -> str:
    """Return file mtime as YYYY-MM-DD."""
    ts = os.path.getmtime(path)
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


def _glob_specs(cwd: str) -> List[str]:
    """Return list of absolute paths to specs/*/spec.md under cwd."""
    specs_dir = Path(cwd) / "specs"
    if not specs_dir.is_dir():
        return []
    result = []
    for sub in specs_dir.iterdir():
        candidate = sub / "spec.md"
        if candidate.is_file():
            result.append(str(candidate.resolve()))
    return result


def _valid_specs(paths: List[str]) -> List[str]:
    """Filter to paths whose content has the full 9-section shape."""
    valid = []
    for p in paths:
        content = _read_file(p)
        if content is not None and _has_nine_sections(content):
            valid.append(p)
    return valid


# ---------------------------------------------------------------------------
# Subcommand: pick-spec
# ---------------------------------------------------------------------------


def cmd_pick_spec(args) -> int:
    """Resolve the spec path and print it to stdout."""
    spec_path = getattr(args, "path", None)

    if spec_path:
        # Explicit path given.
        resolved = Path(spec_path)
        if not resolved.is_absolute():
            resolved = Path.cwd() / resolved
        if not resolved.is_file():
            sys.stderr.write(
                "plan_helper: spec not found: {0}\n".format(spec_path)
            )
            return 2
        content = _read_file(str(resolved))
        if content is None or not _has_nine_sections(content):
            sys.stderr.write(
                "plan_helper: spec at {0} does not have the required "
                "9-section shape (## 1. Overview ... ## 9. Risks)\n".format(spec_path)
            )
            return 2
        sys.stdout.write(str(resolved) + "\n")
        return 0

    # Auto-pick: find highest-mtime valid spec under specs/.
    cwd = str(Path.cwd())
    specs_dir = Path(cwd) / "specs"
    if not specs_dir.is_dir():
        sys.stderr.write(
            "plan_helper: no valid spec found under specs/; run /specify first\n"
        )
        return 2

    all_paths = _glob_specs(cwd)
    valid = _valid_specs(all_paths)
    if not valid:
        sys.stderr.write(
            "plan_helper: no valid spec found under specs/; run /specify first\n"
        )
        return 2

    # Pick highest mtime.
    best = max(valid, key=lambda p: os.path.getmtime(p))
    sys.stdout.write(best + "\n")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: render-pick-summary
# ---------------------------------------------------------------------------


def cmd_render_pick_summary(args) -> int:
    """Print a 5-line deterministic pick-summary block."""
    spec_path = args.spec_path
    content = _read_file(spec_path)
    if content is None:
        sys.stderr.write(
            "plan_helper: cannot read spec: {0}\n".format(spec_path)
        )
        return 2

    status = _parse_frontmatter_field(content, _STATUS_PATTERN) or "unknown"
    spec_type = _parse_frontmatter_field(content, _SPEC_TYPE_PATTERN) or "unknown"
    total_acs, subsections = _count_acs(content)
    last_modified = _file_mtime_iso(spec_path)

    sys.stdout.write("**Spec**: {0}\n".format(spec_path))
    sys.stdout.write("**Type**: {0}\n".format(spec_type))
    sys.stdout.write(
        "**AC count**: {0} criteria across {1} subsections\n".format(
            total_acs, subsections
        )
    )
    sys.stdout.write("**Status**: {0}\n".format(status))
    sys.stdout.write("**Last modified**: {0}\n".format(last_modified))
    return 0


# ---------------------------------------------------------------------------
# Subcommand: list-specs
# ---------------------------------------------------------------------------


def cmd_list_specs(args) -> int:
    """List all specs sorted by mtime desc."""
    cwd = str(Path.cwd())
    specs_dir = Path(cwd) / "specs"
    if not specs_dir.is_dir():
        sys.stderr.write(
            "plan_helper: specs/ directory not found under cwd\n"
        )
        return 2

    all_paths = _glob_specs(cwd)
    if not all_paths:
        # Empty dir is valid; emit nothing.
        return 0

    # Sort by mtime descending.
    sorted_paths = sorted(all_paths, key=lambda p: os.path.getmtime(p), reverse=True)

    for idx, abs_path in enumerate(sorted_paths, start=1):
        content = _read_file(abs_path)
        if content is None:
            status = "unknown"
            ac_count = 0
        else:
            status = _parse_frontmatter_field(content, _STATUS_PATTERN) or "unknown"
            ac_count, _ = _count_acs(content)

        # Relative path from cwd.
        try:
            rel_path = str(Path(abs_path).relative_to(Path(cwd)))
        except ValueError:
            rel_path = abs_path

        sys.stdout.write(
            "{0}) {1} [Status: {2}] ({3} ACs)\n".format(
                idx, rel_path, status, ac_count
            )
        )
    return 0


# ---------------------------------------------------------------------------
# Subcommand: check-status-and-flip
# ---------------------------------------------------------------------------


def _atomic_write(path: str, content: str) -> None:
    """Write content to path atomically using tempfile + os.replace."""
    target = Path(path)
    fd, tmp_path = tempfile.mkstemp(
        prefix="plan-status-",
        suffix=".tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, str(target))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def cmd_check_status_and_flip(args) -> int:
    """Read **Status**: line and flip Draft → Approved as needed."""
    spec_path = args.spec_path
    content = _read_file(spec_path)
    if content is None:
        sys.stderr.write(
            "plan_helper: cannot read spec: {0}\n".format(spec_path)
        )
        return 2

    status_match = _STATUS_PATTERN.search(content)
    date_match = _DATE_PATTERN.search(content)

    if status_match:
        status_val = status_match.group(1).strip()
        if status_val == "Draft":
            new_content = (
                content[: status_match.start()]
                + "**Status**: Approved"
                + content[status_match.end():]
            )
            try:
                _atomic_write(spec_path, new_content)
            except OSError as err:
                sys.stderr.write(
                    "plan_helper: cannot write spec: {0}\n".format(err)
                )
                return 1
            sys.stdout.write("flipped\n")
            return 0
        elif status_val == "Approved":
            sys.stdout.write("already-approved\n")
            return 0
        elif status_val == "Complete":
            sys.stdout.write("complete\n")
            return 0
        else:
            sys.stdout.write("unknown-status:{0}\n".format(status_val))
            return 0

    # No **Status**: line found.
    if date_match is None:
        sys.stderr.write(
            "plan_helper: no Date or Status frontmatter line found; "
            "spec malformed\n"
        )
        return 2

    # Insert **Status**: Approved immediately after the **Date**: line.
    insert_pos = date_match.end()
    # Find the end of the date line (the newline character).
    # date_match.end() is right after the matched text on that line.
    # We need to move past the newline if present.
    new_content = (
        content[:insert_pos]
        + "\n**Status**: Approved"
        + content[insert_pos:]
    )
    try:
        _atomic_write(spec_path, new_content)
    except OSError as err:
        sys.stderr.write(
            "plan_helper: cannot write spec: {0}\n".format(err)
        )
        return 1
    sys.stdout.write("inserted\n")
    return 0


# ---------------------------------------------------------------------------
# Section rendering helpers for render-findings-from-spec.
# ---------------------------------------------------------------------------


def _truncate(text: str, max_len: int = 80) -> str:
    """Return text truncated to max_len chars with '...' suffix if truncated."""
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def _render_sec3(sec_text: str) -> List[str]:
    """Enumerate §3 Desired Behavior items."""
    lines_out = []

    # Try numbered bullets first: "1. ", "2. ", etc.
    numbered_pat = re.compile(r"^\d+\.\s+(.+)", re.MULTILINE)
    numbered = numbered_pat.findall(sec_text)
    if numbered:
        for i, item in enumerate(numbered, start=1):
            lines_out.append(
                "- §3 item {0}: {1} [PLAN COVERAGE: ?]".format(
                    i, _truncate(item)
                )
            )
        return lines_out

    # Try bullet list: "- text" (but skip the heading line itself).
    bullet_pat = re.compile(r"^\s*-\s+(?!\[)(.+)", re.MULTILINE)
    bullets = bullet_pat.findall(sec_text)
    if bullets:
        for i, item in enumerate(bullets, start=1):
            lines_out.append(
                "- §3 item {0}: {1} [PLAN COVERAGE: ?]".format(
                    i, _truncate(item)
                )
            )
        return lines_out

    # Fallback: non-blank paragraphs (skip heading line).
    paras = []
    current = []
    for line in sec_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("##"):
            continue
        if stripped:
            current.append(stripped)
        else:
            if current:
                paras.append(" ".join(current))
                current = []
    if current:
        paras.append(" ".join(current))

    for i, para in enumerate(paras, start=1):
        lines_out.append(
            "- §3 item {0}: {1} [PLAN COVERAGE: ?]".format(i, _truncate(para))
        )
    return lines_out


def _parse_table_rows(sec_text: str) -> List[List[str]]:
    """Return list of non-header, non-separator table rows as cell lists."""
    rows = []
    header_seen = False
    for line in sec_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        # Check separator row: only |, -, spaces.
        if re.match(r"^\|[\s\-|:]+\|?\s*$", stripped):
            header_seen = True
            continue
        # First non-separator pipe row is the header.
        if not header_seen:
            header_seen = True
            continue
        # Data row.
        cells = [c.strip() for c in stripped.split("|") if c.strip()]
        if cells:
            rows.append(cells)
    return rows


def _is_empty_placeholder_row(cells: List[str]) -> bool:
    """Return True if the first cell is an '_(none)_' placeholder."""
    if not cells:
        return False
    return bool(re.match(r"_\(none\)_", cells[0]))


def _render_sec4(sec_text: str) -> List[str]:
    """Enumerate §4 Affected Areas table rows."""
    rows = _parse_table_rows(sec_text)
    if not rows:
        return ["- §4: (no affected areas recorded)"]
    if len(rows) == 1 and _is_empty_placeholder_row(rows[0]):
        return ["- §4: (no affected areas recorded)"]
    lines_out = []
    for i, cells in enumerate(rows, start=1):
        area = cells[0] if len(cells) > 0 else "?"
        files = cells[1] if len(cells) > 1 else "?"
        lines_out.append(
            "- §4 row {0}: {1} → {2}: [PLAN COVERAGE: ?]".format(
                i, _truncate(area, 40), _truncate(files, 40)
            )
        )
    return lines_out


def _render_sec5(sec_text: str) -> List[str]:
    """Enumerate §5 AC subsections with per-AC entries."""
    lines_out = []

    # Split by ### 5.x headings.
    subsection_pat = re.compile(r"^(###\s+5\.\d+\s+.+)$", re.MULTILINE)
    subsection_starts = list(subsection_pat.finditer(sec_text))

    if not subsection_starts:
        # No subsections found — emit raw ACs if any.
        acs = _AC_LINE_PATTERN.findall(sec_text)
        if acs:
            lines_out.append("- §5: {0} ACs".format(len(acs)))
        return lines_out

    for idx, sub_m in enumerate(subsection_starts):
        sub_heading = sub_m.group(1).strip()
        sub_start = sub_m.start()
        if idx + 1 < len(subsection_starts):
            sub_end = subsection_starts[idx + 1].start()
        else:
            sub_end = len(sec_text)
        sub_text = sec_text[sub_start:sub_end]

        # Find AC lines.
        # Pattern handles optional annotation between AC number and colon,
        # e.g. "**AC-10** (repro pass): text" as well as "**AC-1**: text".
        ac_lines_raw = re.findall(
            r"^\s*-\s+\[[xX ]\]\s+\*\*AC-(\d+)\*\*(?:[^:]*)?:\s*(.+)$",
            sub_text,
            re.MULTILINE,
        )
        if not ac_lines_raw:
            continue  # Skip empty subsections.

        # Subsection title: strip "### 5.N " prefix for readability.
        # Extract actual subsection number from heading so missing/skipped
        # subsections in the spec don't shift labels in the output.
        sub_num_m = re.search(r"###\s+5\.(\d+)\s+", sub_heading)
        sub_num = sub_num_m.group(1) if sub_num_m else str(idx + 1)
        sub_title = re.sub(r"^###\s+5\.\d+\s+", "", sub_heading)
        lines_out.append(
            "- §5.{0} ({1}): {2} ACs".format(
                sub_num, sub_title, len(ac_lines_raw)
            )
        )
        for ac_num, ac_text in ac_lines_raw:
            lines_out.append(
                "  - AC-{0}: {1} [PLAN COVERAGE: ?]".format(
                    ac_num, _truncate(ac_text)
                )
            )

    return lines_out


def _render_sec6(sec_text: str) -> List[str]:
    """Enumerate §6 Out of Scope bullets."""
    lines_out = []
    # Pattern: "- NOT included: <text>"
    not_included_pat = re.compile(
        r"^\s*-\s+NOT included:\s*(.+)$", re.MULTILINE
    )
    items = not_included_pat.findall(sec_text)
    if not items:
        return ["- §6: (no out-of-scope items recorded)"]
    for i, item in enumerate(items, start=1):
        lines_out.append(
            "- §6 item {0}: {1} [must not contradict]".format(
                i, _truncate(item)
            )
        )
    return lines_out


def _render_sec7(sec_text: str) -> List[str]:
    """Enumerate §7 Technical Constraints bullets."""
    lines_out = []
    # Pattern: "- **Label**: text" or "- Label: text" (bold optional)
    constraint_pat = re.compile(
        r"^\s*-\s+(?:\*\*)?([^:*\n]+?)(?:\*\*)?:\s+(.+)$", re.MULTILINE
    )
    items = constraint_pat.findall(sec_text)
    # Filter out placeholder lines.
    real_items = [
        (label, text)
        for label, text in items
        if not re.match(r"_\(no", label.strip())
    ]
    if not real_items:
        return ["- §7: (no constraints recorded)"]
    for i, (label, text) in enumerate(real_items, start=1):
        lines_out.append(
            "- §7 item {0} ({1}): {2} [LANDS IN: ?]".format(
                i, label.strip(), _truncate(text)
            )
        )
    return lines_out


def _render_sec8(sec_text: str) -> List[str]:
    """Enumerate §8 Open Questions + Decision-Point bullets.

    Captures both Q-prefixed open-question entries and DP-prefixed
    decision-point entries (specify_helper emits both shapes into §8).
    """
    lines_out = []
    # Pattern: "- **ID**: content" where ID is Q<digit-or-hyphen>... or DP-...
    # (possibly struck-through with ~~ when resolved).
    # ID grammar:
    #   Q[\d-][\w-]*  matches Q1, Q12, Q1-scope, Q-1, Q-scope (rejects
    #                 Question, Quality, Quack — first char after Q must be
    #                 digit or hyphen, not letter)
    #   DP-[\w-]+     matches DP-A, DP-1, DP-foo (rejects DPR, DPA, DP)
    item_pat = re.compile(
        r"^\s*-\s+(?:~~)?(?:\*\*)?(Q[\d-][\w-]*|DP-[\w-]+)(?:\*\*)?:?\s*"
        r"(?:~~)?(.+?)(?:~~)?\s*$",
        re.MULTILINE,
    )
    items = item_pat.findall(sec_text)
    real_items = [
        (item_id, text)
        for item_id, text in items
        if not re.match(r"_\(no", text.strip())
    ]
    if not real_items:
        return ["- §8: (no open questions recorded)"]
    for i, (item_id, text) in enumerate(real_items, start=1):
        # Strip any remaining ~~ or ** markers that survived the capture.
        clean_text = re.sub(r"~~|\*\*", "", text).strip()
        lines_out.append(
            "- §8 item {0} ({1}): {2} [RESOLUTION: ?]".format(
                i, item_id, _truncate(clean_text)
            )
        )
    return lines_out


def _render_sec9(sec_text: str) -> List[str]:
    """Enumerate §9 Risks table rows."""
    rows = _parse_table_rows(sec_text)
    if not rows:
        return ["- §9: (no risks recorded)"]
    if len(rows) == 1 and _is_empty_placeholder_row(rows[0]):
        return ["- §9: (no risks recorded)"]
    lines_out = []
    for i, cells in enumerate(rows, start=1):
        risk = cells[0] if cells else "?"
        lines_out.append(
            "- §9 risk {0}: {1} [MITIGATION CARRIED: ?]".format(
                i, _truncate(risk)
            )
        )
    return lines_out


# ---------------------------------------------------------------------------
# Subcommand: render-findings-from-spec
# ---------------------------------------------------------------------------


def cmd_render_findings_from_spec(args) -> int:
    """Emit the Phase 1.5 findings skeleton from the spec."""
    spec_path = args.spec_path
    content = _read_file(spec_path)
    if content is None:
        sys.stderr.write(
            "plan_helper: cannot read spec: {0}\n".format(spec_path)
        )
        return 2
    if not _has_nine_sections(content):
        sys.stderr.write(
            "plan_helper: spec does not have the required 9-section shape "
            "(## 1. Overview ... ## 9. Risks)\n"
        )
        return 2

    output_lines: List[str] = ["## Findings from Spec", ""]

    # §3 Desired Behavior.
    sec3 = _extract_section(content, 3)
    output_lines.append("### From spec §3 (Desired Behavior)")
    output_lines.extend(_render_sec3(sec3))
    output_lines.append("")

    # §4 Affected Areas.
    sec4 = _extract_section(content, 4)
    output_lines.append("### From spec §4 (Affected Areas)")
    output_lines.extend(_render_sec4(sec4))
    output_lines.append("")

    # §5 Acceptance Criteria.
    sec5 = _extract_section(content, 5)
    output_lines.append("### From spec §5 (Acceptance Criteria)")
    output_lines.extend(_render_sec5(sec5))
    output_lines.append("")

    # §6 Out of Scope.
    sec6 = _extract_section(content, 6)
    output_lines.append("### From spec §6 (Out of Scope)")
    output_lines.extend(_render_sec6(sec6))
    output_lines.append("")

    # §7 Technical Constraints.
    sec7 = _extract_section(content, 7)
    output_lines.append("### From spec §7 (Technical Constraints)")
    output_lines.extend(_render_sec7(sec7))
    output_lines.append("")

    # §8 Open Questions.
    sec8 = _extract_section(content, 8)
    output_lines.append("### From spec §8 (Open Questions)")
    output_lines.extend(_render_sec8(sec8))
    output_lines.append("")

    # §9 Risks.
    sec9 = _extract_section(content, 9)
    output_lines.append("### From spec §9 (Risks)")
    output_lines.extend(_render_sec9(sec9))

    sys.stdout.write("\n".join(output_lines) + "\n")
    return 0


# ---------------------------------------------------------------------------
# Plan parsing helpers for render-breakdown-handoff.
# ---------------------------------------------------------------------------


def _count_file_impact(plan_content: str) -> Tuple[int, int, int]:
    """Return (total_files, new_files, modified_files) from the File Impact table.

    Returns (0, 0, 0) if no File Impact table is found.
    """
    # Find the "### File Impact" section.
    fi_match = re.search(
        r"###\s+File Impact\b", plan_content, re.IGNORECASE
    )
    if not fi_match:
        return 0, 0, 0

    # Extract text from the heading to the next heading (any level >= ##) or
    # end. Using ^#{2,}\s+ stops at the next ## or ### heading so the
    # File Impact table doesn't bleed into a sibling ## Risk Assessment table.
    next_heading = re.search(
        r"^#{2,}\s+", plan_content[fi_match.end():], re.MULTILINE
    )
    if next_heading:
        fi_text = plan_content[fi_match.start():fi_match.end() + next_heading.start()]
    else:
        fi_text = plan_content[fi_match.start():]

    rows = _parse_table_rows(fi_text)
    total = 0
    new_count = 0
    modified_count = 0
    for cells in rows:
        if len(cells) < 2:
            continue
        action = cells[1].strip() if len(cells) > 1 else ""
        if re.search(r"Create|New|create|new", action):
            new_count += 1
            total += 1
        elif re.search(r"Modify|modify|Update|update", action):
            modified_count += 1
            total += 1
        elif re.search(r"Verify|verify", action):
            # Verify rows are confirm-only — count in total, not modified.
            total += 1
        else:
            total += 1
    return total, new_count, modified_count


def _count_risks(plan_content: str) -> int:
    """Return risk count from the Risk Assessment table.

    Returns 0 if no Risk Assessment table is found.
    """
    risk_match = re.search(
        r"###?\s+Risk Assessment\b", plan_content, re.IGNORECASE
    )
    if not risk_match:
        # Also try "## Risk" heading variant.
        risk_match = re.search(
            r"##\s+Risk", plan_content, re.IGNORECASE
        )
    if not risk_match:
        return 0

    # Extract text to next heading of any level >= ##. Using ^#{2,}\s+
    # stops at sibling ### headings (e.g., ### Dependencies) so their
    # tables don't leak into the Risk Assessment count.
    next_h = re.search(
        r"^#{2,}\s+", plan_content[risk_match.end():], re.MULTILINE
    )
    if next_h:
        risk_text = plan_content[risk_match.start():risk_match.end() + next_h.start()]
    else:
        risk_text = plan_content[risk_match.start():]

    rows = _parse_table_rows(risk_text)
    return len(rows)


# ---------------------------------------------------------------------------
# Subcommand: render-breakdown-handoff
# ---------------------------------------------------------------------------


def cmd_render_breakdown_handoff(args) -> int:
    """Emit the Phase 4 manual handoff block targeting /breakdown."""
    spec_path = args.spec_path
    plan_path = args.plan_path

    spec_content = _read_file(spec_path)
    if spec_content is None:
        sys.stderr.write(
            "plan_helper: cannot read spec: {0}\n".format(spec_path)
        )
        return 2

    plan_content = _read_file(plan_path)
    if plan_content is None:
        sys.stderr.write(
            "plan_helper: cannot read plan: {0}\n".format(plan_path)
        )
        return 2

    total_acs, subsections = _count_acs(spec_content)
    total_files, new_files, modified_files = _count_file_impact(plan_content)
    risk_count = _count_risks(plan_content)

    output = (
        "## Manual next step — run /breakdown\n"
        "\n"
        "The plan is approved. No automated handoff exists — restart Claude Code "
        "(exit and relaunch the CLI/app so any newly-installed command is picked up), "
        "then run:\n"
        "\n"
        "```\n"
        "/breakdown {plan_path}\n"
        "```\n"
        "\n"
        "**Plan status**: Draft — plan stays Draft until `/breakdown` runs "
        "(forward reference: `/breakdown` spec not yet ported into this framework).\n"
        "**Spec ACs**: {total_acs} criteria across {subsections} subsections\n"
        "**Plan file impact**: {total_files} files ({new_files} new, "
        "{modified_files} modified)\n"
        "**Plan risks**: {risk_count}\n"
        "\n"
        "Phase 1.5 coverage: every spec §3–§9 finding accounted for in the plan "
        "(Phase 1.5 enumeration; Phase 2.5 AC-level cross-check).\n"
    ).format(
        plan_path=plan_path,
        total_acs=total_acs,
        subsections=subsections,
        total_files=total_files,
        new_files=new_files,
        modified_files=modified_files,
        risk_count=risk_count,
    )

    sys.stdout.write(output)
    return 0


# ---------------------------------------------------------------------------
# Error helper.
# ---------------------------------------------------------------------------


def _die(msg: str, code: int = 2) -> int:
    """Write msg to stderr and return code."""
    sys.stderr.write("plan_helper: " + msg + "\n")
    return code


# ---------------------------------------------------------------------------
# Subcommand: read-specify-handoff
# ---------------------------------------------------------------------------


_SPECIFY_HANDOFF_REQUIRED_KEYS = frozenset({
    "schema_version",
    "handoff_kind",
    "spec_path",
    "specify_completed_at",
    "classification",
    "spec_seeds",
    "provenance",
    "downstream_links",
})

_PROVENANCE_KEYS = frozenset({
    "upstream_handoff_path",
    "upstream_handoff_kind",
})


def _validate_specify_handoff_dict(d: Any) -> str:
    """Return error string if d is not a valid specify-handoff dict, else empty string.

    Lightweight structural validation: checks handoff_kind constant,
    required top-level keys, and provenance sub-record keys. Does NOT
    reconstruct the full dataclass (avoids cross-module coupling; the
    shape contract is enforced here at the fields plan_helper actually
    uses).
    """
    if not isinstance(d, dict):
        return "root is not a JSON object"
    # Check all required top-level keys exist.
    missing = _SPECIFY_HANDOFF_REQUIRED_KEYS - d.keys()
    if missing:
        return "missing required fields: {0}".format(sorted(missing))
    # handoff_kind constant.
    if d.get("handoff_kind") != "specify":
        return "handoff_kind is {0!r}, expected 'specify'".format(d.get("handoff_kind"))
    # provenance must be a dict with expected keys.
    prov = d.get("provenance")
    if not isinstance(prov, dict):
        return "provenance is not a JSON object"
    missing_prov = _PROVENANCE_KEYS - prov.keys()
    if missing_prov:
        return "provenance missing fields: {0}".format(sorted(missing_prov))
    # Co-vary invariant: upstream_handoff_path and upstream_handoff_kind must
    # both be set or both be null (mirrors Provenance.__post_init__ invariant).
    path_set = bool(prov.get("upstream_handoff_path"))
    kind_set = bool(prov.get("upstream_handoff_kind"))
    if path_set != kind_set:
        return (
            "provenance.upstream_handoff_path and upstream_handoff_kind "
            "must both be set or both be null"
        )
    return ""


def cmd_read_specify_handoff(args: argparse.Namespace) -> int:
    """Resolve and validate the sibling specify handoff.json for a spec.md.

    Prints a deterministic block to stdout on success; 'no-handoff' when
    no sibling exists; dies with exit 2 on malformed sibling or missing spec.

    Output format (success):
      spec-handoff: <absolute path to handoff.json>
      spec_seeds: present
      upstream_handoff_path: <path or "none">
      upstream_handoff_kind: <kind or "none">
    """
    spec_path_raw = args.spec_path
    spec_path = Path(spec_path_raw)
    if not spec_path.is_absolute():
        spec_path = Path.cwd() / spec_path
    spec_path = spec_path.resolve()

    if not spec_path.is_file():
        return _die("spec not found: {0}".format(spec_path_raw))

    handoff_path = spec_path.parent / "handoff.json"

    if not handoff_path.exists():
        sys.stdout.write("no-handoff\n")
        return 0

    # Sibling exists — parse and validate.
    try:
        raw_text = handoff_path.read_text(encoding="utf-8")
        d = json.loads(raw_text)
    except (OSError, IOError, json.JSONDecodeError) as err:
        return _die(
            "handoff.json at {0} is malformed: {1}".format(handoff_path, err)
        )

    err_msg = _validate_specify_handoff_dict(d)
    if err_msg:
        return _die(
            "handoff.json at {0} fails specify-Handoff schema validation: {1}".format(
                handoff_path, err_msg
            )
        )

    prov = d["provenance"]
    upstream_path = prov.get("upstream_handoff_path") or None
    upstream_kind = prov.get("upstream_handoff_kind") or None

    sys.stdout.write("spec-handoff: {0}\n".format(handoff_path.resolve()))
    sys.stdout.write("spec_seeds: present\n")
    sys.stdout.write(
        "upstream_handoff_path: {0}\n".format(upstream_path if upstream_path else "none")
    )
    sys.stdout.write(
        "upstream_handoff_kind: {0}\n".format(upstream_kind if upstream_kind else "none")
    )
    return 0


# ---------------------------------------------------------------------------
# Subcommand: render-plan-seeds
# ---------------------------------------------------------------------------


def _render_research_plan_seeds(upstream_path: str, d: Dict[str, Any]) -> str:
    """Render the plan-seeds block for a research upstream handoff.

    All plan_seeds fields are represented. Lists render as bullet entries
    (one line each). Empty lists render as '- (none)'.
    """
    ps = d.get("plan_seeds", {}) or {}

    rec_id = ps.get("recommended_approach_id", "(unset)")
    rec_summary = ps.get("recommended_approach_summary", "(unset)")
    layer_dest = ps.get("layer_destination", "(unset)")
    layer_just = ps.get("layer_justification", "(unset)")
    call_shape = ps.get("proposed_call_shape") or "(none)"

    # Complexity.
    complexity = ps.get("complexity") or {}
    if isinstance(complexity, dict):
        complexity_str = "changes={0}, risk={1}, verify_cost={2}".format(
            complexity.get("changes", "?"),
            complexity.get("risk", "?"),
            complexity.get("verify_cost", "?"),
        )
    else:
        complexity_str = str(complexity)

    # Alternatives considered.
    alts = ps.get("alternatives_considered") or []
    if alts:
        alt_lines = []
        for alt in alts:
            if isinstance(alt, dict):
                alt_lines.append(
                    "- {0}: {1} (rejected: {2})".format(
                        alt.get("id", "?"),
                        alt.get("summary", "?"),
                        alt.get("rejected_reason", "?"),
                    )
                )
            else:
                alt_lines.append("- {0}".format(alt))
        alts_block = "\n".join(alt_lines)
    else:
        alts_block = "- (none)"

    # Cited canonical patterns.
    patterns = ps.get("cited_canonical_patterns") or []
    if patterns:
        pat_lines = []
        for pat in patterns:
            if isinstance(pat, dict):
                pat_lines.append(
                    "- {0} ({1})".format(pat.get("qn", "?"), pat.get("file_line", "?"))
                )
            else:
                pat_lines.append("- {0}".format(pat))
        patterns_block = "\n".join(pat_lines)
    else:
        patterns_block = "- (none)"

    return (
        "## Upstream plan-seeds (research handoff: {upstream_path})\n"
        "\n"
        "**Recommended approach**: {rec_id} — {rec_summary}\n"
        "**Layer**: {layer_dest} — {layer_just}\n"
        "**Complexity**: {complexity_str}\n"
        "**Proposed call shape**: {call_shape}\n"
        "\n"
        "**Alternatives considered**:\n"
        "{alts_block}\n"
        "\n"
        "**Cited canonical patterns**:\n"
        "{patterns_block}\n"
    ).format(
        upstream_path=upstream_path,
        rec_id=rec_id,
        rec_summary=rec_summary,
        layer_dest=layer_dest,
        layer_just=layer_just,
        complexity_str=complexity_str,
        call_shape=call_shape,
        alts_block=alts_block,
        patterns_block=patterns_block,
    )


def _render_discover_plan_seeds(upstream_path: str, d: Dict[str, Any]) -> str:
    """Render the plan-seeds block for a discover upstream handoff.

    All plan_seeds fields are represented. Lists render as bullet entries
    (one line each). Empty lists render as '- (none)'.
    """
    ps = d.get("plan_seeds", {}) or {}

    rec_id = ps.get("recommended_option_id") or "(none)"
    rec_rationale = ps.get("recommended_option_rationale", "(unset)")

    # Build vs buy.
    bvb = ps.get("build_vs_buy") or {}
    if isinstance(bvb, dict):
        bvb_str = "recommendation={0}, build={1}, buy={2}, reasoning={3}".format(
            bvb.get("recommendation", "?"),
            bvb.get("build_path", "?"),
            bvb.get("buy_path", "?"),
            bvb.get("reasoning", "?"),
        )
    else:
        bvb_str = str(bvb)

    # Complexity.
    complexity = ps.get("complexity") or {}
    if isinstance(complexity, dict):
        complexity_str = "changes={0}, risk={1}, verify_cost={2}".format(
            complexity.get("changes", "?"),
            complexity.get("risk", "?"),
            complexity.get("verify_cost", "?"),
        )
    else:
        complexity_str = str(complexity)

    # Design options.
    opts = ps.get("design_options") or []
    if opts:
        opt_lines = []
        for opt in opts:
            if isinstance(opt, dict):
                opt_lines.append(
                    "- {0}: {1} (shape: {2}, complexity: {3})".format(
                        opt.get("id", "?"),
                        opt.get("name", "?"),
                        opt.get("shape", "?"),
                        opt.get("complexity", "?"),
                    )
                )
            else:
                opt_lines.append("- {0}".format(opt))
        opts_block = "\n".join(opt_lines)
    else:
        opts_block = "- (none)"

    # Cited canonical patterns.
    patterns = ps.get("cited_canonical_patterns") or []
    if patterns:
        pat_lines = []
        for pat in patterns:
            if isinstance(pat, dict):
                pat_lines.append(
                    "- {0} ({1}) [{2}]".format(
                        pat.get("reference", "?"),
                        pat.get("kind", "?"),
                        pat.get("source", "?"),
                    )
                )
            else:
                pat_lines.append("- {0}".format(pat))
        patterns_block = "\n".join(pat_lines)
    else:
        patterns_block = "- (none)"

    return (
        "## Upstream plan-seeds (discover handoff: {upstream_path})\n"
        "\n"
        "**Recommended option**: {rec_id} — {rec_rationale}\n"
        "**Build vs buy**: {bvb_str}\n"
        "**Complexity**: {complexity_str}\n"
        "\n"
        "**Design options**:\n"
        "{opts_block}\n"
        "\n"
        "**Cited canonical patterns**:\n"
        "{patterns_block}\n"
    ).format(
        upstream_path=upstream_path,
        rec_id=rec_id,
        rec_rationale=rec_rationale,
        bvb_str=bvb_str,
        complexity_str=complexity_str,
        opts_block=opts_block,
        patterns_block=patterns_block,
    )


def cmd_render_consultation_block(args: argparse.Namespace) -> int:
    """Emit the content under the '## Specialist Consultation' heading.

    Takes no arguments. Prints the intro paragraph, the five-column table,
    and the verdict-enum rule to stdout. The heading itself is NOT emitted —
    the plan.md template already contains '## Specialist Consultation' and the
    orchestrator copies this helper's stdout into that section; emitting the
    heading here would produce a duplicate.

    The block includes:
      - An intro paragraph explaining the table's purpose and the no-relay fallback.
      - A markdown table with five fixed columns.
      - A rule line enumerating the verdict enum and the Cites requirement.
      - An empty-state (none) row.

    Exit 0 always (no inputs to fail on).
    """
    block = (
        "Record one row per specialist consulted during planning. "
        "The architect is the decision-authority and synthesizer; "
        "specialists supply domain input only. "
        "If a consult was requested but no response was relayed, record that too "
        "(use Verdict `no-response`). "
        "If NO specialists were consulted on this plan, keep the single `(none)` row below.\n"
        "\n"
        "| Specialist | Sub-question | Input summary | Verdict | Cites |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| db-engineer | <the specific sub-question> | <1-line summary of their input> | accepted | <file:line or doc ref> |\n"
        "| (none) | — | — | — | — |\n"
        "\n"
        "**Verdict** must be one of: `accepted` / `modified` / `rejected` / `no-response`. "
        "Every row requires a **Cites** entry: file:line, doc section, or `own-reasoning`.\n"
    )
    sys.stdout.write(block)
    return 0


def cmd_render_plan_seeds(args: argparse.Namespace) -> int:
    """Render a structured plan-seeds block from the upstream research/discover handoff.

    Reads the specify-handoff at the given path, follows
    provenance.upstream_handoff_path to the upstream handoff, dispatches on
    handoff_kind ('research' or 'discover'), and emits a deterministic block.

    Outputs 'cold-no-plan-seeds' and exits 0 when upstream_handoff_path is
    null/empty (cold path — manual /specify without upstream). Dies exit 2 on
    missing upstream file or unknown handoff_kind.
    """
    specify_handoff_path_raw = args.specify_handoff_path
    specify_handoff_path = Path(specify_handoff_path_raw)
    if not specify_handoff_path.is_absolute():
        specify_handoff_path = Path.cwd() / specify_handoff_path
    specify_handoff_path = specify_handoff_path.resolve()

    # Read the specify handoff.
    try:
        raw_text = specify_handoff_path.read_text(encoding="utf-8")
        specify_d = json.loads(raw_text)
    except FileNotFoundError:
        return _die("specify-handoff not found: {0}".format(specify_handoff_path_raw))
    except (OSError, IOError, json.JSONDecodeError) as err:
        return _die(
            "cannot read specify-handoff at {0}: {1}".format(
                specify_handoff_path_raw, err
            )
        )

    # Extract upstream_handoff_path from provenance.
    prov = specify_d.get("provenance") or {}
    upstream_path_raw = prov.get("upstream_handoff_path") or None

    if not upstream_path_raw:
        sys.stdout.write("cold-no-plan-seeds\n")
        return 0

    # Resolve upstream path (may be relative to the repo root / cwd).
    upstream_path = Path(upstream_path_raw)
    if not upstream_path.is_absolute():
        upstream_path = Path.cwd() / upstream_path
    upstream_path = upstream_path.resolve()

    if not upstream_path.exists():
        return _die(
            "upstream handoff not found: {0}".format(upstream_path_raw)
        )

    # Read and parse the upstream handoff.
    try:
        raw_upstream = upstream_path.read_text(encoding="utf-8")
        upstream_d = json.loads(raw_upstream)
    except (OSError, IOError, json.JSONDecodeError) as err:
        return _die(
            "cannot read upstream handoff at {0}: {1}".format(upstream_path_raw, err)
        )

    # Kind dispatch: prefer provenance.upstream_handoff_kind from the SPECIFY
    # handoff (authoritative, set by specify's import-handoff), since the
    # research handoff schema predates the handoff_kind field convention and
    # does not include it at the top level. Fall back to upstream's own
    # handoff_kind field for forward-compatibility if provenance kind is absent.
    handoff_kind = (
        prov.get("upstream_handoff_kind")
        or upstream_d.get("handoff_kind", "")
    )

    if handoff_kind == "research":
        block = _render_research_plan_seeds(str(upstream_path_raw), upstream_d)
    elif handoff_kind == "discover":
        block = _render_discover_plan_seeds(str(upstream_path_raw), upstream_d)
    else:
        return _die(
            "upstream handoff at {0} has unknown handoff_kind={1!r}; "
            "expected 'research' or 'discover'".format(upstream_path_raw, handoff_kind)
        )

    sys.stdout.write(block)
    return 0


# ---------------------------------------------------------------------------
# Plan parsing helpers for finalize-handoff.
# ---------------------------------------------------------------------------

# Placeholder patterns: cells whose first value matches these are skipped.
# Covers: [path], [decision], [risk], [any bracketed placeholder], _(none)_, (none).
# NOTE: angle-bracket placeholders (<...>) are NOT covered here —
# _parse_specialist_consultation handles them inline on the sub_question column.
_PLACEHOLDER_CELL_RE = re.compile(
    r"^\s*(?:"
    r"\[.*\]"           # any [bracketed] placeholder
    r"|_\(none\)_"      # _(none)_ markdown italic
    r"|\(none\)"        # bare (none)
    r")\s*$"
)


def _is_placeholder_cell(text: str) -> bool:
    """Return True if text is a placeholder that should be skipped.

    The regex anchors (^\\s* and \\s*$) handle surrounding whitespace;
    no additional strip() at call sites is required.
    """
    return bool(_PLACEHOLDER_CELL_RE.match(text))


def _extract_plan_section(content: str, heading_pattern: re.Pattern) -> str:
    """Extract text of the section whose heading matches heading_pattern.

    Returns text from the heading line to the next ## or ### heading or EOF.
    Returns empty string when the heading is not found.
    """
    m = heading_pattern.search(content)
    if not m:
        return ""
    start = m.start()
    # Find next ## or ### heading at the same or higher level.
    next_h = re.compile(r"^#{2,}\s+", re.MULTILINE)
    m_next = next_h.search(content, m.end())
    if m_next:
        return content[start:m_next.start()]
    return content[start:]


def _parse_layer_map(plan_content: str) -> List[Any]:
    """Parse ### Layer Map table rows into LayerRow records.

    Columns: Layer | What | Files (existing or new).
    Skips placeholder rows. Returns empty list when section absent.
    """
    from _plan.handoff_schema import LayerRow

    pat = re.compile(r"^###\s+Layer Map\b", re.MULTILINE | re.IGNORECASE)
    section = _extract_plan_section(plan_content, pat)
    if not section:
        return []

    rows = _parse_table_rows(section)
    result = []
    for cells in rows:
        if not cells:
            continue
        layer = cells[0] if len(cells) > 0 else ""
        what = cells[1] if len(cells) > 1 else ""
        files = cells[2] if len(cells) > 2 else ""
        # Skip placeholder rows.
        if _is_placeholder_cell(layer):
            continue
        try:
            result.append(LayerRow(layer=layer, what=what, files=files))
        except (TypeError, ValueError):
            continue  # skip malformed rows without crashing
    return result


def _parse_key_design_decisions(plan_content: str) -> List[Any]:
    """Parse ### Key Design Decisions table rows into DecisionRow records.

    Columns: Decision | Chosen Approach | Why | Alternatives Rejected.
    Skips placeholder rows. Returns empty list when section absent.
    """
    from _plan.handoff_schema import DecisionRow

    pat = re.compile(r"^###\s+Key Design Decisions\b", re.MULTILINE | re.IGNORECASE)
    section = _extract_plan_section(plan_content, pat)
    if not section:
        return []

    rows = _parse_table_rows(section)
    result = []
    for cells in rows:
        if not cells:
            continue
        decision = cells[0] if len(cells) > 0 else ""
        chosen = cells[1] if len(cells) > 1 else ""
        why = cells[2] if len(cells) > 2 else ""
        alts = cells[3] if len(cells) > 3 else ""
        if _is_placeholder_cell(decision):
            continue
        try:
            result.append(
                DecisionRow(
                    decision=decision,
                    chosen_approach=chosen,
                    why=why,
                    alternatives_rejected=alts,
                )
            )
        except (TypeError, ValueError):
            continue
    return result


def _parse_file_impact_rows(plan_content: str) -> List[Any]:
    """Parse ### File Impact table rows into FileImpactRow records.

    Columns: File | Action | What Changes.
    Uses _extract_plan_section to locate the section boundary.
    Skips placeholder rows. Returns empty list when section absent.
    """
    from _plan.handoff_schema import FileImpactRow

    pat = re.compile(r"^###\s+File Impact\b", re.MULTILINE | re.IGNORECASE)
    section = _extract_plan_section(plan_content, pat)
    if not section:
        return []

    rows = _parse_table_rows(section)
    result = []
    for cells in rows:
        if not cells:
            continue
        file_ = cells[0] if len(cells) > 0 else ""
        action = cells[1] if len(cells) > 1 else ""
        what = cells[2] if len(cells) > 2 else ""
        if _is_placeholder_cell(file_):
            continue
        try:
            result.append(
                FileImpactRow(file=file_, action=action, what_changes=what)
            )
        except (TypeError, ValueError):
            continue
    return result


def _parse_doc_impact_rows(plan_content: str) -> List[Any]:
    """Parse ### Documentation Impact table rows into DocImpactRow records.

    Columns: Doc File | Action | What Changes.
    Skips placeholder rows. Returns empty list when section absent.
    """
    from _plan.handoff_schema import DocImpactRow

    pat = re.compile(r"^###\s+Documentation Impact\b", re.MULTILINE | re.IGNORECASE)
    section = _extract_plan_section(plan_content, pat)
    if not section:
        return []

    rows = _parse_table_rows(section)
    result = []
    for cells in rows:
        if not cells:
            continue
        doc_file = cells[0] if len(cells) > 0 else ""
        action = cells[1] if len(cells) > 1 else ""
        what = cells[2] if len(cells) > 2 else ""
        if _is_placeholder_cell(doc_file):
            continue
        try:
            result.append(
                DocImpactRow(doc_file=doc_file, action=action, what_changes=what)
            )
        except (TypeError, ValueError):
            continue
    return result


def _parse_risk_rows(plan_content: str) -> List[Any]:
    """Parse ## Risk Assessment table rows into RiskRow records.

    Columns: Risk | Likelihood | Impact | Mitigation.
    Uses _extract_plan_section to locate the section boundary.
    Matches both '## Risk Assessment' and '### Risk Assessment' heading forms.
    Skips placeholder rows. Returns empty list when section absent.
    """
    from _plan.handoff_schema import RiskRow

    # Try the primary heading form first (## or ### Risk Assessment).
    pat = re.compile(r"^###?\s+Risk Assessment\b", re.MULTILINE | re.IGNORECASE)
    section = _extract_plan_section(plan_content, pat)
    if not section:
        # Fall back to bare '## Risk' variant.
        pat = re.compile(r"^##\s+Risk\b", re.MULTILINE | re.IGNORECASE)
        section = _extract_plan_section(plan_content, pat)
    if not section:
        return []

    rows = _parse_table_rows(section)
    result = []
    for cells in rows:
        if not cells:
            continue
        risk = cells[0] if len(cells) > 0 else ""
        likelihood = cells[1] if len(cells) > 1 else ""
        impact = cells[2] if len(cells) > 2 else ""
        mitigation = cells[3] if len(cells) > 3 else ""
        if _is_placeholder_cell(risk):
            continue
        try:
            result.append(
                RiskRow(
                    risk=risk,
                    likelihood=likelihood,
                    impact=impact,
                    mitigation=mitigation,
                )
            )
        except (TypeError, ValueError):
            continue
    return result


# Accepted verdict values for specialist consultation rows.
_CONSULT_VERDICT_VALUES = frozenset({"accepted", "modified", "rejected", "no-response"})

# "(none)" placeholder for specialist consultation: the no-consult sentinel row.
_CONSULT_NONE_SPECIALIST_RE = re.compile(r"^\s*\(none\)\s*$")


def _parse_specialist_consultation(plan_content: str) -> List[Any]:
    """Parse ## Specialist Consultation table rows into ConsultRow records.

    Columns: Specialist | Sub-question | Input summary | Verdict | Cites.
    Verdict values: accepted / modified / rejected / no-response.
    Skips the (none) sentinel row and rows with placeholder/invalid verdicts.
    Also skips the example placeholder row emitted by render-consultation-block.
    Returns empty list when section absent or all rows are placeholders.
    """
    from _plan.handoff_schema import ConsultRow

    pat = re.compile(r"^##\s+Specialist Consultation\b", re.MULTILINE | re.IGNORECASE)
    section = _extract_plan_section(plan_content, pat)
    if not section:
        return []

    rows = _parse_table_rows(section)
    result = []
    for cells in rows:
        if not cells:
            continue
        specialist = cells[0] if len(cells) > 0 else ""
        sub_q = cells[1] if len(cells) > 1 else ""
        summary = cells[2] if len(cells) > 2 else ""
        verdict = cells[3] if len(cells) > 3 else ""
        cites = cells[4] if len(cells) > 4 else ""
        # Skip the (none) sentinel row.
        if _CONSULT_NONE_SPECIALIST_RE.match(specialist):
            continue
        # Skip placeholder rows.
        if _is_placeholder_cell(specialist):
            continue
        # Skip rows with angle-bracket placeholder sub-questions (template row).
        if sub_q.startswith("<") and sub_q.endswith(">"):
            continue
        # Skip rows with invalid verdict values (includes placeholder "-").
        if verdict not in _CONSULT_VERDICT_VALUES:
            continue
        try:
            result.append(
                ConsultRow(
                    specialist=specialist,
                    sub_question=sub_q,
                    input_summary=summary,
                    verdict=verdict,
                    cites=cites,
                )
            )
        except (TypeError, ValueError):
            continue
    return result


def _parse_dependencies(plan_content: str) -> List[str]:
    """Parse ## Dependencies section into a list of non-blank content lines.

    Captures all non-blank, non-heading lines under ## Dependencies.
    Returns empty list when the section is absent or contains only
    the template placeholder ("Any external dependencies: ...").
    """
    pat = re.compile(r"^##\s+Dependencies\b", re.MULTILINE | re.IGNORECASE)
    section = _extract_plan_section(plan_content, pat)
    if not section:
        return []

    lines = []
    for raw_line in section.splitlines():
        stripped = raw_line.strip()
        # Skip the heading line itself.
        if re.match(r"^##\s+Dependencies", stripped, re.IGNORECASE):
            continue
        # Skip blank lines.
        if not stripped:
            continue
        # Skip pure template placeholder text.
        if stripped.startswith("[Any external dependencies") or stripped.startswith("[any external"):
            continue
        lines.append(stripped)
    return lines


def _resolve_sibling_specify_handoff(plan_dir: Path) -> Optional[str]:
    """Return path to the sibling specify handoff.json if it is valid, else None.

    'Valid' means: exists, parses as JSON, has handoff_kind == 'specify'.
    Does NOT do full schema validation — just enough to confirm it is the
    sibling specify handoff and not a different artefact.
    """
    candidate = plan_dir / "handoff.json"
    if not candidate.exists():
        return None
    try:
        raw = candidate.read_text(encoding="utf-8")
        d = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(d, dict):
        return None
    if d.get("handoff_kind") != "specify":
        return None
    return str(candidate.resolve())


def _asdict_handoff(handoff: Any) -> Dict[str, Any]:
    """Serialize a plan Handoff dataclass to a plain JSON-ready dict.

    Uses dataclasses.asdict recursively to flatten nested dataclasses.
    Lists of dataclasses are converted to lists of dicts.
    """
    import dataclasses as _dc
    return _dc.asdict(handoff)


def _atomic_write_json_plan(data: Dict[str, Any], target: Path) -> None:
    """Atomically write data as JSON to target.

    Uses tempfile.mkstemp + os.replace.  Cleans up temp on failure.
    """
    fd, tmp_path = tempfile.mkstemp(
        prefix="plan-handoff-",
        suffix=".json.tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=False)
            f.write("\n")
        os.replace(tmp_path, str(target))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Subcommand: finalize-handoff
# ---------------------------------------------------------------------------


def cmd_finalize_handoff(args: argparse.Namespace) -> int:
    """Parse plan.md -> build Handoff -> validate -> write plan-handoff.json.

    Sections parsed (in order):
      Layer Map, Key Design Decisions, File Impact, Documentation Impact,
      Risk Assessment, Specialist Consultation, Dependencies.
    Placeholder rows are skipped transparently.

    Provenance:
      Resolves the sibling specify handoff.json (same directory as plan.md).
      If present and valid (handoff_kind == 'specify'), sets
        upstream_handoff_path = absolute path
        upstream_handoff_kind = 'specify'
      Else both None.
      spec_path: sibling spec.md if it exists, else None.

    Output: <plan-dir>/plan-handoff.json (sibling to plan.md, separate from
    the specify handoff.json which carries handoff_kind='specify').

    Idempotent: re-running overwrites the previous plan-handoff.json.
    """
    # _plan.handoff_schema imports -- done inside the function to avoid
    # circular import if plan_helper is imported from tests that import
    # _plan submodules separately.
    _lib_dir = Path(__file__).resolve().parent
    if str(_lib_dir) not in sys.path:
        sys.path.insert(0, str(_lib_dir))

    from _plan.handoff_schema import (
        BreakdownSeeds,
        Handoff,
        Provenance,
        SCHEMA_VERSION,
        HANDOFF_KIND,
    )

    plan_path_raw = args.plan_path
    plan_path = Path(plan_path_raw)
    if not plan_path.is_absolute():
        plan_path = Path.cwd() / plan_path
    plan_path = plan_path.resolve()

    if not plan_path.is_file():
        return _die("plan not found: {0}".format(plan_path_raw))

    plan_content = _read_file(str(plan_path))
    if plan_content is None:
        return _die("cannot read plan: {0}".format(plan_path_raw))

    plan_dir = plan_path.parent

    # Resolve plan_completed_at.
    completed_at_raw = getattr(args, "completed_at", None)
    if completed_at_raw:
        plan_completed_at = completed_at_raw.strip()
    else:
        plan_completed_at = (
            datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        )

    # Build BreakdownSeeds by parsing each section.
    layer_map = _parse_layer_map(plan_content)
    key_design_decisions = _parse_key_design_decisions(plan_content)
    file_impact = _parse_file_impact_rows(plan_content)
    doc_impact = _parse_doc_impact_rows(plan_content)
    risks = _parse_risk_rows(plan_content)
    specialist_consultation = _parse_specialist_consultation(plan_content)
    dependencies = _parse_dependencies(plan_content)

    try:
        breakdown_seeds = BreakdownSeeds(
            layer_map=layer_map,
            key_design_decisions=key_design_decisions,
            file_impact=file_impact,
            doc_impact=doc_impact,
            risks=risks,
            specialist_consultation=specialist_consultation,
            dependencies=dependencies,
        )
    except (TypeError, ValueError) as err:
        return _die(
            "finalize-handoff: schema validation failed building BreakdownSeeds: {0}".format(err)
        )

    # Resolve provenance.
    sibling_specify_path = _resolve_sibling_specify_handoff(plan_dir)
    if sibling_specify_path is not None:
        upstream_handoff_path = sibling_specify_path  # type: Optional[str]
        upstream_handoff_kind = "specify"              # type: Optional[str]
    else:
        upstream_handoff_path = None
        upstream_handoff_kind = None

    # spec_path: sibling spec.md if it exists.
    sibling_spec = plan_dir / "spec.md"
    spec_path_val = str(sibling_spec.resolve()) if sibling_spec.is_file() else None

    try:
        provenance = Provenance(
            upstream_handoff_path=upstream_handoff_path,
            upstream_handoff_kind=upstream_handoff_kind,
            spec_path=spec_path_val,
        )
    except (TypeError, ValueError) as err:
        return _die(
            "finalize-handoff: schema validation failed building Provenance: {0}".format(err)
        )

    try:
        handoff = Handoff(
            schema_version=SCHEMA_VERSION,
            handoff_kind=HANDOFF_KIND,
            plan_path=str(plan_path),
            plan_completed_at=plan_completed_at,
            provenance=provenance,
            breakdown_seeds=breakdown_seeds,
        )
    except (TypeError, ValueError) as err:
        return _die(
            "finalize-handoff: schema validation failed: {0}".format(err)
        )

    # Write plan-handoff.json as sibling to plan.md.
    target = plan_dir / "plan-handoff.json"
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_json_plan(_asdict_handoff(handoff), target)
    except OSError as err:
        sys.stderr.write(
            "plan_helper: finalize-handoff: cannot write {0}: {1}\n".format(
                target, err
            )
        )
        return 1

    sys.stdout.write("{0}\n".format(target.resolve()))
    return 0


# ---------------------------------------------------------------------------
# CLI wiring.
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="plan_helper",
        description=(
            "Structural emission helper for the /plan slash command. "
            "Helper owns shape; LLM composes values."
        ),
    )
    sub = parser.add_subparsers(dest="subcommand")

    # pick-spec
    sp = sub.add_parser(
        "pick-spec",
        help="Resolve which spec to plan against (auto-picks by mtime if no path given).",
    )
    sp.add_argument(
        "path",
        nargs="?",
        default=None,
        help="Explicit path to a spec.md (optional).",
    )
    sp.set_defaults(func=cmd_pick_spec)

    # render-pick-summary
    sp = sub.add_parser(
        "render-pick-summary",
        help="Print a 5-line deterministic spec summary block.",
    )
    sp.add_argument("spec_path", help="Path to spec.md.")
    sp.set_defaults(func=cmd_render_pick_summary)

    # list-specs
    sp = sub.add_parser(
        "list-specs",
        help="List all specs/*/spec.md sorted by mtime desc.",
    )
    sp.set_defaults(func=cmd_list_specs)

    # check-status-and-flip
    sp = sub.add_parser(
        "check-status-and-flip",
        help="Flip spec Status from Draft to Approved (idempotent).",
    )
    sp.add_argument("spec_path", help="Path to spec.md.")
    sp.set_defaults(func=cmd_check_status_and_flip)

    # render-findings-from-spec
    sp = sub.add_parser(
        "render-findings-from-spec",
        help="Emit Phase 1.5 findings skeleton from spec §3-§9.",
    )
    sp.add_argument("spec_path", help="Path to spec.md.")
    sp.set_defaults(func=cmd_render_findings_from_spec)

    # render-breakdown-handoff
    sp = sub.add_parser(
        "render-breakdown-handoff",
        help="Emit Phase 4 manual handoff block targeting /breakdown.",
    )
    sp.add_argument("spec_path", help="Path to spec.md.")
    sp.add_argument("plan_path", help="Path to plan.md.")
    sp.set_defaults(func=cmd_render_breakdown_handoff)

    # read-specify-handoff
    sp = sub.add_parser(
        "read-specify-handoff",
        help=(
            "Resolve and validate the sibling specify handoff.json for a spec.md. "
            "Prints a 4-line block on success, 'no-handoff' when none exists, "
            "exits 2 on malformed sibling or missing spec."
        ),
    )
    sp.add_argument("spec_path", help="Path to spec.md.")
    sp.set_defaults(func=cmd_read_specify_handoff)

    # render-consultation-block
    sp = sub.add_parser(
        "render-consultation-block",
        help=(
            "Emit the content under '## Specialist Consultation' (intro + table + rule). "
            "Heading is NOT emitted — template owns it. No arguments required."
        ),
    )
    sp.set_defaults(func=cmd_render_consultation_block)

    # render-plan-seeds
    sp = sub.add_parser(
        "render-plan-seeds",
        help=(
            "Render structured plan-seeds block from the upstream research/discover "
            "handoff referenced by a specify-handoff. Prints 'cold-no-plan-seeds' "
            "when provenance.upstream_handoff_path is null."
        ),
    )
    sp.add_argument(
        "specify_handoff_path",
        help="Path to the specify handoff.json (specs/NNN-slug/handoff.json).",
    )
    sp.set_defaults(func=cmd_render_plan_seeds)

    # finalize-handoff
    sp = sub.add_parser(
        "finalize-handoff",
        help=(
            "Parse plan.md into structured breakdown_seeds and write "
            "plan-handoff.json as a sibling to plan.md. "
            "Provenance resolves the sibling specify handoff.json when present."
        ),
    )
    sp.add_argument(
        "plan_path",
        help="Path to plan.md (specs/NNN-slug/plan.md).",
    )
    sp.add_argument(
        "--completed-at",
        default=None,
        dest="completed_at",
        help="UTC ISO-8601 timestamp for plan_completed_at (default: now).",
    )
    sp.set_defaults(func=cmd_finalize_handoff)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "func", None) is None:
        parser.print_help(sys.stderr)
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
