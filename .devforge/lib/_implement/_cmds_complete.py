"""_cmds_complete -- mark-complete verb for implement_helper.

Mark a task file as Complete, tick its Done-When checkboxes, fill Completion
Notes, and update the matching row in tasks/README.md.

Algorithm
---------
1. In tasks/<NNN>.md:
   a. Replace `**Status**: <anything>` with `**Status**: Complete`.
   b. Process every checkbox in the `## Done When` section (from the heading
      until the next `## ` heading or EOF).  Each box is handled as follows:
        - If the box line matches any substring in --unverified-box: force the
          box UNticked (`- [ ]`) and append the unverified annotation if not
          already present (idempotent).
        - Otherwise: force the box ticked (`- [x]`) and strip the annotation if
          present (handles the repair → now-verified case).
      When --unverified-box is not supplied (the default), all boxes are ticked
      and no annotations are added.  Byte-identical to the previous behavior for
      files with no prior annotations; for files where a prior run annotated a
      ``- [x]`` box, the annotation is stripped on a clean re-run (the intended
      repair behavior).
   c. Fill Completion Notes: replace the skeleton lines with real values
      supplied via args:
        [Filled in by /implement after completion] → (removed / replaced)
        **Completed**: [date/time]    → **Completed**: <completed_at>
        **Files changed**: [actual files] → **Files changed**: <files list>
        **Contract**: Expects [X/Y verified] | Produces [X/Y verified]
               → **Contract**: Expects <expects_met> | Produces <produces_met>
        **Notes**: [deviations or observations] → **Notes**: <notes>
2. In tasks/README.md:
   - Find the row matching the task number in the `## Task Index` table and
     rewrite its Status cell from whatever it was to `Complete`.

Arguments (argparse):
  --task-file      <path>   Required. Path to the task .md file.
  --index          <path>   Required. Path to tasks/README.md.
  --number         <str>    Required. Task number (e.g. "001").
  --files          <json>   Optional. JSON array of files changed (for
                            Completion Notes "Files changed" line). Default: [].
  --expects-met    <str>    Optional. Expects fraction, e.g. "2/2". Default "".
  --produces-met   <str>    Optional. Produces fraction, e.g. "2/2". Default "".
  --notes          <str>    Optional. Deviation / observation notes. Default "".
  --completed-at   <str>    Optional. Timestamp string. If absent, the helper
                            stamps with the current UTC time (ISO format).
                            Pass an explicit value in tests for determinism.
  --unverified-box <str>    Optional, repeatable. A substring identifying a
                            Done-When condition that was NOT mechanically
                            verified (e.g. the type-check / lint gate when
                            verify-touched did not return pass). Matching
                            box(es) are left unticked and annotated instead of
                            ticked. Substrings should be specific enough to
                            identify the intended box. Default: none (all boxes
                            ticked, unchanged behavior).
  --root           <path>   Optional. Not used by mark-complete directly but
                            present for CLI consistency.

Emitted JSON (stdout, exit 0):
  {"marked": true}

Exit codes:
  0 — marked successfully.
  1 — I/O error reading or writing files.
  2 — task file or index not found / parse error.

Design notes:
- Status line pattern: `**Status**: <value>` (per storage-rules.md and the
  exact format emitted by `breakdown_helper render-task-file`).
- Done-When ticking: by default, all boxes in the `## Done When` section are
  ticked (the approve path implies all conditions were verified). The caller
  may supply --unverified-box <substring> (repeatable) to mark specific
  conditions as not mechanically verified; those boxes are left unticked and
  annotated with `_UNVERIFIED_ANNOTATION` so they are visibly honest instead
  of falsely green. The function processes both `- [ ]` and `- [x]` forms so
  it is idempotent across repair re-runs.
- Completion Notes filling: uses exact heading text from the storage-rules.md
  skeleton (`[Filled in by /implement after completion]` placeholder line;
  exact **Key**: [placeholder] patterns). Only the Completion Notes section
  (from `## Completion Notes` until EOF or next `##`) is rewritten.
- README.md row update: the Task Index table row has format
    `| NNN | ... | ... | ... | <Status> |`
  The helper replaces only the Status cell in the matching row.
- Atomic writes for both files (tempfile.mkstemp + os.replace).
- --completed-at injected by caller for test determinism; falls back to
  UTC timestamp if absent.

Stdlib only. Python 3.8+.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXIT_OK = 0
EXIT_ERR = 1
EXIT_FINDINGS = 2

# Pattern to match the **Status**: line.
# Group 1 = prefix ("**Status**: "), group 2 = current value.
# _set_status uses: replacement = m.group(1) + new_status
#   → preserves the prefix exactly (group 1) and overwrites only the value.
#
# IMPORTANT: uses [ \t]* (horizontal whitespace only) inside group 1, NOT \s*.
# The status value MUST appear on the same line as the **Status**: marker.
# Using \s* would allow the match to bleed across a blank line and capture a
# value from the next non-empty line in a malformed task file (e.g.
# "**Status**:\n\nComplete\n" would wrongly match "Complete").
# On a well-formed line ("**Status**: Pending"), group 1 = "**Status**: "
# and the replacement still reconstructs "**Status**: Complete" correctly.
_STATUS_PATTERN = re.compile(r"^(\*\*Status\*\*:[ \t]*)(.+)$", re.MULTILINE)

# Pattern to match an unticked Done-When checkbox.
_UNCHECKED_BOX = re.compile(r"^(- \[ \] .*)$", re.MULTILINE)

# Pattern to match any Done-When checkbox line (ticked or unticked).
_ANY_BOX = re.compile(r"^(- \[[ x]\] .*)$", re.MULTILINE)

# Annotation appended to boxes that were not mechanically verified.
# Leading space is intentional; em-dash (—) is a literal Unicode character.
_UNVERIFIED_ANNOTATION = " _(unverified — see Completion Notes)_"

# Pattern to find the start of the Done When section.
_DONE_WHEN_HEADING = re.compile(r"^## Done When\s*$", re.MULTILINE)

# Pattern to find the start of the Completion Notes section.
_COMPLETION_NOTES_HEADING = re.compile(r"^## Completion Notes\s*$", re.MULTILINE)

# Pattern to find next ## heading.
_NEXT_SECTION = re.compile(r"^## ", re.MULTILINE)


# ---------------------------------------------------------------------------
# Atomic write helper
# ---------------------------------------------------------------------------


def _atomic_write(target_path, content, prefix="mark-complete-"):
    # type: (Path, str, str) -> None
    """Atomically overwrite target_path with content."""
    fd, tmp_path = tempfile.mkstemp(
        prefix=prefix,
        suffix=".tmp",
        dir=str(target_path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, str(target_path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Task file mutation helpers
# ---------------------------------------------------------------------------


def _set_status(text, new_status):
    # type: (str, str) -> str
    """Replace the **Status**: line value with ``new_status``.

    When no Status line is found, one is inserted after the first non-blank
    line (same behaviour as the original _set_status_complete).  Idempotent:
    if the Status line already carries ``new_status``, the text is unchanged.
    """
    def _replacer(m):
        return m.group(1) + new_status
    new_text, count = _STATUS_PATTERN.subn(_replacer, text)
    if count == 0:
        # No Status line found: append one after the first non-blank line.
        lines = text.splitlines(keepends=True)
        out = []
        inserted = False
        for line in lines:
            out.append(line)
            if not inserted and line.strip():
                out.append("**Status**: {0}\n".format(new_status))
                inserted = True
        return "".join(out)
    return new_text


def _set_status_complete(text):
    # type: (str) -> str
    """Replace the **Status**: line value with 'Complete'."""
    return _set_status(text, "Complete")


def _tick_done_when_boxes(text, unverified_substrings=None):
    # type: (str, object) -> str
    """Process all checkboxes inside the `## Done When` section.

    Only checkboxes between the `## Done When` heading and the next
    `## ` heading (or EOF) are touched. Checkboxes in other sections
    are not modified.

    Parameters
    ----------
    text : str
        Full task file text.
    unverified_substrings : list of str or None
        Substrings identifying Done-When conditions that were NOT
        mechanically verified.  For each checkbox line in the section:

        - If the line contains any substring in ``unverified_substrings``
          (plain case-sensitive ``in`` containment): force the box UNticked
          (``- [ ]``) and ensure ``_UNVERIFIED_ANNOTATION`` is appended
          exactly once (idempotent — never double-appends).
        - Otherwise: force the box ticked (``- [x]``) and strip
          ``_UNVERIFIED_ANNOTATION`` if present (handles the repair →
          now-verified case).

        When ``unverified_substrings`` is empty or None (the default), the
        output is byte-identical to the pre-change all-tick behavior: every
        unticked box is ticked, no annotations added, already-ticked boxes
        are left as-is.

        Note: an empty string substring (``""``) would match every box because
        ``"" in x`` is always True.  Callers (``cmd_mark_complete``) filter
        empty/whitespace-only entries before passing the list here.
    """
    if unverified_substrings is None:
        unverified_substrings = []

    dw_match = _DONE_WHEN_HEADING.search(text)
    if dw_match is None:
        return text  # No Done When section — nothing to tick.

    section_start = dw_match.end()

    # Find next ## heading after the section start.
    next_match = _NEXT_SECTION.search(text, section_start)
    section_end = next_match.start() if next_match else len(text)

    before = text[:section_start]
    section = text[section_start:section_end]
    after = text[section_end:]

    if not unverified_substrings:
        # Fast path (default / back-compat): tick all boxes; strip any annotation
        # that may have been applied by a prior run with --unverified-box.
        # On a "clean" task file (no prior annotations) this is byte-identical
        # to the pre-change all-tick behavior because _ANY_BOX matches the same
        # lines as _UNCHECKED_BOX for unticked boxes, and already-ticked boxes
        # without annotations are unchanged.
        def _tick_and_strip(m):
            # type: (object) -> str
            line = m.group(1)
            # Separate any trailing \r so all matching runs against a clean core.
            cr = "\r" if line.endswith("\r") else ""
            if cr:
                line = line[:-1]
            line = line.replace("- [ ]", "- [x]", 1)
            if line.endswith(_UNVERIFIED_ANNOTATION):
                line = line[: -len(_UNVERIFIED_ANNOTATION)]
            return line + cr
        ticked_section = _ANY_BOX.sub(_tick_and_strip, section)
        return before + ticked_section + after

    # Slow path: per-box decision based on unverified_substrings.
    def _process_box(m):
        # type: (object) -> str
        line = m.group(1)
        # Separate any trailing \r so all substring matching and annotation
        # add/strip run against a \r-free core, then re-attach at the end.
        cr = "\r" if line.endswith("\r") else ""
        if cr:
            line = line[:-1]
        is_unverified = any(sub in line for sub in unverified_substrings)
        if is_unverified:
            # Ensure box is unticked.
            line = line.replace("- [x]", "- [ ]", 1)
            # Ensure annotation present exactly once (idempotent — trailing
            # annotation only; mid-line annotations are not deduped here).
            if line.endswith(_UNVERIFIED_ANNOTATION):
                return line + cr
            line = line + _UNVERIFIED_ANNOTATION
            return line + cr
        else:
            # Ensure box is ticked.
            line = line.replace("- [ ]", "- [x]", 1)
            # Strip trailing annotation if present.
            if line.endswith(_UNVERIFIED_ANNOTATION):
                line = line[: -len(_UNVERIFIED_ANNOTATION)]
            return line + cr

    processed_section = _ANY_BOX.sub(_process_box, section)
    return before + processed_section + after


def _fill_completion_notes(text, completed_at, files_changed, expects_met, produces_met, notes):
    # type: (str, str, str, str, str, str) -> str
    """Rewrite the ## Completion Notes section with real values.

    The skeleton produced by `breakdown_helper render-task-file` is:

        ## Completion Notes

        [Filled in by /implement after completion]
        **Completed**: [date/time]
        **Files changed**: [actual files]
        **Contract**: Expects [X/Y verified] | Produces [X/Y verified]
        **Notes**: [deviations or observations]

    This function replaces the skeleton with populated values.
    """
    cn_match = _COMPLETION_NOTES_HEADING.search(text)
    if cn_match is None:
        # No Completion Notes section: append it.
        filled = _build_completion_notes_block(
            completed_at, files_changed, expects_met, produces_met, notes
        )
        return text.rstrip("\n") + "\n\n" + filled + "\n"

    section_start = cn_match.end()
    # Completion Notes is always the last section (no next ## heading expected),
    # but handle the case where there is one.
    next_match = _NEXT_SECTION.search(text, section_start)
    section_end = next_match.start() if next_match else len(text)

    before = text[:cn_match.start()]
    after = text[section_end:]

    filled = _build_completion_notes_block(
        completed_at, files_changed, expects_met, produces_met, notes
    )

    return before + filled + "\n" + (after if after.strip() else "")


def _build_completion_notes_block(completed_at, files_changed, expects_met, produces_met, notes):
    # type: (str, str, str, str, str) -> str
    """Build the filled Completion Notes section block."""
    lines = [
        "## Completion Notes",
        "",
        "**Completed**: {0}".format(completed_at),
        "**Files changed**: {0}".format(files_changed),
        "**Contract**: Expects {0} | Produces {1}".format(expects_met, produces_met),
        "**Notes**: {0}".format(notes),
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# README index row update helper
# ---------------------------------------------------------------------------


_TASK_INDEX_HEADING = re.compile(r"^## Task Index\s*$", re.MULTILINE)


def _update_readme_row(text, number, new_status):
    # type: (str, str, str) -> tuple
    """Replace the Status cell of the task-number row in the Task Index table.

    Strategy: region-aware.
      1. Locate the ``## Task Index`` heading.
      2. Scan only the lines from that heading until the next ``## `` heading
         (or EOF) — this is the Task Index region.
      3. Within that region, find the row whose first cell matches `number`
         exactly and rewrite only the Status (last data) cell.
      4. If the target row is NOT found within the region, write a descriptive
         error to stderr and return (text, EXIT_FINDINGS).

    This approach is immune to:
    - Risk Assessment rows (``| 001 | Low | reason |``) — they live under a
      different ``## Risk Assessment`` heading, outside the Task Index region.
    - Titles containing a literal pipe character — the region restriction
      eliminates the need for a column-count heuristic.

    Returns
    -------
    tuple (str, int)
        (updated_text, EXIT_OK) on success;
        (original_text, EXIT_FINDINGS) when the target row is not found or
        the Task Index section is absent.  Writes to sys.stderr on failure.
    """
    # Locate the ## Task Index heading.
    heading_match = _TASK_INDEX_HEADING.search(text)
    if heading_match is None:
        sys.stderr.write(
            "mark-complete: Task Index section not found in index file; "
            "cannot update row for task {0}\n".format(number)
        )
        return text, EXIT_FINDINGS

    region_start = heading_match.end()

    # Find the next ## heading after the Task Index heading to bound the region.
    next_heading = _NEXT_SECTION.search(text, region_start)
    region_end = next_heading.start() if next_heading else len(text)

    before = text[:region_start]
    region = text[region_start:region_end]
    after = text[region_end:]

    region_lines = region.splitlines(keepends=True)
    updated_lines = []
    found = False
    for line in region_lines:
        stripped = line.rstrip("\n\r")
        if not found and stripped.startswith("|") and stripped.endswith("|"):
            cells = stripped.split("|")
            # cells[0] and cells[-1] are empty strings from the leading/trailing pipes.
            if len(cells) >= 3 and cells[1].strip() == number:
                # Update the last data cell (second-to-last token = Status).
                cells[-2] = " {0} ".format(new_status)
                new_line = "|".join(cells)
                ending = line[len(stripped):]
                updated_lines.append(new_line + ending)
                found = True
                continue
        updated_lines.append(line)

    if not found:
        sys.stderr.write(
            "mark-complete: row for task {0} not found in Task Index; "
            "index file may be out of sync\n".format(number)
        )
        return text, EXIT_FINDINGS

    updated_text = before + "".join(updated_lines) + after
    return updated_text, EXIT_OK


# ---------------------------------------------------------------------------
# argparse setup
# ---------------------------------------------------------------------------


def add_args_mark_complete(parser):
    # type: (object) -> None
    """Register mark-complete arguments on the given subparser."""
    parser.add_argument(
        "--task-file",
        required=True,
        dest="task_file",
        help="Path to the task .md file.",
    )
    parser.add_argument(
        "--index",
        required=True,
        help="Path to tasks/README.md index file.",
    )
    parser.add_argument(
        "--number",
        required=True,
        help="Task number string, e.g. '001'.",
    )
    parser.add_argument(
        "--files",
        default="[]",
        help="JSON array of files changed. Default: [].",
    )
    parser.add_argument(
        "--expects-met",
        default="",
        dest="expects_met",
        help="Expects fraction, e.g. '2/2'.",
    )
    parser.add_argument(
        "--produces-met",
        default="",
        dest="produces_met",
        help="Produces fraction, e.g. '2/2'.",
    )
    parser.add_argument(
        "--notes",
        default="",
        help="Deviation / observation notes.",
    )
    parser.add_argument(
        "--completed-at",
        default="",
        dest="completed_at",
        help=(
            "Timestamp string. If absent, the helper stamps with the "
            "current UTC time (ISO format). Pass an explicit value in "
            "tests for determinism."
        ),
    )
    parser.add_argument(
        "--unverified-box",
        action="append",
        default=None,
        dest="unverified_box",
        help=(
            "A substring identifying a Done-When condition that was NOT "
            "mechanically verified (e.g. the type-check / lint gate when "
            "verify-touched did not return pass). Repeatable. The matching "
            "box(es) are left unticked and annotated instead of ticked. "
            "Substrings should be specific enough to identify the intended "
            "box. Default: none (all boxes ticked, unchanged behavior)."
        ),
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repo root. Not used directly by mark-complete.",
    )


# ---------------------------------------------------------------------------
# Command handler
# ---------------------------------------------------------------------------


def cmd_mark_complete(args):
    # type: (object) -> int
    """Mark a task Complete, tick Done-When boxes, fill Completion Notes,
    and update the README.md index row.

    Parameters
    ----------
    args : argparse.Namespace

    Returns
    -------
    int
        0 on success; 1 on I/O error; 2 on parse/file-not-found error.
    """
    task_file = Path(getattr(args, "task_file", ""))
    index_file = Path(getattr(args, "index", ""))
    number = getattr(args, "number", "").strip()

    if not number:
        sys.stderr.write("mark-complete: --number is required\n")
        return EXIT_FINDINGS

    if not task_file or not str(task_file):
        sys.stderr.write("mark-complete: --task-file is required\n")
        return EXIT_FINDINGS

    if not index_file or not str(index_file):
        sys.stderr.write("mark-complete: --index is required\n")
        return EXIT_FINDINGS

    # --- Parse --files ---
    files_json = getattr(args, "files", "[]")
    try:
        files_list = json.loads(files_json)
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "mark-complete: --files is not valid JSON: {0}\n".format(exc)
        )
        return EXIT_ERR
    if not isinstance(files_list, list):
        sys.stderr.write(
            "mark-complete: --files must be a JSON array\n"
        )
        return EXIT_ERR

    files_str = ", ".join(str(f) for f in files_list) if files_list else "(none)"

    expects_met = getattr(args, "expects_met", "") or ""
    produces_met = getattr(args, "produces_met", "") or ""
    notes = getattr(args, "notes", "") or ""

    completed_at = getattr(args, "completed_at", "") or ""
    if not completed_at:
        completed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # --- Read and update task file ---
    if not task_file.exists():
        sys.stderr.write(
            "mark-complete: task file not found: {0}\n".format(task_file)
        )
        return EXIT_FINDINGS

    try:
        task_text = task_file.read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(
            "mark-complete: cannot read task file: {0}\n".format(exc)
        )
        return EXIT_ERR

    unverified = [s for s in (getattr(args, "unverified_box", None) or []) if s.strip()]

    task_text = _set_status_complete(task_text)
    task_text = _tick_done_when_boxes(task_text, unverified)
    task_text = _fill_completion_notes(
        task_text,
        completed_at=completed_at,
        files_changed=files_str,
        expects_met=expects_met or "?/?",
        produces_met=produces_met or "?/?",
        notes=notes or "(none)",
    )

    try:
        _atomic_write(task_file, task_text)
    except OSError as exc:
        sys.stderr.write(
            "mark-complete: cannot write task file: {0}\n".format(exc)
        )
        return EXIT_ERR

    # --- Read and update README index ---
    if not index_file.exists():
        sys.stderr.write(
            "mark-complete: index file not found: {0}\n".format(index_file)
        )
        return EXIT_FINDINGS

    try:
        index_text = index_file.read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(
            "mark-complete: cannot read index file: {0}\n".format(exc)
        )
        return EXIT_ERR

    index_text, row_rc = _update_readme_row(index_text, number, "Complete")
    if row_rc != EXIT_OK:
        return row_rc

    try:
        _atomic_write(index_file, index_text)
    except OSError as exc:
        sys.stderr.write(
            "mark-complete: cannot write index file: {0}\n".format(exc)
        )
        return EXIT_ERR

    sys.stdout.write(json.dumps({"marked": True}) + "\n")
    return EXIT_OK


# ---------------------------------------------------------------------------
# mark-skipped verb
# ---------------------------------------------------------------------------


def add_args_mark_skipped(parser):
    # type: (object) -> None
    """Register mark-skipped arguments on the given subparser."""
    parser.add_argument(
        "--task-file",
        required=True,
        dest="task_file",
        help="Path to the task .md file.",
    )
    parser.add_argument(
        "--index",
        required=True,
        help="Path to tasks/README.md index file.",
    )
    parser.add_argument(
        "--number",
        required=True,
        help="Task number string, e.g. '001'.",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repo root. Not used directly by mark-skipped.",
    )


def cmd_mark_skipped(args):
    # type: (object) -> int
    """Mark a task Skipped in tasks/<NNN>.md and update its README.md index row.

    Sets ``**Status**: Skipped`` in the task file.  Does NOT fill Completion
    Notes (skip differs from complete — no execution took place).  Does NOT
    touch git (the orchestrator handles branch clean-up per the /implement spec).

    Updates the matching Status cell in tasks/README.md via the same
    region-aware _update_readme_row as mark-complete.  Propagates
    EXIT_FINDINGS when the row or Task Index section is absent.

    Idempotent: re-running when already Skipped leaves the file unchanged
    (the status regex replace is a no-op, and the README row is already Skipped).

    Emits ``{"marked_skipped": true}`` JSON on stdout (exit 0).

    Returns
    -------
    int
        0 on success; 1 on I/O error; 2 on parse/file-not-found error.
    """
    task_file = Path(getattr(args, "task_file", ""))
    index_file = Path(getattr(args, "index", ""))
    number = getattr(args, "number", "").strip()

    if not number:
        sys.stderr.write("mark-skipped: --number is required\n")
        return EXIT_FINDINGS

    if not task_file or not str(task_file):
        sys.stderr.write("mark-skipped: --task-file is required\n")
        return EXIT_FINDINGS

    if not index_file or not str(index_file):
        sys.stderr.write("mark-skipped: --index is required\n")
        return EXIT_FINDINGS

    # --- Read and update task file ---
    if not task_file.exists():
        sys.stderr.write(
            "mark-skipped: task file not found: {0}\n".format(task_file)
        )
        return EXIT_FINDINGS

    try:
        task_text = task_file.read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(
            "mark-skipped: cannot read task file: {0}\n".format(exc)
        )
        return EXIT_ERR

    task_text = _set_status(task_text, "Skipped")

    try:
        _atomic_write(task_file, task_text, prefix="mark-skipped-")
    except OSError as exc:
        sys.stderr.write(
            "mark-skipped: cannot write task file: {0}\n".format(exc)
        )
        return EXIT_ERR

    # --- Read and update README index ---
    if not index_file.exists():
        sys.stderr.write(
            "mark-skipped: index file not found: {0}\n".format(index_file)
        )
        return EXIT_FINDINGS

    try:
        index_text = index_file.read_text(encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(
            "mark-skipped: cannot read index file: {0}\n".format(exc)
        )
        return EXIT_ERR

    index_text, row_rc = _update_readme_row(index_text, number, "Skipped")
    if row_rc != EXIT_OK:
        return row_rc

    try:
        _atomic_write(index_file, index_text, prefix="mark-skipped-")
    except OSError as exc:
        sys.stderr.write(
            "mark-skipped: cannot write index file: {0}\n".format(exc)
        )
        return EXIT_ERR

    sys.stdout.write(json.dumps({"marked_skipped": True}) + "\n")
    return EXIT_OK
