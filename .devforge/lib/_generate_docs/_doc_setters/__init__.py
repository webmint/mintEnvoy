"""Multi-tier skeleton-fill primitives — split sub-package.

Re-exports the public surface (the symbols that `_generate_docs/_cli.py`
imports) from internal sub-modules:

- `_skeletons` — placeholders, path resolution, skeleton builders
- `_blocks` — section replacers + annotation interleavers
- `_renderers` — bullet / table / sub-section render helpers
- `_cmds_package` — cmd_init_doc + cmd_set_doc_* + cmd_render_doc + builders
- `_cmds_project` — cmd_set_overview_* + cmd_set_architecture_* + builders

Refactor lineage: split from a 2041-line `_doc_setters.py` module per
Phase B1 of `REFACTOR-MONOLITHIC-HELPERS-PLAN.md`. No public API
change — `_cli.py`'s existing `from ._doc_setters import …` block
continues to resolve through this `__init__`.
"""

from ._cmds_package import (  # noqa: F401
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
    cmd_init_doc,
    cmd_render_doc,
    cmd_set_doc_concerns,
    cmd_set_doc_cross_cuts,
    cmd_set_doc_files,
    cmd_set_doc_layers,
    cmd_set_doc_packages,
    cmd_set_doc_patterns,
    cmd_set_doc_purpose,
    cmd_set_doc_structure,
    cmd_set_doc_subconcerns,
)
from ._cmds_project import (  # noqa: F401
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
    cmd_set_architecture_conventions,
    cmd_set_architecture_cross_cuts_detailed,
    cmd_set_architecture_dependency_direction_rules,
    cmd_set_architecture_dependency_overview_mermaid,
    cmd_set_architecture_module_structure,
    cmd_set_architecture_overview_narrative,
    cmd_set_architecture_patterns,
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
