"""report_schema -- audit-specific top-level report container.

Holds ``AuditReport`` and the ``MODE_ENUM`` it validates against.
These are /audit-specific constructs and live here (inside ``_audit/``)
so that ``_shared/findings_schema.py`` can remain free of any dependency on
``_audit/``.

``AuditReport`` carries the full audit session result:
  * roster-agnostic fields (findings, consensus, scope) from ``_shared``
  * hotspot-specific field (next_candidates: List[FileScore]) from this
    package's own ``hotspot_schema``

Import graph is one-way:
    _shared.findings_schema  ←  _audit.report_schema  ←  _audit._cli / _audit._report

Design notes match ``_shared/findings_schema.py``:
  - Pure dataclass record; no serialization or I/O.
  - __post_init__ runs mechanical validation.
  - Type-hint convention: explicit typing.Optional / List
    (no PEP 604 X | None, no PEP 585 list[str]). Targets Python 3.8+.
  - from __future__ import annotations intentionally NOT used.

Stdlib only. No third-party dependencies.
"""

from dataclasses import dataclass
from typing import List

from _shared.findings_schema import (  # type: ignore[import]
    Finding,
    SCHEMA_VERSION,
    _require_nonempty,
    _require_in_enum,
)
from _audit.hotspot_schema import FileScore  # type: ignore[import]

# ---------------------------------------------------------------------------
# Audit mode enum.
# ---------------------------------------------------------------------------

MODE_ENUM = ("narrow", "hotspot", "broad")

# ---------------------------------------------------------------------------
# AuditReport -- top-level audit report record.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuditReport:
    """Top-level audit report record.

    schema_version must equal SCHEMA_VERSION (from findings_schema).
    audit_date is "YYYY-MM-DD" (non-empty; format not strictly validated).
    mode must be one of MODE_ENUM: "narrow", "hotspot", "broad".
    scope_description is a non-empty string describing what was audited.
    scope_files, agents_run, agents_skipped, top10, recurring_issues_resolved,
    and recurring_issues_unresolved are lists of strings (may be empty).
    findings is a list of Finding instances (may be empty).
    consensus is a dict mapping finding_id to a list of agent name strings.
    next_candidates is a list of FileScore instances (hotspot mode only;
    empty otherwise).
    """

    schema_version: str
    audit_date: str
    mode: str
    scope_description: str
    scope_files: List[str]
    agents_run: List[str]
    agents_skipped: List[str]
    findings: List[Finding]
    consensus: dict
    top10: List[str]
    recurring_issues_resolved: List[str]
    recurring_issues_unresolved: List[str]
    next_candidates: List[FileScore]

    def __post_init__(self):
        # type: () -> None
        _require_nonempty(self.schema_version, "AuditReport.schema_version")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(
                "AuditReport.schema_version must be {0!r}, "
                "got {1!r}".format(SCHEMA_VERSION, self.schema_version)
            )

        _require_nonempty(self.audit_date, "AuditReport.audit_date")
        _require_in_enum(self.mode, MODE_ENUM, "AuditReport.mode")
        _require_nonempty(self.scope_description, "AuditReport.scope_description")

        # String-list fields.
        for fname in (
            "scope_files",
            "agents_run",
            "agents_skipped",
            "top10",
            "recurring_issues_resolved",
            "recurring_issues_unresolved",
        ):
            val = getattr(self, fname)
            if not isinstance(val, list):
                raise ValueError(
                    "AuditReport.{0} must be a list".format(fname)
                )
            for i, elem in enumerate(val):
                if not isinstance(elem, str):
                    raise ValueError(
                        "AuditReport.{0}[{1}] must be a str, "
                        "got {2}".format(fname, i, type(elem).__name__)
                    )

        # findings: list of Finding instances.
        if not isinstance(self.findings, list):
            raise ValueError("AuditReport.findings must be a list")
        for i, item in enumerate(self.findings):
            if not isinstance(item, Finding):
                raise ValueError(
                    "AuditReport.findings[{0}] must be a Finding, "
                    "got {1}".format(i, type(item).__name__)
                )

        # consensus: dict.
        if not isinstance(self.consensus, dict):
            raise ValueError(
                "AuditReport.consensus must be a dict, "
                "got {0}".format(type(self.consensus).__name__)
            )

        # next_candidates: list of FileScore instances.
        if not isinstance(self.next_candidates, list):
            raise ValueError("AuditReport.next_candidates must be a list")
        for i, item in enumerate(self.next_candidates):
            if not isinstance(item, FileScore):
                raise ValueError(
                    "AuditReport.next_candidates[{0}] must be a FileScore, "
                    "got {1}".format(i, type(item).__name__)
                )
