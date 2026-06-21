# /onboard — Codebase Documentation Generation

You are running the onboarding process for an existing codebase. This command produces comprehensive documentation in `docs/` that serves as the **knowledge base for all agents**. Every agent reads from `docs/` before making changes; the quality and coverage of your documentation directly determines how well agents understand and work with this codebase.

This command runs once after `/setup-wizard` for brownfield projects. Re-run when the codebase changes substantially; the pre-scan check (§1.0) protects user-edited docs across re-runs.

---

## ⚠️ ITERATION MODE — APP-WEB ONLY (TEMPORARY)

**This override is in effect until removed.** The full multi-unit flow below is paused; this iteration validates output shape on a single unit before broader rollout.

For this run, `/onboard` operates in single-unit verification mode:

| Phase | Behavior |
|---|---|
| §1.0 Pre-scan baseline check | Run normally |
| §1.1 Gather project knowledge | Run normally |
| §1.2 Discover documentation units | **Override** — skip `packages[]` iteration. Hardcode unit = `apps/app` (path: `apps/app`, doc target: `docs/apps/app/index.md`). |
| §1.3 Subagent strategy | **Override** — direct mode. No subagents. Orchestrator runs Pass 2A inline. |
| Pass 2A (per-package) | Run **once** for `apps/app` only. Use the per-package subagent prompt as your own instruction set. |
| Pass 2B (architecture) | **SKIPPED** — architecture observations need cross-package signal we won't have. |
| Pass 2C (memory archaeology) | **SKIPPED** — cross-codebase pass; out of scope for single-unit verification. |
| Pass 2D (compose-onboard) | **SKIPPED** — compose's per-package-coverage gate (gate 2.1) requires every detected package to have a registration. With 25+ unregistered packages, compose would reject. Instead: after Pass 2A registers content via `add-package-doc`, run `onboard_helper status` and report the registered content verbatim to the user for shape evaluation. |

**Helper invocation in this mode:**

1. `.devforge/lib/onboard_helper add-package-doc --unit app --path apps/app --content "..." --block-count N --ref-count N`
2. `.devforge/lib/onboard_helper status`
3. Read `.devforge/.onboard-state.json` and display the registered content to the user as a fenced markdown block. Do NOT invoke `compose-onboard`. Do NOT write to `docs/`.

The user evaluates the registered content against their target shape and gives feedback. Iterate by re-invoking `add-package-doc` (re-registration overwrites) until shape is locked.

**Removing this override:** when output shape is confirmed, delete this entire `## ⚠️ ITERATION MODE` section. The full Phase 1/Phase 2 flow below resumes unchanged.

---

## CORE PRINCIPLE — COVER ALL CODE

**Every package, every meaningful source folder, every external interface gets a documentation home.** No sample-based silence. No skipping at scale. No "we'll cluster these into one file" merges that drop substance.

If the project has 23 packages, the result is 23 package docs. If it has 4 large composite packages, the result is 4 doc folders, each with sub-docs for internal concerns. The depth adapts; the coverage does not.

The docs are a **substitute for first-pass code reading**. An agent should be able to read `docs/<package>/index.md` and:
- Know what the package provides (Overview)
- See real code (lifted, not paraphrased) for every public export
- Identify "to add a new X, I touch Y" — from the doc alone
- Know the dependencies before importing
- See a real consumer pattern before writing new consumer code

…all without opening source files. Source becomes a verification step, not a discovery step.

## HELPER INVOCATION CONTRACT (load-bearing)

**You MUST register every doc through `.devforge/lib/onboard_helper`. Direct file writes to `docs/` are not part of this command's contract.**

The helper exposes 7 verbs. These are the only sanctioned doc-write paths:

| Verb | Used for | Required args |
|---|---|---|
| `set` | top-level scalar (mode = overwrite\|merge\|fresh) | `<field> --value <v>` |
| `add-package-doc` | one package's index.md | `--unit --path --content --block-count --ref-count` |
| `add-concern-doc` | one concern doc inside a package | `--unit --concern --content --block-count --ref-count` |
| `add-architecture-doc` | workspace `docs/architecture.md` | `--content --block-count --ref-count` |
| `add-memory-finding` | one observation for `.devforge/memory.md` | `--category --unit --observation` |
| `status` | machine-readable progress | (none) |
| `compose-onboard` | atomic finalization with all validation gates | (none) |

**Why this contract exists.** R5/R6 evidence shows that "produce N similar artifacts" framings activate generator-build defaults that produce mechanically-extracted, semantically-thin output. The helper's verb surface forces per-unit + per-concern dispatch (one tool call per doc) and enforces 7 validation gates at compose time:

1. Per-package coverage (every detected package has a doc).
2. Per-concern decomposition (every substantive subfolder has its own concern doc).
3. Block-count vs ref-count equality (every fenced code block has a `<!-- path/file.ext:line-range -->` reference).
4. Boilerplate-overview detector (rejects template-shape phrases like "is a documentation unit").
5. Principal-type presence (BLoC ownership requires the corresponding State type inline).
6. Type dedup within docs (each exported name appears at most once per doc).
7. Cross-link existence + sigil hygiene.

**Compose-onboard rejects non-compliant state with explicit per-error guidance.** State is preserved on rejection; you fix the registration and re-invoke compose. Bulk-script writes to `docs/` cannot satisfy these gates because the helper only knows what it's been told via verb invocations.

**Invocation example** (run from project root):

```bash
.devforge/lib/onboard_helper add-package-doc \
  --unit pkg-foo \
  --path packages/pkg-foo \
  --content "$(cat <<'EOF'
# pkg-foo

## Overview
pkg-foo provides X for the workflow.

## Main Exports
<!-- packages/pkg-foo/src/index.ts:1-9 -->
\`\`\`ts
export const provideFooBLoC = ...
\`\`\`

[... rest of the per-doc template ...]
EOF
)" \
  --block-count 1 \
  --ref-count 1
```

After all per-package, per-concern, and per-architecture invocations + all `add-memory-finding` calls, finalize with:

```bash
.devforge/lib/onboard_helper compose-onboard
```

If validation fails, the helper prints the error list and exits 2 with state preserved. Read the errors, fix the affected registration(s) by re-invoking `add-*-doc` for the relevant unit/concern (re-registration overwrites), and re-run `compose-onboard`.

## Prerequisites

1. `/setup-wizard` must have been run — runtime primer (`CLAUDE.md`), agents directory, runtime config, and `.devforge/` scaffold must exist.
2. `docs/` folder must exist (placed by install, populated by setup wizard).
3. Project is **brownfield** — `.devforge/project-config.json` has `"PROJECT_STATE": "brownfield"`. Greenfield/empty projects skip onboard; the wizard's Phase 5 summary routes those to `/constitute` + `/specify`.
4. `.devforge/lib/onboard_helper` must be present and executable. install.sh copies it; verify with `ls .devforge/lib/onboard_helper`. If missing, the install is incomplete.

If any prerequisite is missing, inform the user and suggest running the missing command first.

---

## PHASE 1: Prepare Onboarding Context

### 1.0: Pre-scan Baseline Check (across all `docs/*` outputs)

Before any scan, check whether `docs/` carries user-edited content from a prior onboard run.

**Detection** (deterministic — diff against baseline):

For every existing file under `docs/` (recursive), compare against its snapshot at `.devforge/baseline/docs/<...same-relative-path...>`. If the file differs beyond trivial whitespace, treat it as **user-modified**.

If a baseline file is missing for an existing `docs/` file, do NOT silently assume stub-or-modified. Ask the user: "I can't determine whether `docs/<path>` carries pre-existing content — the baseline snapshot is missing. How should I proceed?" Offer the same three options below; fail closed.

**If user-modified content is detected anywhere under `docs/`**, pause and ask the user once for the whole set:

- **Overwrite** — discard existing content; regenerate from scan.
- **Merge** — preserve user-edited prose; regenerate only sections matching the baseline.
- **Abort** — skip onboard; user reconciles manually.

Default when uncertain: abort. Do not proceed silently.

**If only stubs are detected** (or `docs/` is empty beyond what the wizard placed), proceed to §1.1.

### 1.1: Gather Project Knowledge

Read the following and extract what the tech-writer needs:

1. **Runtime primer** (`CLAUDE.md`) — project name, type, framework, language, project structure, dev commands.
2. **`constitution.md`** — project identity (Section 1, populated by setup-wizard) and universal coding rules. The `[project-specific]` sections are sentinel-marked at this stage; `/constitute` populates them later from onboard's findings + user preferences.
3. **`.devforge/project-config.json`** — wizard-detected facts: `LANGUAGES[]`, `FRAMEWORKS[]`, `WORKSPACE_MODE` (`standalone`/`wrapper`), `PROJECT_ROOT`, `manifest_count`, `packages[]`, etc.
4. **`.devforge/memory.md`** — pre-seeded knowledge from setup wizard.

Compile a **project brief** — concise summary (~30 lines max) of what's already known: project name, type, stack, architecture pattern (if wizard captured), error handling pattern, API layer, testing framework, pre-seeded findings.

Do NOT include layer boundaries, domain entities, or naming conventions — those are the tech-writer's job to DISCOVER during scan, not preconditions.

### 1.2: Discover Documentation Units

Read `.devforge/detection_report.yaml` (or `project-config.json` if the wizard exposes it differently) to get the `packages[]` array. Each entry has a `path` field — the actual filesystem location of a manifest (package.json, Cargo.toml, pyproject.toml, go.mod, pom.xml, *.csproj, Gemfile, composer.json).

