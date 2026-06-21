"""_cmds_commit -- wip-commit verb for implement_helper and fix_helper.

Stage only the explicitly named paths, compose a commit message per
wrapper/standalone convention, and commit.  After a successful commit,
clear the wip.md marker.

Two modes
---------
TASK mode (/implement):   --files + --task-file + --index + --number + --title all present.
  Stages source touched_files + task_file + index (standalone) or only source
  touched_files (wrapper).  Message: "[WIP] task: <title> (Task NNN)" (standalone)
  / "[TICKET-ID] - <title> (Task NNN)" (wrapper).

FIX mode (/fix):          --files + --title present; --task-file, --index, --number ALL absent.
  Stages ONLY the touched files in both standalone and wrapper mode (there is no
  task file or index to stage).  Message: "[WIP] fix: <title>" (standalone)
  / "[TICKET-ID] - <title>" (wrapper; no "(Task NNN)" suffix).

MIXED (some but not all of --task-file/--index/--number present): rejected with
  EXIT_ERR and a clear stderr message naming the missing arguments.

Algorithm
---------
1. Parse --files (JSON array).  Mode detection (task / fix / mixed) from
   --task-file, --index, --number.
2. Resolve workspace via resolve_workspace(--root): gives install_root,
   source_root, is_wrapper.  Config is loaded from install_root.
3. Read .devforge/project-config.json for COMMIT_ATTRIBUTION.
4. Derive TICKET-ID:
   - WRAPPER mode: run `git -C <source_root> rev-parse --abbrev-ref HEAD`
     to get the SOURCE repo branch; extract [A-Z]+-[0-9]+ ticket token
     (e.g. `bugfix/MIG-123` → `MIG-123`); fall back to full branch name.
   - STANDALONE mode: ticket-id is unused (non-wrapper message format).
5. Compose message per mode (see Two modes above).
6. Append COMMIT_ATTRIBUTION: in STANDALONE mode, append verbatim when non-empty
   (empty/absent → no append). In WRAPPER mode, NO attribution is appended — the
   SOURCE repo commit must carry no AI traces (D5 / Phase 6 belt-and-suspenders).
   Attribution rules are IDENTICAL in task and fix modes.
7. Stage paths individually (`git add -- <path>`). NEVER `git add -A`.
   TASK mode:
   - WRAPPER: stage ONLY source touched_files in the SOURCE repo (task_file and
     index are wrapper artifacts, left uncommitted per D1).
   - STANDALONE: stage source touched_files + task_file + index together.
   FIX mode (both wrapper and standalone): stage ONLY source touched_files.
8. Commit in the TARGET repo:
   - WRAPPER mode:   `git -C <source_root> commit -m <msg>` in SOURCE repo.
   - STANDALONE mode: `git commit -m <msg>` (single repo).
9. Capture the new HEAD SHA from the TARGET repo.
10. Clear wip.md in the INSTALL root (wrapper artifacts, always install-root).
11. Emit JSON {committed: true, head_sha: "...", message: "..."} to stdout.

Arguments (argparse):
  --files     <json>   Required. JSON array of source-relative touched file paths.
  --task-file <path>   Optional. Path to the task .md file (install-root-relative
                       in wrapper mode; not staged there per D1).  All three of
                       --task-file, --index, --number must be given together or
                       not at all; giving a subset is a mixed-mode error.
  --index     <path>   Optional. Path to tasks/README.md index file (install-root-
                       relative in wrapper mode; not staged per D1).
  --number    <str>    Optional. Task number string, e.g. "001".
  --title     <str>    Required. Task title.
  --root      <path>   Optional. Install root; defaults to cwd.

Emitted JSON (stdout, exit 0):
  {"committed": true, "head_sha": "<sha>", "message": "<msg>"}

Exit codes:
  0 — committed successfully.
  1 — I/O / config error (message on stderr).
  2 — git staging or commit failure (message on stderr).

Design notes:
- D1 (wrapper mode): only source touched_files are staged and committed per
  task; task_file and index (wrapper artifacts) are written by mark-complete
  but NOT committed by wip-commit in wrapper mode.  The wrapper tree accumulates
  those changes separately (not auto-committed per task, per D1 of the plan).
- D2 (ticket-id source): in wrapper mode the TICKET-ID derives from the SOURCE
  repo's branch name, not the wrapper branch.  The wrapper branch (spec/NNN-…)
  is irrelevant to the source repo commit message.
- TICKET-ID pattern [A-Z]+-[0-9]+: industry-standard Jira-style ticket pattern.
  Applied after stripping path prefixes:
    bugfix/MIG-123-desc → MIG-123
    PROJ-42-do-thing    → PROJ-42
    develop-no-ticket   → fallback = full branch name
- WORKSPACE_MODE key: project-config.json stores workspace mode as
  "WORKSPACE_MODE" (uppercase). Value "wrapper" means wrapper mode is active.
  resolve_workspace() is the canonical detector (via PROJECT_ROOT); WORKSPACE_MODE
  is consulted for compatibility when the config contains it.
- COMMIT_ATTRIBUTION: stored verbatim in project-config.json. May be an empty
  string (ai_attribution == "No") or "\\n\\nCo-Authored-By: Claude <...>". In
  STANDALONE mode the value is appended directly to the message body (no extra
  newline added); if absent (key not in config), no attribution line is added.
  In WRAPPER mode attribution is SUPPRESSED entirely — the source-repo WIP commit
  must carry no AI traces (D5 / Phase 6).  These rules apply equally in task and
  fix modes.
- Staging safety: each path is staged individually so an unrelated dirty file
  in the working tree is NEVER committed.  git add -A is never used.
- subprocess timeout: 30 s per git call. Generous but bounded.
- git -C <path>: used for all source-repo operations in wrapper mode so the
  implementation never changes the process working directory.

Stdlib only. Python 3.8+.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

from _implement._wip import clear_wip_marker  # type: ignore[import]
from _implement._workspace import resolve_workspace  # type: ignore[import]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXIT_OK = 0
EXIT_ERR = 1
EXIT_FINDINGS = 2

# Helper-owned ticket-token regex: matches Jira-style PROJ-123 tokens.
# Requires all-uppercase letter prefix, dash, one-or-more digits.
_TICKET_PATTERN = re.compile(r"\b([A-Z]+-[0-9]+)\b")

# Timeout (seconds) for git subprocess calls.
_GIT_TIMEOUT = 30

# The project-config.json key for commit attribution.
_COMMIT_ATTRIBUTION_KEY = "COMMIT_ATTRIBUTION"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_project_config(root):
    # type: (Path) -> dict
    """Load .devforge/project-config.json relative to root.

    Returns an empty dict if the file is absent (config is optional —
    caller falls back to defaults). Raises ValueError on malformed JSON.
    """
    config_path = root / ".devforge" / "project-config.json"
    if not config_path.exists():
        return {}
    try:
        with open(str(config_path), "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Malformed .devforge/project-config.json: {0}".format(exc)
        )


def _get_commit_attribution(config):
    # type: (dict) -> str
    """Return COMMIT_ATTRIBUTION from config, or '' if absent/empty."""
    val = config.get(_COMMIT_ATTRIBUTION_KEY, "")
    if not val:
        return ""
    return val


def _current_branch(repo_root):
    # type: (Path) -> Optional[str]
    """Return the current git branch name in repo_root, or None on failure.

    Uses 'git -C <repo_root>' so the caller can target either the install
    repo or the source repo without changing the process working directory.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_TIMEOUT,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip() or None
    except (subprocess.TimeoutExpired, OSError):
        return None


