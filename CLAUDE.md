# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

A desktop API client built with Electron, React, and TypeScript

- **Name**: mintenvoy
- **Type**: desktop app
- **Frameworks**: Electron, React
- **Languages**: TypeScript
- **Build Tool**: electron-vite, Vite, electron-builder
- **Build Command**: `npm run typecheck && electron-vite build`
- **Type Check Command**: `npm run typecheck:node && npm run typecheck:web`
- **Lint Command**: `eslint --cache .`
- **Project Root**: .



## Project Structure

```text
mintenvoy/
├── src/
│   ├── main/          # Electron main process (Node.js, app lifecycle)
│   │   └── index.ts
│   ├── preload/       # Preload bridge (contextIsolation-safe IPC)
│   │   ├── index.ts
│   │   └── index.d.ts
│   └── renderer/      # React UI (renderer process)
│       ├── index.html
│       └── src/
│           ├── App.tsx
│           ├── main.tsx
│           ├── components/
│           └── assets/
├── resources/         # App icons / static resources
├── design/            # Design mockups + tokens
└── electron.vite.config.ts
```

## Development Commands

| Command | Description |
|---------|-------------|
| `npm run dev` | Start app in dev mode (electron-vite dev) |
| `npm run build` | Type-check then build (electron-vite build) |
| `npm run start` | Preview built app (electron-vite preview) |
| `npm run lint` | Lint with ESLint (cached) |
| `npm run format` | Format with Prettier |
| `npm run typecheck` | Type-check node + web TS configs |
| `npm run build:mac` | Build + package macOS |
| `npm run build:win` | Build + package Windows |
| `npm run build:linux` | Build + package Linux |

## Architecture

mintEnvoy follows Electron's three-process model: a **main** process (Node.js — app lifecycle + native APIs), a **preload** bridge (contextIsolation-safe IPC surface between main and renderer), and a **renderer** process (React 19 UI). UI state is held in zustand; local persistence via electron-store; outbound HTTP via undici; auto-update via electron-updater. Bundled by electron-vite, packaged by electron-builder.

| Package | Language | Framework | Build Tool | Test Command |
|---------|----------|-----------|------------|--------------|
| . | TypeScript | React | vite |  |

## Workflow

### Spec-Driven Development Flow

```
/init-forge → /generate-docs → /configure → /constitute → /research OR /discover → /specify → /plan → [/grill] → /breakdown → /implement → /review → /verify → /summarize → /finalize
  (once)         (once)         (once)       (once)     (per feat — required)     (per feat)  (per feat)  (optional,   (per feat)   (per task)    (per feat) (per feat) (per feat)  (per feat)
                                                                                                        high-stakes)
```

`/research` (bug/enhancement against existing code) OR `/discover` (greenfield) is a **required precondition** for `/specify` — `/specify` blocks until a research or discover handoff exists. Use `/research` when investigating existing code, `/discover` when surveying a greenfield idea; the two cover complementary intake lanes, and either one satisfies the `/specify` gate.

`/fix` is **not a linear step** — it is a proposal-only remediation loop OFF `/review` and `/verify` (and off an in-window conversational defect), run inside the post-`/implement`/pre-`/summarize` window; the model OFFERS it, the user invokes it. It never appears in the arrow chain above.

