"""CLI command handler for ``constitute_helper verify-design-tokens`` (plan 40 Phase 4).

Reads the ``forcing_functions.design_token_provenance`` block from
``.devforge/constitute.json``, optionally loads a token source CSS file, and
scans component style sources for provenance violations.

Exit codes follow the Phase 0 substrate:
  0 — clean (no violations, or feature disabled/unconfigured).
  2 — one or more violations found.

Early-exit conditions (exit 0)
------------------------------
- ``.devforge/constitute.json`` does not exist.
- ``forcing_functions`` key absent from config.
- ``forcing_functions.design_token_provenance`` absent from config.
- ``forcing_functions.design_token_provenance.enabled == false``.

Config-parse error (exit 0)
----------------------------
Malformed JSON exits EXIT_CLEAN with a stderr note.  Consistent with the
family-wide design (same pattern as verify-any-leak, verify-magic-enum,
verify-cross-layer-imports): a corrupt config gives a "clean" signal so
as not to block CI on infrastructure problems.  Phase 5 wire-in may revisit.

Checks 1-4 (color/border literals, var-fallback, undefined-token,
interactive-state coverage) are the full check set here — manifest-independent,
they run unconditionally whenever the rule is enabled.

Check 5 RETIRED (plan 53 Phase 7a)
-----------------------------------
The MATCH-element / disposition-manifest token-binding check (formerly
Check 5) has been removed along with the `data-ref` disposition-manifest
schema it depended on (plan 53 Phase 3 retires `ElementRecord` / `disposition`
/ `ManifestContainer` in `_design/_schema.py` in favour of the anchor +
binding schema).  All manifest-resolution machinery that existed solely to
support Check 5 (glob-based `specs/*/design-manifest.json` discovery, the
reference.html-anchored spacing-scope circularity fix from plan 45 Step 3)
is removed with it — none of it is read by this detector any more.

When ``token_source_css`` is set in the config (path to design/styles.css),
the command extracts defined tokens (--token-name patterns) from it for
Check 3.  When absent, Check 3 is skipped (OQ-6: absent CSS → no token
source to bind to).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Set

from .._shared import EXIT_CLEAN, emit_findings
from ._scanner import scan_for_design_token_violations, _extract_defined_tokens


_RULE_KEY = "design_token_provenance"


def _load_token_source(token_source_css):
    # type: (str) -> Set[str]
    """Load defined tokens from a CSS token source file.

    Returns the set of CSS custom property names (e.g. ``{"--color-primary"}``)
    defined in the file.  Returns an empty set when the file does not exist
    (OQ-6: absent CSS → relax Check 3, no crash) or cannot be read.
    """
    css_path = Path(token_source_css)
    if not css_path.exists():
        # OQ-6: absent CSS → relax Check 3 (skipped entirely, see _scanner.py)
        return set()

    try:
        css_text = css_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        sys.stderr.write(
            "verify-design-tokens: cannot read token source {path}: {err}\n".format(
                path=token_source_css, err=exc
            )
        )
        return set()

    return _extract_defined_tokens(css_text)


def cmd_verify_design_tokens(args):
    # type: (argparse.Namespace) -> int
    """Handler for the ``verify-design-tokens`` subcommand.

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
            "skipping verify-design-tokens\n".format(path=config_path)
        )
        return EXIT_CLEAN

    # --- 4. Load config ---
    try:
        state = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(
            "verify-design-tokens: cannot parse config {path}: {err}\n".format(
                path=config_path, err=exc
            )
        )
        return EXIT_CLEAN

    # --- 5. Tolerate absent forcing_functions block ---
    ff = state.get("forcing_functions")
    if not ff or not isinstance(ff, dict):
        sys.stderr.write(
            "forcing_functions block absent from constitute.json; "
            "skipping verify-design-tokens\n"
        )
        return EXIT_CLEAN

    # --- 6. Tolerate absent rule block ---
    rule_cfg = ff.get(_RULE_KEY)
    if not rule_cfg or not isinstance(rule_cfg, dict):
        sys.stderr.write(
            "forcing_functions.{rule} not configured; "
            "skipping verify-design-tokens\n".format(rule=_RULE_KEY)
        )
        return EXIT_CLEAN

    # --- 7. Check enabled flag ---
    if not rule_cfg.get("enabled", False):
        return EXIT_CLEAN

    # --- 8. Read allowlist_paths (default []) ---
    allowlist_globs = rule_cfg.get("allowlist_paths", [])  # type: List[str]
    if not isinstance(allowlist_globs, list):
        allowlist_globs = []

    # --- 9. Load optional token source (CSS) ---
    defined_tokens = set()  # type: Set[str]
    token_source_css = rule_cfg.get("token_source_css")
    if token_source_css:
        # Resolve relative to root
        css_full = str(root / token_source_css)
        defined_tokens = _load_token_source(css_full)
        # Exclude the token source file from the component scan — it IS the token
        # source (definitions live there), not a component consuming tokens.
        # Both the bare relative path and a **-prefixed pattern are added so
        # fnmatch covers top-level and nested locations.
        _excl = token_source_css.replace("\\", "/")
        allowlist_globs = list(allowlist_globs) + [_excl, "**/" + _excl.lstrip("/")]

    # --- 10. Scan ---
    findings = scan_for_design_token_violations(
        root=root,
        allowlist_globs=allowlist_globs,
        defined_tokens=defined_tokens,
    )

    # --- 11. Emit findings ---
    return emit_findings(_RULE_KEY, findings)
