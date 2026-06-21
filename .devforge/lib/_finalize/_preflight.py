"""Pure preflight function for finalize_helper.

preflight_context — read and validate the 4-command setup chain artefacts,
                    check the target spec **Status**: Complete, report
                    Source-Root / wrapper-mode from CLAUDE.md, and detect
                    WIP/checkpoint commits for the no-op signal.

The function returns a plain dict; the CLI handler (cmd_preflight in _cli.py)
decides whether to stop on missing artefacts or a non-Complete spec (exit 2)
or pass.

Setup-chain artefacts checked (same as /audit's, /review's, /verify's, and
/summarize's preflight — all helpers enforce the same gate on the same markers):
  1. constitution.md present
  2. CLAUDE.md present
  3. .devforge/project-config.json present  (/configure output)
  4. .devforge/index.json present           (/generate-docs output)

NOTE: this module intentionally OMITS the constitution-populated sentinel guard
(_UNPOPULATED_SENTINELS) that /verify and /review carry.  /finalize runs AFTER
/verify has already approved the feature — the spec **Status**: Complete gate is
a strictly stronger precondition than a populated constitution at this pipeline
stage.  The setup-chain EXISTENCE check still includes constitution.md (artefact
#1 above), ensuring the command was run.
Rationale is identical to _summarize/_preflight.py's documented omission.

NOTE: this module reads .devforge/memory.md — the live path per
src/CLAUDE.md References block ("Memory: .devforge/memory.md").
Do NOT change the memory path without verifying the current convention in
src/CLAUDE.md.

WIP/checkpoint detection:
  Uses the BSD-safe two-flag --grep form: each pattern passed as its own
  --grep flag so git ORs them.  Do NOT use the backslash-pipe BRE alternation
  (written as backslash + pipe) — BSD/macOS git does not honor it (the same
  fix applied in /summarize).
  ALSO uses --fixed-strings to prevent git from treating the square brackets
  in [WIP] and [checkpoint] as BRE character classes (without it, [WIP] matches
  any single character from the set {W, I, P}, which would incorrectly match
  ordinary commit messages containing those characters).
"""

from __future__ import annotations

import os
import re
import subprocess
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Setup-chain artefacts that must exist for /finalize to run.
# Parallel to /audit's, /review's, /verify's, and /summarize's preflight —
# same four-command chain.  Must stay in sync with those preflights.
_SETUP_CHAIN_ARTEFACTS = [
    # (relative_path, label) — label shown in missing_artefacts list
    ("constitution.md",                      "/constitute"),
    ("CLAUDE.md",                            "/init-forge"),
    (".devforge/project-config.json",        "/configure"),
    (".devforge/index.json",                 "/generate-docs"),
]

# The only valid status value that allows /finalize to proceed.
# Value from _specify/_schema.py SPEC_STATUS_ENUM: ("Draft", "Approved", "In Progress", "Complete")
_REQUIRED_SPEC_STATUS = "Complete"

# Regex to parse **Status**: <value> from spec.md.
# The spec renders this as a bare bold line, e.g.: **Status**: Draft
#
# IMPORTANT: uses [ \t]* (horizontal whitespace only), NOT \s*, and does NOT
# use re.DOTALL.  This is intentional — the status value MUST appear on the
# same line as the **Status**: marker.  Using \s* would allow the match to
# bleed across blank lines and capture a value from a subsequent line in a
# malformed spec (e.g. "**Status**:\n\nComplete\n" would wrongly pass the gate).
_STATUS_RE = re.compile(r"^\*\*Status\*\*:[ \t]*(.+)$", re.MULTILINE)

# Maximum seconds for any single git subprocess call.
_GIT_TIMEOUT = 60


# ---------------------------------------------------------------------------
# Internal git helper
# ---------------------------------------------------------------------------

def _git(args, cwd, timeout=_GIT_TIMEOUT):
    # type: (List[str], str, int) -> tuple
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


# ---------------------------------------------------------------------------
# WIP / checkpoint detection
# ---------------------------------------------------------------------------

