---
name: configure
description: Populate config + substitute templates from /init-forge state + /generate-docs output
disable-model-invocation: true
---

# /configure — Project Configuration

`/configure` is the third command in the 4-command sequence (`/init-forge` → `/generate-docs` → `/configure` → `/constitute`). It consumes the structural fields persisted by `/init-forge` and the docs corpus produced by `/generate-docs`, fills 29 configuration fields via `.devforge/lib/configure_helper` setters, prunes `.claude/agents/*.md` against the project's natures, renders the consolidated config, and substitutes `{{KEY}}` placeholders in the framework's templates.

## Outputs of this phase

- `.devforge/configure.yaml` — canonical state (29 fields). Owned + shaped by the helper; mutated only via setter subcommands.
- `.devforge/project-config.json` — render artifact rebuilt from `configure.yaml` + `.devforge/init.yaml` + `.claude/agents/` listing on every run (37 keys: 29 from configure.yaml + 5 from init.yaml + 3 derived).
- `.claude/agents/*.md` — pruned to those whose `applies_to` frontmatter overlaps `project_natures` (Phase 5.2); each remaining file is substituted in place; no `{{KEY}}` markers remain.
- `CLAUDE.md` — substituted in place; no `{{KEY}}` markers remain.

## Phase 0 — Pre-flight gate

Verify each predecessor artifact exists; abort the run on the first miss.

```bash
test -f .devforge/init.yaml
test -f .devforge/index.json
test -f docs/overview.md
test -f docs/architecture.md
```

- If `.devforge/init.yaml` is missing → ABORT: "missing .devforge/init.yaml — run `/init-forge` first."
- If `.devforge/index.json` is missing → ABORT: "missing .devforge/index.json — run `/init-forge` first (Step 6 builds the index)."
- If `docs/overview.md` is missing → ABORT: "missing docs/overview.md — run `/generate-docs` first."
- If `docs/architecture.md` is missing → ABORT: "missing docs/architecture.md — run `/generate-docs` first."

## Phase 1 — Reset + pull inputs

Reset helper state, then invoke each `read-*` subcommand in order. Every read subcommand emits JSON to stdout; capture each output into a named variable so Phase 2 has all four inputs in memory before composing.

```bash
.devforge/lib/configure_helper reset
```

`reset` writes a fresh defaults yaml at `.devforge/configure.yaml` (every schema field reset to its null/empty default). Idempotent on re-runs.

```bash
.devforge/lib/configure_helper read-init
```

Stdout JSON carries every field in `.devforge/init.yaml`: `project_root`, `workspace_mode`, `project_state`, `default_branch`, `packages_detected[]`. Capture as `INIT_JSON`.

```bash
.devforge/lib/configure_helper read-docs
```

Stdout JSON has two top-level keys: `overview` and `architecture`. Field types vary by section — most are pre-parsed dicts/lists, a few are raw section text strings:

- `overview.purpose` — raw paragraph text (string)
- `overview.tech_stack` — list of `{layer, technology}` row dicts
- `overview.project_structure` — raw section text (string, includes the fenced text-tree)
- `overview.entry_points` — list of `{entry_point, path, purpose}` row dicts
- `overview.key_commands` — list of `{command, description}` row dicts
- `overview.module_map` — nested dict keyed by `infrastructure` / `core` / `domain`, each value a list of row dicts
- `overview.cross_module_dependencies` — raw section text (string)
- `overview.application_routes` — list of `{route, component, description}` row dicts
- `overview.navigation_guards` — list of bullet strings
- `overview.test_files` — list of bullet strings
- `overview.packages` — list of bullet strings
- `architecture.architecture_overview` — raw section text (string)
- `architecture.module_structure` — raw section text (string)
- `architecture.patterns` — list of pattern record dicts (`{name, applies_in, snippet_lang, snippet}`)
- `architecture.conventions` — raw section text (string)
- `architecture.layers` — list of bullet strings
- `architecture.cross_cuts` — list of bullet strings
- `architecture.dependency_direction_rules` — list of bullet strings
- `architecture.dependency_overview` — raw section text (string)

Capture as `DOCS_JSON`. The exact per-field shape is owned by the helper's `_parse_overview_md` + `_parse_architecture_md` functions.

```bash
.devforge/lib/configure_helper read-manifests
```

Stdout JSON has one top-level key `packages[]`. Each entry is `{path, manifest, scripts, dependencies, dev_dependencies, build_tool_hint, framework_hint}`, sourced from `.devforge/index.json` (no fresh disk scan). `build_tool_hint` is `vite` / `webpack` / `rollup` / `next` / `tsc` / `null`, derived from dep names. `framework_hint` is the per-package framework derived from dep names (e.g., `Vue` / `React` / `Next.js` / `Express` / `FastAPI` / `null`); meta-frameworks (Next.js, Nuxt, Remix, SvelteKit, Expo) win over their underlying frameworks. Capture as `MANIFESTS_JSON`.

