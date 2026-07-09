"""_ui_scope -- resolve whether a feature touches UI code.

Implements the resolve-ui-scope verb for review_helper.

resolve_ui_scope(files, workspace_root) -> dict
    Reads .devforge/project-config.json, checks PROJECT_NATURES against
    the UI-nature set {web, mobile, desktop}, and returns a dict with
    is_ui, platform_hint, natures, and reason.

    Recall-bias contract (failure modes are ASYMMETRIC):
      - Config missing/unreadable  -> is_ui=True (a11y not silently dropped)
      - PROJECT_NATURES absent/empty -> is_ui=True (recall bias)
      - Overlap with {web, mobile, desktop} -> is_ui=True
      - No overlap (field present and non-empty) -> is_ui=False

    The `files` argument is accepted for CLI compatibility (same shape as
    validate-findings --files) but is NOT used to narrow the classification.
    Per-package PACKAGE_STACKS records carry `framework`, not a `nature`,
    and building a framework->UI-nature map would weaken the classifier
    (the failure modes are asymmetric: a false is_ui=False silently drops
    the a11y audit, while a false is_ui=True merely triggers a wasted
    dispatch that design-auditor's own platform preflight handles gracefully).
    PROJECT_NATURES is the sole clean, non-fuzzy signal.

_match_package is mirrored from _implement/_cmds_verify.py (see comment
there) to avoid transitive dependency coupling into _implement's heavier
workspace resolver.

Stdlib only.  Python 3.8+.
"""

import json
import os
from typing import List, Optional

# ---------------------------------------------------------------------------
# UI-nature constants
# ---------------------------------------------------------------------------

# Project natures that indicate UI code is present.
_UI_NATURES = frozenset({"web", "mobile", "desktop"})

# Path within the workspace root to project-config.json.
_CONFIG_REL_PATH = os.path.join(".devforge", "project-config.json")


# ---------------------------------------------------------------------------
# _match_package (mirrored from _implement/_cmds_verify.py)
#
# SOURCE: src/devforge/lib/_implement/_cmds_verify.py :: _match_package
# Mirrored here rather than imported to avoid dragging in _implement's
# transitive dependencies (resolve_workspace, node_bin, etc.) into the
# lighter _review package.  Any divergence from the original must be
# treated as a bug in this copy.  See the original for the authoritative
# spec-comment and test coverage.
# ---------------------------------------------------------------------------


def _match_package(file_path, package_stacks):
    # type: (str, List[dict]) -> Optional[dict]
    """Find the package whose path is the longest prefix of file_path.

    Packages are checked longest-path first; first match wins.
    Returns the matching package dict, or None if no package matches.

    Matching rule: package.path is a prefix of the file's directory when
    the file path starts with '<package_path>/' (slash-normalized).
    An exact path match (package.path == file_path) is also accepted.
    """
    if not package_stacks:
        return None

    # Normalize the file path to forward slashes (git always emits forward slashes).
    norm_file = file_path.replace("\\", "/")

    # Sort by path length descending so the longest (most specific) prefix wins.
    sorted_stacks = sorted(
        package_stacks,
        key=lambda p: len((p.get("path") or "").strip()),
        reverse=True,
    )

    for pkg in sorted_stacks:
        pkg_path = (pkg.get("path") or "").strip().rstrip("/")
        if not pkg_path:
            continue
        norm_pkg = pkg_path.replace("\\", "/")
        # Match: file starts with '<pkg_path>/' OR file == pkg_path.
        if norm_file == norm_pkg or norm_file.startswith(norm_pkg + "/"):
            return pkg

    return None


# ---------------------------------------------------------------------------
# resolve_ui_scope
# ---------------------------------------------------------------------------


def resolve_ui_scope(files, workspace_root):
    # type: (List[str], str) -> dict
    """Return a UI-scope classification dict for review_helper resolve-ui-scope.

    Parameters
    ----------
    files : list[str]
        Touched source-relative file paths from the feature diff.
        Accepted for CLI compatibility; not used for narrowing classification
        (see module docstring for the asymmetric-failure-mode rationale).
    workspace_root : str
        Workspace root path (where .devforge/ lives).

    Returns
    -------
    dict with keys:
      is_ui         -- bool: True if the project contains UI code
      platform_hint -- "web" | "mobile" | None
      natures       -- list[str]: the raw PROJECT_NATURES value (or [])
      reason        -- str: human-readable classification rationale
    """
    config_path = os.path.join(workspace_root, _CONFIG_REL_PATH)

    # --- Load project-config.json ---
    try:
        with open(config_path, "r", encoding="utf-8") as fh:
            config = json.load(fh)
        if not isinstance(config, dict):
            raise ValueError("project-config.json is not a JSON object")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        # Recall bias: config unreadable -> default is_ui=True so a11y is
        # not silently dropped on a broken or missing config.
        return {
            "is_ui": True,
            "platform_hint": None,
            "natures": [],
            "reason": (
                "project-config.json unreadable or malformed ({0}); "
                "defaulting to is_ui=True (recall bias)".format(exc)
            ),
        }

    # --- Read PROJECT_NATURES ---
    natures_raw = config.get("PROJECT_NATURES")
    if not natures_raw or not isinstance(natures_raw, list):
        # Recall bias: PROJECT_NATURES absent or empty (e.g. an older config
        # predating the field) -> default is_ui=True so a11y is not silently
        # skipped.
        return {
            "is_ui": True,
            "platform_hint": None,
            "natures": [],
            "reason": (
                "PROJECT_NATURES absent or empty (got {0!r}); "
                "defaulting to is_ui=True (recall bias — do not silently skip "
                "a11y on a config that predates this field)".format(natures_raw)
            ),
        }

    # Keep only string entries (type guard for a malformed array).
    natures = [str(n) for n in natures_raw if isinstance(n, str)]

    # --- Classify against the UI-nature set (CASE-INSENSITIVE) ---
    # PROJECT_NATURES is NOT enum-restricted at set time (see _configure
    # _schema.py) and _cmd_set_string_array stores values verbatim, so a
    # title-cased "Web" or "Mobile" can reach here. A case-sensitive compare
    # would miss it -> is_ui=False -> the a11y audit silently dropped, which
    # violates this helper's recall-bias contract. Lower-case both sides.
    ui_overlap = [n.lower() for n in natures if n.lower() in _UI_NATURES]
    is_ui = bool(ui_overlap)

    if is_ui:
        # platform_hint: web > mobile > None (desktop has no distinct a11y hint).
        if "web" in ui_overlap:
            platform_hint = "web"  # type: Optional[str]
        elif "mobile" in ui_overlap:
            platform_hint = "mobile"
        else:
            # desktop-only: is_ui=True but no specific hint
            platform_hint = None
        reason = (
            "PROJECT_NATURES {0!r} contains UI nature(s) {1!r}; "
            "accessibility audit warranted".format(natures, ui_overlap)
        )
    else:
        platform_hint = None
        reason = (
            "PROJECT_NATURES {0!r} has no UI natures "
            "(UI = {{{1}}}); accessibility audit not warranted".format(
                natures, ", ".join(sorted(_UI_NATURES))
            )
        )

    return {
        "is_ui": is_ui,
        "platform_hint": platform_hint,
        "natures": natures,
        "reason": reason,
    }
