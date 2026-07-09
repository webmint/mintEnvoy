"""Design-anchor capture command handler for discover_helper (plan 53 Phase 1).

One setter: set-scope-design-anchor -- named to match the "set-scope-<dim>"
convention of the 8 rubric-dimension setters (_cmds_scope.py), even though
design_anchor is NOT one of RUBRIC_DIMENSIONS (see below).

Captures design intent {kind, file, selectors} into discover-scope.json
(memo.design_anchor) for finalize-handoff to emit into
SpecSeeds.design_anchor.

Reuses parse_design_source (_design/_source.py) to parse --value's
"scheme:target" shape into kind + file -- scheme parsing is NOT
re-implemented here (helper-owns-shape, single source of truth).
--selectors is a JSON array of intent selectors (may be empty).

Note the layering: DesignAnchor.kind is an OPEN discriminator at the schema
layer (any string deserializes cleanly; an unrecognized kind resolves to
NOT-COVERED downstream, never a schema error) -- but THIS setter is
narrower, since it reuses parse_design_source's scheme validation against
_KNOWN_SCHEMES (html/figma/screenshot/none). Capturing a new kind requires
extending _KNOWN_SCHEMES in _design/_source.py, kept in lockstep with
DESIGN_SOURCE_SCHEME_ENUM in _specify/_schema.py (the plan 43 "**Design
source**:" frontmatter SYNC pair).

design_anchor is OPTIONAL (an empty/unset anchor is the valid default, plan
53 D3/D5) -- unlike the 8 RUBRIC_DIMENSIONS, it does NOT participate in
scope-coverage / scope-finalize gating. --state mirrors the sibling rubric
setters' CLI shape for consistency but carries no gating semantics here.
"""

from __future__ import annotations

import argparse
import json

from ._state import _empty_design_anchor_record, _state_transaction
from ._validators import _die


def cmd_set_scope_design_anchor(args: argparse.Namespace) -> int:
    """Parse --value via parse_design_source + --selectors JSON array; persist.

    --value must be a valid `scheme:target` (or the bare literal "none") per
    parse_design_source's rules; an invalid value (unknown scheme, empty
    target, malformed 'none:' form) exits 2 with NO persistence.
    --selectors must decode to a JSON array of strings (possibly empty `[]`);
    malformed JSON, a non-list decode, or a non-string element exits 2 with
    NO persistence.
    A bare "none" --value clears the anchor to kind="" file="" (matching the
    handoff_schema.DesignAnchor empty default) -- "none" is a sentinel, not a
    kind name.
    """
    # Lazy import: avoids a hard cross-subpackage import at module load time
    # (mirrors breakdown_helper.py's `from _design._schema import ...`
    # function-local pattern for the same _design sibling package).
    from _design._source import parse_design_source

    ds = parse_design_source(args.value)
    if not ds.valid:
        return _die(
            "set-scope-design-anchor: malformed --value {0!r}; expected "
            "'<scheme>:<target>' (scheme one of html|figma|screenshot) or "
            "the literal 'none'".format(args.value),
            code=2,
        )

    try:
        decoded = json.loads(args.selectors)
    except ValueError as err:
        return _die(
            "set-scope-design-anchor: --selectors is not valid JSON: {0}".format(err),
            code=2,
        )
    if not isinstance(decoded, list):
        return _die(
            "set-scope-design-anchor: --selectors must decode to a JSON array, "
            "got {0}".format(type(decoded).__name__),
            code=2,
        )
    selectors = []
    for item in decoded:
        if not isinstance(item, str):
            return _die(
                "set-scope-design-anchor: --selectors items must be strings, "
                "got {0}".format(type(item).__name__),
                code=2,
            )
        selectors.append(item)

    # "none" is a bare sentinel (no scheme/target) -- clear kind + file.
    kind = "" if ds.scheme == "none" else ds.scheme
    file_ = "" if ds.scheme == "none" else ds.target

    try:
        with _state_transaction(args.devforge_dir, "memo") as memo:
            rec = memo.get("design_anchor")
            if not isinstance(rec, dict):
                rec = _empty_design_anchor_record()
            rec["value"] = {"kind": kind, "file": file_, "selectors": selectors}
            rec["state"] = args.state
            memo["design_anchor"] = rec
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-scope-design-anchor: {0}".format(err))
    return 0
