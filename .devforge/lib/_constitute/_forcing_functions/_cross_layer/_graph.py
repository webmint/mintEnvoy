"""Layer-graph resolver for the cross-layer import detector (Phase 3).

Loads the ``layer_graph`` and ``layer_dirs`` configuration from a validated
config dict and builds the directed allowed-import map used by the scanner.

Public API
----------
load_layer_graph(config)
    Validates + parses ``layer_graph`` and ``layer_dirs`` blocks from a rule
    config dict.  Returns ``(allowed_imports_map, layer_dirs_map)``.

classify_path(rel_path, layer_dirs_map)
    Returns the layer name that owns ``rel_path``, or ``None`` if the path
    does not fall under any declared layer.

Design notes
------------
- ``allowed_imports_map[L]`` always includes ``L`` itself (same-layer imports
  are always allowed — intra-layer cohesion is not a violation).
- Every layer that appears in either ``layer_graph`` or ``layer_dirs`` MUST
  appear in BOTH.  Missing-in-one raises ``ValueError`` at load time so
  misconfigured detectors surface immediately rather than silently skipping
  files.
- ``layer_dirs`` values may be a single glob string OR a list of glob
  strings.  List form supports the paired-pattern convention (e.g.,
  ``["pkg/domain/**", "**/pkg/domain/**"]``) needed to cover both top-level
  and nested paths when using ``fnmatch`` (which does NOT expand ``**``
  across directory separators).
- ``classify_path`` uses first-match-wins iteration over ``layer_dirs_map``
  in dict insertion order.  If two layers' globs overlap on a single path,
  the layer declared first in the config wins.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


def load_layer_graph(
    config: dict,
) -> Tuple[Dict[str, Set[str]], Dict[str, List[str]]]:
    """Load and validate ``layer_graph`` + ``layer_dirs`` from a rule config dict.

    Parameters
    ----------
    config:
        The ``forcing_functions.cross_layer_imports`` block as a Python dict.
        Expected shape::

            {
                "layer_graph": {"domain": [], "infra": ["domain"], ...},
                "layer_dirs":  {"domain": "pkg/domain/**", "infra": ["pkg/infra/**", ...]}
            }

    Returns
    -------
    (allowed_imports_map, layer_dirs_map)
        ``allowed_imports_map``
            ``{layer_name: frozenset-like set of layer names that layer_name
            may import from, always including layer_name itself}``.
        ``layer_dirs_map``
            ``{layer_name: [glob_string, ...]}``.  Single-string dir values
            are normalised to a one-element list.

    Raises
    ------
    ValueError
        If any layer name appears in ``layer_graph`` but not in
        ``layer_dirs`` (or vice versa), or if a ``layer_graph`` dependency
        list references an unknown layer name.
    """
    raw_graph: dict = config.get("layer_graph", {})
    raw_dirs: dict = config.get("layer_dirs", {})

    if not isinstance(raw_graph, dict):
        raise ValueError("layer_graph must be a dict mapping layer names to lists")
    if not isinstance(raw_dirs, dict):
        raise ValueError("layer_dirs must be a dict mapping layer names to glob strings/lists")

    graph_keys: Set[str] = set(raw_graph.keys())
    dirs_keys: Set[str] = set(raw_dirs.keys())

    # Every layer must appear in BOTH maps.
    only_in_graph = graph_keys - dirs_keys
    only_in_dirs = dirs_keys - graph_keys
    if only_in_graph:
        raise ValueError(
            "layer(s) {names!r} declared in layer_graph but missing from layer_dirs".format(
                names=sorted(only_in_graph)
            )
        )
    if only_in_dirs:
        raise ValueError(
            "layer(s) {names!r} declared in layer_dirs but missing from layer_graph".format(
                names=sorted(only_in_dirs)
            )
        )

    all_layers: Set[str] = graph_keys  # == dirs_keys at this point

    # Validate that every dependency list references known layers.
    for layer, deps in raw_graph.items():
        if not isinstance(deps, list):
            raise ValueError(
                "layer_graph[{layer!r}] must be a list of layer names, got {t}".format(
                    layer=layer, t=type(deps).__name__
                )
            )
        unknown = [d for d in deps if d not in all_layers]
        if unknown:
            raise ValueError(
                "layer_graph[{layer!r}] references unknown layer(s) {unknown!r}".format(
                    layer=layer, unknown=sorted(unknown)
                )
            )

    # Build allowed_imports_map: include self always.
    allowed_imports_map: Dict[str, Set[str]] = {}
    for layer, deps in raw_graph.items():
        allowed_imports_map[layer] = set(deps) | {layer}

    # Normalise layer_dirs values to lists of strings.
    layer_dirs_map: Dict[str, List[str]] = {}
    for layer, globs in raw_dirs.items():
        if isinstance(globs, str):
            layer_dirs_map[layer] = [globs]
        elif isinstance(globs, list):
            layer_dirs_map[layer] = list(globs)
        else:
            raise ValueError(
                "layer_dirs[{layer!r}] must be a string or list of strings, got {t}".format(
                    layer=layer, t=type(globs).__name__
                )
            )

    return allowed_imports_map, layer_dirs_map


def classify_path(
    rel_path: Path,
    layer_dirs_map: Dict[str, List[str]],
) -> Optional[str]:
    """Return the layer name this path belongs to, or ``None`` if unmatched.

    Iterates ``layer_dirs_map`` in insertion order.  For each layer, tests
    the path against every glob pattern using ``fnmatch.fnmatch``.  The
    first layer whose glob list contains a match is returned.

    Parameters
    ----------
    rel_path:
        File path relative to the consumer project root.
    layer_dirs_map:
        ``{layer_name: [glob_string, ...]}``.  Glob strings are matched
        against the string representation of ``rel_path`` using
        ``fnmatch.fnmatch`` (NOT recursive ``**`` expansion — see
        paired-pattern convention in module docstring).

    Returns
    -------
    Layer name string, or ``None`` if no glob matches.
    """
    path_str = str(rel_path)
    for layer, globs in layer_dirs_map.items():
        for glob in globs:
            if fnmatch.fnmatch(path_str, glob):
                return layer
    return None