- `/research "topic"` — Investigate a bug or enhancement against the existing codebase → research handoff (required intake lane for `/specify`); WIP-commits its report + handoff as it writes them (folds into `/finalize`'s squash)
- `/discover "feature idea"` — Greenfield-feature discovery → discover handoff (required intake lane for `/specify`); WIP-commits its report + handoff as it writes them (folds into `/finalize`'s squash)
- `/specify "feature"` — Create spec with acceptance criteria → `specs/NNN-name/spec.md` (blocks until a research or discover handoff exists); WIP-commits the spec + handoff as it writes them (folds into `/finalize`'s squash)
- `/plan` — Technical plan from approved spec → `specs/NNN-name/plan.md`; WIP-commits the plan + handoff as it writes them (folds into `/finalize`'s squash)
- `/grill` — **Optional, opt-in** design-time adversarial review of the completed `plan.md` → `specs/NNN-name/grill.md` (run for high-stakes plans before `/breakdown`; not a mandatory gate); WIP-commits its report + any re-entry seed as it writes them (folds into `/finalize`'s squash)
- `/breakdown` — Atomic tasks with dependencies → `specs/NNN-name/tasks/`; WIP-commits the task files + handoff as it writes them (folds into `/finalize`'s squash)
- `/implement` — Drain the feature's tasks one at a time (no args); per-task hard gate before commit
- `/review` — Feature-level emergent cross-task review → findings report; WIP-commits the report as it writes it (folds into `/finalize`'s squash)
- `/verify` — Verify ACs + assembled mechanical checks, fold `/review` findings → APPROVED / NEEDS WORK / REJECTED verdict + spec flip on APPROVED; WIP-commits the verification report (and the flipped spec) as it writes them (folds into `/finalize`'s squash)
- `/fix` — **Proposal-only remediation loop** (NOT a linear step) OFFERED off `/review` findings / `/verify` NEEDS WORK / an in-window conversational defect → gated fix via `/implement`'s back half → `[WIP] fix:` commit; `/report-bug` is the file-and-defer alternative
- `/finalize` — Surgical `docs/` updates via tech-writer + an unconditional `specs/<feature>/` safety-net commit + squash WIP commits into a clean feature commit

`/research` and `/discover` are read-only and produce no spec themselves, but their handoffs are a required precondition for `/specify` — so they belong to the spec pipeline above, not to the standalone group below.

Standalone (no pipeline connection — runs outside the spec pipeline):
- `/audit` — Adversarial whole-codebase quality + system-design + best-practices review
- `/report-bug` — Pure-capture bug report: writes one `bugs/NNN-<slug>.md` (Status Open, Source manual) and stops; dispatches no agent

### Command Details

#### `/research "<topic>"` (required intake lane for `/specify`)
Investigate a bug or enhancement against the existing codebase and produce a structured research report grounded in the codebase-memory-mcp graph + `docs/`. Hard-gated on the 4-command setup chain (`/init-forge` → `/generate-docs` → `/configure` → `/constitute`). Read-only — does not modify code; the run writes a research `handoff.json` that `/specify` auto-discovers and requires (see `/specify` Phase 0.4 — a research OR discover handoff is a mandatory precondition), plus a copy-pasteable `/specify` block (manual, no auto-dispatch). WIP-commits its report + handoff as it writes them (folds into `/finalize`'s squash). Proportionate: scales down to a fast pass for a trivial bug.

#### `/discover "<feature idea>"` (required intake lane for `/specify`, greenfield)
Pre-`/specify` discovery for a greenfield feature — surveys internal prior art then the web, and produces a fit-checked discovery report with design options (typically 2-3) and a build-vs-buy verdict. Same 4-command setup-chain hard gate. Read-only — does not modify code; the run writes a discover `handoff.json` that `/specify` auto-discovers and requires (the greenfield counterpart to `/research`'s handoff; either one satisfies the `/specify` Phase 0.4 gate), plus a copy-pasteable `/specify` block (manual, no auto-dispatch). WIP-commits its report + handoff as it writes them (folds into `/finalize`'s squash).

#### `/specify "feature description"`
Authors a structured 9-section feature spec at `specs/NNN-<feature-name>/spec.md` with EARS-validated acceptance criteria. Hard-gated on the 4-command setup chain (`/init-forge` → `/generate-docs` → `/configure` → `/constitute`). **Requires approval before proceeding**; on approve, writes a specify→plan `handoff.json` + a manual-next-step `/plan` block (no auto-dispatch). WIP-commits the spec + handoff as it writes them (folds into `/finalize`'s squash). Auto-creates a `spec/NNN-short-desc` branch when on the default branch.

#### `/plan [spec-file]`
Takes an approved spec and produces a technical plan: architecture decisions, data model, API contracts, research. Saves to `specs/[feature]/plan.md`. On re-run, consumes a `/grill` REVISE-PLAN re-entry seed (`grill-seed.json`, `target_stage="plan"`) when present, directing the revision at the grill's confirmed findings. WIP-commits the plan + handoff as it writes them (folds into `/finalize`'s squash). **Requires approval before breakdown.**

#### `/breakdown [plan-file]`
Takes an approved plan and generates ordered, atomic tasks with dependencies, agent assignments, and verifiable Expects/Produces contracts. Each assigned agent is validated against the installed `.claude/agents/` roster (a Phase 3.5 hard gate) so a task can never be assigned an agent the project doesn't have. Saves task files to `specs/[feature]/tasks/` and writes a structured `specs/[feature]/breakdown-handoff.json` (the producer side of the breakdown→`/implement` handoff). When the feature has a `design/reference.html`, an intake gate also produces a per-element design-fidelity disposition manifest (`specs/[feature]/design-manifest.json`, backing the constitution's Design Fidelity principle) and halts intake on an unclassified element or an unresolvable reference value. WIP-commits the task files + handoff as it writes them (folds into `/finalize`'s squash). **Requires approval before execution.**

#### `/grill [plan-file]`
**Optional, opt-in** design-time adversarial review of the completed `plan.md` — the design-level mirror of `/review`, positioned between `/plan` and `/breakdown` so a fatally-flawed design is killed before `/breakdown` decomposes it. Run it for high-stakes plans (new architecture / dependency / data model / security); it is NOT a mandatory gate. Dispatches the `devils-advocate` adversary plus a refutation pass (architect-excluded `[code-reviewer, qa-reviewer, security-reviewer]`), reusing the shared refutation engine. The adversary reads `plan.md` + `spec.md` + the recon dossier + `constitution.md` + a scoped three-ring codebase slice, with self-gated web-verification of the plan's external claims. Writes `specs/[feature]/grill.md` with a recommended 4-way disposition — PROCEED / REVISE-PLAN / RE-ENTER-UPSTREAM / KILL; when the user's PHASE-7 pick matches a REVISE-PLAN or RE-ENTER-UPSTREAM recommendation, the orchestrator emits a backward re-entry seed (`specs/[feature]/grill-seed.json`) whose `target_stage` routes the consumer — on RE-ENTER-UPSTREAM the seed targets an upstream stage for the `/research`/`/discover`/`/specify` commands to consume, on REVISE-PLAN it targets `plan` for `/plan` to consume on re-run (so the revision addresses the grill's confirmed findings instead of re-deriving the plan). WIP-commits its report + any re-entry seed as it writes them (folds into `/finalize`'s squash). The USER owns the final verdict at the `/breakdown` approval gate.

#### `/implement`
Drains an approved feature's breakdown tasks one at a time — NO arguments; auto-resolves the lowest-numbered incomplete feature and its next dependency-ready task, and loops. Per task: dispatch the assigned agent → scope-aware verify with self-repair (type-check / lint / build / test) → an autonomous parallel review **panel of four read-only reviewers** (code-reviewer + qa-reviewer + security-reviewer + performance-analyst, merged to a single verdict) → forcing-functions gate (which includes a static design-token provenance check, backing the constitution's Design Fidelity principle, when a design manifest exists) → a per-task HARD GATE where all findings are fixed before approval (the human reviews the ready diff and approves/repairs/skips/stops; nothing is committed before approval; approval is reachable only from a fully-clean panel, and any reviewer conflicts surface as focused questions first). On approve: mark the task complete, single WIP commit, refresh the codebase-memory graph, advance. WIP commits accumulate and are squashed by `/finalize`. Writes a `.devforge/wip.md` marker + git checkpoint for crash recovery.

#### `/review [spec-file]`
Feature-level emergent cross-task review — runs after `/implement` drains a feature's tasks, before `/verify`. Dispatches a 5-finder ensemble (code-reviewer, architect, qa-reviewer, security-reviewer, performance-analyst) in emergent-cross-task mode over the ASSEMBLED feature diff (all the feature's tasks together) — plus `design-auditor` for a runtime design-fidelity check when the feature has a `design/reference.html` and `specs/[feature]/design-manifest.json` — then a refutation pass cross-examines each finding — hunting the emergent cross-task issues the `/implement` per-task panel structurally cannot see (cross-task security holes, assembled-data-flow performance, cross-task duplication, architectural drift). Writes a findings-only report to `specs/[feature]/review.md` that `/verify` folds into its verdict and `/audit`'s recurring-issue scan reads, and WIP-commits that report as it writes it (folds into `/finalize`'s squash). Read-only on source — findings only, NO verdict (the verdict is `/verify`'s).

#### `/verify [spec-file]`
The pipeline step after `/review`, before `/summarize`/`/finalize` — it OWNS the verdict (`/review` is findings-only). Proves the spec's acceptance criteria PASS/FAIL/PARTIAL via the **ac-verifier** agent, whose method is set by `ac_verification_mode` in `.devforge/project-config.json` (`runtime-assisted` probes the running app via Chrome DevTools MCP and/or API using the `ac_runtime_*` config; `tests` / `code-only` / `off` read code). Runs the assembled-feature mechanical checks (type-check / lint / build / test across all the feature's tasks together, reusing `implement_helper verify-touched` report-only — no self-repair), folds in `/review`'s findings (warns if `review.md` is missing), and renders the single APPROVED / NEEDS WORK / REJECTED verdict to `specs/[feature]/verification.md`. On APPROVED it flips the spec `**Status**:` → Complete (after a task-completion cross-check) and ticks the passed AC boxes; on NEEDS WORK it can file bugs to `bugs/`; on REJECTED (a spec-level problem) the user revises the spec via `/specify` → `/plan` → `/breakdown` and re-implements, rather than filing bugs. WIP-commits the verification report (and the flipped spec) as it writes them (folds into `/finalize`'s squash). It does NOT re-review — `/review` owns cross-task code-quality reasoning.

#### `/fix`
**Proposal-only gated remediation loop** — NOT a linear pipeline step and NOT a cold bug-fixer. OFFERED (never auto-invoked — the model proposes, the user types `/fix`) off `/review`'s findings, `/verify`'s NEEDS WORK verdict, or an in-window conversational defect the user raised and the model code-confirmed, all inside the post-`/implement`/pre-`/summarize` window. Consumes those already-diagnosed findings (`specs/[feature]/review.md` / `specs/[feature]/verification.md`) — it never invents a defect — triages and scopes them, then reuses `/implement`'s back half by CALLING the `implement_helper` verbs (scope-aware verify + self-repair → four-reviewer panel → forcing-functions gate → two-stage hard gate → `[WIP] fix:` commit); it copies no machinery. Writes NO `bugs/` file (`/report-bug` is the separate "defer" arm). A "fix" that turns out to need an architectural/behavior change bounces to `/specify` instead.

#### `/summarize [spec-file]`
The pipeline step after `/verify` approves, before `/finalize` — pure SYNTHESIS that renders a PR-ready feature narrative: what was built (in user terms), change stats, key decisions, deviations, and AC status. Gates on the spec `**Status**: Complete` flip that `/verify` owns. Agent-free and renders NO verdict — the AC status is read from `/verify`'s `specs/[feature]/verification.md`, NOT re-derived from the spec. Consumes the spec + plan + each task's `## Completion Notes` + git change stats + `verification.md`, and writes ONLY `specs/[feature]/summary.md` (mutates none of its inputs). Idempotent — a re-run overwrites `summary.md`; the run makes a `[WIP]` commit that `/finalize` squashes.

#### `/finalize [spec-file]`
Dispatches tech-writer for surgical `docs/` updates (`docs/<package>/`, `docs/architecture.md`) — not a dropped `docs/features/` tier — makes an unconditional `specs/<feature>/` safety-net commit (so any planning artifact a per-step commit missed is captured), then squashes all WIP commits — including each pipeline command's per-step artifact commits — into a single clean feature commit. Gate-checked: spec must be Complete (set by `/verify`). The last step before creating a PR.

#### `/generate-docs`
One-time brownfield doc generation (second command in the 4-command setup chain) — reads the indexed codebase and builds the `docs/` knowledge base in bottom-up tiers (concern → package → project + glossary) via the `generate_docs_helper` setter API (tech-writer in Skeleton-Fill Mode). Handles both monorepo and standalone single-root layouts. The replacement for the retired `/onboard`. Re-run when the codebase structure changes significantly.

#### `/constitute`
One-time deep codebase analysis (or interview for greenfield projects) that generates `constitution.md` — non-negotiable rules, architecture decisions, patterns. Its Section 3.5 forcing-functions config-capture offers the `design_token_provenance` rule (the build-time half of the Design Fidelity principle) for UI projects with a design source.

#### `/audit [--full | --uncommitted | --top N | path] [--passes N]`
Standalone adversarial whole-codebase audit for periodic "second opinion" quality reviews. Three scope modes: **broad** (`--full` / empty — whole codebase), **hotspot** (`--top N`, default 25 — risk-scored files by churn × CBM-callers × size, for large repos), **narrow** (file / directory / `--uncommitted`). **Full-spectrum** — one run hunts five dimensions: mislogic (lying names/comments, dead branches, cross-file contradictions) + **system design** (layering/SOLID/god-component) + **language/framework best practices** (type-safety suppression, untyped boundaries, reactivity/lifecycle misuse, perf-idiom smells) + **duplication/divergence** + **constitution-principle adherence** — system/software design, NOT visual. Launches code-reviewer, architect, qa-reviewer, and security-reviewer in **adversarial mode** with two structured checklists (Mislogic Hunt + Best-Practices/System-Design); each finding declares a `Category` (`mislogic | system_design | best_practice | duplication | security | blind_spot`) and the report buckets by it. Subjective best-practice findings are marked `Likely`/`Speculative`, never `Certain`. Reads up to 5 recent `specs/*/review.md` files to track recurring/unresolved issues across features. Anti-hallucination grounding: every finding must include a verbatim Evidence quote from the actual code; Phase 4 validation re-reads cited files and discards ungrounded findings. Writes dated reports to `audits/YYYY-MM-DD-audit.md` and prints inline summary. `--passes N` (clamped 1–3) overrides the **mode-conditional default** — broad/hotspot default to 2 passes (union findings to widen recall), narrow defaults to 1 — and composes with all three scope modes; multi-pass costs K× and is for periodic deep audits, and multi-pass recurrence is descriptive only — it no longer inflates a finding's confidence. Before ranking, a **refutation pass** cross-examines each finding (routed to a non-author reviewer; default-dismiss unless the defect is demonstrated from quoted code) and gates which findings reach the report. The report then separates CONFIRMED findings (the `## Top N Priorities` + `## Findings by File` headline) from DISMISSED + low-stakes uncertain findings (a `## Dismissed / Worth a Glance` appendix); high-stakes `[CONTESTED]` findings (`security` / `[CONSTITUTION-VIOLATION]` the refuter could not confirm) are surfaced in the headline flagged, never buried. Read-only, not auto-committed, **NOT part of any workflow chain** — invoke manually after several specs ship.

#### `/report-bug "<description>" [--file <path>] [--severity Critical|Warning|Info]`
Standalone **pure-capture** bug report — writes one `bugs/NNN-<slug>.md` record (`**Status**: Open`, `**Source**: manual`, the description, the optional `--file`, and the severity — default `Warning`) and stops. The `NNN` prefix is assigned by the helper (it scans `bugs/` for the highest number and increments); the file lands in the working tree uncommitted. Dispatches no agent, reads no source to confirm the defect, and does NOT advance or close the bug — the `Open → In Progress → Fixed` lifecycle is manual. The file-it-for-later counterpart to `/fix`'s remediate-now path; it never proposes or chains into `/fix`. Forward pointer only: `/research "<description>"` to investigate, or `/specify "<description>"` to address it as a feature. **NOT part of any workflow chain.**

### Conversational fix-or-file offer

When the user points out a defect AND you confirm it is real by reading the actual code AND the active feature is implemented-but-not-yet-summarized (verify with `.devforge/lib/fix_helper in-fix-window --feature <feature>` — exit 0 = in-window; any other result, whether out-of-window or the helper is unavailable/errors, → treat as not in-window and offer file-only), offer a two-arm choice: run `/fix` to remediate now (a gated remediation loop), or run `/report-bug` to file a bug and defer. All three conditions are required (user-raised AND code-confirmed AND in-window) — if any is absent (the defect is unconfirmed, you originated it, or no feature is in that window), offer only `/report-bug`, never `/fix`. Never auto-run `/fix` — propose it; the user invokes it.

## Available Agents

- ac-verifier
- api-designer
- architect
- backend-engineer
- code-reviewer
- db-engineer
- design-auditor
- devils-advocate
- devops-engineer
- frontend-engineer
- migration-engineer
- mobile-engineer
- performance-analyst
- qa-engineer
- qa-reviewer
- runtime-debugger
- security-reviewer
- tech-writer

Agent selection is automatic in `/implement` based on the task's assigned agent.

## Enforced Quality Gates

### Hard Gates (block until approved)
- Spec approval → before `/plan` can run
- Plan approval → before `/breakdown` can run
- Task breakdown approval → before `/implement` can start
- Acceptance criteria → verified in `/verify`

### Verification (explicit, scope-aware — no per-edit hooks)

Verification runs at task boundaries (end of `/implement`, etc.), not after every file edit. No per-edit hooks, no auto-execution after Edit/Write. (Runtime hooks for CBM-first discovery enforcement are described in **CBM-first Protocol Enforcement** below — those operate on Read/Grep/Glob/Bash/SessionStart, not on Edit/Write.) Verification is **scope-aware**: the phase reads `PACKAGE_STACKS` (see `## Packages` above) to determine which type-check / lint / build / test commands apply to each file touched during the task.

**Scope-aware verification flow**:

1. Identify files touched during the task (git diff against the task-start checkpoint).
2. For each touched file, find its package via `PACKAGE_STACKS` path lookup (longest path prefix wins; e.g., `services/api/users.py` matches the `services/api` package).
3. Run that package's `type_check_command`, `lint_command`, and `test_command` (stored in `.devforge/project-config.json`). Skip `"N/A"` and absent commands silently (no-op; not a failure).
4. Build (`build_command`) runs once per task between the static checks and the tests, aggregated across touched packages when multiple are edited. The fixed order is static checks (type-check + lint) → build → tests, so a failing build surfaces before any test runs.
5. For files not inside any detected package (top-level scripts, misc files): fall back to the primary-stack commands (`TYPE_CHECK_COMMANDS[0]` / `LINT_COMMANDS[0]` / `BUILD_COMMANDS[0]` / `TEST_COMMANDS[0]`).
6. **Self-repair loop**: if type check, lint, or a test fails, attempt up to 3 auto-repair iterations before stopping and reporting. Code-review findings are reported to the user, not auto-repaired.

**Pre-flight check** (before each task): read `constitution.md` and `.devforge/memory.md` so the task starts with the right context.

Full specification in `/implement`.

## CBM-first Protocol Enforcement

Four hook scripts ship at `.claude/hooks/` and are wired in `.claude/settings.json` to enforce the codebase-memory-mcp (CBM) discovery protocol at runtime. They steer code exploration toward `search_graph`, `trace_path`, `get_code_snippet`, `search_code`, and `query_graph` instead of raw `Read`/`Grep`/`Glob` or shell `grep`/`find`/`cat` over source files.

| Hook | Event | Matcher | Behavior |
|---|---|---|---|
| `cbm-code-discovery-gate` | `PreToolUse` | `Read\|Grep\|Glob` | Blocks (exit 2) on the first matched call of the session and sets the gate file, with a stderr reminder to use CBM tools; subsequent matches in the same session pass through (exit 0). Gate file: `/tmp/cbm-code-discovery-gate-$PPID`. |
| `bash-ban-raw-tools` | `PreToolUse` | `Bash` | First call per session whose `command` contains `grep`/`find`/`cat` over a source-extension file (`.py`, `.ts`, `.tsx`, `.vue`, `.go`, …) blocks (exit 2); other Bash calls and subsequent same-session matches pass through. Gate file: `/tmp/bash-ban-raw-tools-$PPID`. |
| `cbm-mcp-marker` | `PostToolUse` | `Bash\|mcp__codebase-memory-mcp__.*` | Appends `<UTC timestamp> <tool_name>` to `.devforge/cbm-usage.log` for every matched call (Bash + every CBM MCP tool); filter the log on the `mcp__` prefix to isolate the CBM-adoption signal. Always exit 0; never blocks. |
| `cbm-session-reminder` | `SessionStart` | `startup\|resume\|clear\|compact` | Stdout is injected as session context; re-states the CBM-first protocol after compaction / resume / clear. |
| `cbm-sync-session-start` | `SessionStart` | `startup\|resume\|clear\|compact` | Calls `.devforge/lib/cbm_sync_helper check`; emits stdout context block instructing Claude to run `mcp__codebase-memory-mcp__detect_changes` (drift) or `mcp__codebase-memory-mcp__index_repository` (missing) plus `cbm_sync_helper write` to refresh the stamp. Silent on `current` / `not-a-git-repo`. Stamp file: `.devforge/cbm-last-indexed-sha`. |

### Disabling individual hooks

To disable any hook, remove its entry from the corresponding event array in `.claude/settings.json`. The hook scripts under `.claude/hooks/` remain on disk but are no longer invoked. Re-running `install.sh` overwrites `.claude/settings.json` and restores the hooks.

### Why CBM-only

The hook messages reference codebase-memory-mcp tools exclusively (`search_graph`, `trace_path`, `get_code_snippet`, `search_code`, `query_graph`, `get_architecture`, `index_repository`). They do NOT reference codegraph's `agentic_*` tools — those require LLM-enabled mode that is not configured in default forge installs.

## Placeholder Convention

Any `{{UPPERCASE}}` marker (e.g., `mintenvoy`, `TypeScript`) in a template file is a substitution placeholder. Each marker is replaced with the user's answer or a detected value before the file is presented to the user.

Authors of template files — constitution, agent files, docs, this CLAUDE.md — may use these placeholders freely. Readers must never see literal `{{...}}` text in substituted output; if a placeholder reaches the user verbatim, the substitution step is broken or the marker name is wrong.

## Key Rules

### Always
1. **Read before write** — always read files before modifying them
2. **Constitution is law** — `constitution.md` rules override everything except user instructions
3. **Minimal changes** — every change should impact as little code as possible
4. **Memory is persistent** — check `.devforge/memory.md` for lessons from past sessions
5. **Specs are contracts** — once approved, implementation must satisfy every acceptance criterion
6. **One task at a time** — execute tasks sequentially following the dependency graph
7. **Document new code** — all new functions/variables must have clear documentation
8. **Lint everything** — linting must pass on all changed files before task completion
9. **Handle both paths** — every fallible operation must handle success AND error cases
10. **Validate at boundaries** — validate external input (user input, API responses, env vars); trust internal code
11. **SOLID, DRY, KISS** — single responsibility, don't repeat logic 3+ times, keep it simple
12. **Search before building** — before writing anything generic/reusable, search the codebase for existing utilities, helpers, or components that already do it
13. **Session state** — after each `/implement`, overwrite `.devforge/session-state.md` with a fixed-size snapshot of current progress. At session start, read it first if it exists.
14. **Crash recovery** — `/implement` writes a WIP marker (`.devforge/wip.md`) before execution and creates git checkpoints at each phase. If interrupted, the next run detects it and offers resume/rollback/skip options.

### Never
1. **Never swallow errors** — empty catch blocks are forbidden; handle, re-throw, or log with reason
2. **Never commit secrets** — no API keys, tokens, or credentials in code
3. **Never commit debug artifacts** — no console.log, debugger, print() left behind
4. **Never leave bare TODOs** — every TODO must have context and a reference
5. **Never modify outside scope** — do not "fix" unrelated code you happen to see
6. **Never guess** — if unsure how code works, read it; if unsure what user wants, ask

## Commit Convention

### Format
- **Final commits**: Conventional Commits — `type(scope): description`
  - `feat(scope):` — new feature
  - `fix(scope):` — bug fix
  - `refactor(scope):` — behavior-preserving restructuring
  - `docs:` — documentation only
- **WIP commits**: `[WIP] Type: description — phase detail` (squashed into final commit)
- **Checkpoint commits**: `[checkpoint] Pre-type: description` (squashed into final commit)

### Attribution


Co-Authored-By: Claude <noreply@anthropic.com>

### Rules
- Keep commit title under 72 characters
- No period at end of title
- Body is optional; use for non-obvious "why"
- One logical change per final commit (WIP commits get squashed)

## Artifact Storage

```
research/
  YYYY-MM-DD-topic-slug.md        # Research reports (/research) — bug/enhancement against existing code

discover/
  YYYY-MM-DD-topic-slug.md        # Discovery reports (/discover) — greenfield feature, pre-/specify

specs/
  001-feature-name/            # Numbered feature directories
    spec.md                    # /specify output
    plan.md                    # /plan output
    research.md                # /plan research (optional)
    data-model.md              # /plan data model (optional)
    contracts.md               # /plan API contracts (optional)
    tasks/                     # /breakdown output
      README.md                # Task index with dependency graph
      001-define-types.md      # Individual task files
      002-create-repo.md
      003-build-component.md

docs/
  overview.md                  # Project overview + package map (project tier)
  architecture.md              # Cross-package architecture + layering rationale
  glossary.md                  # CBM-augmented project glossary (project tier; Phase B)
  <package>/                   # One subdir per package (from .devforge/index.json)
    overview.md                # Package role + concerns list
    architecture.md            # Package layers + patterns
    <concern>/                 # One subdir per src/ subfolder
      index.md                 # Concern: Purpose + Structure (annotated tree, fenced) — LLM-first density
```

- Feature dirs: `NNN-kebab-name`, sequential numbering (001, 002, ...)
- Task files: `NNN-short-title.md`, sequential within feature
- Everything for a feature lives in one directory
- docs/ is generated by `/generate-docs` (Plan F): bottom-up tiers (concerns → packages → project), incremental skip via `source_stamp` frontmatter
- docs/ files are LLM context source first, dev-greppable second (LLM-first density format; see `.devforge/storage-rules.md`)
- Structural queries (exports, types, callers, deps, dead code) are NOT in docs/ — query the codebase-memory-mcp graph live via MCP tools (`search_graph`, `trace_path`, `get_code_snippet`, `search_code`, `query_graph`)
- Md files are auto-indexed by codebase-memory-mcp; `search_graph(query="<fuzzy topic>")` plus `search_code(pattern)` together surface md narrative + code structure
- `docs/glossary.md` is the project-tier consolidated glossary produced by Phase B — 30-150 CBM-classified terms (code-anchored / fuzzy-anchored / prose-only) with 1-2 sentence definitions and cite-back paths; concern-tier Purpose paragraphs still carry inline disambiguation
- See `.devforge/storage-rules.md` for full conventions including density rules + cite-back validation
- **Wrapper mode**: All artifacts (`specs/`, `docs/`, `constitution.md`) live in the wrapper root, NOT inside `.`

## Session Continuity

At the start of each session, read `.devforge/session-state.md` if it exists. It contains a compact snapshot from the last completed task — current feature, progress, recent decisions, and recently modified files.

This file is:
- **Fixed-size** — always fully overwritten, never appended, max ~40 lines
- **A sliding window** — only tracks the last 3 tasks' modifications and last 3 decisions
- **Not a history log** — history lives in task completion notes (`specs/`) and `MEMORY.md`
- **Updated automatically** by `/implement` (Phase 7)

If context is compacted or a new session starts, session-state.md ensures the next `/implement` can bootstrap without re-discovering state.

### Crash Recovery

If a task execution is interrupted (power loss, terminal crash, network drop), the next `/implement` will detect the interrupted state via `.devforge/wip.md` and offer recovery options: resume from where it stopped, rollback and retry, rollback and skip, or keep changes for manual handling. The WIP marker includes a `Command` field identifying which command was interrupted; if you run a different command while a marker exists, it detects the mismatch and asks you to resolve the previous session first. Git checkpoint commits (`[WIP]` prefix) preserve partial work and are squashed into a clean feature commit by `/finalize` when the feature is approved.

## References

- [Constitution](constitution.md) — Project rules and patterns
- [Specs](specs/) — Feature specifications, plans, and tasks
- [Memory](.devforge/memory.md) — Persistent learnings
- [Project Config](.devforge/project-config.json) — `/configure` answers plus per-stack arrays (`LANGUAGES`, `FRAMEWORKS`, `ARCHITECTURES`, `ERROR_HANDLINGS`, `API_LAYERS`, `TESTINGS`) and per-package `PACKAGE_STACKS` records
