"""Schema constants — enums, regexes, mandatory-reads tables, render labels."""

from __future__ import annotations

import re
from typing import Dict, Tuple

STATE_FILE_NAME = "specify-state.json"

# Hard-gate prereqs (mirrors discover_helper / research_helper). The
# SPECIFY-REDESIGN-PLAN.md Prerequisites table cites `manifest.json` /
# `project-config.json`, but the shipped /init-forge writes
# `.devforge/init.yaml` and /configure writes `.devforge/configure.yaml`
# (project-config.json is a downstream render). Matching the existing
# helpers — single source of truth.
PREFLIGHT_PREREQS: Tuple[Tuple[str, str], ...] = (
    (".devforge/init.yaml", "/init-forge"),
    ("docs/architecture.md", "/generate-docs"),
    (".devforge/configure.yaml", "/configure"),
    ("constitution.md", "/constitute"),
)

# Constitution populate-guard literal (v3 verbatim).
CONSTITUTION_POPULATE_GUARD = "_Run /constitute to populate_"

# Phase 1 — source_origin enum (auto-tagged from file path).
SOURCE_ORIGIN_ENUM: Tuple[str, ...] = (
    "discover", "research", "prior_spec", "context",
)

# Spec status lifecycle (v3 verbatim).
SPEC_STATUS_ENUM: Tuple[str, ...] = (
    "Draft", "Approved", "In Progress", "Complete",
)
SPEC_STATUS_DEFAULT = "Draft"

# Spec type — v3's 4 + v3.1 greenfield.
SPEC_TYPE_ENUM: Tuple[str, ...] = (
    "migration_tooling", "feature_addition", "bug_fix", "refactor",
    "greenfield_feature",
)

# Phase 1.5 — Variance rule #5 finding-landing tracker.
LANDED_IN_ENUM: Tuple[str, ...] = (
    "AC", "Constraint", "OOS", "Risk", "unlanded",
)
LANDED_IN_DEFAULT = "unlanded"

# Phase 2 — decision-point categories (v3 verbatim, locked order).
DP_CATEGORY_ENUM: Tuple[str, ...] = (
    "scope_boundaries", "existing_behavior", "data_flow_state",
    "edge_cases", "ui_ux_details", "breaking_changes",
    "tooling_configuration",
)
DP_STATUS_ENUM: Tuple[str, ...] = (
    "pending", "answered", "default_applied",
    "deferred_OOS", "deferred_open_question",
    "no_DP_in_category",
)
DP_COVERAGE_STATE_ENUM: Tuple[str, ...] = (
    "Clear", "Partial", "Missing", "NoDPInCategory",
)
DP_TURN_CAP = 3

# Phase 4 — AC subsection enum (v3 verbatim, locked order: 5.1 → 5.7).
AC_SUBSECTION_ENUM: Tuple[str, ...] = (
    "tooling_artifact_presence",  # 5.1
    "behavior_preservation",      # 5.2
    "behavior_change",            # 5.3
    "ci_pipeline",                # 5.4
    "hooks_gates",                # 5.5
    "documentation",              # 5.6
    "hygiene",                    # 5.7
)
AC_UBIQUITOUS_ONLY_SUBSECTIONS: Tuple[str, ...] = (
    "tooling_artifact_presence", "hygiene",
)

# EARS notation variants (Kiro / IEEE 29148-2018; Variance rule #10).
EARS_VARIANT_ENUM: Tuple[str, ...] = (
    "ubiquitous", "event_driven", "state_driven", "optional", "unwanted",
)
EARS_REGEX: Dict[str, "re.Pattern[str]"] = {
    "ubiquitous":   re.compile(r"^The [^.]+ shall [^.]+\.$"),
    "event_driven": re.compile(r"^WHEN [^,]+,? the [^.]+ shall [^.]+\.$"),
    "state_driven": re.compile(r"^WHILE [^,]+,? the [^.]+ shall [^.]+\.$"),
    "optional":     re.compile(r"^WHERE [^,]+,? the [^.]+ shall [^.]+\.$"),
    "unwanted":     re.compile(r"^IF [^,]+, THEN the [^.]+ shall [^.]+\.$"),
}

CONFLICT_TYPE_ENUM: Tuple[str, ...] = ("direct", "drift", "refinement")