**A documentation unit is one of:**

- Each entry in `packages[]` (one unit per detected manifest).
- If `packages[]` is empty or has only one entry pointing to the workspace/source root, **the project itself is the single unit** (single-source-tree projects).

**The unit's doc location** = `docs/<unit-path>/index.md`, mirroring whatever path the wizard found:

- npm package at `packages/pkg-foo/` → `docs/packages/pkg-foo/index.md`
- Rust crate at root (`my-cli/`) → `docs/my-cli/index.md`
- Rust crate in custom folder (`workspace/crates/my-lib/`) → `docs/workspace/crates/my-lib/index.md`
- Go module at root (path = `.`) → `docs/index.md`
- Java module at `services/billing/` → `docs/services/billing/index.md`
- Single-app project (`packages[]` = `[{path: "."}]`) → `docs/index.md`

**WORKSPACE_MODE** (`standalone` or `wrapper`) is irrelevant to unit discovery — it encodes only whether LLM tooling lives inside or alongside the project folder.

### 1.3: Determine Subagent Strategy

| Source files | Strategy |
|---|---|
| < 50 | Direct: orchestrator writes everything itself, no subagents. |
| 50–500 | One subagent per documentation unit. Sequential or small parallel batches respecting runtime concurrency limits. |
| 500+ | One subagent per unit, parallel batches. |

**Subagent dispatch rule**: invoke subagents WITHOUT full-history fork. Each subagent receives a self-contained prompt with: unit identifier, scope path, project brief from §1.1, per-doc template (Section A.2), write target. They do not need the orchestrator's conversation history.

---

## PHASE 2: Execute Onboarding Scan

Phase 2 runs as **four distinct passes**, each with its own prompt template. **The orchestrator never writes to `docs/` directly** — every doc registration goes through `.devforge/lib/onboard_helper`. This separation is load-bearing: each pass has its own focus and its own per-doc template.

| Pass | Dispatch shape | Helper verb |
|---|---|---|
| **2A — Per-package** | One subagent per documentation unit (parallel-per-unit per §1.3) | `add-package-doc` (one per package) + `add-concern-doc` (per substantive subfolder) |
| **2B — Architecture** | Single dispatch (orchestrator or one subagent) | `add-architecture-doc` (single call) |
| **2C — Memory archaeology** | Single dispatch with explicit source-reading mandate | `add-memory-finding` × N (multiple calls) |
| **2D — Compose** | Orchestrator | `compose-onboard` (validation + atomic write) |

The passes run in order. 2A and 2B can be parallelized; 2C must run after 2A so its source-reading pass is informed by what was registered (but it does NOT summarize the docs — it reads source for archaeology). 2D runs last.

### Pass 2A — Per-package subagent prompt

For each documentation unit, dispatch one subagent (or run direct for small projects per §1.3). Subagent prompt:

```
You are operating in ONBOARDING MODE — pass 2A (per-package). Generate complete documentation for ONE unit by registering content through the onboard_helper CLI.

## Project Brief

[Insert project brief from §1.1]

## Documentation Unit Assigned

Unit name: [unit identifier]
Unit path: [path relative to PROJECT_ROOT, e.g. packages/pkg-foo]

## Pre-seeded findings (from prior memory.md)

[Insert any .devforge/memory.md entries that mention this unit. If none, omit this section.]

## Your Mission

Register one package doc + concern docs for this unit's substantive subfolders by calling `.devforge/lib/onboard_helper`. You MUST NOT write directly to docs/. The helper enforces 7 validation gates; non-compliant registrations are rejected at compose time with explicit guidance.

## CORE MANDATE — COVER ALL CODE

Every meaningful source folder under this unit gets a documentation home (via `add-concern-doc`). No sample-based silence. No skipping at scale. No "we'll cluster these into one file" merges that drop substance.

Density adapts to size — a small utility folder gets a short section; a complex multi-concern subfolder gets its own file with substantive depth — but every meaningful source folder gets its own helper invocation.

If you are tempted to merge two distinct concerns into one doc with a compound name (e.g. "auth-and-routing", "stores-and-services") — STOP — split them. Each `add-concern-doc` call covers one concern.

## Mode

[Insert mode from §1.0: overwrite | merge | fresh]

You can persist the mode at the start of the unit's pass:
`.devforge/lib/onboard_helper set mode --value [overwrite|merge|fresh]`

## Documentation Shape

For your assigned unit:

1. Identify the source root by ecosystem convention:
   - JS/TS/PHP-PSR4: src/
   - Rust: src/
   - Ruby: lib/
   - Java/Kotlin: src/main/java/<groupId>/<pkg>/ (collapse boilerplate path segments)
   - Python: src/<pkg>/ or <pkg>/
   - Go: unit root (subfolders like cmd/, pkg/, internal/ are direct concerns)
   - C#/.NET: project folder directly
2. Call `add-package-doc --unit <name> --path <unit-path> --content "$(cat ...)" --block-count N --ref-count N` once for the unit's index.md.
3. For each substantive subfolder of the source root (multiple files OR clear architectural role like components/, services/, routing/, handlers/, daos/, models/, views/, stores/, composables/, hooks/, plugins/, controllers/, presentation/, domain/, data/, repositories/, entities/), call `add-concern-doc --unit <name> --concern <subfolder-name> --content "$(cat ...)" --block-count N --ref-count N`.
4. Trivial subfolders (1-2 files, single-purpose utilities) fold into the package's index.md content. Don't call add-concern-doc for them.
5. Files never get individual concern docs; enumerate them within their folder's concern doc.

The helper's per-concern-decomposition gate (gate 2.2) checks the source filesystem for substantive subfolders and rejects compose if any are missing add-concern-doc registrations. The "concern mentioned inside index.md" satisfy-cheaply pattern does not pass this gate.

## Per-Doc Template (required sections, in order)

For each `docs/<unit-path>/index.md` and each meaningful concern sub-doc:

1. `# <unit or concern name>`
2. `## Overview` — 1 paragraph: what this provides, who consumes it.
3. `## Directory Structure` — annotated tree of the source layout (the actual paths). Mark non-exported subdirs explicitly (e.g., "`<subdir>/` — internal, not exported").
4. `## Main Exports` (or `Public Surface`, `Public API`) — every exported symbol grouped by concern. For each: signature + a code block lifted from real source with a `<!-- path/file.ext:line-range -->` reference comment. Group by concern (CRUD, lifecycle, validation, etc.) so an agent adding a parallel operation can locate the nearest pattern.
5. `## Types` (or `Data Shapes`) — principal types this exposes, full inline definitions. Not "see types.ts" — the actual type definitions inline.
6. `## Dependencies` — workspace-internal and external dependencies. Workspace-internal entries hyperlink to their docs (e.g., `[pkg-bar](../pkg-bar/index.md)`); each entry gets one line about what's used. External deps named with version, no link.
7. `## Usage Example` — lifted from a real consumer file in the codebase. End-to-end pattern showing how the unit is consumed.

## Code-Block Discipline (with mandatory self-validation)

Every fenced code block in the docs MUST be lifted from actual source. Add a `<!-- path/to/file.ext:line-range -->` reference comment immediately above each block. Never invent code. Never paraphrase. If you cannot find a real example, omit the block rather than fabricating one.

**Before invoking `add-package-doc` or `add-concern-doc`, you MUST count:**

1. Number of fenced code blocks in your content (` ``` ` opening lines, excluding ` ```mermaid ` blocks).
2. Number of `<!-- path/file.ext:line-range -->` reference comments.

These two counts MUST be equal. Pass them as `--block-count N --ref-count N`. The helper rejects any registration where they differ. If they're not equal:

- Either you're missing a reference comment for some block (add it).
- Or you have an extra reference (delete it).
- Or a "block" is actually a Mermaid diagram (which doesn't need a ref) — verify by checking the opening fence.

The helper's compose-time gate ALSO recounts your content and rejects if your declared numbers don't match the actual counts. **Self-validating count IS the discipline. Lying about counts gets caught.**

Annotate non-exported subdirs explicitly in the Directory Structure section. These annotations help downstream agents avoid false leads.

## Boundary Surface, Not Implementation

Document what crosses module/package/component boundaries: exported functions, public class members, route handlers, type definitions, props/emits/slots. Do NOT document private helpers, internal-only utilities, or implementation bodies.

The visibility model is the language's, not ours. The LLM knows each language's idiomatic boundary mechanism (TS `export`, Python `_` convention / `__all__`, Vue parent-contract via `defineExpose`/`props`/`emits`, Go capitalization, Rust `pub`, C# `public`/`internal`, Java member modifiers, etc.). Apply that language's mechanism. Skip what doesn't cross the boundary.

- ✅ YES: "`ReportService.generate(input: ReportInput): Either<ReportError, Report>` — builds a report from the input. <!-- src/services/report.ts:24-38 -->"
- ❌ NO: "`generate` first validates the input, then queries the database, then renders each section by calling helper X which loops..."

## What NOT to Document

- Implementation bodies — code is the source of truth for how something works internally.
- Private helpers / internal-only functions — name them well in code; skip the doc.
- Duplicated rules from `constitution.md` — docs describe what EXISTS; constitution describes the RULES.
- Tech-stack / dev-command duplication from the runtime primer — primer is the source of truth.
- Anything the scan is uncertain about — better silent than wrong.

[Insert full Section A instructions below — A.1 Smart Extraction, A.2 Per-Doc Templates, A.3 Bare Command Names, A.4 Quality Checks.]

After your registrations complete, return a brief summary noting how many add-package-doc + add-concern-doc calls you made.
```

### Pass 2B — Architecture subagent prompt

Single dispatch (orchestrator runs direct, or one subagent). Prompt:

```
You are operating in ONBOARDING MODE — pass 2B (architecture). Your job is to register the workspace-level architecture.md by calling `.devforge/lib/onboard_helper add-architecture-doc`.

This is a DIFFERENT prompt from pass 2A. Do NOT use the per-package per-doc template. The architecture template observes patterns that exist across the whole workspace, not within one package.

## Project Brief

[Insert project brief from §1.1]

## What was registered in pass 2A

[Insert: list of unit names + their paths from state. The orchestrator can get this via `.devforge/lib/onboard_helper status`.]

## Your Mission

Register `docs/architecture.md` once via:
`.devforge/lib/onboard_helper add-architecture-doc --content "$(cat ...)" --block-count N --ref-count N`

The architecture doc carries the project's actual architectural patterns, dependency directions, naming conventions, decision rules — observed from the codebase, not prescribed by this spec.

Required sections (per A.2.2):

1. Architecture overview — what the project IS at the architectural level.
2. Module/package structure — workspace layout, how units relate.
3. Patterns — every architectural pattern observed; multi-pattern when present, scoped explicitly with "applies in: <paths>".
4. Conventions — naming, file organization, import style, error handling.
5. Cross-cutting concerns — auth flow, data flow, state management, error propagation.
6. Dependency direction rules — observed inward/outward dependencies.
7. Dependency overview — Mermaid graph or bullet list of who-depends-on-whom across all units.

DO NOT include a "Main Exports" section here. Architecture is workspace-level, not surface-enumeration-of-one-unit. Avoid the failure mode where reusing the per-package template forces a misleading "Main Exports" section into architecture.md.

Same code-block self-validation rule applies: count fenced blocks, count refs, pass --block-count and --ref-count.

[Insert full Section A instructions below — A.1 Smart Extraction, A.2.2 architecture template, A.3 Bare Command Names, A.4 Quality Checks.]
```

### Pass 2C — Memory archaeology subagent prompt

Single dispatch with explicit source-reading mandate. Prompt:

```
You are operating in ONBOARDING MODE — pass 2C (memory archaeology).

This pass is NOT a postscript over the docs you generated in pass 2A. It is a SEPARATE source-reading pass with the explicit purpose of finding project archaeology that downstream agents need but can't grep for: latent bugs, naming hazards, V1/V2 coexistence, performance traps, dead code, dependency gotchas.

You will READ SOURCE FILES, not summarize the docs already generated. The helper rejects observations that match prose already written to docs/ (heuristic: discourage summarization-of-generated-content).

## Project Brief

[Insert project brief from §1.1]

## Pre-seeded findings (from prior memory.md)

[Insert any existing memory findings. Re-confirm them by reading source. Add new findings.]

## Your Mission

Walk source files (with the standard ignore set) looking for:

1. **Latent bugs** — typos in field names, silent error swallowing (e.g., console.log instead of structured error), wrong-type-but-compiles patterns, off-by-one logic errors visible at the boundary.
2. **Naming hazards** — class names that mislead (e.g., "InMemoryRepository" actually wrapping Apollo or LocalStorage), package descriptions copy-pasted from other packages, duplicate index.js/index.ts artifacts.
3. **V1/V2 coexistence** — same operation with V1 and V2 variants live simultaneously, often with different mappers/Either types/return shapes. Map every coexistence pair.
4. **Performance/complexity warnings** — classes >500 lines, constructors with >20 parameters, deep-clone-on-every-state-change patterns, module-level shared timers, unusual factory wiring.
5. **Cross-package operation duplication** — same GraphQL operation / API endpoint / use case implemented in multiple places.
6. **Type-safety gaps** — `any` returns where the interface declares a typed result, `// @ts-ignore` usage, `as any as X` casts.
7. **Inconsistencies** — Either bifurcation (purify-ts vs local Either), conflicting error-handling styles within the same unit, divergent naming patterns.

For each finding, call:
`.devforge/lib/onboard_helper add-memory-finding --category <module-boundaries|dependency-warnings|complexity|inconsistencies> --unit <unit-name-or-workspace> --observation "<one-line finding>"`

Cover EVERY unit, not a curated subset. Even thin packages get at least one boundary observation.

[Insert full Section A instructions below — A.1 Smart Extraction, A.5 Memory Enrichment.]
```

### Pass 2D — Compose

After 2A, 2B, 2C all complete, the orchestrator invokes:

`.devforge/lib/onboard_helper compose-onboard`

This runs all 7 validation gates and atomically writes registered content to `docs/` if validation passes. State is preserved on failure for retry. Errors are LLM-readable with specific guidance per failure.

If compose fails, the orchestrator reports the errors to the user and offers:
- **Re-run the relevant pass** to fix the errors.
- **Accept** — user explicitly waives the gap (rare).
- **Abort** — user reconciles manually.

Optional `docs/cross-cutting/<topic>.md` files are NOT part of this command's output by default. They're created in a follow-up if the architecture pass surfaces a pattern that genuinely spans units without a folder home; covered in a later spec amendment.

---

## PHASE 3: Process Results

The helper's `compose-onboard` already enforces all 7 validation gates (per-package coverage / per-concern decomposition / block-ref count equality / boilerplate-overview / principal-type presence / type dedup / cross-link + sigil hygiene), atomically writes docs to `docs/`, appends memory findings to `.devforge/memory.md`, and drops baselines to `.devforge/baseline/docs/`. The orchestrator's job in Phase 3 is to report the compose result and handle re-run flow if validation failed.

### 3.1: Report compose result

If `compose-onboard` exited 0:
- Read the helper's stdout summary (count of doc files written, baselines dropped, memory findings appended).
- Run `find docs/ -name "*.md"` to confirm written files.
- Proceed to Phase 4 summary.

If `compose-onboard` exited 2 (validation failed):
- Read the error list from stderr.
- Identify which pass produced the offending registration (per-package, per-concern, architecture, memory).
- Re-dispatch the relevant pass with explicit error context (the specific gate failures).
- Re-invoke `compose-onboard`.
- Repeat until pass or user chooses Abort/Accept.

### 3.2: Spot-check (post-compose, optional sanity)

The helper has already validated structurally and semantically. Spot-checks here are optional sanity-only:
- Confirm `docs/architecture.md` exists.
- Confirm `.devforge/baseline/docs/` mirrors `docs/`.
- Confirm `.devforge/memory.md` has new dated subsections.

If any of these are missing despite compose returning 0, the helper has a bug — report and abort rather than proceed silently.

---

## PHASE 4: Summary

Present to the user:

```
## Onboarding Complete

### Documentation Generated
- [N] documentation units mirrored under `docs/`
- `docs/architecture.md`
- [list optional `docs/cross-cutting/*` if any]

### Scan
- [count] source files across [count] units (subagent-strategy: [direct | per-unit | parallel-per-unit])

### Memory Updated
[Summarize in 1-3 lines what was appended to .devforge/memory.md.]

### Next Steps
1. Review `docs/` and adjust as needed
2. Run `/constitute` — turn scan findings + your architectural preferences into enforceable rules in `constitution.md`
3. Start working: `/specify "your first feature"`
```

---

## SECTION A: Tech-Writer Onboarding Instructions

These instructions are inlined into the tech-writer agent prompt at the placeholder above (Phase 2).

**Project Root**: All source code scanning targets the Project Root specified in the runtime primer (`CLAUDE.md`), or canonically in `.devforge/project-config.json` `PROJECT_ROOT` field. For wrapper-mode projects, this is a subfolder.

### A.1: Smart Extraction — What to Read from Each File Type

Context is finite. Extract the high-information content from each file type; skip the rest.

| File Type | What to Extract | What to Skip |
|---|---|---|
| Type/interface/trait/protocol definitions (`.d.ts`, `types.ts`, `.pyi`, `interfaces/`, `entities/`; Rust `trait`/`struct`/`enum`; Python `Protocol`/`TypedDict`/dataclass; Go `type`; Swift `protocol`/`struct`; Kotlin `sealed`/`data class`) | Read full content — highest information density | Nothing |
| Index/barrel/module entry files (`index.ts`, `__init__.py`, `mod.rs`, `lib.rs`; Go `package`; Swift `@_exported import`; Java/Kotlin module-info) | Read full content — defines module boundaries | Nothing |
| Route/API definitions (HTTP routes, gRPC services, GraphQL resolvers, RPC controllers, message handlers) | Read full content — defines API surface | Nothing |
| Config files (`.env.example`, config modules, framework config) | Read full content | `.env` (secrets) |
| Implementation files (services, repositories, helpers) | Function/method signatures, class/struct/trait definitions, imports, exports | Function bodies |
| UI component files (`.vue`, `.tsx`, `.svelte`, `.dart`; Android `@Composable` + XML; SwiftUI `View`; native mobile view classes) | Props/interface, template/view structure, emits/events, composable/hook usage | Template HTML/CSS details, style internals |
| Test files (JS/TS `describe`/`it`, Python `def test_*`, Rust `#[test]`, Go `func TestXxx`, JUnit `@Test`, XCTest, RSpec) | Test names only — these reveal WHAT the code does | Test bodies, assertions, mocks |
| Migrations/schemas (SQL, Alembic, Prisma, TypeORM, ActiveRecord, Flyway, Liquibase) | Schema definitions, table/type structures | Individual migration steps |
| Generated/vendored code (protobuf outputs, GraphQL codegen, SwiftGen, vendored deps) | Skip entirely | Everything |
| Assets (images, fonts, static) | Skip entirely | Everything |

**Ignore set** (never scan, never count): `node_modules/`, `target/`, `build/`, `dist/`, `.next/`, `.nuxt/`, `vendor/`, `.gradle/`, `.cargo/`, `__pycache__/`, `.venv/`, `venv/`, `.tox/`, `.mypy_cache/`, `.ruff_cache/`, `coverage/`, `.coverage`, `.cache/`, `tmp/`, `.tmp/`, `bin/`, `obj/`, `Pods/`, `.bundle/`, `.dart_tool/`, plus forge-managed artifacts (`.claude/`, `.devforge/`, `specs/`, `docs/`), lock files, and binary/asset files.

### A.2: Per-Doc Templates

#### A.2.1 — Per-unit / per-concern doc template

For each `docs/<unit-path>/index.md` and each meaningful concern sub-doc, the template defined in Phase 2's prompt applies (Overview / Directory Structure / Main Exports with sourced code blocks / Types inline / Dependencies with cross-links / Usage Example).

Length adapts to scope:
- Tiny utility folder: 30–80 lines (folded into parent if even smaller).
- Small library / single-concern subdir: 80–200 lines.
- Mid-size unit: 200–400 lines.
- Composite unit (multi-concern): main `index.md` is overview + directory + cross-references to sub-docs; sub-docs carry per-concern depth.

#### A.2.2 — `docs/architecture.md` template

`architecture.md` carries the project's actual architectural patterns, dependency directions, naming conventions, decision rules — observed from the codebase, not prescribed by the spec.

Required sections:

1. **Architecture overview** — what the project IS at the architectural level.
2. **Module/package structure** — workspace layout, how units relate.
3. **Patterns** — every architectural pattern observed in the codebase. **A project may legitimately have multiple coexisting patterns** (e.g., MVC in backend services + Clean Architecture in frontend; legacy procedural code being phased out alongside modern layered code; different paradigms in different microservices). When multiple patterns coexist, document each with explicit "where it applies" scope:
   ```
   ### <Pattern A> (applies in: <unit-paths or module-paths>)
   <observed description, conventions, decision rules>

   ### <Pattern B> (applies in: <other paths>)
   <observed description>
   ```
   Do NOT force-fit the project into a single pattern when more than one exists.
4. **Conventions** — naming, file organization, import style, error handling — all observed. If conventions vary across patterns, scope each accordingly.
5. **Cross-cutting concerns** — auth flow, data flow, state management, error propagation — all observed.
6. **Dependency direction rules** — observed (where inward/outward dependencies go); per-pattern when patterns diverge.
7. **Dependency overview** — high-level "who depends on whom" listing across all units. Mermaid graph OR plain bullet list. Bird's-eye view complementing per-unit `Dependencies` sections.

**Per-unit overrides**: a unit's `index.md` MAY contain a "Pattern" section when that unit follows a distinct pattern worth calling out at unit level (cross-reference `docs/architecture.md` for workspace context).

**Optional split**: when one or more patterns warrant their own deep document, split into `docs/architecture/<pattern>.md` per pattern; `docs/architecture.md` becomes the index pointing at each.

#### A.2.3 — `docs/cross-cutting/<topic>.md` (optional)

Only when the LLM observes a pattern that genuinely spans multiple units without a folder home (e.g., authentication flow that touches an auth package, a router config in an app, and middleware in another service). Each cross-cutting topic explicitly hyperlinks into every unit it touches.

### A.3: Bare Command Names in Documentation (MANDATORY)

In any `docs/*.md` prose that names a workflow command — `onboard`, `constitute`, `specify`, `plan`, `breakdown`, `implement`, `verify`, etc. — use the **bare command name**. The `/` sigil belongs in user-facing command output (wizard summaries, command headers) where the user would actually type it; documentation prose reads better without it.

- ✅ RIGHT: "Run onboard again after significant changes."
- ❌ WRONG: "Run `/onboard` again..."

If you need to show a literal command invocation in docs, phrase it as: "invoke the `onboard` command."

### A.4: Quality Checks (your self-check before returning)

Before returning, verify:

1. **Coverage**: every meaningful source folder under your assigned unit has a doc home. **This is the load-bearing check.**
2. **Structural completeness**: every doc has the required template sections — Overview, Directory Structure, Main Exports with sourced code blocks, Types inline, Dependencies, Usage Example.
3. **Real code only**: every code block in docs is copied from actual source with a `<!-- path/file.ext:line-range -->` reference. No invented code.
4. **Boundary surface only**: docs enumerate what crosses module/class/component boundaries. Internals stay in source.
5. **Cross-references resolve**: workspace-internal `Dependencies` entries link to their package docs; broken links not allowed.
6. **No constitution duplication**: docs describe HOW the code is organized; constitution describes the RULES.
7. **No primer duplication**: tech-stack and dev-command tables live in `CLAUDE.md`; do not repeat them in `docs/`.
8. **Inline annotations**: subdirs that exist in source but are NOT exported are explicitly annotated in directory trees.
9. **No source modifications**: onboarding mode does NOT modify source files. Only `docs/` and (via the orchestrator) `.devforge/memory.md`.

### A.5: Memory Enrichment

After generating docs, return a summary of findings to be added to `.devforge/memory.md`. **Cover every unit, not a curated subset.**

Include:

- **Module/package boundaries** — every unit's responsibility in 1 line.
- **Cross-package dependency warnings** — tightly coupled areas, circular imports, brittle interfaces observed.
- **Areas of complexity** — units or concerns with many dependencies, unusual patterns, or unclear conventions.
- **Inconsistencies** — self-contradictions within observed code (different error-handling styles in the same unit, divergent naming, etc.), or deviations from constitution's `[universal]` sections.

**Return format:**

```
## MEMORY_ADDITIONS

### Module/package boundaries
- <unit-1>: <one-line responsibility>
- <unit-2>: <one-line responsibility>
- ... (every unit, not a sample)

### Dependency warnings
- <observation>

### Areas of complexity
- <unit/area>: <why it's complex>

### Inconsistencies
- <what was expected vs what was found>
```

---

## Glossary (locked terminology)

These terms have precise meanings in onboard's output and downstream consumers:

| Term | Means |
|---|---|
| **package** | A self-contained unit detected by the wizard — one entry in `packages[]`. Has its own manifest (package.json, Cargo.toml, etc.). |
| **unit** (documentation unit) | A package, OR the project itself if `packages[]` has only a root entry. The thing onboard generates a `docs/<unit-path>/` folder for. |
| **concern** | A meaningful subfolder within a unit's source root (e.g., `components/`, `services/`, `routing/`, `handlers/`). Each substantive concern gets its own sub-doc. |
| **boundary surface** | Symbols that cross a file/class/component boundary (exports, public class members, props/emits/slots, route handlers). What docs enumerate. |
| **module** | Used loosely to mean a directory inside a unit; not a fixed-meaning term in this command's output. Prefer "concern" for sub-folder docs and "package"/"unit" for top-level. |

---

## IMPORTANT RULES

1. **All doc writes go through `.devforge/lib/onboard_helper`** — this is the only sanctioned write path. Direct `Write` tool calls to `docs/` are not part of this command's contract. The helper enforces 7 validation gates at compose time; bulk-script writes cannot satisfy them.
2. **Self-validate code-block counts before every registration** — count fenced blocks, count `<!-- path:line -->` reference comments, pass `--block-count N --ref-count N`. The helper rejects mismatches at registration AND at compose (content recount).
3. **Cover all code** — every package or meaningful source folder gets a helper invocation. Coverage failure is a compose-time gate failure.
4. **Architecture and memory are SEPARATE passes** — different prompts, different per-doc templates. Don't reuse the per-package template for architecture.md (forces wrong section shape). Memory is source-archaeology, not summarization-of-generated-docs.
5. **Tech-writer subagents register; orchestrator composes** — orchestrator handles pre-scan, dispatch coordination, compose invocation, error report + re-run flow.
6. **Never modify source files** — onboarding writes only to `docs/`, `.devforge/memory.md`, and `.devforge/baseline/` (all via helper).
7. **Code blocks lifted from real source** — every fenced block has a `<!-- path/file.ext:line-range -->` reference. Mermaid blocks are exempt. No invented code.
8. **Boundary surface, not implementation** — what crosses module boundaries. Skip internals.
9. **Mirror folder structure** — `docs/<unit-path>/...` mirrors the source layout. Path-from-source = path-to-docs.
10. **No bundled pattern assumptions** — `architecture.md` observes the project's actual patterns; spec mandates structure not content. Document multi-pattern projects honestly.
11. **Preserve user-edited docs** — §1.0 detects user edits via baseline diff. Re-runs ask Overwrite/Merge/Abort, never silently overwrite.
12. **Bare command names in `docs/`** — use bare command names (no `/` sigil) in documentation prose.
13. **No constitution / primer duplication** — docs describe what EXISTS; constitution + primer carry their own concerns.
14. **This is for agents** — primary audience is the agents running subsequent commands. Be explicit, structured, precise. Documents must be a substitute for first-pass code reading.
