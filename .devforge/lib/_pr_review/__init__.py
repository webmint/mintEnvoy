"""Internal package for pr_review_helper.

Public entry point is `main` (re-exported below). Submodules are
underscore-prefixed; external callers should invoke via the POSIX
launcher `pr_review_helper` or via `pr_review_helper.main`.
"""

from ._cli import main

__all__ = ["main"]