LIKELIHOOD_ENUM: Tuple[str, ...] = ("Low", "Med", "High")
IMPACT_ENUM: Tuple[str, ...] = ("Low", "Med", "High")

CONSTRAINT_KIND_ENUM: Tuple[str, ...] = (
    "follow",
    "not_break",
    "nfr",
    "constitution_anchor",
    "external_system",
)

AUTO_MODE_ENV_VAR = "DEVFORGE_AUTO_MODE"
AUTO_MODE_REMINDER_SUBSTRINGS: Tuple[str, ...] = (
    "auto mode is active", "auto mode still active",
)

FEATURE_NAME_RE: "re.Pattern[str]" = re.compile(
    r"^[a-z][a-z0-9]*(?:-[a-z0-9]+){1,3}$"
)
SPECS_ROOT_DEFAULT = "specs"
SPEC_NUMBER_WIDTH = 3
SPEC_NUMBER_DIR_RE = re.compile(r"^(\d{3})-")

SUBSECTION_HEADING_BY_KEY: Dict[str, Tuple[str, str]] = {
    "tooling_artifact_presence": ("5.1", "Tooling / artifact presence and absence"),
    "behavior_preservation":     ("5.2", "Behavior preservation"),
    "behavior_change":           ("5.3", "Behavior change"),
    "ci_pipeline":               ("5.4", "CI / pipeline"),
    "hooks_gates":               ("5.5", "Hooks / gates"),
    "documentation":             ("5.6", "Documentation"),
    "hygiene":                   ("5.7", "Hygiene"),
}

AC_FRAMING_LINE = (
    "Each AC must be testable and unambiguous. **Cover each category "
    "that applies. Mark non-applicable categories with \"N/A — [reason]\".**"
)

COVERAGE_RULE_BANNER = (
    "**Coverage rule (v3)**: For each Phase 1.5 finding, the finding "
    "either (a) becomes an AC in §5, (b) becomes a Constraint in §7, "
    "(c) is explicitly listed here as out of scope, OR (d) is in §9 "
    "Risks with documented mitigation. Unlanded finding = hard error — "
    "re-verify Phase 1.5 enumeration is complete before saving."
)

CONSTRAINT_KIND_LABEL: Dict[str, str] = {
    "follow":              "Must follow",
    "not_break":           "Must not break",
    "nfr":                 "Must satisfy NFR",
    "constitution_anchor": "Must follow constitution",
    "external_system":     "Must integrate with external system",
}

CONSTRAINT_KIND_REQUIRED_FLAGS: Dict[str, Tuple[str, ...]] = {
    "follow":              (),
    "not_break":           (),
    "nfr":                 ("quantifier",),
    "constitution_anchor": ("constitution_ref",),
    "external_system":     (),
}

NFR_NUMERIC_THRESHOLD_RE: "re.Pattern[str]" = re.compile(
    r"\d+\s*(ms|s|sec|min|hr|users?|req/s|rps|qps|tps|GB|MB|KB|TB|%|\$|connections?|rows?|records?)\b",
    re.IGNORECASE,
)
NFR_VAGUE_BLOCKLIST: frozenset = frozenset({
    "high", "low", "fast", "slow", "scalable", "good", "acceptable",
    "reasonable", "robust", "performant", "efficient", "secure", "reliable",
})
NFR_NAMED_CLASS_RE: "re.Pattern[str]" = re.compile(
    r"\b(PCI-DSS|SOC\s*2|ISO\s*\d{4,5}|GDPR|HIPAA|FedRAMP|FIPS|NIST)\b",
    re.IGNORECASE,
)

NUMERIC_DIGIT_NOUN_RE: "re.Pattern[str]" = re.compile(
    r"\b(\d+)\s+([a-zA-Z]+)\b"
)
NUMERIC_HEADING_RE: "re.Pattern[str]" = re.compile(r"^\s*#+\s")
NUMERIC_TABLE_SEP_RE: "re.Pattern[str]" = re.compile(
    r"^\s*\|[-:|\s]+\|\s*$"
)

