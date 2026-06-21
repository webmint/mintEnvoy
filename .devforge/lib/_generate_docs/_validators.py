"""Re-export shim for the generate_docs validator surface (post-2026-05-07 B.5 cleanup).

Orchestration moved to tier modules: _validators_package owns package-tier
render-coupled functions; _validators_concern owns concern-tier ones. This
file re-exports the full public API so existing `from ._validators import X`
call sites work unchanged.

Render symbols are re-exported for legacy patch tolerance. New code that
needs to monkey-patch a render function should patch it on the tier module
directly (_validators_package.render_package_skeleton or
_validators_concern.render_concern_skeleton).

Zero function definitions in this file.
"""

# --- shared helpers ----------------------------------------------------------
from ._validators_shared import (  # noqa: F401
    _check_codeblock,
    _err,
    _format_error_line,
    _normalize_for_compare,
    _print_errors,
    _slice_snippet_diff,
)

# --- decomposition gate ------------------------------------------------------
from ._validators_decomposition import (  # noqa: F401
    _ARCH_ROLE_FOLDER_NAMES,
    _TRIVIAL_LEAF_FOLDER_NAMES,
    _check_decomposition,
    _is_substantive_subfolder,
    _scan_substantive_subfolders,
)

# --- package-tier ------------------------------------------------------------
from ._validators_package import (  # noqa: F401
    INIT_YAML_FILE_NAME,
    _PACKAGES_DETECTED_PATH_RE,
    _check_all_codeblocks,
    _check_at_least_one_dependency,
    _check_at_least_one_export,
    _check_enums,
    _check_internal_deps,
    _check_no_todos,
    _check_optional_render,
    _load_packages_detected_paths,
    _resolve_internal_dep,
    cmd_render_package_doc,
    cmd_validate_package,
    validate_package,
)

# --- concern-tier ------------------------------------------------------------
from ._validators_concern import (  # noqa: F401
    FILE_DOC_MIN_SIZE_BYTES,
    _check_concern_at_least_one_public_surface,
    _check_concern_codeblocks,
    _check_concern_enums,
    _check_concern_no_todos,
    _check_concern_optional_render,
    _check_concern_required_fields,
    _check_file_docs_complete,
    cmd_render_concern_doc,
    cmd_validate_concern,
    validate_concern,
)

# --- file-doc-tier (B.3 + B.4) -----------------------------------------------
from ._validators_file_doc import (  # noqa: F401
    AMBIGUOUS_RATE_THRESHOLD,
    BANNED_PHRASE_TOLERANCE,
    CROSS_CONCERN_DUPLICATE_RATE_THRESHOLD,
    VACUOUS_PASS_TOLERANCE,
    _check_annotation_banned_phrase,
    _check_annotation_cite_resolves,
    _check_annotation_schema,
    _check_file_doc_specificity,
    _recompute_content_hash,
    cmd_validate_file_doc,
    cmd_verify_file_docs,
)

# --- render symbols (legacy patch tolerance) ---------------------------------
from ._render import (  # noqa: F401
    CONCERN_OPTIONAL_SECTION_MARKERS,
    CONCERN_REQUIRED_FIELD_TODO_MARKERS,
    OPTIONAL_SECTION_MARKERS,
    REQUIRED_FIELD_TODO_MARKERS,
    _atomic_write_text,
    _project_root,
    render_concern_skeleton,
    render_package_skeleton,
)
