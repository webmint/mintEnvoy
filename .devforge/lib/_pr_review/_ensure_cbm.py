"""CBM index state detection for pr_review_helper.

`run(target, devforge_dir)` invokes `cbm_sync_helper check` as a
subprocess, parses the state token it emits on stdout, and returns a
structured dict the LLM orchestrator uses to decide whether the CBM
index needs refreshing before the /pr-review proceeds.

Subprocess boundary:
  The helper is invoked as:
    [sys.executable, <path-to-cbm_sync_helper.py>, "check"]
  with DEVFORGE_DIR set in the subprocess environment so cbm_sync_helper
  resolves the stamp file relative to `target/<devforge_dir>/` rather
  than relative to the helper's own location.

  Using subprocess (rather than a direct import + function call) keeps
  the boundary clean: cbm_sync_helper owns its own path-resolution
  logic, and no coupling to its internal `_stamp_path()` is introduced
  here. Tests can mock `subprocess.run` without touching cbm_sync_helper.

State token → result mapping (single canonical mapping, no escape hatches):
  current        → status ok,           next_action none,                 mcp_tool_hint null
  drift <a>..<b> → status stale,        next_action run-detect-changes,   mcp_tool_hint mcp__codebase-memory-mcp__detect_changes
  missing        → status absent,       next_action run-index-repository, mcp_tool_hint mcp__codebase-memory-mcp__index_repository
  not-a-git-repo → status not-a-git-repo, next_action setup-cbm,         mcp_tool_hint null

Cost estimate for `missing` case:
  Counts source files with target extensions under `target` (capped at
  10000 to bound scan time). Applies a $1/1000-files rule-of-thumb
  (rough Haiku-pricing heuristic — document in field, not guaranteed).
  Result rounded to 2 decimal places.

Stdlib only. Targets Python 3.8+.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Extensions counted for the indexing-cost heuristic.
# $1 per ~1000 files is a rule-of-thumb; actual Haiku cost depends on
# token count per file, not raw file count.
_COST_EXTENSIONS = frozenset(
    [".py", ".ts", ".tsx", ".vue", ".go", ".java", ".rb", ".rs"]
)
_COST_PER_1000_FILES = 1.0
_COST_FILE_CAP = 10000


# ---------------------------------------------------------------------------
# Locate cbm_sync_helper.py relative to this module.
# ---------------------------------------------------------------------------

# cbm_sync_helper.py lives in the same lib directory as this package:
#   src/devforge/lib/cbm_sync_helper.py
# This module lives at:
#   src/devforge/lib/_pr_review/_ensure_cbm.py
# So the lib dir is two levels up from this file.
_LIB_DIR = Path(__file__).resolve().parent.parent
_CBM_SYNC_HELPER = _LIB_DIR / "cbm_sync_helper.py"


# ---------------------------------------------------------------------------
# Internal helpers.
# ---------------------------------------------------------------------------


def _estimate_indexing_cost(target: str) -> float:
    """Estimate CBM indexing cost for `target` based on source-file count.

    Walks `target` and counts files whose extension is in _COST_EXTENSIONS.
    Stops counting at _COST_FILE_CAP files (10000) to bound scan time.
    Returns cost in USD rounded to 2 decimals: count / 1000 * _COST_PER_1000_FILES.

    This is a rule-of-thumb only; actual cost depends on token count.
    """
    count = 0
    for dirpath, _dirnames, filenames in os.walk(target):
        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext in _COST_EXTENSIONS:
                count += 1
                if count >= _COST_FILE_CAP:
                    return round(_COST_FILE_CAP / 1000.0 * _COST_PER_1000_FILES, 2)
    return round(count / 1000.0 * _COST_PER_1000_FILES, 2)


def _parse_token(raw: str) -> str:
    """Strip and return the first line of raw cbm_sync_helper stdout."""
    return raw.strip().splitlines()[0].strip() if raw.strip() else ""


def _token_to_result(
    token: str,
    target: str,
    cost_estimate: Optional[float],
) -> dict:
    """Map a cbm_sync_helper state token to the structured result dict.

    Single canonical mapping per module docstring. token is the raw
    first-line output from `cbm_sync_helper check`.

    cost_estimate is only used for the `missing` branch; pass None for
    other branches (caller controls when to compute it).
    """
    if token == "current":
        return {
            "cbm_state_token": token,
            "cost_estimate_usd": None,
            "mcp_tool_hint": None,
            "next_action": "none",
            "status": "ok",
            "target_path": os.path.abspath(target),
        }

    if token.startswith("drift "):
        return {
            "cbm_state_token": token,
            "cost_estimate_usd": None,
            "mcp_tool_hint": "mcp__codebase-memory-mcp__detect_changes",
            "next_action": "run-detect-changes",
            "status": "stale",
            "target_path": os.path.abspath(target),
        }

    if token == "missing":
        return {
            "cbm_state_token": token,
            "cost_estimate_usd": cost_estimate,
            "mcp_tool_hint": "mcp__codebase-memory-mcp__index_repository",
            "next_action": "run-index-repository",
            "status": "absent",
            "target_path": os.path.abspath(target),
        }

    # Covers "not-a-git-repo" and any unexpected token from cbm_sync_helper.
    # Both map to the setup-cbm action with null hint (no CBM op makes sense).
    return {
        "cbm_state_token": token,
        "cost_estimate_usd": None,
        "mcp_tool_hint": None,
        "next_action": "setup-cbm",
        "status": "not-a-git-repo",
        "target_path": os.path.abspath(target),
    }


# ---------------------------------------------------------------------------
# Public entry point.
# ---------------------------------------------------------------------------


def run(target: str, devforge_dir: str = ".devforge") -> dict:
    """Invoke cbm_sync_helper check and return a structured CBM state dict.

    Args:
        target:       Absolute path to the repository root.
        devforge_dir: Name of the devforge directory (default ".devforge").
                      Passed as DEVFORGE_DIR env so cbm_sync_helper resolves
                      the stamp file under target/<devforge_dir>/.

    Returns a dict with keys:
      status            — "ok" | "stale" | "absent" | "not-a-git-repo"
      cbm_state_token   — raw token from cbm_sync_helper check
      next_action       — "none" | "run-detect-changes" | "run-index-repository" | "setup-cbm"
      mcp_tool_hint     — MCP tool name string or null
      cost_estimate_usd — float or null
      target_path       — absolute path of target (normalized)

    Raises:
        OSError / subprocess-related exceptions if cbm_sync_helper.py cannot
        be found or the subprocess fails to launch. The _cli layer catches
        these and emits a non-zero exit code.

    Non-zero subprocess exit with empty stdout is mapped to `not-a-git-repo`
    status (helper failure surfaces same as missing git repo from the LLM's
    perspective; both require setup-cbm action).
    """
    abs_target = os.path.abspath(target)
    abs_devforge = os.path.join(abs_target, devforge_dir)

    # Inject DEVFORGE_DIR so cbm_sync_helper._stamp_path() resolves the stamp
    # under the target repo's .devforge/, not relative to its own __file__.
    env = dict(os.environ)
    env["DEVFORGE_DIR"] = abs_devforge

    result = subprocess.run(
        [sys.executable, str(_CBM_SYNC_HELPER), "check"],
        capture_output=True,
        text=True,
        cwd=abs_target,
        env=env,
    )

    stdout = result.stdout.strip()
    if result.returncode != 0 and not stdout:
        # Subprocess crashed without producing output. Map explicitly to
        # not-a-git-repo (preserves prior behavior + bounded blast), but make
        # the assignment intentional rather than fallthrough.
        token = "not-a-git-repo"
    else:
        token = _parse_token(result.stdout)

    # Compute cost estimate only for the missing case (avoids expensive scan
    # when not needed).
    cost_estimate: Optional[float] = None
    if token == "missing":
        cost_estimate = _estimate_indexing_cost(abs_target)

    return _token_to_result(token, abs_target, cost_estimate)
