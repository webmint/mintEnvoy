"""_cmds_preflight -- preflight verb for implement_helper.

Checks that the project is ready for /implement to start a task:

  1. Constitution populated: read constitution.md (relative to install root);
     if it contains the sentinel "_Run /constitute to populate_" → exit 2.
  2. Branch check: get current git branch of the **source** repo; refuse
     main / master / trunk and the source repo's actual default branch
     detected dynamically via `git symbolic-ref --quiet refs/remotes/origin/HEAD`;
     require a feature branch.  On git failure, exit 2.
  3. Defensive wip.md assert: the Phase 9 recovery branch (loop entry) is the
     SOLE interrupted-session detector.  Preflight only asserts that no stale
     wip.md remains at per-task entry (wip.md is in the install root).
     If one is unexpectedly present, exit 2.
  4. Snapshot **source** repo HEAD sha as head_sha (rollback target for the
     source repo, matching wip.md checkpoint semantics in wrapper mode).
  5. Dirty-source warning: if the source repo has pre-existing uncommitted
     changes at task start, include a "source_dirty_warning" in the output
     JSON (advisory, exit still 0 if other checks pass — precise staging in
     wip-commit means it won't corrupt the commit, but the user should know
     the source repo was not clean when the task started).

Emits JSON to stdout on success:
  {
    "constitution_digest": "<first 5 lines of constitution.md>",
    "memory_digest": "<first 5 lines of .devforge/memory.md or null>",
    "head_sha": "<full source-repo git HEAD SHA>",
    "branch": "<current branch name (source repo)>",
    "source_branch": "<same as branch (source repo, explicit alias)>",
    "source_dirty_warning": "<message or null>"  // null if source is clean
  }

Exit codes:
  0 — preflight passed; JSON emitted.
  2 — preflight blocked; message on stderr.

Design notes:
- Wrapper vs standalone: resolve_workspace(install_root) → Workspace gives
  source_root.  When PROJECT_ROOT == "." (standalone), source_root ==
  install_root, so all git ops target the same directory — identical to
  before this change.  When PROJECT_ROOT is a non-trivial path (wrapper mode),
  git ops (branch check, HEAD SHA, dirty check) target the source repo.
- Constitution sentinel constant: "_Run /constitute to populate_" (verbatim
  from _specify._schema.CONSTITUTION_POPULATE_GUARD; not imported to avoid
  cross-package coupling — the value is stable by contract).
- constitution.md and .devforge/ (memory.md, wip.md) are install-root
  artifacts — they stay at the install root in wrapper mode.
- Default branches refused: main, master, trunk (case-insensitive static set)
  PLUS the source repo's origin default branch detected dynamically (exact
  match, case-sensitive).  Dynamic detection failure is non-fatal.
- git subprocess calls use capture_output=True + check=False + timeout so
  network-unavailable or missing-git conditions degrade gracefully.
- _check_branch returns (branch_name, None) on success, (None, error) on
  failure so cmd_preflight reads the git branch exactly once.
- Digest lines = first N non-blank lines (up to DIGEST_LINES) of each file.
  Not the whole file — the orchestrator uses this as a quick sanity check.
- memory.md absence is NOT an error; its digest is null in that case.
- source_dirty_warning field: present in JSON output but set to null when
  the source repo is clean.  Non-null string value contains a human-readable
  advisory message.  This is ported from the proven 1.x execute-task.md
  design (line 153: dirty-source warning at task start).

Stdlib only. Python 3.8+.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from _implement._workspace import resolve_workspace

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# The literal that _Run /constitute to populate_ writes into constitution.md
# before the user has run /constitute.  (Verbatim from
# src/devforge/lib/_specify/_schema.py CONSTITUTION_POPULATE_GUARD.)
CONSTITUTION_POPULATE_GUARD = "_Run /constitute to populate_"

# Branch names that are STATICALLY considered "default" and are refused.
# Compared case-insensitively.  Does NOT include "develop" — gitflow teams use
# develop as a feature-integration branch; refusing it statically would lock
# them out.  Instead, the repo's actual default branch is detected dynamically
# via _git_origin_default_branch() and also refused.
DEFAULT_BRANCHES = frozenset(["main", "master", "trunk"])

# Number of leading lines to include in each digest.
DIGEST_LINES = 5

# Exit codes (match breakdown_helper.py convention).
EXIT_OK = 0
EXIT_FINDINGS = 2

# Timeout (seconds) for git subprocess calls.
_GIT_TIMEOUT = 15


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _read_first_n_lines(path, n):
    # type: (Path, int) -> Optional[str]
    """Return the first n non-blank lines of path joined with newlines.

    Returns None when the file is absent or unreadable.
    Returns an empty string when the file is present but has no non-blank lines.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, IOError):
        return None
    lines = [ln for ln in text.splitlines() if ln.strip()]
    snippet = lines[:n]
    return "\n".join(snippet)


