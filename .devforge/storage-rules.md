# Storage Rules — Specs, Plans, Tasks, and Docs

These rules define how all development artifacts are organized. All commands MUST follow them.

## Directory Structure

```
bugs/
  NNN-short-description.md           # Bug reports (report-bug or verify triage)

research/
  YYYY-MM-DD-[topic-slug].md          # Research reports (research) — bug/enhancement against existing code

discover/
  YYYY-MM-DD-[topic-slug].md          # Discovery reports (discover) — greenfield feature, pre-/specify

audits/
  YYYY-MM-DD-audit.md                  # Adversarial codebase audits (audit) — periodic, dated, not auto-committed
  .gitignore                           # Auto-created on first audit run (excludes .tmp-* files)

specs/
  NNN-feature-name/                # One numbered directory per feature
    spec.md                        # Feature specification (specify)
    plan.md                        # Technical implementation plan (plan)
    research.md                    # Research findings (plan) — optional
    data-model.md                  # Entity definitions (plan) — optional
    contracts.md                   # API contracts (plan) — optional
    handoff.json                   # specify→plan structured handoff (specify)
    plan-handoff.json              # plan→breakdown structured handoff (plan)
    breakdown-handoff.json         # breakdown→implement structured handoff (breakdown)
    tasks/                         # Task breakdown (breakdown)
      001-short-task-title.md      # Individual task files
      002-short-task-title.md
      003-short-task-title.md

docs/
  overview.md                      # Project overview + package map (project tier)
  architecture.md                  # Cross-package architecture + layering rationale (project tier)
  glossary.md                      # CBM-augmented project glossary (project tier; Phase B)
  <package>/                       # One subdir per package detected by /init-forge
    overview.md                    # Package role + concern enumeration
    architecture.md                # Package layers + patterns
    <concern>/                     # One subdir per src/ subfolder concern
      index.md                     # Concern: Purpose + Structure (annotated tree) + Hazards
```

NOTE: legacy layout (`docs/features/`, `docs/api/`, `docs/guides/`) is dropped.
Structural information (exports, types, deps, public-surface, call chains) is
NOT pre-rendered into docs/ — query the codebase-memory-mcp graph live via
`search_graph`, `trace_path`, `get_code_snippet`, `search_code`,
`query_graph`. Md files carry the narrative + judgment layer; CBM carries
the structural-query layer.

