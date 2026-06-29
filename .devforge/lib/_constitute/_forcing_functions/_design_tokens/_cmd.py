"""CLI command handler for ``constitute_helper verify-design-tokens`` (plan 40 Phase 4).

Reads the ``forcing_functions.design_token_provenance`` block from
``.devforge/constitute.json``, optionally loads disposition manifests and
a spacing scale from the design helper, and scans component style sources for
provenance violations.

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

Manifest resolution (Check 5 — MATCH token binding)
----------------------------------------------------
The global config block carries ``enabled`` and ``token_source_css`` only.
The disposition manifest is PER-FEATURE (``specs/[feature]/design-manifest.json``),
so the detector resolves manifests at run time via one of two paths:

1. If ``manifest_path`` is set in the config (legacy / explicit override), that
   single file is loaded.  Back-compat: callers that already stored a path keep
   working unchanged.
2. Otherwise the detector globs ``specs/*/design-manifest.json`` under ``--root``
   and loads all found manifests.  MATCH data-refs are unioned across all of them.

Checks 1-4 (color/border literals, var-fallback, undefined-token,
interactive-state coverage) run WITHOUT any manifest (manifest-independent).
Check 5 applies only to component files whose ``data-ref`` anchors are
dispositioned MATCH in at least one loaded manifest.  When no manifests are
found (neither explicit path nor any glob hit), Check 5 is a no-op.

When ``token_source_css`` is set in the config (path to design/styles.css),
the command extracts defined tokens (--token-name patterns) and the spacing
scale from it for Checks 3 and 5's spacing sub-check (OQ-6).
When absent, Check 3 is skipped and the spacing sub-check of Check 5 is
relaxed (OQ-6: absent CSS → no spacing token to bind to).
"""

from __future__ import annotations

import argparse
import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import List, Optional, Set

from .._shared import EXIT_CLEAN, emit_findings
from ._scanner import scan_for_design_token_violations, _extract_defined_tokens


_RULE_KEY = "design_token_provenance"

# Glob pattern for per-feature design manifests (relative to root).
_MANIFEST_GLOB = "specs/*/design-manifest.json"


