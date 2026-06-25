"""_source.py — design-source parser and check-design-source CLI verb.

A feature declares its design source in specs/NNN-<slug>/spec.md frontmatter
as a **Design source**: line.  The value is shaped `scheme:target` where
scheme ∈ {html, figma, screenshot}, or the literal "none".

check-design-source reads that line and emits a loud NON-BLOCKING WARN on
stderr (exit 0) when a non-file design source is declared but no enforceable
local design/reference.html exists — so teams using Figma/URL/screenshot are
no longer silently un-enforced.  The remedy is to convert the design to
design/reference.html so the plan-40 apparatus engages.

Parsing rules (parse_design_source):
  - Split on the FIRST colon only (figma/URL targets contain ':' in https://).
  - The literal "none" (no colon, case-insensitive after strip) →
    DesignSource(scheme="none", target="", raw=value, valid=True).
  - Empty/whitespace-only value → treat as "none" (valid=True, scheme="none").
  - A recognized scheme (html/figma/screenshot) with a non-empty target →
    valid=True.
  - Unknown scheme, or recognized scheme with empty target → valid=False.
  - "none:" or "none:<target>" → valid=False.  SYNC contract: "none" is a bare
    sentinel and cannot take a colon/target; _validate_design_source in
    _specify/_cmds_phase4_setters.py enforces the same rule — keep in lockstep.
  - raw always preserves the original stripped value.

Regex note: uses [ \\t]* (horizontal whitespace only), NOT \\s*.  \\s* would
bleed across a blank line and capture a value from the next non-empty line in
a malformed spec (e.g. "**Design source**:\\n\\nfigma:..." would wrongly
yield "figma:...").  The IMPORTANT comment in breakdown_helper.py:166-170
explains this trap for _STATUS_PATTERN; we apply the same guard here.
"""

from __future__ import annotations

import collections
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Schema constants (mirrored from _specify/_schema.py for decoupled import)
# ---------------------------------------------------------------------------

# SYNC: keep these in lockstep with DESIGN_SOURCE_SCHEME_ENUM in
# _specify/_schema.py — duplicated (not imported) because the design_helper
# shim loads _design as a top-level package, so a cross-subpackage import
# (from .._specify._schema or from _specify._schema) is not safe here.
_KNOWN_SCHEMES = frozenset(["html", "figma", "screenshot", "none"])

# ---------------------------------------------------------------------------
# DesignSource namedtuple
# ---------------------------------------------------------------------------

DesignSource = collections.namedtuple("DesignSource", ["scheme", "target", "raw", "valid"])

# ---------------------------------------------------------------------------
# Frontmatter regex — mirrors _STATUS_PATTERN in breakdown_helper.py:171.
# MULTILINE so ^ anchors to line starts within the file text.
# [ \t]* (horizontal whitespace only) prevents cross-line bleed.
# ---------------------------------------------------------------------------

_DESIGN_SOURCE_PATTERN = re.compile(
    r"^\*\*Design source\*\*:[ \t]*(.+)$", re.MULTILINE
)


# ---------------------------------------------------------------------------
# Public: parse_design_source
# ---------------------------------------------------------------------------


def parse_design_source(value):
    # type: (str) -> DesignSource
    """Parse a raw **Design source**: field value into a DesignSource.

    Args:
        value: the raw field value string (may be empty/whitespace).

    Returns:
        DesignSource(scheme, target, raw, valid) namedtuple.
        - scheme: the part before the first ':', or 'none' for bare 'none'.
        - target: everything after the first ':', or '' for 'none'/empty.
        - raw: the stripped input value (preserved regardless of validity).
        - valid: True when the value is well-formed, False otherwise.
    """
    stripped = value.strip() if value else ""

    # Empty / whitespace-only → treat as "none"
    if not stripped:
        return DesignSource(scheme="none", target="", raw=stripped, valid=True)

    # Bare "none" (case-insensitive)
    if stripped.lower() == "none":
        return DesignSource(scheme="none", target="", raw=stripped, valid=True)

    # Split on FIRST colon only — preserves https:// and other colons in target
    if ":" not in stripped:
        # Has content but no colon and is not "none" → unknown / malformed
        return DesignSource(scheme=stripped, target="", raw=stripped, valid=False)

    scheme, target = stripped.split(":", 1)
    scheme = scheme.strip()
    # Strip target: a user who writes "html: design/reference.html" (space after
    # the colon) gets the correct path.  Strip is safe for URLs too —
    # 'https://figma.com/...'.strip() is idempotent; no URL legitimately starts
    # or ends with whitespace.  The FIRST-COLON split is what preserves internal
    # colons (e.g. https:// in the target), not leaving target unstripped.
    target = target.strip()

    # Unknown scheme → invalid
    if scheme not in _KNOWN_SCHEMES:
        return DesignSource(scheme=scheme, target=target, raw=stripped, valid=False)

    # Known scheme "none" with a colon is malformed.
    # SYNC contract: none is valid ONLY as the bare sentinel (no colon).
    # "none:" (empty target) and "none:<anything>" are both invalid because the
    # colon signals a scheme:target parse — the bare sentinel path exits above
    # before reaching this split.  Accepting "none:" here diverged from the
    # setter (_validate_design_source), which rejects both forms.
    if scheme == "none":
        return DesignSource(scheme="none", target=target, raw=stripped, valid=False)

    # Recognized non-none scheme: require non-empty target
    if not target:
        return DesignSource(scheme=scheme, target="", raw=stripped, valid=False)

    return DesignSource(scheme=scheme, target=target, raw=stripped, valid=True)


