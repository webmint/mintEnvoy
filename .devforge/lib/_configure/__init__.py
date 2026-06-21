"""Internal package for configure_helper.

Public entry point is `main` (re-exported below). Submodules are
underscore-prefixed; external callers should import via
`configure_helper.main` (the shim) or invoke the POSIX launcher
`configure_helper`.
"""

from ._cli import main

__all__ = ["main"]