```bash
.devforge/lib/configure_helper read-configs
```

Stdout JSON enumerates config files matched against the helper's fixed basename set (`vite.config.{ts,js,mjs}`, `next.config.{ts,js,mjs}`, `nuxt.config.{ts,js}`, `webpack.config.{ts,js}`, `vitest.config.{ts,js}`, `jest.config.{ts,js}`, `.env`, `.env.local`, `.env.development`). Each match carries its file content (capped at 10 KB; `truncated: true` when the cap is hit). Capture as `CONFIGS_JSON`.

If any read subcommand exits non-zero, surface its stderr verbatim and ABORT — Phase 2 cannot compose without all four inputs.

## Phase 2 — Compose detection-derived values

Orchestrator-direct compose (NO Task-tool dispatch to any subagent — same convention as `/generate-docs` Phase 2). The orchestrator (this thread) reads the four Phase 1 JSON outputs inline and synthesizes 23 detection-derived values in memory. Values are NOT yet persisted; Phase 3's bulk confirmation decides what gets written. Composition rules per field:

**Identity**

- `PROJECT_NAME` — root manifest `name` from `MANIFESTS_JSON.packages[]` (the entry whose `path` equals `.` or, for wrapper mode, the entry matching `INIT_JSON.project_root`). Fall back to the basename of `INIT_JSON.project_root` when no root manifest exists.
- `PROJECT_DESCRIPTION` — the Purpose paragraph from `DOCS_JSON.overview` (`docs/overview.md` `## Purpose` section). One concise sentence; trim whitespace.
- `PROJECT_TYPE` — single-label classification from the legacy 13-category taxonomy (web app / web service / CLI tool / library/SDK / desktop app / mobile app / data pipeline / ML model / browser extension / game / framework / static site / monorepo platform). Pick the label that best matches the composed `FRAMEWORKS` + `LANGUAGES` signal.

**Stack**

