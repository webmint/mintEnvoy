"""generate_docs_schema — dataclass schema for the /generate-docs command.

Single source of truth for the doc-artifact records the LLM populates and
the helper renders. Imported by `generate_docs_helper.py` (the renderer +
validator) and by the schema's own test module. Independent of every
other helper in this directory.

Design notes:

- Dataclasses are pure records. No serialization (`to_dict` /
  `from_dict`), no rendering (`to_markdown`), no I/O. Those responsibilities
  live in `generate_docs_helper.py` so the schema stays small, importable,
  and testable in isolation.

- Schema-level validation runs in `__post_init__` and is mechanical only:
    * required string fields are non-empty after `.strip()`
    * `Literal` enum values are checked against an explicit allow-tuple
      (Python's `Literal` is a type-checker hint, not a runtime
      constraint, so we must enforce it ourselves)
    * `SourceCite.start` / `.end` line-range invariants

- Schema-level validation does NOT cover:
    * `cite.file` exists on disk
    * `code.snippet` matches the cited line range verbatim in the source
    * `ArchitectureDoc.architecture_shape` is one of the values from
      the `architecture_shape` closed enum (defined by a future Track A
      step — see `GENERATE-DOCS-PLAN.md` Schema section + Phase 4 for
      the closed-enum list). Kept in the helper because the enum lives
      next to the detection logic that produces it.
    * `Dependency(kind="internal")` resolves to a registered package
    * Any other cross-record invariant
  These belong in `generate_docs_helper.py`'s validator pass; the schema
  is per-record only.

- Declaration order: `SourceCite` and `CodeBlock` come first because many
  other dataclasses embed them. `Pattern`, `Layer`, `DepEdge`, `Decision`
  are declared before `ArchitectureDoc` so its field types resolve
  without forward-string references.

- Type-hint convention: explicit `typing.Optional` / `List` / `Dict` /
  `Literal` (no PEP 604 `X | None`, no PEP 585 `list[str]`). Targets
  Python 3.8+. `from __future__ import annotations` is intentionally
  NOT used so `__post_init__` introspection sees real type objects.

Stdlib only. No third-party dependencies.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Literal enums.
#
# Python's `typing.Literal` is a hint to type-checkers and is NOT enforced
# at runtime. We mirror each Literal with a tuple-form allow-list and call
# `_require_in_enum` from `__post_init__` so invalid values raise on
# construction.
# ---------------------------------------------------------------------------

EXPORT_KINDS: Tuple[str, ...] = (
    "function",
    "class",
    "type",
    "constant",
    "config",
    "schema",
    "command",
    "component",
    "directive",
    "plugin",
    "other",
)

DEPENDENCY_KINDS: Tuple[str, ...] = ("internal", "external")

HAZARD_CATEGORIES: Tuple[str, ...] = (
    "naming",
    "performance",
    "type-safety",
    "duplication",
    "inconsistency",
    "v1-v2-coexistence",
    "complexity",
)

ANNOTATION_CONFIDENCE_VALUES: Tuple[str, ...] = (
    "extracted",
    "inferred",
    "ambiguous",
)


# ---------------------------------------------------------------------------
# Validation helpers.
# ---------------------------------------------------------------------------


def _require_nonempty(value, field_name):
    """Raise ValueError if `value` is not a non-empty (post-strip) string."""
    if not isinstance(value, str):
        raise ValueError(
            f"{field_name} must be a string, got {type(value).__name__}"
        )
    if value.strip() == "":
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_in_enum(value, allowed, field_name):
    """Raise ValueError if `value` is not one of `allowed` (a tuple of strings)."""
    if value not in allowed:
        raise ValueError(
            f"{field_name} must be one of {list(allowed)}, got {value!r}"
        )


# ---------------------------------------------------------------------------
# Citation primitives — embedded by most other records.
# ---------------------------------------------------------------------------


@dataclass
class SourceCite:
    """A `<file>:<start>-<end>` source reference.

    `file` is relative to the project root. `start` and `end` are
    1-indexed line numbers; `start == end` is a valid single-line cite.
    """

    file: str
    start: int
    end: int

    def __post_init__(self):
        _require_nonempty(self.file, "SourceCite.file")
        if not isinstance(self.start, int) or isinstance(self.start, bool):
            raise ValueError("SourceCite.start must be an int")
        if not isinstance(self.end, int) or isinstance(self.end, bool):
            raise ValueError("SourceCite.end must be an int")
        if self.start < 1:
            raise ValueError(
                f"SourceCite.start must be >= 1, got {self.start}"
            )
        if self.end < self.start:
            raise ValueError(
                f"SourceCite.end ({self.end}) must be >= "
                f"SourceCite.start ({self.start})"
            )


@dataclass
class CodeBlock:
    """A code snippet lifted verbatim from source with citation.

    The `snippet` is intended to match `cite`'s line range exactly. The
    schema only checks non-emptiness; verbatim-match is enforced by
    `generate_docs_helper.py` against the on-disk file at validation time.
    """

    language: str
    snippet: str
    cite: SourceCite

    def __post_init__(self):
        _require_nonempty(self.language, "CodeBlock.language")
        _require_nonempty(self.snippet, "CodeBlock.snippet")
        if not isinstance(self.cite, SourceCite):
            raise ValueError(
                "CodeBlock.cite must be a SourceCite, got "
                f"{type(self.cite).__name__}"
            )


# ---------------------------------------------------------------------------
# Per-package records.
# ---------------------------------------------------------------------------


@dataclass
class Export:
    """One exported symbol of a package or concern."""

    name: str
    kind: str  # one of EXPORT_KINDS
    signature: Optional[str]
    description: str
    code: CodeBlock

    def __post_init__(self):
        _require_nonempty(self.name, "Export.name")
        _require_in_enum(self.kind, EXPORT_KINDS, "Export.kind")
        _require_nonempty(self.description, "Export.description")
        if self.signature is not None and not isinstance(self.signature, str):
            raise ValueError(
                "Export.signature must be a string or None, got "
                f"{type(self.signature).__name__}"
            )
        if not isinstance(self.code, CodeBlock):
            raise ValueError(
                "Export.code must be a CodeBlock, got "
                f"{type(self.code).__name__}"
            )


@dataclass
class Dependency:
    """One dependency edge from a package or concern."""

    name: str
    kind: str  # one of DEPENDENCY_KINDS
    version: Optional[str]
    purpose: str
    consumer_locations: List[str] = field(default_factory=list)

    def __post_init__(self):
        _require_nonempty(self.name, "Dependency.name")
        _require_in_enum(self.kind, DEPENDENCY_KINDS, "Dependency.kind")
        _require_nonempty(self.purpose, "Dependency.purpose")
        if self.version is not None and not isinstance(self.version, str):
            raise ValueError(
                "Dependency.version must be a string or None, got "
                f"{type(self.version).__name__}"
            )
        if not isinstance(self.consumer_locations, list):
            raise ValueError(
                "Dependency.consumer_locations must be a list, got "
                f"{type(self.consumer_locations).__name__}"
            )


@dataclass
class Hazard:
    """One adverse pattern observed in a package or concern."""

    category: str  # one of HAZARD_CATEGORIES
    description: str
    cite: Optional[SourceCite]

    def __post_init__(self):
        _require_in_enum(self.category, HAZARD_CATEGORIES, "Hazard.category")
        _require_nonempty(self.description, "Hazard.description")
        if self.cite is not None and not isinstance(self.cite, SourceCite):
            raise ValueError(
                "Hazard.cite must be a SourceCite or None, got "
                f"{type(self.cite).__name__}"
            )


@dataclass
class PackageDoc:
    """Top-level package doc record."""

    name: str
    path: str
    overview: str
    directory_tree: str
    primary_language: str
    framework: Optional[str]
    build_tool: Optional[str]
    scripts: Dict[str, str] = field(default_factory=dict)
    # Lists default to [] for ergonomic incremental construction;
    # generate_docs_helper.py's validate-* subcommands enforce non-empty where required.
    exports: List[Export] = field(default_factory=list)
    dependencies: List[Dependency] = field(default_factory=list)
    hazards: List[Hazard] = field(default_factory=list)
    usage_example: Optional[CodeBlock] = None
    consumer_pattern: Optional[CodeBlock] = None

    def __post_init__(self):
        _require_nonempty(self.name, "PackageDoc.name")
        _require_nonempty(self.path, "PackageDoc.path")
        _require_nonempty(self.overview, "PackageDoc.overview")
        _require_nonempty(self.directory_tree, "PackageDoc.directory_tree")
        _require_nonempty(self.primary_language, "PackageDoc.primary_language")
        if self.framework is not None and not isinstance(self.framework, str):
            raise ValueError(
                "PackageDoc.framework must be a string or None, got "
                f"{type(self.framework).__name__}"
            )
        if self.build_tool is not None and not isinstance(self.build_tool, str):
            raise ValueError(
                "PackageDoc.build_tool must be a string or None, got "
                f"{type(self.build_tool).__name__}"
            )
        if not isinstance(self.scripts, dict):
            raise ValueError("PackageDoc.scripts must be a dict")
        if not isinstance(self.exports, list):
            raise ValueError("PackageDoc.exports must be a list")
        if not isinstance(self.dependencies, list):
            raise ValueError("PackageDoc.dependencies must be a list")
        if not isinstance(self.hazards, list):
            raise ValueError("PackageDoc.hazards must be a list")
        if self.usage_example is not None and not isinstance(
            self.usage_example, CodeBlock
        ):
            raise ValueError(
                "PackageDoc.usage_example must be a CodeBlock or None"
            )
        if self.consumer_pattern is not None and not isinstance(
            self.consumer_pattern, CodeBlock
        ):
            raise ValueError(
                "PackageDoc.consumer_pattern must be a CodeBlock or None"
            )


@dataclass
class ConcernDoc:
    """A concern-level doc nested inside a package.

    Note: at the concern level the export list is rendered as
    "Public Surface" rather than "Main Exports". The data shape is the
    same `List[Export]`; the heading change is the helper's job.
    """

    package_path: str
    concern_name: str
    overview: str
    directory_tree: str
    # Lists default to [] for ergonomic incremental construction;
    # generate_docs_helper.py's validate-* subcommands enforce non-empty where required.
    public_surface: List[Export] = field(default_factory=list)
    types: List[CodeBlock] = field(default_factory=list)
    dependencies: List[Dependency] = field(default_factory=list)
    hazards: List[Hazard] = field(default_factory=list)
    usage_example: Optional[CodeBlock] = None

    def __post_init__(self):
        _require_nonempty(self.package_path, "ConcernDoc.package_path")
        _require_nonempty(self.concern_name, "ConcernDoc.concern_name")
        _require_nonempty(self.overview, "ConcernDoc.overview")
        _require_nonempty(self.directory_tree, "ConcernDoc.directory_tree")
        if not isinstance(self.public_surface, list):
            raise ValueError("ConcernDoc.public_surface must be a list")
        if not isinstance(self.types, list):
            raise ValueError("ConcernDoc.types must be a list")
        if not isinstance(self.dependencies, list):
            raise ValueError("ConcernDoc.dependencies must be a list")
        if not isinstance(self.hazards, list):
            raise ValueError("ConcernDoc.hazards must be a list")
        if self.usage_example is not None and not isinstance(
            self.usage_example, CodeBlock
        ):
            raise ValueError(
                "ConcernDoc.usage_example must be a CodeBlock or None"
            )


# ---------------------------------------------------------------------------
# Architecture records.
#
# Pattern / Layer / DepEdge / Decision are declared before ArchitectureDoc
# so its field types resolve without string forward references.
# ---------------------------------------------------------------------------


@dataclass
class Pattern:
    """A recurring code/design pattern observed across the workspace."""

    name: str
    description: str
    applies_in: List[str] = field(default_factory=list)
    evidence: List[SourceCite] = field(default_factory=list)

    def __post_init__(self):
        _require_nonempty(self.name, "Pattern.name")
        _require_nonempty(self.description, "Pattern.description")
        if not isinstance(self.applies_in, list):
            raise ValueError("Pattern.applies_in must be a list")
        if not isinstance(self.evidence, list):
            raise ValueError("Pattern.evidence must be a list")


@dataclass
class Layer:
    """A logical layer in the workspace's architecture."""

    name: str
    description: str
    sample_packages: List[str] = field(default_factory=list)

    def __post_init__(self):
        _require_nonempty(self.name, "Layer.name")
        _require_nonempty(self.description, "Layer.description")
        if not isinstance(self.sample_packages, list):
            raise ValueError("Layer.sample_packages must be a list")


