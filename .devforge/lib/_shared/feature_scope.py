"""Assembled-feature scope resolver shared between /review and /verify.

Extracted from src/devforge/lib/_review/_scope.py so that both /review and
/verify share one copy of the merge-base diff computation and scope-block
renderer.

The heading_label parameter on _render_scope_block and resolve_feature_scope
controls the banner line (`=== <label> ===`):
  - /review passes "Review Scope"        (the historical default)
  - /verify will pass "Verification Scope"

Existing /review callers that rely on the default are byte-behaviorally
identical to the pre-extraction code.

Stdlib only.  Python 3.8+.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# <base> auto-detect precedence (tried in order; first that resolves wins):
#   1. origin/HEAD (resolves via git symbolic-ref refs/remotes/origin/HEAD)
#   2. local branch "main"
#   3. local branch "develop"
#   4. local branch "master"
# If none resolves, the caller must pass --base explicitly.
_BASE_CANDIDATES = ["main", "develop", "master"]

# Maximum seconds for any single git subprocess call.
_GIT_TIMEOUT = 60


# ---------------------------------------------------------------------------
# Internal git helpers
# ---------------------------------------------------------------------------


def _git(args, cwd, timeout=_GIT_TIMEOUT):
    # type: (List[str], str, int) -> Tuple[int, str, str]
    """Run a git command with cwd=source_root.

    Returns (returncode, stdout, stderr).
    Never raises — subprocess errors are returned as (1, "", error_message).
    """
    cmd = ["git"] + args
    try:
        proc = subprocess.run(
            cmd,
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
        return 1, "", "git command timed out after {0}s: {1}".format(
            timeout, " ".join(cmd)
        )


def _is_git_repo(source_root):
    # type: (str) -> bool
    """Return True if source_root is inside a git repository."""
    rc, _, _ = _git(
        ["rev-parse", "--is-inside-work-tree"],
        cwd=source_root,
    )
    return rc == 0


def _resolve_head_sha(source_root):
    # type: (str) -> Optional[str]
    """Return the current HEAD SHA, or None on error."""
    rc, stdout, _ = _git(["rev-parse", "HEAD"], cwd=source_root)
    if rc != 0:
        return None
    return stdout.strip() or None


def _ref_exists(ref, source_root):
    # type: (str, str) -> bool
    """Return True if ref can be resolved by git."""
    rc, _, _ = _git(["rev-parse", "--verify", ref], cwd=source_root)
    return rc == 0


def _resolve_origin_head(source_root):
    # type: (str) -> Optional[str]
    """Attempt to resolve origin/HEAD via git symbolic-ref.

    Returns the resolved ref name (e.g. 'refs/remotes/origin/main') or None.
    Falls back to checking whether 'origin/HEAD' itself resolves as a ref.
    """
    rc, stdout, _ = _git(
        ["symbolic-ref", "refs/remotes/origin/HEAD"],
        cwd=source_root,
    )
    if rc == 0:
        resolved = stdout.strip()
        if resolved:
            return resolved
    # Fallback: try origin/HEAD as a direct ref (handles some bare-checkout cases).
    if _ref_exists("origin/HEAD", source_root):
        return "origin/HEAD"
    return None


def _autodetect_base(source_root):
    # type: (str) -> Optional[str]
    """Auto-detect the trunk base ref using the documented precedence:

    1. origin/HEAD (via git symbolic-ref refs/remotes/origin/HEAD)
    2. local branch "main"
    3. local branch "develop"
    4. local branch "master"

    Returns the first ref that resolves, or None if none do.
    """
    # Step 1: origin/HEAD.
    origin_head = _resolve_origin_head(source_root)
    if origin_head is not None:
        return origin_head

    # Steps 2-4: local branches.
    for candidate in _BASE_CANDIDATES:
        if _ref_exists(candidate, source_root):
            return candidate

    return None


def _compute_merge_base(base, head, source_root):
    # type: (str, str, str) -> Optional[str]
    """Return the merge-base SHA of base and head, or None on error."""
    rc, stdout, _ = _git(["merge-base", base, head], cwd=source_root)
    if rc != 0:
        return None
    return stdout.strip() or None


def _diff_name_only(merge_base_sha, head_sha, source_root):
    # type: (str, str, str) -> Optional[List[str]]
    """Run git diff --name-only <merge_base>..<head> and return sorted file list.

    Returns None on git error.  An empty list (no changes) is valid.
    """
    rc, stdout, _ = _git(
        ["diff", "--name-only", "{0}..{1}".format(merge_base_sha, head_sha)],
        cwd=source_root,
    )
    if rc != 0:
        return None
    files = []
    for line in stdout.splitlines():
        fp = line.strip()
        if fp:
            files.append(fp)
    files.sort()
    return files


# ---------------------------------------------------------------------------
# Source-root prefixing for wrapper mode
# ---------------------------------------------------------------------------


def _prefix_paths(files, source_root, install_root):
    # type: (List[str], str, str) -> List[str]
    """Prefix source-relative paths with the source-root subdir when in wrapper mode.

    In standalone mode (source_root == install_root), paths are already relative
    to the install root and are returned unchanged.

    In wrapper mode (source_root is a subdirectory of install_root), the
    source-relative paths need to be prefixed with the relative subdir so that
    agents operating from the install root can locate files.

    Example:
      install_root = /work/forge
      source_root  = /work/forge/my-project
      file         = src/main.py
      -> prefixed  = my-project/src/main.py

    Note: normpath is applied so "." prefixes never leak (e.g. when the
    source_root IS the install_root the prefix is "" / "." and we skip it).
    """
    abs_source = os.path.realpath(source_root)
    abs_install = os.path.realpath(install_root)

    if abs_source == abs_install:
        # Standalone: paths are already install-root-relative.
        return list(files)

    try:
        rel_prefix = os.path.relpath(abs_source, abs_install)
    except ValueError:
        # Different drives on Windows — cannot compute relative path.
        return list(files)

    if rel_prefix in ("", "."):
        return list(files)

    prefixed = []
    for fp in files:
        joined = os.path.normpath(os.path.join(rel_prefix, fp))
        # Normalize separators to forward slashes (git convention).
        prefixed.append(joined.replace(os.sep, "/"))
    return prefixed


# ---------------------------------------------------------------------------
# _render_scope_block
# ---------------------------------------------------------------------------


def _render_scope_block(
    feature_dir,        # type: str
    source_root,        # type: str
    base,               # type: str
    merge_base,         # type: str
    head,               # type: str
    files,              # type: List[str]
    files_for_finders,  # type: List[str]
    heading_label="Review Scope",  # type: str
):
    # type: (...) -> str
    """Render a human-readable scope summary for the assembled-feature diff.

    Shape mirrors _audit/_scope.py's render_scope_block:
      === <heading_label> ===
      Feature dir : ...
      Source root : ...
      Base        : ...
      Merge base  : ...
      HEAD        : ...
      File count  : N

      Files:
        path/to/file.py
        ...
    (file list omitted with a count note when > 25 files)

    Parameters
    ----------
    heading_label:
        Banner text for the scope block header line.
        /review passes "Review Scope" (the default).
        /verify passes "Verification Scope".
    """
    lines = []
    lines.append("=== {0} ===".format(heading_label))
    lines.append("Feature dir : {0}".format(feature_dir))
    lines.append("Source root : {0}".format(source_root))
    lines.append("Base        : {0}".format(base))
    lines.append("Merge base  : {0}".format(merge_base))
    lines.append("HEAD        : {0}".format(head))
    lines.append("File count  : {0}".format(len(files)))

    lines.append("")

    # Use files_for_finders (prefixed for wrapper mode) for the displayed list.
    display_files = files_for_finders

    if len(display_files) == 0:
        lines.append("Files: (none — no changes between base and HEAD)")
    elif len(display_files) <= 25:
        lines.append("Files:")
        for fp in display_files:
            lines.append("  {0}".format(fp))
    else:
        lines.append(
            "Files: ({0} files — list omitted; see scope JSON)".format(
                len(display_files)
            )
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# resolve_feature_scope
# ---------------------------------------------------------------------------


def resolve_feature_scope(
    feature_dir,            # type: str
    source_root,            # type: str
    install_root=None,      # type: Optional[str]
    base=None,              # type: Optional[str]
    heading_label="Review Scope",  # type: str
):
    # type: (...) -> Tuple[dict, Optional[str]]
    """Compute the assembled-feature diff and render the scope block.

    The assembled-feature diff is:
        git diff --name-only $(git merge-base <base> HEAD)..HEAD
    run with cwd = source_root.  This spans every WIP commit the feature
    accumulated (git diff sees them all), producing the union of all changes.

    Parameters
    ----------
    feature_dir:
        Path to the specs/NNN-<name>/ directory (used for context only —
        not for git operations; included in the JSON output).
    source_root:
        Absolute path to the source tree (where git runs).
        In standalone mode this is the repo root; in wrapper mode it is the
        inner project directory (e.g. /wrapper/my-project).
    install_root:
        Absolute path to the forge install root (where .devforge/ lives).
        Required for wrapper-mode path prefixing.  When None, defaults to
        source_root (standalone assumed — no prefixing).
    base:
        Git ref for the branch the feature forked from (e.g. "main",
        "origin/main").  When None, auto-detect via the documented precedence:
          1. origin/HEAD (git symbolic-ref refs/remotes/origin/HEAD)
          2. local branch "main"
          3. local branch "develop"
          4. local branch "master"
        If none resolves, returns an error result.
    heading_label:
        Label for the scope-block banner line (=== <label> ===).
        Defaults to "Review Scope" so /review callers are byte-identical
        when they do not pass this argument.

    Returns
    -------
    (result_dict, error_message)
        On success: (dict, None) — dict with stable keys (see below).
        On error:   ({}, error_message) — caller writes error_message to
                    stderr and exits 2.

    result_dict keys (always present on success):
      feature_dir   str       — the feature_dir argument
      source_root   str       — the source_root argument
      base          str       — the resolved base ref
      merge_base    str       — the merge-base SHA
      head          str       — HEAD SHA
      files         list[str] — sorted source-relative changed paths
      files_for_finders list[str]
                    — paths as finders should see them:
                      identical to files in standalone mode;
                      prefixed with the source-root subdir in wrapper mode
                      so agents working from install_root can locate them
      file_count    int       — len(files)
      scope_block   str       — rendered human-readable scope summary
    """
    if install_root is None:
        install_root = source_root

    # --- Gate: must be a git repo ---
    if not _is_git_repo(source_root):
        return {}, (
            "not a git repository: {0!r}. "
            "Ensure --source-root points to a git repo.".format(source_root)
        )

    # --- HEAD ---
    head_sha = _resolve_head_sha(source_root)
    if head_sha is None:
        return {}, (
            "cannot resolve HEAD in {0!r}. "
            "The repository may have no commits.".format(source_root)
        )

    # --- Resolve base ---
    if base:
        resolved_base = base
        if not _ref_exists(resolved_base, source_root):
            return {}, (
                "base ref {0!r} does not exist in {1!r}. "
                "Pass a valid branch or commit ref via --base.".format(
                    base, source_root
                )
            )
    else:
        resolved_base = _autodetect_base(source_root)
        if resolved_base is None:
            return {}, (
                "cannot auto-detect base branch in {0!r}. "
                "None of origin/HEAD, main, develop, master resolve. "
                "Pass --base <ref> explicitly.".format(source_root)
            )

    # --- Merge-base ---
    merge_base_sha = _compute_merge_base(resolved_base, head_sha, source_root)
    if merge_base_sha is None:
        return {}, (
            "git merge-base {0!r} {1!r} failed in {2!r}. "
            "The base ref may not share history with HEAD.".format(
                resolved_base, head_sha, source_root
            )
        )

    # --- Changed files ---
    files = _diff_name_only(merge_base_sha, head_sha, source_root)
    if files is None:
        return {}, (
            "git diff --name-only {0}..HEAD failed in {1!r}.".format(
                merge_base_sha, source_root
            )
        )

    # --- Wrapper-mode path prefixing ---
    files_for_finders = _prefix_paths(files, source_root, install_root)

    # --- Render scope block ---
    scope_block = _render_scope_block(
        feature_dir=feature_dir,
        source_root=source_root,
        base=resolved_base,
        merge_base=merge_base_sha,
        head=head_sha,
        files=files,
        files_for_finders=files_for_finders,
        heading_label=heading_label,
    )

    result = {
        "feature_dir": feature_dir,
        "source_root": source_root,
        "base": resolved_base,
        "merge_base": merge_base_sha,
        "head": head_sha,
        "files": files,
        "files_for_finders": files_for_finders,
        "file_count": len(files),
        "scope_block": scope_block,
    }

    return result, None