def _load_manifest_match_refs_from_json(manifest_path):
    # type: (str) -> Set[str]
    """Load MATCH element data-refs from a manifest JSON file.

    Parses the raw JSON directly: reads ``elements[].data_ref`` where
    ``elements[].disposition`` is ``"MATCH"`` (case-insensitive).  This is the
    sole canonical manifest parser — no external _design._schema import is
    required.  Returns empty set on any error; never raises.
    """
    try:
        with open(manifest_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        refs = set()  # type: Set[str]
        for elem in data.get("elements", []):
            if isinstance(elem, dict):
                disposition = str(elem.get("disposition", "")).upper()
                if disposition == "MATCH":
                    ref = elem.get("data_ref")
                    if ref:
                        refs.add(str(ref))
        return refs
    except Exception:  # noqa: BLE001
        sys.stderr.write(
            "verify-design-tokens: cannot load manifest {path}; "
            "Check 5 (MATCH token binding) will be skipped for this file\n".format(
                path=manifest_path
            )
        )
        return set()


def _glob_manifests(root):
    # type: (Path) -> List[Path]
    """Return all per-feature design manifest paths under root matching the glob.

    Globs ``specs/*/design-manifest.json`` relative to ``root``.
    Returns an empty list when none are found.
    """
    return sorted(root.glob(_MANIFEST_GLOB))


def _collect_match_refs(root, explicit_manifest_path):
    # type: (Path, Optional[str]) -> Set[str]
    """Union MATCH data-refs from all relevant manifests.

    Resolution order:
    1. If ``explicit_manifest_path`` is non-None (legacy config key present),
       load only that single file via the canonical raw-JSON parser.
       Back-compat: existing callers unchanged.
    2. Otherwise glob ``specs/*/design-manifest.json`` under ``root`` and
       union MATCH refs across all found manifests.

    Returns an empty set when no manifests are found or all fail to parse.
    Checks 1-4 are NOT affected by this function — they always run.
    """
    if explicit_manifest_path is not None:
        # Legacy/explicit single-manifest path: one file, raw-JSON parser.
        return _load_manifest_match_refs_from_json(str(root / explicit_manifest_path))

    # Glob-based: load all per-feature manifests and union their MATCH refs.
    manifest_paths = _glob_manifests(root)
    if not manifest_paths:
        return set()

    combined = set()  # type: Set[str]
    for mp in manifest_paths:
        combined.update(_load_manifest_match_refs_from_json(str(mp)))
    return combined


# ---------------------------------------------------------------------------
# Step 3 — circular spacing fix: reference-html-anchored spacing scope
# ---------------------------------------------------------------------------


class _DataRefFinder(HTMLParser):
    """Minimal HTML parser that collects data-ref attribute values.

    Walks the HTML token stream and records the value of every ``data-ref``
    attribute encountered.  No CSS is parsed; we only need the presence of
    ``data-ref`` anchors in the HTML file, not their visual values.
    """

    def __init__(self):
        # type: () -> None
        super(_DataRefFinder, self).__init__()
        self.refs = set()  # type: Set[str]

    def handle_starttag(self, tag, attrs):
        # type: (str, list) -> None
        for name, value in attrs:
            if name.lower() == "data-ref" and value:
                self.refs.add(value)


def _extract_reference_html_refs(html_path):
    # type: (str) -> Set[str]
    """Return the set of all data-ref anchor values present in an HTML file.

    Uses stdlib ``html.parser`` — no model call, no CSS parsing.  This is the
    ground-truth source for the spacing scope: the LLM authors the manifest
    disposition, NOT the HTML file, so an element's presence in reference.html
    is not LLM-mistaggable for this purpose.

    Returns an empty set on any read or parse error; never raises.
    """
    try:
        with open(html_path, "r", encoding="utf-8", errors="replace") as fh:
            html_text = fh.read()
    except OSError:
        return set()

    finder = _DataRefFinder()
    try:
        finder.feed(html_text)
        finder.close()
    except Exception:  # noqa: BLE001
        return set()

    return finder.refs


def _load_manifest_deviate_reason_refs_from_json(manifest_path):
    # type: (str) -> Set[str]
    """Return DEVIATE data-ref values that have a non-empty deviate_reason.

    Reads the raw manifest JSON (same approach as
    ``_load_manifest_match_refs_from_json``).  Only elements with BOTH
    ``disposition == "DEVIATE"`` (case-insensitive) AND a non-whitespace
    ``deviate_reason`` are collected.

    A DEVIATE element with an empty or absent ``deviate_reason`` is NOT
    collected — it cannot claim "intentional deviation" without recording why,
    and an LLM mistag typically produces ``deviate_reason = ""``.

    Returns empty set on any error; never raises.
    """
    try:
        with open(manifest_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        refs = set()  # type: Set[str]
        for elem in data.get("elements", []):
            if isinstance(elem, dict):
                disposition = str(elem.get("disposition", "")).upper()
                if disposition == "DEVIATE":
                    reason = str(elem.get("deviate_reason", "")).strip()
                    if reason:  # non-empty stripped reason = verifiable exemption
                        ref = elem.get("data_ref")
                        if ref:
                            refs.add(str(ref))
        return refs
    except Exception:  # noqa: BLE001
        return set()


def _collect_deviate_reason_refs(root, explicit_manifest_path):
    # type: (Path, Optional[str]) -> Set[str]
    """Union DEVIATE-with-reason data-refs from all relevant manifests.

    Resolution order mirrors ``_collect_match_refs``:
    1. If ``explicit_manifest_path`` is non-None, load only that single file.
    2. Otherwise glob ``specs/*/design-manifest.json`` under ``root``.

    Returns an empty set when no manifests are found or all fail to parse.
    """
    if explicit_manifest_path is not None:
        return _load_manifest_deviate_reason_refs_from_json(
            str(root / explicit_manifest_path)
        )

    manifest_paths = _glob_manifests(root)
    if not manifest_paths:
        return set()

    combined = set()  # type: Set[str]
    for mp in manifest_paths:
        combined.update(_load_manifest_deviate_reason_refs_from_json(str(mp)))
    return combined


def _build_spacing_scope_refs(root, explicit_manifest_path):
    # type: (Path, Optional[str]) -> Optional[Set[str]]
    """Compute the reference-html-anchored spacing scope for Check 5.

    Returns ``None`` when ``design/reference.html`` is absent — the caller
    (``cmd_verify_design_tokens``) passes ``None`` to
    ``scan_for_design_token_violations``, which preserves the pre-fix behaviour
    (spacing scope = match_refs).

    When ``design/reference.html`` exists:
    - Parses it for all data-ref anchor values (the ground truth).
    - If the HTML contains no data-ref anchors, returns ``None`` (same as
      absent reference.html) so the caller falls back to match_refs.  Returning
      an empty set would silently disable spacing checks for all elements.
    - Subtracts elements that have ``disposition == "DEVIATE"`` AND a non-empty
      ``deviate_reason`` in any loaded manifest — those represent intentional,
      verifiable deviations and are exempt.
    - Returns the resulting set.

    This breaks the circular scoping bug: a DEVIATE-mistagged element that is
    present in reference.html IS in the returned set (because ``deviate_reason``
    is empty → not exempt), so its spacing literal WILL be caught.

    Parameters
    ----------
    root:
        Consumer project root.  ``design/reference.html`` is resolved relative
        to this.
    explicit_manifest_path:
        Legacy single-manifest path from config (passed through to
        ``_collect_deviate_reason_refs``).  ``None`` → glob-based discovery.
    """
    reference_html = root / "design" / "reference.html"
    if not reference_html.exists():
        # No reference.html → no new behaviour; caller uses match_refs fallback.
        return None

    ref_html_refs = _extract_reference_html_refs(str(reference_html))
    # Empty HTML (no data-ref elements) → fall back to match_refs, same as absent
    # reference.html.  Returning set() would silently disable spacing checks for
    # ALL elements (including correctly-MATCH-dispositioned ones), because the
    # scanner's _spacing_refs would be an empty set and no element would match.
    if not ref_html_refs:
        return None

    deviate_reason_refs = _collect_deviate_reason_refs(root, explicit_manifest_path)

    # spacing_scope = all ref-html elements minus those with a verifiable reason
    return ref_html_refs - deviate_reason_refs


def _load_token_source(token_source_css):
    # type: (str) -> tuple
    """Load defined tokens and spacing scale from a CSS token source file.

    Returns (defined_tokens: Set[str], spacing_scale_available: bool).
    Returns (set(), False) on any error.
    """
    css_path = Path(token_source_css)
    if not css_path.exists():
        # OQ-6: absent CSS → relax spacing check, keep color/border checks hard
        return set(), False

    try:
        css_text = css_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        sys.stderr.write(
            "verify-design-tokens: cannot read token source {path}: {err}\n".format(
                path=token_source_css, err=exc
            )
        )
        return set(), False

    defined = _extract_defined_tokens(css_text)

    # Determine if a spacing scale is available (at least one spacing token
    # or spacing value defined).  We delegate to the design_helper's
    # extract_spacing_scale for this.
    spacing_available = False
    try:
        import sys as _sys
        lib_root = str(Path(__file__).parent.parent.parent.parent.parent)
        if lib_root not in _sys.path:
            _sys.path.insert(0, lib_root)
        from _design._manifest import extract_spacing_scale  # type: ignore
        result = extract_spacing_scale(token_source_css)
        spacing_available = result.get("available", False) and bool(
            result.get("scale", [])
        )
    except Exception:  # noqa: BLE001
        # Graceful fallback: if extract_spacing_scale is unavailable, use
        # whether we found any token definitions as a proxy.
        spacing_available = bool(defined)

    return defined, spacing_available


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
    spacing_scale_available = False
    token_source_css = rule_cfg.get("token_source_css")
    if token_source_css:
        # Resolve relative to root
        css_full = str(root / token_source_css)
        defined_tokens, spacing_scale_available = _load_token_source(css_full)
        # Exclude the token source file from the component scan — it IS the token
        # source (definitions live there), not a component consuming tokens.
        # Both the bare relative path and a **-prefixed pattern are added so
        # fnmatch covers top-level and nested locations.
        _excl = token_source_css.replace("\\", "/")
        allowlist_globs = list(allowlist_globs) + [_excl, "**/" + _excl.lstrip("/")]

    # --- 10. Resolve disposition manifests ---
    # Global config carries only {enabled, token_source_css}; the manifest is
    # PER-FEATURE (specs/[feature]/design-manifest.json).  Resolution:
    #   - manifest_path in config → legacy single-path (back-compat).
    #   - manifest_path absent   → glob specs/*/design-manifest.json at runtime.
    # Checks 1-4 always run; Check 5 is a no-op when match_refs is empty.
    explicit_manifest = rule_cfg.get("manifest_path") or None  # None if absent/empty
    match_refs = _collect_match_refs(root, explicit_manifest)

    # --- 10.5 Build reference-anchored spacing scope (Step 3 — circular fix) ---
    # When design/reference.html exists, the spacing sub-check of Check 5 uses
    # a scope derived from the HTML file (LLM-unmistaggable) rather than solely
    # from the manifest MATCH disposition.  When reference.html is absent,
    # spacing_scope_refs is None and the scanner falls back to match_refs,
    # preserving the pre-fix behaviour unchanged.
    spacing_scope_refs = _build_spacing_scope_refs(root, explicit_manifest)

    # --- 11. Scan ---
    findings = scan_for_design_token_violations(
        root=root,
        allowlist_globs=allowlist_globs,
        defined_tokens=defined_tokens,
        match_refs=match_refs,
        spacing_scale_available=spacing_scale_available,
        spacing_scope_refs=spacing_scope_refs,
    )

    # --- 12. Emit findings ---
    return emit_findings(_RULE_KEY, findings)
