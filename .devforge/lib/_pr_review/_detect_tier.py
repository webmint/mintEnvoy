"""Pure-filesystem forge-tier detection for pr_review_helper.

`run(target, devforge_dir)` scans the target directory and returns a
structured dict classifying the repo's forge state into one of three
tiers:

  full    — .devforge/constitute.json + src/constitution.md + at least
             one concern doc directory under .devforge/
  partial — at least one of the two key files exists, but not both
             combined with concern dirs
  none    — no forge artefacts found at all

The returned dict matches the schema consumed by the LLM orchestrator
in /pr-review Phase 0. Paths in the manifest are always absolute.

No subprocess, no network. Stdlib only. Targets Python 3.8+.
"""

from __future__ import annotations

import os
from typing import List, Optional

# Priority-ordered list of well-known ADR directory names.
# First existing path under target wins; later candidates are not checked.
_ADR_CANDIDATES = (
    "docs/adr",
    "docs/architecture/decisions",
    "architecture/decisions",
    "adr",
)

# Operational subdirectories under .devforge/ that are NOT concern doc dirs.
# install.sh copies src/devforge/lib/ → .devforge/lib/ (line 114) and creates
# .devforge/template/ (line 156). /pr-review itself creates .devforge/pr-reviews/.
# Without this exclusion, a freshly-installed forge repo always satisfies
# has_concerns=True from lib/, misclassifying as `full` tier.
_DEVFORGE_INFRA_SUBDIRS = frozenset(["lib", "template", "pr-reviews"])


# ---------------------------------------------------------------------------
# Internal helpers.
# ---------------------------------------------------------------------------


def _find_concern_dirs(devforge_path: str) -> List[str]:
    """Return sorted list of absolute paths to concern doc subdirectories of devforge_path.

    Only directories (not files) directly under devforge_path are included.
    Operational infra dirs (lib/, template/, pr-reviews/) are excluded via
    _DEVFORGE_INFRA_SUBDIRS — install.sh copies forge lib/ there, which would
    otherwise trigger false-positive full-tier detection before /generate-docs runs.
    Returns empty list when devforge_path does not exist.
    """
    if not os.path.isdir(devforge_path):
        return []
    result = []
    try:
        entries = os.listdir(devforge_path)
    except OSError:
        return []
    for name in entries:
        full = os.path.join(devforge_path, name)
        if os.path.isdir(full) and name not in _DEVFORGE_INFRA_SUBDIRS:
            result.append(full)
    result.sort()
    return result


def _find_adr_dir(target: str) -> Optional[str]:
    """Return absolute path of the first existing ADR directory, or None.

    Checks each entry in _ADR_CANDIDATES in order; returns the first
    whose joined path with target resolves to an existing directory.
    """
    for candidate in _ADR_CANDIDATES:
        full = os.path.join(target, candidate)
        if os.path.isdir(full):
            return full
    return None


def _find_constitution(target: str) -> Optional[str]:
    """Return absolute path of constitution.md, or None.

    Checks src/constitution.md first (forge convention), then
    constitution.md at the repo root. Returns first existing file.
    """
    for relpath in ("src/constitution.md", "constitution.md"):
        full = os.path.join(target, relpath)
        if os.path.isfile(full):
            return full
    return None


def _classify_tier(
    constitute_json: Optional[str],
    constitution_md: Optional[str],
    concern_doc_dirs: List[str],
) -> str:
    """Map presence of forge artefacts to a tier string.

    Rules (single canonical mapping, no escape hatches):
      full    — constitute_json exists AND constitution_md exists AND
                concern_doc_dirs is non-empty
      partial — at least one of constitute_json OR constitution_md exists
                (but the full condition is not satisfied)
      none    — neither constitute_json nor constitution_md exists
    """
    has_json = constitute_json is not None
    has_md = constitution_md is not None
    has_concerns = len(concern_doc_dirs) > 0

    if has_json and has_md and has_concerns:
        return "full"
    if has_json or has_md:
        return "partial"
    return "none"


# ---------------------------------------------------------------------------
# Public entry point.
# ---------------------------------------------------------------------------


def run(target: str, devforge_dir: str = ".devforge") -> dict:
    """Scan target for forge artefacts and return a tier classification dict.

    Args:
        target:      Absolute path to the repository root to scan.
        devforge_dir: Name of the devforge directory (default ".devforge").
                      Joined with target to locate .devforge/.

    Returns a dict with keys:
      tier           — "full" | "partial" | "none"
      manifest       — dict with constitute_json, constitution_md,
                       concern_doc_dirs, adr_dir
      target_path    — absolute path of target (normalized via os.path.abspath)
    """
    abs_target = os.path.abspath(target)
    devforge_path = os.path.join(abs_target, devforge_dir)

    constitute_json_path = os.path.join(devforge_path, "constitute.json")
    constitute_json: Optional[str] = (
        constitute_json_path if os.path.isfile(constitute_json_path) else None
    )

    constitution_md = _find_constitution(abs_target)
    concern_doc_dirs = _find_concern_dirs(devforge_path)
    adr_dir = _find_adr_dir(abs_target)

    tier = _classify_tier(constitute_json, constitution_md, concern_doc_dirs)

    return {
        "manifest": {
            "adr_dir": adr_dir,
            "concern_doc_dirs": concern_doc_dirs,
            "constitute_json": constitute_json,
            "constitution_md": constitution_md,
        },
        "target_path": abs_target,
        "tier": tier,
    }
