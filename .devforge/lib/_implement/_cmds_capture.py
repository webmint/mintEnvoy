"""_cmds_capture -- capture-touched-files verb for implement_helper.

Captures the set of files changed since the task-start checkpoint by
combining two git queries:

  1. `git diff --name-only <checkpoint-sha>` -- all tracked files that
     differ between the checkpoint commit and the current working tree
     (includes staged changes and unstaged modifications to tracked files).

  2. `git status --porcelain` -- the untracked/new-file column (lines
     starting with '??' in porcelain output) that `git diff` would miss
     because the files were never committed.

The union of both sets is emitted as a JSON array of path strings to
stdout, one JSON payload per invocation.  Paths are relative to the
**source** repository root (as git reports them), which is the form that
verify-touched and wip-commit expect.

Arguments (argparse):
  --checkpoint <sha>   Required. The git SHA of the pre-task empty
                       checkpoint commit (from the source repo's preflight
                       output).
  --root <path>        Optional. The **install** root directory.  Defaults
                       to the current working directory.  The source root
                       is resolved from this via resolve_workspace().

Exit codes:
  0 — success; JSON array emitted to stdout.
  1 — I/O or subprocess failure; message on stderr.
  2 — usage error (missing required arg, invalid SHA format).

Design notes:
- Workspace resolution: resolve_workspace(install_root) → Workspace gives
  the source_root.  All git operations run with cwd = source_root.  For
  standalone installs (PROJECT_ROOT == "."), source_root == install_root,
  so behaviour is identical to before this change.
- `git diff --name-only` resolves through all intermediate commits between
  the checkpoint and HEAD, plus any staged/unstaged local changes.  This
  correctly captures files modified during a long-running agent run.
- `git status --porcelain` is the canonical way to discover untracked files
  that are NEW since the checkpoint (the agent created them but never staged
  them).
- Paths are NOT re-prefixed; they are returned exactly as git emits them
  (relative to the source root).  The caller (`verify-touched`) uses them
  for path-prefix matching against PACKAGE_STACKS; those paths must stay
  source-root-relative.
- Empty result (no files changed) is valid and emits [].
- The SHA is validated as a non-empty alphanumeric-hex string before calling
  git; an obviously invalid SHA surfaces a usage error (exit 2) before
  spending a subprocess.
- subprocess timeout: 30 s (matches other implement helpers); git operations
  are local and should never exceed this for normal repos.

Stdlib only. Python 3.8+.
"""

import json
import os
import re
import subprocess
import sys
from typing import List

from _implement._workspace import resolve_workspace

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Accepted SHA format: 4-40 hex chars (abbreviated or full).
_SHA_RE = re.compile(r"^[0-9a-fA-F]{4,40}$")

EXIT_OK = 0
EXIT_ERR = 1
EXIT_USAGE = 2

_GIT_TIMEOUT = 30  # seconds


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _validate_sha(sha):
    # type: (str) -> bool
    """Return True if sha looks like a valid git SHA (4-40 hex chars)."""
    return bool(_SHA_RE.match(sha))


def _git_diff_files(checkpoint_sha, cwd):
    # type: (str, str) -> List[str]
    """Return files that differ between checkpoint and the current working tree.

    Runs `git diff --name-only <sha>` which reports all changes (staged +
    unstaged + committed-since-checkpoint) relative to the checkpoint.

    Returns empty list on any subprocess failure (caller decides severity).
    Raises RuntimeError on non-zero git exit.
    """
    result = subprocess.run(
        ["git", "diff", "--name-only", checkpoint_sha],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=_GIT_TIMEOUT,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "git diff failed (exit {0}): {1}".format(
                result.returncode, result.stderr.strip()
            )
        )
    lines = [ln.strip() for ln in result.stdout.splitlines() if ln.strip()]
    return lines


