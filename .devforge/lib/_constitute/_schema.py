"""Schema constants — top-level shape + enums + bucket mappings + universal sections."""

from __future__ import annotations

OUTPUT_FILE_NAME = "constitute.json"

# Top-level key order is locked. Reordering changes on-disk byte order.
# Kind abbreviations:
#   "scalar"           — string-or-None
#   "date_scalar"      — string-or-None expected as YYYY-MM-DD
#   "enum_scalar"      — string-or-None restricted by ENUM_FIELDS["mode"]
#   "nullable_record"  — None or a nested record. Step 2 setters populate
#                        the dict shape (project_identity = 4 subfields;
#                        scaffolding_guide = 2 subfields). Both default to
#                        None — greenfield mode may legitimately leave
#                        scaffolding_guide null until set, and project_identity
#                        is null until set-project-identity runs in Phase 2.
#   "section_array"    — list of section records (default [])
#   "patterns_section" — dict with 6 named buckets, each a rule_array
FIELD_SCHEMA = (
    ("project_name",              "scalar"),
    ("generated_date",            "date_scalar"),
    ("last_updated",              "date_scalar"),
    ("mode",                      "enum_scalar"),
    ("project_identity",          "nullable_record"),
    ("architecture_rules",        "section_array"),
    ("code_quality_standards",    "section_array"),
    ("patterns_and_antipatterns", "patterns_section"),
    ("domain_rules",              "section_array"),
    ("workflow_rules",            "section_array"),
    ("scaffolding_guide",         "nullable_record"),
    # Forcing-functions detector config.  Populated by
    # ``constitute_helper set-forcing-functions`` (Phase 5a) or hand-edited
    # directly.  Per-rule schema is validated by validate_forcing_functions()
    # below; detector verbs read the block directly without re-validating.
    ("forcing_functions",         "optional_dict"),
)


# ---------------------------------------------------------------------------
# Forcing-functions per-rule schema validation (Phase 5a)
# ---------------------------------------------------------------------------

# Public name for the set of known forcing-function rules.
FORCING_FUNCTION_RULES = frozenset({
    "magic_enum_duplication",
    "cross_layer_imports",
    "any_with_generated_available",
    "design_token_provenance",
})


def validate_forcing_functions(ff_block: object) -> list:
    """Validate the ``forcing_functions`` dict from constitute.json.

    Returns a list of error message strings (empty = valid).  Does NOT
    raise; the caller decides whether to abort or warn.

    Accepts ``None`` (field absent) or any non-dict value as "no config"
    and returns no errors — toleration mirrors the existing detector
    early-exit pattern.

    Per-rule rules
    --------------
    magic_enum_duplication:
      - ``enabled`` must be bool
      - ``generated_types_dirs`` must be a list[str] (present + non-empty
        when enabled=true)
      - ``allowlist_paths`` optional; if present must be list[str]

    cross_layer_imports:
      - ``enabled`` must be bool
      - ``layer_graph`` must be a dict of str → list[str] (present + non-empty
        when enabled=true)
      - ``layer_dirs`` must be a dict of str → str (present + non-empty
        when enabled=true)
      - when enabled=true, layer_graph and layer_dirs keys must match

    any_with_generated_available:
      - ``enabled`` must be bool
      - ``generated_types_dirs`` must be list[str] (present + non-empty
        when enabled=true)
      - ``allowlist_paths`` optional; if present must be list[str]
    """
    if ff_block is None or not isinstance(ff_block, dict):
        return []

    errors = []

    for rule_name, rule_cfg in ff_block.items():
        prefix = "forcing_functions.{rule}".format(rule=rule_name)

        if not isinstance(rule_cfg, dict):
            errors.append("{prefix}: must be a dict, got {t}".format(
                prefix=prefix, t=type(rule_cfg).__name__
            ))
            continue

        # ---- enabled field ----
        enabled_val = rule_cfg.get("enabled")
        if not isinstance(enabled_val, bool):
            errors.append("{prefix}.enabled: must be a bool".format(prefix=prefix))
        enabled = bool(enabled_val)

        if rule_name == "magic_enum_duplication":
            errors.extend(_validate_dirs_list(
                rule_cfg, "generated_types_dirs", prefix, required_when_enabled=enabled
            ))
            if "allowlist_paths" in rule_cfg:
                errors.extend(_validate_str_list(
                    rule_cfg["allowlist_paths"], prefix + ".allowlist_paths"
                ))

        elif rule_name == "cross_layer_imports":
            errors.extend(_validate_layer_graph(rule_cfg, prefix, enabled))

        elif rule_name == "any_with_generated_available":
            errors.extend(_validate_dirs_list(
                rule_cfg, "generated_types_dirs", prefix, required_when_enabled=enabled
            ))
            if "allowlist_paths" in rule_cfg:
                errors.extend(_validate_str_list(
                    rule_cfg["allowlist_paths"], prefix + ".allowlist_paths"
                ))

        elif rule_name == "design_token_provenance":
            # token_source_css: optional str
            tsc = rule_cfg.get("token_source_css")
            if tsc is not None and not isinstance(tsc, str):
                errors.append(
                    "{prefix}.token_source_css: must be a string, "
                    "got {t}".format(prefix=prefix, t=type(tsc).__name__)
                )
            # manifest_path: optional str (back-compat; absent = glob at run time)
            mp = rule_cfg.get("manifest_path")
            if mp is not None and not isinstance(mp, str):
                errors.append(
                    "{prefix}.manifest_path: must be a string, "
                    "got {t}".format(prefix=prefix, t=type(mp).__name__)
                )
            # allowlist_paths: optional list[str]
            if "allowlist_paths" in rule_cfg:
                errors.extend(_validate_str_list(
                    rule_cfg["allowlist_paths"], prefix + ".allowlist_paths"
                ))

        elif rule_name not in FORCING_FUNCTION_RULES:
            # Unknown rule names are tolerated (forward-compat; user may have a
            # newer version of the config that added a rule not yet in this build).
            pass

    return errors


