---
name: constitute
description: Synthesize constitution.md from /configure + /generate-docs outputs (schema-anchored)
disable-model-invocation: true
---

# /constitute — Project Constitution

`/constitute` is the fourth and last command in the 4-command sequence (`/init-forge` → `/generate-docs` → `/configure` → `/constitute`). It consumes the structural fields persisted by `/init-forge`, the configuration fields persisted by `/configure`, and the docs corpus produced by `/generate-docs`; populates `.devforge/constitute.json` via `.devforge/lib/constitute_helper` setters; renders `<install_root>/constitution.md` with seven schema-anchored sections (Section 7 emitted only when `mode == greenfield`); verifies the round-trip and content quality; and prints a deterministic summary.

## Outputs of this phase

- `.devforge/constitute.json` — canonical state. Owned + shaped by the helper; mutated only via setter subcommands.
- `.devforge/constitute.json.lock` — fcntl `LOCK_EX` sidecar; `_state_transaction` plumbing.
- `<install_root>/constitution.md` — render artifact rebuilt from `.devforge/constitute.json` on every `render` call. Lives at install root in both standalone and wrapper modes (parallels `docs/`); never inside `project_root`.

## Phase 0 — Pre-flight gate

Verify each predecessor artifact exists; abort the run on the first miss.

```bash
test -f .devforge/init.yaml
test -f .devforge/configure.yaml
test -f docs/overview.md
test -f docs/architecture.md
test -f docs/glossary.md
```

- If `.devforge/init.yaml` is missing → ABORT: "missing .devforge/init.yaml — run `/init-forge` first."
- If `.devforge/configure.yaml` is missing → ABORT: "missing .devforge/configure.yaml — run `/configure` first."
- If `docs/overview.md` is missing → ABORT: "missing docs/overview.md — run `/generate-docs` first."
- If `docs/architecture.md` is missing → ABORT: "missing docs/architecture.md — run `/generate-docs` first."
- If `docs/glossary.md` is missing → ABORT: "missing docs/glossary.md — run `/generate-docs` first."

## Phase 1 — Reset + pull inputs

Reset helper state, then invoke each `read-*` subcommand in order. Every read subcommand emits JSON to stdout; capture each output into a named variable so Phase 2 has all four inputs in memory before composing.

```bash
.devforge/lib/constitute_helper reset
```

`reset` writes a fresh defaults JSON at `.devforge/constitute.json` (every schema field reset to its null/empty default). Idempotent on re-runs.

```bash
.devforge/lib/constitute_helper read-init
```

Stdout JSON carries every field in `.devforge/init.yaml`: `project_root`, `workspace_mode`, `project_state`, `default_branch`, `packages_detected[]`. Capture as `INIT_JSON`.

```bash
.devforge/lib/constitute_helper read-configure
```

Stdout JSON carries every field in `.devforge/configure.yaml` (29 keys, including `project_name`, `project_description`, `project_type`, `primary_language`, `languages`, `frameworks`, `architectures`, `project_natures`, `error_handlings`, `api_layers`, `testings`, `build_tools`, `workflow_enforcement`, etc.). Capture as `CONFIGURE_JSON`.

```bash
.devforge/lib/constitute_helper read-docs
```

Stdout JSON has two top-level keys: `overview` and `architecture`. The shape is owned by `configure_helper`'s `_parse_overview_md` + `_parse_architecture_md` parsers (reused by `read-docs`). Phase 2 consumes the following keys:

- `architecture.architecture_overview` — raw section text (string)
- `architecture.module_structure` — raw section text (string)
- `architecture.patterns` — list of pattern record dicts (`{name, applies_in, snippet_lang, snippet}`). `name` is the pattern heading; `applies_in` is the "Applies in:" prose; `snippet_lang` + `snippet` are the fenced code block. Phase 2 composes rule text from `name` + `applies_in` (no pre-extracted `rule` field exists)
- `architecture.conventions` — raw section text (string)
- `architecture.layers` — list of bullet strings
- `architecture.dependency_direction_rules` — list of bullet strings
- `overview.tech_stack` — list of `{layer, technology}` row dicts
- `overview.module_map` — nested dict keyed by `infrastructure` / `core` / `domain`

Capture as `DOCS_JSON`.

```bash
.devforge/lib/constitute_helper read-glossary
```

Stdout JSON is a list of term records. Each record has shape `{term, definition, used_in, related}` parsed from `docs/glossary.md` `## <term>` blocks. Empty file → `[]`. Capture as `GLOSSARY_JSON`.

If any read subcommand exits non-zero, surface its stderr verbatim and ABORT — Phase 2 cannot compose without all four inputs.

## Phase 2 — Compose section content

Orchestrator-direct compose (NO Task-tool dispatch to any subagent — same convention as `/configure` Phase 2 and `/generate-docs` Phase 2). The orchestrator (this thread) reads the four Phase 1 JSON outputs inline and synthesizes per-section content in memory. Values are NOT yet persisted; Phase 3's bulk confirmation decides what gets written via setters.

