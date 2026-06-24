"""_schema.py — disposition manifest schema for design_helper.

Defines the data shapes, validation helpers, and serialization for the
per-element design-disposition manifest.  The manifest is the required
pre-code intake artifact that classifies every element of reference.html
before any implementation code is written (plan 40 Phase 2).

Shape overview
--------------
DispositionEnum — the four valid dispositions (MATCH / DEFER-EMPTY /
  STATIC-PLACEHOLDER / DEVIATE).

ElementRecord — one classified element:
  data_ref    str   — required; the data-ref anchor id from reference.html
                      (OQ-5: anchors required, fuzzy matching rejected).
  disposition str   — one of DispositionEnum values, or "" (unclassified).
  deviate_reason str — required (non-empty) when disposition == "DEVIATE";
                       empty string otherwise.

ManifestContainer — the full manifest:
  version       str       — schema version string "1"
  reference_html str      — path to the reference HTML file
  elements      list[ElementRecord]   — the classified elements
  gap_list      list[str] — unresolvable classes/tokens from resolve-reference

Validation helpers
------------------
validate_element(rec) -> list[str]        — per-element validation errors
validate_manifest(container) -> list[str] — full-manifest validation errors
  (empty list = valid)

Serialization
-------------
element_to_dict(rec) -> dict
element_from_dict(d)  -> ElementRecord
manifest_to_dict(container) -> dict
manifest_from_dict(d)  -> ManifestContainer

Design notes
------------
- stdlib only; Python 3.8+
- No third-party deps
- helper-owns-shape: callers supply values; this module owns structure/validation
- Control characters (< 0x20) are rejected at set-time in string fields to
  prevent silent YAML/JSON corruption (audit anti-pattern #1).
"""

from __future__ import annotations

import json
from typing import List, Optional

# ---------------------------------------------------------------------------
# Disposition enum
# ---------------------------------------------------------------------------

DISPOSITION_MATCH = "MATCH"
DISPOSITION_DEFER_EMPTY = "DEFER-EMPTY"
DISPOSITION_STATIC_PLACEHOLDER = "STATIC-PLACEHOLDER"
DISPOSITION_DEVIATE = "DEVIATE"
DISPOSITION_UNCLASSIFIED = ""  # sentinel for "not yet classified"

VALID_DISPOSITIONS = frozenset(
    [
        DISPOSITION_MATCH,
        DISPOSITION_DEFER_EMPTY,
        DISPOSITION_STATIC_PLACEHOLDER,
        DISPOSITION_DEVIATE,
    ]
)

SCHEMA_VERSION = "1"


# ---------------------------------------------------------------------------
# Control-character guard (audit anti-pattern #1)
# ---------------------------------------------------------------------------


def _has_control_chars(s):
    # type: (str) -> bool
    """Return True if s contains a control character (< 0x20 except tab)."""
    for ch in s:
        code = ord(ch)
        if code < 0x20 and code != 0x09:  # allow tab
            return True
    return False


def _require_clean_string(value, field_name):
    # type: (str, str) -> Optional[str]
    """Return an error string if value contains control chars; None if clean."""
    if not isinstance(value, str):
        return "{0}: expected str, got {1}".format(field_name, type(value).__name__)
    if _has_control_chars(value):
        return "{0}: contains control characters".format(field_name)
    return None


# ---------------------------------------------------------------------------
# ElementRecord
# ---------------------------------------------------------------------------


class ElementRecord(object):
    """One classified element from reference.html."""

    __slots__ = ("data_ref", "disposition", "deviate_reason")

    def __init__(self, data_ref, disposition="", deviate_reason=""):
        # type: (str, str, str) -> None
        self.data_ref = data_ref          # type: str
        self.disposition = disposition    # type: str
        self.deviate_reason = deviate_reason  # type: str


