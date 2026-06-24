---
name: breakdown
description: Translate an approved technical plan into ordered, atomic, agent-assigned tasks with verifiable contracts and a structured breakdown→implement handoff.
argument-hint: "[plan-file]"
disable-model-invocation: true
---

# /breakdown — Task Breakdown from Plan

`/breakdown` is repeatable per feature. It takes an approved plan authored by `/plan` and produces ordered, atomic, agent-assigned tasks with verifiable cross-task contracts: a `tasks/*.md` file per task, a `tasks/README.md` index, and a structured `breakdown-handoff.json`. The orchestrator (the LLM following this spec) writes all task artefacts in the main thread via Write or Edit. Subagent dispatch is reserved for **decision work at one mandatory hook**: the `architect` agent is invoked at Phase 2 (Decomposition) for every run to validate task atomicity, dependency ordering, and contract-chain integrity. Outside that hook, the orchestrator authors directly and assigns agents via the inlined Agent Assignment table — no per-phase auto-dispatch. Phase 0b's hard gate ensures `/constitute` has populated the constitution before any breakdown work fires. Produces `specs/NNN-<feature>/tasks/` plus `specs/NNN-<feature>/breakdown-handoff.json`, and ends with a manual handoff to `/implement` — no automated dispatch.

Usage: `/breakdown [plan-file]` (e.g. `/breakdown specs/008-prevent-duplicate-config-options/plan.md`, or `/breakdown` with no argument to use the most-recently-modified plan under `specs/`).

## Outputs of this phase

- `specs/NNN-<feature>/tasks/NNN-<title>.md` — one rendered task file per task (required).
- `specs/NNN-<feature>/tasks/README.md` — task index with dependency graph, risk assessment, and review checkpoints (required).
- `specs/NNN-<feature>/breakdown-handoff.json` — structured producer-side handoff (best-effort; see Phase 5).
- `specs/NNN-<feature>/design-manifest.json` — per-element design-fidelity disposition manifest (conditional; written only when the feature has a `design/reference.html` — see Phase 2.5).

After approval (Phase 5), `/breakdown` WIP-commits these artifacts — the whole `tasks/` directory plus `breakdown-handoff.json` — via `.devforge/lib/artifact_helper commit-artifacts`. The commit lands in the INSTALL repo only (never the wrapper-mode source/product repo) and is fail-soft (a git failure warns and `/breakdown` continues — the artifacts are already written). The `[WIP]` commit folds into `/finalize`'s squash, so the final PR is unchanged. **In WRAPPER mode this is the FIRST per-step commit that tracks the task files + `tasks/README.md` in the install repo** — `/implement`'s wrapper path stages ONLY source code in the source repo and leaves the task files uncommitted, so this commit is NOT redundant there. (In standalone mode `/implement` already tracks the task files, so re-staging unchanged ones is a harmless no-op; `breakdown-handoff.json` is newly tracked either way.)

## Context in the Workflow

```
/research (optional) → /specify → /plan → /breakdown → /implement → /review → /verify → /summarize → /finalize
```

`/breakdown` runs AFTER the plan is approved, BEFORE task execution. The plan describes HOW the feature maps to the architecture; `/breakdown` decomposes that into atomic, independently-verifiable units of work with explicit dependencies and contracts.

## PHASE 0a: Plan resolution

`/breakdown` consumes one approved plan per invocation. Resolve which plan via the helper:

```bash
.devforge/lib/breakdown_helper pick-plan $ARGUMENTS
```

If `$ARGUMENTS` is non-empty, the helper validates the explicit file path (must be an existing `plan.md` file, not a directory) and prints its absolute path on stdout. If empty, the helper picks the most-recently-modified `specs/*/plan.md`. Exit 2 means no valid plan was found — copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then end the turn.

Capture the resolved absolute path. Then render the preview block:

```bash
.devforge/lib/breakdown_helper render-pick-summary <resolved-path>
```

Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). Exit 2 means the plan file is missing — copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block, then end the turn. Otherwise ask the user via `AskUserQuestion`:

- Question: `"Process this plan?"` — single-line text.
- Options: `["yes", "pick-other", "cancel"]`.

End the turn. The user's reply opens the next turn.

- **`yes`** → proceed to Phase 0a.5 with the resolved path.
- **`pick-other`** → in the next turn, run `.devforge/lib/breakdown_helper list-plans` and emit stdout as a numbered list inside a fenced block (exit 2 means no `specs/` directory exists — copy the helper's stderr VERBATIM into a fenced block and end the turn). The helper output is unbounded (one line per plan, mtime desc). For `AskUserQuestion`, take the first four lines as the four option labels — AskUserQuestion caps at four options, so the LLM truncates client-side, not the helper. Question: `"Which plan to break down?"` — single-line text. If more than four plans exist, include `other` as the fourth option; on `other`, ask the user via free-text follow-up for the explicit path, then re-run `pick-plan <path>` to validate. On the chosen path, treat it as the resolved path and proceed to Phase 0a.5.
- **`cancel`** → tell the user `"/breakdown cancelled. Re-run /breakdown when ready."` and end the turn.

## PHASE 0a.5: Upstream handoff (consumer)

`/plan` may have written a sibling `plan-handoff.json` next to the plan, carrying the structured decomposition seeds (layer map, file impact, key design decisions, dependencies, risks). This phase surfaces those seeds as the authoritative decomposition input. There is no user gate here; do not invoke `AskUserQuestion`.

Read the sibling handoff via the helper:

```bash
.devforge/lib/breakdown_helper read-plan-handoff <resolved-path>
```

- Stdout `no-handoff` → no sibling `plan-handoff.json` exists. Tell the user `"No structured plan handoff; decomposing from plan.md directly."` and proceed to Phase 0b with the resolved path. The decomposition input comes from reading `plan.md` directly in Phase 0 and Phase 1.
- A `## Upstream plan seeds` block (Layer Map / File Impact / Key Design Decisions / Dependencies / Risks) → copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). State that this block is the authoritative decomposition input — Phase 1 (Deep file analysis) and Phase 2 (Decomposition) are driven by these seeds, not by re-scanning the spec. Then proceed to Phase 0b with the resolved path.