def _git_untracked_files(cwd):
    # type: (str) -> List[str]
    """Return untracked files from `git status --porcelain`.

    Lines starting with '??' are untracked; extract the path portion (after
    the two-character status code and a space).

    Returns empty list on any subprocess failure.
    Raises RuntimeError on non-zero git exit.
    """
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=_GIT_TIMEOUT,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "git status failed (exit {0}): {1}".format(
                result.returncode, result.stderr.strip()
            )
        )
    paths = []
    for line in result.stdout.splitlines():
        # porcelain format: 'XY path' where XY is 2-char status code.
        # '?? path' = untracked.
        if line.startswith("??"):
            # Strip the leading '?? ' prefix (exactly 3 chars).
            path = line[3:].strip()
            # git --porcelain quotes paths containing spaces or non-ASCII chars
            # (e.g. '?? "my file.ts"'). Strip surrounding double-quotes so the
            # path round-trips cleanly for prefix-matching in verify-touched.
            # Note: git also backslash-escapes inner chars inside quoted paths
            # (e.g. '\"'), but the surrounding-quote strip covers the common
            # space case without needing a full unescape pass.
            if path.startswith('"') and path.endswith('"'):
                path = path[1:-1]
            # Strip optional trailing '/' from directory entries.
            path = path.rstrip("/")
            if path:
                paths.append(path)
    return paths


# ---------------------------------------------------------------------------
# Public command
# ---------------------------------------------------------------------------


def cmd_capture_touched_files(args):
    # type: (object) -> int
    """Capture files changed since the checkpoint and emit a JSON list.

    Combines git diff (tracked changes) + git status (new untracked files)
    to produce the complete union of files the agent touched.

    In wrapper mode (PROJECT_ROOT != "."), all git operations run against
    the **source** repo so only source-relative paths are returned — never
    install/forge churn or the nested source dir as a single entry.
    In standalone mode (PROJECT_ROOT == "."), behaviour is identical to
    before this change (source_root == install_root).
    """
    checkpoint = args.checkpoint
    install_root_str = getattr(args, "root", None) or "."

    # Validate checkpoint SHA before calling git.
    if not checkpoint or not _validate_sha(checkpoint):
        sys.stderr.write(
            "capture-touched-files: --checkpoint must be a 4-40 char hex SHA, "
            "got: {0!r}\n".format(checkpoint)
        )
        return EXIT_USAGE

    # Resolve the workspace so git ops target the source repo.
    workspace = resolve_workspace(install_root_str)
    source_cwd = str(workspace.source_root)

    # FIX 1: in wrapper mode the source_root might not exist if PROJECT_ROOT
    # points at an un-cloned directory.  Catch that here with a clear message
    # rather than letting subprocess.run(cwd=<missing>) raise FileNotFoundError
    # which we would misreport as "git not found on PATH".
    if workspace.is_wrapper and not workspace.source_root.exists():
        sys.stderr.write(
            "capture-touched-files: configured source root does not exist: "
            "{0} (check PROJECT_ROOT in .devforge/project-config.json)\n".format(
                workspace.source_root
            )
        )
        return EXIT_ERR

    try:
        diff_files = _git_diff_files(checkpoint, source_cwd)
    except RuntimeError as exc:
        sys.stderr.write("capture-touched-files: {0}\n".format(exc))
        return EXIT_ERR
    except subprocess.TimeoutExpired:
        sys.stderr.write("capture-touched-files: git diff timed out\n")
        return EXIT_ERR
    except FileNotFoundError:
        sys.stderr.write("capture-touched-files: git not found on PATH\n")
        return EXIT_ERR

    try:
        untracked = _git_untracked_files(source_cwd)
    except RuntimeError as exc:
        sys.stderr.write("capture-touched-files: {0}\n".format(exc))
        return EXIT_ERR
    except subprocess.TimeoutExpired:
        sys.stderr.write("capture-touched-files: git status timed out\n")
        return EXIT_ERR
    except FileNotFoundError:
        sys.stderr.write("capture-touched-files: git not found on PATH\n")
        return EXIT_ERR

    # Union: preserve order (diff files first, then new untracked), de-dup.
    seen = set()
    result = []
    for path in diff_files + untracked:
        if path not in seen:
            seen.add(path)
            result.append(path)

    sys.stdout.write(json.dumps(result))
    sys.stdout.write("\n")
    return EXIT_OK


# ---------------------------------------------------------------------------
# Argparse registration (called from _cli.py)
# ---------------------------------------------------------------------------


def add_args_capture_touched_files(parser):
    # type: (object) -> None
    """Add arguments for capture-touched-files to the subparser."""
    parser.add_argument(
        "--checkpoint",
        required=True,
        help=(
            "Git SHA of the pre-task checkpoint commit (from preflight output). "
            "Used as the baseline for git diff to detect touched files."
        ),
    )
    parser.add_argument(
        "--root",
        default=None,
        help=(
            "Install root directory. Defaults to the current working directory. "
            "The source root is resolved from this via .devforge/project-config.json "
            "PROJECT_ROOT; git diff and git status run against the source root."
        ),
    )
