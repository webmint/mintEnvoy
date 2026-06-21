"""Scope resolution for review_helper (Phase 2).

Rationale — why merge-base diff, not completion-note prose
-----------------------------------------------------------
The assembled-feature diff (git diff --name-only <merge-base>..HEAD) is the
mechanical ground truth of what the feature changed.  Parsing task-completion-
note prose to reconstruct the same information is brittle and is exactly the
anti-pattern the repo's "consumer obeys producer" discipline rejects: the
producer here is git's history, not human prose.

This module:
  resolve_feature_scope  — re-exported from _shared.feature_scope
  _render_scope_block    — re-exported from _shared.feature_scope
  cmd_resolve_feature_scope — thin /review CLI verb handler

The implementation lives in _shared/feature_scope.py so that /verify can
share the same resolver without duplicating code.  The heading_label parameter
on resolve_feature_scope defaults to "Review Scope", keeping /review
byte-behaviorally identical to the pre-extraction code.

No imports from _audit/ are allowed; the _review package must be
independently operable.

Stdlib only.  Python 3.8+.
"""

from __future__ import annotations

import json
import os
import sys

# Re-export the shared implementation so existing imports of
#   from _review._scope import resolve_feature_scope
#   from _review._scope import _render_scope_block
#   from _review._scope import _prefix_paths
#   from _review._scope import _is_git_repo
#   etc.
# continue to resolve unchanged.
from _shared.feature_scope import (  # type: ignore[import]  # noqa: E402
    _BASE_CANDIDATES,
    _GIT_TIMEOUT,
    _autodetect_base,
    _compute_merge_base,
    _diff_name_only,
    _git,
    _is_git_repo,
    _prefix_paths,
    _ref_exists,
    _render_scope_block,
    _resolve_head_sha,
    _resolve_origin_head,
    resolve_feature_scope,
)

__all__ = [
    "_BASE_CANDIDATES",
    "_GIT_TIMEOUT",
    "_autodetect_base",
    "_compute_merge_base",
    "_diff_name_only",
    "_git",
    "_is_git_repo",
    "_prefix_paths",
    "_ref_exists",
    "_render_scope_block",
    "_resolve_head_sha",
    "_resolve_origin_head",
    "resolve_feature_scope",
    "cmd_resolve_feature_scope",
]


# ---------------------------------------------------------------------------
# CLI command handler (registered in _cli.py)
# ---------------------------------------------------------------------------


def cmd_resolve_feature_scope(args):
    # type: (object) -> int
    """CLI handler for the resolve-feature-scope verb.

    Emits JSON on stdout on success; error message on stderr + exit 2 on failure.

    Returns:
      0 — success (files list may be empty — HEAD == merge-base is valid)
      2 — user error (not a git repo, bad ref, no auto-detectable base, etc.)
    """
    feature_dir = getattr(args, "feature", ".")
    source_root = getattr(args, "source_root", None) or os.getcwd()
    install_root = getattr(args, "install_root", None)
    base = getattr(args, "base", None)

    # Resolve source_root to absolute.
    source_root = os.path.realpath(source_root)

    # Resolve install_root to absolute if provided; default to source_root.
    if install_root:
        install_root = os.path.realpath(install_root)
    else:
        install_root = source_root

    # Pass "Review Scope" explicitly (relies on the shared default but is
    # stated here so /verify's handler can pass "Verification Scope" without
    # confusion about which default applies).
    result, error = resolve_feature_scope(
        feature_dir=feature_dir,
        source_root=source_root,
        install_root=install_root,
        base=base,
        heading_label="Review Scope",
    )

    if error is not None:
        sys.stderr.write(
            "review_helper resolve-feature-scope: {0}\n".format(error)
        )
        return 2

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0
