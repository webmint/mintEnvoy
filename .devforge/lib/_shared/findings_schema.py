"""findings_schema -- roster-agnostic finding schema for /audit and /review.

Provides the ``Finding`` dataclass, ``SEVERITY_ENUM``, and ``CATEGORY_ENUM``
shared by every command that needs to store or consume individual code-review
findings (``/audit``, ``/review``, and the engine modules that feed them).

Design notes:

- Dataclasses are pure records. No serialization (to_dict / from_dict),
  no rendering, no I/O. Those responsibilities live in the helper command
  layer so this schema stays small and independently testable.

- Schema-level validation runs in __post_init__ and is mechanical:
    * Required string fields are non-empty after .strip().
    * Finding.severity is validated against SEVERITY_ENUM.
    * Finding.category is validated against CATEGORY_ENUM.
    * Finding.line: int (no bool), -1 is accepted as "unspecified" sentinel,
      otherwise must be >= 1; 0 and other negatives are rejected.
    * Finding.references may be an empty list.

- This module has NO dependency on ``_audit/``. Audit-specific containers
  (``AuditReport``, ``MODE_ENUM``) live in ``_audit/report_schema.py``, which
  depends on this module, not the reverse.

- Type-hint convention: explicit typing.Optional / List
  (no PEP 604 X | None, no PEP 585 list[str]). Targets Python 3.8+.
  from __future__ import annotations intentionally NOT used so
  __post_init__ introspection sees real type objects.

Stdlib only. No third-party dependencies.
"""

from dataclasses import dataclass
from typing import List

# ---------------------------------------------------------------------------
# Schema version constant.
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "1"

# ---------------------------------------------------------------------------
# Allowed enum values.
# ---------------------------------------------------------------------------

SEVERITY_ENUM = ("Critical", "High", "Medium", "Info")
CATEGORY_ENUM = (
    "mislogic",
    "system_design",
    "best_practice",
    "duplication",
    "security",
    "blind_spot",
)

# ---------------------------------------------------------------------------
# Validation helpers.
# (Self-contained so this schema is independently importable.)
# ---------------------------------------------------------------------------


def _require_nonempty(value, field_name):
    # type: (object, str) -> None
    """Raise ValueError if value is not a non-empty (post-strip) string."""
    if not isinstance(value, str):
        raise ValueError(
            "{0} must be a string, got {1}".format(field_name, type(value).__name__)
        )
    if value.strip() == "":
        raise ValueError("{0} must be a non-empty string".format(field_name))


def _require_in_enum(value, allowed, field_name):
    # type: (object, tuple, str) -> None
    """Raise ValueError if value is not in allowed."""
    if value not in allowed:
        raise ValueError(
            "{0} must be one of {1}, got {2!r}".format(
                field_name, list(allowed), value
            )
        )


# ---------------------------------------------------------------------------
# Finding -- one audit finding record.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """One adversarial audit finding.

    finding_id is a non-empty identifier (e.g. "F-001").
    agent is the producing agent name; the roster is NOT validated here --
    only non-empty is required.
    severity must be one of SEVERITY_ENUM: "Critical", "High", "Medium", "Info".
    file is a non-empty path string.
    line is 1-based. -1 is accepted as the "unspecified" sentinel.
    0 and all other negative values are rejected.
    title, explanation, suggested_fix, source_pass are non-empty strings.
    references is a list of strings (may be empty).
    category must be one of CATEGORY_ENUM; defaults to 'mislogic'.
    pass_count is a strict int (no bool) >= 1; defaults to 1 (single-pass).
    Multi-pass runs set pass_count via the merger (_merge.merge_passes).
    """

    finding_id: str
    agent: str
    severity: str
    file: str
    line: int
    title: str
    explanation: str
    suggested_fix: str
    references: List[str]
    source_pass: str
    category: str = "mislogic"
    pass_count: int = 1

    def __post_init__(self):
        # type: () -> None
        _require_nonempty(self.finding_id, "Finding.finding_id")
        _require_nonempty(self.agent, "Finding.agent")
        _require_in_enum(self.severity, SEVERITY_ENUM, "Finding.severity")
        _require_in_enum(self.category, CATEGORY_ENUM, "Finding.category")
        _require_nonempty(self.file, "Finding.file")

        # line: strict int (no bool), -1 sentinel or >= 1.
        if isinstance(self.line, bool):
            raise ValueError(
                "Finding.line must be an int, got bool"
            )
        if not isinstance(self.line, int):
            raise ValueError(
                "Finding.line must be an int, got {0}".format(
                    type(self.line).__name__
                )
            )
        if self.line != -1 and self.line < 1:
            raise ValueError(
                "Finding.line must be -1 (unspecified) or >= 1, got {0}".format(
                    self.line
                )
            )

        _require_nonempty(self.title, "Finding.title")
        _require_nonempty(self.explanation, "Finding.explanation")
        _require_nonempty(self.suggested_fix, "Finding.suggested_fix")

        if not isinstance(self.references, list):
            raise ValueError("Finding.references must be a list")
        for i, ref in enumerate(self.references):
            if not isinstance(ref, str):
                raise ValueError(
                    "Finding.references[{0}] must be a str, "
                    "got {1}".format(i, type(ref).__name__)
                )

        _require_nonempty(self.source_pass, "Finding.source_pass")

        # pass_count: strict int (no bool), >= 1.
        if isinstance(self.pass_count, bool):
            raise ValueError(
                "Finding.pass_count must be an int, got bool"
            )
        if not isinstance(self.pass_count, int):
            raise ValueError(
                "Finding.pass_count must be an int, got {0}".format(
                    type(self.pass_count).__name__
                )
            )
        if self.pass_count < 1:
            raise ValueError(
                "Finding.pass_count must be >= 1, got {0}".format(
                    self.pass_count
                )
            )
