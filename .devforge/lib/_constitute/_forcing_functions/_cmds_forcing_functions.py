"""CLI handlers for set-forcing-functions and list-forcing-functions.

set-forcing-functions
    Writes/updates a ``forcing_functions.<rule>`` block in
    ``.devforge/constitute.json``.  Validates per-rule required fields.

list-forcing-functions
    Reads constitute.json and prints the names of configured rules, one
    per line (machine-readable for the pre-commit hook).  ``--enabled``
    filters to rules with ``enabled: true``.

Both commands default ``--config`` to ``<cwd>/.devforge/constitute.json``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ._setters import KNOWN_RULES, RULE_TO_VERB, set_forcing_function


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _resolve_config_path(config_arg: object) -> Path:
    """Resolve the --config arg (str | None) to a Path."""
    if config_arg:
        return Path(str(config_arg)).resolve()
    return Path(".").resolve() / ".devforge" / "constitute.json"


# ---------------------------------------------------------------------------
# set-forcing-functions handler
# ---------------------------------------------------------------------------

def cmd_set_forcing_functions(args: argparse.Namespace) -> int:
    """Handler for the ``set-forcing-functions`` subcommand.

    Parses CLI args, converts types, calls ``set_forcing_function``, exits
    0 on success or 2 on validation error.
    """
    rule = args.rule
    if rule not in KNOWN_RULES:
        sys.stderr.write(
            "set-forcing-functions: unknown rule {rule!r}; "
            "allowed: {allowed}\n".format(
                rule=rule, allowed=sorted(KNOWN_RULES)
            )
        )
        return 2

    # Parse --enabled (string "true"/"false" from CLI)
    enabled_raw = getattr(args, "enabled", "true").lower()
    if enabled_raw not in ("true", "false"):
        sys.stderr.write(
            "set-forcing-functions: --enabled must be 'true' or 'false', "
            "got {val!r}\n".format(val=args.enabled)
        )
        return 2
    enabled = enabled_raw == "true"

    # Parse --generated-types-dirs (CSV or absent)
    generated_types_dirs = None
    raw_gen = getattr(args, "generated_types_dirs", None)
    if raw_gen is not None:
        generated_types_dirs = [p.strip() for p in raw_gen.split(",") if p.strip()]
        if not generated_types_dirs:
            sys.stderr.write(
                "set-forcing-functions: --generated-types-dirs must contain "
                "at least one non-empty path\n"
            )
            return 2

    # Parse --allowlist-paths (CSV or absent)
    allowlist_paths = None
    raw_al = getattr(args, "allowlist_paths", None)
    if raw_al is not None:
        allowlist_paths = [p.strip() for p in raw_al.split(",") if p.strip()]

    # Parse --layer-graph-json (JSON object string or absent)
    layer_graph = None
    raw_lg = getattr(args, "layer_graph_json", None)
    if raw_lg is not None:
        try:
            parsed = json.loads(raw_lg)
        except json.JSONDecodeError as exc:
            sys.stderr.write(
                "set-forcing-functions: --layer-graph-json is not valid JSON: "
                "{err}\n".format(err=exc)
            )
            return 2
        if not isinstance(parsed, dict):
            sys.stderr.write(
                "set-forcing-functions: --layer-graph-json must be a JSON object\n"
            )
            return 2
        layer_graph = parsed

    # Parse --layer-dirs-json (JSON object string or absent)
    layer_dirs = None
    raw_ld = getattr(args, "layer_dirs_json", None)
    if raw_ld is not None:
        try:
            parsed = json.loads(raw_ld)
        except json.JSONDecodeError as exc:
            sys.stderr.write(
                "set-forcing-functions: --layer-dirs-json is not valid JSON: "
                "{err}\n".format(err=exc)
            )
            return 2
        if not isinstance(parsed, dict):
            sys.stderr.write(
                "set-forcing-functions: --layer-dirs-json must be a JSON object\n"
            )
            return 2
        layer_dirs = parsed

    config_path = _resolve_config_path(getattr(args, "config", None))

    try:
        set_forcing_function(
            config_path,
            rule,
            enabled,
            generated_types_dirs=generated_types_dirs,
            allowlist_paths=allowlist_paths,
            layer_graph=layer_graph,
            layer_dirs=layer_dirs,
        )
    except (ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write("set-forcing-functions: {err}\n".format(err=exc))
        return 2
    except OSError as exc:
        sys.stderr.write(
            "set-forcing-functions: cannot write config: {err}\n".format(err=exc)
        )
        return 1

    return 0


# ---------------------------------------------------------------------------
# list-forcing-functions handler
# ---------------------------------------------------------------------------

def cmd_list_forcing_functions(args: argparse.Namespace) -> int:
    """Handler for the ``list-forcing-functions`` subcommand.

    Reads constitute.json and prints rule names (one per line).
    With ``--enabled``, prints only rules where ``enabled: true``.
    With ``--format verb``, outputs the CLI verb accepted by constitute_helper
    (e.g. ``verify-magic-enum``) instead of the config key; unknown rule names
    are omitted from verb output (forward-compat rules have no verb yet).

    Exit codes:
      0  -- success (zero or more rules printed; missing config = 0 lines).
      1  -- config file present but cannot be parsed (malformed JSON).
    """
    config_path = _resolve_config_path(getattr(args, "config", None))
    filter_enabled = getattr(args, "enabled_only", False)
    fmt = getattr(args, "format", "key") or "key"

    if not config_path.exists():
        # Missing config = no rules configured; machine-readable: no output.
        return 0

    try:
        raw = config_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "list-forcing-functions: cannot parse {path}: {err}\n".format(
                path=config_path, err=exc
            )
        )
        return 1

    if not isinstance(data, dict):
        sys.stderr.write(
            "list-forcing-functions: {path}: expected a JSON object\n".format(
                path=config_path
            )
        )
        return 1

    ff = data.get("forcing_functions")
    if not ff or not isinstance(ff, dict):
        # No forcing_functions block — zero rules.
        return 0

    for rule_name, rule_block in ff.items():
        include = True
        if filter_enabled:
            include = isinstance(rule_block, dict) and rule_block.get("enabled", False)
        if not include:
            continue

        if fmt == "verb":
            verb = RULE_TO_VERB.get(rule_name)
            if verb is None:
                # Unknown rule (forward-compat): no verb available, skip.
                continue
            sys.stdout.write(verb + "\n")
        else:
            sys.stdout.write(rule_name + "\n")

    return 0