`docs/glossary.md` is the project-tier consolidated glossary produced by
Phase B of `/generate-docs` — 30-150 entries classified by CBM presence
(code-anchored: exact name match in graph; fuzzy-anchored: BM25 hit; prose-
only: no graph match) with 1-2 sentence definitions and cite-back paths.
Validator-enforced shape (term unique case-insensitive, definition ≤280 chars
single paragraph, cite_md_paths ≥1 each on disk, code/fuzzy-anchored
snippet must resolve via CBM, prose-only ≥2 cite_md_paths, related_terms
must reference other entries, aliases_to_avoid optional list of banned
synonyms guarded against self-reference / in-list dup / cross-entry
collision with another entry's canonical term, count 30..150). Concern-tier Purpose paragraphs
still carry inline term disambiguation; this file is the project-tier
consolidation, not a replacement.

## Naming Rules

### Feature Directories

- **Format**: `NNN-feature-name` where NNN is a zero-padded sequential number
- Scan existing `specs/` directories to determine the next number
- Examples: `001-user-auth`, `002-cart-pricing`, `003-order-history`
- Feature name part: lowercase kebab-case, 2-4 words

### Task Files

- **Format**: `NNN-short-task-title.md` where NNN is a zero-padded sequential number within the feature
- Numbers are sequential within the feature: 001, 002, 003...
- Title part: lowercase kebab-case, concise description of the task
- Examples: `001-define-types.md`, `002-create-repository.md`, `003-build-form-component.md`

### How to Determine Next Feature Number

1. List all directories in `specs/`
2. Extract the highest NNN prefix
3. Next feature = highest + 1 (or 001 if empty)

## Task File Format

Each task file (`specs/NNN-feature/tasks/NNN-title.md`) contains:

```markdown
# Task NNN: [Title]

**Feature**: [feature directory name]
**Agent**: [assigned agent name]
**Status**: Pending | In Progress | Complete | Skipped
**Depends on**: [task numbers] or None
**Blocks**: [task numbers] or None
**Spec criteria**: AC-[numbers]
**Review checkpoint**: Yes/No
**Context docs**: [doc file paths] or None

## Files

| File   | Action        | Description    |
| ------ | ------------- | -------------- |
| [path] | Create/Modify | [what changes] |

## Description

[Detailed description of what to do]

## Change Details

- In `path/to/file`:
  - [specific change]
- In `path/to/other`:
  - [specific change]

## Contracts

### Expects (checked before execution)

- [precondition: what must be true in the codebase before this task runs]

### Produces (checked after execution)

- [postcondition: what must be true in the codebase after this task completes]

## Done When

- [ ] [Testable condition specific to this task]
- [ ] [Another task-specific condition]
- [ ] No debug artifacts left in changed files
- [ ] Type checker passes on changed files (see Development Commands section)
- [ ] Linter passes on changed files (see Development Commands section)
- [ ] No new secrets or credentials in code

## Completion Notes

[Filled in by /implement after completion]
**Completed**: [date/time]
**Files changed**: [actual files]
**Contract**: Expects [X/Y verified] | Produces [X/Y verified]
**Notes**: [deviations or observations]
```

## File Lifecycle

```
research     → displays report in console, optionally saves to research/YYYY-MM-DD-[topic-slug].md
discover     → displays report in console, optionally saves to discover/YYYY-MM-DD-[topic-slug].md
specify      → creates specs/NNN-name/spec.md
plan         → creates specs/NNN-name/plan.md (+ research.md, data-model.md, contracts.md if needed)
breakdown    → creates specs/NNN-name/tasks/001-xxx.md, 002-xxx.md, ... + specs/NNN-name/breakdown-handoff.json (machine contract for /implement; task .md files stay human-readable)
implement    → updates individual task file status + completion notes
review       → creates specs/NNN-name/review.md (emergent cross-task findings; findings only, no verdict)
verify       → updates specs/NNN-name/spec.md status to Complete; Phase 9 triage may create bugs/NNN-xxx.md
summarize    → creates specs/NNN-name/summary.md (PR-ready feature summary)
finalize     → squashes WIP commits + surgical docs/ updates via tech-writer
report-bug   → creates bugs/NNN-description.md
fix          → writes a [WIP] commit in the source repo (no spec/bugs/ files written)
audit        → creates audits/YYYY-MM-DD-audit.md (dated, not overwritten; standalone, not in workflow chain)
```

## Status Tracking

### Spec Status (in spec.md header)

- `Draft` — initial creation, not yet approved
- `Approved` — user approved, ready for plan command
- `In Progress` — tasks are being executed
- `Complete` — all acceptance criteria verified

### Plan Status (in plan.md header)

- `Draft` — initial creation
- `Approved` — user approved, ready for breakdown

### Task Status (in each task file header)

- `Pending` — not yet started
- `In Progress` — currently being executed
- `Complete` — done and verified
- `Skipped` — `/implement` gate skip path: the task was not executed (its working-tree edits were reset). Counts as satisfied for downstream dependency resolution.

## Cross-Referencing

- Every plan.md MUST reference its spec
- Every task file MUST reference which acceptance criteria (AC-N) it addresses
- Task dependencies reference other task numbers within the same feature
- The verify command reads the spec and all task files to cross-check

## Documentation Rules

### Audience

Docs/ are LLM context source first, dev-greppable second. Density and structure are optimized for LLM consumption (compact, parseable, cite-backed); humans grep them as a side benefit.

### File Naming

- Tier files use fixed names: `overview.md`, `architecture.md`
- Concern dirs use the source-subfolder name verbatim (e.g., `docs/<package>/order/index.md` for `<package>/src/order/`)
- Package dirs mirror the package's index.json key (e.g., `docs/module/apps/app/`)

### When Docs Are Generated

- /generate-docs (Plan F) walks all tiers bottom-up: concerns → packages → project
- Incremental: each doc carries `source_stamp` in frontmatter; helper skips regeneration when the stamp matches the current source-subfolder content hash
- Manual `--full` flag forces regeneration of everything

### Doc Structure (LLM-first density format)

Every doc opens with YAML-subset frontmatter, then fixed section anchors.

**Concern doc** (`docs/<package>/<concern>/index.md`):

````markdown
---
concern: <name>
package: <package-path>
files: <count>
source_stamp: <sha256-prefix>
last_indexed: <YYYY-MM-DD>
---

# <concern>

## Purpose

<1-2 sentences; no preamble>

## Structure

```text
<ASCII tree of files in subfolder; each leaf annotated `  # <≤60 chars>`>
```
````

````

**Package architecture** (`docs/<package>/architecture.md`): `## Layers` + `## Patterns` sections, each entry cite-backed.

**Package overview** (`docs/<package>/overview.md`): `## Purpose` + `## Concerns` (list with cite-backs to concern dirs).

**Project overview/architecture** (`docs/overview.md`, `docs/architecture.md`): same shape as package tier but at project scope; package list / cross-package layers.

### Density rules (validate-doc enforces)
- Banned phrases: "This document...", "In this section...", "We will...", "various", "several", "many", "some", "other"
- Per-bullet length cap: ≤200 chars (Layers/Patterns/Concerns/Packages/Cross-Cuts); Structure annotations: ≤60 chars
- Concern docs ship `## Purpose` + `## Structure` only (Hazards moved to `/audit`; Glossary tier dropped — Purpose paragraphs surface terms in context)
- No prose tables for structural data — exports/types/deps/callees lists live in CBM, NOT in md

### CBM auto-indexing
Md files are walked by `codebase-memory-mcp index_repository` automatically. Their content becomes searchable via `search_code`. No separate registration step.

### Rules
- Every cite-back must resolve at validation time (file exists, line range valid)
- Vue cite-backs (`<f>.vue:N`) are validated through the `.vue.ts.map` sourcemap chain
- Concerns are derived from `src/` subfolders enumerated by /init-forge's index.json
- `docs/api/`, `docs/features/`, `docs/guides/` are NOT generated under Plan F

## Bug Report Rules

### Directory
- Location: `bugs/` at project root (parallel to `specs/` and `docs/`)
- Each bug is a single file: `NNN-short-description.md`

### Naming
- **Format**: `NNN-short-description.md` where NNN is a zero-padded sequential number
- Scan existing `bugs/` files to determine the next number
- Description part: lowercase kebab-case, 2-4 words
- Examples: `001-null-cart-total.md`, `002-missing-auth-check.md`, `003-broken-date-format.md`

### Status Lifecycle
- `Open` — reported, not yet being fixed
- `In Progress` — currently being fixed
- `Fixed` — fix applied and verified

### Bug File Format

```markdown
# Bug NNN: [Short Title]

**Status**: Open | In Progress | Fixed
**Severity**: Critical | Warning | Info
**Source**: verify | manual
**Feature**: [spec path, e.g. specs/001-feature/spec.md — or N/A for standalone bugs]
**AC**: [AC-N — or N/A if not tied to an acceptance criterion]
**Reported**: [YYYY-MM-DD]
**Fixed**: [YYYY-MM-DD or empty]

## Description

[What is wrong — 1-3 sentences. Use behavioral description, not line numbers.]

## Expected Behavior

[What should happen — from the spec's acceptance criterion. Omit for manual bugs where this isn't known.]

## Actual Behavior

[What actually happens — from verification evidence or user observation. Omit for manual bugs where this isn't known.]

## File(s)

| File | Detail |
|------|--------|
| [path/to/file] | [area or function — not line numbers, they shift after other fixes] |

## Evidence

[How this was discovered — error message, verification report excerpt, user observation]

## Related Issues

[Other bugs filed in the same batch, if any. Omit if standalone.]
- bugs/NNN-xxx.md — [short title]

## Fix Notes

[Filled in after resolution — root cause, what was changed, commit reference]
````

**Field notes:**

- `Feature` and `AC` are populated by verify. report-bug sets them to N/A.
- `Expected Behavior` and `Actual Behavior` are populated by verify (from spec + verification evidence). report-bug may omit them if unknown.
- `Related Issues` is populated when multiple bugs are filed in the same batch. Helps whoever resolves the batch know what else is being addressed.
- `File(s)` should use area/function references, not line numbers — line numbers shift after other fixes are applied.

### How Bug Files Are Created

- verify Phase 9 — user requests batch bug filing for verification issues
- report-bug — standalone manual bug reporting

### How Bug Files Are Resolved

- Manual: the user edits `**Status**: Fixed` after resolving the issue (the `Open → In Progress → Fixed` lifecycle is not driven by any command)
- Re-running `/verify` re-proves the ACs against the remediated diff

## Cleanup Rules

- Do NOT delete feature directories after completion — they serve as documentation
- Do NOT modify completed specs unless explicitly asked
- Task files are permanent records of what was done and why