def _count_wip_commits(source_root, base_ref=None):
    # type: (str, Optional[str]) -> int
    """Count [WIP] and [checkpoint] commits reachable from HEAD but not base.

    Uses the BSD-safe two-flag --grep form: each prefix as its own --grep flag.
    CRITICAL: also uses --fixed-strings to prevent git from treating the square
    brackets in [WIP] and [checkpoint] as BRE character classes.  Without
    --fixed-strings, [WIP] is treated as a character class matching {W, I, P},
    which causes false-positives on ordinary commit messages.

    Each pattern is its own --grep flag; git ORs them (default, no --all-match).

    Parameters
    ----------
    source_root : str
        The git repository root to run git in.
    base_ref : str or None
        The base git ref to compute the range from (e.g. "main").
        When None, auto-detects from origin/HEAD -> main -> develop -> master.
        When the base cannot be resolved (not a git repo, no branches), returns 0.

    Returns the count of matching commits (0 = nothing to finalize).
    """
    if not base_ref:
        base_ref = _autodetect_base(source_root)
    if not base_ref:
        return 0

    # BSD-safe: each pattern as its own --grep flag.
    # --fixed-strings prevents [WIP] from being treated as a char class [W,I,P].
    # git ORs multiple --grep patterns by default (no --all-match).
    rc, stdout, _ = _git(
        [
            "log", "--oneline",
            "--fixed-strings",
            "--grep=[WIP]",
            "--grep=[checkpoint]",
            "{0}..HEAD".format(base_ref),
        ],
        cwd=source_root,
    )
    if rc != 0:
        return 0

    lines = [ln for ln in stdout.splitlines() if ln.strip()]
    return len(lines)


def _ref_exists(ref, source_root):
    # type: (str, str) -> bool
    """Return True if ref can be resolved by git."""
    rc, _, _ = _git(["rev-parse", "--verify", ref], cwd=source_root)
    return rc == 0


def _autodetect_base(source_root):
    # type: (str) -> Optional[str]
    """Auto-detect the base branch ref.

    Tries in order:
      1. origin/HEAD (via git symbolic-ref refs/remotes/origin/HEAD)
      2. origin/HEAD as a direct resolvable ref (bare-checkout fallback)
      3. local branch "main"
      4. local branch "develop"
      5. local branch "master"

    Returns the first that resolves, or None if none resolves.
    Mirrors _shared/feature_scope.py's _autodetect_base / _resolve_origin_head
    logic exactly (3-step precedence: symbolic-ref → direct-ref → local branches).
    """
    # Step 1: origin/HEAD via symbolic-ref.
    rc, stdout, _ = _git(
        ["symbolic-ref", "refs/remotes/origin/HEAD"],
        cwd=source_root,
    )
    if rc == 0 and stdout.strip():
        ref = stdout.strip()
        if _ref_exists(ref, source_root):
            return ref

    # Step 2: origin/HEAD as a direct ref (handles some bare-checkout cases).
    if _ref_exists("origin/HEAD", source_root):
        return "origin/HEAD"

    # Steps 3-5: local branch candidates.
    for candidate in ["main", "develop", "master"]:
        if _ref_exists(candidate, source_root):
            return candidate

    return None


# ---------------------------------------------------------------------------
# preflight_context
# ---------------------------------------------------------------------------

