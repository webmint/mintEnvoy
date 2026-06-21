"""bug_file.py — write bug reports to bugs/NNN-*.md in storage-rules.md format.

Extracted from _verify/_bugs.py and promoted to _shared/ so callers other
than /verify can file bugs with a custom Source field.

Public surface
--------------
  file_bugs(bugs_dir, issues, feature_spec_path, date, source="verify")
      -> list[str]

      Scan bugs_dir for highest existing NNN prefix, assign sequential
      numbers from there.  For each issue dict, write bugs/NNN-<slug>.md
      in the EXACT src/devforge/storage-rules.md format.

      Parameters
      ----------
      bugs_dir : str
          Path to the bugs/ directory.  Created if absent.
      issues : list[dict]
          List of issue dicts.  Each dict:
            {
              title:     str   — short title (1-5 words, used for slug)
              severity:  str   — Critical | Warning | Info
                                 (storage-rules vocabulary; NOT Critical/High/Medium/Info
                                 from findings — the caller must map if needed)
              description: str — what is wrong (1-3 sentences)
              expected:  str   — expected behavior (from spec AC or "" when unknown)
              actual:    str   — actual behavior (from verification evidence or "")
              files:     list[{path: str, detail: str}]  — file table rows
              evidence:  str   — how this was discovered
              ac_ref:    str   — "AC-N" or "N/A"
              category:  str   — optional, for tagging (not in format, used for slug)
            }
          Missing keys default to sensible placeholders.
      feature_spec_path : str
          Path to the feature spec file (e.g. specs/001-auth/spec.md),
          or "N/A" for standalone bugs.
      date : str
          YYYY-MM-DD.  REQUIRED — never call the clock.
      source : str
          Value for the **Source** field in the bug file.  Defaults to
          "verify" so existing callers need no change.

      Returns
      -------
      list[str]  Paths of the bug files written, in order.

Bug file format (verbatim from storage-rules.md)
-------------------------------------------------
  # Bug NNN: [Short Title]

  **Status**: Open
  **Severity**: Critical | Warning | Info
  **Source**: <source>
  **Feature**: [spec path]
  **AC**: [AC-N or N/A]
  **Reported**: [YYYY-MM-DD]
  **Fixed**: [empty]

  ## Description
  ...

  ## Expected Behavior
  ...

  ## Actual Behavior
  ...

  ## File(s)
  | File | Detail |
  |------|--------|
  | ... | ... |

  ## Evidence
  ...

  ## Related Issues
  [cross-links to other bugs filed in the same batch, or omitted if standalone]

  ## Fix Notes
  [Filled in after resolution]

Numbering
---------
  Scan bugs_dir for all *.md files whose name starts with a sequence of digits
  followed by a hyphen (e.g. 001-*, 042-*).  The highest such prefix + 1 is
  the first number for this batch.  Numbers are zero-padded to 3 digits.
  If bugs_dir is empty, start at 001.

  The scan is performed ONCE before writing any file in the batch; numbers
  are assigned sequentially from that point so a crash-and-retry won't
  produce gaps (the same number would simply be overwritten by the retry).

Slug sanitisation
-----------------
  title → lowercase, replace non-alphanumeric (except hyphen) → hyphen,
  collapse runs of hyphens → single hyphen, strip leading/trailing hyphens,
  cap at 30 chars.

Stdlib only.  Python 3.8+.  Atomic writes (mkstemp + os.replace).
"""

from __future__ import annotations

import os
import re
import tempfile
from typing import Dict, List

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LEADING_DIGITS_RE = re.compile(r"^(\d+)-")
# Replaces any run of non-alphanumeric characters (including hyphens) with a
# single hyphen.  Consecutive hyphens are collapsed by the follow-up
# _SLUG_COLLAPSE_RE pass.
_SLUG_NONALNUM_RE = re.compile(r"[^a-z0-9]+")
_SLUG_COLLAPSE_RE = re.compile(r"-{2,}")


def _scan_highest_bug_number(bugs_dir):
    # type: (str) -> int
    """Return the highest NNN prefix found in bugs_dir, or 0 if none."""
    if not os.path.isdir(bugs_dir):
        return 0
    highest = 0
    try:
        entries = os.listdir(bugs_dir)
    except OSError:
        return 0
    for name in entries:
        if not name.endswith(".md"):
            continue
        m = _LEADING_DIGITS_RE.match(name)
        if m:
            n = int(m.group(1))
            if n > highest:
                highest = n
    return highest


def _slugify(title, max_len=30):
    # type: (str, int) -> str
    """Convert title to a filename slug, truncating at a word boundary.

    Truncation rule: if the slug exceeds max_len, find the last hyphen that
    fits within the cap and cut there (dropping the trailing partial word).
    If no hyphen exists within the cap (i.e. the first word alone exceeds the
    cap), keep the full first word so the slug is never empty.
    """
    slug = title.lower()
    slug = _SLUG_NONALNUM_RE.sub("-", slug)
    slug = _SLUG_COLLAPSE_RE.sub("-", slug)
    slug = slug.strip("-")
    if len(slug) > max_len:
        candidate = slug[:max_len]
        last_hyphen = candidate.rfind("-")
        if last_hyphen > 0:
            # Cut at the word boundary, then strip any trailing hyphen.
            slug = candidate[:last_hyphen].rstrip("-")
        else:
            # No hyphen within the cap: the first word exceeds max_len.
            # Keep it intact rather than producing an empty slug.
            slug = candidate.rstrip("-")
    return slug or "bug"


