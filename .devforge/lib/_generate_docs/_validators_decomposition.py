"""Decomposition gate: verifies every substantive subfolder under
`<package_path>/src/` is registered as a concern.

Owns `_is_substantive_subfolder`, `_scan_substantive_subfolders`, and
`_check_decomposition`. Imports shared helpers from `_validators_shared`.

Stdlib only. Targets Python 3.8+.
"""

from pathlib import Path
from typing import Any, Dict, List, Tuple

from ._validators_shared import _err


# ---------------------------------------------------------------------------
# Decomposition gate (Phase 3.1).
#
# A package is "decomposed" if every substantive subfolder under
# `<package_path>/src/` is registered as a concern. The gate walks the
# top-level subfolders only (no recursion) and compares against
# `pkg["concerns"]`. Substantive = ≥2 files OR a known architectural-
# role basename. Trivial leaves (assets, dist, etc.) are skipped
# unconditionally.
#
# These lists are intentionally small KISS extension points. Match by
# basename (folder name), not by detected language — a Java project
# with a `services/` folder gets the same treatment as a Python project
# with `services/`. Add to the lists on evidence; do not preemptively
# expand.
# ---------------------------------------------------------------------------


_ARCH_ROLE_FOLDER_NAMES: Tuple = (
    # JS/TS
    "components", "composables", "services", "routing", "router",
    "stores", "plugins", "helpers", "hooks",
    # Python
    "handlers", "models", "repositories", "views", "serializers",
    # Go
    "middleware", "repository", "service",
    # Rust
    "traits",
    # Java/Kotlin
    "controllers", "entities",
)


_TRIVIAL_LEAF_FOLDER_NAMES: Tuple = (
    "assets", "static", "node_modules", "__pycache__", "target", "dist",
    "build", "vendor", "locales", "i18n", "fixtures", "__tests__",
    "test", "tests",
)


def _is_substantive_subfolder(subdir: Path) -> bool:
    """Return True if `subdir` qualifies as a substantive subfolder.

    Rules (in order):
    1. Trivial-leaf basename -> always-skip (return False even if
       file count would otherwise qualify).
    2. Architectural-role basename -> always-substantive (return True
       even when the folder contains a single file — e.g., a `services/`
       directory holding one service file is still architecturally
       meaningful).
    3. Otherwise: substantive iff direct child file count is ≥ 2.

    File count walks only direct children (top-level) — sub-files inside
    nested subdirectories don't count. This keeps the gate's behavior
    predictable: a folder with one file plus several deep subfolders
    would NOT register as substantive without the role-name override,
    matching the operator's mental model that "≥2 files in this folder"
    means an architectural cluster.
    """
    name = subdir.name
    if name in _TRIVIAL_LEAF_FOLDER_NAMES:
        return False
    if name in _ARCH_ROLE_FOLDER_NAMES:
        return True
    try:
        entries = [p for p in subdir.iterdir() if p.is_file()]
    except OSError:
        # Permission errors are surfaced indirectly: an unreadable
        # subfolder cannot be substantive (we have no signal). The
        # operator can intervene if needed.
        return False
    return len(entries) >= 2


def _scan_substantive_subfolders(src_dir: Path) -> List[str]:
    """Return sorted basenames of substantive subfolders under `src_dir`.

    No recursion — only top-level. Stable sort so error messages are
    deterministic. Returns `[]` when `src_dir` doesn't exist (the
    decomposition gate becomes a no-op for flat-layout packages).
    """
    if not src_dir.is_dir():
        return []
    found: List[str] = []
    try:
        children = sorted(src_dir.iterdir(), key=lambda p: p.name)
    except OSError:
        return []
    for child in children:
        if not child.is_dir():
            continue
        if _is_substantive_subfolder(child):
            found.append(child.name)
    return found


def _check_decomposition(
    pkg: Dict[str, Any],
    package_path: str,
    project_root: Path,
) -> List[Dict[str, Any]]:
    """Verify registered concerns cover every substantive subfolder.

    No-op when `<project_root>/<package_path>/src/` doesn't exist (some
    ecosystems use a flat package layout). When `src/` exists, every
    substantive top-level subfolder must be registered as a concern.

    The gate emits one error record per missing concern (no truncation —
    LLMs need the full list to fix in one pass).
    """
    src_dir = project_root / package_path / "src"
    substantive = _scan_substantive_subfolders(src_dir)
    if not substantive:
        return []
    registered = set((pkg.get("concerns") or {}).keys())
    errors: List[Dict[str, Any]] = []
    for subfolder in substantive:
        if subfolder in registered:
            continue
        # Include the subfolder name in the message text AND as a
        # structured `subfolder` extra. The CLI's text output (consumed
        # by the LLM running /generate-docs) renders the message text
        # only — keeping the name in the message keeps it visible at
        # the prompt without forcing the consumer to parse a JSON tail.
        errors.append(_err(
            "decomposition", "concerns",
            "missing concern for substantive subfolder {0!r} under "
            "{1}/src/; run add-concern --package {1} --concern "
            "{0}".format(subfolder, package_path),
            subfolder=subfolder,
        ))
    return errors