def _extract_ticket_id(branch):
    # type: (str) -> str
    """Extract a Jira-style ticket token from branch name, or return branch.

    Pattern: [A-Z]+-[0-9]+
    Examples:
      spec/PROJ-123-slugify-feature  → PROJ-123
      PROJ-42-do-thing               → PROJ-42
      develop-2.0-init               → develop-2.0-init (no match)
      feature/ABC-99                 → ABC-99
    """
    m = _TICKET_PATTERN.search(branch)
    if m:
        return m.group(1)
    # No ticket token found: use full branch name as fallback.
    return branch


def _compose_message(is_wrapper, ticket_id, title, number, attribution,
                     fix_mode=False):
    # type: (bool, str, str, str, str, bool) -> str
    """Compose the commit message with optional attribution.

    Task mode (fix_mode=False):
      wrapper:     "[TICKET-ID] - <title> (Task NNN)"
      non-wrapper: "[WIP] task: <title> (Task NNN)"

    Fix mode (fix_mode=True):
      wrapper:     "[TICKET-ID] - <title>"    (no "(Task NNN)" suffix)
      non-wrapper: "[WIP] fix: <title>"       (no "(Task NNN)" suffix)

    Attribution is appended verbatim when non-empty (identical rule for both modes).
    """
    if fix_mode:
        if is_wrapper:
            subject = "[{0}] - {1}".format(ticket_id, title)
        else:
            subject = "[WIP] fix: {0}".format(title)
    else:
        if is_wrapper:
            subject = "[{0}] - {1} (Task {2})".format(ticket_id, title, number)
        else:
            subject = "[WIP] task: {0} (Task {1})".format(title, number)

    if attribution:
        return subject + attribution
    return subject


