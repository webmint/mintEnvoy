"""Shared utilities consumed by multiple devforge.lib subpackages.

Modules here are pure-function / pure-regex utilities with no
helper-specific state. Cross-subpackage imports from `_shared/` are
the supported way to reuse logic between sibling helpers (e.g.
`_research`).
"""