- `PRIMARY_LANGUAGE` — Tech Stack `Language` row from `DOCS_JSON.overview` (the dominant language across the workspace).
- `LANGUAGES` — comma-separated list across all detected packages, derived per-package from `MANIFESTS_JSON.packages[].manifest` (e.g., `package.json` → JavaScript/TypeScript inferred from `.ts` files in the package, `pyproject.toml` → Python).
- `FRAMEWORKS` — Tech Stack `Framework` row from `DOCS_JSON.overview`, comma-separated.
- `ARCHITECTURES` — comma-separated; extract from `DOCS_JSON.architecture.architecture_overview` (e.g., "Clean Architecture", "Turborepo monorepo").
- `PROJECT_NATURES` — comma-separated atomic nature labels derived from `PROJECT_TYPE` + `FRAMEWORKS`. Closed vocabulary: `web`, `backend`, `mobile`, `desktop`, `cli`, `library`, `plugin`, `data`, `ml`, `game`, `infra`, `docs`. Phase 5.2 (`prune-agents`) consumes this field to decide which `.claude/agents/*.md` to delete; empty value blocks Phase 5.2 with helper exit 2 and is flagged by Phase 7 `verify`. Composition rules (apply LLM judgment when input doesn't fit cleanly):
  - `PROJECT_TYPE == "web app"` + frontend frameworks (Vue/React/Angular/Svelte/etc.) → `web`
  - `PROJECT_TYPE == "web service"` + backend frameworks (Express/FastAPI/Django/Rails/etc.) → `backend`
  - `PROJECT_TYPE == "fullstack"` OR (frontend AND backend frameworks present in the same project) → `web, backend`
  - `PROJECT_TYPE == "mobile app"` + mobile frameworks (React Native/Flutter/SwiftUI/Jetpack/etc.) → `mobile`
  - `PROJECT_TYPE == "desktop app"` → `desktop`
  - `PROJECT_TYPE == "library/SDK"` → `library`; `"browser extension"` → `plugin`; `"CLI tool"` → `cli`
  - `PROJECT_TYPE == "data pipeline"` → `data`; `"ML model"` → `data, ml`; `"game"` → `game`; `"static site"` / `"framework"` / `"monorepo platform"` → choose the closest match (`docs` / `library` / `infra`) based on detected `FRAMEWORKS`
  - For monorepos exposing multiple natures (e.g., `apps/web` + `apps/api` from `MANIFESTS_JSON.packages[]`), include each detected nature as a separate atomic value (e.g., `web, backend`).
- `ERROR_HANDLINGS` — comma-separated; extract from `DOCS_JSON.architecture.patterns` + `DOCS_JSON.architecture.conventions` (e.g., "Either monad", "thrown exceptions with global handler").
- `API_LAYERS` — Tech Stack `API Layer` row from `DOCS_JSON.overview`, comma-separated.
- `TESTINGS` — Tech Stack `Testing` row from `DOCS_JSON.overview`, comma-separated.
- `BUILD_TOOLS` — Tech Stack `Build Tool` row from `DOCS_JSON.overview` plus per-package `build_tool_hint` from `MANIFESTS_JSON`, deduplicated, comma-separated.

**Per-package**

- `BUILD_COMMANDS` — comma-separated list aligned per-package; each entry is the package's `scripts.build` from `MANIFESTS_JSON.packages[]`. When a package lacks a `build` script, emit the ecosystem default (`npm run build` for `package.json`, `cargo build` for `Cargo.toml`, etc.).
- `TYPE_CHECK_COMMANDS` — comma-separated; per-package `scripts.typecheck` or `scripts.tsc` from `MANIFESTS_JSON`. When absent, emit `tsc --noEmit` for TypeScript packages, `mypy .` for Python packages, or `N/A` when no type checker applies.
- `LINT_COMMANDS` — comma-separated; per-package `scripts.lint`. When absent, emit `N/A`.
- `TEST_COMMANDS` — comma-separated; per-package `scripts.test`. When absent, emit `N/A`.
- `PACKAGE_STACKS` — composite per-package record list. Each record is `{path, language, framework, build_tool, build_command, type_check_command, lint_command, test_command}`. Per-record fields:
  - `path` — project-relative path matching `INIT_JSON.packages_detected[].path`.
  - `language` — derived per-package from manifest extension (`package.json` → TypeScript when `*.ts` files in package, else JavaScript; `pyproject.toml` → Python; `Cargo.toml` → Rust; etc.).
  - `framework` — `MANIFESTS_JSON.packages[<path>].framework_hint` VERBATIM. Do NOT inherit the project-level top framework. A package that does not import a recognized framework gets `null` (helper returns null when no framework dep is present). This prevents mis-attributing e.g. `Vue` to a pure-TS domain package whose only deps are workspace siblings + utility libs.
  - `build_tool` — `MANIFESTS_JSON.packages[<path>].build_tool_hint` verbatim.
  - `build_command` / `type_check_command` / `lint_command` — same per-package values used by the flat string-arrays above; `test_command` is derived separately (see the next bullet) — it does NOT follow the flat arrays' `N/A`-when-absent rule.
  - `test_command` — `MANIFESTS_JSON.packages[<path>].scripts.test` (or the ecosystem-equivalent test script). `null` when the package has no test script — do NOT invent an ecosystem-default guess.

**Verbatim from docs/**

- `PROJECT_STRUCTURE` — `DOCS_JSON.overview.project_structure` raw section text, verbatim (already a single string from the helper's section extractor; pass to `set-project-structure --text` unchanged).
- `DEV_COMMANDS` — reconstruct a markdown table from `DOCS_JSON.overview.key_commands[]` (parsed list of `{command, description}` row dicts). Emit a header row `| Command | Description |`, an alignment row `|---------|-------------|`, then one body row per entry with the `command` and `description` cells; pass the resulting table text to `set-dev-commands --text`. Empty list → empty string.
- `ARCHITECTURE_DETAILS` — `DOCS_JSON.architecture.architecture_overview` raw section text, verbatim (single string from the section extractor; pass to `set-architecture-details --text` unchanged).

**AC runtime (best-effort detection)**

- `AC_RUNTIME_URL` — extract from matched configs in `CONFIGS_JSON` (e.g., `vite.config.*` `server.host` + `server.port`; `next.config.*` `server.port`; `webpack.config.*` `devServer.host` + `devServer.port`). Compose `http://<host>:<port>`. Empty string when no config exposes a dev-server binding.
- `AC_RUNTIME_API_BASE` — extract from `.env*` matches in `CONFIGS_JSON` (`VITE_API_URL` / `NEXT_PUBLIC_API_URL` / `REACT_APP_API_URL`). Empty string when none present.
- `AC_RUNTIME_CLI_COMMAND` — manifest `scripts.dev` or `scripts.start` from `MANIFESTS_JSON` (root or workspace-root package). Empty string when neither script exists.

## Phase 3 — Bulk-confirmation prompt

Plain prose echo, NOT AskUserQuestion (multi-line content cannot fit AskUserQuestion's single-line question text constraint). Display all 23 detection-derived values from Phase 2 in a fenced block, grouped by category, then ask the user to confirm or override.

**Stop discipline (mandatory).** After emitting the echo block below, this phase MUST end the assistant turn and wait for the user's reply. Do NOT advance to Phase 4 setters in the same turn. Do NOT call any `set-*` subcommand in the same turn. Do NOT call any tool after the echo — the echo is the final output of the turn. The user replies organically; the next turn begins with their reply, which is parsed per the rules below. Plain-prose prompts have no harness-level "wait for user" affordance, so the LLM-level stop is the only mechanism preventing accidental auto-advance through the bulk confirmation.

Echo template (substitute `<...>` with the Phase 2 composed values):

```
Here's what /init-forge + /generate-docs found and what /configure proposes:

Project:
- name: <PROJECT_NAME>
- description: <PROJECT_DESCRIPTION>
- type: <PROJECT_TYPE>

Stack:
- primary_language: <PRIMARY_LANGUAGE>
- languages: <LANGUAGES>
- frameworks: <FRAMEWORKS>
- architectures: <ARCHITECTURES>
- project_natures: <PROJECT_NATURES>
- error_handlings: <ERROR_HANDLINGS>
- api_layers: <API_LAYERS>
- testings: <TESTINGS>
- build_tools: <BUILD_TOOLS>

Per-package commands:
- build_commands: <BUILD_COMMANDS>
- type_check_commands: <TYPE_CHECK_COMMANDS>
- lint_commands: <LINT_COMMANDS>
- test_commands: <TEST_COMMANDS>
- package_stacks: <count> packages — <list path entries>

Verbatim from docs/:
- project_structure: (<N> lines from docs/overview.md ## Project Structure)
- dev_commands: (<N> lines from docs/overview.md ## Key Commands)
- architecture_details: (<N> lines from docs/architecture.md ## Architecture Overview)

AC runtime (detected):
- ac_runtime_url: <AC_RUNTIME_URL>
- ac_runtime_api_base: <AC_RUNTIME_API_BASE>
- ac_runtime_cli_command: <AC_RUNTIME_CLI_COMMAND>

Reply 'yes' to confirm all, 'cancel' to abort, or list overrides one per line as 'field: value' (e.g., 'project_type: CLI tool'). For string-array fields whose values contain literal commas (e.g., TypeScript generic syntax `Either<DataError, T>`), supply the value as a JSON array: `error_handlings: ["Either<DataError, T>", "BLoC notifications"]`.
```

For the three verbatim fields (`project_structure`, `dev_commands`, `architecture_details`), echo the line count instead of inlining the full text — they are large blocks already visible in `docs/overview.md` + `docs/architecture.md`. The user can override by re-typing the field followed by the replacement text on the same line; multi-line overrides for these three fields are rare in practice.

### Parsing the user reply

- Reply equals `yes` (case-insensitive, exact after strip) → apply all 23 Phase 2 values via setters.
- Reply equals `cancel` (case-insensitive, exact after strip) → ABORT cleanly: "Run `/configure` again when you're ready to review the detected values." Leave `configure.yaml` in its post-`reset` defaults state. Do not advance to Phase 4.
- Otherwise → parse line-by-line as `<field>: <value>`. Field names are case-insensitive; tolerate either dashed (`project-name`) or underscore-separated (`project_name`) keys. Apply the user's override for matched lines; apply the Phase 2 composed value for every other field.
- Reply not parsable as any of the above (no `yes`, no `cancel`, no `field: value` lines) → re-prompt: "I couldn't parse your reply. Reply 'yes' to confirm all, 'cancel' to abort, or list overrides one per line in 'field_name: value' format." Allow up to 2 retries (3 total attempts). After the third invalid reply, fall back to applying all Phase 2 values as confirmed and warn the user: "Proceeding with detected values; re-run `/configure` to revise."

### Setter mapping

Apply each accepted/overridden value via the matching setter. Setter argument shape is taken verbatim from the helper's argparse:

| Field                    | Setter                                       |
| ------------------------ | -------------------------------------------- |
| `project_name`           | `set-project-name <value>`                   |
| `project_description`    | `set-project-description <value>`            |
| `project_type`           | `set-project-type <value>`                   |
| `primary_language`       | `set-primary-language <value>`               |
| `languages`              | `set-languages <comma-sep-list>`             |
| `frameworks`             | `set-frameworks <comma-sep-list>`            |
| `architectures`          | `set-architectures <comma-sep-list>`         |
| `project_natures`        | `set-project-natures <comma-sep-list>`       |
| `error_handlings`        | `set-error-handlings <comma-sep-list>`       |
| `api_layers`             | `set-api-layers <comma-sep-list>`            |
| `testings`               | `set-testings <comma-sep-list>`              |
| `build_tools`            | `set-build-tools <comma-sep-list>`           |
| `build_commands`         | `set-build-commands <comma-sep-list>`        |
| `type_check_commands`    | `set-type-check-commands <comma-sep-list>`   |
| `lint_commands`          | `set-lint-commands <comma-sep-list>`         |
| `test_commands`          | `set-test-commands <comma-sep-list>`         |
| `project_structure`      | `set-project-structure --text <verbatim>`    |
| `dev_commands`           | `set-dev-commands --text <verbatim>`         |
| `architecture_details`   | `set-architecture-details --text <verbatim>` |
| `ac_runtime_url`         | `set-ac-runtime-url <value>`                 |
| `ac_runtime_api_base`    | `set-ac-runtime-api-base <value>`            |
| `ac_runtime_cli_command` | `set-ac-runtime-cli-command <value>`         |

For `package_stacks`: serialize Phase 2's composed package list (already in memory) into a SINGLE JSON object and pipe it once to the bulk verb `set-package-stacks`, which validates each record, then replaces the whole `package_stacks` list in one call. The JSON top-level shape is `{"package_stacks": [<record>, ...]}`; every record carries all 8 keys `{path, language, framework, build_tool, build_command, type_check_command, lint_command, test_command}`. Absent values are explicit JSON `null` — never omitted, never an empty string. `path` and `language` are required and must be non-null; the other 6 keys accept `null`.

Pipe the JSON to the helper on stdin via a quoted heredoc so it is passed verbatim (the `'JSON'` delimiter suppresses shell expansion):

```bash
.devforge/lib/configure_helper set-package-stacks <<'JSON'
{
  "package_stacks": [
    {
      "path": "apps/web",
      "language": "TypeScript",
      "framework": "Vue",
      "build_tool": "vite",
      "build_command": "npm run build",
      "type_check_command": "vue-tsc --noEmit",
      "lint_command": "eslint .",
      "test_command": "vitest run"
    },
    {
      "path": "packages/core",
      "language": "TypeScript",
      "framework": null,
      "build_tool": null,
      "build_command": "tsc -b",
      "type_check_command": "tsc --noEmit",
      "lint_command": "eslint .",
      "test_command": null
    }
  ]
}
JSON
```

Include one object per detected package. Every record carries all 8 keys `{path, language, framework, build_tool, build_command, type_check_command, lint_command, test_command}`; absent optional values are the literal JSON `null` (unquoted) — never an omitted key, never an empty string. `path` and `language` are required and must be non-null; the other 6 keys accept `null`.

**MUST NOT**: do not build a whitespace-, tab-, or comma-delimited intermediate table; do not iterate with a bash `read` loop; do not call `add-package-stack` per record. Compose the JSON object once and pipe it once. A delimited `read` loop collapses empty fields and shifts every subsequent column left, silently corrupting records.

If `set-package-stacks` exits non-zero, capture its stderr, surface it verbatim, fix the offending record in the JSON, and retry the one call (cap at 3 retries). `set-package-stacks` validates every record before entering the atomic `_state_transaction` and replaces the whole list in one write, so a failure never half-writes `configure.yaml` — the `package_stacks` field is simply left unpopulated while the other Phase 3 fields are already written. On the 4th failure, surface the failure to the user and ABORT; the user can re-run `/configure`, or read the JSON validation error, fix the source data, and re-run.

## Phase 4 — Sequential user-only prompts

These six fields cannot be derived from filesystem scan; each requires a user choice. One AskUserQuestion per question, in order. Persist each answer via its setter before issuing the next question.

### Q9: Workflow Enforcement

Use AskUserQuestion: "How strict should workflow enforcement be?"

- `Strict` (Recommended) — every step requires explicit approval; no shortcuts
- `Moderate` — approval gates at major milestones; smaller decisions auto-proceed
- `Light` — minimal gating; rely on conventions over enforcement

Save via `.devforge/lib/configure_helper set-workflow-enforcement <choice>`.

### Q10: AI Attribution

Use AskUserQuestion: "Add AI attribution footer to commit messages?"

- `Yes` (Recommended) — commits include `Generated with Claude Code` footer
- `No` — commit messages stay clean of attribution

Save via `.devforge/lib/configure_helper set-ai-attribution <choice>`.

### Q11: Claude Tier Models

Three sequential AskUserQuestion calls — Q11.1 (think), Q11.2 (do), Q11.3 (verify). See `.claude/commands/configure/references/q11-tiers.md` for the full prompt text, options, and recommended-defaults rationale per tier.

### Q12: AC Verification Mode

Use AskUserQuestion to pick the mode, then conditionally ask the runtime triple. See `.claude/commands/configure/references/q12-ac.md` for the full prompt text, the four mode options, and the conditional Q12.1 / Q12.2 / Q12.3 follow-up logic that runs only when the user selects `runtime-assisted`.

## Phase 5 — Render + prune + substitute

Once `configure.yaml` is fully populated (29 fields set), render the consolidated JSON config, prune the agents directory against `project_natures`, then substitute the templates. Three sub-steps in fixed order: render-config → prune-agents → substitute-templates. The order matters: `render-config` derives `AGENT_LIST` from the on-disk agent listing, so any pruning must happen AFTER `render-config` writes the snapshot to `project-config.json` (otherwise the substituted `{{AGENT_LIST}}` would still advertise dropped agents). `substitute-templates` then walks the post-prune file set, so dropped agents are not substituted.

### Phase 5.1 — Render config

```bash
.devforge/lib/configure_helper render-config
```

`render-config` reads `.devforge/configure.yaml` + `.devforge/init.yaml`, derives `AGENT_LIST` from `.claude/agents/*.md` filenames, and writes `.devforge/project-config.json` atomically. Exit codes:

- Exit 0 → success.
- Exit 1 → `.devforge/init.yaml` missing or unreadable, OR `.devforge/configure.yaml` unreadable, OR write to `project-config.json` failed. Surface stderr verbatim and ABORT.

### Phase 5.2 — Prune agents

Run `prune-agents` in dry-run first to surface keep/drop decisions, then ask the user to confirm + bulk-override before applying.

```bash
.devforge/lib/configure_helper prune-agents
```

The dry-run subcommand reads `project_natures` from `.devforge/configure.yaml`, walks `<install_root>/.claude/agents/*.md`, parses each file's `applies_to` frontmatter, and emits a JSON report to stdout with shape `{kept: [...], dropped: [...], decisions: [...]}`. Each `decisions[]` entry is `{name, applies_to, status}` where `status` is `keep` or `drop`. The decision rules (in order, mirroring `_decide_agent` in the helper):

1. `applies_to` missing or unparseable → KEEP (conservative; helper writes a `keep-warning` line to stderr).
2. `"all"` in `applies_to` → KEEP (universal-fit agent).
3. `applies_to ∩ project_natures` non-empty → KEEP.
4. Otherwise → DROP.

Capture the JSON as `PRUNE_REPORT`. If stderr contains any `keep-warning` lines (e.g., agent files with malformed `applies_to`), surface those warnings to the user inline alongside the bulk-confirmation echo below; do NOT auto-drop those agents — they were already classified KEEP by rule 1.

Exit-code interpretation:

- Exit 0 + non-empty `dropped[]` → proceed to the bulk-confirmation echo.
- Exit 0 + empty `dropped[]` → no agents to prune (every agent's `applies_to` already matches `project_natures` or contains `"all"`). Skip the bulk-confirmation prompt entirely; advance to Phase 5.3 silently.
- Exit 1 → I/O failure (cannot load `configure.yaml`, cannot list `.claude/agents/`, cannot read an agent file in apply mode). Surface stderr verbatim and ABORT.
- Exit 2 → `project_natures` unset in `configure.yaml`. Surface stderr verbatim and ABORT — Phase 2 should have populated this field via `set-project-natures` and Phase 3 should have applied it; this exit means the setter didn't fire. Treat as a workflow bug.

Echo template (plain prose; substitute `<...>` with values from `PRUNE_REPORT` and `state["project_natures"]`):

```
Pruning .claude/agents/ for project natures: <project_natures>.

Will KEEP (<N> agents):
  - <agent-name-1> — applies_to: <applies_to-1>
  - <agent-name-2> — applies_to: <applies_to-2>
  ...

Will DROP (<M> agents):
  - <agent-name-1> — applies_to: <applies_to-1>
  - <agent-name-2> — applies_to: <applies_to-2>

Reply 'yes' to apply, 'cancel' to skip pruning, or list overrides one per line as 'keep <name>' or 'drop <name>'.
```

For each `decisions[]` entry, render `applies_to` as a comma-separated list (or the literal token `<missing>` when the helper reported `applies_to: null`).

**Stop discipline (mandatory).** After emitting the echo block, this sub-step MUST end the assistant turn and wait for the user's reply. Do NOT call `prune-agents --apply` in the same turn. Do NOT call any setter or any other tool. Same rule as Phase 3's bulk-confirmation echo: plain-prose prompts have no harness-level "wait for user" affordance, so the LLM-level stop is the only mechanism preventing accidental auto-advance.

#### Parsing the user reply

- Reply equals `yes` (case-insensitive, exact after strip) → invoke `prune-agents --apply` to apply the helper's decisions exactly:

  ```bash
  .devforge/lib/configure_helper prune-agents --apply
  ```

  Surface its stdout JSON for transparency, then advance to Phase 5.3.

- Reply equals `cancel` (case-insensitive, exact after strip) → SKIP pruning entirely; no agents deleted; advance to Phase 5.3. This is a valid choice — the user retains every agent regardless of `project_natures` overlap.

- Reply contains override lines of the form `keep <agent-name>` or `drop <agent-name>` (one per line; case-insensitive verb; agent name matches a `decisions[].name` value) → adjust the kept/dropped sets accordingly:
  - `keep <name>` → move `<name>` from `dropped[]` to `kept[]` (no-op if already in `kept[]`).
  - `drop <name>` → move `<name>` from `kept[]` to `dropped[]` (no-op if already in `dropped[]`).
  - Override lines may be interleaved with a `yes`/`cancel` token; if neither is present, treat the reply as an implicit `yes` after the override pass.

  After resolving the final `dropped[]` set, the orchestrator deletes those files directly (the helper has no per-agent flag — `--apply` deletes exactly the helper's decisions, not the override-adjusted set):

  ```bash
  rm <install_root>/.claude/agents/<name>.md   # one call per name in the final dropped[]
  ```

  Use absolute paths; do not rely on prior `cd` state. Then advance to Phase 5.3.

- Reply unparseable (no `yes`, no `cancel`, no recognizable override lines, or override lines reference unknown agent names) → re-prompt once with the parsing rules clarified. On the second invalid reply, fall back to applying the helper's exact decisions (`prune-agents --apply`) and warn the user: "Proceeding with helper's pruning decisions; re-run `/configure` to revise."

### Phase 5.3 — Substitute templates

```bash
.devforge/lib/configure_helper substitute-templates
```

`substitute-templates` reads `.devforge/project-config.json` + `.devforge/init.yaml`, walks `CLAUDE.md` + every `.claude/agents/*.md` file remaining after Phase 5.2, and replaces every `{{KEY}}` placeholder atomically per file. Exit codes:

- Exit 0 → every template substituted; no `{{KEY}}` markers remain.
- Exit 1 → `project-config.json` missing or malformed, OR `CLAUDE.md` missing, OR a per-file write failed. Surface stderr verbatim and ABORT. (Note: `.devforge/init.yaml` missing is NOT an exit-1 condition for this subcommand — substitute-templates falls back to empty `packages_detected` when init.yaml is absent. The init.yaml dependency is enforced earlier by Phase 0's pre-flight gate and by `render-config` exit 1.)
- Exit 2 → at least one template contained a placeholder the helper cannot resolve. Stderr enumerates the unknown placeholders per file. Failed files are NOT modified (atomic per-file). Surface stderr verbatim and ABORT — the project state is partial; the user must extend the substitution map (helper-side) before re-running.

## Phase 6 — Exclude framework folders from project linters

Exclude the framework's installed folders (`.claude/`, `.devforge/`, `specs/`, `bugs/`, `research/`, `discover/`, `audits/` — NOT `docs/`) from the CONSUMER project's own linters and formatters, so the project's prettier/ruff/eslint/etc. don't reformat or flag the framework's templates + helper code. Run `lint-ignore` in dry-run first to surface what would change, then ask the user to confirm before applying. This phase is NON-FATAL and writes into the user's OWN tooling config files — on any error it SKIPS rather than aborts, and on an ambiguous reply it defaults to SKIP rather than apply.

```bash
.devforge/lib/configure_helper lint-ignore
```

The dry-run subcommand scans `<install_root>` for each tool's config file (`--install-root` defaults to the parent of `--devforge-dir`, same as other configure verbs) and emits a JSON report to stdout with shape `{entries: [...], summary: {...}}`. Handlers run by config-file PRESENCE — a handler is a no-op when its tool's config file is absent under `<install_root>`; there is no language-based scoping. The scanned tool set is prettier, eslint, markdownlint (cli + cli2), flake8, biome, ruff, black, isort, mypy, pylint, rustfmt, rubocop, golangci-lint, VS Code, and JetBrains. Each `entries[]` record carries `tool` + `action` (`auto` or `manual`):

- `auto` entries get written by `--apply`. Shape: `{tool, file, action: "auto", status, lines: [...], preemptive}` where `status` is `would-add` / `would-create` / `already-present`, `lines[]` are the ignore-file lines that would be added, and `preemptive: bool` is `true` when at least one framework folder does not yet exist under `install_root` at setup (the exclusion registers the folder before workflow commands create it). The AUTO-tier tools (written by `--apply`) are prettier, eslint with a legacy `.eslintrc`, markdownlint-cli (`.markdownlintignore`), markdownlint-cli2 in its JSON variant, flake8, biome when its JSON config parses, ruff / black / isort / mypy / pylint in their clean `pyproject.toml` cases, rustfmt in its clean case, and VS Code (`.vscode/settings.json`).
- `manual` entries are printed instructions the user must hand-add — the helper NEVER edits those files. Shape: `{tool, file, action: "manual", status: "pending-manual", preemptive, instruction}`. The always-manual tools (eslint flat-config `eslint.config.*`, golangci-lint, rubocop, JetBrains) are never auto-edited. Some AUTO-tier tools also fall back to a `manual` entry when a safe auto-edit isn't possible — markdownlint-cli2 in its YAML variant, biome when its JSONC config fails to parse, ruff / black / isort / mypy / pylint when the `pyproject.toml` table already exists in a non-idempotent state or only a sub-table exists, and rustfmt when its `ignore` key exists non-idempotently. In every `manual` case the user applies the exclusion themselves from the printed `instruction` text. (VS Code is AUTO-tier, not manual.)

Capture the JSON as `LINT_REPORT`.

Exit-code interpretation:

- Exit 1 → unexpected scanning error (stderr has the message). Surface stderr verbatim and SKIP this phase — do NOT abort `/configure`. Linter-exclusion is a convenience, not a correctness gate; advance to Phase 7. (Contrast: Phase 5.3 `substitute-templates` and Phase 7 `verify` ABORT on failure; this phase does not.)
- Exit 0 with no actionable entries — no `auto` entry in `would-add` / `would-create` status AND no `manual` entry in `pending-manual` status → nothing to do (every applicable ignore file already excludes the framework folders). Skip the bulk-confirmation prompt entirely; advance to Phase 7 silently.
- Exit 0 with actionable entries (any `auto` entry in `would-add` / `would-create`, or any `manual` entry) → proceed to the bulk-confirmation echo.

Echo template (plain prose; substitute `<...>` with values from `LINT_REPORT`):

```
Excluding framework folders (.claude/, .devforge/, specs/, bugs/, research/, discover/, audits/) from your project's linters.

Automatic — will add/create these (reply 'yes' to apply):
  <tool-1> → <file-1>:
    + <line-1>
    + <line-2>
  <tool-2> → <file-2>:  (folder not present yet — pre-emptive)
    + <line-1>
  ...

Manual — add these yourself:
  - <tool-3>: <instruction-3>
  - <tool-4>: <instruction-4>

Reply 'yes' to apply the automatic exclusions, or 'cancel' to skip.
```

List each `auto` entry grouped by `tool` → `file`, showing each line from its `lines[]` (mark `would-create` and `preemptive` entries, e.g. append `(folder not present yet — pre-emptive)`). List each `manual` entry's `instruction` under the separate "Manual — add these yourself" section. Omit either section when it has no entries.

**Stop discipline (mandatory).** After emitting the echo block, this phase MUST end the assistant turn and wait for the user's reply. Do NOT call `lint-ignore --apply` in the same turn. Do NOT call any setter or any other tool. Same rule as Phase 3's bulk-confirmation echo and Phase 5.2's prune-agents echo: plain-prose prompts have no harness-level "wait for user" affordance, so the LLM-level stop is the only mechanism preventing accidental auto-advance.

### Parsing the user reply

- Reply equals `yes` (case-insensitive, exact after strip) → invoke `lint-ignore --apply` to write the `auto`-tier changes (the `manual`-tier files are left untouched):

  ```bash
  .devforge/lib/configure_helper lint-ignore --apply
  ```

  Surface its stdout JSON (what was written) for transparency, then restate each `manual` entry's `instruction` so the user can hand-apply those exclusions. Advance to Phase 7.

- Reply equals `cancel` (case-insensitive, exact after strip) → SKIP this phase; no ignore files written. Note that the `manual` instructions are still worth doing. Advance to Phase 7.

- Reply unparseable (no `yes`, no `cancel`) → re-prompt once with the choice restated. On the second invalid reply, default to SKIP — write nothing — and warn the user: "Skipping framework-folder linter exclusions; re-run `/configure` to apply them." Do NOT auto-apply on an ambiguous reply: unlike Phase 5.2's prune-agents (which defaults to apply), this phase writes into the user's OWN project tooling configs, so default-skip is the safer fallback.

## Phase 7 — Verify + report

```bash
.devforge/lib/configure_helper verify
```

`verify` cross-checks `.devforge/configure.yaml` + `.devforge/project-config.json`: every required field populated; AC runtime fields exempt unless `ac_verification_mode == runtime-assisted`; round-trip identity between the two files. Exit 0 = pass; exit 2 = at least one violation (each enumerated on stderr). On exit 2, surface stderr verbatim and ABORT — the user must address the violations before `/constitute`.

`project_natures` is one of the required fields: an empty value is flagged as a violation (no AC-mode exemption applies). Phase 2's composition rule and Phase 3's `set-project-natures` setter are jointly responsible for populating it; if `verify` reports `PROJECT_NATURES is empty`, Phase 5.2's `prune-agents` would have already aborted with exit 2 before reaching Phase 7, so this violation only appears when `verify` is invoked standalone after a partial earlier run.

Scope note: `verify` does NOT re-scan `CLAUDE.md` or `.claude/agents/*.md` for remaining `{{KEY}}` markers. Template-substitution completeness is enforced by Phase 5's `substitute-templates` exit 0; if Phase 5 succeeded, the templates are clean. If you re-run only `verify` standalone after a partial Phase 5 (e.g., aborted mid-substitution), it will not re-detect template markers — re-run `substitute-templates` to re-establish that guarantee.

```bash
.devforge/lib/configure_helper summary
```

`summary` is read-only; it prints a deterministic field-by-field report to stdout. After the helper runs, copy its stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase).

## Closing

`/configure` is complete. The 29 configuration fields are persisted in `.devforge/configure.yaml`; `.devforge/project-config.json` carries all 37 keys; `.claude/agents/` is pruned to the agents whose `applies_to` overlaps `project_natures` (or every shipped agent retained when the user replied `cancel` in Phase 5.2); `CLAUDE.md` and every remaining file under `.claude/agents/` is fully substituted; the framework's folders were excluded from the project's linters (Phase 6 — applied, skipped on `cancel`/error, or nothing-to-do). Tell the user: "Run `/constitute` next."