def _git_stage_path(repo_root, path_str):
    # type: (Path, str) -> Optional[str]
    """Stage a single file path via `git -C <repo_root> add -- <path>`.

    Returns None on success, error message string on failure.
    path_str may be relative (to repo_root) or absolute.

    Uses 'git -C <repo_root>' so the caller can target either the install
    repo or the source repo without changing the process working directory.
    Precise staging: only the explicitly named path is staged (never add -A).
    """
    # Resolve relative paths against repo_root.
    p = Path(path_str)
    if not p.is_absolute():
        p = repo_root / p

    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "add", "--", str(p)],
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_TIMEOUT,
        )
        if result.returncode != 0:
            return "git add {0!r} failed (rc={1}): {2}".format(
                path_str, result.returncode, (result.stderr or result.stdout).strip()
            )
        return None
    except subprocess.TimeoutExpired:
        return "git add {0!r} timed out".format(path_str)
    except OSError as exc:
        return "git add {0!r} OS error: {1}".format(path_str, exc)


def _git_commit(repo_root, message):
    # type: (Path, str) -> Optional[str]
    """Create a commit with the given message in repo_root.

    Returns None on success, error message string on failure.
    Uses 'git -C <repo_root>' so the caller can target either the install
    repo or the source repo without changing the process working directory.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "commit", "-m", message],
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_TIMEOUT,
        )
        if result.returncode != 0:
            return "git commit failed (rc={0}): {1}".format(
                result.returncode, (result.stderr or result.stdout).strip()
            )
        return None
    except subprocess.TimeoutExpired:
        return "git commit timed out"
    except OSError as exc:
        return "git commit OS error: {0}".format(exc)


def _git_head_sha(repo_root):
    # type: (Path) -> Optional[str]
    """Return the current HEAD SHA of repo_root, or None on failure.

    Uses 'git -C <repo_root>' so the caller can target either the install
    repo or the source repo without changing the process working directory.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_TIMEOUT,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip() or None
    except (subprocess.TimeoutExpired, OSError):
        return None


# ---------------------------------------------------------------------------
# argparse setup
# ---------------------------------------------------------------------------


