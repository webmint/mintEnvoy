"""Static path manifest resolver for grill_helper (Phase 2).

Design — why paths only, no diff, no CBM
-----------------------------------------
/grill runs BEFORE /breakdown (between /plan and /breakdown). Its job is to
hand a `devils-advocate` AGENT the paths it needs to read plan.md, spec.md,
the upstream specify handoff (+ its provenance chain), constitution.md, and
CLAUDE.md. The agent holds the codebase-memory MCP tools and performs any
blast-radius traversal itself — this helper cannot call MCP. Therefore
_scope's ONLY responsibility is:

  1. Resolve the target feature directory — from an explicit arg
     (specs/NNN-*/ dir or a plan.md path) or by auto-detecting the
     lowest-numbered feature under specs/ that has a plan.md.

  2. Build a GrillScopeManifest — a small dataclass carrying the
     existence-checked paths the agent will be handed. File CONTENTS are
     NOT read here; the agent reads them directly.

No git diff is computed. No CBM calls are made. No file contents are loaded.
This keeps the helper fast, deterministic, and runnable without a git repo.

Public surface
--------------
  resolve_target_feature  — (specs_root, feature_arg) -> (feature_dir, error)
  GrillScopeManifest      — dataclass holding the resolved path set
  build_scope_manifest    — (feature_dir, workspace_root) -> (manifest, error)
  cmd_resolve_scope       — thin CLI handler (registered in _cli.py)

Stdlib only.  Python 3.8+.  No from __future__ import annotations.
"""

import dataclasses
import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Optional, Tuple


# ---------------------------------------------------------------------------
# Feature sort key (matches _implement/_cmds_resolve.py precedent)
# ---------------------------------------------------------------------------

_NNN_RE = re.compile(r"^(\d+)")


def _feature_sort_key(name):
    # type: (str) -> int
    """Return the numeric prefix of a feature directory name for sort order.

    Non-numeric or missing prefix returns maxint so those dirs sort last.
    """
    base = os.path.basename(name)
    m = _NNN_RE.match(base)
    if not m:
        return 2 ** 31
    try:
        return int(m.group(1))
    except ValueError:
        return 2 ** 31


# ---------------------------------------------------------------------------
# resolve_target_feature
# ---------------------------------------------------------------------------


def resolve_target_feature(
    specs_root,   # type: str
    feature_arg,  # type: Optional[str]
):
    # type: (...) -> Tuple[Optional[str], Optional[str]]
    """Resolve the feature directory from an explicit arg or auto-detection.

    Parameters
    ----------
    specs_root:
        Absolute path to the specs/ directory (e.g. /project/specs).
    feature_arg:
        Optional explicit argument — either:
          - a path to a specs/NNN-*/ directory, or
          - a path to a plan.md file (parent dir is used as the feature dir).
        When None, auto-detect: pick the lowest-numbered subdir of specs_root
        that contains a plan.md file.

    Returns
    -------
    (feature_dir, error)
        feature_dir: absolute path to the resolved feature directory,
                     or None on error.
        error:       human-readable error string, or None on success.

    Auto-detection criteria: directory name must match r'^\\d+' (has a numeric
    NNN prefix) AND contain a plan.md file.  The lowest-numbered such directory
    is returned.  Directories without a numeric prefix are ignored.
    """
    if feature_arg is not None:
        # Normalise: if the arg is a path to a plan.md file, use its parent.
        candidate = os.path.abspath(feature_arg)
        if os.path.isfile(candidate) and os.path.basename(candidate) == "plan.md":
            candidate = os.path.dirname(candidate)

        if not os.path.isdir(candidate):
            return None, (
                "feature argument {0!r} does not resolve to a directory. "
                "Pass a specs/NNN-*/ directory or a plan.md path.".format(feature_arg)
            )
        return candidate, None

    # Auto-detection: scan specs_root for numbered dirs with plan.md.
    if not os.path.isdir(specs_root):
        return None, (
            "specs directory {0!r} does not exist. "
            "Cannot auto-detect a feature.".format(specs_root)
        )

    candidates = []
    try:
        entries = os.listdir(specs_root)
    except OSError as exc:
        return None, "cannot list {0!r}: {1}".format(specs_root, exc)

    for entry in entries:
        full = os.path.join(specs_root, entry)
        if not os.path.isdir(full):
            continue
        # Must have a numeric NNN prefix.
        if not _NNN_RE.match(entry):
            continue
        # Must have plan.md.
        if os.path.isfile(os.path.join(full, "plan.md")):
            candidates.append(full)

    if not candidates:
        return None, (
            "no feature directories with a plan.md found under {0!r}. "
            "Run /plan first to produce a plan.md.".format(specs_root)
        )

    candidates.sort(key=_feature_sort_key)
    return os.path.abspath(candidates[0]), None


