"""argparse parser + dispatch + main entry for design_helper.

build_parser composes the top-level + subparsers.
_register_subcommands attaches each cmd_* handler via set_defaults(func=...).
main parses argv + dispatches (prints help + returns 2 when no subcommand).

Phase 2 verbs (this file):
  resolve-reference       — parse reference.html: element list + resolved values
                            + gap-list of unresolvable classes/tokens
  init-manifest           — produce a skeleton manifest (all unclassified) from
                            resolve-reference output
  validate-manifest       — validate a manifest: unclassified element → exit 1
                            naming the element; non-empty gap-list → exit 1
                            naming each token; fully-classified + empty gap-list → exit 0
  extract-spacing-scale   — extract spacing scale from design/styles.css;
                            relaxes (available=false) when CSS is absent (OQ-6)

Extension point: append to _SUBCOMMAND_REGISTRY and add the argument block in
_register_subcommands's elif chain.
"""

from __future__ import annotations

import argparse
import sys

from ._reference import cmd_resolve_reference
from ._manifest import (
    cmd_init_manifest,
    cmd_validate_manifest,
    cmd_extract_spacing_scale,
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_SUBCOMMAND_REGISTRY = [
    (
        "resolve-reference",
        (
            "Parse reference.html: returns element list (data-ref anchors, tags, "
            "classes, inline styles) + declared CSS values from <style> blocks "
            "and linked stylesheets resolvable on disk + gap-list of unresolvable "
            "classes/tokens (classes with no CSS definition, undefined --custom-props). "
            "Emits JSON to stdout. (Phase 2)."
        ),
        cmd_resolve_reference,
    ),
    (
        "init-manifest",
        (
            "Read a resolve-reference JSON output (--reference-json) and produce "
            "a skeleton disposition manifest JSON to stdout with every element set "
            "to disposition='' (unclassified). The orchestrator fills in dispositions "
            "before running validate-manifest. (Phase 2)."
        ),
        cmd_init_manifest,
    ),
    (
        "validate-manifest",
        (
            "Read a manifest JSON (--manifest-path) and validate it. "
            "Unclassified element → exit 1 naming the element. "
            "Non-empty gap-list → exit 1 naming each unresolvable token. "
            "Fully-classified manifest + empty gap-list → exit 0. "
            "Emits {valid, errors} JSON to stdout. (Phase 2)."
        ),
        cmd_validate_manifest,
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
            "Helper for the design-fidelity forcing function (plan 40 Phase 2). "
            "Produces and validates a per-element disposition manifest from a "
            "reference.html (+ optional design/styles.css). "
            "Verbs: resolve-reference, init-manifest, validate-manifest, "
            "extract-spacing-scale."
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

        if verb == "resolve-reference":
            sp.add_argument(
                "--html-path",
                required=True,
                dest="html_path",
                metavar="PATH",
                help=(
                    "Path to the reference.html file to parse. "
                    "Linked stylesheets are resolved relative to this file's directory."
                ),
            )

        elif verb == "init-manifest":
            sp.add_argument(
                "--reference-json",
                required=True,
                dest="reference_json",
                metavar="PATH",
                help=(
                    "Path to a JSON file produced by the resolve-reference verb. "
                    "The skeleton manifest is written to stdout."
                ),
            )

        elif verb == "validate-manifest":
            sp.add_argument(
                "--manifest-path",
                required=True,
                dest="manifest_path",
                metavar="PATH",
                help=(
                    "Path to the disposition manifest JSON to validate. "
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