@dataclass
class DepEdge:
    """One cross-package dependency edge."""

    from_pkg: str
    to_pkg: str
    reason: str

    def __post_init__(self):
        _require_nonempty(self.from_pkg, "DepEdge.from_pkg")
        _require_nonempty(self.to_pkg, "DepEdge.to_pkg")
        _require_nonempty(self.reason, "DepEdge.reason")


@dataclass
class Decision:
    """One architectural decision with rationale and evidence."""

    title: str
    rationale: str
    evidence: List[SourceCite] = field(default_factory=list)

    def __post_init__(self):
        _require_nonempty(self.title, "Decision.title")
        _require_nonempty(self.rationale, "Decision.rationale")
        if not isinstance(self.evidence, list):
            raise ValueError("Decision.evidence must be a list")


@dataclass
class ArchitectureDoc:
    """Workspace-level architecture doc record.

    `architecture_shape` is checked only for non-emptiness here. The
    closed-enum check (against the `architecture_shape` closed enum
    defined by a future Track A step — see `GENERATE-DOCS-PLAN.md`
    Schema section + Phase 4 for the closed-enum list) lives in
    `generate_docs_helper.py` so the enum stays next to the detection
    logic that produces it.
    """

    project_name: str
    architecture_shape: str
    # Lists default to [] for ergonomic incremental construction;
    # generate_docs_helper.py's validate-* subcommands enforce non-empty where required.
    patterns: List[Pattern] = field(default_factory=list)
    layers: List[Layer] = field(default_factory=list)
    cross_package_deps: List[DepEdge] = field(default_factory=list)
    decisions: List[Decision] = field(default_factory=list)

    def __post_init__(self):
        _require_nonempty(self.project_name, "ArchitectureDoc.project_name")
        _require_nonempty(
            self.architecture_shape, "ArchitectureDoc.architecture_shape"
        )
        if not isinstance(self.patterns, list):
            raise ValueError("ArchitectureDoc.patterns must be a list")
        if not isinstance(self.layers, list):
            raise ValueError("ArchitectureDoc.layers must be a list")
        if not isinstance(self.cross_package_deps, list):
            raise ValueError("ArchitectureDoc.cross_package_deps must be a list")
        if not isinstance(self.decisions, list):
            raise ValueError("ArchitectureDoc.decisions must be a list")


# ---------------------------------------------------------------------------
# Memory record.
# ---------------------------------------------------------------------------


@dataclass
class MemoryFinding:
    """One memory-worthy observation produced by /generate-docs.

    `unit` is either a package path (e.g. `packages/api`) or the literal
    string `workspace` for cross-cutting findings. The schema only checks
    non-emptiness; the package-path-vs-`workspace` distinction is left
    to the helper validator.
    """

    category: str  # one of HAZARD_CATEGORIES
    unit: str
    observation: str
    cite: Optional[SourceCite] = None

    def __post_init__(self):
        _require_in_enum(
            self.category, HAZARD_CATEGORIES, "MemoryFinding.category"
        )
        _require_nonempty(self.unit, "MemoryFinding.unit")
        _require_nonempty(self.observation, "MemoryFinding.observation")
        if self.cite is not None and not isinstance(self.cite, SourceCite):
            raise ValueError(
                "MemoryFinding.cite must be a SourceCite or None, got "
                f"{type(self.cite).__name__}"
            )