Exit 2 means the sibling `plan-handoff.json` is malformed, the wrong handoff kind, or the wrong schema version — copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then end the turn.

## PHASE 0b: Status flip + gates

**Guard**: Read `constitution.md`. If it contains `_Run /constitute to populate_`, stop: "⛔ constitution.md has not been populated yet. Run `/constitute` before using `/breakdown`."

The act of running `/breakdown` constitutes approval of the plan for decomposition. Flip Draft → Approved structurally via the helper:

```bash
.devforge/lib/breakdown_helper check-status-and-flip <resolved-path>
```

Stdout is one of five state tokens:

- `flipped` — plan was Draft, now Approved. Tell the user: `"Plan status: Draft → Approved (implicit approval via /breakdown)."`
- `already-approved` — continue silently; no message needed.
- `complete` — the plan has a Status of `Complete` (e.g. manually set). Warn the user, then `AskUserQuestion` `"Plan status is Complete — proceed against a completed plan?"` with options `["yes", "cancel"]`. On `cancel`, end the turn.
- `inserted` — plan lacked a Status line; helper inserted `**Status**: Approved`. Tell the user: `"Plan was missing a Status line; helper inserted **Status**: Approved."`
- `unknown-status:<value>` — plan has a non-standard status. Tell the user the value, then `AskUserQuestion` `"Status is non-standard — proceed?"` with options `["yes", "cancel"]`. On `cancel`, end the turn.

Exit 2 means the plan is malformed (neither Date nor Status frontmatter line). Copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then end the turn.

## PHASE 0: Context load

**This phase always runs.** Load the context the decomposition depends on.

Read these in order:

1. The plan's sibling `spec.md` (same `specs/NNN-<feature>/` directory) — the acceptance criteria the tasks must collectively cover. Capture its absolute path — `<plan-dir>/spec.md`, the sibling of the resolved plan path — as `<spec-path>`; the Phase 0 drift check, Phase 1.5 findings, Phase 3 task writing, and Phase 3.5 AC-coverage gate all pass this `<spec-path>` to their helpers.
2. `plan.md` (the resolved path) — the layer map, file impact, key design decisions, and risk assessment. If Phase 0a.5 surfaced a `## Upstream plan seeds` block, that block is the authoritative seed; `plan.md` is the full source.
3. The feature's supporting docs if present: `research.md`, `data-model.md`, `contracts.md` (same directory).
4. `constitution.md` — architecture rules and constraints.
5. `MEMORY.md` — past lessons about similar decompositions.
6. `CLAUDE.md` — project structure, the `## Architecture` section, and the `## Packages` table for multi-stack projects.

**Source Root**: If `CLAUDE.md` specifies a Source Root other than `.`, resolve all source file references relative to that path. Claude artifact paths (`specs/`, `docs/`) remain at the workspace root.

**Optional spec drift check**: the spec may have been written against source files that changed since. Check via the helper (advisory, gate only):

```bash
.devforge/lib/cbm_sync_helper check-spec <spec-path>
```

Stdout is one of four forms:

- `current` — the spec's cited files are unchanged since it was stamped. Proceed silently to Phase 1; no message needed.
- `missing` — no drift stamp exists for this spec. Tell the user `"No drift stamp for this spec; proceeding."` and proceed to Phase 1.
- `drift <a>..<b> <file-1> <file-2> ...` — one or more spec-cited files changed since the spec was stamped. Tell the user the spec's cited files changed since it was stamped, listing the changed files from the `<file-...>` tokens. If the `drift` token carries no `<file-...>` tokens (only the two SHAs), do not claim specific files changed — tell the user the spec has drifted from its stamp but the cited-file list could not be computed (the spec file may have moved). Then ask via `AskUserQuestion` `"Spec-cited files changed since the spec was written — proceed with breakdown?"` — single-line text — with options `["proceed", "cancel"]`. On `cancel`, tell the user `"Re-check the spec against the changed files before re-running /breakdown."` and end the turn. On `proceed`, continue to Phase 1.
- `not-a-git-repo` on stdout (exit 2) — the drift check cannot run (no git repository / no HEAD / git binary missing). Tell the user `"Spec drift check unavailable (not a git repository); proceeding without it."` and proceed to Phase 1. The drift check is advisory — a non-git target must NOT block breakdown.

## PHASE 1: Deep file analysis

Analyze the files the tasks will touch, driven by the plan-handoff `File Impact` + `Layer Map` seeds (from Phase 0a.5) and by reading `plan.md`. Do NOT re-scan the spec for file impact — the plan already settled it. Branch on whether the feature touches an existing codebase or is greenfield.

### If existing codebase

For every file listed in the plan's File Impact table:

1. **Read the file** completely.
2. **Map its dependencies**: what does it import? What imports it?
3. **Identify the change points**: exactly which functions/blocks need to change.
4. **Estimate scope**: how many lines will change? Is it a rename or a logic change?
5. **Check for cascading effects**: will changing this file require changes in files not in the plan's File Impact table?
6. **Identify verifiable semantics**: what exports, interfaces, functions, or call patterns must exist after the change? What must be imported from where? These become the basis for cross-task contracts (Phase 3).

If you discover files that should have been in the plan but weren't, note them as additions — they go in the `## Additions to Spec` section of the tasks index (Phase 3).

### If greenfield (creating new files)

For every file listed in the plan's File Impact table:

1. **Confirm the file does not exist** — if not, this is a "Create" task.
2. **Read the constitution's scaffolding guide** — verify the file will land in the correct directory per the architecture rules.
3. **Identify the pattern reference** — find the closest pattern example from the constitution.
4. **Map required dependencies** — what types, interfaces, or modules must be created first?
5. **Check for infrastructure needs** — does this feature need new directories, config changes, or package installs?
6. **Identify verifiable semantics** — what exports, interfaces, or functions must exist after each creation step? These become cross-task contracts.

