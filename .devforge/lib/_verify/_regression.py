"""_regression.py — baseline-diff regression gate for /verify.

Runs a baseline-diff regression check: compares the test suite exit code at
the feature's merge-base with the exit code at HEAD.  Only triggers a NEEDS
WORK blocker when the suite was PASSING at the merge-base and is FAILING now
(green→red only).  Pre-existing failures at the merge-base are reported, never
gated — this is the core false-positive guard.

Public surface
--------------
  run_regression_gate(feature_dir, workspace_root, mode=None) -> dict

      Fail-soft: always returns a dict, never raises.  Exit code semantics are
      handled by the CLI verb (cmd_regression_gate in _cli.py), which always
      returns 0 on success and 2 only on bad-arg usage.

      Parameters
      ----------
      feature_dir : str
          Path to the feature directory (context only — not used for git ops).
      workspace_root : str
          Absolute path to the install root (where .devforge/ lives).
      mode : str or None
          "full" | "off" override.  When None, reads REGRESSION_GATE from
          .devforge/project-config.json (default "full" when the key is absent).

      Returns
      -------
      dict with keys:
        status          : str  — "off" | "inconclusive" | "clean" |
                                  "baseline-failing" | "regression"
        regression      : bool — True only when status == "regression"
        mode            : str  — effective mode applied
        baseline_status : str or None  — "pass" | "fail" | None (not run)
        head_status     : str or None  — "pass" | "fail" | None (not run)
        note            : str  — human-readable explanation (always present)
        head_output_tail: str  — last 50 lines of combined stdout+stderr from
                                  the HEAD test run (present only on regression)

Worktree lifecycle guarantee
----------------------------
A git worktree is created under the system temp directory (NOT inside the
repo) for the baseline run.  The worktree is removed in a try/finally block
so it is never left dangling regardless of exceptions, KeyboardInterrupt, or
test-run failures.

Merge-base resolution
---------------------
Reuses the git helpers from _shared.feature_scope rather than re-implementing
merge-base resolution.  The auto-detect precedence is:
  1. origin/HEAD (git symbolic-ref refs/remotes/origin/HEAD)
  2. local branch "main"
  3. local branch "develop"
  4. local branch "master"

If no base resolves, the gate is inconclusive (not gating).

MVP scope
---------
The test command used is TEST_COMMANDS[0] from project-config.json (the
primary-stack test runner).  Per-package test_command aggregation would
require running K test commands per baseline+HEAD pair, which multiplies
wall-clock cost.

# TODO(refinement): aggregate per-package TEST_COMMANDS (each PACKAGE_STACKS
# entry's test_command field) and run each one for a full-spectrum regression
# check.  This requires collecting the union of package test commands and
# running each in the worktree + at HEAD.

Stdlib only.  Python 3.8+.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from typing import Dict, List, Optional, Tuple

# Reuse git helpers from the shared feature_scope module instead of
# re-implementing merge-base resolution.  These helpers are private
# (underscore-prefixed) but stable across this codebase; they are imported
# here rather than duplicated to preserve a single source of truth for
# merge-base logic.  See _shared/feature_scope.py for full documentation.
from _shared.feature_scope import (   # type: ignore[import]
    _autodetect_base,
    _compute_merge_base,
    _git,
    _is_git_repo,
    _resolve_head_sha,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Number of tail lines to capture from the HEAD test run when a regression
# is detected (kept small so the result JSON stays reasonably compact).
_TAIL_LINES = 50

# Max seconds for worktree management git commands (add / remove).
_WORKTREE_TIMEOUT = 120

# Max seconds for a test-command run (both baseline and HEAD).
_TEST_TIMEOUT = 600

# Top-level dependency directories to symlink from source_root into the
# baseline worktree when they exist.  This lets tests run without a full
# reinstall when dependencies have not changed between the merge-base and HEAD.
# Top-level only (MVP scope — nested workspace dep dirs are not linked).
_DEP_DIRS = ("node_modules", ".venv", "venv", "vendor")

# project-config.json key for the regression gate mode setting.
_CONFIG_REGRESSION_GATE_KEY = "REGRESSION_GATE"

# project-config.json key for the primary test commands array.
_CONFIG_TEST_COMMANDS_KEY = "TEST_COMMANDS"


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


def _read_config(workspace_root):
    # type: (str) -> Dict
    """Read .devforge/project-config.json from workspace_root.

    Returns an empty dict on any failure (file absent, malformed JSON, etc.).
    Never raises.
    """
    config_path = os.path.join(workspace_root, ".devforge", "project-config.json")
    try:
        with open(config_path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _get_effective_mode(config, mode_override):
    # type: (Dict, Optional[str]) -> str
    """Return the effective regression gate mode.

    Priority: mode_override argument > REGRESSION_GATE config key > "full".
    """
    if mode_override is not None:
        return mode_override
    return config.get(_CONFIG_REGRESSION_GATE_KEY) or "full"


def _get_test_command(config):
    # type: (Dict) -> Optional[str]
    """Return the primary test command from project-config, or None.

    Returns None when TEST_COMMANDS is absent, empty, or the first element
    is "N/A" or empty.

    # TODO(refinement): aggregate all per-package TEST_COMMANDS (each
    # PACKAGE_STACKS entry's test_command field) and run each one.
    # MVP scope is primary-stack only.
    """
    cmds = config.get(_CONFIG_TEST_COMMANDS_KEY) or []
    if not isinstance(cmds, list) or not cmds:
        return None
    first = (cmds[0] or "").strip()
    if not first or first == "N/A":
        return None
    return first


# ---------------------------------------------------------------------------
# Merge-base resolution
# ---------------------------------------------------------------------------


def _resolve_merge_base(source_root):
    # type: (str) -> Tuple[Optional[str], str]
    """Resolve the feature's merge-base SHA against the trunk branch.

    Reuses helpers from _shared.feature_scope to avoid re-implementing git
    logic.  Auto-detection precedence: origin/HEAD → main → develop → master.

    Returns (merge_base_sha, note) where:
      - On success: (sha, "")
      - On failure: (None, human-readable reason string)
    """
    if not _is_git_repo(source_root):
        return None, "not a git repository: {0!r}".format(source_root)

    head_sha = _resolve_head_sha(source_root)
    if head_sha is None:
        return None, "cannot resolve HEAD (no commits or unborn branch)"

    base = _autodetect_base(source_root)
    if base is None:
        return None, (
            "cannot auto-detect base branch; "
            "none of origin/HEAD, main, develop, master resolve"
        )

    merge_base_sha = _compute_merge_base(base, head_sha, source_root)
    if merge_base_sha is None:
        return None, (
            "git merge-base {0!r} HEAD failed "
            "(shallow clone, no common ancestor, or detached HEAD)".format(base)
        )

    return merge_base_sha, ""


# ---------------------------------------------------------------------------
# Worktree management
# ---------------------------------------------------------------------------


def _add_worktree(source_root, worktree_dir, merge_base_sha):
    # type: (str, str, str) -> Optional[str]
    """Add a git worktree at worktree_dir checked out at merge_base_sha.

    Returns None on success, an error string on failure.
    """
    rc, _, stderr = _git(
        ["worktree", "add", "--detach", worktree_dir, merge_base_sha],
        cwd=source_root,
        timeout=_WORKTREE_TIMEOUT,
    )
    if rc != 0:
        return "git worktree add failed: {0}".format(stderr.strip())
    return None


def _remove_worktree(source_root, worktree_dir):
    # type: (str, str) -> None
    """Remove the git worktree registration and directory.

    Best-effort — never raises.  Called in finally blocks to guarantee
    no dangling worktrees are left after any exit path.

    Two-step cleanup:
      1. git worktree remove --force <dir>  — removes git registration
      2. shutil.rmtree <dir>                — belt-and-suspenders directory cleanup
    """
    try:
        _git(
            ["worktree", "remove", "--force", worktree_dir],
            cwd=source_root,
            timeout=_WORKTREE_TIMEOUT,
        )
    except Exception:  # noqa: BLE001
        pass  # best-effort; shutil.rmtree below handles the directory

    try:
        if os.path.exists(worktree_dir):
            shutil.rmtree(worktree_dir, ignore_errors=True)
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# Dependency symlinking
# ---------------------------------------------------------------------------


def _symlink_deps(source_root, worktree_dir):
    # type: (str, str) -> None
    """Best-effort: symlink top-level dep directories from source_root into the worktree.

    Covers node_modules, .venv, venv, vendor (top-level only, MVP scope).
    If a dep dir does not exist in source_root, the symlink step is silently
    skipped.  If a symlink can't be created (permissions, target already
    exists), the error is silently ignored — tests must not fail solely
    because deps couldn't be linked.
    """
    for dep in _DEP_DIRS:
        src = os.path.join(source_root, dep)
        dst = os.path.join(worktree_dir, dep)
        if not os.path.exists(src):
            continue
        if os.path.exists(dst) or os.path.islink(dst):
            continue
        try:
            os.symlink(src, dst)
        except OSError:
            pass  # best-effort


# ---------------------------------------------------------------------------
# Test-command runner
# ---------------------------------------------------------------------------


def _tail_text(text, n=_TAIL_LINES):
    # type: (str, int) -> str
    """Return the last n lines of text (for output capture)."""
    lines = text.splitlines()
    if not lines:
        return ""
    return "\n".join(lines[-n:])


def _run_test_cmd(cmd, cwd):
    # type: (str, str) -> Tuple[int, str]
    """Run cmd (shell string) in cwd.

    Returns (exit_code, output_tail).  Never raises.
    """
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            shell=True,
            capture_output=True,
            text=True,
            check=False,
            timeout=_TEST_TIMEOUT,
        )
        combined = proc.stdout + proc.stderr
        return proc.returncode, _tail_text(combined)
    except subprocess.TimeoutExpired:
        return 1, "(test command timed out after {0}s)".format(_TEST_TIMEOUT)
    except OSError as exc:
        return 1, "(subprocess error: {0})".format(exc)
    except Exception as exc:  # noqa: BLE001
        return 1, "(unexpected error running test command: {0})".format(exc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_regression_gate(
    feature_dir,     # type: str
    workspace_root,  # type: str
    mode=None,       # type: Optional[str]
):
    # type: (...) -> Dict
    """Run the regression gate and return a result dict.

    Always returns a dict, never raises.  Any internal error is caught and
    reported as status="inconclusive", regression=False.

    See module docstring for full parameter and return-value documentation.
    """
    try:
        return _run_regression_gate_inner(feature_dir, workspace_root, mode)
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "inconclusive",
            "regression": False,
            "mode": mode or "full",
            "baseline_status": None,
            "head_status": None,
            "note": "unexpected error in regression gate: {0}".format(exc),
        }


def _run_regression_gate_inner(feature_dir, workspace_root, mode_override):
    # type: (str, str, Optional[str]) -> Dict
    """Inner implementation; may propagate exceptions — caller wraps in try/except."""
    config = _read_config(workspace_root)
    effective_mode = _get_effective_mode(config, mode_override)

    # --- mode=off: skip everything, return immediately ---
    if effective_mode == "off":
        return {
            "status": "off",
            "regression": False,
            "mode": "off",
            "baseline_status": None,
            "head_status": None,
            "note": "regression gate disabled",
        }

    # --- Resolve workspace (source_root for git operations) ---
    # Uses the same resolve_workspace function that the rest of _verify uses
    # for wrapper-mode support (source_root may differ from workspace_root).
    from _implement._workspace import resolve_workspace  # type: ignore[import]
    ws = resolve_workspace(workspace_root)
    source_root = str(ws.source_root)

    # --- Test command ---
    test_cmd = _get_test_command(config)
    if not test_cmd:
        return {
            "status": "inconclusive",
            "regression": False,
            "mode": effective_mode,
            "baseline_status": None,
            "head_status": None,
            "note": "no test command configured (TEST_COMMANDS absent or N/A)",
        }

    # --- Merge-base resolution ---
    merge_base_sha, note = _resolve_merge_base(source_root)
    if merge_base_sha is None:
        return {
            "status": "inconclusive",
            "regression": False,
            "mode": effective_mode,
            "baseline_status": None,
            "head_status": None,
            "note": note,
        }

    # --- Baseline run (isolated worktree) ---
    # worktree_dir is initialised to None so the finally block can guard
    # against calling _remove_worktree when mkdtemp itself raises.
    worktree_dir = None
    baseline_status = None
    head_status = None
    head_output_tail = ""

    try:
        worktree_dir = tempfile.mkdtemp(prefix="forge-regression-")

        err = _add_worktree(source_root, worktree_dir, merge_base_sha)
        if err:
            # git worktree add failed; return inconclusive.
            # finally still runs and cleans up the empty mkdtemp dir.
            return {
                "status": "inconclusive",
                "regression": False,
                "mode": effective_mode,
                "baseline_status": None,
                "head_status": None,
                "note": err,
            }

        _symlink_deps(source_root, worktree_dir)

        baseline_rc, _baseline_tail = _run_test_cmd(test_cmd, worktree_dir)
        baseline_status = "pass" if baseline_rc == 0 else "fail"

    finally:
        # GUARANTEE: remove the worktree on every exit path — normal return,
        # early return after add-failure, and exception.
        if worktree_dir is not None:
            _remove_worktree(source_root, worktree_dir)

    # --- HEAD run (main working tree, source_root) ---
    head_rc, head_output_tail = _run_test_cmd(test_cmd, source_root)
    head_status = "pass" if head_rc == 0 else "fail"

    # --- Verdict ---

    # Pre-existing failure: baseline was already failing — not gating.
    if baseline_status == "fail":
        return {
            "status": "baseline-failing",
            "regression": False,
            "mode": effective_mode,
            "baseline_status": baseline_status,
            "head_status": head_status,
            "note": (
                "baseline already failing at merge-base — "
                "regression gate inconclusive, not gating"
            ),
        }

    # Both passing: clean, no regression.
    if head_status == "pass":
        return {
            "status": "clean",
            "regression": False,
            "mode": effective_mode,
            "baseline_status": baseline_status,
            "head_status": head_status,
            "note": "test suite passing at both merge-base and HEAD",
        }

    # baseline pass + head fail: genuine regression.
    return {
        "status": "regression",
        "regression": True,
        "mode": effective_mode,
        "baseline_status": baseline_status,
        "head_status": head_status,
        "note": (
            "test suite was PASSING at merge-base and is now FAILING at HEAD"
        ),
        "head_output_tail": head_output_tail,
    }