Compose the following per-section content. The structural shape (section numbers, bucket assignment, rule-tag enum) is locked by the helper; only the rule TEXT, table CELLS, and code-example CONTENT are LLM-composed. Authoring guidance (opening prose, tag distribution, code-example selection, sub-section count expectations) lives in `.claude/commands/constitute/references/section-shapes.md` — read it before composing.

### Section 1 — Project Identity (4 scalars)

- `name` — `CONFIGURE_JSON.project_name`.
- `type` — `CONFIGURE_JSON.project_type`.
- `domain` — one-sentence domain description composed from `GLOSSARY_JSON` key entity terms (the 3-5 most-used terms by `used_in` count).
- `stack` — one-sentence stack summary composed from `CONFIGURE_JSON.languages` + `CONFIGURE_JSON.frameworks` + `CONFIGURE_JSON.architectures` + `CONFIGURE_JSON.build_tools`, comma-separated.

### Section 2 — Architecture Rules (NON-NEGOTIABLE)

Compose 2-4 sub-sections (e.g., 2.1 Layer Boundaries, 2.2 File Organization, 2.3 Dependency Rules) drawing from `DOCS_JSON.architecture.layers` (table-shaped sub-section), `DOCS_JSON.architecture.patterns` (rules + CORRECT/WRONG code-example pairs), `DOCS_JSON.architecture.dependency_direction_rules` (bullet rules), and `DOCS_JSON.architecture.module_structure` (tree code block).

Per-rule tag selection: rules cited from `architecture.md` → `extracted`; rules implied by tooling configuration (tsconfig strict, ESLint rules, etc.) → `enforced`. See `.claude/commands/constitute/references/section-shapes.md` § "Tag distribution" for the full decision rubric.

### Section 3 — Code Quality Standards

Compose 4-7 sub-sections (e.g., 3.1 Type Safety, 3.2 Error Handling, 3.3 Naming Conventions, 3.4 Testing Requirements, 3.5 Documentation, 3.6 Function Length, 3.7 Check Before You Build) drawing from `DOCS_JSON.architecture.patterns` + the code-quality buckets of `DOCS_JSON.architecture.conventions` + universal defaults applicable to every project.