CONSTITUTION_RULE_RE: "re.Pattern[str]" = re.compile(
    r"\b(MUST\s+NOT|MUST|SHALL\s+NOT|SHALL)\b", re.IGNORECASE,
)
CONSTITUTION_STOPWORDS: frozenset = frozenset({
    "the", "and", "or", "of", "to", "in", "on", "for", "with", "by",
    "not", "this", "that", "must", "shall", "will", "do", "does",
    "any", "all", "no", "yes", "than", "then", "from", "into", "are",
    "is", "be", "been", "have", "has", "had", "what", "when", "where",
    "which", "who", "why", "how", "as", "at", "an", "a", "it", "its",
    "if", "but", "so", "such", "may", "can", "could", "should", "would",
})

RESOLUTION_PHASE_ENUM: Tuple[str, ...] = ("plan", "breakdown")

# Mandatory base reads — every project must have these regardless of topic.
PHASE1_MANDATORY_READS: Tuple[str, ...] = (
    "constitution.md",
    ".claude/memory/MEMORY.md",
    "CLAUDE.md",
    "docs/architecture.md",
)

# Deferral-kind argument enum.
DP_DEFERRAL_KIND_ENUM: Tuple[str, ...] = ("OOS", "open_question")
_DEFERRAL_KIND_TO_STATUS: Dict[str, str] = {
    "OOS": "deferred_OOS",
    "open_question": "deferred_open_question",
}
DP_TURN_CAP_REASON = "exceeded follow-up cap"

_DP_CLEAR_STATUSES: Tuple[str, ...] = (
    "answered", "default_applied", "deferred_OOS", "deferred_open_question",
)

# Mandatory-read slot table (per spec_type).
MANDATORY_READS_BY_TYPE: Dict[str, Tuple[Tuple[str, str], ...]] = {
    "migration_tooling": (
        ("package.json", "Root package.json"),
        (".github/workflows/*", "Every .github/workflows/ file"),
        ("**/package.json",
         "Per-package package.json with peer/deps/workspace links"),
        (".husky/*", "Husky hook configs (.husky/)"),
        (".pre-commit-config.yaml", "pre-commit config"),
        (".lefthook.yml", "lefthook config"),
        ("lerna.json", "lerna monorepo config"),
        ("turbo.json", "turbo monorepo config"),
        ("nx.json", "nx monorepo config"),
        ("pnpm-workspace.yaml", "pnpm workspace config"),
        ("rush.json", "rush monorepo config"),
        ("*lock*", "Lockfiles (note presence/size only)"),
        (".npmrc", "Root .npmrc"),
        (".yarnrc", "Root .yarnrc"),
        (".pnpmrc", "Root .pnpmrc"),
    ),
    "feature_addition": (
        ("__entry__", "Root component/entry files (router, store, app init)"),
        ("__similar_feature__",
         "Most-similar existing feature (via grep)"),
        ("__type_defs__", "Type defs for affected entities"),
        ("__api_ops__", "API/GraphQL ops for affected resources"),
        ("__test_files__", "Test files for affected area"),
    ),
    "bug_fix": (
        ("__buggy_files__", "The buggy file(s) named in request"),
        ("__direct_deps__", "Direct deps of buggy file"),
        ("__direct_callers__", "Direct callers (via grep)"),
        ("__recent_git_log__", "Recent git log on buggy file (git log -5)"),
    ),
    "refactor": (
        ("__refactored_files__", "The file(s) being refactored"),
        ("__all_callers__", "All callers (via grep)"),
        ("__all_tests__", "All tests for refactored code"),
    ),
    "greenfield_feature": (
        ("constitution.md#scaffolding-guide",
         "Constitution Section 7 (Scaffolding Guide)"),
        ("__framework_docs__",
         "Framework docs via WebSearch for feature pattern"),
        (".claude/memory/MEMORY.md",
         "MEMORY.md prior-feature lessons"),
        ("discover/*.md",
         "/discover reference md (if Phase 1 adapter loaded one)"),
    ),
}

# Helper-owned render-group order for findings.
_RENDER_SECTION_ORDER: Tuple[str, ...] = (
    "constitution.md",
    ".claude/memory/MEMORY.md",
    "research/",
    "discover/",
    "CLAUDE.md",
    "docs/",
    "specs/",
)

# Phase 5 subsection render order.
_SUBSECTION_RENDER_ORDER: Tuple[str, ...] = (
    "5.1", "5.2", "5.3", "5.4", "5.5", "5.6", "5.7",
)
