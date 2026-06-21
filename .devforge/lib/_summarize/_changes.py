"""_changes.py — gather-change-data verb for summarize_helper.

Assembles the changed-file list + scope_block (via _shared.feature_scope) and
supplements with git diff --stat for +/- insertion/deletion totals that the
_shared resolver does not provide (it is --name-only based).

JSON emitted to stdout on success:

  {
    "feature_dir":      str,            # from resolve_feature_scope
    "source_root":      str,            # from resolve_feature_scope
    "base":             str,            # resolved base ref
    "merge_base":       str,            # merge-base SHA
    "head":             str,            # HEAD SHA
    "files":            list[str],      # sorted source-relative changed paths
    "files_for_finders": list[str],     # wrapper-prefixed paths (=files in standalone)
    "file_count":       int,
    "scope_block":      str,            # human-readable scope summary block
    "by_directory":     dict[str,list], # files grouped by top-level directory
    "insertions":       int,            # total inserted lines (0 when no stat)
    "deletions":        int,            # total deleted lines (0 when no stat)
    "stat_summary":     str,            # raw git diff --stat summary line, or ""
    "source_changes":   dict or None    # wrapper-mode source-repo changes, or None
  }

When source_root != install_root (wrapper mode), "source_changes" is a parallel
dict with the same keys as the top-level (except "source_changes" itself), but
scoped to the source repo.  In standalone mode "source_changes" is null/None.

Exit codes:
  0 — success (JSON emitted to stdout)
  2 — error (message on stderr, no JSON)

Stdlib only.  Python 3.8+.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_GIT_TIMEOUT = 60

# Pattern that matches the git diff --stat summary line, e.g.:
#   " 4 files changed, 12 insertions(+), 3 deletions(-)"
# We capture the insertions/deletions counts (the files count is already in
# the scope_block via file_count).
_STAT_SUMMARY_RE = re.compile(
    r"\d+ files? changed"
    r"(?:,\s*(\d+) insertions?\(\+\))?"
    r"(?:,\s*(\d+) deletions?\(-\))?",
)


# ---------------------------------------------------------------------------
# git helpers
# ---------------------------------------------------------------------------


def _run_git(args, cwd, timeout=_GIT_TIMEOUT):
    # type: (List[str], str, int) -> Tuple[int, str, str]
    """Run a git command.  Returns (returncode, stdout, stderr).

    Never raises — subprocess errors become (1, "", message).
    """
    try:
        proc = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError:
        return 1, "", "git not found on PATH"
    except subprocess.TimeoutExpired:
        return 1, "", "git diff --stat timed out"


# ---------------------------------------------------------------------------
# git diff --stat helpers
# ---------------------------------------------------------------------------


def _diff_stat(merge_base, head, cwd):
    # type: (str, str, str) -> Tuple[int, int, str]
    """Run git diff --stat <merge_base>..<head> and return (insertions, deletions, summary).

    On error or zero changes, returns (0, 0, "").
    """
    rc, stdout, _ = _run_git(
        ["diff", "--stat", "{0}..{1}".format(merge_base, head)],
        cwd=cwd,
    )
    if rc != 0:
        return 0, 0, ""

    # The last non-empty line is the summary line.
    lines = [ln.strip() for ln in stdout.splitlines() if ln.strip()]
    if not lines:
        return 0, 0, ""

    summary_line = lines[-1]
    m = _STAT_SUMMARY_RE.search(summary_line)
    if not m:
        return 0, 0, summary_line

    insertions = int(m.group(1)) if m.group(1) else 0
    deletions = int(m.group(2)) if m.group(2) else 0
    return insertions, deletions, summary_line


# ---------------------------------------------------------------------------
# grouping helper
# ---------------------------------------------------------------------------


def _group_by_directory(files):
    # type: (List[str]) -> Dict[str, List[str]]
    """Group file paths by their top-level directory component.

    Files directly in the root (no '/' in path) are grouped under "." to
    make the top-level grouping explicit.

    Returns an ordered dict (insertion order = sorted key order).
    """
    groups = {}  # type: Dict[str, List[str]]
    for fp in sorted(files):
        if "/" in fp:
            top = fp.split("/", 1)[0]
        else:
            top = "."
        groups.setdefault(top, []).append(fp)
    return dict(sorted(groups.items()))


# ---------------------------------------------------------------------------
# gather_change_data — public interface called by cmd_gather_change_data
# ---------------------------------------------------------------------------


def gather_change_data(
    feature_dir,     # type: str
    source_root,     # type: str
    install_root,    # type: Optional[str]
    base=None,       # type: Optional[str]
):
    # type: (...) -> Tuple[Optional[Dict], Optional[str]]
    """Gather the assembled-feature change data for /summarize.

    Uses _shared.feature_scope.resolve_feature_scope for the file list and
    scope_block, then supplements with git diff --stat for +/- totals and
    groups files by top-level directory.

    In wrapper mode (source_root != install_root), gathers source-repo changes
    separately and returns them under "source_changes".

    Returns (result_dict, None) on success, ({}, error_message) on failure.
    """
    # Import here to allow tests to set up sys.path before this module loads.
    from _shared.feature_scope import resolve_feature_scope  # type: ignore

    if install_root is None:
        install_root = source_root

    # --- Assembled scope (file list + scope_block) via _shared ---
    scope_result, err = resolve_feature_scope(
        feature_dir=feature_dir,
        source_root=source_root,
        install_root=install_root,
        base=base,
        heading_label="Summary Scope",
    )
    if err:
        return None, err

    # --- git diff --stat for +/- totals ---
    merge_base = scope_result["merge_base"]
    head = scope_result["head"]

    insertions, deletions, stat_summary = _diff_stat(merge_base, head, source_root)

    # --- group by directory ---
    by_directory = _group_by_directory(scope_result["files"])

    result = {
        "feature_dir":       scope_result["feature_dir"],
        "source_root":       scope_result["source_root"],
        "base":              scope_result["base"],
        "merge_base":        merge_base,
        "head":              head,
        "files":             scope_result["files"],
        "files_for_finders": scope_result["files_for_finders"],
        "file_count":        scope_result["file_count"],
        "scope_block":       scope_result["scope_block"],
        "by_directory":      by_directory,
        "insertions":        insertions,
        "deletions":         deletions,
        "stat_summary":      stat_summary,
        "source_changes":    None,
    }

    # --- wrapper-mode source-repo changes ---
    abs_source = os.path.realpath(source_root)
    abs_install = os.path.realpath(install_root)
    if abs_source != abs_install:
        # Source root differs from install root: gather changes in the source repo.
        src_scope, src_err = resolve_feature_scope(
            feature_dir=feature_dir,
            source_root=source_root,
            install_root=source_root,  # scope within source repo only
            base=base,
            heading_label="Summary Scope (source repo)",
        )
        if src_err:
            # Non-fatal: surface the error in source_changes but don't fail.
            result["source_changes"] = {"error": src_err}
        else:
            src_ins, src_del, src_stat = _diff_stat(
                src_scope["merge_base"], src_scope["head"], source_root
            )
            result["source_changes"] = {
                "feature_dir":       src_scope["feature_dir"],
                "source_root":       src_scope["source_root"],
                "base":              src_scope["base"],
                "merge_base":        src_scope["merge_base"],
                "head":              src_scope["head"],
                "files":             src_scope["files"],
                "files_for_finders": src_scope["files_for_finders"],
                "file_count":        src_scope["file_count"],
                "scope_block":       src_scope["scope_block"],
                "by_directory":      _group_by_directory(src_scope["files"]),
                "insertions":        src_ins,
                "deletions":         src_del,
                "stat_summary":      src_stat,
            }

    return result, None


# ---------------------------------------------------------------------------
# CLI handler — registered via _cli.py _SUBCOMMAND_REGISTRY
# ---------------------------------------------------------------------------


def cmd_gather_change_data(args):
    # type: (object) -> int
    """Handle the gather-change-data verb.

    Emits JSON to stdout on success (exit 0).
    Emits an error message to stderr on failure (exit 2).
    """
    feature_dir = getattr(args, "feature_dir", "") or ""
    source_root = getattr(args, "source_root", ".") or "."
    install_root = getattr(args, "install_root", None) or None
    base = getattr(args, "base", None) or None

    if not feature_dir:
        sys.stderr.write(
            "gather-change-data: --feature-dir is required\n"
        )
        return 2

    result, err = gather_change_data(
        feature_dir=feature_dir,
        source_root=os.path.realpath(source_root),
        install_root=os.path.realpath(install_root) if install_root else None,
        base=base,
    )
    if err:
        sys.stderr.write(
            "gather-change-data: {0}\n".format(err)
        )
        return 2

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0