def _git_current_branch(cwd):
    # type: (str) -> Optional[str]
    """Return the current git branch name, or None on any failure.

    Uses `git rev-parse --abbrev-ref HEAD`.  Returns "HEAD" when in detached-
    HEAD state.  Returns None when git is not on PATH, times out, or the
    directory is not a git repository.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_TIMEOUT,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _git_head_sha(cwd):
    # type: (str) -> Optional[str]
    """Return the full SHA of HEAD, or None on any failure."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_TIMEOUT,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    sha = result.stdout.strip()
    return sha if sha else None


def _git_origin_default_branch(cwd):
    # type: (str) -> Optional[str]
    """Return the name of origin's default branch, or None if undetectable.

    Reads `git symbolic-ref --quiet refs/remotes/origin/HEAD` and strips the
    "refs/remotes/origin/" prefix.  Returns None when:
    - the repo has no remote named origin,
    - origin/HEAD has not been set (no `git remote set-head` has been run),
    - git is unavailable, or
    - the command times out.

    Callers must treat None as "unknown, skip the dynamic check" rather than
    as an error — dynamic detection failure is non-fatal.
    """
    try:
        result = subprocess.run(
            ["git", "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_TIMEOUT,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    ref = result.stdout.strip()
    # ref is e.g. "refs/remotes/origin/main" or "refs/remotes/origin/develop"
    prefix = "refs/remotes/origin/"
    if ref.startswith(prefix):
        return ref[len(prefix):]
    return None


def _git_status_dirty(cwd):
    # type: (str) -> bool
    """Return True if the git repo at cwd has any uncommitted changes.

    Runs `git status --porcelain`.  Any non-empty output means the working
    tree or index is dirty.  Returns False on any subprocess failure (missing
    git, non-repo dir, timeout) — fail-soft so dirty detection doesn't block
    the task; the warning is advisory.
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_TIMEOUT,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    if result.returncode != 0:
        return False
    return bool(result.stdout.strip())


def _check_constitution(root):
    # type: (Path) -> Optional[str]
    """Check constitution.md is present and populated.

    Returns None on success, or an error string describing why it failed.
    """
    constitution_path = root / "constitution.md"
    if not constitution_path.exists():
        return (
            "constitution.md not found at {0}; "
            "run /constitute to populate.".format(constitution_path)
        )
    try:
        text = constitution_path.read_text(encoding="utf-8")
    except (OSError, IOError) as exc:
        return "cannot read constitution.md: {0}".format(exc)
    if CONSTITUTION_POPULATE_GUARD in text:
        return (
            "constitution.md contains the populate-guard sentinel "
            "{0!r} — run /constitute to populate.".format(CONSTITUTION_POPULATE_GUARD)
        )
    return None


def _check_branch(cwd):
    # type: (str) -> tuple
    """Check that the current branch is NOT a default branch.

    Returns (branch_name, None) on success, or (None, error_string) on failure.
    This two-value return means cmd_preflight reads the git branch exactly once.

    Refuses:
    - Detached HEAD state ("HEAD" literal from git rev-parse).
    - Any branch whose lowercase form is in DEFAULT_BRANCHES (main/master/trunk).
    - The repo's actual origin default branch detected via
      _git_origin_default_branch (exact, case-sensitive match).  Detection
      failure is non-fatal — the dynamic check is simply skipped.
    """
    branch = _git_current_branch(cwd)
    if branch is None:
        return (None,
                "cannot determine current git branch "
                "(is this a git repository? is git installed?).")
    if branch == "HEAD":
        return (None,
                "currently in detached HEAD state; "
                "check out a feature branch before running /implement.")
    if branch.lower() in DEFAULT_BRANCHES:
        return (None,
                "currently on default branch {0!r}; "
                "/implement requires a feature branch.".format(branch))
    # Dynamic check: refuse if this branch IS the repo's origin default.
    origin_default = _git_origin_default_branch(cwd)
    if origin_default is not None and branch == origin_default:
        return (None,
                "currently on default branch {0!r} (origin/HEAD); "
                "/implement requires a feature branch.".format(branch))
    return (branch, None)


def _check_wip_marker(root):
    # type: (Path) -> Optional[str]
    """Assert that no stale wip.md remains from a previous interrupted task.

    The Phase 9 recovery branch (loop entry) is the SOLE interrupted-session
    detector.  Preflight only asserts here.  If wip.md is unexpectedly present,
    instruct the user to resolve the previous session first.

    Returns None when no wip.md exists (clean state), or an error string.
    """
    devforge_dir = root / ".devforge"
    wip_path = devforge_dir / "wip.md"
    if wip_path.exists():
        return (
            "stale .devforge/wip.md detected; "
            "a previous task was interrupted. "
            "Re-run /implement (or restart the loop) to enter the "
            "Phase 9 crash-recovery branch (resume / rollback / skip / manual)."
        )
    return None


# ---------------------------------------------------------------------------
# Public command handler
# ---------------------------------------------------------------------------


def cmd_preflight(args):
    # type: (object) -> int
    """Run preflight checks and emit JSON to stdout.

    Checks (in order):
      1. Constitution populated (install root — wrapper artifact).
      2. Feature branch (not main/master/trunk or origin's default branch),
         checked against the **source** repo (where code commits land).
      3. No stale wip.md (install root — wrapper artifact).
      4. Capture **source** repo HEAD SHA (rollback target for the source repo).
      5. Dirty-source advisory: warn if source repo has pre-existing uncommitted
         changes (advisory only — precise staging means it won't corrupt the
         commit, but the user should know the baseline was muddied).

    Emits JSON on success; writes to stderr and returns 2 on failure.

    args.root : str
        Install root directory (default: cwd).  The source root is resolved
        from this via resolve_workspace().
    """
    root_str = getattr(args, "root", None) or "."
    root = Path(root_str).resolve()

    # Resolve workspace: source_root is where all git ops run.
    # For standalone installs source_root == install_root (behaviour unchanged).
    workspace = resolve_workspace(root)
    source_cwd = str(workspace.source_root)

    # --- Check 1: constitution populated (install root). ---
    constitution_err = _check_constitution(root)
    if constitution_err is not None:
        sys.stderr.write(
            "implement_helper preflight: {0}\n".format(constitution_err)
        )
        return EXIT_FINDINGS

    # --- FIX 1: guard missing source root in wrapper mode ---
    # In wrapper mode, if PROJECT_ROOT points at an un-cloned directory,
    # every git subprocess below would raise FileNotFoundError (from
    # subprocess.run's cwd= argument) — not because git is missing from
    # PATH, but because the directory doesn't exist.  Catch that here with
    # a clear diagnostic so the user debugs their config, not their PATH.
    if workspace.is_wrapper and not workspace.source_root.exists():
        sys.stderr.write(
            "implement_helper preflight: configured source root does not exist: "
            "{0} (check PROJECT_ROOT in .devforge/project-config.json)\n".format(
                workspace.source_root
            )
        )
        return EXIT_FINDINGS

    # --- Check 2: feature branch (source repo). ---
    # _check_branch returns (branch_name, None) on success, (None, error) on
    # failure — branch is read exactly once here, no second git call needed.
    branch, branch_err = _check_branch(source_cwd)
    if branch_err is not None:
        sys.stderr.write(
            "implement_helper preflight: {0}\n".format(branch_err)
        )
        return EXIT_FINDINGS

    # branch is guaranteed non-None here (branch_err was None).

    # --- Check 3: stale wip.md (install root). ---
    wip_err = _check_wip_marker(root)
    if wip_err is not None:
        sys.stderr.write(
            "implement_helper preflight: {0}\n".format(wip_err)
        )
        return EXIT_FINDINGS

    # --- Step 4: snapshot source repo HEAD SHA. ---
    head_sha = _git_head_sha(source_cwd)
    if head_sha is None:
        sys.stderr.write(
            "implement_helper preflight: cannot read git HEAD SHA; "
            "ensure the source repository has at least one commit.\n"
        )
        return EXIT_FINDINGS

    # --- Step 5: dirty-source advisory (source repo, non-blocking). ---
    source_dirty_warning = None  # type: Optional[str]
    if _git_status_dirty(source_cwd):
        source_dirty_warning = (
            "Source repo has pre-existing uncommitted changes at task start. "
            "The checkpoint baseline is muddied — consider stashing or "
            "committing these changes before proceeding. "
            "(Precise touched-files staging means they will NOT corrupt the "
            "per-task WIP commit, but the diff will be harder to read.)"
        )

    # --- Build digests (install root — constitution + memory are wrapper artifacts). ---
    constitution_path = root / "constitution.md"
    constitution_digest = _read_first_n_lines(constitution_path, DIGEST_LINES)

    memory_path = root / ".devforge" / "memory.md"
    memory_digest = _read_first_n_lines(memory_path, DIGEST_LINES)
    # memory.md absence is NOT an error; null digest is valid.

    result = {
        "constitution_digest": constitution_digest,
        "memory_digest": memory_digest,
        "head_sha": head_sha,
        "branch": branch,
        "source_branch": branch,
        "source_dirty_warning": source_dirty_warning,
    }
    sys.stdout.write(json.dumps(result, indent=2) + "\n")
    return EXIT_OK


# ---------------------------------------------------------------------------
# Argument adder for CLI registration
# ---------------------------------------------------------------------------


def add_args_preflight(parser):
    # type: (object) -> None
    """Add --root argument to the preflight subparser."""
    parser.add_argument(
        "--root",
        default=".",
        metavar="DIR",
        help=(
            "Install root directory (must contain constitution.md and .devforge/; "
            "default: current working directory). The source root is resolved "
            "from this via .devforge/project-config.json PROJECT_ROOT."
        ),
    )
