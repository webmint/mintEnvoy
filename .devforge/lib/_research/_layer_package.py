"""Layer-boundary path utilities + check-8b predicate.

`_is_presentation_layer` classifies a path as a presentation-layer file
(extension or path-component heuristic). `_extract_package` derives a
two-component package key. `_compute_check_8b_would_fire` evaluates the
cross-layer rule used by cmd_verify check 8b AND cmd_set_recommended_approach
(for check-13 suppression).
"""

from __future__ import annotations

import os
from typing import Optional


# Presentation-layer file extensions.
_PRESENTATION_EXTENSIONS = {".vue", ".tsx", ".jsx"}

# Presentation-layer path fragments — must appear as full path components
# (i.e., preceded by '/') to avoid matching 'subviews/' when '/views/' is
# the intended sentinel.
_PRESENTATION_PATH_FRAGMENTS = ("/views/", "/components/", "/pages/", "/screens/", "/ui/")

# Presentation-layer path prefixes (normalized, no leading slash).
_PRESENTATION_PATH_PREFIXES = ("apps/app/", "apps/web/", "apps/frontend/")


def _is_presentation_layer(file_path: str) -> bool:
    """Return True iff file_path is a presentation-layer file.

    Heuristics (case-sensitive, in order):
    1. Extension ∈ {.vue, .tsx, .jsx}.
    2. Normalized path contains a presentation fragment (/views/, /components/,
       /pages/, /screens/, /ui/) — the leading '/' guards against false matches
       on e.g. 'subviews/'.
    3. Normalized path starts with a presentation prefix (apps/app/, etc.).

    None or empty → False.
    """
    if not file_path:
        return False
    # Extension check.
    _, ext = os.path.splitext(file_path)
    if ext in _PRESENTATION_EXTENSIONS:
        return True
    # Normalize: strip leading './' but keep leading '/' so fragment checks work.
    normalized = file_path
    if normalized.startswith("./"):
        normalized = normalized[2:]
    # Prepend '/' so fragment checks work on paths that start at the first
    # component (e.g. 'src/views/Foo.ts' → '/src/views/Foo.ts').
    slashed = "/" + normalized if not normalized.startswith("/") else normalized
    for frag in _PRESENTATION_PATH_FRAGMENTS:
        if frag in slashed:
            return True
    # Prefix check against normalized (leading '/' already stripped by logic above).
    normed_no_slash = normalized.lstrip("/")
    for prefix in _PRESENTATION_PATH_PREFIXES:
        if normed_no_slash.startswith(prefix):
            return True
    return False


def _extract_package(file_path: str) -> str:
    """Derive a two-component package key from file_path.

    Rules:
    - Strip a leading '/' or './' prefix.
    - Split on '/'; take the first two components when both are present.
    - When only one component exists (no '/'), return it as-is.
    - None, empty, or whitespace-only → empty string.

    Examples:
      'apps/app/src/foo.vue' → 'apps/app'
      'foo/utils.ts'    → 'foo'  (file at index 1)
      'src/admin/Products.vue'   → 'src/admin'
      'foo.vue'                  → 'foo.vue'
      './apps/web/x.ts'          → 'apps/web'
      '/apps/web/x.ts'           → 'apps/web'
      ''                         → ''
    """
    if not file_path or not file_path.strip():
        return ""
    # Strip leading './' or '/'.
    normalized = file_path
    if normalized.startswith("./"):
        normalized = normalized[2:]
    normalized = normalized.lstrip("/")
    parts = normalized.split("/")
    # Filter out empty segments (shouldn't arise after strip, but be safe).
    parts = [p for p in parts if p]
    if not parts:
        return ""
    if len(parts) == 1:
        # Single component — no directory structure, return as-is.
        return parts[0]
    # Two components: if the second is a file (contains '.'), the first
    # component IS the package (flat-package layout like foo/utils.ts).
    # If the second has no dot it's a directory → return both (src/admin).
    if len(parts) == 2 and "." in parts[1]:
        return parts[0]
    # Three or more components, or two components where the second is a
    # directory: return first two.
    return parts[0] + "/" + parts[1]


# ---------------------------------------------------------------------------
# Check 8b predicate — shared between cmd_verify and cmd_set_recommended_approach.
# ---------------------------------------------------------------------------


def _compute_check_8b_would_fire(report: dict, bug_mode: bool) -> bool:
    """Return True iff check 8b's conditions are fully met.

    Conditions (all must hold):
    - bug_mode is True
    - fix_path_helpers is non-empty
    - The first primary finding's file_line resolves to a presentation-layer path
      (per _is_presentation_layer)
    - Every fix_path_helper's file_line resolves to the SAME package as the
      primary symptom (i.e., no helper crosses a package boundary)

    Used by cmd_verify (to decide whether check 13 is suppressed) and by
    cmd_set_recommended_approach (to decide whether the single-layer gate
    should be enforced). When check 8b would fire, check 13 / the setter gate
    are structurally unavailable — the LLM's only recovery path is to add
    cross-layer helpers, not to supply single_layer_justification.
    """
    if not bug_mode:
        return False
    fix_path_helpers = report.get("fix_path_helpers") or []
    if not fix_path_helpers:
        return False
    # Identify the primary symptom path from findings.
    primary_path = None  # type: Optional[str]
    for f in (report.get("findings") or []):
        framing_val = f.get("framing") or "primary"
        if framing_val == "primary":
            fl = f.get("file_line") or ""
            colon_pos = fl.rfind(":")
            primary_path = fl[:colon_pos] if colon_pos > 0 else (fl if fl else None)
            break
    if not primary_path or not _is_presentation_layer(primary_path):
        return False
    symptom_pkg = _extract_package(primary_path)
    # All helpers must be in the same package as the symptom for 8b to fire.
    for h in fix_path_helpers:
        if not isinstance(h, dict):
            continue
        helper_file_line = h.get("file_line") or ""
        colon_pos = helper_file_line.rfind(":")
        helper_file = helper_file_line[:colon_pos] if colon_pos > 0 else helper_file_line
        if _extract_package(helper_file) != symptom_pkg:
            return False
    return True