`DOCS_JSON.architecture.conventions` is the raw text of the docs `## Conventions` section, which carries up to six bucket sub-sections rendered as bold-heading labels (`**Naming**`, `**File Organization**`, `**Import Style**`, `**Error Handling**`, `**Styling**`, `**State Management**`). The orchestrator identifies each bucket by its bold-heading sub-section label in that raw text. For Section 3, draw from ONLY the four legacy code-quality buckets — `**Naming**`, `**File Organization**`, `**Import Style**`, `**Error Handling**` — and explicitly EXCLUDE the `**Styling**` and `**State Management**` bold-heading sub-sections of `DOCS_JSON.architecture.conventions` specifically (this exclusion narrows only the conventions-bucket path; state-management content documented in the architecture.md `## Patterns` section still feeds Section 3 via `DOCS_JSON.architecture.patterns`, a separate architecture-tier path). `**State Management**` routes to Section 4 instead (see Section 4 below); `**Styling**` is documented-only and is lifted into neither Section 3 nor Section 4 (see Section 4's styling note).

Per-rule tag selection: project-specific conventions → `extracted` (or `project-specific` when the rule applies only to this project); universal defaults → `universal`; tooling-enforced rules → `enforced`.

### Section 4 — Patterns & Anti-Patterns

Six buckets emitted via `add-pattern-rule` (one bucket per `--bucket` × `--scope` combination):

- `--bucket always --scope universal` — always-do rules that apply to every project (e.g., "Validate inputs at module boundaries").
- `--bucket always --scope project-specific` — always-do rules extracted from `DOCS_JSON.architecture.patterns` and from the `**State Management**` bucket of `DOCS_JSON.architecture.conventions` (state-management conventions phrased as mandates — e.g., "All shared state lives in the store").
- `--bucket never --scope universal` — never-do rules that apply to every project (e.g., "Never swallow errors silently").
- `--bucket never --scope project-specific` — never-do rules extracted from this project's anti-patterns and from the `**State Management**` bucket of `DOCS_JSON.architecture.conventions` (state-management conventions phrased as prohibitions — e.g., "Never mutate state outside a reducer").
- `--bucket prefer --scope universal` — universal preferences (e.g., "Prefer composition over inheritance").
- `--bucket prefer --scope project-specific` — preferences extracted from `DOCS_JSON.architecture.patterns` and from the `**State Management**` bucket of `DOCS_JSON.architecture.conventions` (state-management conventions phrased as preferences — e.g., "Prefer selectors over direct store reads").

**Conventions-bucket routing (where each `DOCS_JSON.architecture.conventions` bucket lands).** The docs `## Conventions` section can carry up to six bold-heading bucket sub-sections; this list records which constitution home each routes to (identified by its bold-heading sub-section label, per Section 3 above):

- `**Naming**` / `**File Organization**` / `**Import Style**` / `**Error Handling**` → Section 3 Code Quality Standards.
- `**State Management**` → Section 4 (the three project-specific buckets above), classified into always / never / prefer by how each rule is phrased — NOT Section 3.
- `**Styling**` → documented-only: lifted into NEITHER Section 3 NOR Section 4. Styling authority is existing components plus the design reference, never the constitution (per `15-AGENT-STANDARDIZATION-PLAN.md`, which set the styling-grounding stance the agents already follow); styling stays captured knowledge in `docs/architecture.md` and never becomes constitution law.

### Section 5 — Domain Rules

Compose 1-3 sub-sections (e.g., 5.1 Key Entities, 5.2 Business Rules, 5.3 External Contracts) from `GLOSSARY_JSON` term records. Entity-classified terms (concrete nouns from the domain — orders, quotes, catalogs, etc.) populate 5.1; rule-classified terms (verbs / constraints — validation rules, lifecycle invariants) populate 5.2; external integrations (APIs, third-party services from `used_in` paths matching `services/`, `integrations/`, `external/`) populate 5.3.

If `GLOSSARY_JSON` has fewer than 3 records AND `mode` resolves to `greenfield` (Phase 4 — runtime-resolved as Phase 1.5; see Phase 4 implementation note for ordering), Phase 4's conditional Q-domain prompt fills the gap with a free-text answer.

### Section 6 — Workflow Rules

Compose 4-6 sub-sections drawing from `CONFIGURE_JSON.workflow_enforcement` + universal workflow defaults (e.g., 6.1 Minimal Changes, 6.2 Read Before Write, 6.3 Search Before Building, 6.4 One Task At A Time, 6.5 Pre-flight Check, 6.6 Project-Specific Workflow). Universal sub-sections carry `tag = "universal"`; project-specific overrides (e.g., "PR titles must include ticket ID" extracted from `CONFIGURE_JSON`) carry `tag = "project-specific"`.

### Section 7 — Scaffolding Guide (greenfield only)

Compose only when `mode == "greenfield"`. Note: `mode` is resolved at runtime by Phase 4's Q-mode (auto-resolved from `INIT_JSON.project_state` when unambiguous; otherwise prompted). Phase 4 appears later in spec text for narrative clarity, but Q-mode executes as Phase 1.5 — see Phase 4's implementation note. Two sub-fields:

- `starter_directories` — comma-separated list (or JSON array) of starter directory names appropriate to the chosen stack (e.g., `src, tests, docs` for a generic project; `apps, packages, tools` for a monorepo).
- `sample_files` — JSON array of `{path, language, content}` records, each a single starter file (e.g., a starter `package.json`, a starter `tsconfig.json`, a starter `README.md`).

When `mode == "existing-codebase"`, skip Section 7 entirely; the helper omits it from render.

## Phase 3 — Per-section bulk-confirmation

Plain prose echo, NOT AskUserQuestion (multi-line content cannot fit AskUserQuestion's single-line question text constraint). Display each section's proposed content in a fenced block, then wait for the user's reply. Sections are confirmed ONE AT A TIME — Section 1 echoes first, awaits reply, applies setters, then Section 2 echoes, etc.

**Stop discipline (mandatory).** After emitting each section's echo block below, this phase MUST end the assistant turn and wait for the user's reply. Do NOT echo the next section in the same turn. Do NOT call any `set-*` / `add-*` subcommand in the same turn. Do NOT call any tool after the echo — the echo is the final output of the turn. The user replies organically; the next turn begins with their reply, parsed per the rules below. Plain-prose prompts have no harness-level "wait for user" affordance, so the LLM-level stop is the only mechanism preventing accidental auto-advance through the bulk confirmation.

### Section 1 echo template (Project Identity)

```
Here's what /constitute proposes for Section 1 — Project Identity:

- name:   <project_identity.name>
- type:   <project_identity.type>
- domain: <project_identity.domain>
- stack:  <project_identity.stack>

Reply 'yes' to apply, 'cancel' to abort the run, or list overrides one per line as 'field: value' (e.g., 'domain: Industrial equipment quoting for dealers').
```

### Section 4 echo template (Patterns & Anti-Patterns — bucket-based, no sub-section numbers)

Section 4 has no numbered sub-sections — its 6 buckets are addressed by `(--bucket × --scope)` not by `--number`. Use this echo template (NOT the Sections 2/3/5/6 template below):

```
Here's what /constitute proposes for Section 4 — Patterns & Anti-Patterns:

Always Do (Universal):
- [<rule.tag>] <rule.text>
- ...

Always Do (Project-Specific):
- [<rule.tag>] <rule.text>
- ...

Never Do (Universal):
- ...

Never Do (Project-Specific):
- ...

Prefer (Universal):
- ...

Prefer (Project-Specific):
- ...

Reply 'yes' to apply this section, 'cancel' to abort the run, or list overrides one per line:
  - 'add pattern <bucket>:<scope>: [<tag>] <text>'   — append to bucket (e.g., 'add pattern always:universal: [universal] Validate inputs at module boundaries')
  - 'drop pattern <bucket>:<scope>:<index>'          — remove rule at 1-based index from the named bucket
  - 'replace pattern <bucket>:<scope>:<index>: [<tag>] <text>' — replace rule at 1-based index
  - 'drop bucket <bucket>:<scope>'                   — drop every rule in the named bucket

Bucket values: always | never | prefer. Scope values: universal | project-specific.
```

Each accepted line maps to one `add-pattern-rule` call (`--bucket <bucket> --scope <scope> --tag <tag> --text "<text>"`). `drop` / `replace` overrides operate against the Phase 2 composed values held in memory before any setter call — apply the merged final list once, not delta-style.

### Sections 2/3/5/6 echo template (rule-bearing sections with numbered sub-sections)

Applies to Sections 2, 3, 5, 6 (each has numbered sub-sections like 2.1, 3.5, etc.). Section 4 uses its own template above. For each section, echo the proposed sub-sections, rules, tables, and code examples as a hierarchical list. Use the following template (substitute `<...>` with Phase 2 composed values):

```
Here's what /constitute proposes for Section <N> — <Section Name>:

### <number> <title>  [<tag>]
<description (one sentence)>

Rules:
- [<rule.tag>] <rule.text>
- [<rule.tag>] <rule.text>
...

Tables (<count>):
- <columns joined by ' | '>: <row_count> rows

Code examples (<count>):
- <label> (<language>): <first non-blank line of code, truncated to 80 chars>
...

Reply 'yes' to apply this section, 'cancel' to abort the run, or list overrides one per line:
  - 'add rule <number>: [<tag>] <text>'             — append a rule to sub-section <number>
  - 'drop rule <number>:<index>'                    — remove rule at 1-based index from sub-section <number>
  - 'replace rule <number>:<index>: [<tag>] <text>' — replace rule at 1-based index
  - 'drop section <number>'                         — drop the entire sub-section
```

For string-array fields whose values contain literal commas (e.g., TypeScript generic syntax `Either<DataError, T>`), supply the value as a JSON array — the helper's `_validate_string_array` accepts either form. Example: `add rule 3.2: [extracted] Errors propagate as ["Either<DataError, T>", "Result<Ok, Err>"]`.

For `add-table` calls with cell content containing internal commas (TS generics, multi-clause sentences), use the JSON-array form for `--columns` and `--rows-json` — see `.claude/commands/constitute/references/empirical-bugs.md` § "JSON-array setter form" for the escape mechanism.

### Section 3.5 echo template (Forcing Functions — config block, not a constitution.md sub-section)

Section 3.5 captures the consumer's `forcing_functions` config block in `.devforge/constitute.json`. It is emitted as a **separate echo block in its own turn** — only AFTER Section 3's reply is parsed and Section 3's `add-section` / `add-rule` / `add-table` / `add-code-example` setters apply. Stop discipline applies per Phase 3 (end the assistant turn after emitting; wait for the user reply). The three rules (`magic_enum_duplication`, `cross_layer_imports`, `any_with_generated_available`) are mechanical detectors backing universal §3.5 ("No magic values") and §3.6 ("Design Principles") of `src/constitution.md`; each rule is independently opt-in. This block targets the top-level `forcing_functions` key in `.devforge/constitute.json` and does NOT add a numbered sub-section to the rendered `constitution.md` — the config is read by `constitute_helper verify-magic-enum` / `verify-cross-layer-imports` / `verify-any-leak` (each rule's `enabled` flag gates whether its detector runs).

Pre-fill defaults before echo:

- `generated_types_dirs` for `magic_enum_duplication` and `any_with_generated_available` — scan `INIT_JSON.packages_detected[]` for package roots that contain `.d.ts` or generated-types subdirectories; the populated default is the list of detected dirs (repo-relative). If detection yields zero candidates, default to `[]`.
- `allowlist_paths` for `magic_enum_duplication` — default `[]`. The user supplies project-specific exemptions (fixtures, logs, scripts).
- `layer_graph` and `layer_dirs` for `cross_layer_imports` — default `{}` (empty). Cross-layer enforcement has no safe default; the user supplies the explicit layer graph when enabling.
- `enabled` for all three rules — default `false` on first-time runs.

Echo template:

```
Here's what /constitute proposes for Section 3.5 — Forcing Functions [config-block]:

magic_enum_duplication:
- enabled:              <true|false>
- generated_types_dirs: <comma-separated dirs>
- allowlist_paths:      <comma-separated globs>

cross_layer_imports:
- enabled:              <true|false>
- layer_graph:          <JSON object or '{}'>
- layer_dirs:           <JSON object or '{}'>

any_with_generated_available:
- enabled:              <true|false>
- generated_types_dirs: <comma-separated dirs>

Allowlist glob behavior: fnmatch does NOT expand '**' across directory separators. Pair every '**/<x>' glob with its top-level twin '<x>' or '<x>/**' to cover both nested and top-level matches.

Reply 'yes' to apply, 'cancel' to abort the run, or list overrides one per line as '<rule>.<field>: <value>':
  - 'magic_enum_duplication.enabled: true'
  - 'magic_enum_duplication.generated_types_dirs: packages/cse-types/src, packages/api-types/src'
  - 'magic_enum_duplication.allowlist_paths: **/*.fixture.ts, *.fixture.ts, scripts/**, scripts'
  - 'cross_layer_imports.enabled: true'
  - 'cross_layer_imports.layer_graph: {"domain": [], "infra": ["domain"], "ui": ["domain", "infra"]}'
  - 'cross_layer_imports.layer_dirs: {"domain": "packages/*/domain/**", "infra": "packages/*/infra/**", "ui": "packages/*/ui/**"}'
  - 'any_with_generated_available.enabled: true'
  - 'any_with_generated_available.generated_types_dirs: packages/cse-types/src'

Field-shape contract: generated_types_dirs and allowlist_paths require comma-separated values; layer_graph and layer_dirs require JSON-object form. See the flag-omission rule paragraph immediately after this echo template for when each field is passed to the setter.
```

Per the stop discipline above (Phase 3 § stop discipline mandatory paragraph), end the assistant turn after emitting this echo block and wait for the user's reply. Apply parsed values via `set-forcing-functions` (one call per rule — three calls total) per the setter mapping below. Flag-omission rule: `--enabled` is required on every call; each bracketed flag (`--generated-types-dirs`, `--allowlist-paths`, `--layer-graph-json`, `--layer-dirs-json`) is passed only when both (a) the rule resolves to `--enabled true` AND (b) the field has a non-empty value. When `enabled` resolves to `false` for a rule, **or** when an optional field has no non-empty value, omit that flag from the setter call. Reply equals `yes` applies the pre-filled defaults; reply equals `cancel` aborts cleanly leaving `.devforge/constitute.json` in its post-Section-3 state. The reply-parsing rules in "Parsing the user reply (per-section)" above apply uniformly (3-attempt retry cap; on the third invalid reply, proceed with proposed values and warn the user).

### Section 7 echo template (greenfield only)

If Phase 4 resolved `mode == "greenfield"`, after Section 6 confirms, echo Section 7:

```
Here's what /constitute proposes for Section 7 — Scaffolding Guide [greenfield-only]:

Starter directories:
- <dir-1>
- <dir-2>
...

Sample files (<N>):
- <path-1>  (<language-1>)
- <path-2>  (<language-2>)
...

Reply 'yes' to apply, 'cancel' to abort the run, or list overrides one per line:
  - 'add dir <name>'           — append a starter directory
  - 'drop dir <name>'          — remove a starter directory
  - 'replace files: <JSON>'    — replace the entire sample_files array (JSON of {path,language,content} records)
```

### Parsing the user reply (per-section)

- Reply equals `yes` (case-insensitive, exact after strip) → apply this section's Phase 2 composed values via the setters listed in the "Setter mapping per section" table below.
- Reply equals `cancel` (case-insensitive, exact after strip) → ABORT cleanly: "Run `/constitute` again when you're ready to review the proposed sections." Leave `.devforge/constitute.json` in its post-`reset` defaults state plus any sections already applied in earlier per-section confirmations. Do not advance to the next section.
- Otherwise → parse line-by-line per the override syntax shown in the section's echo template. Apply each accepted override in order; apply the Phase 2 composed value for every other rule/table/code-example. Tag values are case-insensitive (helper's `_validate_enum` normalizes mixed-case to canonical lowercase / uppercase per enum).
- Reply not parsable as any of the above → re-prompt: "I couldn't parse your reply. Reply 'yes' to confirm, 'cancel' to abort, or use the override syntax shown above." Allow up to 2 retries (3 total attempts). On the third invalid reply, fall back to applying the section's Phase 2 composed values as confirmed and warn: "Proceeding with proposed values for Section <N>; re-run `/constitute` to revise."