**Greenfield task ordering** follows this sequence:

1. **Infrastructure** — create directories, install packages, add config.
2. **Types / interfaces** — define the data shapes.
3. **Core logic** — domain / business logic, use cases, repositories.
4. **Presentation** — UI components, views, routes.
5. **Integration** — wire everything together (DI, routing, store registration).

## PHASE 1.5: Findings from Plan (REQUIRED INTERMEDIATE OUTPUT)

Before writing any task file, produce a structured intermediate output enumerating what the plan contains and which task will cover each item. This is a hard requirement.

Render the skeleton via the helper (pass the spec path so AC markers are emitted):

```bash
.devforge/lib/breakdown_helper render-findings-from-plan <resolved-path> <spec-path>
```

The helper emits `## Findings from Plan` with a `[TASK COVERAGE: ?]` marker on each plan File Impact + Layer Map row, and an `[ADDRESSED BY: ?]` marker on each spec acceptance criterion. Exit 2 means the plan file is missing — copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then end the turn. Otherwise copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). In the SAME message, replace each marker inline with the task(s) that will cover it:

- `[TASK COVERAGE: ?]` on a File Impact / Layer Map row → `[TASK COVERAGE: task NNN]` (or `tasks NNN, MMM` if split across tasks).
- `[ADDRESSED BY: ?]` on a spec AC → `[ADDRESSED BY: task NNN]` (or `tasks NNN, MMM`).

This intermediate output forces every plan row and every spec AC to be accounted for before tasks are written. Same purpose as `/plan` Phase 1.5: convert implicit recall into explicit enumeration. Skipping or compressing this step is a hard error.

After this intermediate output is complete, proceed to Phase 2. The "1.5" numbering runs after Phase 0/1 and before Phase 2 despite the numeric ordering, because it gates the task decomposition itself.

## PHASE 2: Decomposition (MANDATORY scoped architect)

This is the decision hook. Translate the plan + file analysis into a draft task set — atomic units, dependency edges, and Expects/Produces contracts — then have the `architect` validate the decomposition before any task file is written.

**Architect consultation: mandatory.**

Before writing any task file, invoke the `architect` agent via the Task tool to validate the decomposition. The architect's `think`-tier reasoning is the specialization point for task-boundary, dependency-direction, and contract-chain-integrity calls — net-new judgment the plan did not produce. Writing task files without this consultation is a hard error at this phase.

**Orchestrator-mediated consultation relay (the architect emits requests; it does NOT invoke anyone):** subagents cannot spawn subagents, so the architect cannot consult a specialist itself. Instead the architect returns zero-or-more **consultation requests** alongside its validation, and the orchestrator (the LLM running this spec) performs the invocations. Run the loop:

1. Invoke the `architect` agent (mandatory, per above) with your draft task set and the three fixed sub-questions below. It returns its validation (confirmations + revisions to atomicity / ordering / contracts) AND zero-or-more consultation requests, each carrying a named specialist + a sub-question + context.
2. For each consultation request: invoke the named specialist via the Task tool with the architect's sub-question + context, capture the specialist's response, then **re-invoke the `architect`** with the relayed response so the architect can synthesize it into its validation. The architect never invokes the specialist — the orchestrator relays both directions.
3. The orchestrator MAY also consult a specialist directly when this spec calls for it, not only on the architect's request.

Any decomposition-relevant specialist may be named: `architect`, `frontend-engineer`, `backend-engineer`, `mobile-engineer`, `security-reviewer`, `db-engineer`, `migration-engineer`, `api-designer`, `performance-analyst`, `design-auditor`, `devops-engineer`, `qa-engineer`, `runtime-debugger`.

**Brief shape (pass file paths, NOT inlined content):**

- `specs/<feature>/spec.md`
- `specs/<feature>/plan.md`
- `specs/<feature>/research.md` / `data-model.md` / `contracts.md` (whichever exist)
- `CLAUDE.md` (architect reads `## Architecture` + `## Packages` directly)
- `constitution.md`

The architect inherits the parent session's Read tool surface and will fetch these itself. Do not summarize their content in the brief — that double-pays context and risks drift. Pass your DRAFT task set (numbers, titles, depends-on edges, Expects/Produces per task) inline in the brief, since it does not yet exist on disk.

**Sub-questions (always asked):**

1. **Task atomicity boundaries / bundling**: is each task one logical change (1-3 files, 5-30 min, one clear done condition)? Should any mechanical task be bundled into its dependency? Should any task be split?
2. **Dependency ordering & direction**: is the depends-on graph acyclic and correctly directed (types before use, data before domain, core before presentation, independent before dependent, riskiest first)?
3. **Contract-chain integrity**: does every `Produces` feed a downstream `Expects` or a spec AC, and does every `Expects` trace to an upstream `Produces` or existing codebase state? Are contracts stated as semantic identifiers (export / function / interface / field names), never line numbers?

**Agent assignment is orchestrator-direct** via the inlined Agent Assignment table below — a lookup, not judgment. The architect only VALIDATES the agent assigned to design-decision tasks (tasks that choose interfaces, data shapes, algorithms, or contracts downstream tasks depend on); it does not re-derive the whole assignment.

### Task Granularity Rules

- **One task = one logical change** that can be verified independently.
- A task should touch **1-3 files** maximum (exception: a rename/replace across many files is ONE task, not many).
- Each task must have a clear **done condition**.
- Tasks should take **5-30 minutes** to implement (not hours). If a task would take longer, break it into sub-tasks.

### Task Nature Classification (mechanical vs design-decision)

For each task, determine whether it is **design-decision** or **mechanical**:

- **Design-decision**: the task requires choosing interfaces, data shapes, algorithms, orchestration logic, or contracts that downstream tasks depend on. No existing pattern to copy — the implementer makes judgment calls. The architect validates the agent assigned to these (see above).
- **Mechanical**: the task follows an established pattern already present in the codebase (e.g., wrapping a data source with try/catch error mapping, registering dependencies in a DI container, adding a route entry). The implementer copies an existing example and substitutes names — zero design decisions.

