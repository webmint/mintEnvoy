"""hotspot_schema -- dataclass schema for the /audit hotspot mode artefact.

Single source of truth for the shape of the hotspot scoring result produced by
``audit_helper`` when invoked with ``--top N`` (hotspot mode).

Design notes:

- Dataclasses are pure records. No serialization (to_dict / from_dict),
  no rendering, no I/O. Those responsibilities live in the helper command
  layer so this schema stays small and independently testable.

- Schema-level validation runs in __post_init__ and is mechanical:
    * Required string fields are non-empty after .strip().
    * Numeric range checks for normalised (0-1) floats and ranks.
    * Bool-as-int is rejected for int fields (bool is a subclass of int;
      isinstance(x, bool) check guards churn, callers, size_loc, rank).
    * Nested HotspotResult receives isinstance checks on its list elements.

- Risk score formula (enforced by the helper layer, NOT this schema):
      score = 0.5 * churn_norm + 0.4 * callers_norm + 0.1 * size_norm
  Weights are stored in HotspotResult.weights for traceability.

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
# Allowed weights dict keys.
# ---------------------------------------------------------------------------

_WEIGHTS_KEYS = frozenset(("c", "k", "s"))

# ---------------------------------------------------------------------------
# Validation helpers.
# (Self-contained so this schema is independently importable without
# cross-dependency on other schema modules.)
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
                field_name, sorted(str(x) for x in allowed), value
            )
        )


def _require_strict_int_ge(value, minimum, field_name):
    # type: (object, int, str) -> None
    """Raise ValueError if value is not a strict int (no bool) >= minimum."""
    if isinstance(value, bool):
        raise ValueError(
            "{0} must be an int, got bool".format(field_name)
        )
    if not isinstance(value, int):
        raise ValueError(
            "{0} must be an int, got {1}".format(field_name, type(value).__name__)
        )
    if value < minimum:
        raise ValueError(
            "{0} must be >= {1}, got {2}".format(field_name, minimum, value)
        )


def _require_float_range(value, lo, hi, field_name):
    # type: (object, float, float, str) -> None
    """Raise ValueError if value is not a number (non-bool) in [lo, hi]."""
    if isinstance(value, bool):
        raise ValueError(
            "{0} must be a float, got bool".format(field_name)
        )
    if not isinstance(value, (int, float)):
        raise ValueError(
            "{0} must be a number, got {1}".format(field_name, type(value).__name__)
        )
    f = float(value)
    if not (lo <= f <= hi):
        raise ValueError(
            "{0} must be in [{1}, {2}], got {3}".format(field_name, lo, hi, value)
        )


# ---------------------------------------------------------------------------
# FileScore -- one file's risk-score record.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FileScore:
    """Risk-score record for a single file in hotspot analysis.

    file is a workspace-relative path (non-empty).
    churn is the commit count in the 90-day window (int >= 0, strict — no bool).
    callers is the CBM inbound-edge count (int >= 0, strict — no bool).
    size_loc is non-blank non-comment lines (int >= 0, strict — no bool).
    churn_norm, callers_norm, size_norm, score are floats in [0.0, 1.0].
    rank is 1-based (int >= 1, strict — no bool).
    """

    file: str
    churn: int
    callers: int
    size_loc: int
    churn_norm: float
    callers_norm: float
    size_norm: float
    score: float
    rank: int

    def __post_init__(self):
        # type: () -> None
        _require_nonempty(self.file, "FileScore.file")
        _require_strict_int_ge(self.churn, 0, "FileScore.churn")
        _require_strict_int_ge(self.callers, 0, "FileScore.callers")
        _require_strict_int_ge(self.size_loc, 0, "FileScore.size_loc")
        _require_float_range(self.churn_norm, 0.0, 1.0, "FileScore.churn_norm")
        _require_float_range(self.callers_norm, 0.0, 1.0, "FileScore.callers_norm")
        _require_float_range(self.size_norm, 0.0, 1.0, "FileScore.size_norm")
        _require_float_range(self.score, 0.0, 1.0, "FileScore.score")
        _require_strict_int_ge(self.rank, 1, "FileScore.rank")


# ---------------------------------------------------------------------------
# HotspotResult -- top-level hotspot mode result.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HotspotResult:
    """Top-level hotspot mode result produced by audit_helper --top N.

    schema_version must equal SCHEMA_VERSION.
    weights is a dict with exactly the keys "c", "k", "s" (churn, callers,
    size weights), each a float in [0, 1].
    top is the ranked top-N list of FileScore records.
    next_candidates holds positions N+1..N+10 (may be empty).
    total_files_scored is the count of all files that were scored (int >= 0).
    """

    schema_version: str
    weights: dict
    top: List[FileScore]
    next_candidates: List[FileScore]
    total_files_scored: int

    def __post_init__(self):
        # type: () -> None
        _require_nonempty(self.schema_version, "HotspotResult.schema_version")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(
                "HotspotResult.schema_version must be {0!r}, "
                "got {1!r}".format(SCHEMA_VERSION, self.schema_version)
            )

        # Validate weights dict.
        if not isinstance(self.weights, dict):
            raise ValueError(
                "HotspotResult.weights must be a dict, "
                "got {0}".format(type(self.weights).__name__)
            )
        missing = _WEIGHTS_KEYS - set(self.weights.keys())
        if missing:
            raise ValueError(
                "HotspotResult.weights is missing keys: {0}".format(sorted(missing))
            )
        extra = set(self.weights.keys()) - _WEIGHTS_KEYS
        if extra:
            raise ValueError(
                "HotspotResult.weights has unexpected keys: {0}".format(sorted(extra))
            )
        for key in ("c", "k", "s"):
            _require_float_range(
                self.weights[key], 0.0, 1.0, "HotspotResult.weights[{0!r}]".format(key)
            )

        # Validate top list.
        if not isinstance(self.top, list):
            raise ValueError("HotspotResult.top must be a list")
        for i, item in enumerate(self.top):
            if not isinstance(item, FileScore):
                raise ValueError(
                    "HotspotResult.top[{0}] must be a FileScore, "
                    "got {1}".format(i, type(item).__name__)
                )

        # Validate next_candidates list.
        if not isinstance(self.next_candidates, list):
            raise ValueError("HotspotResult.next_candidates must be a list")
        for i, item in enumerate(self.next_candidates):
            if not isinstance(item, FileScore):
                raise ValueError(
                    "HotspotResult.next_candidates[{0}] must be a FileScore, "
                    "got {1}".format(i, type(item).__name__)
                )

        _require_strict_int_ge(
            self.total_files_scored, 0, "HotspotResult.total_files_scored"
        )