def preflight_context(workspace_root, spec_path=None, base_ref=None):
    # type: (str, Optional[str], Optional[str]) -> Dict
    """Check setup-chain artefacts, spec Complete gate, CLAUDE.md context,
    and WIP/checkpoint commit detection.

    Never raises on a missing file — returns sane defaults.

    Parameters
    ----------
    workspace_root : str
        The directory to scan for setup-chain artefacts and CLAUDE.md.
        In wrapper mode this is the wrapper root, not the project sub-directory.
    spec_path : str or None
        Explicit path to a spec.md to check.  When None, the spec gate
        is skipped (spec_status will be "" and spec_complete will be False).
    base_ref : str or None
        Base git ref for the WIP/checkpoint commit range.  When None,
        auto-detected from origin/HEAD → main → develop → master.

    Returns a dict with keys always present:

      setup_chain_ok            bool  — all 4 artefacts present
      missing_artefacts         list  — labels of missing artefacts (empty = ok)
      spec_path                 str   — the resolved spec path (or "" if not given)
      spec_status               str   — the parsed **Status**: value (or "")
      spec_complete             bool  — True when spec_status == "Complete"
      source_root               str   — value from CLAUDE.md Project Root / Source Root
      wrapper_mode              bool  — True when CLAUDE.md contains a wrapper-mode marker
      project_type              str   — value of **Type**: line in CLAUDE.md
      framework                 str   — value of **Frameworks**: line in CLAUDE.md
      language                  str   — value of **Languages**: line in CLAUDE.md
      claude_md_present         bool  — CLAUDE.md exists
      memory_present            bool  — .devforge/memory.md exists
      memory_excerpt            str   — first 40 lines of memory.md (empty if absent)
      wip_commit_count          int   — count of [WIP]/[checkpoint] commits in base..HEAD
      has_wip_commits           bool  — True when wip_commit_count > 0
    """
    result = {
        "setup_chain_ok": False,
        "missing_artefacts": [],
        "spec_path": spec_path or "",
        "spec_status": "",
        "spec_complete": False,
        "source_root": ".",
        "wrapper_mode": False,
        "project_type": "",
        "framework": "",
        "language": "",
        "claude_md_present": False,
        "memory_present": False,
        "memory_excerpt": "",
        "wip_commit_count": 0,
        "has_wip_commits": False,
    }  # type: Dict

    # --- Check all setup-chain artefacts ---
    missing = []  # type: List[str]
    for rel_path, label in _SETUP_CHAIN_ARTEFACTS:
        full = os.path.join(workspace_root, rel_path)
        if not os.path.isfile(full):
            missing.append(label)
    result["missing_artefacts"] = missing
    result["setup_chain_ok"] = len(missing) == 0

    # --- Spec **Status**: Complete gate ---
    if spec_path:
        try:
            with open(spec_path, "r", encoding="utf-8") as fh:
                spec_text = fh.read()
            m = _STATUS_RE.search(spec_text)
            if m:
                status_value = m.group(1).strip()
                result["spec_status"] = status_value
                result["spec_complete"] = (status_value == _REQUIRED_SPEC_STATUS)
        except OSError:
            pass

    # --- CLAUDE.md ---
    claude_path = os.path.join(workspace_root, "CLAUDE.md")
    try:
        with open(claude_path, "r", encoding="utf-8") as fh:
            claude_lines = fh.readlines()
        result["claude_md_present"] = True
        for line in claude_lines:
            stripped = line.strip()
            lower = stripped.lower()

            # Wrapper-mode detection: look for the WRAPPER_MODE_SECTION marker
            # or a "Source Root:" / "Wrapper root:" line.  The /init-forge wizard
            # writes a {{WRAPPER_MODE_SECTION}} block that expands to contain
            # the phrase "wrapper mode" when wrapper mode is active.
            if "wrapper mode" in lower or "wrapper root" in lower:
                result["wrapper_mode"] = True

            # Source Root / Project Root extraction.
            # Mirrors _summarize/_preflight.py's logic exactly.
            # Known limitation (shared with _audit/_preflight, _review/_preflight,
            # _verify/_preflight, _summarize/_preflight): a path value containing
            # a colon — e.g. a Windows drive letter like C:\Users\me — is truncated
            # to the part after the last colon (\Users\me). Forge installs on
            # Windows are uncommon; accepted.
            if result["source_root"] == "." and (
                "source root" in lower or "project root" in lower
            ):
                if ":" in stripped:
                    val = stripped.rsplit(":", 1)[-1].strip()
                    val = val.strip("*`")
                    if val:
                        result["source_root"] = val

            # Bold-key extraction (anchored to "**Key**:" lines).
            if "**" in stripped and "type" in lower and ":" in stripped:
                if not result["project_type"]:
                    val = stripped.rsplit(":", 1)[-1].strip().strip("*`")
                    if val:
                        result["project_type"] = val

            if "**" in stripped and "framework" in lower and ":" in stripped:
                if not result["framework"]:
                    val = stripped.rsplit(":", 1)[-1].strip().strip("*`")
                    if val:
                        result["framework"] = val

            if "**" in stripped and "language" in lower and ":" in stripped:
                if not result["language"]:
                    val = stripped.rsplit(":", 1)[-1].strip().strip("*`")
                    if val:
                        result["language"] = val
    except OSError:
        pass

    # --- .devforge/memory.md ---
    # Reads .devforge/memory.md — the live path per src/CLAUDE.md
    # References block ("Memory: .devforge/memory.md").
    memory_path = os.path.join(workspace_root, ".devforge", "memory.md")
    try:
        with open(memory_path, "r", encoding="utf-8") as fh:
            mem_lines = fh.readlines()
        result["memory_present"] = True
        result["memory_excerpt"] = "".join(mem_lines[:40])
    except OSError:
        pass

    # --- WIP / checkpoint detection ---
    # Runs in source_root (resolved against workspace_root when relative).
    source_root = result["source_root"]
    if not os.path.isabs(source_root):
        source_root = os.path.join(workspace_root, source_root)

    count = _count_wip_commits(source_root, base_ref=base_ref)
    result["wip_commit_count"] = count
    result["has_wip_commits"] = count > 0

    return result
