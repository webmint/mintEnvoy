"""CLI command handler for ``constitute_helper verify-magic-enum`` (Phase 1).

Reads the ``forcing_functions.magic_enum_duplication`` block from
``.devforge/constitute.json``, builds the generated-enum inventory, scans
consumer source, and emits findings.

Exit codes follow the Phase 0 substrate:
  0 — clean (no violations, or feature disabled/unconfigured).
  2 — one or more violations found.

Early-exit conditions (exit 0)
------------------------------
- ``.devforge/constitute.json`` does not exist (early-adoption case; not an
  error).
- ``forcing_functions`` key absent from config.
- ``forcing_functions.magic_enum_duplication`` absent from config.
- ``forcing_functions.magic_enum_duplication.enabled == false``.

In all early-exit cases a brief note is written to stderr so the user knows
why the detector ran clean.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

from .._shared import EXIT_CLEAN, emit_findings
from ._inventory import extract_enum_inventory
from ._scanner import scan_for_magic_enum_violations


def cmd_verify_magic_enum(args: argparse.Namespace) -> int:
    """Handler for ``verify-magic-enum`` subcommand.

    Parameters
    ----------
    args:
        Namespace with attributes:
        - ``root`` (str | None): consumer project root; defaults to cwd.
        - ``config`` (str | None): path to constitute.json; defaults to
          ``<root>/.devforge/constitute.json``.

    Returns
    -------
    int -- exit code (0 = clean, 2 = violations).
    """
    # --- 1. Resolve root ---
    root = Path(getattr(args, "root", None) or ".").resolve()

    # --- 2. Resolve config path ---
    config_path_arg = getattr(args, "config", None)
    if config_path_arg:
        config_path = Path(config_path_arg).resolve()
    else:
        config_path = root / ".devforge" / "constitute.json"

    # --- 3. Load config ---
    if not config_path.exists():
        sys.stderr.write(
            "constitute.json not found at {path}; skipping verify-magic-enum\n".format(
                path=config_path,
            )
        )
        return EXIT_CLEAN

    try:
        import json
        state = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(
            "verify-magic-enum: cannot parse config {path}: {err}\n".format(
                path=config_path, err=exc
            )
        )
        return EXIT_CLEAN

    # --- 4. Check forcing_functions.magic_enum_duplication ---
    ff = state.get("forcing_functions")
    if not ff or not isinstance(ff, dict):
        sys.stderr.write(
            "forcing_functions block absent from constitute.json; "
            "skipping verify-magic-enum\n"
        )
        return EXIT_CLEAN

    rule_cfg = ff.get("magic_enum_duplication")
    if not rule_cfg or not isinstance(rule_cfg, dict):
        sys.stderr.write(
            "forcing_functions.magic_enum_duplication not configured; "
            "skipping verify-magic-enum\n"
        )
        return EXIT_CLEAN

    if not rule_cfg.get("enabled", False):
        return EXIT_CLEAN

    # --- 5. Resolve generated_types_dirs ---
    raw_gen_dirs = rule_cfg.get("generated_types_dirs", [])
    if not isinstance(raw_gen_dirs, list):
        raw_gen_dirs = []
    generated_dirs: List[Path] = [root / d for d in raw_gen_dirs]

    # --- 6. Read allowlist ---
    allowlist_globs: List[str] = rule_cfg.get("allowlist_paths", [])
    if not isinstance(allowlist_globs, list):
        allowlist_globs = []

    # --- 7. Build inventory ---
    inventory = extract_enum_inventory(generated_dirs)

    # --- 8. Scan source ---
    findings = scan_for_magic_enum_violations(root, inventory, allowlist_globs, generated_dirs)

    # --- 9. Emit findings and return exit code ---
    return emit_findings("magic_enum_duplication", findings)