def validate_element(rec):
    # type: (ElementRecord) -> List[str]
    """Validate a single ElementRecord.  Returns a list of error strings (empty = ok)."""
    errors = []  # type: List[str]

    # --- data_ref ---
    err = _require_clean_string(rec.data_ref, "data_ref")
    if err:
        errors.append(err)
    elif not rec.data_ref.strip():
        errors.append("data_ref: must be non-empty")

    # --- disposition ---
    if rec.disposition == DISPOSITION_UNCLASSIFIED:
        errors.append(
            "element '{0}': disposition is unclassified (must be one of {1})".format(
                rec.data_ref, ", ".join(sorted(VALID_DISPOSITIONS))
            )
        )
    elif rec.disposition not in VALID_DISPOSITIONS:
        errors.append(
            "element '{0}': invalid disposition '{1}' (must be one of {2})".format(
                rec.data_ref,
                rec.disposition,
                ", ".join(sorted(VALID_DISPOSITIONS)),
            )
        )

    # --- deviate_reason ---
    err = _require_clean_string(rec.deviate_reason, "deviate_reason")
    if err:
        errors.append("element '{0}': {1}".format(rec.data_ref, err))
    elif rec.disposition == DISPOSITION_DEVIATE and not rec.deviate_reason.strip():
        errors.append(
            "element '{0}': disposition is DEVIATE but deviate_reason is empty".format(
                rec.data_ref
            )
        )
    elif rec.disposition != DISPOSITION_DEVIATE and rec.deviate_reason:
        # Non-DEVIATE element should not carry a reason (warn, not error).
        # We treat this as an informational issue; validation still passes.
        pass

    return errors


# ---------------------------------------------------------------------------
# ManifestContainer
# ---------------------------------------------------------------------------


class ManifestContainer(object):
    """The full per-feature disposition manifest."""

    __slots__ = ("version", "reference_html", "elements", "gap_list")

    def __init__(self, reference_html, elements=None, gap_list=None):
        # type: (str, Optional[List[ElementRecord]], Optional[List[str]]) -> None
        self.version = SCHEMA_VERSION         # type: str
        self.reference_html = reference_html  # type: str
        self.elements = elements or []        # type: List[ElementRecord]
        self.gap_list = gap_list or []        # type: List[str]


def validate_manifest(container):
    # type: (ManifestContainer) -> List[str]
    """Validate the full manifest.

    Returns a list of error strings (empty list = valid / exit 0).

    Validation rules (plan 40 D4):
    1. reference_html must be non-empty.
    2. Every element must pass validate_element (unclassified → fail naming the element).
    3. gap_list must be empty (non-empty gap-list → fail naming each token/class).
    """
    errors = []  # type: List[str]

    # Rule 1: reference path
    if not container.reference_html or not container.reference_html.strip():
        errors.append("manifest: reference_html is empty")

    # Rule 2: per-element validation
    for rec in container.elements:
        errors.extend(validate_element(rec))

    # Rule 3: gap-list must be empty
    for token in container.gap_list:
        errors.append(
            "gap-list: unresolvable class/token '{0}' — "
            "supply the missing artifact or record a DEVIATE entry".format(token)
        )

    return errors


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def element_to_dict(rec):
    # type: (ElementRecord) -> dict
    """Serialize an ElementRecord to a JSON-safe dict."""
    d = {
        "data_ref": rec.data_ref,
        "disposition": rec.disposition,
    }
    if rec.deviate_reason:
        d["deviate_reason"] = rec.deviate_reason
    return d


def element_from_dict(d):
    # type: (dict) -> ElementRecord
    """Deserialize an ElementRecord from a dict (e.g. parsed from JSON)."""
    return ElementRecord(
        data_ref=d.get("data_ref", ""),
        disposition=d.get("disposition", ""),
        deviate_reason=d.get("deviate_reason", ""),
    )


def manifest_to_dict(container):
    # type: (ManifestContainer) -> dict
    """Serialize a ManifestContainer to a JSON-safe dict."""
    return {
        "version": container.version,
        "reference_html": container.reference_html,
        "elements": [element_to_dict(e) for e in container.elements],
        "gap_list": list(container.gap_list),
    }


def manifest_from_dict(d):
    # type: (dict) -> ManifestContainer
    """Deserialize a ManifestContainer from a dict (e.g. parsed from JSON)."""
    elements = [element_from_dict(e) for e in d.get("elements", [])]
    return ManifestContainer(
        reference_html=d.get("reference_html", ""),
        elements=elements,
        gap_list=list(d.get("gap_list", [])),
    )


def manifest_to_json(container, indent=2):
    # type: (ManifestContainer, int) -> str
    """Serialize a ManifestContainer to a JSON string."""
    return json.dumps(manifest_to_dict(container), indent=indent, sort_keys=True)


def manifest_from_json(text):
    # type: (str) -> ManifestContainer
    """Deserialize a ManifestContainer from a JSON string."""
    return manifest_from_dict(json.loads(text))
