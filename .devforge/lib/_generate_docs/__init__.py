"""Internal package for generate_docs_helper.

The public entry point is `main` (re-exported below). Submodules are
underscore-prefixed to mark them as internal — external callers should
import via `generate_docs_helper.main` (the shim) or invoke the POSIX
launcher `generate_docs`.
"""

from ._cli import main

__all__ = ["main"]
