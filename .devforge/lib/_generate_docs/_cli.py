"""argparse wiring + dispatch for the generate_docs helper.

This module is the Controller (per GRASP): a single entry point
(`main`) parses the CLI, looks up the handler in a registry, and
calls it. Subcommands are appended to `_SUBCOMMANDS` — adding a new
one means writing a parser-factory + handler in the appropriate
sibling module (`_setters` / `_setters_concern` for state mutation,
`_setters_concern_files` for filesystem skeleton emission per source
file, `_status` for read-only state inspection, `_manifest` for
ecosystem manifest extraction, `_render` for skeleton emission,
`_validators_file_doc` for per-file-doc validation + post-batch
aggregation, `_validators` shim for the full validator surface) and
adding one tuple here. The dispatch path stays closed against
modification (OCP).

The `_add_cite_args` factory is shared by eight subcommands — four
package-tier (`add-package-export`, `add-package-hazard`,
`set-package-usage-example`, `set-package-consumer-pattern`), three
concern-tier (`add-concern-export`, `add-concern-type`,
`add-concern-hazard`, `set-concern-usage-example`), and the file-doc
writer (`write-file-doc`) — all of which accept the
`--cite-file / --cite-start / --cite-end` triple.

Stdlib only. Targets Python 3.8+.
"""

import argparse
import sys
import time
from typing import Callable, List, Optional, Tuple

from . import _circuit, _trace
from ._concern_input import _build_concern_input, cmd_concern_input
from ._doc_setters import (
    _build_init_doc,
    _build_render_doc,
    _build_set_doc_concerns,
    _build_set_doc_cross_cuts,
    _build_set_doc_files,
    _build_set_doc_layers,
    _build_set_doc_packages,
    _build_set_doc_patterns,
    _build_set_doc_purpose,
    _build_set_doc_structure,
    _build_set_doc_subconcerns,
    _build_set_architecture_conventions,
    _build_set_architecture_cross_cuts_detailed,
    _build_set_architecture_dependency_direction_rules,
    _build_set_architecture_dependency_overview_mermaid,
    _build_set_architecture_module_structure,
    _build_set_architecture_overview_narrative,
    _build_set_architecture_patterns,
    _build_set_overview_application_routes,
    _build_set_overview_cross_module_deps,
    _build_set_overview_entry_points,
    _build_set_overview_key_commands,
    _build_set_overview_module_map,
    _build_set_overview_navigation_guards,
    _build_set_overview_project_structure_annotations,
    _build_set_overview_project_structure_tree,
    _build_set_overview_tech_stack,
    _build_set_overview_test_files,
    cmd_init_doc,
    cmd_render_doc,
    cmd_set_architecture_conventions,
    cmd_set_architecture_cross_cuts_detailed,
    cmd_set_architecture_dependency_direction_rules,
    cmd_set_architecture_dependency_overview_mermaid,
    cmd_set_architecture_module_structure,
    cmd_set_architecture_overview_narrative,
    cmd_set_architecture_patterns,
    cmd_set_doc_concerns,
    cmd_set_doc_cross_cuts,
    cmd_set_doc_files,
    cmd_set_doc_layers,
    cmd_set_doc_packages,
    cmd_set_doc_patterns,
    cmd_set_doc_purpose,
    cmd_set_doc_structure,
    cmd_set_doc_subconcerns,
    cmd_set_overview_application_routes,
    cmd_set_overview_cross_module_deps,
    cmd_set_overview_entry_points,
    cmd_set_overview_key_commands,
    cmd_set_overview_module_map,
    cmd_set_overview_navigation_guards,
    cmd_set_overview_project_structure_annotations,
    cmd_set_overview_project_structure_tree,
    cmd_set_overview_tech_stack,
    cmd_set_overview_test_files,
)
from ._manifest import cmd_extract_package_scripts
from ._package_input import _build_package_input, cmd_package_input
from ._preflight import _build_preflight, cmd_preflight
from ._project_input import _build_project_input, cmd_project_input
from ._validate_doc import _build_validate_doc, cmd_validate_doc
from ._verify_all import _build_verify_all, cmd_verify_all
from ._glossary import (
    _build_build_glossary_bundles,
    cmd_build_glossary_bundles,
    _build_set_glossary_entries,
    cmd_set_glossary_entries,
)
from ._render import (
    cmd_render_concern_skeleton,
    cmd_render_package_skeleton,
)
from ._snippet import cmd_extract_snippet
from ._setters import (
    cmd_add_package,
    cmd_add_package_dep,
    cmd_add_package_export,
    cmd_add_package_hazard,
    cmd_add_package_script,
    cmd_reset,
    cmd_set_package_build_tool,
    cmd_set_package_consumer_pattern,
    cmd_set_package_framework,
    cmd_set_package_language,
    cmd_set_package_overview,
    cmd_set_package_tree,
    cmd_set_package_usage_example,
)
from ._setters_concern import (
    cmd_add_concern,
    cmd_add_concern_dep,
    cmd_add_concern_export,
    cmd_add_concern_hazard,
    cmd_add_concern_type,
    cmd_set_concern_overview,
    cmd_set_concern_tree,
    cmd_set_concern_usage_example,
)
from ._setters_concern_files import cmd_render_file_skeletons, cmd_write_file_doc
from ._status import cmd_status
from ._validators import (
    cmd_render_concern_doc,
    cmd_render_package_doc,
    cmd_validate_concern,
    cmd_validate_file_doc,
    cmd_validate_package,
    cmd_verify_file_docs,
)


