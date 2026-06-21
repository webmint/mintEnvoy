"""CLI command handler for ``constitute_helper verify-cross-layer-imports`` (Phase 3).

Reads the ``forcing_functions.cross_layer_imports`` block from
``.devforge/constitute.json``, validates the layer graph, scans consumer
source, and emits findings.

Exit codes follow the Phase 0 substrate:
  0 — clean (no violations, or feature disabled/unconfigured).
  2 — one or more violations found OR malformed layer_graph config.

Early-exit conditions (exit 0)
------------------------------
- ``.devforge/constitute.json`` does not exist (early-adoption case; not an
  error).
- ``forcing_functions`` key absent from config.
- ``forcing_functions.cross_layer_imports`` absent from config.
- ``forcing_functions.cross_layer_imports.enabled == false``.

Config-error condition (exit 2)
--------------------------------
If ``load_layer_graph`` raises ``ValueError`` (e.g., unknown layer reference,
layer declared in one map but not the other), the error message is written to
stderr and the command exits with ``EXIT_FINDINGS``.  A malformed layer graph
is treated as a gate failure so misconfigured detectors are immediately
surfaced rather than silently skipped.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from .._shared import EXIT_CLEAN, EXIT_FINDINGS, emit_findings
from ._graph import load_layer_graph
from ._scanner import scan_for_cross_layer_violations


def cmd_verify_cross_layer_imports(args: argparse.Namespace) -> int:
    """Handler for the ``verify-cross-layer-imports`` subcommand.

    Parameters
    ----------
    args:
        Namespace with attributes:
        - ``root`` (str | None): consumer project root; defaults to cwd.
        - ``config`` (str | None): path to constitute.json; defaults to
          ``<root>/.devforge/constitute.json``.

    Returns
    -------
    int -- exit code (0 = clean or disabled, 2 = violations or config error).
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
            "skipping verify-cross-layer-imports\n".format(path=config_path)
        )
        return EXIT_CLEAN

    # --- 4. Load config ---
    # NOTE: malformed JSON exits EXIT_CLEAN (consistent with Phase 1
    # cmd_verify_magic_enum at _magic_enum/_cmd.py).  This is a family-wide
    # design choice: a corrupt config silently gives a "clean" signal,
    # which in a CI gate context could mask gate-not-running.  Phase 5
    # (/implement wire-in) may promote this to EXIT_FINDINGS once the
    # detector family is wired into CI gates.  Do NOT diverge Phase 3
    # from Phase 1 in isolation — change requires a cross-family audit.
    try:
        state = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(
            "verify-cross-layer-imports: cannot parse config {path}: {err}\n".format(
                path=config_path, err=exc
            )
        )
        return EXIT_CLEAN

    # --- 5. Tolerate absent forcing_functions block ---
    ff = state.get("forcing_functions")
    if not ff or not isinstance(ff, dict):
        sys.stderr.write(
            "forcing_functions block absent from constitute.json; "
            "skipping verify-cross-layer-imports\n"
        )
        return EXIT_CLEAN

    # --- 6. Tolerate absent or disabled cross_layer_imports block ---
    rule_cfg = ff.get("cross_layer_imports")
    if not rule_cfg or not isinstance(rule_cfg, dict):
        sys.stderr.write(
            "forcing_functions.cross_layer_imports not configured; "
            "skipping verify-cross-layer-imports\n"
        )
        return EXIT_CLEAN

    if not rule_cfg.get("enabled", False):
        # Silently exit 0 when disabled (consistent with Phase 1 magic-enum pattern).
        return EXIT_CLEAN

    # --- 7. Load and validate layer graph ---
    try:
        allowed_imports_map, layer_dirs_map = load_layer_graph(rule_cfg)
    except ValueError as exc:
        sys.stderr.write(
            "verify-cross-layer-imports: invalid layer_graph config: {err}\n".format(
                err=exc
            )
        )
        return EXIT_FINDINGS

    # --- 8. Read allowlist ---
    allowlist_globs: List[str] = rule_cfg.get("allowlist_paths", [])
    if not isinstance(allowlist_globs, list):
        allowlist_globs = []

    # --- 9. Scan source ---
    findings = scan_for_cross_layer_violations(
        root, allowed_imports_map, layer_dirs_map, allowlist_globs
    )

    # --- 10. Emit findings and return exit code ---
    return emit_findings("cross_layer_imports", findings)
