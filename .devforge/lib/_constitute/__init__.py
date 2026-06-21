"""Internal package for constitute_helper.

Public entry point is `main` (re-exported below). Submodules are
underscore-prefixed; external callers should import via
`constitute_helper.main` (the shim) or invoke the POSIX launcher
`constitute_helper`.
"""

from ._cli import main

__all__ = ["main"]
