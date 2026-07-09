"""write-design-anchor -- persist the design_anchor into the feature dir.

Plan 53 Phase 2 (Persistence + backstop): `/specify` is the gate that
guarantees a design_anchor is persisted to specs/[feature]/design-anchor.json
before /plan -- either the one carried across the research/discover intake
handoff (cmd_import_handoff in _cmds_handoff.py), or -- when intake skipped
capture -- one composed from the /specify-declared design_source (the
backstop, D5/D6).

Two resolution branches, evaluated in this order:
  1. Carried anchor (state["design_anchor"]) non-empty (kind non-empty) ->
     use it as-is.
  2. Carried anchor empty AND state["design_source"] declares a non-"none"
     scheme -> compose {kind, file, selectors: []} from parse_design_source
     (selectors stay empty -- the flat **Design source**: field names only
     the file, not the elements, per the task brief).
  3. Both empty -> persist the empty anchor {kind:"", file:"", selectors:[],
     source_hash:""}. A valid "no design intent" state, never an error.

source_hash (OQ-C resolved: yes) is computed HERE, at /specify persist time
(the D13 re-confirm baseline), NOT carried through the handoff and NOT
recomputed downstream. It is a sha256 hex digest of the anchor `file`'s
bytes when kind == "html" and the file resolves + reads under
--workspace-root; "" otherwise (kind != "html", file absent, or unreadable
-- fail-soft, an honest NOT-COVERED per D13, never an error).

Schema-home decision: design-anchor.json is its OWN artifact shape
{kind, file, selectors, source_hash} -- a plain dict, not a dataclass and
NOT the handoff_schema.DesignAnchor used for the research/discover/specify
SpecSeeds carrier. DesignAnchor is transport-only intent (identical across
3 already-shipped handoff schemas); source_hash is a value derived exactly
once, at exactly one persist site (/specify), and never flows back into
that shared carrier. Keeping it a sibling dict avoids widening 3 already-
tested schema files for a field only one of them would ever populate.

IMMUTABLE (D6): this verb WRITES design-anchor.json; there is no companion
"update" verb. A re-run of /specify (hence a re-run of this verb) overwrites
the file -- idempotent, not additive.

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict

from ._schema import SPECS_ROOT_DEFAULT
from ._state import _atomic_write_json, _load_state
from ._validators import _die


def _resolve_anchor_dict(state: Dict[str, Any]) -> Dict[str, Any]:
    """Return the {kind, file, selectors} anchor to persist.

    Carried (state["design_anchor"]) wins when non-empty (kind non-empty).
    Otherwise composes from state["design_source"] (the backstop) when that
    declares a resolvable non-"none" scheme. Otherwise returns the empty
    anchor. Never raises -- a malformed carried record or design_source
    value degrades to empty, fail-soft.

    Edge case: a carried anchor with kind == "" but a non-empty file/selectors
    is treated as absent (falls through to the backstop, discarding that
    file/selectors) -- the carried-wins gate is `if kind:` alone. This is
    safe because the only upstream producers (_import_handoff_research /
    _import_handoff_discover in _cmds_handoff.py) always set kind and file
    together from one DesignAnchor, so an empty-kind-but-populated-file state
    is not producible by the real pipeline; it is only reachable via
    hand-corrupted state.
    """
    carried = state.get("design_anchor")
    if not isinstance(carried, dict):
        carried = {}
    kind = carried.get("kind") or ""
    file_ = carried.get("file") or ""
    selectors = carried.get("selectors") or []
    if not isinstance(selectors, list):
        selectors = []
    selectors = [s for s in selectors if isinstance(s, str)]

    if kind:
        return {"kind": kind, "file": file_, "selectors": selectors}

    # Backstop (Task C): compose from the /specify design_source declaration.
    design_source_raw = state.get("design_source") or "none"
    # Lazy import: mirrors _research/_cmds_design_anchor.py's convention --
    # avoids a hard cross-subpackage import at module load time. By the time
    # this function runs, specify_helper.py's shim has already inserted
    # src/devforge/lib/ into sys.path, making _design importable as a
    # top-level package sibling.
    from _design._source import parse_design_source

    ds = parse_design_source(design_source_raw)
    if ds.valid and ds.scheme != "none":
        return {"kind": ds.scheme, "file": ds.target, "selectors": []}

    return {"kind": "", "file": "", "selectors": []}


def _compute_source_hash(kind: str, file_: str, workspace_root: str) -> str:
    """Sha256 hex digest of `file_`'s bytes, resolved under workspace_root.

    "" (never an exception) when kind != "html", file_ is empty, the
    resolved path is not a file, or it cannot be read -- fail-soft per D13:
    an unresolvable file is an honest NOT-COVERED signal, not an error.
    """
    if kind != "html" or not file_:
        return ""
    target = Path(workspace_root) / file_
    try:
        if not target.is_file():
            return ""
        data = target.read_bytes()
    except OSError:
        return ""
    return hashlib.sha256(data).hexdigest()


def cmd_write_design_anchor(args: argparse.Namespace) -> int:
    """Persist specs/[feature]/design-anchor.json from the /specify state.

    Read-only on state. Requires spec_number + feature_slug (same
    precondition as finalize-handoff) to compute the target path.

    Args exposed via CLI:
      --devforge-dir    (required, inherited from parent parser)
      --specs-root      (optional; default: "specs")
      --workspace-root  (optional; default: "."; resolves the anchor `file`
                         for the source_hash computation -- design refs live
                         at the install/wrapper root, e.g. design/reference.html,
                         the same convention design_helper's --workspace-root
                         and /breakdown's `test -f design/reference.html` use)
      --emit-path       (optional; overrides the default
                         {specs-root}/{spec_number}-{feature_slug}/design-anchor.json)
    """
    devforge_dir = args.devforge_dir
    specs_root = getattr(args, "specs_root", None) or SPECS_ROOT_DEFAULT
    workspace_root = getattr(args, "workspace_root", None) or "."

    try:
        state = _load_state(devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        return _die("write-design-anchor: cannot load state: {0}".format(err))

    spec_number = state.get("spec_number") or ""
    feature_slug = state.get("feature_slug") or ""
    if not spec_number or not feature_slug:
        return _die(
            "write-design-anchor: spec_number and feature_slug must be set in state"
            " (run assign-spec-number + assign-feature-name first)",
            code=2,
        )

    anchor = _resolve_anchor_dict(state)
    source_hash = _compute_source_hash(anchor["kind"], anchor["file"], workspace_root)
    persisted = {
        "kind": anchor["kind"],
        "file": anchor["file"],
        "selectors": anchor["selectors"],
        "source_hash": source_hash,
    }

    emit_path = getattr(args, "emit_path", None)
    if not emit_path:
        emit_path = "{0}/{1}-{2}/design-anchor.json".format(
            specs_root, spec_number, feature_slug
        )
    target = Path(emit_path)
    if not target.is_absolute():
        target = Path.cwd() / target
    target = target.resolve()

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_json(persisted, target)
    except OSError as err:
        return _die(
            "write-design-anchor: cannot write {0}: {1}".format(target, err)
        )

    sys.stdout.write("wrote: {0}\n".format(target))
    return 0
