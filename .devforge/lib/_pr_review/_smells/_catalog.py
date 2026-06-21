"""Smell-heuristic registry and dispatcher.

Owns the CATALOG of registered heuristics and the run_all() dispatch function.
Heuristic modules register themselves by calling register() at import time
(via _smells/__init__.py which imports each module).

Finding schema — every heuristic emits dicts with these keys:
    name     : str  — heuristic name, e.g. "empty_pr_body"
    severity : str  — one of: "nit", "low", "medium"
                      ("high" reserved for Step 5 blast-radius-driven heuristics)
    location : str  — diff location if applicable; "*" for whole-PR; "N/A" for non-code.
                      All `location` values use 0-based indexing for both diff line
                      offsets (e.g. "diff:line+0" for the first added line) and commit
                      list positions (e.g. "commit:0" for the first commit subject).
    evidence : str  — human-readable evidence quote, short string

Heuristics may emit MULTIPLE findings per invocation (e.g. one per hedge-
defensive match in the diff).  run_all() returns a flat list of all findings
from all registered heuristics, in registration order.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Tuple

# Import here to avoid circular: _catalog does not import heuristic modules.
# Heuristic modules import PRReviewState from _state directly.
# The TYPE_CHECKING guard is not needed since we only use the name for the alias.


# Type alias: a heuristic function takes a state object and returns findings.
# We use Any here to avoid importing PRReviewState at module level (which would
# create a package-level circular dependency if _smells/__init__.py imports
# heuristic modules that in turn import _catalog).
HeuristicFn = Callable[[Any], List[Dict[str, Any]]]

# Registry entries: (name, severity_default, fn).
# severity_default is stored for documentation purposes; the fn itself embeds
# the severity into each finding it emits.
_CATALOG: List[Tuple[str, str, HeuristicFn]] = []


def register(name: str, severity: str, fn: HeuristicFn) -> None:
    """Register a heuristic in the catalog.

    Args:
        name:     Unique heuristic name (e.g. "empty_pr_body").
        severity: Default severity ("nit", "low", "medium").
        fn:       Callable that accepts a PRReviewState and returns a list of
                  finding dicts.  May return an empty list if no smell found.

    Raises:
        ValueError: if a heuristic with the same name is already registered.
    """
    for existing_name, _, _ in _CATALOG:
        if existing_name == name:
            raise ValueError(
                "Heuristic already registered: {name!r}".format(name=name)
            )
    _CATALOG.append((name, severity, fn))


def run_all(state: Any) -> List[Dict[str, Any]]:
    """Dispatch every registered heuristic in registration order.

    Each heuristic may emit zero or more findings.  Findings from all
    heuristics are collected into a single flat list and returned.

    Args:
        state: PRReviewState instance (typed as Any to avoid circular import
               at the _catalog module level; runtime type is always PRReviewState).

    Returns:
        Flat list of finding dicts.  Empty list if no smells detected.
    """
    findings: List[Dict[str, Any]] = []
    for _name, _severity, fn in _CATALOG:
        findings.extend(fn(state))
    return findings


def clear_registry() -> None:
    """Remove all registered heuristics.

    Intended for test isolation only.  Production code does not call this.
    """
    _CATALOG.clear()