**Signals a task is mechanical**: the codebase already has 1+ examples of the exact same pattern; the task's output is fully determined by its inputs; the task body is <30 lines of boilerplate with no conditional logic; the task description reduces to "do what feature X did, but for feature Y".

### Bundle Mechanical Tasks

After classification, check whether any mechanical task should be **bundled into its dependency** rather than standing alone:

- **Bundle when**: the mechanical task is <30 lines, has exactly one dependency, and would be assigned to the same agent as that dependency. Keeping it separate adds an execution wave and an agent launch for trivial work.
- **Keep separate when**: the mechanical task touches files in a different layer than its dependency, has multiple dependents that need its output as a checkpoint, or the combined task would exceed the 1-3 file limit.

When bundling, merge the mechanical task's files, contracts, and done-when conditions into the parent task, and update the dependency graph accordingly.

### Agent Assignment table

Assign exactly ONE agent per task by the file's owning package/stack (see `## Packages` / `PACKAGE_STACKS` in `CLAUDE.md`). A type, interface, domain model, contract, or state store is **not its own layer with its own agent** — it belongs to the stack that owns the file, and that stack's implementer writes it. The architect never appears in this table: it shapes at `/plan` and only *VALIDATES* the decomposition (above) — it does not write code.

| Files in... | Agent |
|-------------|-------|
| API endpoints, controllers, middleware, services, server-side logic — and the backend stack's domain models, types, interfaces, contracts, and business/state logic | backend-engineer |
| UI components, styles, routes, composables, stores — and the frontend stack's domain models, types, interfaces, and state management (BLoC / Redux / Pinia) | frontend-engineer |
| Mobile screens, navigation, native modules, platform-specific code, app lifecycle — and the mobile stack's domain models, types, and state | mobile-engineer |
| Non-server host / runtime-entrypoint code — Electron main process, desktop-app `main`, CLI entrypoint, Tauri core — i.e. the app's host process, NOT a backend server | the owning package's stack implementer per `## Packages` / `PACKAGE_STACKS` (the app's primary implementer — e.g. the frontend/app engineer that owns the rest of the codebase) — NOT `backend-engineer` by default |
| Bug investigation with runtime symptoms | runtime-debugger |
| Performance-critical path or optimization task | owning stack engineer (backend/frontend/mobile-engineer, per the file's layer) — `performance-analyst` diagnoses and recommends during `/review`, it never implements |
| Auth, secrets, input validation, security hardening | owning stack engineer (backend-engineer for server-side auth/secrets/validation; frontend-engineer for client-side) — `security-reviewer` reviews during `/review`, it never implements |
| Database schemas, migrations, queries, seed data | db-engineer |
| API contract design, OpenAPI specs, endpoint structure | api-designer |
| CI/CD, Docker, deployment config, infrastructure | devops-engineer |
| Data migration scripts, backward compatibility layers | migration-engineer |
| Accessibility, design-system compliance, visual-fidelity work on UI files | owning stack engineer (frontend-engineer / mobile-engineer, per the file's layer) |
| Dedicated test-authoring / coverage-gap task — a standalone task that writes tests for existing or just-built behavior, NOT the inline tests an engineer writes for their own implementation task | qa-engineer |
| Unclear or mixed | split per the rule below — never `architect` |

A mixed or unclear task is a decomposition smell, not a routing problem: split it until each piece maps to exactly one stack's implementer; if a piece genuinely spans stacks (e.g. a backend API plus its frontend consumer), break it into per-stack tasks joined by a dependency edge. If splitting is genuinely impossible, escalate to the human. Never assign `architect` to write code — the architect cannot implement.

Host / runtime-entrypoint code that is non-renderer but also not a backend server (an Electron main process, a desktop-app `main`, a CLI entrypoint, a Tauri core) is NOT a `backend-engineer` task by default — route it via the host / runtime-entrypoint row above to the owning package's stack implementer per `## Packages` / `PACKAGE_STACKS`. For a desktop / Electron / CLI app whose code is one app stack, that is the app's primary implementer (the engineer that owns the rest of the codebase), never backend-by-default.

If the owning stack's implementer is not generated for this project (not all projects generate all agents), split or escalate to the human — never fall back to `architect` (the architect cannot write code). `performance-analyst`, `security-reviewer`, and `design-auditor` are READ-ONLY reviewers — they run during `/review` (and `/audit`) on the changed files and are never assigned an implementation task (`design-auditor` runs the `/review` runtime design-fidelity check when the feature has a design reference + manifest). For a genuinely perf- or security-focused investigation, the diagnosis still routes to the owning stack engineer to implement the fix; the reviewer recommends, the engineer changes the code.

Inline tests stay the per-engineer default — each stack engineer writes the tests for their own implementation task. Create a SEPARATE task assigned to `qa-engineer` (the dedicated test-authoring row above) ONLY when decomposition or the Phase-2 architect consult flags a coverage gap or a test-heavy acceptance criterion; this gives `qa-engineer` a real executor without double-covering every task. `qa-engineer` is `model_tier: do` — a valid implementer, so the "Never assign `architect` to write code" rule above does not apply: `qa-engineer` is a builder, not the architect. If `qa-engineer` is not generated for this project, the split-or-escalate rule applies as for any other missing implementer, and the Phase 3.5 agent-roster gate catches any task assigned to an uninstalled agent. Distinct responsibilities: `qa-engineer` WRITES tests, while `/implement`'s per-task scope-aware verify step RUNS them.

**Halt rule:** if you reach Phase 3 without having completed the architect consultation, halt, invoke the architect now, then record its validation provenance in the tasks index Specialist Consultation table (Phase 3) before writing any task file. Task files written without a corresponding Specialist Consultation entry are a hard error.

## PHASE 2.5: Design-fidelity intake gate (CONDITIONAL — fires only when the feature has a design reference)

**This phase runs ONLY when the feature implements against a design reference.** A design reference is a `design/reference.html` file at the workspace root (the single HTML artifact the feature's UI implements against). If no such file exists, this feature is not UI-against-a-reference work — SKIP this entire phase and proceed directly to Phase 3. Non-UI features and UI features with no `design/reference.html` are NOT blocked by this gate.

When a `design/reference.html` DOES exist, this gate produces a per-element disposition manifest — the pre-code contract that classifies every reference element before any task file is written — and HALTS intake if any reference value cannot be resolved or any element is left unclassified. The gate runs at INTAKE (before Phase 3 writes task files), not at verify: a fidelity gap is escalated to the user BEFORE code is written, never after. The `design_helper` owns the manifest's structure, validation, and the gap-list computation; the orchestrator composes only the disposition values.

**Detect the design reference.** Check whether `design/reference.html` exists at the workspace root. If it does not exist, tell the user `"No design/reference.html for this feature; skipping the design-fidelity intake gate."` and proceed to Phase 3. If it exists, continue.

**Step 1 — Resolve the reference into elements + a gap-list.** Run the helper, capturing its stdout JSON to a scratch file outside the work tree (the helper's next verb reads a file path, not a pipe):

```bash
mkdir -p "${TMPDIR:-/tmp}/forge-breakdown"
.devforge/lib/design_helper resolve-reference --html-path design/reference.html \
  > "${TMPDIR:-/tmp}/forge-breakdown/design-reference.json"
```

**Check the exit code before proceeding.** Because the command redirects stdout to a file, a non-zero exit (exit 2 — `design/reference.html` was not found or could not be read) leaves an empty/partial JSON file and the helper's informative stderr is the only diagnostic. If the exit code is non-zero, copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then end the turn. Proceed to Step 2 ONLY on exit 0.

On exit 0 the verb has emitted a JSON object carrying the `data-ref`-anchored element list (each element's `data_ref`, tag, id, classes, inline style), the resolved CSS values, and a `gap_list` of unresolvable classes/undefined tokens (a class with no CSS definition on disk, a `var(--token)` with no definition in the collected CSS). The gap-list is NOT escalated here — it is carried into the manifest and enforced by `validate-manifest` (Step 4), which is the single halt point for both unresolvable values and unclassified elements.

**Step 2 — Initialize the skeleton manifest.** Produce a skeleton manifest (every element unclassified) from the resolve-reference output, and write it to the feature's manifest path via Write:

```bash
.devforge/lib/design_helper init-manifest \
  --reference-json "${TMPDIR:-/tmp}/forge-breakdown/design-reference.json"
```

The verb emits the skeleton manifest JSON to stdout — every element carries `disposition: ""` (unclassified) and the `gap_list` is copied in. Exit 2 means the reference JSON could not be read — copy the helper's stderr VERBATIM into a fenced code block and end the turn. Otherwise write the helper's stdout VERBATIM to `specs/NNN-<feature>/design-manifest.json` via Write (substitute `NNN-<feature>` with the resolved feature dir name). Do not edit the structure; you will fill only the disposition values in Step 3.

**Step 3 — Classify every element's disposition (judgment step, WITH the architect consult already performed in Phase 2).** This is the orchestrator's composition step. For each element in `specs/NNN-<feature>/design-manifest.json`, set its `disposition` field to exactly one of:

- **`MATCH`** — the element is in scope; its runtime values (color, border, radius, spacing, typography, `:hover`, `:focus-visible`) must equal the reference 1:1.
- **`DEFER-EMPTY`** — the element's CONTENT is out of scope (an empty mount slot), but the CONTAINER's box model (border, padding, dimensions) still matches the reference 1:1.
- **`STATIC-PLACEHOLDER`** — the element's content is fixed/hardcoded, but its styling still matches the reference 1:1.
- **`DEVIATE`** — an explicit, recorded decision to depart from the reference. A `DEVIATE` element REQUIRES a non-empty `deviate_reason` field stating why; that reason is the audit trail.

The Phase-2 architect validation of task boundaries and the design decisions it surfaced are the basis for these classifications — classify in light of that consultation, not independently of it. Write the classified `specs/NNN-<feature>/design-manifest.json` via Edit (set each `disposition`, and the `deviate_reason` on every `DEVIATE` element).

**Step 4 — Validate the manifest (the HALT point).** Run the validator against the classified manifest:

```bash
.devforge/lib/design_helper validate-manifest \
  --manifest-path specs/NNN-<feature>/design-manifest.json
```

Substitute `NNN-<feature>` with the resolved feature dir name. The verb emits a `{valid, errors}` JSON object to stdout and, on failure, one error line per problem to stderr. It enforces two rules: every element MUST carry a disposition (an unclassified element fails, naming the element), and the gap-list MUST be empty (each unresolvable class/token fails, naming the token with a "supply the missing artifact or record a DEVIATE entry" instruction).

- **Exit 0** — the manifest is fully classified with an empty gap-list. The intake gate passes. Remove the scratch dir, then proceed to Phase 3:

  ```bash
  rm -rf "${TMPDIR:-/tmp}/forge-breakdown"
  ```
- **Exit 1** — validation errors. Copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then HALT and escalate. Two distinct failure classes appear in the stderr, with distinct recovery paths — tell the user which applies and that intake cannot proceed until it is resolved. Do NOT write any task file. End the turn; the user's resolution opens the next turn, after which re-run from the step named below for the failure they fixed, then re-validate.
  - **An unclassified element** (`element '<data-ref>': disposition is unclassified`) → the element was left blank in Step 3. Recovery: re-enter Step 3 to set its `disposition` (and `deviate_reason` if `DEVIATE`), then re-run Step 4.
  - **A gap-list entry** (`gap-list: unresolvable class/token '<token>'`) → a class or token in the reference could not be resolved on disk. The `gap_list` is a SEPARATE top-level field of the manifest; reclassifying an element does NOT clear it. Two accurate recovery paths: (1) **supply the missing artifact** — add the missing stylesheet or define the missing token at its source, then re-run from Step 1 to recompute the gap-list from the updated reference; or (2) **accept it as a known deviation** — manually edit `specs/NNN-<feature>/design-manifest.json` to REMOVE that token from the `gap_list` array AND set the corresponding element's `disposition` to `DEVIATE` with a `deviate_reason` recording the acceptance, then re-run Step 4 to re-validate. Path 1 re-runs from Step 1; path 2 is a manual edit followed by Step 4.
- **Exit 2** — the manifest file could not be read or parsed (a Step 2/Step 3 write problem). Copy the helper's stderr VERBATIM into a fenced code block, then end the turn.

The validated `specs/NNN-<feature>/design-manifest.json` PERSISTS as the design-fidelity CONTRACT for the feature. It declares, per element, what the two downstream fidelity gates enforce: a `MATCH` element's runtime values must equal the reference 1:1 (color, border, radius, spacing, typography, `:hover`, `:focus-visible`); a `DEFER-EMPTY` element's container box model must match 1:1 while its content is out of scope; a `STATIC-PLACEHOLDER` element's styling must match 1:1 while its content is fixed; a `DEVIATE` element is exempt, its `deviate_reason` the audit trail. The manifest is consumed by two enforcement concerns: `/implement`'s per-task forcing-functions gate runs the write-time provenance check `verify-design-tokens` against it (no hardcoded color literals, no `var(--x, <literal>)` fallbacks, token-binding on `MATCH` elements, `:hover` + `:focus-visible` on interactive elements), and `/review`'s PHASE 2.5 dispatches `design-auditor` to read it for the review-time runtime-conformance check (each in-scope element's rendered values against the reference per its disposition). This phase only PRODUCES that contract; it does not itself run either enforcement.

## PHASE 3: Write tasks

For each task in the validated decomposition, render its skeleton via the helper, then fill the values and write the file. The helper owns the task-file structure (per `.devforge/storage-rules.md` §Task File Format); you compose the values.

```bash
.devforge/lib/breakdown_helper render-task-file --number NNN --title "<imperative title>" --feature <feature-dir-name>
```

Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then fill its placeholders and write the result to `specs/NNN-<feature>/tasks/NNN-<title>.md` via Write. Fill these per task:

- **Header fields**: Agent (from the Agent Assignment table), Depends on, Blocks, Spec criteria (`AC-N`), Review checkpoint (Yes/No — see below), Context docs (see below).
- **Files table**, **Description**, **Change Details** — from the Phase 1 file analysis.
- **Contracts** (`Expects` / `Produces`) — per the Contract Generation Rules below.
- **Done When** — task-specific testable conditions; the helper-emitted skeleton already carries the standing tsc/lint/no-secrets/no-debug conditions.
- **Completion Notes** — leave the helper-emitted Completion Notes skeleton empty — it is the read contract that the `/implement` consumer will fill on completion.

### Contract Generation Rules

Each task's `## Contracts` section has `### Expects` (preconditions) and `### Produces` (postconditions):

- **Expects**: what must be true in the codebase before this task runs correctly. For the first task in a chain, these describe existing state. For downstream tasks, these match an upstream task's `Produces`.
- **Produces**: what must be true after this task completes. The `/implement` consumer verifies these by reading the source.

Rules:

- 2-5 items per section. Keep them concrete and code-verifiable by reading the source file.
- Reference **semantic identifiers** (function names, export names, interface names, field names) — never line numbers. Line numbers shift as earlier tasks modify files.
- Contracts must reference **literal strings that appear in source code** — export names, function names, interface names, field names, class names. Reference the literal declaration pattern (e.g., "`get cartTotals()` appears in `CartBLoC.ts`"), not abstract concepts ("has a getter").
- Bad contracts: "Cart totals work correctly" (not verifiable); "Line 45 returns the right value" (line numbers shift); "Performance is acceptable" (not code-verifiable).

### Doc Reference Rules

Determine if the agent needs documentation context beyond the task description:

- **Integration tasks** (wiring into an existing feature): reference the neighboring feature's doc.
- **Tasks extending an existing pattern**: reference `docs/architecture.md` if the pattern is documented there.
- **API tasks touching existing endpoints**: reference the relevant `docs/` API file.
- **Self-contained tasks** (new types, isolated logic): no doc reference — the task description is sufficient.
- **Maximum 2 doc references per task** — if more context is needed, include it directly in the task description.

### Review Checkpoint Placement

Set `**Review checkpoint**: Yes` or `No` per task. Auto-place `Yes` at:

1. **Convergence points** — the task depends on 2+ other tasks.
2. **Layer boundary crossings** — the first presentation-layer task after domain/data-layer tasks.
3. **High-risk tasks** — any task rated High in the risk assessment.

All other tasks get `No`. The user can add or remove checkpoints during the Phase 4 approval gate.

### Tasks index

After all task files are written, render the index skeleton via the helper:

```bash
.devforge/lib/breakdown_helper render-tasks-index --feature <feature-dir-name> --spec <spec-path> --plan <resolved-path>
```

Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then fill its sections and write the result to `specs/NNN-<feature>/tasks/README.md` via Write. Fill: the dependency-graph fence, the index table (one row per task), the `## Additions to Spec` section (files discovered in Phase 1 not in the plan, or "None"), the risk assessment, and the review checkpoints table.

### Specialist Consultation provenance

Render the consultation provenance skeleton via the helper and fill its rows — one row per specialist consulted (Verdict from the enum `accepted` / `modified` / `rejected` / `no-response`; Cites required; the `(none)` row stays when no specialist beyond the mandatory architect was consulted):

```bash
.devforge/lib/breakdown_helper render-consultation-block
```

The helper takes no arguments and owns the column names and verdict enum. Copy its stdout into the tasks index (`README.md`) and fill the rows; this table is the single source of truth for the Phase 2 consultation provenance.

## PHASE 3.5: Integrity gates

Three forcing-functions walk the task set mechanically. Contract-chain and AC-coverage findings MAY be carried to Phase 4 as a documented deferral — explicitly recorded in the index `## Risk Assessment` with a one-line justification. The agent-roster gate has NO such bypass: it is a HARD gate, and a roster violation must be re-routed before Phase 4 (a task literally cannot be implemented by an agent that is not installed).

**Contract chain** — orphan `Produces` / unsatisfied `Expects`:

```bash
.devforge/lib/breakdown_helper verify-contract-chain <tasks-dir>
```

- Exit 0 (`contract-chain: ok (N tasks, P produces, E expects)`) → the chain is intact. No action.
- Exit 2 with a `## Contract chain findings` block on stdout → advisory findings (orphan Produces or unsatisfied Expects). Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). For each finding, either revise the tasks (add the missing consumer/producer task, or fix the dependency edge) and re-run, or record the finding in the index `## Risk Assessment` with a one-line justification.
- Exit 2 with `no task files...` on stderr → the tasks directory is missing or empty. Copy the helper's stderr VERBATIM into a fenced code block; this indicates Phase 3 did not write the task files — return to Phase 3.

**AC coverage** — every spec acceptance criterion addressed by ≥1 task:

```bash
.devforge/lib/breakdown_helper verify-ac-coverage <tasks-dir> <spec-path>
```

- Exit 0 (`ac-coverage: ok (...)` or `ac-coverage: no-acs (...)`) → every AC is covered, or the spec has no ACs. No action.
- Exit 2 with a `## Uncovered acceptance criteria` block on stdout → copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). Every uncovered AC must get a covering task (return to Phase 3 to add it) or be explicitly flagged in the index `## Risk Assessment` as having no implementation path.
- Exit 2 on stderr → the tasks directory is missing or the spec is unreadable. Copy the helper's stderr VERBATIM into a fenced code block and resolve the named problem before re-running.

**Agent roster** — every assigned agent is actually installed in this project's `.claude/agents/` roster:

```bash
.devforge/lib/breakdown_helper verify-agent-roster <tasks-dir>
```

Pass only the tasks directory — do NOT pass `--agents-dir`. The verb defaults to `.claude/agents` relative to the working directory, which is correct in both standalone and wrapper mode: the helper is invoked via the relative path `.devforge/lib/breakdown_helper`, so the working directory is always the install root, where `.claude/` lives.

- Exit 0 (`agent-roster: ok (N tasks, M agents installed)`) → every assigned agent is installed. No action.
- Exit 2 with a `## Agent roster findings` block on stdout → one or more tasks assign an agent that is NOT installed for this project (the block lists each offending task filename and its uninstalled agent name, plus an `Available agents:` line). Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). For each offender, RE-ROUTE the task to an installed agent that owns the file's stack — re-enter Phase 3, consult the Agent Assignment table, and apply its split-or-escalate rule — then re-run this gate; NEVER fall back to `architect` (it cannot write code). This is a HARD gate: do not proceed to Phase 4 with an unresolved roster offender.
- Exit 2 with `no agent roster found...` on stderr → `.claude/agents/` is missing or has no agent files (a broken install). Copy the helper's stderr VERBATIM into a fenced code block; this is an install problem to resolve before breakdown can assign agents.
- Exit 2 with `no task files...` on stderr → the tasks directory is missing or empty (Phase 3 did not write the task files). Copy the helper's stderr VERBATIM into a fenced code block; return to Phase 3.

## PHASE 4: User approval (HARD GATE)

**Mode-dependent execution path** (mirrors `/plan` Phase 3):

- **If auto mode is active** (detect via `<system-reminder>` about auto mode, or explicit user instruction to operate autonomously): do not pause for clarifying questions during decomposition. Apply the model's recommended defaults to any boundary the plan left open. The user reviews the breakdown at the approval gate below.
- **If auto mode is NOT active** (interactive mode, default): if the decomposition surfaces decision points (e.g., whether to split or bundle a borderline task), the architect consultation in Phase 2 is the place to resolve them; present the resolved breakdown here.
- **When uncertain about mode**: prefer pausing (interactive default). Asking and waiting is reversible; proceeding without input is not.

**HARD GATE**: the breakdown MUST be approved before `/implement` can run.

Present a summary. This block is LLM-authored (breakdown state lives on disk in the task files and index, not in a state JSON):

"I've broken down the plan into **[N] tasks** at `specs/NNN-<feature>/tasks/`.

**Dependency chain**: [simplified graph]
**Riskiest tasks**: [list High-risk tasks and why]
**Review checkpoints**: [count] (before tasks [list])
**Contract chain**: [ok | N findings recorded in Risk Assessment]
**AC coverage**: [all covered | N flagged in Risk Assessment]
**Agent roster**: all agents installed"

Then ask via `AskUserQuestion`:

- Question: `"Approve this breakdown?"` — single-line text.
- Options: `["approve", "request-changes", "cancel"]`.

End the turn. The user's reply opens the next turn.

- **`approve`** → proceed to Phase 5 (finalize).
- **`request-changes`** → in the next turn, ask the user which task or aspect to revise. Re-enter the relevant phase (Phase 1 file analysis / Phase 2 decomposition / Phase 3 task writing / Phase 3.5 gates) as needed; re-render the affected task files and index via Write or Edit; re-run the Phase 3.5 gates; re-present the summary above and re-issue this approval prompt. The state lives in the rendered files on disk; this loop mutates them in place.
- **`cancel`** → tell the user `"/breakdown cancelled. Task drafts preserved at specs/NNN-<feature>/tasks/."` and end the turn.

## PHASE 5: Finalize

On `approve`, first write the structured breakdown→implement handoff via the helper. The `<plan-path>` for the call below is the resolved path to the approved `plan.md`.

```bash
.devforge/lib/breakdown_helper finalize-handoff <plan-path>
```

The helper parses `<plan-dir>/tasks/*.md` + the tasks `README.md` and atomic-writes `<plan-dir>/breakdown-handoff.json` (a structured handoff carrying the per-task machine contract — agent, depends_on, touched_files, expects, produces, ac_addressed, review_checkpoint — plus provenance to the sibling `plan-handoff.json`). Handle the exit code:

- Exit 0 → the helper wrote `specs/NNN-<feature>/breakdown-handoff.json` and printed its path on stdout. Surface the written path to the user in one line, e.g. `"Structured breakdown handoff written: <path>."`
- Non-zero exit → the helper could not write or validate the handoff. `finalize-handoff` runs the roster check internally as a backstop, so capture BOTH stdout and stderr and branch on their content:
  - If STDOUT contains a `## Agent roster findings` block → this is a HARD failure, NOT best-effort: one or more tasks assign an uninstalled agent. Copy that stdout block VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then HALT and return to Phase 3.5 to re-route the offending task per its gate; do NOT continue to the `render-implement-handoff` block. (In normal flow the Phase 3.5 roster gate already caught this, so this stdout-block path should rarely fire.)
  - Else if STDERR contains `no agent roster found` → this is a HARD failure (broken install — `.claude/agents/` is missing or empty). Copy the helper's stderr VERBATIM into a fenced code block, then HALT and resolve the install before re-running; do NOT continue to the `render-implement-handoff` block.
  - Else (any other non-zero cause — Exit 2 → plan or task files missing, a task carries a placeholder agent, or rendered content failed schema validation; Exit 1 → I/O error writing `breakdown-handoff.json`, e.g. permissions or disk-full) → copy the helper's stderr VERBATIM into a fenced code block, then do NOT abort. Continue to the `render-implement-handoff` block below. The structured handoff is best-effort for these causes; the manual block is the guaranteed human bridge.

The `breakdown-handoff.json` is the **producer side** of the breakdown→implement handoff. The `/implement` consumer reads this producer's contract. There is no auto-dispatch and no auto-consume: the manual block below remains how the user launches `/implement`.

Now WIP-commit `/breakdown`'s own artifacts so the work is git-safe at this step. Run this UNCONDITIONALLY (the task files + index were written in Phase 3 and approved in Phase 4; `breakdown-handoff.json` was just written above, best-effort):

```bash
.devforge/lib/artifact_helper commit-artifacts --paths '["specs/NNN-<feature>/tasks", "specs/NNN-<feature>/breakdown-handoff.json", "specs/NNN-<feature>/design-manifest.json"]' --label 'breakdown: NNN-<slug>'
```

Substitute `NNN-<feature>` with the resolved feature dir name and `NNN-<slug>` with the feature id. Passing the `tasks` DIRECTORY path stages every task file plus `tasks/README.md` under it (the verb passes a directory path to `git add` unchanged, identical to `git add specs/NNN-<feature>/tasks`). `commit-artifacts` stages ONLY the named paths and makes a `[WIP] breakdown: NNN-<slug>` commit in the INSTALL repo (never the wrapper-mode source/product repo). It is FAIL-SOFT: a git staging or commit failure warns on stderr and exits 1 (non-fatal — the artifacts are already written, so note the warning and CONTINUE; do NOT abort); "nothing to commit" (paths already staged or absent) exits 0 silently as a benign no-op. **In WRAPPER mode this is the FIRST per-step commit that tracks the task files + `tasks/README.md` in the install repo** — `/implement`'s wrapper path stages ONLY source code in the source repo and leaves these uncommitted — so the commit is NOT redundant there. The `[WIP]` commit folds into `/finalize`'s squash, leaving the final PR unchanged. If `finalize-handoff` above failed to write `breakdown-handoff.json`, that path is simply not present and the verb stages only the present paths — a benign skip, not a failure. The `design-manifest.json` path is likewise present only when Phase 2.5 produced it (a feature with a `design/reference.html`); for a non-UI feature it is simply absent and skipped.

Then emit the deterministic manual next-step block via the helper:

```bash
.devforge/lib/breakdown_helper render-implement-handoff <plan-path>
```

Handle the exit code:

- Exit 2 → the plan or task files could not be read. Copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), tell the user to verify `specs/NNN-<feature>/tasks/` exists and re-run `/breakdown`, and end the turn. Unlike `finalize-handoff`'s non-blocking non-zero exit above (which continues to this block), a failure here DOES end the turn — this block is the guaranteed human bridge, and if it cannot render there is no fallback next-step to fall through to.
- Exit 0 → stdout is the deterministic manual-next-step block — copy it VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). The block heading reads `## Manual next step — run /implement`; it carries the task count, informationally names the numerically-lowest first task, and the literal `/implement` invocation (no argument — `/implement` auto-resolves the lowest incomplete feature and its next task). The block also instructs the user to **restart Claude Code** before running `/implement` so any newly-installed command is picked up.

