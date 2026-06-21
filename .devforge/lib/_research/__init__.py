"""Internal package for research_helper.

Public entry point is `main` (re-exported below). Submodules are
underscore-prefixed; external callers should import via
`research_helper.main` (the shim) or invoke the POSIX launcher
`research_helper`.
"""

from ._cli import main

__all__ = ["main"]