After parsing each section's reply, apply the resulting setter calls IN ORDER per section type:

- Section 1: one `set-project-identity` call.
- Sections 2, 3, 5, 6: `add-section` first (creates the sub-section record), then `add-rule` / `add-table` / `add-code-example` referencing that section's `--number`.
- Section 3.5 (Forcing Functions): three `set-forcing-functions` calls (one per rule). Runs after Section 3's setters apply, before the next section's echo. Does NOT issue `add-section` — `forcing_functions` is a top-level config block, not a numbered constitution.md sub-section.
- Section 4: `add-pattern-rule` per accepted pattern (no `add-section` prerequisite — Section 4 has no numbered sub-sections).
- Section 7: one `set-scaffolding-guide` call (greenfield only).

Then advance to the next section's echo (in the next turn — Phase 3 stop discipline still applies between sections).

### Setter mapping per section

For every section in Sections 2, 3, 5, 6 (the rule-bearing sections with numbered sub-sections), the per-section setter sequence is:

```bash
.devforge/lib/constitute_helper add-section \
    --bucket <architecture|code-quality|domain|workflow> \
    --number <N.M> --title "<title>" \
    [--tag <universal|project-specific|greenfield-only>] \
    [--description "<one-sentence opener>"]
# add-section --tag is section_tag enum (3 values); does NOT accept
# 'extracted' or 'enforced' — those belong to add-rule's rule_tag.
# A section extracted from this codebase carries --tag project-specific.

.devforge/lib/constitute_helper add-rule \
    --section <N.M> --tag <extracted|enforced|universal|project-specific> \
    --text "<rule text>"
# add-rule --tag is rule_tag enum (4 values; required).
# repeat per rule

.devforge/lib/constitute_helper add-table \
    --section <N.M> \
    --columns '["<col-1>", "<col-2>", ...]' \
    --rows-json '[["<r1c1>", "<r1c2>"], ["<r2c1>", "<r2c2>"]]'
# repeat per table; --columns + --rows-json both accept JSON-array form

.devforge/lib/constitute_helper add-code-example \
    --section <N.M> \
    --label <CORRECT|WRONG|EXAMPLE> \
    --language <ts|tsx|js|python|json|...> \
    --code "<code content (multi-line OK)>" \
    [--annotation "<short annotation>"]
# repeat per code example
```

