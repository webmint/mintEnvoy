"""_changes.py — gather-change-data verb for finalize_helper.

Assembles the changed-file list + scope_block (via _shared.feature_scope)
for the tech-writer brief.  Unlike _summarize/_changes.py, this module does
NOT include git diff --stat +/- totals — the finalize results block does not
require them, so we keep the implementation lean.

JSON emitted to stdout on success:

  {
    "feature_dir":       str,            # from resolve_feature_scope
    "source_root":       str,            # from resolve_feature_scope
    "base":              str,            # resolved base ref
    "merge_base":        str,            # merge-base SHA
    "head":              str,            # HEAD SHA
    "files":             list[str],      # sorted source-relative changed paths
    "files_for_finders": list[str],      # wrapper-prefixed paths (=files in standalone)
    "file_count":        int,
    "scope_block":       str,            # human-readable scope summary block
    "source_changes":    dict or None    # wrapper-mode source-repo changes (see below)
  }

"source_changes" has three possible shapes:
  - None                         — standalone mode (source_root == install_root).
  - {"error": str}               — wrapper mode, source-repo resolve_feature_scope failed.
                                   Non-fatal: the top-level result still succeeds.
                                   A Phase 4 consumer MUST check for the "error" key
                                   before accessing "files" or any other field to avoid
                                   a KeyError.
  - {<parallel dict>}            — wrapper mode, success: same keys as the top-level
                                   result (except "source_changes" itself), scoped to
                                   the source repo.

Exit codes:
  0 — success (JSON emitted to stdout)
  2 — error (message on stderr, no JSON)

Stdlib only.  Python 3.8+.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Dict, Optional, Tuple


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
    """Gather the assembled-feature change data for /finalize.

    Uses _shared.feature_scope.resolve_feature_scope for the file list,
    scope_block, and merge_base.  Heading label is "Finalize Scope" (distinct
    from /summarize's "Summary Scope", /review's "Review Scope", and
    /verify's "Verification Scope").

    In wrapper mode (source_root != install_root), gathers source-repo changes
    separately and returns them under "source_changes".

    Returns (result_dict, None) on success, (None, error_message) on failure.
    """
    # Import here to allow tests to set up sys.path before this module loads.
    from _shared.feature_scope import resolve_feature_scope  # type: ignore

    if install_root is None:
        install_root = source_root

    # --- Assembled scope (file list + scope_block + merge_base) via _shared ---
    scope_result, err = resolve_feature_scope(
        feature_dir=feature_dir,
        source_root=source_root,
        install_root=install_root,
        base=base,
        heading_label="Finalize Scope",
    )
    if err:
        return None, err

    result = {
        "feature_dir":       scope_result["feature_dir"],
        "source_root":       scope_result["source_root"],
        "base":              scope_result["base"],
        "merge_base":        scope_result["merge_base"],
        "head":              scope_result["head"],
        "files":             scope_result["files"],
        "files_for_finders": scope_result["files_for_finders"],
        "file_count":        scope_result["file_count"],
        "scope_block":       scope_result["scope_block"],
        "source_changes":    None,
    }  # type: Dict

    # --- wrapper-mode source-repo changes ---
    abs_source = os.path.realpath(source_root)
    abs_install = os.path.realpath(install_root)
    if abs_source != abs_install:
        src_scope, src_err = resolve_feature_scope(
            feature_dir=feature_dir,
            source_root=source_root,
            install_root=source_root,   # scope within source repo only
            base=base,
            heading_label="Finalize Scope (source repo)",
        )
        if src_err:
            # Non-fatal: surface the error in source_changes but don't fail.
            result["source_changes"] = {"error": src_err}
        else:
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
