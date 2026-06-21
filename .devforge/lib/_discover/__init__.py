"""Internal package for discover_helper.

The public entry point is `main` (re-exported below). Submodules are
underscore-prefixed to mark them as internal — external callers should
import via `discover_helper.main` (the shim) or invoke the POSIX
launcher `discover_helper`.
"""

from ._cli import main

__all__ = ["main"]
