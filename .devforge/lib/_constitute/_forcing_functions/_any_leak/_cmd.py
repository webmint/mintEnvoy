"""CLI command handler for ``constitute_helper verify-any-leak`` (Phase 4).

Reads the ``forcing_functions.any_with_generated_available`` block from
``.devforge/constitute.json``, scans consumer source for explicit ``any``
annotations in files that import from declared generated-types dirs, and emits
findings.

Exit codes follow the Phase 0 substrate:
  0 — clean (no violations, or feature disabled/unconfigured).
  2 — one or more violations found.

Early-exit conditions (exit 0)
------------------------------
- ``.devforge/constitute.json`` does not exist (early-adoption case; not an
  error).
- ``forcing_functions`` key absent from config.
- ``forcing_functions.any_with_generated_available`` absent from config.
- ``forcing_functions.any_with_generated_available.enabled == false``.
- ``forcing_functions.any_with_generated_available.generated_types_dirs``
  absent (warns to stderr).

Config-parse error (exit 0)
-----------------------------
Malformed JSON exits EXIT_CLEAN with a stderr note.  This is a family-wide
design choice consistent with Phase 1 (cmd_verify_magic_enum) and Phase 3
(cmd_verify_cross_layer_imports): a corrupt config silently gives a "clean"
signal.  Phase 5 (/implement wire-in) may promote this to EXIT_FINDINGS
once the detector family is wired into CI gates.  Do NOT diverge Phase 4
from Phase 1/3 in isolation — change requires a cross-family audit.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from .._shared import EXIT_CLEAN, emit_findings
from ._scanner import scan_for_any_leak_violations


def cmd_verify_any_leak(args: argparse.Namespace) -> int:
    """Handler for the ``verify-any-leak`` subcommand.

    Parameters
    ----------
    args:
        Namespace with attributes:
        - ``root`` (str | None): consumer project root; defaults to cwd.
        - ``config`` (str | None): path to constitute.json; defaults to
          ``<root>/.devforge/constitute.json``.

    Returns
    -------
    int -- exit code (0 = clean or disabled, 2 = violations).
    """
    # --- 1. Resolve root ---
    root = Path(getattr(args, "root", None) or ".").resolve()

    # --- 2. Resolve config path ---
    config_path_arg = getattr(args, "config", None)
    if config_path_arg:
        config_path = Path(config_path_arg).resolve()
    else:
        config_path = root / ".devforge" / "constitute.json"

    # --- 3. Tolerate missing config ---
    if not config_path.exists():
        sys.stderr.write(
            "constitute.json not found at {path}; "
            "skipping verify-any-leak\n".format(path=config_path)
        )
        return EXIT_CLEAN

    # --- 4. Load config ---
    # NOTE: malformed JSON exits EXIT_CLEAN — see module docstring for
    # cross-family design rationale.
    try:
        state = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(
            "verify-any-leak: cannot parse config {path}: {err}\n".format(
                path=config_path, err=exc
            )
        )
        return EXIT_CLEAN

    # --- 5. Tolerate absent forcing_functions block ---
    ff = state.get("forcing_functions")
    if not ff or not isinstance(ff, dict):
        sys.stderr.write(
            "forcing_functions block absent from constitute.json; "
            "skipping verify-any-leak\n"
        )
        return EXIT_CLEAN

    # --- 6. Tolerate absent any_with_generated_available block ---
    rule_cfg = ff.get("any_with_generated_available")
    if not rule_cfg or not isinstance(rule_cfg, dict):
        sys.stderr.write(
            "forcing_functions.any_with_generated_available not configured; "
            "skipping verify-any-leak\n"
        )
        return EXIT_CLEAN

    # --- 7. Check enabled flag ---
    if not rule_cfg.get("enabled", False):
        # Silently exit 0 when disabled (consistent with Phase 1/3 pattern).
        return EXIT_CLEAN

    # --- 8. Read generated_types_dirs (required) ---
    raw_gen_dirs = rule_cfg.get("generated_types_dirs")
    if not raw_gen_dirs or not isinstance(raw_gen_dirs, list):
        sys.stderr.write(
            "any_with_generated_available.generated_types_dirs missing; "
            "skipping verify-any-leak\n"
        )
        return EXIT_CLEAN

    # --- 9. Read allowlist_paths (default []) ---
    allowlist_globs: List[str] = rule_cfg.get("allowlist_paths", [])
    if not isinstance(allowlist_globs, list):
        allowlist_globs = []

    # --- 10. Resolve generated_types_dirs to absolute paths ---
    generated_dirs: List[Path] = [root / d for d in raw_gen_dirs]

    # --- 11. Scan source ---
    findings = scan_for_any_leak_violations(root, generated_dirs, allowlist_globs)

    # --- 12. Emit findings and return exit code ---
    return emit_findings("any_with_generated_available", findings)