# Each parser-factory takes the subparsers' `add_parser`-returned
# `argparse.ArgumentParser` and adds its own `--*` arguments to it.
# It returns nothing (the parser is mutated in place).
_ParserFactory = Callable[[argparse.ArgumentParser], None]
_Handler = Callable[[argparse.Namespace], int]


def _add_cite_args(parser: argparse.ArgumentParser, optional: bool) -> None:
    """Add the `--cite-file / --cite-start / --cite-end` triple.

    `optional=True` makes all three arguments default to None (used by
    `add-package-hazard`, where the cite is itself optional). Required
    sites pass `optional=False` so argparse rejects missing values.
    """
    if optional:
        parser.add_argument("--cite-file", default=None)
        parser.add_argument("--cite-start", default=None, type=int)
        parser.add_argument("--cite-end", default=None, type=int)
    else:
        parser.add_argument("--cite-file", required=True)
        parser.add_argument("--cite-start", required=True, type=int)
        parser.add_argument("--cite-end", required=True, type=int)


# ---------------------------------------------------------------------------
# Per-subcommand parser factories.
# ---------------------------------------------------------------------------


def _build_reset(p: argparse.ArgumentParser) -> None:
    pass


def _build_add_package(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)
    p.add_argument("--name", required=True)


def _build_set_package_overview(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)
    p.add_argument("--text", required=True)


def _build_set_package_tree(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)
    p.add_argument("--text", required=True)


def _build_set_package_language(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)
    p.add_argument("--value", required=True)


def _build_set_package_framework(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)
    p.add_argument("--value", required=True)


def _build_set_package_build_tool(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)
    p.add_argument("--value", required=True)


def _build_add_package_script(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)
    p.add_argument("--script-name", required=True)
    p.add_argument("--command", required=True)