def add_args_wip_commit(parser):
    # type: (object) -> None
    """Register wip-commit arguments on the given subparser.

    Two modes are supported:
      Task mode (/implement): --files + --task-file + --index + --number + --title.
      Fix mode  (/fix):       --files + --title only (--task-file/--index/--number absent).
    Providing some but not all of --task-file/--index/--number is rejected at
    runtime with EXIT_ERR (mixed-mode error).
    """
    parser.add_argument(
        "--files",
        required=True,
        help="JSON array of touched file paths to stage.",
    )
    parser.add_argument(
        "--task-file",
        required=False,
        default="",
        dest="task_file",
        help=(
            "Path to the task .md file to stage (task mode only). "
            "Must be given together with --index and --number, or not at all."
        ),
    )
    parser.add_argument(
        "--index",
        required=False,
        default="",
        help=(
            "Path to tasks/README.md index file to stage (task mode only). "
            "Must be given together with --task-file and --number, or not at all."
        ),
    )
    parser.add_argument(
        "--number",
        required=False,
        default="",
        help=(
            "Task number string, e.g. '001' (task mode only). "
            "Must be given together with --task-file and --index, or not at all."
        ),
    )
    parser.add_argument(
        "--title",
        required=True,
        help="Task title string (required in both task and fix modes).",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repo root directory. Defaults to cwd.",
    )


# ---------------------------------------------------------------------------
# Command handler
# ---------------------------------------------------------------------------


