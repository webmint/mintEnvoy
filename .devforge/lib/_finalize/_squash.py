"""_squash.py — squash-base resolution, already-pushed guard, and squash execution.

Phase 2 ships two read/compute verbs (NO git history mutation):

  resolve-squash-base
      Compute the commit SHA to squash back to:
      - Wrapper/install repo, feature branch case:
            use the _shared merge-base (git merge-base HEAD <DEFAULT_BRANCH>).
      - Wrapper/install repo, on-DEFAULT_BRANCH case (no feature branch):
            find the oldest [checkpoint] commit's parent as the squash base.
      - Source repo (wrapper mode):
            use the _shared merge-base scoped to source_root (replaces the
            draft finalize.md's grep-based source-repo base detection at :39).
      Returns a dict with keys:
        install_squash_base   str or None  — SHA to squash to in the install repo
        source_squash_base    str or None  — SHA to squash to in the source repo (None in standalone)
        strategy              str          — "merge-base" | "checkpoint-parent" | "none"
        is_feature_branch     bool         — True when HEAD is not on DEFAULT_BRANCH
        default_branch        str or None  — the detected/resolved DEFAULT_BRANCH name
        error                 str or None  — present and non-None only on fatal failure

  check-pushed
      Detect whether the current feature's commits have already been pushed to
      the remote (origin/<branch>..HEAD).  Pushed commits must NOT be squashed
      (rewriting shared history is forbidden).
      Returns a dict with keys:
        is_pushed             bool  — True when origin/<branch>..HEAD is empty —
                                      i.e. all HEAD commits are already on
                                      origin/<branch> (commit_count == 0).
                                      Safe-to-squash = NOT is_pushed.
        commit_count          int   — number of commits in origin/<branch>..HEAD
        branch                str or None  — current branch name
        no_upstream           bool  — True when the remote or upstream doesn't exist
        error                 str or None  — present and non-None only on fatal failure

Phase 3 adds the git-mutating squash verb:

  squash
      Squash WIP/checkpoint commits into one clean commit.
      Guards (enforced in-helper, regardless of what the orchestrator does):
        1. --confirm required: without it, emits a dry-run preview JSON and exits 0
           with confirmed=false.  NO history mutation without explicit confirmation.
        2. Already-pushed refusal: re-runs check_pushed per repo; refuses squash for
           any repo whose commits are already on the remote (don't rewrite shared history).
        3. No-op when nothing to squash: each repo's no-op is determined by ITS OWN
           squash base — install strategy="none" does NOT short-circuit the source
           repo in wrapper mode if the source repo has a valid base.
        4. Root-commit error: `resolve_squash_base` returns `error != None`;
           `squash()` surfaces it via the `if base_info.get('error')` check, BEFORE
           the per-repo no-op logic.
      In wrapper mode (source_root != install_root), squashes BOTH repos:
        - Install repo:  feat(<feature-name>): <title> + COMMIT_ATTRIBUTION per config
        - Source repo:   [TICKET-ID] - Description, NO attribution, NO traces (D5).
          This is enforced by the helper — the source path NEVER appends attribution
          regardless of config or what the orchestrator passes as source_message.
      Dangerous-state handling: if reset --soft succeeded but git commit failed,
      the resulting state is reported with a DANGER_STATE flag so the caller knows
      the working tree is in a partially-squashed state.
      Returns a dict with per-repo outcomes.

Exit codes for CLI handlers:
  0 — success (JSON emitted to stdout); also 0 for dry-run (confirmed=false)
  2 — error (message on stderr) or already-pushed refusal

Design notes:
- All git operations use git -C <repo> (never a process cwd change).
- _extract_ticket_id is imported from _implement._cmds_commit — the one
  canonical authority for the [A-Z]+-[0-9]+ Jira-style ticket token.
- _get_commit_attribution and _load_project_config are imported from
  _implement._cmds_commit — the one canonical authority for config loading
  and attribution reading.
- The BSD-safe --fixed-strings form is used for all [checkpoint] / [WIP]
  greps (same discipline as _preflight.py, _summarize, etc.).

Stdlib only.  Python 3.8+.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Import canonical helpers from implement — do NOT re-author any of these.
from _implement._cmds_commit import _extract_ticket_id       # type: ignore  # noqa: F401
from _implement._cmds_commit import _get_commit_attribution  # type: ignore  # noqa: F401
from _implement._cmds_commit import _load_project_config     # type: ignore  # noqa: F401


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_GIT_TIMEOUT = 60

# Candidates for the default branch, tried in order when origin/HEAD is absent.
# Must match _shared/feature_scope._BASE_CANDIDATES — update both together.
_DEFAULT_BRANCH_CANDIDATES = ["main", "develop", "master"]


# ---------------------------------------------------------------------------
# Internal git helper
# ---------------------------------------------------------------------------


def _git(args, cwd, timeout=_GIT_TIMEOUT):
    # type: (List[str], str, int) -> Tuple[int, str, str]
    """Run git -C <cwd> <args>.

    Returns (returncode, stdout, stderr).
    Never raises — subprocess errors become (1, "", error_message).
    """
    cmd = ["git", "-C", cwd] + args
    try:
        proc = subprocess.run(
            cmd,
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


# ---------------------------------------------------------------------------
# Internal helpers shared by both verbs
# ---------------------------------------------------------------------------


def _ref_exists(ref, repo_root):
    # type: (str, str) -> bool
    """Return True if the git ref resolves in repo_root."""
    rc, _, _ = _git(["rev-parse", "--verify", ref], repo_root)
    return rc == 0


def _current_branch_str(repo_root):
    # type: (str) -> Optional[str]
    """Return the current git branch name (string), or None on detached/error."""
    rc, stdout, _ = _git(["rev-parse", "--abbrev-ref", "HEAD"], repo_root)
    if rc != 0:
        return None
    branch = stdout.strip()
    if not branch or branch == "HEAD":
        return None
    return branch


def _resolve_default_branch(repo_root):
    # type: (str) -> Optional[str]
    """Auto-detect the trunk/default branch.

    Precedence (mirrors _shared/feature_scope.py _autodetect_base):
      1. origin/HEAD via git symbolic-ref refs/remotes/origin/HEAD
      2. origin/HEAD as a direct ref (bare-checkout fallback)
      3. local branch "main"
      4. local branch "develop"
      5. local branch "master"

    Returns the first that resolves, or None.
    """
    # Step 1: origin/HEAD via symbolic-ref.
    rc, stdout, _ = _git(
        ["symbolic-ref", "refs/remotes/origin/HEAD"],
        repo_root,
    )
    if rc == 0:
        ref = stdout.strip()
        if ref and _ref_exists(ref, repo_root):
            return ref

    # Step 2: origin/HEAD as a direct ref.
    if _ref_exists("origin/HEAD", repo_root):
        return "origin/HEAD"

    # Steps 3-5: local branch candidates.
    for candidate in _DEFAULT_BRANCH_CANDIDATES:
        if _ref_exists(candidate, repo_root):
            return candidate

    return None


def _is_on_default_branch(repo_root, default_branch):
    # type: (str, str) -> bool
    """Return True when HEAD and default_branch resolve to the same commit."""
    rc_h, head_sha, _ = _git(["rev-parse", "HEAD"], repo_root)
    if rc_h != 0:
        return False
    rc_d, default_sha, _ = _git(["rev-parse", default_branch], repo_root)
    if rc_d != 0:
        return False
    return head_sha.strip() == default_sha.strip()


def _compute_merge_base(repo_root, default_branch):
    # type: (str, str) -> Optional[str]
    """Return git merge-base HEAD <default_branch> SHA, or None on error."""
    rc, stdout, _ = _git(["merge-base", "HEAD", default_branch], repo_root)
    if rc != 0:
        return None
    return stdout.strip() or None


def _oldest_checkpoint_parent(repo_root):
    # type: (str,) -> Tuple[Optional[str], Optional[str]]
    """Find the oldest [checkpoint] commit reachable from HEAD and return its parent SHA.

    This is the on-DEFAULT_BRANCH squash-base fallback: when the user is not
    on a feature branch, the squash base is the commit just before the oldest
    [checkpoint] entry in the full history.

    NOTE: No range is used here — when the caller is already ON the default
    branch, the range `<default_branch>..HEAD` would be empty (HEAD IS the
    default branch tip).  We search the full history so all [checkpoint]
    commits are visible regardless of branch position.

    Uses the BSD-safe --fixed-strings form to prevent git from treating the
    square brackets in [checkpoint] as a BRE character class.

    Returns (parent_sha, error_or_none):
      - (sha_str, None)   — success: parent SHA of the oldest [checkpoint] commit
      - (None, None)      — no [checkpoint] commits exist in history (or git log failed)
      - (None, error_str) — [checkpoint] commits exist but the oldest IS the repository's
                            initial commit (no parent; git rev-parse <sha>^ fails with rc=128)
    """
    rc, stdout, _ = _git(
        [
            "log",
            "--fixed-strings",
            "--grep=[checkpoint]",
            "--format=%H",
        ],
        repo_root,
    )
    if rc != 0 or not stdout.strip():
        return None, None

    # tail -1 equivalent: git log lists newest-first; the last entry is the
    # chronologically oldest [checkpoint] commit.
    shas = [s.strip() for s in stdout.splitlines() if s.strip()]
    if not shas:
        return None, None

    oldest_sha = shas[-1]

    # Resolve the parent of the oldest checkpoint commit.
    rc2, parent_out, _ = _git(
        ["rev-parse", "{0}^".format(oldest_sha)],
        repo_root,
    )
    if rc2 != 0:
        # rc=128 is git's "bad revision" exit code, which is what rev-parse
        # returns when the commit has no parent (it is the repository's initial
        # commit).  Surface a clear error so resolve_squash_base can distinguish
        # this case from the "no checkpoints found" no-op.
        return None, (
            "cannot squash: the oldest [checkpoint] commit ({0}) is the "
            "repository's initial commit (no parent to squash back to)".format(
                oldest_sha[:12]
            )
        )
    parent_sha = parent_out.strip()
    return (parent_sha if parent_sha else None), None


# ---------------------------------------------------------------------------
# resolve_squash_base — public interface
# ---------------------------------------------------------------------------


def resolve_squash_base(
    install_root,       # type: str
    source_root,        # type: str
    default_branch=None,  # type: Optional[str]
):
    # type: (...) -> Dict
    """Compute the squash base SHAs for the install repo and (in wrapper mode) source repo.

    Parameters
    ----------
    install_root:
        Absolute path to the forge install/wrapper root.
    source_root:
        Absolute path to the source tree.  Equals install_root in standalone mode.
    default_branch:
        The trunk/default branch name (e.g. "main").  When None, auto-detected
        via the standard precedence (origin/HEAD -> main -> develop -> master).

    Returns a dict (always — never raises):
      install_squash_base   str or None  — SHA to squash to in install repo
      source_squash_base    str or None  — SHA to squash to in source repo (None in standalone)
      strategy              str          — "merge-base" | "checkpoint-parent" | "none"
      is_feature_branch     bool         — True when HEAD is not on DEFAULT_BRANCH
      default_branch        str or None  — resolved DEFAULT_BRANCH ref name
      error                 str or None  — fatal error message (None = success)
    """
    result = {
        "install_squash_base": None,
        "source_squash_base":  None,
        "strategy":            "none",
        "is_feature_branch":   False,
        "default_branch":      None,
        "error":               None,
    }  # type: Dict

    # --- Resolve default branch ---
    if default_branch:
        db = default_branch
        if not _ref_exists(db, install_root):
            result["error"] = (
                "default branch {0!r} does not exist in {1!r}".format(
                    db, install_root
                )
            )
            return result
    else:
        db = _resolve_default_branch(install_root)
        if db is None:
            result["error"] = (
                "cannot auto-detect default branch in {0!r}. "
                "None of origin/HEAD, main, develop, master resolve. "
                "Pass --default-branch <ref> explicitly.".format(install_root)
            )
            return result

    result["default_branch"] = db

    # --- Determine whether we are on the default branch or a feature branch ---
    on_default = _is_on_default_branch(install_root, db)
    result["is_feature_branch"] = not on_default

    # --- Install repo squash base ---
    if not on_default:
        # Feature-branch case: use merge-base.
        mb = _compute_merge_base(install_root, db)
        if mb is None:
            result["error"] = (
                "git merge-base HEAD {0!r} failed in {1!r}".format(db, install_root)
            )
            return result
        result["install_squash_base"] = mb
        result["strategy"] = "merge-base"
    else:
        # On DEFAULT_BRANCH: fall back to the oldest [checkpoint] commit's parent.
        # No range needed — we search full history because HEAD IS the default
        # branch tip, making the <default_branch>..HEAD range empty.
        parent, cp_err = _oldest_checkpoint_parent(install_root)
        if cp_err:
            # [checkpoint] commits exist but the oldest is the repo's initial
            # commit — distinguish this from the silent "no checkpoints" no-op.
            result["error"] = cp_err
            return result
        if parent:
            result["install_squash_base"] = parent
            result["strategy"] = "checkpoint-parent"
        else:
            # No checkpoint commits found — nothing to squash.
            result["strategy"] = "none"

    # --- Source repo squash base (wrapper mode only) ---
    abs_source = os.path.realpath(source_root)
    abs_install = os.path.realpath(install_root)
    if abs_source != abs_install:
        # In wrapper mode the source repo may be on a different branch from the
        # install repo.  Use the _shared merge-base scoped to source_root.
        src_db = _resolve_default_branch(source_root)
        if src_db is None:
            # Non-fatal: surface None but don't fail the whole call.
            result["source_squash_base"] = None
        else:
            src_mb = _compute_merge_base(source_root, src_db)
            result["source_squash_base"] = src_mb  # None if computation failed

    return result


# ---------------------------------------------------------------------------
# check_pushed — public interface
# ---------------------------------------------------------------------------


def check_pushed(repo_root):
    # type: (str) -> Dict
    """Check whether the current branch's commits are already on the remote.

    Runs:  git -C <repo_root> log --oneline origin/<branch>..HEAD

    Returns a dict (always — never raises):
      is_pushed     bool         — True when origin/<branch>..HEAD is empty —
                                   i.e. all HEAD commits are already on
                                   origin/<branch> (commit_count == 0).
                                   Safe-to-squash = NOT is_pushed.
      commit_count  int          — commits in origin/<branch>..HEAD (0 = pushed / no range)
      branch        str or None  — current branch name (None if detached)
      no_upstream   bool         — True when origin/<branch> doesn't exist OR no remote
      error         str or None  — fatal git error (None = success)

    Graceful degradation:
      - No remote configured or origin/<branch> not found:
            no_upstream=True, is_pushed=False, commit_count=0
            (treated as "not pushed → safe to squash" but the caller is warned
            via the no_upstream flag)
      - Detached HEAD: branch=None, no_upstream=True, is_pushed=False
    """
    result = {
        "is_pushed":    False,
        "commit_count": 0,
        "branch":       None,
        "no_upstream":  False,
        "error":        None,
    }  # type: Dict

    branch = _current_branch_str(repo_root)
    result["branch"] = branch

    if branch is None:
        # Detached HEAD — cannot determine origin reference.
        result["no_upstream"] = True
        return result

    origin_ref = "origin/{0}".format(branch)

    # Check whether the remote tracking ref exists.
    if not _ref_exists(origin_ref, repo_root):
        # Remote branch does not exist → treat as "not pushed → safe to squash".
        result["no_upstream"] = True
        return result

    # Run git log --oneline <origin/branch>..HEAD to count local-only commits.
    rc, stdout, stderr = _git(
        ["log", "--oneline", "{0}..HEAD".format(origin_ref)],
        repo_root,
    )
    if rc != 0:
        result["error"] = (
            "git log {0}..HEAD failed in {1!r}: {2}".format(
                origin_ref, repo_root, stderr.strip()
            )
        )
        return result

    commits = [ln for ln in stdout.splitlines() if ln.strip()]
    count = len(commits)
    result["commit_count"] = count
    # is_pushed=True means commits HAVE been pushed (count == 0 → all on remote).
    result["is_pushed"] = (count == 0)

    return result


# ---------------------------------------------------------------------------
# CLI handlers — registered via _cli.py _SUBCOMMAND_REGISTRY
# ---------------------------------------------------------------------------


def cmd_resolve_squash_base(args):
    # type: (object) -> int
    """Handle the resolve-squash-base verb.

    Emits JSON to stdout on success (exit 0).
    Emits an error message to stderr on failure (exit 2).
    """
    install_root = getattr(args, "install_root", ".") or "."
    source_root  = getattr(args, "source_root", None) or install_root
    default_branch = getattr(args, "default_branch", None) or None

    result = resolve_squash_base(
        install_root=os.path.realpath(install_root),
        source_root=os.path.realpath(source_root),
        default_branch=default_branch,
    )

    if result.get("error"):
        sys.stderr.write(
            "resolve-squash-base: {0}\n".format(result["error"])
        )
        sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
        return 2

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_check_pushed(args):
    # type: (object) -> int
    """Handle the check-pushed verb.

    Emits JSON to stdout (always, so the orchestrator can read no_upstream etc.).
    Exits 2 only on a fatal git error.
    """
    repo_root = getattr(args, "repo_root", ".") or "."

    result = check_pushed(os.path.realpath(repo_root))

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")

    if result.get("error"):
        sys.stderr.write(
            "check-pushed: {0}\n".format(result["error"])
        )
        return 2

    return 0


# ---------------------------------------------------------------------------
# squash — Phase 3: the net-new git-mutating core
# ---------------------------------------------------------------------------


def _git_reset_soft(repo_root, base_sha):
    # type: (str, str) -> Optional[str]
    """Run git -C <repo_root> reset --soft <base_sha>.

    Returns None on success, error message string on failure.
    Never raises.
    """
    rc, stdout, stderr = _git(["reset", "--soft", base_sha], repo_root)
    if rc != 0:
        return "git reset --soft {0} failed in {1!r} (rc={2}): {3}".format(
            base_sha[:12], repo_root, rc, stderr.strip() or stdout.strip()
        )
    return None


def _git_commit_simple(repo_root, message):
    # type: (str, str) -> Tuple[Optional[str], Optional[str]]
    """Run git -C <repo_root> commit -m <message>.

    Returns (new_head_sha, error_or_none).
    Never raises.
    """
    rc, stdout, stderr = _git(["commit", "-m", message], repo_root)
    if rc != 0:
        return None, "git commit failed in {0!r} (rc={1}): {2}".format(
            repo_root, rc, stderr.strip() or stdout.strip()
        )
    # Read the new HEAD SHA.
    rc2, head_out, _ = _git(["rev-parse", "HEAD"], repo_root)
    if rc2 != 0:
        return None, "commit succeeded but could not read HEAD SHA in {0!r}".format(
            repo_root
        )
    head_sha = head_out.strip()
    return (head_sha if head_sha else None), None


def squash(
    install_root,          # type: str
    source_root,           # type: str
    install_message,       # type: str
    source_message,        # type: str
    confirm=False,         # type: bool
    default_branch=None,   # type: Optional[str]
):
    # type: (...) -> Dict
    """Squash WIP/checkpoint commits in install repo and (wrapper mode) source repo.

    Parameters
    ----------
    install_root:
        Absolute path to the forge install/wrapper root.
    source_root:
        Absolute path to the source tree.  Equals install_root in standalone mode.
    install_message:
        The orchestrator-composed commit subject for the install/wrapper repo
        (e.g. 'feat(001-my-feature): implement widget catalog').
        The verb APPENDS COMMIT_ATTRIBUTION from config when non-empty.
    source_message:
        The orchestrator-composed commit message for the source repo
        (e.g. '[PROJ-123] - Implement widget catalog').
        Used AS-IS — the verb NEVER appends attribution to the source repo.
        This is a hard invariant enforced here, not by the caller.
    confirm:
        When False: dry-run — emits preview JSON (the exact commit messages that WILL
            be used, attribution already included — no mutation).
        When True: execute the squash.
    default_branch:
        Branch name for squash-base resolution.  None = auto-detect.

    Returns a dict (always — never raises):
      confirmed          bool         — True if execution was attempted (not dry-run)
      install_repo       dict or None — per-repo outcome for the install repo
      source_repo        dict or None — per-repo outcome for the source repo (None = standalone)
      error              str or None  — top-level error (e.g. squash-base resolution failure)

    Per-repo outcome dict:
      repo               str          — absolute path to the repo
      squash_base        str or None  — SHA squashed back to
      head_sha           str or None  — new HEAD SHA after squash (None if refused/failed)
      message_used       str or None  — exact commit message used
      attribution_applied bool        — True when attribution was appended (install repo only)
      refused            bool         — True when squash was refused (already pushed / no base)
      refusal_reason     str or None  — human-readable refusal reason
      danger_state       bool         — True when reset --soft succeeded but commit failed
      error              str or None  — per-repo error message
    """
    abs_install = os.path.realpath(install_root)
    abs_source  = os.path.realpath(source_root)
    is_wrapper  = (abs_source != abs_install)

    result = {
        "confirmed":   confirm,
        "install_repo": None,
        "source_repo":  None,
        "error":        None,
    }  # type: Dict

    # --- Resolve the squash base (no mutation) ---
    base_info = resolve_squash_base(
        install_root=abs_install,
        source_root=abs_source,
        default_branch=default_branch,
    )

    # Fatal error from resolve_squash_base (e.g. root-commit-checkpoint) — surface, no mutation.
    if base_info.get("error"):
        result["error"] = base_info["error"]
        return result

    install_base = base_info.get("install_squash_base")
    source_base  = base_info.get("source_squash_base")

    # --- Load attribution config (from install_root's .devforge/) ---
    # Done before the per-repo logic so dry-run preview includes the attribution.
    try:
        config = _load_project_config(Path(abs_install))
    except ValueError:
        config = {}
    attribution = _get_commit_attribution(config)

    # Compose the final install message (subject + optional attribution trailer).
    if attribution:
        install_final_message = install_message + attribution
    else:
        install_final_message = install_message

    # Source repo message is ALWAYS the caller-supplied string with NO attribution.
    # This is enforced HERE, never delegated to the caller (D5).
    source_final_message = source_message  # attribution is NEVER appended here

    # --- Per-repo no-op check ---
    # Each repo's no-op is determined by ITS OWN squash base, not the install
    # strategy.  install_base=None means install repo has nothing to squash;
    # source_base=None means source repo has nothing to squash (or is standalone).
    install_no_op = (install_base is None)
    source_no_op  = (not is_wrapper) or (source_base is None)

    # --- Dry-run (no --confirm): return preview without any mutation ---
    if not confirm:
        if install_no_op:
            result["install_repo"] = {
                "repo":               abs_install,
                "squash_base":        None,
                "head_sha":           None,
                "message_used":       None,
                "attribution_applied": False,
                "refused":            False,
                "refusal_reason":     "nothing to squash (no WIP/checkpoint commits found)",
                "danger_state":       False,
                "error":              None,
            }
        else:
            result["install_repo"] = {
                "repo":               abs_install,
                "squash_base":        install_base,
                "head_sha":           None,
                "message_used":       install_final_message,
                "attribution_applied": bool(attribution),
                "refused":            False,
                "refusal_reason":     None,
                "danger_state":       False,
                "error":              None,
            }
        if is_wrapper:
            if source_no_op:
                result["source_repo"] = {
                    "repo":               abs_source,
                    "squash_base":        None,
                    "head_sha":           None,
                    "message_used":       None,
                    "attribution_applied": False,
                    "refused":            False,
                    "refusal_reason":     "could not resolve squash base for source repo",
                    "danger_state":       False,
                    "error":              None,
                }
            else:
                result["source_repo"] = {
                    "repo":               abs_source,
                    "squash_base":        source_base,
                    "head_sha":           None,
                    "message_used":       source_final_message,
                    "attribution_applied": False,  # NEVER for source repo
                    "refused":            False,
                    "refusal_reason":     None,
                    "danger_state":       False,
                    "error":              None,
                }
        return result

    # --- Execute the squash (--confirm provided) ---

    # ---- Install repo ----
    if install_no_op:
        result["install_repo"] = {
            "repo":               abs_install,
            "squash_base":        None,
            "head_sha":           None,
            "message_used":       None,
            "attribution_applied": False,
            "refused":            False,
            "refusal_reason":     "nothing to squash (no WIP/checkpoint commits found)",
            "danger_state":       False,
            "error":              None,
        }
    else:
        install_outcome = _squash_one_repo(
            repo_root=abs_install,
            squash_base=install_base,
            message=install_final_message,
            attribution_applied=bool(attribution),
            repo_label="install",
        )
        result["install_repo"] = install_outcome

    # ---- Source repo (wrapper mode only) ----
    if is_wrapper:
        if source_no_op:
            result["source_repo"] = {
                "repo":               abs_source,
                "squash_base":        None,
                "head_sha":           None,
                "message_used":       None,
                "attribution_applied": False,
                "refused":            False,
                "refusal_reason":     "could not resolve squash base for source repo",
                "danger_state":       False,
                "error":              None,
            }
        else:
            source_outcome = _squash_one_repo(
                repo_root=abs_source,
                squash_base=source_base,
                message=source_final_message,
                # Source repo NEVER gets attribution — hard-coded False here (D5).
                attribution_applied=False,
                repo_label="source",
            )
            result["source_repo"] = source_outcome

    return result


def _squash_one_repo(repo_root, squash_base, message, attribution_applied, repo_label):
    # type: (str, str, str, bool, str) -> Dict
    """Squash one repo (install or source) via reset --soft + commit.

    Returns a per-repo outcome dict.  Never raises.

    D6 guard: runs check_pushed first; refuses if already pushed.
    Dangerous-state handling: if reset succeeded but commit failed, sets
    danger_state=True in the returned dict so the caller knows the history
    is in a partially-squashed state.
    """
    outcome = {
        "repo":               repo_root,
        "squash_base":        squash_base,
        "head_sha":           None,
        "message_used":       message,
        "attribution_applied": attribution_applied,
        "refused":            False,
        "refusal_reason":     None,
        "danger_state":       False,
        "error":              None,
    }  # type: Dict

    # Guard: already pushed → refuse (never rewrite shared history).
    push_check = check_pushed(repo_root)
    if push_check.get("error"):
        outcome["refused"] = True
        outcome["refusal_reason"] = (
            "could not determine push status for {0} repo ({1}): {2}".format(
                repo_label, repo_root, push_check["error"]
            )
        )
        outcome["error"] = push_check["error"]
        return outcome

    if push_check.get("is_pushed"):
        outcome["refused"] = True
        outcome["refusal_reason"] = (
            "{0} repo ({1}) branch {2!r} has already been pushed to origin — "
            "refusing squash to avoid rewriting shared history".format(
                repo_label, repo_root, push_check.get("branch")
            )
        )
        return outcome

    # Run git reset --soft <base>.
    reset_err = _git_reset_soft(repo_root, squash_base)
    if reset_err is not None:
        outcome["error"] = reset_err
        return outcome

    # Run git commit (the point of no return after reset --soft).
    new_sha, commit_err = _git_commit_simple(repo_root, message)
    if commit_err is not None:
        # reset --soft succeeded but commit failed — DANGER STATE.
        # The working tree has all changes staged but no commit yet.
        outcome["danger_state"] = True
        outcome["error"] = (
            "DANGER STATE: git reset --soft succeeded but git commit failed "
            "in {0} repo ({1}). Working tree is staged but uncommitted. "
            "Commit manually with: git -C {1} commit -m '<message>'. "
            "Original error: {2}".format(repo_label, repo_root, commit_err)
        )
        return outcome

    outcome["head_sha"] = new_sha
    return outcome


def cmd_squash(args):
    # type: (object) -> int
    """Handle the squash verb.

    Without --confirm: emits dry-run preview JSON (confirmed=false), exits 0.
    With --confirm: executes the squash, emits result JSON.
    Exits 2 on fatal errors (squash-base resolution failure, already-pushed
    refusal in either repo, or dangerous half-complete state).
    """
    install_root    = getattr(args, "install_root", ".") or "."
    source_root     = getattr(args, "source_root",  None) or install_root
    install_message = getattr(args, "install_message", "") or ""
    source_message  = getattr(args, "source_message",  "") or ""
    confirm         = bool(getattr(args, "confirm", False))
    default_branch  = getattr(args, "default_branch", None) or None

    result = squash(
        install_root=os.path.realpath(install_root),
        source_root=os.path.realpath(source_root),
        install_message=install_message,
        source_message=source_message,
        confirm=confirm,
        default_branch=default_branch,
    )

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")

    # Top-level error (e.g. root-commit squash base, unresolvable base).
    if result.get("error"):
        sys.stderr.write("squash: {0}\n".format(result["error"]))
        return 2

    # Per-repo refusals or errors.
    exit_code = 0
    for repo_key in ("install_repo", "source_repo"):
        repo_out = result.get(repo_key)
        if repo_out is None:
            continue
        if repo_out.get("danger_state"):
            sys.stderr.write("squash: {0}\n".format(repo_out.get("error", "")))
            exit_code = 2
        elif repo_out.get("error"):
            sys.stderr.write(
                "squash ({0}): {1}\n".format(repo_key, repo_out["error"])
            )
            exit_code = 2
        elif repo_out.get("refused"):
            sys.stderr.write(
                "squash ({0}): refused — {1}\n".format(
                    repo_key, repo_out.get("refusal_reason", "")
                )
            )
            # Refused but not a dangerous state — still exit 2 so the orchestrator
            # knows the squash did not complete.
            exit_code = 2

    return exit_code
