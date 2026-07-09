"""argparse parser + dispatch + main entry for design_helper.

build_parser composes the top-level + subparsers.
_register_subcommands attaches each cmd_* handler via set_defaults(func=...).
main parses argv + dispatches (prints help + returns 2 when no subcommand).

Verbs (this file):
  validate-binding        — validate a binding JSON (specs/[feature]/
                            design-manifest.json): route + >=1 fully-
                            specified pair required; empty/invalid binding
                            -> exit 1 naming the gap. (plan 53 Phase 3)
  extract-spacing-scale   — extract spacing scale from design/styles.css;
                            relaxes (available=false) when CSS is absent (OQ-6)
  check-design-source     — warn (non-blocking) when a non-file design
                            source is declared but no enforceable
                            design/reference.html exists (plan 43)
  compare                 — run the deterministic intent-reader x
                            built-reader x comparator engine over a built
                            bag (+ optional intent bag + binding); emits a
                            {status, ...} ComparisonResult JSON distinguishing
                            NOT_COVERED / CLEAN / DEFECT (plan 53 Phase 4/5)

RETIRED (plan 53 Phase 3): resolve-reference and init-manifest.  The data-ref
HTML-anchor extraction (resolve-reference) and its skeleton-manifest
generator (init-manifest) fed the retired disposition-manifest schema; the
binding schema's route + pairs are always human/LLM authored directly, so
neither verb has a mechanical replacement.

Extension point: append to _SUBCOMMAND_REGISTRY and add the argument block in
_register_subcommands's elif chain.
"""

from __future__ import annotations

import argparse
import sys

from ._manifest import (
    cmd_validate_binding,
    cmd_extract_spacing_scale,
)
from ._source import cmd_check_design_source
from ._cmds_compare import cmd_compare


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_SUBCOMMAND_REGISTRY = [
    (
        "validate-binding",
        (
            "Read a binding JSON (--binding-path) and validate it. "
            "Missing/empty route -> exit 1 naming 'route'. "
            "Zero pairs -> exit 1. A pair missing anchor_selector or "
            "built_testid -> exit 1 naming the pair index and field. "
            "Valid binding (route + >=1 fully-specified pair) -> exit 0. "
            "Emits {valid, errors} JSON to stdout. (plan 53 Phase 3)."
        ),
        cmd_validate_binding,
    ),
    (
        "extract-spacing-scale",
        (
            "Parse design/styles.css (--css-path) and extract distinct spacing "
            "values (margin/padding/gap/inset). Returns {available, scale, source}. "
            "When CSS is absent, returns available=false (OQ-6 relaxation: the "
            "spacing provenance check relaxes when no CSS is present). "
            "Emits JSON to stdout. (Phase 2)."
        ),
        cmd_extract_spacing_scale,
    ),
    (
        "check-design-source",
        (
            "Read the **Design source**: frontmatter line from a spec.md "
            "(--spec) and emit a NON-BLOCKING WARN to stderr (exit 0) when a "
            "non-file design source (figma/screenshot) is declared but no "
            "enforceable design/reference.html exists in the workspace root "
            "(--workspace-root, default '.').  Also warns on malformed values. "
            "Silent on 'none', on valid html: sources, and when a reference.html "
            "is already present alongside a figma/screenshot source.  "
            "Always exits 0 (non-blocking). (plan 43 Step 1A)."
        ),
        cmd_check_design_source,
    ),
    (
        "compare",
        (
            "Run the deterministic intent-reader x built-reader x "
            "comparator engine. Reads a built bag (--built-bag, required), "
            "an optional intent bag (--intent-bag), and an optional "
            "binding (--binding), and emits a JSON ComparisonResult "
            "distinguishing NOT_COVERED (built region not found) / CLEAN "
            "(region found, zero findings) / DEFECT (real findings). "
            "The always-on anchor-free sanity floor (overflow/clip/"
            "font-not-loaded) runs whenever the region is found, with or "
            "without an intent bag; anchor-gated value + geometry fidelity "
            "runs only when both --intent-bag and --binding are given. "
            "(plan 53 Phase 4/5)."
        ),
        cmd_compare,
    ),
]


