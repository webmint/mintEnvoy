"""Setter for forcing-functions config blocks in constitute.json.

Owns the read-merge-validate-write lifecycle for the
``forcing_functions.<rule>`` block in ``.devforge/constitute.json``.

Public API
----------
set_forcing_function(config_path, rule, enabled, *, generated_types_dirs,
                     allowlist_paths, layer_graph, layer_dirs)

    Write or update the named rule block inside the ``forcing_functions``
    top-level dict.  Reads the existing config, merges only the keys
    relevant to the rule, validates per-rule constraints when ``enabled``
    is True, then atomically replaces the file.

Supported rules
---------------
  magic_enum_duplication         -- requires non-empty generated_types_dirs
                                    when enabled; allowlist_paths optional
  cross_layer_imports            -- requires both layer_graph (dict) and
                                    layer_dirs (dict) when enabled; their
                                    keys must match
  any_with_generated_available   -- requires non-empty generated_types_dirs
                                    when enabled; allowlist_paths optional
  Unknown rule name              -- raises ValueError; caller exits non-zero

Atomic write
------------
Uses ``tempfile.mkstemp`` in the same directory as the target; ``os.replace``
on success; unlinks temp on any failure.  Mirrors ``_state._write_state``.

Python 3.8+ compatibility
--------------------------
No ``X | Y`` union syntax; uses ``Optional`` / ``List`` / ``Dict`` from
``typing`` throughout.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from .._schema import FORCING_FUNCTION_RULES

# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

# Re-export for callers that import KNOWN_RULES from this module directly.
KNOWN_RULES = FORCING_FUNCTION_RULES

# Maps rule config-key → the CLI verb accepted by constitute_helper.
# Keys must exactly match FORCING_FUNCTION_RULES — enforced by assertion below.
RULE_TO_VERB = {
    "magic_enum_duplication": "verify-magic-enum",
    "cross_layer_imports": "verify-cross-layer-imports",
    "any_with_generated_available": "verify-any-leak",
}  # type: Dict[str, str]

assert set(RULE_TO_VERB) == FORCING_FUNCTION_RULES, (
    "RULE_TO_VERB keys do not match FORCING_FUNCTION_RULES; "
    "update _setters.RULE_TO_VERB when adding a new rule"
)


# ---------------------------------------------------------------------------
# Validation helpers (private)
# ---------------------------------------------------------------------------

def _require_nonempty_list(value: Optional[List[str]], field: str) -> List[str]:
    """Assert value is a non-empty list; raise ValueError otherwise."""
    if not value or not isinstance(value, list) or len(value) == 0:
        raise ValueError(
            "{field}: must be a non-empty list when enabled=true".format(field=field)
        )
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                "{field}: every item must be a non-empty string".format(field=field)
            )
    return value


def _require_matching_dict_keys(
    graph: Optional[Dict], dirs: Optional[Dict], field_prefix: str
) -> None:
    """Assert that layer_graph and layer_dirs have exactly the same key set."""
    if not isinstance(graph, dict) or not graph:
        raise ValueError(
            "{prefix}.layer_graph: must be a non-empty dict when enabled=true".format(
                prefix=field_prefix
            )
        )
    if not isinstance(dirs, dict) or not dirs:
        raise ValueError(
            "{prefix}.layer_dirs: must be a non-empty dict when enabled=true".format(
                prefix=field_prefix
            )
        )
    graph_keys = set(graph.keys())
    dirs_keys = set(dirs.keys())
    if graph_keys != dirs_keys:
        extra_graph = sorted(graph_keys - dirs_keys)
        extra_dirs = sorted(dirs_keys - graph_keys)
        parts = []
        if extra_graph:
            parts.append("layer_graph has extra keys: {0}".format(extra_graph))
        if extra_dirs:
            parts.append("layer_dirs has extra keys: {0}".format(extra_dirs))
        raise ValueError(
            "{prefix}: layer_graph and layer_dirs keys must match; {msg}".format(
                prefix=field_prefix, msg="; ".join(parts)
            )
        )


def _validate_rule_block(
    rule: str,
    enabled: bool,
    generated_types_dirs: Optional[List[str]],
    allowlist_paths: Optional[List[str]],
    layer_graph: Optional[Dict],
    layer_dirs: Optional[Dict],
) -> None:
    """Validate per-rule constraints.  Raises ValueError on violation."""
    if rule == "magic_enum_duplication":
        if enabled:
            _require_nonempty_list(
                generated_types_dirs, "magic_enum_duplication.generated_types_dirs"
            )
        # allowlist_paths is optional; no constraint

    elif rule == "cross_layer_imports":
        if enabled:
            _require_matching_dict_keys(layer_graph, layer_dirs, "cross_layer_imports")

    elif rule == "any_with_generated_available":
        if enabled:
            _require_nonempty_list(
                generated_types_dirs, "any_with_generated_available.generated_types_dirs"
            )
        # allowlist_paths is optional; no constraint

    else:
        # Should not be reached if callers gate on KNOWN_RULES first, but
        # included for defence-in-depth.
        raise ValueError("unknown rule: {rule!r}".format(rule=rule))


# ---------------------------------------------------------------------------
# Block builders (private)
# ---------------------------------------------------------------------------

def _build_magic_enum_block(
    enabled: bool,
    generated_types_dirs: Optional[List[str]],
    allowlist_paths: Optional[List[str]],
) -> Dict:
    """Return a magic_enum_duplication config dict for the given inputs."""
    block = {}  # type: Dict
    block["enabled"] = enabled
    if generated_types_dirs is not None:
        block["generated_types_dirs"] = list(generated_types_dirs)
    if allowlist_paths is not None:
        block["allowlist_paths"] = list(allowlist_paths)
    return block


def _build_cross_layer_block(
    enabled: bool,
    layer_graph: Optional[Dict],
    layer_dirs: Optional[Dict],
    allowlist_paths: Optional[List[str]],
) -> Dict:
    """Return a cross_layer_imports config dict for the given inputs."""
    block = {}  # type: Dict
    block["enabled"] = enabled
    if layer_graph is not None:
        block["layer_graph"] = dict(layer_graph)
    if layer_dirs is not None:
        block["layer_dirs"] = dict(layer_dirs)
    if allowlist_paths is not None:
        block["allowlist_paths"] = list(allowlist_paths)
    return block


def _build_any_leak_block(
    enabled: bool,
    generated_types_dirs: Optional[List[str]],
    allowlist_paths: Optional[List[str]],
) -> Dict:
    """Return an any_with_generated_available config dict for the given inputs."""
    block = {}  # type: Dict
    block["enabled"] = enabled
    if generated_types_dirs is not None:
        block["generated_types_dirs"] = list(generated_types_dirs)
    if allowlist_paths is not None:
        block["allowlist_paths"] = list(allowlist_paths)
    return block


def _build_rule_block(
    rule: str,
    enabled: bool,
    generated_types_dirs: Optional[List[str]],
    allowlist_paths: Optional[List[str]],
    layer_graph: Optional[Dict],
    layer_dirs: Optional[Dict],
) -> Dict:
    """Dispatch to the appropriate rule-block builder."""
    if rule == "magic_enum_duplication":
        return _build_magic_enum_block(enabled, generated_types_dirs, allowlist_paths)
    if rule == "cross_layer_imports":
        return _build_cross_layer_block(enabled, layer_graph, layer_dirs, allowlist_paths)
    if rule == "any_with_generated_available":
        return _build_any_leak_block(enabled, generated_types_dirs, allowlist_paths)
    raise ValueError("unknown rule: {rule!r}".format(rule=rule))


# ---------------------------------------------------------------------------
# Atomic JSON write (mirrors _state._write_state)
# ---------------------------------------------------------------------------

def _atomic_write_json(config_path: Path, data: Dict) -> None:
    """Atomically write ``data`` as pretty-printed JSON to ``config_path``.

    Creates parent directories if missing.  Uses mkstemp in the same
    directory so os.replace is atomic on a single filesystem.  Unlinks
    the temp file on any failure before re-raising.
    """
    config_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix="constitute-ff-",
        suffix=".json.tmp",
        dir=str(config_path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=False)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, str(config_path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def set_forcing_function(
    config_path: Path,
    rule: str,
    enabled: bool,
    *,
    generated_types_dirs: Optional[List[str]] = None,
    allowlist_paths: Optional[List[str]] = None,
    layer_graph: Optional[Dict] = None,
    layer_dirs: Optional[Dict] = None,
) -> None:
    """Write or update ``forcing_functions.<rule>`` in ``config_path``.

    Parameters
    ----------
    config_path
        Absolute path to ``.devforge/constitute.json``.  If the file is
        missing, it is created with an empty dict as the base.  The caller
        is responsible for ensuring the parent directory exists (or can be
        created — ``_atomic_write_json`` creates parents automatically).
    rule
        One of ``KNOWN_RULES``.  Unknown rule name raises ``ValueError``.
    enabled
        Whether the rule is active.  When ``True``, required fields are
        validated; when ``False``, required fields (e.g.,
        ``generated_types_dirs``) are not validated at this call (allowing a
        rule to be stored as disabled without configuration); to re-enable
        later, required fields must be supplied again.
    generated_types_dirs
        Paths to generated-type source directories (relative to consumer
        project root).  Required when ``enabled=True`` for
        ``magic_enum_duplication`` and ``any_with_generated_available``.
    allowlist_paths
        Glob patterns for file/dir exemptions.  Optional for all rules.
    layer_graph
        Dict mapping layer name → list of layer names it may import from.
        Required when ``enabled=True`` for ``cross_layer_imports``.
    layer_dirs
        Dict mapping layer name → glob pattern for that layer's source dirs.
        Required when ``enabled=True`` for ``cross_layer_imports``.  Must
        have the same key set as ``layer_graph``.

    Raises
    ------
    ValueError
        Unknown rule name, or a required field is missing/invalid when
        ``enabled=True``.
    OSError
        Config file cannot be read or written.
    json.JSONDecodeError
        Existing config file contains malformed JSON.
    """
    if rule not in KNOWN_RULES:
        raise ValueError(
            "set-forcing-functions: unknown rule {rule!r}; "
            "allowed: {allowed}".format(
                rule=rule,
                allowed=sorted(KNOWN_RULES),
            )
        )

    # Validate per-rule constraints *before* touching the file.
    _validate_rule_block(
        rule, enabled, generated_types_dirs, allowlist_paths, layer_graph, layer_dirs
    )

    # Load existing config (creates empty baseline when file is missing).
    if config_path.exists():
        raw = config_path.read_text(encoding="utf-8")
        data = json.loads(raw)  # propagates JSONDecodeError to caller
        if not isinstance(data, dict):
            raise ValueError(
                "set-forcing-functions: {path}: expected a JSON object at top level".format(
                    path=config_path
                )
            )
    else:
        data = {}

    # Ensure forcing_functions block exists.
    if not isinstance(data.get("forcing_functions"), dict):
        data["forcing_functions"] = {}

    # Build the new rule sub-block, merging with existing values.
    existing_block = data["forcing_functions"].get(rule, {})
    if not isinstance(existing_block, dict):
        existing_block = {}

    new_block = _build_rule_block(
        rule, enabled, generated_types_dirs, allowlist_paths, layer_graph, layer_dirs
    )

    # Merge: existing keys preserved unless the caller supplied a new value.
    # Build order: start from existing, then overwrite with new (caller wins).
    merged = dict(existing_block)
    merged.update(new_block)

    data["forcing_functions"][rule] = merged

    _atomic_write_json(config_path, data)