After the block lands in the user-facing message, end the turn with one short confirmation: `"/breakdown is done. Restart Claude Code, then copy the /implement command above to continue."` Do NOT restate the `/implement` invocation in your closing sentence — the block already contains the literal `/implement` line.

## IMPORTANT RULES

1. **Atomic tasks** — each task must be independently verifiable. Never bundle unrelated changes.
2. **Explicit dependencies** — if task B uses something task A produces, mark it. Missing dependencies cause bugs.
3. **One agent per task** — assign exactly ONE agent. If a task genuinely spans two stacks, split it into per-stack tasks joined by a dependency edge (per the Agent Assignment table's split-or-escalate rule) — never assign `architect` to write code.
4. **Include verification in every task** — every task's Done When carries tsc + lint conditions (the helper-emitted skeleton already does).
5. **Reference spec criteria** — every task maps to at least one acceptance criterion (`AC-N`).
6. **All ACs covered** — every spec acceptance criterion must be addressed by at least one task (enforced by `verify-ac-coverage`).
7. **Don't over-split** — a single find-and-replace across many files is ONE task, not many.
8. **Contract chain integrity** — every `Produces` feeds a downstream `Expects` or a spec AC; every `Expects` traces to an upstream `Produces` or existing state (enforced by `verify-contract-chain`).
9. **Contracts use semantic identifiers** — reference function / export / interface / field names. Never line numbers (they shift as earlier tasks modify files).
10. **Tasks decompose the plan, not the spec** — the plan already settled WHAT and HOW; `/breakdown` decomposes the plan's File Impact and Layer Map into ordered units. Drive Phase 1 and Phase 2 from the plan, not by re-scanning the spec.