# ---------------------------------------------------------------------------
# Internal: _emit_warn
# ---------------------------------------------------------------------------


def _emit_warn(lines):
    # type: (list) -> None
    """Write a WARN block to stderr.  lines = list of strings (no newline)."""
    for line in lines:
        sys.stderr.write(line + "\n")


# ---------------------------------------------------------------------------
# Public: cmd_check_design_source (CLI handler)
# ---------------------------------------------------------------------------


def cmd_check_design_source(args):
    # type: (object) -> int
    """CLI handler for check-design-source.

    Reads the spec file at args.spec, extracts the **Design source**: line,
    and emits a NON-BLOCKING WARN to stderr (exit 0) when the declared source
    is non-file (figma/screenshot) and no design/reference.html is present, or
    when the value is malformed.

    Always returns 0 — non-blocking by design (mirrors verify-scope-coherence
    in _cmds_phase4_verify.py).  Missing/unreadable spec → silent return 0
    (back-compat: undeclared features are silent).
    """
    spec_path = getattr(args, "spec", None)
    workspace_root = getattr(args, "workspace_root", ".")

    # --- read spec file ---
    if not spec_path:
        # No spec provided — silently succeed (back-compat)
        return 0

    try:
        with open(spec_path, "r", encoding="utf-8") as fh:
            spec_text = fh.read()
    except (OSError, IOError):
        # Unreadable / absent spec → silent, back-compat
        return 0

    # --- extract Design source line ---
    m = _DESIGN_SOURCE_PATTERN.search(spec_text)
    if not m:
        # No **Design source**: line → treat as "none", silent
        return 0

    raw_value = m.group(1).strip()
    ds = parse_design_source(raw_value)

    # --- resolve workspace root ---
    root = Path(workspace_root)
    reference_present = (root / "design" / "reference.html").is_file()

    # --- decision tree ---
    if not ds.valid:
        # Malformed value → WARN
        _emit_warn([
            "check-design-source: malformed design_source value (non-blocking — review and fix):",
            "  - malformed design_source value: {0}".format(ds.raw),
            "  remedy: use one of the valid shapes: html:<path> | figma:<url> | screenshot:<path> | none",
        ])
        return 0

    if ds.scheme == "none":
        # Explicitly declared none or empty → silent
        return 0

    if ds.scheme in ("figma", "screenshot"):
        if reference_present:
            # Team already has a local reference; apparatus engages on it — silent
            return 0
        # Non-file source, no enforceable reference → WARN
        _emit_warn([
            "check-design-source: design source declared but no enforceable design/reference.html (non-blocking — review and convert):",
            "  - declared: {0}".format(ds.raw),
            "  - design/reference.html: absent",
            "  remedy: export the {0} design to design/reference.html so the plan-40 design-fidelity gates engage; until then visual drift is unenforced for this feature.".format(ds.scheme),
        ])
        return 0

    if ds.scheme == "html":
        html_target_present = (root / ds.target).is_file()
        if html_target_present:
            return 0
        # Declared an html source file that doesn't exist → WARN
        # Use ds.target (the actual declared path) — NOT a hardcoded fallback —
        # so the message names the file the user actually declared.
        _emit_warn([
            "check-design-source: declared html design source file is absent (non-blocking — review and fix):",
            "  - declared: {0}".format(ds.raw),
            "  - {0}: absent".format(ds.target),
            "  remedy: create {0}, or update the **Design source**: line; the plan-40 design-fidelity gates require the target to be design/reference.html.".format(ds.target),
        ])
        return 0

    # Fallback — should not be reached for valid known schemes, but be safe
    return 0
