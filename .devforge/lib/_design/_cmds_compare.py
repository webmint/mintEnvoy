"""_cmds_compare.py -- the `compare` CLI verb (plan 53 Phase 4/5).

Wires the bag loader (`_bag.py`) + comparator (`_comparator.py`) into a
single design_helper verb so an agent whose tools are limited to Bash +
`evaluate_script` (no direct Python import access -- e.g. `design-auditor`)
can drive the deterministic engine: capture the built/intent bags to
scratch files via `evaluate_script`, then call

    design_helper compare --built-bag <path> [--intent-bag <path>]
                           [--binding <path>] [--route <str>]

--built-bag   required. Path to the built web reader's JSON bag
              (js/built_reader.js's evaluate_script output, written to a
              scratch file by the caller).
--intent-bag  optional. Path to the html intent reader's JSON bag
              (js/intent_reader.js's output). Omit when the feature has no
              captured design anchor -- the fidelity layer is then
              NOT-COVERED but the sanity floor still runs (plan 53 D9).
--binding     optional. Path to the feature's binding JSON
              (specs/[feature]/design-manifest.json). Omit alongside
              --intent-bag; a binding with zero pairs behaves the same as
              an absent binding.
--route       required, non-blank. The built app's route, carried into
              every emitted finding's `file` field.

Emits the ComparisonResult as JSON to stdout (see `_comparator.py`'s
`ComparisonResult.to_dict()` for the exact shape: status / region_found /
not_covered_reason / floor_findings / fidelity_covered / fidelity_findings /
fidelity_not_covered_pairs).

Exit codes:
  0 -- the comparison ran to completion. `status` may be NOT_COVERED,
       CLEAN, or DEFECT -- none of those is a HELPER failure; DEFECT is
       data for the caller (design-auditor, Phase 6) to render into its
       report, not an error this verb signals via exit code.
  2 -- argument error (including a blank --route), missing/unreadable
       file, or malformed bag/binding JSON (a loud, described failure --
       never a silently-empty result).
"""

from __future__ import annotations

import json
import os
import sys

from ._bag import BagParseError, load_bag
from ._comparator import compare
from ._schema import RetiredManifestSchemaError, binding_from_json


def _read_file_or_none(path, flag_label):
    # type: (str, str) -> str
    """Return file contents, or None (after printing to stderr) if absent."""
    if not os.path.isfile(path):
        sys.stderr.write(
            "design_helper compare: {0} not found: {1}\n".format(flag_label, path)
        )
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def cmd_compare(args):
    # type: (object) -> int
    """CLI handler for the `compare` verb. See module docstring for the
    full argument + output contract."""
    built_bag_path = getattr(args, "built_bag", None)
    if not built_bag_path:
        sys.stderr.write("design_helper compare: --built-bag is required\n")
        return 2

    built_text = _read_file_or_none(built_bag_path, "--built-bag")
    if built_text is None:
        return 2
    try:
        built_bag = load_bag(built_text)
    except BagParseError as exc:
        sys.stderr.write("design_helper compare: {0}\n".format(exc))
        return 2

    intent_bag = None
    intent_bag_path = getattr(args, "intent_bag", None)
    if intent_bag_path:
        intent_text = _read_file_or_none(intent_bag_path, "--intent-bag")
        if intent_text is None:
            return 2
        try:
            intent_bag = load_bag(intent_text)
        except BagParseError as exc:
            sys.stderr.write("design_helper compare: {0}\n".format(exc))
            return 2

    binding = None
    binding_path = getattr(args, "binding", None)
    if binding_path:
        binding_text = _read_file_or_none(binding_path, "--binding")
        if binding_text is None:
            return 2
        try:
            binding = binding_from_json(binding_text)
        except (RetiredManifestSchemaError, ValueError) as exc:
            sys.stderr.write(
                "design_helper compare: cannot parse --binding: {0}\n".format(exc)
            )
            return 2

    # FIX F1: --route is required=True in argparse, but a blank string
    # ("") still satisfies `required` -- it reaches here and, when the
    # comparator finds a real defect, DesignFinding.__init__ rejects the
    # blank `file` field with an uncaught ValueError (a data-dependent
    # crash: it only fires when a finding is produced). Reject a blank
    # route explicitly and unconditionally, mirroring the blank/missing
    # checks above for --built-bag/--intent-bag/--binding, so the failure
    # is loud and deterministic regardless of what the comparison would
    # have found.
    route = getattr(args, "route", None) or ""
    if not route.strip():
        sys.stderr.write("design_helper compare: --route must not be blank\n")
        return 2

    # FIX F6: --intent-bag and --binding are only meaningful together (both
    # feed the anchor-gated fidelity layer, see _comparator.compare). Giving
    # one without the other silently degrades to floor-only coverage with no
    # signal to the caller -- surface a non-fatal diagnostic; the floor still
    # runs either way.
    if bool(intent_bag_path) != bool(binding_path):
        if intent_bag_path:
            sys.stderr.write(
                "design_helper compare: note: --intent-bag given without "
                "--binding; fidelity not covered (floor only)\n"
            )
        else:
            sys.stderr.write(
                "design_helper compare: note: --binding given without "
                "--intent-bag; fidelity not covered (floor only)\n"
            )

    result = compare(built_bag, intent_bag, binding, route)
    sys.stdout.write(json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n")
    return 0
