"""node_bin -- Node.js local bin resolution utilities.

Mimics npm's upward-walk strategy for resolving devDependency binaries
that live in `node_modules/.bin/` rather than on the global PATH.

Two public functions:

    node_bin_dirs(source_root, package_path)
        Return the ordered list of `node_modules/.bin` directories to
        search, walking from the package directory up to source_root.
        Most-specific (package-local) first; least-specific (hoisted
        root) last.  Only dirs that EXIST on disk are returned.

    resolves(executable_token, source_root, package_path)
        Return True if `shutil.which(token)` finds the binary on the
        global PATH OR the binary exists as an executable file in any
        of the `node_bin_dirs`.

These are consumed by two distinct helpers that must stay consistent:
    _implement._cmds_verify   — prepends node_bin_dirs to subprocess PATH
                                (env-PATH path; the actual runner)
    _configure._validators    — calls node_bin_dirs() directly via
                                collect_executability_warnings to probe
                                per-package bin dirs before emitting a
                                "not found" warning

If one helper can run a locally-installed binary, the other will predict
(probe) it correctly.  Both helpers import from here so the resolution
logic is defined in exactly one place.

Stdlib only.  Python 3.8+.
"""

import os
import shutil
from pathlib import Path
from typing import List


def node_bin_dirs(source_root, package_path):
    # type: (str, str) -> List[str]
    """Return existing `node_modules/.bin` dirs for a package, root-inclusive.

    Walk upward from `<source_root>/<package_path>` to `source_root`
    (inclusive), collecting each `<dir>/node_modules/.bin` that exists.

    Order: most-specific (package-local) first, least-specific (hoisted
    root) last.  This mirrors npm's resolution order: a locally installed
    binary shadows a hoisted one.

    Args:
        source_root:  Absolute path to the project's source root
                      (the directory that contains node_modules/ at the
                      top level when dependencies are hoisted).
        package_path: Package-relative path from source_root (e.g.
                      "packages/frontend" or "services/api").
                      Empty string or "." means start from source_root
                      itself (only the root node_modules/.bin is checked).

    Returns:
        List of absolute path strings for existing `node_modules/.bin`
        dirs, ordered most-specific first.  May be empty if no
        `node_modules/.bin` exists anywhere in the walk.

    Examples:
        source_root = "/proj"
        package_path = "packages/frontend"
        Walk: /proj/packages/frontend, /proj/packages, /proj
        Returned (if all exist):
          ["/proj/packages/frontend/node_modules/.bin",
           "/proj/packages/node_modules/.bin",
           "/proj/node_modules/.bin"]
    """
    root = Path(source_root).resolve()
    pkg_path = package_path.strip().strip("/") if package_path else ""

    # Compute the starting directory (package dir or source root).
    if pkg_path and pkg_path != ".":
        start = root / pkg_path
    else:
        start = root

    # Walk upward from start to root (inclusive), collecting existing bins.
    dirs = []
    current = start.resolve()

    while True:
        candidate = current / "node_modules" / ".bin"
        if candidate.is_dir():
            dirs.append(str(candidate))

        # Stop once we have processed source_root.
        if current == root:
            break

        parent = current.parent
        # Safety: if we somehow went above root (should not happen because
        # start is always under root, but be defensive), stop.
        # Use relative_to() — a separator-safe containment check — rather
        # than a string startswith() prefix, which would incorrectly pass
        # for sibling directories whose name happens to share the root's
        # string prefix (e.g. /tmp/proj_sibling startswith /tmp/proj).
        try:
            parent.relative_to(root)
        except ValueError:
            break
        current = parent

    return dirs


def resolves(executable_token, source_root, package_path):
    # type: (str, str, str) -> bool
    """Return True if executable_token can be found for this project.

    Checks two sources in order:
      1. Global PATH via shutil.which (standard resolution).
      2. Any existing `node_modules/.bin` dir returned by
         node_bin_dirs(source_root, package_path).

    A binary found in either source can be executed when the subprocess
    PATH is augmented with node_bin_dirs (as _cmds_verify does).

    Args:
        executable_token: Bare executable name (e.g. "vue-tsc", "eslint").
                          Caller must already have stripped flags/args.
        source_root:      Absolute path to the project source root.
        package_path:     Package path relative to source_root (may be "").

    Returns:
        True  — binary is findable via PATH or node_modules/.bin.
        False — binary is absent from both.
    """
    if shutil.which(executable_token) is not None:
        return True

    for bin_dir in node_bin_dirs(source_root, package_path):
        candidate = os.path.join(bin_dir, executable_token)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return True

    return False