def _format_bug(
    number,            # type: int
    issue,             # type: Dict
    feature_spec_path, # type: str
    date,              # type: str
    related_paths,     # type: List[str]
    source,            # type: str
):
    # type: (...) -> str
    """Render a single bug file in storage-rules.md format."""
    title = (issue.get("title") or "Untitled bug").strip()
    severity = (issue.get("severity") or "Info").strip()
    description = (issue.get("description") or "").strip()
    expected = (issue.get("expected") or "").strip()
    actual = (issue.get("actual") or "").strip()
    files = issue.get("files") or []
    evidence = (issue.get("evidence") or "").strip()
    ac_ref = (issue.get("ac_ref") or "N/A").strip()

    lines = []  # type: List[str]

    lines.append("# Bug {0:03d}: {1}".format(number, title))
    lines.append("")
    lines.append("**Status**: Open")
    lines.append("**Severity**: {0}".format(severity))
    lines.append("**Source**: {0}".format(source))
    lines.append("**Feature**: {0}".format(feature_spec_path or "N/A"))
    lines.append("**AC**: {0}".format(ac_ref))
    lines.append("**Reported**: {0}".format(date))
    lines.append("**Fixed**: ")
    lines.append("")
    lines.append("## Description")
    lines.append("")
    lines.append(description if description else "_No description provided._")
    lines.append("")
    lines.append("## Expected Behavior")
    lines.append("")
    lines.append(
        expected if expected else "_Expected behavior not specified — see spec AC._"
    )
    lines.append("")
    lines.append("## Actual Behavior")
    lines.append("")
    lines.append(
        actual if actual else "_Actual behavior not specified — see verification evidence._"
    )
    lines.append("")
    lines.append("## File(s)")
    lines.append("")
    lines.append("| File | Detail |")
    lines.append("|------|--------|")
    if files:
        for f in files:
            fpath = (f.get("path") or "").strip()
            fdetail = (f.get("detail") or "").strip()
            lines.append("| {0} | {1} |".format(fpath, fdetail))
    else:
        lines.append("| (unknown) | (see evidence) |")
    lines.append("")
    lines.append("## Evidence")
    lines.append("")
    lines.append(evidence if evidence else "_No evidence provided._")
    lines.append("")
    lines.append("## Related Issues")
    lines.append("")
    if related_paths:
        for rp in related_paths:
            slug_part = os.path.basename(rp)
            title_part = re.sub(r"^\d+-", "", os.path.splitext(slug_part)[0])
            lines.append("- {0} — {1}".format(rp, title_part.replace("-", " ")))
    else:
        lines.append("_None — standalone bug._")
    lines.append("")
    lines.append("## Fix Notes")
    lines.append("")
    lines.append("_Filled in after resolution._")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# file_bugs
# ---------------------------------------------------------------------------


def file_bugs(bugs_dir, issues, feature_spec_path, date, source="verify"):
    # type: (str, List[Dict], str, str, str) -> List[str]
    """Write bug files in bugs/NNN-<slug>.md format.

    Parameters
    ----------
    bugs_dir : str
        Path to the bugs/ directory.  Created if absent.
    issues : list[dict]
        Issue dicts — see module docstring for shape.
    feature_spec_path : str
        Path to the feature spec (e.g. specs/001-auth/spec.md).
    date : str
        YYYY-MM-DD.  REQUIRED — never call the clock.
    source : str
        Value for the **Source** field.  Defaults to "verify" so existing
        callers that omit the argument are byte-identical to before.

    Returns
    -------
    list[str]  Paths written, in order.
    """
    if not issues:
        return []

    os.makedirs(bugs_dir, exist_ok=True)

    # Scan ONCE for the highest existing bug number
    highest = _scan_highest_bug_number(bugs_dir)
    start_num = highest + 1

    # Pre-compute all file paths (for Related Issues cross-links)
    paths = []  # type: List[str]
    for i, issue in enumerate(issues):
        number = start_num + i
        title = (issue.get("title") or "bug").strip()
        slug = _slugify(title)
        filename = "{0:03d}-{1}.md".format(number, slug)
        paths.append(os.path.join(bugs_dir, filename))

    written = []  # type: List[str]
    for i, issue in enumerate(issues):
        out_path = paths[i]
        number = start_num + i

        # Related Issues = all OTHER bug paths in this batch
        related = [p for j, p in enumerate(paths) if j != i]

        content = _format_bug(
            number=number,
            issue=issue,
            feature_spec_path=feature_spec_path,
            date=date,
            related_paths=related,
            source=source,
        )

        # Atomic write
        bugs_abs_dir = os.path.dirname(out_path) or "."
        tmp_fd, tmp_path = tempfile.mkstemp(
            prefix=".tmp-bug-",
            suffix=".md",
            dir=bugs_abs_dir,
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
                fh.write(content)
            os.replace(tmp_path, out_path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

        written.append(out_path)

    return written