def cmd_wip_commit(args):
    # type: (object) -> int
    """Stage named paths and create a WIP commit (task mode or fix mode).

    Task mode (/implement) — all of --task-file, --index, --number are present:
      In WRAPPER mode:
        - Ticket-id derived from the SOURCE repo branch (D2).
        - Stage ONLY source touched_files in the SOURCE repo (D1).
        - task_file and index are NOT staged (wrapper artifacts, left uncommitted per D1).
        - Commit lands in the SOURCE repo.
        - wip.md is cleared in the INSTALL root.
        - Emitted head_sha is the SOURCE repo's new HEAD.
      In STANDALONE mode:
        - Stage source touched_files + task_file + index all in the single repo.
        - Message: "[WIP] task: <title> (Task NNN)".

    Fix mode (/fix) — none of --task-file, --index, --number are present:
      Stage ONLY source touched_files in both wrapper and standalone mode.
      Message: "[WIP] fix: <title>" (standalone) / "[TICKET-ID] - <title>" (wrapper).
      Attribution and ticket-id derivation are identical to task mode.
      No "(Task NNN)" suffix.

    Mixed mode (some but not all of --task-file/--index/--number present):
      Rejected immediately with EXIT_ERR and a descriptive stderr message.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed arguments: files, task_file, index, number, title, root.

    Returns
    -------
    int
        0 on success; 1 on config/I/O error; 2 on git failure.
    """
    install_root = Path(getattr(args, "root", ".")).resolve()

    # --- Resolve workspace (single source of truth for repo targeting) ---
    workspace = resolve_workspace(install_root)

    # --- Parse --files JSON ---
    files_json = getattr(args, "files", "[]")
    try:
        touched = json.loads(files_json)
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "wip-commit: --files is not valid JSON: {0}\n".format(exc)
        )
        return EXIT_ERR
    if not isinstance(touched, list):
        sys.stderr.write(
            "wip-commit: --files must be a JSON array, got {0}\n".format(
                type(touched).__name__
            )
        )
        return EXIT_ERR

    task_file = getattr(args, "task_file", "") or ""
    index = getattr(args, "index", "") or ""
    number = getattr(args, "number", "") or ""
    title = getattr(args, "title", "") or ""

    if not title:
        sys.stderr.write("wip-commit: --title is required\n")
        return EXIT_ERR

    # --- Mode detection ---
    task_present = bool(task_file) and bool(index) and bool(number)
    task_absent = (not task_file) and (not index) and (not number)

    if not task_present and not task_absent:
        # Mixed: some but not all of --task-file/--index/--number were given.
        missing = []
        if not task_file:
            missing.append("--task-file")
        if not index:
            missing.append("--index")
        if not number:
            missing.append("--number")
        sys.stderr.write(
            "wip-commit: mixed mode — provide all of --task-file, --index, "
            "--number (task mode) or none of them (fix mode). "
            "Missing: {0}\n".format(", ".join(missing))
        )
        return EXIT_ERR

    fix_mode = task_absent  # True → fix mode; False → task mode

    # --- Load project config (from install_root where .devforge/ lives) ---
    try:
        config = _load_project_config(workspace.install_root)
    except ValueError as exc:
        sys.stderr.write("wip-commit: config error: {0}\n".format(exc))
        return EXIT_ERR

    is_wrapper = workspace.is_wrapper
    attribution = _get_commit_attribution(config)

    # --- Determine the commit target repo and ticket-id ---
    if is_wrapper:
        # D2: ticket-id from the SOURCE repo's branch (where code commits land).
        commit_repo = workspace.source_root
        branch = _current_branch(workspace.source_root)
        if branch:
            ticket_id = _extract_ticket_id(branch)
        else:
            ticket_id = "UNKNOWN"
    else:
        # Standalone: single repo; ticket-id unused (non-wrapper message format).
        commit_repo = workspace.install_root  # install_root == source_root
        ticket_id = ""

    # --- Compose commit message ---
    # D5 (Phase 6 belt-and-suspenders): the SOURCE (product) repo WIP commit
    # must carry NO AI traces regardless of the COMMIT_ATTRIBUTION config.
    # In wrapper mode the commit lands in the source repo, so attribution is
    # suppressed here.  In standalone mode attribution is applied normally —
    # the single repo follows the Commit Convention the user opted into.
    # Attribution suppression rule is identical in task and fix modes.
    message_attribution = "" if is_wrapper else attribution
    message = _compose_message(
        is_wrapper, ticket_id, title, number, message_attribution,
        fix_mode=fix_mode,
    )

    # --- Stage paths individually (NEVER git add -A) ---
    if is_wrapper or fix_mode:
        # Wrapper task mode (D1): stage ONLY the source touched_files in the SOURCE repo.
        #   task_file and index are wrapper artifacts — they are NOT staged here.
        #   mark-complete already wrote them to disk.
        # Fix mode (both wrapper and standalone): no task_file or index exists;
        #   stage ONLY source touched_files.
        seen = set()  # type: ignore
        to_stage = []  # type: List[str]
        for p in list(touched):
            if p and p not in seen:
                seen.add(p)
                to_stage.append(p)
    else:
        # Standalone task mode: stage source touched_files + task_file + index together.
        seen = set()
        to_stage = []
        for p in list(touched) + [task_file, index]:
            if p and p not in seen:
                seen.add(p)
                to_stage.append(p)

    for path_str in to_stage:
        err = _git_stage_path(commit_repo, path_str)
        if err is not None:
            sys.stderr.write("wip-commit: staging failed: {0}\n".format(err))
            return EXIT_FINDINGS

    # --- Commit (in the target repo) ---
    err = _git_commit(commit_repo, message)
    if err is not None:
        sys.stderr.write("wip-commit: {0}\n".format(err))
        return EXIT_FINDINGS

    # --- Capture new HEAD SHA from the target repo ---
    head_sha = _git_head_sha(commit_repo)
    if head_sha is None:
        sys.stderr.write(
            "wip-commit: commit succeeded but could not read HEAD SHA\n"
        )
        return EXIT_ERR

    # --- Clear wip.md (always in the INSTALL root's .devforge/) ---
    devforge_dir = workspace.install_root / ".devforge"
    try:
        clear_wip_marker(str(devforge_dir))
    except OSError as exc:
        # Non-fatal: commit already succeeded; warn but don't fail.
        sys.stderr.write(
            "wip-commit: warning: could not clear wip.md: {0}\n".format(exc)
        )

    # --- Emit result JSON ---
    result = {
        "committed": True,
        "head_sha": head_sha,
        "message": message,
    }
    sys.stdout.write(json.dumps(result) + "\n")
    return EXIT_OK
