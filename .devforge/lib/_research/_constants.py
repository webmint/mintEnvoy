"""Schema constants — single source of truth for research_helper.

All module-level enums, defaults, and the preflight prereq list.
Imported by sibling modules; carries no code, just data.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Schema constants — single source of truth.
# ---------------------------------------------------------------------------

MEMO_FILE_NAME = "research-state.json"
REPORT_FILE_NAME = "research-report.json"

# Phase 0 rubric — 6 dimensions, neutral over bug vs enhancement. Locked
# order: this is the order symptom-coverage emits, render uses, and tests
# verify.
RUBRIC_DIMENSIONS = (
    "symptom",
    "affected_area",
    "repro_or_current",
    "desired",
    "scope",
    "unchanged_behavior",
)

# Per-dimension state machine. Helper transitions Missing→Partial→Clear
# as setters fire; "Partial" is reached when a dimension has a value but
# the bounded-turn cap (TURN_CAP) has been hit without explicit Clear.
RUBRIC_STATE_ENUM = ("Clear", "Partial", "Missing")
RUBRIC_STATE_DEFAULT = "Missing"

# Bounded follow-ups per dimension. Plan §"Bounded turns": 2 follow-ups
# per dimension (lighter than /discover's 3). After cap, dimension logs
# as Partial.
TURN_CAP = 2

# Mode enum (auto-detected from symptom tokens or user-set via override).
MODE_ENUM = ("bug", "enhancement")

# Confidence enum (Phase 1).
CONFIDENCE_ENUM = ("Confirmed", "Hypothesis", "Speculative")

# Verdict enum, mode-aware. Helper `set-verdict` enforces value ∈
# verdicts-allowed-for-current-mode; non-zero exit on mismatch.
VERDICT_ENUM = {
    "bug": (
        "Root cause confirmed",
        "Root cause hypothesis (needs repro)",
        "Multiple plausible causes",
    ),
    "enhancement": (
        "Feasible",
        "Feasible with caveats",
        "Not Recommended",
    ),
}

# Verdict subset that allows proceeding to /specify — next-step text emits
# only on these values.
VERDICT_PROCEEDING = {
    "bug": {"Root cause confirmed", "Root cause hypothesis (needs repro)"},
    "enhancement": {"Feasible", "Feasible with caveats"},
}

# Complexity rating enum (used in 3 sub-fields: codebase_changes, risk,
# verify_cost).
COMPLEXITY_ENUM = ("Low", "Med", "High")

# Confidence-vs-primary enum for runner-up framing.
CONFIDENCE_VS_PRIMARY_ENUM = ("lower", "comparable", "higher")

# Framing tag enum for findings.
FRAMING_ENUM = ("primary", "runner-up")

# Conflict type enum (Phase 0 misalignment detection).
CONFLICT_TYPE_ENUM = ("direct", "drift", "refinement", "mode-flip")

# Hard-gate prerequisites checked by `preflight` subcommand. Tuple of
# (relative-path-from-install-root, label). Order matters for stderr
# enumeration. constitution.md lives at install-root; the rest under
# .devforge/ + docs/.
PREFLIGHT_PREREQS = (
    (".devforge/init.yaml", "/init-forge"),
    ("docs/architecture.md", "/generate-docs"),
    (".devforge/configure.yaml", "/configure"),
    ("constitution.md", "/constitute"),
)