# ---------------------------------------------------------------------------
# Private schema sub-validators
# ---------------------------------------------------------------------------

def _validate_str_list(value: object, field_path: str) -> list:
    """Return errors if ``value`` is not a list[str]."""
    if not isinstance(value, list):
        return ["{fp}: must be a list".format(fp=field_path)]
    errs = []
    for i, item in enumerate(value):
        if not isinstance(item, str):
            errs.append("{fp}[{i}]: must be a string".format(fp=field_path, i=i))
    return errs


def _validate_dirs_list(
    rule_cfg: dict,
    key: str,
    prefix: str,
    required_when_enabled: bool,
) -> list:
    """Validate a ``generated_types_dirs``-style field."""
    field_path = "{prefix}.{key}".format(prefix=prefix, key=key)
    value = rule_cfg.get(key)
    if value is None:
        if required_when_enabled:
            return ["{fp}: required when enabled=true".format(fp=field_path)]
        return []
    errs = _validate_str_list(value, field_path)
    if not errs and required_when_enabled and len(value) == 0:
        errs.append("{fp}: must be non-empty when enabled=true".format(fp=field_path))
    return errs


def _validate_layer_graph(rule_cfg: dict, prefix: str, enabled: bool) -> list:
    """Validate cross_layer_imports layer_graph and layer_dirs fields."""
    errs = []

    graph = rule_cfg.get("layer_graph")
    dirs = rule_cfg.get("layer_dirs")

    if graph is None:
        if enabled:
            errs.append("{prefix}.layer_graph: required when enabled=true".format(
                prefix=prefix
            ))
    elif not isinstance(graph, dict):
        errs.append("{prefix}.layer_graph: must be a dict".format(prefix=prefix))
    else:
        for layer, allows in graph.items():
            if not isinstance(allows, list):
                errs.append(
                    "{prefix}.layer_graph.{layer}: value must be a list".format(
                        prefix=prefix, layer=layer
                    )
                )
            else:
                for i, dep in enumerate(allows):
                    if not isinstance(dep, str):
                        errs.append(
                            "{prefix}.layer_graph.{layer}[{i}]: "
                            "must be a string".format(
                                prefix=prefix, layer=layer, i=i
                            )
                        )

    if dirs is None:
        if enabled:
            errs.append("{prefix}.layer_dirs: required when enabled=true".format(
                prefix=prefix
            ))
    elif not isinstance(dirs, dict):
        errs.append("{prefix}.layer_dirs: must be a dict".format(prefix=prefix))
    else:
        for layer, path_val in dirs.items():
            if not isinstance(path_val, str):
                errs.append(
                    "{prefix}.layer_dirs.{layer}: value must be a string".format(
                        prefix=prefix, layer=layer
                    )
                )

    # Cross-field key-match check (only when both are valid dicts and enabled)
    if (enabled
            and isinstance(graph, dict)
            and isinstance(dirs, dict)
            and not errs):
        graph_keys = set(graph.keys())
        dirs_keys = set(dirs.keys())
        if graph_keys != dirs_keys:
            extra_graph = sorted(graph_keys - dirs_keys)
            extra_dirs = sorted(dirs_keys - graph_keys)
            msg_parts = []
            if extra_graph:
                msg_parts.append(
                    "layer_graph has extra keys: {k}".format(k=extra_graph)
                )
            if extra_dirs:
                msg_parts.append(
                    "layer_dirs has extra keys: {k}".format(k=extra_dirs)
                )
            errs.append(
                "{prefix}: layer_graph and layer_dirs keys must match; "
                "{msg}".format(prefix=prefix, msg="; ".join(msg_parts))
            )

    return errs

# Closed enum sets. Step 2 setters enforce these at set-time.
ENUM_FIELDS = {
    "mode":        {"existing-codebase", "greenfield"},
    "rule_tag":    {"extracted", "enforced", "universal", "project-specific"},
    "section_tag": {"universal", "project-specific", "greenfield-only"},
    "code_label":  {"CORRECT", "WRONG", "EXAMPLE"},
}

# Patterns-and-antipatterns bucket names (locked order for deterministic JSON).
_PATTERNS_BUCKETS = (
    "always_universal",
    "always_project_specific",
    "never_universal",
    "never_project_specific",
    "prefer_universal",
    "prefer_project_specific",
)

_SECTION_BUCKET_TO_KEY = {
    "architecture":  "architecture_rules",
    "code-quality":  "code_quality_standards",
    "domain":        "domain_rules",
    "workflow":      "workflow_rules",
}

_PATTERN_SCOPE_TO_SUFFIX = {
    "universal":        "universal",
    "project-specific": "project_specific",
}

# Closed list of universal section numbers (§-prefixed, as used in return shapes).
_UNIVERSAL_SECTIONS = (
    "§3.5", "§3.6", "§3.7", "§3.8",
    "§4.1", "§4.2", "§4.3",
    "§6.1", "§6.2", "§6.3", "§6.4",
)

# Maps patterns_and_antipatterns bucket names to §-number keys.
_PATTERNS_BUCKET_TO_SECTION = {
    "always_universal":  "§4.1",
    "never_universal":   "§4.2",
    "prefer_universal":  "§4.3",
}