# ---------------------------------------------------------------------------
# GrillScopeManifest
# ---------------------------------------------------------------------------


@dataclass
class GrillScopeManifest:
    """Static path manifest for the /grill scope phase.

    All paths are absolute.  Contents are NOT read — the agent reads them.

    Fields
    ------
    feature_dir     str           Resolved feature directory (e.g. /proj/specs/001-auth)
    feature_id      str           Basename of the feature dir (e.g. 001-auth)
    plan_path       str           <feature_dir>/plan.md   (required; validated)
    spec_path       str           <feature_dir>/spec.md   (required; validated)
    handoff_path    Optional[str] <feature_dir>/handoff.json (if it exists, else None)
    constitution_path str         <workspace_root>/constitution.md
    claude_md_path  str           <workspace_root>/CLAUDE.md
    """

    feature_dir: str = ""
    feature_id: str = ""
    plan_path: str = ""
    spec_path: str = ""
    handoff_path: Optional[str] = None
    constitution_path: str = ""
    claude_md_path: str = ""


# ---------------------------------------------------------------------------
# build_scope_manifest
# ---------------------------------------------------------------------------


def build_scope_manifest(
    feature_dir,    # type: str
    workspace_root, # type: str
):
    # type: (...) -> Tuple[Optional[GrillScopeManifest], Optional[str]]
    """Build and existence-check the GrillScopeManifest for a feature.

    Parameters
    ----------
    feature_dir:
        Absolute path to the resolved feature directory (e.g. /proj/specs/001-auth).
    workspace_root:
        Absolute path to the forge install root (where constitution.md / CLAUDE.md
        live).

    Returns
    -------
    (manifest, error)
        On success: (GrillScopeManifest, None)
        On error:   (None, error_string) — error names the missing required path.

    Required paths (return error if absent):
        <feature_dir>/plan.md
        <feature_dir>/spec.md

    Optional paths (None when absent, not an error):
        <feature_dir>/handoff.json
    """
    feature_id = os.path.basename(feature_dir)

    plan_path = os.path.join(feature_dir, "plan.md")
    spec_path = os.path.join(feature_dir, "spec.md")
    handoff_path = os.path.join(feature_dir, "handoff.json")
    constitution_path = os.path.join(workspace_root, "constitution.md")
    claude_md_path = os.path.join(workspace_root, "CLAUDE.md")

    # Validate required paths.
    if not os.path.isfile(plan_path):
        return None, (
            "required artefact missing: {0}. "
            "Run /plan to produce a plan.md for this feature.".format(plan_path)
        )
    if not os.path.isfile(spec_path):
        return None, (
            "required artefact missing: {0}. "
            "Run /specify to produce a spec.md for this feature.".format(spec_path)
        )

    # Optional handoff.json — present or None.
    resolved_handoff = handoff_path if os.path.isfile(handoff_path) else None

    manifest = GrillScopeManifest(
        feature_dir=feature_dir,
        feature_id=feature_id,
        plan_path=plan_path,
        spec_path=spec_path,
        handoff_path=resolved_handoff,
        constitution_path=constitution_path,
        claude_md_path=claude_md_path,
    )
    return manifest, None


# ---------------------------------------------------------------------------
# CLI handler
# ---------------------------------------------------------------------------


def cmd_resolve_scope(args):
    # type: (object) -> int
    """CLI handler for the resolve-scope verb.

    Resolves the target feature, builds the path manifest, and emits JSON to
    stdout.  Emits an error message to stderr and returns exit code 2 on any
    failure.

    Expected args attributes (all optional — use getattr with defaults):
      feature        str|None  explicit feature dir or plan.md path
      workspace_root str       install root (where constitution.md lives); default CWD
      specs_dir      str|None  override for the specs/ directory; default <workspace_root>/specs
    """
    feature_arg = getattr(args, "feature", None)
    workspace_root = getattr(args, "workspace_root", None) or os.getcwd()
    specs_dir_arg = getattr(args, "specs_dir", None)

    workspace_root = os.path.realpath(workspace_root)
    specs_root = (
        os.path.realpath(specs_dir_arg)
        if specs_dir_arg
        else os.path.join(workspace_root, "specs")
    )

    # Step 1: resolve feature directory.
    feature_dir, error = resolve_target_feature(specs_root, feature_arg)
    if error is not None:
        sys.stderr.write("grill_helper resolve-scope: {0}\n".format(error))
        return 2

    # Step 2: build manifest.
    manifest, error = build_scope_manifest(feature_dir, workspace_root)
    if error is not None:
        sys.stderr.write("grill_helper resolve-scope: {0}\n".format(error))
        return 2

    sys.stdout.write(
        json.dumps(dataclasses.asdict(manifest), indent=2, sort_keys=True) + "\n"
    )
    return 0