Bucket-to-section mapping (locked by the helper's `_SECTION_BUCKET_TO_KEY`):

| Section                            | --bucket value |
| ---------------------------------- | -------------- |
| Section 2 (Architecture Rules)     | `architecture` |
| Section 3 (Code Quality Standards) | `code-quality` |
| Section 5 (Domain Rules)           | `domain`       |
| Section 6 (Workflow Rules)         | `workflow`     |

Section 4 (Patterns & Anti-Patterns) uses `add-pattern-rule` instead — six bucket × scope combinations:

```bash
.devforge/lib/constitute_helper add-pattern-rule \
    --bucket <always|never|prefer> \
    --scope <universal|project-specific> \
    --tag <extracted|enforced|universal|project-specific> \
    --text "<pattern rule text>"
# repeat per pattern rule
```

Section 1 (Project Identity) uses a single setter:

```bash
.devforge/lib/constitute_helper set-project-identity \
    --name "<name>" --type "<type>" \
    --domain "<domain>" --stack "<stack>"
```

Section 7 (Scaffolding Guide; greenfield only) uses a single setter:

```bash
.devforge/lib/constitute_helper set-scaffolding-guide \
    --starter-dirs '["src", "tests", "docs"]' \
    --sample-files-json '[{"path": "package.json", "language": "json", "content": "..."}, ...]'
```

Section 3.5 (Forcing Functions; config block) uses three `set-forcing-functions` calls — one per rule:

```bash
.devforge/lib/constitute_helper set-forcing-functions \
    --rule magic_enum_duplication \
    --enabled <true|false> \
    [--generated-types-dirs "packages/cse-types/src,packages/api-types/src"] \
    [--allowlist-paths "**/*.fixture.ts,*.fixture.ts,scripts/**,scripts"]

.devforge/lib/constitute_helper set-forcing-functions \
    --rule cross_layer_imports \
    --enabled <true|false> \
    [--layer-graph-json '{"domain": [], "infra": ["domain"], "ui": ["domain", "infra"]}'] \
    [--layer-dirs-json '{"domain": "packages/*/domain/**", "infra": "packages/*/infra/**", "ui": "packages/*/ui/**"}']

.devforge/lib/constitute_helper set-forcing-functions \
    --rule any_with_generated_available \
    --enabled <true|false> \
    [--generated-types-dirs "packages/cse-types/src"]
# --enabled is required on every call. See Section 3.5 echo template footer
# for the flag-omission rule (when each bracketed flag is passed).
# --generated-types-dirs and --allowlist-paths accept comma-separated values.
# --layer-graph-json and --layer-dirs-json require JSON-object form.
# layer_dirs keys MUST match layer_graph keys; mismatched keys exit non-zero.
```

If any setter exits non-zero, capture its stderr, fix the input value, and retry the same setter (cap at 3 retries per setter). On the 4th failure, surface the failure to the user and ABORT — `.devforge/constitute.json` is left in a partial state and the user must re-run `/constitute`.

## Phase 4 — Sequential user-only prompts

Two prompts at most. Q-mode runs always (with auto-resolution when the default is unambiguous); Q-domain runs conditionally. Q-mode runs BEFORE Phase 3 in runtime ordering — the mode value gates whether Section 7 is composed at all. Implementation note: this phase appears AFTER Phase 3 in spec text for narrative clarity, but treat Q-mode as Phase 1.5 in execution order; resolve `mode` and persist it via `set-mode` immediately after Phase 1's `read-init` capture, before Phase 2's Section 7 compose decision.

After both prompts resolve, also persist the date pair via `set-dates` and the project-name scalar via `set-project-name`.

### Q-mode (codebase mode)

Default mapping (skip the prompt entirely when default is unambiguous, then apply via `set-mode`):

- `INIT_JSON.project_state == "brownfield"` → default `existing-codebase`. Skip the prompt; apply `.devforge/lib/constitute_helper set-mode --value existing-codebase`.
- `INIT_JSON.project_state == "empty"` → default `greenfield`. Skip the prompt; apply `.devforge/lib/constitute_helper set-mode --value greenfield`.

If `INIT_JSON.project_state` is missing or holds an unexpected value, ask via AskUserQuestion: "Is this an existing codebase (rules extracted from code) or a greenfield project (rules from interview answers)?"

- `Existing codebase` (Recommended) — extract rules from architecture + glossary
- `Greenfield` — interview-driven; emit Section 7 Scaffolding Guide

Save via `.devforge/lib/constitute_helper set-mode --value <existing-codebase|greenfield>` (helper's `_validate_enum` accepts the lowercase canonical form).

### Q-domain (conditional, greenfield only)

Run this prompt only when BOTH conditions hold:

1. The Q-mode resolution above produced `mode == "greenfield"`, AND
2. `GLOSSARY_JSON` has fewer than 3 records (insufficient terms to populate Section 5.1 from glossary alone — matches the threshold cited in Phase 2 § Section 5).

When both hold, ask via a plain free-text prompt (NOT AskUserQuestion — the answer is open-ended free text): "What 3-5 key business entities does this project manage? (e.g., 'orders, quotes, customers')"

Apply the answer by composing one rule per entity into Section 5.1. Each entity becomes:

```bash
.devforge/lib/constitute_helper add-rule \
    --section 5.1 \
    --tag project-specific \
    --text "<entity name> — <one-line role description>"
```

(If Section 5.1 wasn't created in Phase 3 because the glossary was empty, also issue `add-section --bucket domain --number 5.1 --title "Key Entities"` first.)

### Date stamps + project name

Apply current-date stamps for both `generated_date` and `last_updated`:

```bash
.devforge/lib/constitute_helper set-dates \
    --generated $(date -u +%Y-%m-%d) \
    --updated $(date -u +%Y-%m-%d)
```

The helper accepts only `YYYY-MM-DD` format; the `date -u +%Y-%m-%d` shell substitution emits exactly that.

Persist the top-level `project_name` scalar (separate from `set-project-identity --name`):

```bash
.devforge/lib/constitute_helper set-project-name --value "<CONFIGURE_JSON.project_name>"
```

## Phase 5 — Render

```bash
.devforge/lib/constitute_helper render
```

`render` reads `.devforge/constitute.json`, walks the locked schema, manually concatenates `constitution.md` per section, and atomically writes the result to `<install_root>/constitution.md`. Section 7 is emitted only when `mode == "greenfield"`; the helper omits it from render when `mode == "existing-codebase"`. Exit codes:

- Exit 0 → render succeeded; `<install_root>/constitution.md` reflects the current state.
- Exit 1 → state file unreadable or corrupted JSON. Surface stderr verbatim and ABORT.
- Exit 2 → required field missing (one of the four required scalars `project_name` / `generated_date` / `last_updated` / `mode`, or one of the four `project_identity` subfields `name` / `type` / `domain` / `stack`). Surface stderr verbatim and ABORT — the user must re-run `/constitute` and ensure the missing field is composed in Phase 2 + applied in Phase 3.

The LLM does NOT edit `<install_root>/constitution.md` directly via the Write or Edit tool at any point. The helper's `render` is the only writer; this preserves the helper-owns-shape invariant.

## Phase 6 — Verify + validate + report

Run the three subcommands in order: `verify` (structural correctness), `validate` (4-dim quality), `summary` (verbatim report).

### Phase 6.1 — Verify

```bash
.devforge/lib/constitute_helper verify
```

`verify` cross-checks `.devforge/constitute.json`: required scalar fields populated; closed-enum tag membership (every `rule.tag` ∈ `{extracted, enforced, universal, project-specific}`, every `code_example.label` ∈ `{CORRECT, WRONG, EXAMPLE}`, etc.); table column/row consistency (every row has exactly `len(columns)` cells); scaffolding-guide shape (when `mode == "greenfield"`, `scaffolding_guide` non-null with `starter_directories` + `sample_files` populated); minimal round-trip identity check. Exit 0 = pass; exit 2 = at least one violation (each enumerated on stderr). On exit 2, surface stderr verbatim and recommend re-running `/constitute` to address the violations.

### Phase 6.2 — Validate

```bash
.devforge/lib/constitute_helper validate
```

`validate` runs the 4-dimension content quality framework and emits a JSON report on stdout. Composite ≥ 0.95 → exit 0 (pass); below → exit 2 with stderr enumerating per-dimension scores + failed items. The four dimensions (weight in parentheses):

1. **Slot-fill** (0.30) — required sections / fields populated (9 slots for `existing-codebase`, 10 for `greenfield`).
2. **Citation validity** (0.25) — path-like tokens in rule text / table cells / code-example annotations resolve relative to install root; package-name lookup via `INIT_JSON.packages_detected[]`.
3. **Code-example syntax** (0.25) — `python` → `ast.parse`; `json` → `json.loads`; `ts` / `tsx` / `js` / `jsx` → balanced-brace + non-empty heuristic; other languages → non-empty. Zero examples → N/A (1.0).
4. **Rule-tag enum** (0.20) — every rule tag in the closed enum. Pass = 1.0 (mechanical check; failure indicates a helper bug, not LLM authorship).

On exit 2, surface stderr verbatim, then ask the user via plain prose: "validate reports composite below 0.95 — see the per-dimension scores above. Reply 'ship' to keep the rendered `constitution.md` as-is, 'cancel' to leave the `constitution.md` in place but flag the run as incomplete, or 'fix <section-number>' to identify a section to revise (you'll re-run `/constitute` to apply the revision)." Stop the assistant turn after this prompt; await user reply.

- Reply `ship` → proceed to Phase 6.3.
- Reply `cancel` → write a one-line warning to stdout: "constitution.md flagged as incomplete; re-run `/constitute` to address per-dimension failures." Then proceed to Phase 6.3 (the summary still helps diagnose the gaps).
- Reply `fix <number>` → proceed to Phase 6.3, then in the closing message recommend the user re-run `/constitute` and edit Section `<number>` during Phase 3.

### Phase 6.3 — Summary

```bash
.devforge/lib/constitute_helper summary
```

`summary` is read-only; it prints a deterministic field-by-field report to stdout (mirrors `init_helper summary` + `configure_helper summary`). After the helper runs, copy its stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase).

### Phase 6.4 — Pre-commit hook opt-in (conditional)

Skip this phase entirely when no `forcing_functions.<rule>` has `enabled: true` in `.devforge/constitute.json` — a pre-commit hook that has no enabled rules to run is a no-op install. Determine the enabled set by reading `.devforge/constitute.json` directly and inspecting each `forcing_functions.<rule>.enabled` value (the same three rules captured in Phase 3 § Section 3.5 echo template). If the `forcing_functions` key is absent from the JSON (older state file from a prior `/constitute` run), treat all three rules as `enabled: false` and skip this phase.

When at least one rule has `enabled: true`, ask via AskUserQuestion:

- Question: `Install pre-commit-forcing-functions hook now into .git/hooks/pre-commit?`
- Options: `Yes (recommended)` and `No, skip for now`. Do NOT list "Other" — the AskUserQuestion tool auto-injects it.
- Default selection: `Yes (recommended)`.

On `Yes`: in your next user-facing message, display the following bash block as a fenced code block (copy VERBATIM; do not summarize or paraphrase). **In the same turn**, invoke the Bash tool to execute it:

```bash
cp .devforge/templates/git-hooks/pre-commit-forcing-functions.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

If either `cp` or `chmod` exits non-zero, surface stderr verbatim and tell the user: "Pre-commit hook install failed — see stderr above. Re-run the two commands manually after resolving the failure."

On `No, skip for now`: emit one line of plain prose: "Pre-commit hook skipped. Install later by running the two commands shown in `/constitute` Phase 6.4 against the same `.devforge/templates/git-hooks/pre-commit-forcing-functions.sh` source."

On `Other`: treat the free-text answer as a "No" with the user's text recorded inline in the closing message; do not attempt to interpret the free text as a partial install.

## Closing

`/constitute` is complete. `.devforge/constitute.json` carries the canonical state; `<install_root>/constitution.md` is rendered with all required sections (plus Section 7 when `mode == "greenfield"`); `verify` passed; `validate` reported a composite quality score (≥ 0.95 = pass, below = user-acknowledged ship-as-is). The 4-command sequence (`/init-forge` → `/generate-docs` → `/configure` → `/constitute`) is now complete. Tell the user: "`/constitute` is done. Open `<install_root>/constitution.md` to review, or run `/specify <feature>` to start a feature."