def _build_add_package_export(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--kind", required=True)
    p.add_argument("--signature", default="")
    p.add_argument("--description", required=True)
    p.add_argument("--language", required=True)
    p.add_argument("--code-snippet", required=True)
    _add_cite_args(p, optional=False)


def _build_add_package_dep(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--kind", required=True)
    p.add_argument("--version", default="")
    p.add_argument("--purpose", required=True)
    p.add_argument("--consumer-location", action="append", default=None)


def _build_add_package_hazard(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)
    p.add_argument("--category", required=True)
    p.add_argument("--description", required=True)
    _add_cite_args(p, optional=True)


def _build_set_package_usage_example(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)
    p.add_argument("--language", required=True)
    p.add_argument("--code-snippet", required=True)
    _add_cite_args(p, optional=False)


def _build_set_package_consumer_pattern(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)
    p.add_argument("--language", required=True)
    p.add_argument("--code-snippet", required=True)
    _add_cite_args(p, optional=False)


def _build_status(p: argparse.ArgumentParser) -> None:
    pass


def _build_extract_package_scripts(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)


def _build_extract_snippet(p: argparse.ArgumentParser) -> None:
    p.add_argument("--file", required=True)
    p.add_argument("--start", required=True, type=int)
    p.add_argument("--end", required=True, type=int)


def _build_render_package_skeleton(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)


def _build_validate_package(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)


def _build_render_package_doc(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True)


# ---------------------------------------------------------------------------
# Concern-tier parser factories (Phase 3.1).
#
# All concern subcommands take `--package` (the path of the parent
# package) and `--concern` (the concern_name). The two-key form
# distinguishes concerns from package-tier subcommands which use
# `--path`. A concern is uniquely identified by the `(package, concern)`
# pair across the state file.
# ---------------------------------------------------------------------------


def _build_add_concern(p: argparse.ArgumentParser) -> None:
    p.add_argument("--package", required=True)
    p.add_argument("--concern", required=True)


def _build_set_concern_overview(p: argparse.ArgumentParser) -> None:
    p.add_argument("--package", required=True)
    p.add_argument("--concern", required=True)
    p.add_argument("--text", required=True)


def _build_set_concern_tree(p: argparse.ArgumentParser) -> None:
    p.add_argument("--package", required=True)
    p.add_argument("--concern", required=True)
    p.add_argument("--text", required=True)


def _build_add_concern_export(p: argparse.ArgumentParser) -> None:
    p.add_argument("--package", required=True)
    p.add_argument("--concern", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--kind", required=True)
    p.add_argument("--signature", default="")
    p.add_argument("--description", required=True)
    p.add_argument("--language", required=True)
    p.add_argument("--code-snippet", required=True)
    _add_cite_args(p, optional=False)


def _build_add_concern_type(p: argparse.ArgumentParser) -> None:
    p.add_argument("--package", required=True)
    p.add_argument("--concern", required=True)
    p.add_argument("--language", required=True)
    p.add_argument("--code-snippet", required=True)
    _add_cite_args(p, optional=False)


def _build_add_concern_dep(p: argparse.ArgumentParser) -> None:
    p.add_argument("--package", required=True)
    p.add_argument("--concern", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--kind", required=True)
    p.add_argument("--version", default="")
    p.add_argument("--purpose", required=True)
    p.add_argument("--consumer-location", action="append", default=None)


def _build_add_concern_hazard(p: argparse.ArgumentParser) -> None:
    p.add_argument("--package", required=True)
    p.add_argument("--concern", required=True)
    p.add_argument("--category", required=True)
    p.add_argument("--description", required=True)
    _add_cite_args(p, optional=True)


def _build_set_concern_usage_example(p: argparse.ArgumentParser) -> None:
    p.add_argument("--package", required=True)
    p.add_argument("--concern", required=True)
    p.add_argument("--language", required=True)
    p.add_argument("--code-snippet", required=True)
    _add_cite_args(p, optional=False)


def _build_render_concern_skeleton(p: argparse.ArgumentParser) -> None:
    p.add_argument("--package", required=True)
    p.add_argument("--concern", required=True)


def _build_validate_concern(p: argparse.ArgumentParser) -> None:
    p.add_argument("--package", required=True)
    p.add_argument("--concern", required=True)


def _build_render_concern_doc(p: argparse.ArgumentParser) -> None:
    p.add_argument("--package", required=True)
    p.add_argument("--concern", required=True)


def _build_render_file_skeletons(p: argparse.ArgumentParser) -> None:
    p.add_argument("--package", required=True)
    p.add_argument("--concern", required=True)


# Per-file-doc subcommands (Step B.3 of VALIDATOR-LOOP-B-PLAN.md).


def _build_write_file_doc(p: argparse.ArgumentParser) -> None:
    p.add_argument("--md-path", required=True)
    p.add_argument("--label", required=True)
    p.add_argument("--confidence", required=True)
    _add_cite_args(p, optional=False)
    p.add_argument("--model-version", required=True)


def _build_validate_file_doc(p: argparse.ArgumentParser) -> None:
    p.add_argument("--md-path", required=True)


def _build_verify_file_docs(p: argparse.ArgumentParser) -> None:
    p.add_argument("--package", required=True)
    p.add_argument("--concern", required=True)


# ---------------------------------------------------------------------------
# Subcommand registry. Append to extend.
# ---------------------------------------------------------------------------


_SUBCOMMANDS: Tuple[Tuple[str, _ParserFactory, _Handler], ...] = (
    ("reset", _build_reset, cmd_reset),
    ("add-package", _build_add_package, cmd_add_package),
    ("set-package-overview", _build_set_package_overview, cmd_set_package_overview),
    ("set-package-tree", _build_set_package_tree, cmd_set_package_tree),
    ("set-package-language", _build_set_package_language, cmd_set_package_language),
    ("set-package-framework", _build_set_package_framework, cmd_set_package_framework),
    ("set-package-build-tool", _build_set_package_build_tool, cmd_set_package_build_tool),
    ("add-package-script", _build_add_package_script, cmd_add_package_script),
    ("add-package-export", _build_add_package_export, cmd_add_package_export),
    ("add-package-dep", _build_add_package_dep, cmd_add_package_dep),
    ("add-package-hazard", _build_add_package_hazard, cmd_add_package_hazard),
    ("set-package-usage-example", _build_set_package_usage_example, cmd_set_package_usage_example),
    ("set-package-consumer-pattern", _build_set_package_consumer_pattern, cmd_set_package_consumer_pattern),
    ("status", _build_status, cmd_status),
    ("extract-package-scripts", _build_extract_package_scripts, cmd_extract_package_scripts),
    ("extract-snippet", _build_extract_snippet, cmd_extract_snippet),
    ("render-package-skeleton", _build_render_package_skeleton, cmd_render_package_skeleton),
    ("validate-package", _build_validate_package, cmd_validate_package),
    ("render-package-doc", _build_render_package_doc, cmd_render_package_doc),
    # Concern-tier subcommands (Phase 3.1).
    ("add-concern", _build_add_concern, cmd_add_concern),
    ("set-concern-overview", _build_set_concern_overview, cmd_set_concern_overview),
    ("set-concern-tree", _build_set_concern_tree, cmd_set_concern_tree),
    ("add-concern-export", _build_add_concern_export, cmd_add_concern_export),
    ("add-concern-type", _build_add_concern_type, cmd_add_concern_type),
    ("add-concern-dep", _build_add_concern_dep, cmd_add_concern_dep),
    ("add-concern-hazard", _build_add_concern_hazard, cmd_add_concern_hazard),
    ("set-concern-usage-example", _build_set_concern_usage_example, cmd_set_concern_usage_example),
    ("render-concern-skeleton", _build_render_concern_skeleton, cmd_render_concern_skeleton),
    ("validate-concern", _build_validate_concern, cmd_validate_concern),
    ("render-concern-doc", _build_render_concern_doc, cmd_render_concern_doc),
    ("render-file-skeletons", _build_render_file_skeletons, cmd_render_file_skeletons),  # B.1
    # Per-file-doc subcommands (Step B.3 of VALIDATOR-LOOP-B-PLAN.md).
    ("write-file-doc", _build_write_file_doc, cmd_write_file_doc),
    ("validate-file-doc", _build_validate_file_doc, cmd_validate_file_doc),
    # Per-file-doc post-batch aggregator (Step B.4 of VALIDATOR-LOOP-B-PLAN.md).
    ("verify-file-docs", _build_verify_file_docs, cmd_verify_file_docs),
    # concern-input helper — feeds batch JSON to the orchestrator's compose step.
    ("concern-input", _build_concern_input, cmd_concern_input),
    # Plan F.7 — package-input helper for package-tier dispatch.
    ("package-input", _build_package_input, cmd_package_input),
    # Plan F.8 — project-input helper for project-tier dispatch.
    ("project-input", _build_project_input, cmd_project_input),
    # Plan F.0 — preflight (vue-extract + index_repository + stamp diff).
    ("preflight", _build_preflight, cmd_preflight),
    # Plan F.5 — validate-doc (concern tier; v0).
    ("validate-doc", _build_validate_doc, cmd_validate_doc),
    # Phase 5 aggregator gate — walks state JSON, runs validate-doc per path.
    ("verify-all", _build_verify_all, cmd_verify_all),
    # Plan F.4 — concern-tier setter primitives + render-doc (v0).
    # F.7b — package-tier setters (set-doc-concerns / -layers / -patterns).
    # Hazards dropped: /audit owns hazard discovery; concern docs ship Purpose + Structure only.
    ("init-doc", _build_init_doc, cmd_init_doc),
    ("set-doc-purpose", _build_set_doc_purpose, cmd_set_doc_purpose),
    ("set-doc-structure", _build_set_doc_structure, cmd_set_doc_structure),
    ("set-doc-concerns", _build_set_doc_concerns, cmd_set_doc_concerns),
    ("set-doc-files", _build_set_doc_files, cmd_set_doc_files),
    ("set-doc-layers", _build_set_doc_layers, cmd_set_doc_layers),
    ("set-doc-patterns", _build_set_doc_patterns, cmd_set_doc_patterns),
    ("set-doc-packages", _build_set_doc_packages, cmd_set_doc_packages),
    ("set-doc-cross-cuts", _build_set_doc_cross_cuts, cmd_set_doc_cross_cuts),
    # Plan F 3a — split-aware concern setter (parent's `## Sub-concerns`).
    ("set-doc-subconcerns", _build_set_doc_subconcerns, cmd_set_doc_subconcerns),
    # Track 4 Phase 1 — project-overview mechanical setters (Tech Stack,
    # Project Structure, Key Commands, Cross-Module Dependencies, Test Files).
    ("set-overview-tech-stack", _build_set_overview_tech_stack, cmd_set_overview_tech_stack),
    ("set-overview-key-commands", _build_set_overview_key_commands, cmd_set_overview_key_commands),
    ("set-overview-test-files", _build_set_overview_test_files, cmd_set_overview_test_files),
    (
        "set-overview-cross-module-deps",
        _build_set_overview_cross_module_deps,
        cmd_set_overview_cross_module_deps,
    ),
    (
        "set-overview-project-structure-tree",
        _build_set_overview_project_structure_tree,
        cmd_set_overview_project_structure_tree,
    ),
    # Track 4 Phase 2 — mixed mechanical+LLM project-overview setters
    # (Entry Points / Application Routes / Navigation Guards / Module Map /
    # Project Structure dir-level annotations).
    (
        "set-overview-entry-points",
        _build_set_overview_entry_points,
        cmd_set_overview_entry_points,
    ),
    (
        "set-overview-application-routes",
        _build_set_overview_application_routes,
        cmd_set_overview_application_routes,
    ),
    (
        "set-overview-navigation-guards",
        _build_set_overview_navigation_guards,
        cmd_set_overview_navigation_guards,
    ),
    (
        "set-overview-module-map",
        _build_set_overview_module_map,
        cmd_set_overview_module_map,
    ),
    (
        "set-overview-project-structure-annotations",
        _build_set_overview_project_structure_annotations,
        cmd_set_overview_project_structure_annotations,
    ),
    # Track 4 Phase 3 — architecture-tier setters (Architecture Overview,
    # Module/Package Structure, Patterns, Conventions, enriched Cross-Cuts,
    # Dependency Direction Rules, Dependency Overview mermaid).
    (
        "set-architecture-overview-narrative",
        _build_set_architecture_overview_narrative,
        cmd_set_architecture_overview_narrative,
    ),
    (
        "set-architecture-module-structure",
        _build_set_architecture_module_structure,
        cmd_set_architecture_module_structure,
    ),
    (
        "set-architecture-patterns",
        _build_set_architecture_patterns,
        cmd_set_architecture_patterns,
    ),
    (
        "set-architecture-conventions",
        _build_set_architecture_conventions,
        cmd_set_architecture_conventions,
    ),
    (
        "set-architecture-cross-cuts-detailed",
        _build_set_architecture_cross_cuts_detailed,
        cmd_set_architecture_cross_cuts_detailed,
    ),
    (
        "set-architecture-dependency-direction-rules",
        _build_set_architecture_dependency_direction_rules,
        cmd_set_architecture_dependency_direction_rules,
    ),
    (
        "set-architecture-dependency-overview-mermaid",
        _build_set_architecture_dependency_overview_mermaid,
        cmd_set_architecture_dependency_overview_mermaid,
    ),
    ("render-doc", _build_render_doc, cmd_render_doc),
    # Track B.1 — glossary helper (build-glossary-bundles + set-glossary-entries).
    (
        "build-glossary-bundles",
        _build_build_glossary_bundles,
        cmd_build_glossary_bundles,
    ),
    (
        "set-glossary-entries",
        _build_set_glossary_entries,
        cmd_set_glossary_entries,
    ),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="generate_docs_helper",
        description="State + setters for /generate-docs (PackageDoc tier).",
    )
    sub = parser.add_subparsers(dest="subcommand")
    for name, factory, handler in _SUBCOMMANDS:
        p = sub.add_parser(name)
        factory(p)
        p.set_defaults(func=handler)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Parse CLI args, dispatch to handler, emit trace line, return exit code.

    Trace logging policy: every invocation appends one line to
    `<DEVFORGE_DIR>/.generate-docs-trace.log` regardless of whether
    the handler succeeded, returned a non-zero exit code, or raised
    an unexpected exception. Help-mode (no subcommand) also emits
    a trace with `subcommand=<unknown>` and `exit_code=2`. See
    `_trace.py` for format and rationale.

    Trace-write failures are absorbed (`try / except OSError`) so a
    full disk or read-only `.devforge/` cannot break a helper run.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    subcommand_name = getattr(args, "subcommand", None) or "<unknown>"
    # Circuit breaker: precondition check BEFORE handler dispatch and
    # BEFORE the trace-write timing wrapper. A tripped breaker aborts
    # the invocation entirely with exit code 3. We do NOT emit a trace
    # line for the trip itself — the stderr message is the audit
    # trail, and re-running to re-evaluate would either trip again or
    # have been bypassed via DEVFORGE_DISABLE_CIRCUIT_BREAKER.
    trip = _circuit.check_circuit_breakers(subcommand_name)
    if trip is not None:
        sys.stderr.write(trip + "\n")
        return 3
    if getattr(args, "func", None) is None:
        parser.print_help(sys.stderr)
        exit_code = 2
        try:
            _trace.write_trace(subcommand_name, 0, exit_code, args)
        except OSError:
            pass
        return exit_code
    start = time.perf_counter()
    try:
        exit_code = args.func(args)
    except Exception as err:
        # Unexpected handler exception (NOT a clean _AbortTransaction —
        # those are caught inside handlers and become exit codes). We
        # still emit a trace line so post-incident forensics can see
        # *something* at the failure point, then re-raise so the
        # underlying bug surfaces to the operator.
        duration_ms = int((time.perf_counter() - start) * 1000)
        try:
            # Best-effort: synthesize a summary that captures the
            # exception class so it's filterable from the trace stream.
            summary_args = argparse.Namespace(**vars(args))
            _trace.write_trace(
                subcommand_name, duration_ms, 1, summary_args,
            )
        except OSError:
            pass
        raise err
    duration_ms = int((time.perf_counter() - start) * 1000)
    try:
        _trace.write_trace(subcommand_name, duration_ms, exit_code, args)
    except OSError:
        pass
    return exit_code
