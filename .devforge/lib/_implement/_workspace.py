"""_workspace -- workspace resolver for /implement.

Resolves where the install root and the source root are, and whether this
is a wrapper-mode install (source code lives in a nested git repo) or a
standalone install (single repo, source == install).

The canonical config field is PROJECT_ROOT inside
<install_root>/.devforge/project-config.json:
  - Standalone: PROJECT_ROOT == "." (or absent/empty — treated as ".")
  - Wrapper:    PROJECT_ROOT == "db-cse-ui-strata" (a non-trivial relative path)

This module is the single source of truth for repo targeting in
_implement.  Every helper that needs to distinguish the install root from
the source root imports Workspace + resolve_workspace from here rather
than reading project-config.json ad-hoc.

Design notes:

- Frozen dataclass: fields are set once at construction; callers get an
  immutable value they can thread through phases without mutation risk.

- resolve_workspace is FAIL-SOFT: if project-config.json is missing,
  unreadable, malformed JSON, or lacks PROJECT_ROOT, it returns a
  standalone Workspace (source_root == install_root, is_wrapper False).
  This keeps non-configured repos and testForge-less environments working
  exactly as they did before the wrapper feature.

- install_root is resolved to an absolute path by the caller or by
  resolve_workspace's internal normalization; source_root is always
  absolute (install_root.resolve() / PROJECT_ROOT, then .resolve() so
  "." collapses cleanly).

- Type-hint convention: typing.Optional (Python 3.8+). No PEP 604
  (X | None) or PEP 585 (list[str]) syntax. from __future__ import
  annotations intentionally NOT used.

Stdlib only. No third-party dependencies.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CONFIG_FILENAME = "project-config.json"

# PROJECT_ROOT values that mean "standalone" (source == install).
# Compared after strip(); case-sensitive.
_STANDALONE_ROOTS = frozenset(["", "."])


# ---------------------------------------------------------------------------
# Workspace dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Workspace:
    """Frozen snapshot of the install vs source root split.

    Fields:
      install_root  Absolute Path to the forge install (wrapper) root.
                    This is where .devforge/, specs/, constitution.md, etc. live.
      source_root   Absolute Path to the source code root.
                    Equals install_root for standalone; equals
                    install_root / PROJECT_ROOT for wrapper mode.
      is_wrapper    True when PROJECT_ROOT is non-trivial (wrapper mode).
                    False for standalone (single repo).
    """

    install_root: Path
    source_root: Path
    is_wrapper: bool

    def __post_init__(self):
        # type: () -> None
        if not isinstance(self.install_root, Path):
            raise ValueError(
                "Workspace.install_root must be a pathlib.Path, "
                "got {0}".format(type(self.install_root).__name__)
            )
        if not isinstance(self.source_root, Path):
            raise ValueError(
                "Workspace.source_root must be a pathlib.Path, "
                "got {0}".format(type(self.source_root).__name__)
            )
        if not isinstance(self.is_wrapper, bool):
            raise ValueError(
                "Workspace.is_wrapper must be a bool, "
                "got {0}".format(type(self.is_wrapper).__name__)
            )


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------


def _read_project_root(install_root):
    # type: (Path) -> Optional[str]
    """Read PROJECT_ROOT from .devforge/project-config.json.

    Returns the raw string value on success, or None on any failure:
    - config file absent or unreadable
    - malformed JSON
    - JSON is not a dict
    - PROJECT_ROOT key absent

    Never raises.
    """
    config_path = install_root / ".devforge" / _CONFIG_FILENAME
    try:
        with open(str(config_path), "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, IOError, json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    raw = data.get("PROJECT_ROOT")
    if not isinstance(raw, str):
        return None
    return raw


def resolve_workspace(install_root):
    # type: (object) -> Workspace
    """Resolve and return the Workspace for the given install root.

    Reads PROJECT_ROOT from <install_root>/.devforge/project-config.json.
    Falls back to standalone (source_root == install_root, is_wrapper False)
    on any config read failure — never raises.

    Parameters
    ----------
    install_root : str or Path
        Path to the forge install root (wrapper or standalone repo root).
        Resolved to an absolute path internally.

    Returns
    -------
    Workspace
        A frozen dataclass with install_root, source_root, and is_wrapper set.
    """
    # Normalise to a resolved absolute Path.
    root = Path(install_root).resolve()

    raw = _read_project_root(root)

    # Treat missing/empty/bare-dot as standalone.
    if raw is None or raw.strip() in _STANDALONE_ROOTS:
        return Workspace(
            install_root=root,
            source_root=root,
            is_wrapper=False,
        )

    project_root_str = raw.strip()
    # Compute source_root: join then resolve so any ".." or symlinks collapse.
    source_root = (root / project_root_str).resolve()

    return Workspace(
        install_root=root,
        source_root=source_root,
        is_wrapper=True,
    )