# ---------------------------------------------------------------------------
# Parser construction
# ---------------------------------------------------------------------------


def build_parser():
    # type: () -> argparse.ArgumentParser
    """Build and return the top-level ArgumentParser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="design_helper",
        description=(
            "Helper for the design-anchor + binding apparatus (plan 53). "
            "Validates a per-feature built-side binding (route + anchor-selector/"
            "built-testid pairs) against specs/[feature]/design-manifest.json, "
            "and runs the deterministic design-fidelity comparator over "
            "measurement bags captured by the js/built_reader.js + "
            "js/intent_reader.js evaluate_script collectors. "
            "Verbs: validate-binding, extract-spacing-scale, check-design-source, "
            "compare."
        ),
    )
    subparsers = parser.add_subparsers(dest="subcommand")
    _register_subcommands(subparsers)
    return parser


def _register_subcommands(subparsers):
    # type: (argparse._SubParsersAction) -> None
    """Attach all handlers from _SUBCOMMAND_REGISTRY."""
    for verb, help_text, handler in _SUBCOMMAND_REGISTRY:
        sp = subparsers.add_parser(verb, help=help_text)

        if verb == "validate-binding":
            sp.add_argument(
                "--binding-path",
                required=True,
                dest="binding_path",
                metavar="PATH",
                help=(
                    "Path to the binding JSON to validate "
                    "(specs/[feature]/design-manifest.json). "
                    "Emits {valid, errors} JSON to stdout; "
                    "exit 0 = valid, exit 1 = validation errors."
                ),
            )

        elif verb == "extract-spacing-scale":
            sp.add_argument(
                "--css-path",
                required=True,
                dest="css_path",
                metavar="PATH",
                help=(
                    "Path to design/styles.css. When the file does not exist, "
                    "exits 0 with available=false (OQ-6 relaxation). "
                    "Emits {available, scale, source} JSON to stdout."
                ),
            )

        elif verb == "check-design-source":
            sp.add_argument(
                "--spec",
                required=True,
                dest="spec",
                metavar="PATH",
                help=(
                    "Path to the spec.md file to inspect for a **Design source**: "
                    "frontmatter line.  Unreadable or absent spec → silent exit 0."
                ),
            )
            sp.add_argument(
                "--workspace-root",
                required=False,
                default=".",
                dest="workspace_root",
                metavar="DIR",
                help=(
                    "Workspace root directory used to resolve design/reference.html. "
                    "Defaults to '.' (current directory)."
                ),
            )

        elif verb == "compare":
            sp.add_argument(
                "--built-bag",
                required=True,
                dest="built_bag",
                metavar="PATH",
                help=(
                    "Path to the built web reader's JSON bag "
                    "(js/built_reader.js's evaluate_script output, saved "
                    "to a scratch file by the caller). Required."
                ),
            )
            sp.add_argument(
                "--intent-bag",
                required=False,
                default=None,
                dest="intent_bag",
                metavar="PATH",
                help=(
                    "Path to the html intent reader's JSON bag "
                    "(js/intent_reader.js's output). Omit when the "
                    "feature has no captured design anchor -- the "
                    "fidelity layer is then NOT-COVERED but the sanity "
                    "floor still runs."
                ),
            )
            sp.add_argument(
                "--binding",
                required=False,
                default=None,
                dest="binding",
                metavar="PATH",
                help=(
                    "Path to the feature's binding JSON "
                    "(specs/[feature]/design-manifest.json). Omit "
                    "alongside --intent-bag."
                ),
            )
            sp.add_argument(
                "--route",
                required=True,
                dest="route",
                metavar="ROUTE",
                help=(
                    "The built app's route, carried into every emitted "
                    "finding's 'file' field. Required -- a route-absent "
                    "run is NOT-COVERED per plan 53 honesty invariant #2 "
                    "and must never reach this verb (the caller decides "
                    "that upstream, before invoking evaluate_script)."
                ),
            )

        sp.set_defaults(func=handler)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv=None):
    # type: (list) -> int
    """Parse argv and dispatch to the selected subcommand handler.

    Returns the handler's exit code (0 = success, non-zero = error).
    When no subcommand is given, prints help and returns 2.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help(sys.stderr)
        return 2

    return args.func(args)
