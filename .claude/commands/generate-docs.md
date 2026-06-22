---
name: generate-docs
description: Generate the docs/ knowledge base — bottom-up bottom-tier (concern → package → project), incremental skip via source_stamp, helper-owned shape, orchestrator-direct compose.
disable-model-invocation: true
---

# /generate-docs

Generates the project's `docs/` knowledge base end-to-end. The pipeline is
bottom-up across three tiers (concern → package → project), gated by per-tier
`source_stamp` so unchanged areas skip dispatch. The orchestrator (this thread)
composes Purpose paragraphs + leaf annotations inline; helpers own all markdown
structure (skeletons, setters, render, validate). No subagent dispatch.

Optional scope filter: a runtime-configured prefix list can narrow Phase 2-4 to
specific packages or concerns. Without a filter, all preflight entries process.

---

## ⚠️ HELPER CHAIN MANDATORY — NO ALTERNATIVE PATHS, NO SUBAGENT DISPATCH

**Active for the entirety of this command.** The Phase 2 per-concern flow MUST go through the helper chain in this order:

```
init-doc → set-doc-purpose → set-doc-structure → render-doc → validate-doc
```

Concern-tier authoring is **orchestrator-direct**: this thread reads the `concern-input` batch JSON inline and emits Purpose + per-leaf annotations itself. NO Task-tool dispatch to any compose subagent. Subagent dispatch costs 30-90K tokens per concern + redundant source-file reads inside the subagent. Orchestrator-direct is 3-10× cheaper because session context is already loaded; the concern's batch JSON inlines (~3-5K tokens) and structured output emits (~2-4K tokens).

The following are FORBIDDEN under /generate-docs:

- Writing concern markdown to disk via the Write tool (helper owns that path via `render-doc`).
- Running custom Python or bash that emits markdown content directly to `docs/<pkg>/<concern>/index.md`.
- Invoking legacy concern setters (`set-concern-overview`, `set-concern-tree`, `add-concern-export`, `add-concern-type`, `add-concern-dep`, `add-concern-hazard`, `set-concern-usage-example`, `render-concern-doc`, `validate-concern`). Those primitives emit a different shape and are out of scope.
- Running `reset` — `init-doc` is idempotent and resets its state slot wholesale on every call.

The helper chain is the ONLY canonical path. Any divergence emits the wrong shape and breaks downstream consumers expecting `## Purpose` + `## Structure`.

---

## CBM-sync preamble (run first)

Before executing any step below, run `.devforge/lib/cbm_sync_helper check`. If output is `drift ...`, call `mcp__codebase-memory-mcp__detect_changes` then `.devforge/lib/cbm_sync_helper write` before continuing. If output is `missing`, call `mcp__codebase-memory-mcp__index_repository` then `.devforge/lib/cbm_sync_helper write` before continuing. If output is `current` or `not-a-git-repo`, proceed.

This catches mid-session `git pull` / `git checkout` drift that the SessionStart hook (`cbm-sync-session-start`) cannot see — the SessionStart hook only fires at session boot. /generate-docs queries CBM heavily (Phase 4 Patterns + Cross-Cuts via `get_code_snippet`; Phase B glossary via `query_graph` + `search_graph` + `get_code_snippet`); a stale graph silently corrupts cite-back paths and snippet contents.

---

## Phase 0 — Pre-flight gate

1. `.devforge/index.json` exists:

   ```
   test -f .devforge/index.json
   ```

   If non-zero → ABORT: "missing .devforge/index.json — run /init-forge first."

2. `codebase-memory-mcp` binary on PATH:
   ```
   command -v codebase-memory-mcp >/dev/null
   ```
   If non-zero → ABORT with install link: `curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | bash`.

---

## Phase 1 — Preflight

```
./.devforge/lib/generate_docs_helper preflight
```

Captures stdout JSON. Key fields used downstream:

- `concerns[]` — list of `{package, concern, source_stamp, prior_stamp, status, [split, sub_concerns[]]}`. Split parents carry `split:true` + embedded `sub_concerns[]` (each sub_concern is `{concern, source_stamp, prior_stamp, status}`).
- `concern_counts` — `{unchanged, changed, new, empty}` over concern-tier entries.
- `subconcern_counts` — `{unchanged, changed, new}` aggregated across every split parent's children. Used for cost estimation.
- `vue_extract` + `index_repository` — wall-clock and counts; surface to user

vue-extract regenerates `.devforge/vue-tmp/` ONLY when `.devforge/index.json` contains the substring `.vue` (cheap text scan, no JSON parse). On Vue-free codebases the helper auto-skips it (`vue_extract.ran=false`, `reason="no .vue files in .devforge/index.json"`) without invoking the launcher. CBM `index_repository` reindexes. Both idempotent. On non-zero exit → ABORT with stderr verbatim.

### Cost gate (split-aware estimate)

Before kicking off Phase 2, surface to the user the dispatch volume + cost estimate using preflight's counts. Apply any configured scope filter first (see "Optional scope filter" in the intro), then count:

- **Single-batch dispatches** = scoped concerns with `status ∈ {changed, new}` AND `split != true`.
- **Sub_concern dispatches** = sum of scoped split parents' `sub_concerns[]` entries with `status ∈ {changed, new}`. (Parent concerns themselves are orchestrator-direct synthesis — no Haiku dispatch.)
- **Skipped via stamp gate** = scoped concerns with `status == unchanged` + scoped split parents' children with `status == unchanged`.

Cost model (Haiku, ~$0.20 per dispatch + ~10s wall-clock):

- `total_dispatches = single_batch + sub_concerns_changed_or_new`
- `total_cost ≈ total_dispatches × $0.20`
- `total_wall_clock ≈ total_dispatches × 10s` (sequential, single-thread)

**Surface the breakdown to the user before Phase 2 starts** — name the count of each bucket, the total, and the estimated cost + wall-clock. For runs over $5 / 5min, recommend confirming with the user before proceeding. Stamp-gate skips are free; surface the savings (e.g., "N/M sub_concerns skip via stamp gate").

---

## Phase 2 — Concern tier loop (only changed/new, scope-filtered)

After preflight returns `concerns[]`, apply the configured scope filter (if any). Drop every concern that does not match. Without a filter, all entries process.

Then for each kept entry where `status` is `changed` or `new`, run Steps 2.1–2.5 in order. The retry loop wraps Steps 2.3–2.5 (capped at 3 retries).

### Step 2.1 — Pull batch input (helper, once per concern)

```
./.devforge/lib/generate_docs_helper concern-input \
    --package "$pkg" --concern "$concern"
```

Capture full JSON output to a variable. Fields used downstream:

- `tree_text` — mechanical ASCII tree from index.json, fed to `set-doc-structure`
- `files[].path` — project-relative file paths
- `files[].comment_rich_span` — top-of-file lines + TODO context windows; used by orchestrator to infer leaf annotations
- `source_stamp` — frontmatter input

**Branch on split:** if the JSON output has `"split": true`, jump to Step 2.S (split path) below. Steps 2.2–2.5 below document the single-batch flow only (the default for concerns under the split threshold). The split path reuses Steps 2.2–2.5 once per child sub_concern + adds a parent-aggregator pass.

### Step 2.2 — init-doc with helper-built frontmatter + tree

```
./.devforge/lib/generate_docs_helper init-doc --tier concern --target "$pkg/$concern" \
    --frontmatter "$(jq -n --arg c "$concern" --arg p "$pkg" --argjson f "$files_count" \
                       --arg s "$source_stamp" --arg d "$today" \
                       '{concern:$c, package:$p, files:$f, source_stamp:$s, last_indexed:$d}')" \
    --tree "<step 2.1 tree_text verbatim>"
```

Frontmatter values:

- `concern`, `package` — string literals from the preflight entry
- `files` — count from `concern-input`'s JSON `files` field
- `source_stamp` — `concerns[*].source_stamp` from preflight
- `last_indexed` — today's ISO date (`date -u +%Y-%m-%d`)

`init-doc` writes `docs/<target>/index.md.skeleton` with frontmatter + Purpose placeholder + `## Structure` section + the tree wrapped in a `text` code fence. Re-running overwrites the skeleton. The skeleton file IS the state — no separate state JSON.

### Step 2.3 — Compose Purpose + leaf annotations (orchestrator-direct, NO subagent)

The orchestrator (the main /generate-docs thread) reads the Step 2.1 batch JSON inline and produces:

1. **Purpose** — 1-3 sentences describing what the concern does. Concrete + cross-cuts named. No banned phrases ("this document", "in this section", "various", "several", "many", "some", "other"). Sourced from filename inference + `files[].comment_rich_span` content.

2. **Annotations** — a flat `{<basename>: <1-line description ≤60 chars>}` JSON map covering every non-trivial leaf in `tree_text`. One annotation per leaf. Skip canonical-aggregator filenames (`mod.rs`, `lib.rs`, `__init__.py`, `index.ts`, `index.js`, `doc.go`).

For very large concerns (>100 leaves), the orchestrator emits the annotations map progressively in chunks during a single response — `set-doc-structure` accepts the full map atomically; the orchestrator must build the map fully before invoking the setter.

### Step 2.4 — Setters

Two setter calls (Hazards dropped — `/audit` territory). Setters edit the skeleton file in-place:

```
./.devforge/lib/generate_docs_helper set-doc-purpose --tier concern --target "$pkg/$concern" \
    --text "<orchestrator-composed Purpose>"

./.devforge/lib/generate_docs_helper set-doc-structure --tier concern --target "$pkg/$concern" \
    --annotations '<orchestrator-composed {basename: annotation} JSON>'
```

`set-doc-purpose` replaces the `<!-- TODO: purpose -->` placeholder with the supplied text (idempotent — re-running with new text replaces the prior content).

`set-doc-structure` walks lines inside the ` ```text ` fence and appends `  # <annotation>` to each leaf line whose basename matches an entry in `--annotations`. Idempotent — leaves already annotated are passed through.

The orchestrator MUST NOT:

- Write the markdown directly via the Write tool
- Run custom Python or bash that emits markdown directly to docs/

Disk writes happen via the setters (in-place skeleton edit) and Step 2.5's `render-doc` (atomic rename).

### Step 2.5 — Render + validate

```
./.devforge/lib/generate_docs_helper render-doc --tier concern --target "$pkg/$concern"
./.devforge/lib/generate_docs_helper validate-doc --tier concern --target "$pkg/$concern"
```

`render-doc` renames `docs/<target>/index.md.skeleton` → `docs/<target>/index.md` (atomic; no content mutation).

- Both exit 0 → done with this concern; advance to next.
- validate-doc exit 2 → capture stderr verbatim. Re-run Step 2.2 (init-doc, wipes the skeleton), then Step 2.3 (orchestrator re-composes Purpose + annotations using the stderr as feedback) → Step 2.4 → Step 2.5. Cap at 3 retries; on the 4th, surface failure to the user and continue with the next concern.

**Why init-doc on retry**: re-init wipes the skeleton wholesale; setters overwrite cleanly. Cheaper than tracking partial state.

### Step 2.S — Split path (only when concern-input emits `split: true`)

When the Step 2.1 JSON has `"split": true`, the concern was over the threshold + has ≥2 immediate child dirs. The output carries `parent_meta` (full tree + `subconcern_names` + `loose_files`) and `sub_concerns[]` (one self-sufficient batch per child). Run the per-child pass first, then the parent-aggregator pass.

**Iterate `sub_concerns[]` directly — do not drive the loop from `parent_meta.subconcern_names`.** The helper drops children whose file list is empty after trivial-leaf filtering, so `sub_concerns[]` may be shorter than `subconcern_names`. The split-batch top-level JSON has NO `files[]` key (unlike single-batch); `files[]` only exists per-child inside `sub_concerns[i]`.

#### Step 2.S.1 — Per-child sub_concern pass

For each entry in `sub_concerns[]`, run the existing Steps 2.2–2.5 unchanged with these substitutions:

- `--target` → `"$pkg/$concern/$sub_name"` (where `$sub_name` is `sub_concerns[i].concern`)
- Frontmatter `concern` → `$sub_name`; `package` → `$pkg`; `parent_concern` → `$concern`; `source_stamp` → `sub_concerns[i].source_stamp`; `files` → `len(sub_concerns[i].files)` (Step 2.2 originally pulls `files_count` from the top-level `files` field, but that field is absent in split-batch — use the per-child entry instead)
- `--tree` → `sub_concerns[i].tree_text` (rooted at `<pkg>/src/<concern>/<sub_name>/`)
- Annotations source → `sub_concerns[i].files[].comment_rich_span` (NOT the parent's full file list)

Each child renders to `docs/<pkg>/<concern>/<sub_name>/index.md`. Validation rules are identical to single-batch concerns (Purpose + Structure required; cite-backs resolve).

Retry budget per child: 3 (same as Step 2.5). On 4th failure, surface that child to the user and continue with the next child. Do NOT abort the parent-aggregator pass — emit the parent with whatever children rendered.

#### Step 2.S.2 — Parent skeleton init

After all children pass (or are surfaced as failed):

```
./.devforge/lib/generate_docs_helper init-doc --tier concern --target "$pkg/$concern" --split \
    --frontmatter "$(jq -n --arg c "$concern" --arg p "$pkg" \
                       --arg s "$source_stamp" --arg d "$today" \
                       '{concern:$c, package:$p, source_stamp:$s, last_indexed:$d, split:true}')"
```

Notes:

- `--split` is a bare flag for `init-doc` (no value; `action="store_true"`). Do NOT write `--split true` here — argparse would treat `true` as an unexpected positional argument.
- `--split` flag triggers the parent skeleton (Purpose + Sub-concerns; NO Structure section).
- `--tree` is omitted; the parent has no Structure tree.
- Frontmatter `source_stamp` = the aggregate stamp from Step 2.1's top-level `source_stamp` field (which already aggregates over child stamps + loose files).
- The frontmatter `split: true` flag lets validate-doc / preflight tell parent docs apart from leaf concern docs.

#### Step 2.S.3 — Parent compose (orchestrator-direct, NO subagent)

The orchestrator reads each rendered child's frontmatter Purpose text + names a per-child 1-line summary. Output:

1. **Parent Purpose** — 1–3 sentences describing the parent concern's role at the package level. Concrete, names the cross-cuts that span children. No banned phrases.

2. **Sub-concerns list** — JSON array `[{name, purpose_summary, doc_path}, ...]` where:
   - `name` = `sub_concerns[i].concern` (the child dir name)
   - `purpose_summary` = ≤200-char one-liner describing that child's role (synthesised from the child's Purpose paragraph; do NOT verbatim-copy)
   - `doc_path` = `<sub_name>/index.md` (parent-relative; matches the rendered child path)

#### Step 2.S.4 — Parent setters

```
./.devforge/lib/generate_docs_helper set-doc-purpose --tier concern --target "$pkg/$concern" \
    --text "<orchestrator-composed parent Purpose>"

./.devforge/lib/generate_docs_helper set-doc-subconcerns --tier concern --target "$pkg/$concern" \
    --subconcerns '<orchestrator-composed sub-concerns JSON>'
```

`set-doc-subconcerns` writes `## Sub-concerns` bullets in the locked shape `- <name> — <purpose_summary> ([→](<doc_path>))`. The helper silently skips entries missing any of the three fields (no error, exit 0); validate-doc will catch the resulting empty section in Step 2.S.5. Sanity check before invoking: confirm the bullet count emitted equals `len(sub_concerns[])` to detect dropped entries early.

#### Step 2.S.5 — Parent render + validate

```
./.devforge/lib/generate_docs_helper render-doc --tier concern --target "$pkg/$concern"
./.devforge/lib/generate_docs_helper validate-doc --tier concern --target "$pkg/$concern" --split
```

Validation for split parents: required sections = `## Purpose` + `## Sub-concerns` only (`## Structure` is forbidden); each Sub-concerns bullet matches the locked shape `- <name> — <summary> ([→](<doc_path>))`; each `doc_path` resolves to an existing rendered child doc under `docs/<pkg>/<concern>/`. Both `init-doc` and `validate-doc` use bare `--split` (store_true) for parent-shape selection.

Retry on validation failure: re-run Steps 2.S.2–2.S.5 (re-init wipes parent skeleton). Cap at 3 retries; on 4th, surface failure to the user. Children are NOT regenerated by parent retries.

**Why per-child first**: parent's `purpose_summary` synthesises from each child's Purpose paragraph, so children must exist + have valid frontmatter Purpose before the parent compose step.

---

## Phase 3 — Package tier loop (after concern tier completes)

After Phase 2's concern docs are all rendered + validated, run the package tier for every package whose concerns appeared in the concern-tier loop. Two docs per package: `overview.md` + `architecture.md`. Domain glossary lives inline in each Purpose paragraph for in-context disambiguation; project-tier consolidated glossary lives at `docs/glossary.md` produced by Phase B.

For each in-scope package P (derive the unique set from preflight's `concerns[*].package`):

### Step 3.1 — Pull batch input

```
./.devforge/lib/generate_docs_helper package-input --package "$P"
```

Returns JSON with `concern_seeds[]` (frontmatter + Purpose text from each rendered concern doc) + `package_root_files[]` (README/CHANGELOG/package.json comment-rich spans) + `source_stamp`.

If all of P's concerns were `status=unchanged` AND the prior package overview/architecture docs' frontmatter `source_stamp` matches the new `source_stamp` from package-input → SKIP this package's package-tier dispatches. (Per-package stamp comparison runs inline in the orchestrator; preflight does not compute package-level stamps.)

### Step 3.2 — package-overview pipeline

Frontmatter:

```json
{ "package": "<P>", "last_indexed": "<today>", "source_stamp": "<from package-input>" }
```

```
./.devforge/lib/generate_docs_helper init-doc --tier package-overview --target "$P" \
    --frontmatter "$FM"
```

Compose orchestrator-direct (no subagent):

- **Purpose** (1-3 sentences) — synthesize across `concern_seeds[*].purpose_text` + `package_root_files[*].comment_rich_span`. Cross-cuts named. Banned phrases absent.
- **Concerns** (bullet list) — one entry per `concern_seeds[*]`: `{name: <concern>, role: <one-line role from concern_seeds[*].purpose_text>, cite: <docs/<P>/<concern>/>}`.
- **Files** (bullet list) — one entry per `src_root_files[*]`: `{name: <basename>, role: <1-line description from comment_rich_span>}`. Loose files at `<P>/src/` root (e.g. `index.ts` barrel, `env.d.ts`, `apolloClient.ts`) are NOT inside any concern subfolder; this section surfaces them at package tier so they don't fall through unannotated.

```
./.devforge/lib/generate_docs_helper set-doc-purpose --tier package-overview --target "$P" --text "..."
./.devforge/lib/generate_docs_helper set-doc-concerns --tier package-overview --target "$P" \
    --concerns '<json array>'
./.devforge/lib/generate_docs_helper set-doc-files --tier package-overview --target "$P" \
    --files '<json array>'
./.devforge/lib/generate_docs_helper render-doc --tier package-overview --target "$P"
./.devforge/lib/generate_docs_helper validate-doc --tier package-overview --target "$P"
```

On validate-doc failure: re-init the slot + re-compose with stderr as feedback. Cap 3 retries.

### Step 3.3 — package-architecture pipeline

Frontmatter (same shape as 3.2). Sections:

- **Layers** (bullet list) — derived from concern groupings in `concern_seeds[]` (e.g., concerns under `presentation/`, `domain/`, `data/`) + cross-package layer cites. Each entry `{name, role, cite}`.
- **Patterns** (bullet list) — package-wide conventions from `package_root_files[]` + cross-concern patterns observed in `concern_seeds[]`. Each entry `{name, rule, cite}`.

```
./.devforge/lib/generate_docs_helper init-doc --tier package-architecture --target "$P" \
    --frontmatter "$FM"
./.devforge/lib/generate_docs_helper set-doc-layers --tier package-architecture --target "$P" \
    --layers '<json array>'
./.devforge/lib/generate_docs_helper set-doc-patterns --tier package-architecture --target "$P" \
    --patterns '<json array>'
./.devforge/lib/generate_docs_helper render-doc --tier package-architecture --target "$P"
./.devforge/lib/generate_docs_helper validate-doc --tier package-architecture --target "$P"
```

Same retry semantics as Step 3.2.

## Phase 4 — Project tier loop (after package tier completes)

After Phase 3's package overviews + architectures are all rendered + validated, run the project tier. Two docs at `docs/overview.md` and `docs/architecture.md` (NO `<package>` subdir at this tier).

### Step 4.1 — Pull batch input

```
./.devforge/lib/generate_docs_helper project-input [--project "<label>"]
```

Returns JSON with:

- `package_seeds[]` — frontmatter + Purpose text from each rendered package overview
- `project_root_files[]` — top-level README/CHANGELOG/package.json comment-rich spans
- `source_stamp`

**Phase 1 mechanical fields** (verbatim passthrough to setters):

- `tech_stack_candidates[]` — `[{layer, technology}]` derived from `package.json` deps + manifest detection
- `key_commands[]` — `[{command, description}]` from `package.json scripts` block
- `test_file_paths[]` — `[{path, description}]` from filesystem walk for test directories + `*.test.ts` / `test_*.py` style suffixes
- `cross_module_deps_tree` — ASCII tree of internal cross-workspace dependencies
- `project_structure_tree` — ASCII directory tree, depth=3, ignore-filtered

**Phase 2 candidate fields** (mechanical pre-extraction; LLM augments with purpose/description/role text):

- `entry_point_candidates[]` — `[{label, path}]` for `main.ts` / `index.ts` / `App.vue` / `router/`-`plugins/`-`store/` files; LLM fills `purpose`
- `router_route_files[]` — file paths under `**/router/routes/`; LLM Reads + extracts `path` literals + components
- `nav_guard_files[]` — file paths in `**/router-guards/`, `**/guards/`; LLM Reads + extracts guard name + role + chain order
- `package_classification_hints` — `{infrastructure: [names], core: [names], domain: [names]}` name-pattern bucket; LLM may regroup based on actual package contents

In wrapper-mode setups (testForge20-style: `.devforge/` at wrapper, monorepo at `<wrapper>/<inner>/`) the helper auto-resolves the inner monorepo via `init.yaml`'s `project_root` field, so all mechanical extraction operates on the right tree.

`--project` defaults to the project_root basename.

If all packages were `unchanged` AND prior project overview/architecture docs' `source_stamp` matches the new project-input `source_stamp` → SKIP project tier dispatches.

### Step 4.2 — project-overview pipeline

Frontmatter:

```json
{ "last_indexed": "<today>", "source_stamp": "<from project-input>" }
```

`--target` is used as the H1 label only (no per-target subdir at this tier). Pass the project label.

```
./.devforge/lib/generate_docs_helper init-doc --tier project-overview --target "<project-label>" \
    --frontmatter "$FM"
```

The skeleton emits eleven sections — five Phase 1 mechanical (verbatim from `project-input`), four Phase 2 mixed (helper renders structure; LLM provides purpose/description/role text), two LLM-synthesized:

| Section                   | Source                                                                                            | Setter                                |
| ------------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------- |
| Purpose                   | LLM synthesis from `package_seeds[*].purpose_text` + `project_root_files`                         | `set-doc-purpose`                     |
| Tech Stack                | `project-input.tech_stack_candidates` (verbatim)                                                  | `set-overview-tech-stack`             |
| Project Structure         | `project-input.project_structure_tree` (verbatim tree)                                            | `set-overview-project-structure-tree` |
| Entry Points              | `project-input.entry_point_candidates` + LLM `purpose` per row                                    | `set-overview-entry-points`           |
| Key Commands              | `project-input.key_commands` (verbatim)                                                           | `set-overview-key-commands`           |
| Module Map                | `project-input.package_classification_hints` + LLM `purpose` per package; LLM may regroup         | `set-overview-module-map`             |
| Cross-Module Dependencies | `project-input.cross_module_deps_tree` (verbatim)                                                 | `set-overview-cross-module-deps`      |
| Application Routes        | LLM Reads `project-input.router_route_files`, extracts `{path, component}` + writes `description` | `set-overview-application-routes`     |
| Navigation Guards         | LLM Reads `project-input.nav_guard_files` + router config, extracts `{name, role}` in chain order | `set-overview-navigation-guards`      |
| Test Files                | `project-input.test_file_paths` (verbatim)                                                        | `set-overview-test-files`             |
| Packages                  | LLM synthesis from `package_seeds[*]`                                                             | `set-doc-packages`                    |

After Project Structure tree is set, Phase 2 also augments tree leaves with directory-level annotations:

| Augmentation                  | Source                                                           | Setter                                       |
| ----------------------------- | ---------------------------------------------------------------- | -------------------------------------------- |
| Project Structure annotations | LLM provides `{dir_basename: annotation_text}` per top-level dir | `set-overview-project-structure-annotations` |

Compose order:

```
./.devforge/lib/generate_docs_helper set-doc-purpose --tier project-overview --target "<project-label>" --text "..."
./.devforge/lib/generate_docs_helper set-overview-tech-stack --tier project-overview --target "<project-label>" \
    --tech-stack '<from project-input.tech_stack_candidates>'
./.devforge/lib/generate_docs_helper set-overview-project-structure-tree --tier project-overview --target "<project-label>" \
    --text "<from project-input.project_structure_tree>"
./.devforge/lib/generate_docs_helper set-overview-project-structure-annotations --tier project-overview --target "<project-label>" \
    --annotations '<LLM-supplied {dir_basename: text}>'
./.devforge/lib/generate_docs_helper set-overview-entry-points --tier project-overview --target "<project-label>" \
    --entry-points '<{label, path, purpose} from project-input.entry_point_candidates + LLM purpose>'
./.devforge/lib/generate_docs_helper set-overview-key-commands --tier project-overview --target "<project-label>" \
    --key-commands '<from project-input.key_commands>'
./.devforge/lib/generate_docs_helper set-overview-module-map --tier project-overview --target "<project-label>" \
    --modules '<{infrastructure, core, domain} with LLM purpose per package>'
./.devforge/lib/generate_docs_helper set-overview-cross-module-deps --tier project-overview --target "<project-label>" \
    --text "<from project-input.cross_module_deps_tree>"
./.devforge/lib/generate_docs_helper set-overview-application-routes --tier project-overview --target "<project-label>" \
    --routes '<{path, component, description} parsed from project-input.router_route_files>'
./.devforge/lib/generate_docs_helper set-overview-navigation-guards --tier project-overview --target "<project-label>" \
    --guards '<{name, role} parsed from project-input.nav_guard_files in chain order>'
./.devforge/lib/generate_docs_helper set-overview-test-files --tier project-overview --target "<project-label>" \
    --test-files '<from project-input.test_file_paths>'
./.devforge/lib/generate_docs_helper set-doc-packages --tier project-overview --target "<project-label>" \
    --packages '<json array>'
./.devforge/lib/generate_docs_helper render-doc --tier project-overview --target "<project-label>"
./.devforge/lib/generate_docs_helper validate-doc --tier project-overview --target "<project-label>"
```

Phase 1 mechanical setters pass `project-input` output through verbatim — no orchestrator interpretation. Phase 2 mixed setters need LLM-supplied prose for purpose/description/role cells, but helper still owns table/list structure. Purpose + Packages stay orchestrator-direct LLM compose. When `project-input` returns empty for a mechanical/candidate field (e.g., no `package.json` → empty `tech_stack_candidates`; no `router/` dir → empty `router_route_files`), call the setter with empty input (`'[]'` / `'{}'`) — `validate-doc` enforces section presence, not content depth.

For `set-overview-application-routes` and `set-overview-navigation-guards`: orchestrator MUST Read each file from `router_route_files` / `nav_guard_files` to extract `path:`, `component:`, guard chain order from `router.beforeEach()` calls. project-input emits paths only (mechanical); content parsing is LLM judgment.

Retry semantics same as Phase 3.

### Step 4.3 — project-architecture pipeline

The skeleton emits eight sections (Track 4 Phase 3 expansion). Six are LLM-judgment-heavy + cite-back-via-CBM-snippet; two (Layers, Dependency Overview) accept verbatim mechanical input.

| Section                    | Source                                                                                                                                                                                                              | Setter                                         |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| Architecture Overview      | LLM multi-paragraph narrative synthesizing across `package_seeds[*]`                                                                                                                                                | `set-architecture-overview-narrative`          |
| Module / Package Structure | LLM emits annotated tree of workspace + per-feature subdir layout                                                                                                                                                   | `set-architecture-module-structure`            |
| Patterns                   | LLM via CBM `get_code_snippet` — `[{name, applies_in, rule, language, code_snippet, cite}]` per pattern                                                                                                             | `set-architecture-patterns`                    |
| Conventions                | LLM extracts from concern docs + filesystem patterns + tech stack (`project-input.tech_stack_candidates`) — `{naming, file_organization, import_style, error_handling, styling, state_management}` 6-bucket bullets | `set-architecture-conventions`                 |
| Layers                     | LLM `[{name, role, cite}]` (Phase 0 shape)                                                                                                                                                                          | `set-doc-layers`                               |
| Cross-Cuts                 | LLM via CBM — `[{name, description, language, code_snippet, cite}]` per cross-cut subsection                                                                                                                        | `set-architecture-cross-cuts-detailed`         |
| Dependency Direction Rules | LLM `[bullet_strings]` per package layer                                                                                                                                                                            | `set-architecture-dependency-direction-rules`  |
| Dependency Overview        | `project-input.dep_graph_mermaid` (verbatim) OR LLM-curated mermaid graph                                                                                                                                           | `set-architecture-dependency-overview-mermaid` |

For Patterns + Cross-Cuts: orchestrator queries CBM `get_code_snippet(qualified_name)` to fetch verbatim source + line range, then passes the snippet + `<file>:<line>` cite into the setter. Helper renders subsection-style (`### <name>` + applies-in + rule prose + cite-back HTML comment + fenced code block).

For Conventions: the orchestrator composes all six buckets — including `styling` and `state_management` — from concern docs + filesystem patterns + the already-detected tech stack (`project-input.tech_stack_candidates`), the same way the other four buckets are extracted; there is no dedicated mechanical detector for any bucket. The `styling` bullets describe the project's observed styling approach (e.g. CSS-modules vs utility-first vs styled-components, theme-token usage, where stylesheets live) and the `state_management` bullets describe the project's observed state approach (e.g. the store/reducer/context idiom in use, local-vs-shared state boundaries). Apply the same judgment discipline as the other four buckets: document only conventions observed in the codebase, ground each bullet in real code, and mark any bullet that is inferred rather than directly observed. When the codebase shows no styling or no shared state-management convention (e.g. a non-UI service), omit that bucket's bullets — the helper omits any empty bucket from the rendered `## Conventions` section.

```
./.devforge/lib/generate_docs_helper init-doc --tier project-architecture --target "<project-label>" \
    --frontmatter "$FM"
./.devforge/lib/generate_docs_helper set-architecture-overview-narrative --tier project-architecture --target "<project-label>" \
    --text "<multi-paragraph narrative>"
./.devforge/lib/generate_docs_helper set-architecture-module-structure --tier project-architecture --target "<project-label>" \
    --text "<annotated tree>"
./.devforge/lib/generate_docs_helper set-architecture-patterns --tier project-architecture --target "<project-label>" \
    --patterns '<JSON array of patterns with snippet+cite>'
./.devforge/lib/generate_docs_helper set-architecture-conventions --tier project-architecture --target "<project-label>" \
    --conventions '<{naming, file_organization, import_style, error_handling, styling, state_management} JSON>'
./.devforge/lib/generate_docs_helper set-doc-layers --tier project-architecture --target "<project-label>" \
    --layers '<JSON array>'
./.devforge/lib/generate_docs_helper set-architecture-cross-cuts-detailed --tier project-architecture --target "<project-label>" \
    --cross-cuts '<JSON array of cross-cuts with snippet+cite>'
./.devforge/lib/generate_docs_helper set-architecture-dependency-direction-rules --tier project-architecture --target "<project-label>" \
    --rules '<JSON bullet-strings array>'
./.devforge/lib/generate_docs_helper set-architecture-dependency-overview-mermaid --tier project-architecture --target "<project-label>" \
    --text "<from project-input.dep_graph_mermaid OR LLM-curated mermaid syntax>"
./.devforge/lib/generate_docs_helper render-doc --tier project-architecture --target "<project-label>"
./.devforge/lib/generate_docs_helper validate-doc --tier project-architecture --target "<project-label>"
```

Phase 0 callers using bullet-list `set-doc-cross-cuts` remain functional; Phase 3 callers use the enriched `set-architecture-cross-cuts-detailed` (subsections with code samples). Both target the same `## Cross-Cuts` anchor — last setter call wins.

Phase 3 ships presence-only validation (sections required + bullet caps). Snippet-fidelity validation (helper reads cited file + diffs against rendered snippet) is a deferred follow-up — same evolution pattern as concern-tier validation (F.5 v0 → enrichment).

---

## Phase B — Glossary (after project tier completes)

After Phase 4's project-tier docs are rendered + validated, run the project-tier glossary at `docs/glossary.md`. The glossary is a judgment-layer artifact: term → 1–2-sentence definition, with code anchors for terms backed by CBM-indexed symbols and prose-only entries for narrative-only concepts. The lettered label ("Phase B" rather than a continued number) marks this as a judgment-layer phase added on top of the original 1–4 pipeline; future judgment-layer phases follow the same lettered-label pattern.

The orchestrator drives two helper SUBCMDs: `build-glossary-bundles` (helper walks `docs/`, classifies terms via CBM, ranks, emits JSON to stdout) and `set-glossary-entries` (helper consumes LLM-composed entries JSON, validates, renders `docs/glossary.md` atomically). Helper owns markdown structure + validation; LLM provides definition values + related-term picks.

### Step B.1 — Build candidate bundles

```
./.devforge/lib/generate_docs_helper build-glossary-bundles \
    --devforge-dir .devforge \
    --top-n 80 \
    --bm25-threshold -25 \
    > /tmp/glossary-bundles.json
```

Capture stdout JSON to a tmp file (the file path is reused as `--bundles-file` in Step B.3). Each bundle entry is:

- `term` — string identifier surfaced in the docs corpus
- `class` — one of `code-anchored` (CBM `query_graph` exact match on a `Function`/`Method`/`Class`/`Type`/`Interface`/`Enum` node), `fuzzy-anchored` (CBM `search_graph` BM25 match above the threshold), or `prose-only` (no CBM hit; term appears in ≥2 distinct md paths)
- `doc_context` — concatenated context windows from each docs occurrence (space-joined)
- `code_anchor` — `{qn, file, line, snippet}` for code-anchored / fuzzy-anchored entries (snippet is the first 5 lines via `get_code_snippet`); fuzzy-anchored entries also carry `"fuzzy": true`. `null` for prose-only.
- `related_set` — list of CBM `SEMANTICALLY_RELATED` neighbor names (may be empty)
- `cite_md_paths` — unique md paths where the term occurs (preserves first-seen order)

Defaults `--top-n 80` and `--bm25-threshold -25` match the helper's argparse defaults. Override either to widen / narrow the candidate pool. The bundles list is already top-N-sorted by combined rank; preserve that order when composing entries.

### Step B.2 — Compose entries (orchestrator-direct, NO subagent)

Before composing: count entries in the bundles JSON from Step B.1. If `len(bundles) < 30`, surface the limitation to the user (suggested message: "Project glossary requires ≥30 candidate terms; only N found after noise filter — project may be too small for a project-tier glossary") and stop Phase B. Do NOT compose entries or call `set-glossary-entries` — retries cannot fix a below-floor bundle pool.

For each bundle, draft a `{term, definition, related_terms, aliases_to_avoid?}` object. `aliases_to_avoid` is optional (default `[]`). The orchestrator (this thread) reads each bundle inline and emits the array; no Task-tool dispatch.

**Definition drafting** — seed the prose from the bundle's `doc_context` and `code_anchor.snippet` (when present); aim for 1–2 sentences. The helper's `_validate_entries` enforces the following hard rules (exit 2 + stderr on any failure):

- non-empty after strip
- ≤280 chars after strip
- single paragraph — no `\n` in the stripped value

**`related_terms` rules:**

- Pick from the bundle's `related_set` (CBM-derived) plus any other glossary terms the orchestrator judges semantically related
- Each `related_terms` value MUST appear as a `term` in some other entry in the same array — dangling references are rejected
- No self-reference (the entry's own term must not appear in its own `related_terms`)

**`aliases_to_avoid` rules** (optional, default `[]`):

- Banned synonyms — alternative names downstream agents must NOT invent for this canonical concept. Seed from variants spotted in the bundle's `doc_context` or from orchestrator judgement about plausible misnamings (e.g., `OrderManager` / `OrderHandler` when the canonical term is `Order`).
- Each value MUST NOT equal the entry's own `term` (case-insensitive) — self-reference is rejected
- Each value MUST NOT equal the canonical `term` of any other entry — a banned synonym in entry A cannot be the canonical name of entry B
- Case-insensitive duplicates within the list are rejected
- Omit the field or pass `[]` when no synonyms apply

**Thin-context guard:** if a bundle's `doc_context` totals fewer than 2 sentences, the orchestrator must NOT fabricate a definition (regardless of whether `code_anchor.snippet` is present). Emit the entry with `"definition": "[TODO: human-define]"` instead. The literal `[TODO: human-define]` string passes the validator (non-empty, ≤280 chars, single paragraph) — surface these terms in Phase 6's report so a human can fill them post-run.

**Hard floor / ceiling:** the helper enforces `30 ≤ N ≤ 150` entries. Above 150, drop the lowest-ranked candidates from the bundles list before composing; the bundles are pre-sorted by combined rank.

### Step B.3 — Set entries + render

```
./.devforge/lib/generate_docs_helper set-glossary-entries \
    --devforge-dir .devforge \
    --bundles-file /tmp/glossary-bundles.json \
    --entries '<orchestrator-composed [{term, definition, related_terms, aliases_to_avoid?}] JSON array>'
```

The helper validates the entries (count, definition shape, term-uniqueness case-insensitive, bundle match per term, cite-path existence, prose-only ≥2 cite_md_paths, code-anchored / fuzzy-anchored requires non-empty `qn` + live `get_code_snippet` resolution, `related_terms` reference closure, `aliases_to_avoid` element shape + self-reference guard + in-list uniqueness + cross-entry collision guard) and on success renders `docs/glossary.md` atomically.

**Output shape** (helper-owned):

- Frontmatter: `generated_by: /generate-docs (Phase B — glossary)`, `last_indexed: <UTC date>`, `total_terms: <N>`
- H1 `# Project Glossary` + intro paragraph
- Entries sorted alphabetically (case-insensitive). Per entry:
  - `## TermName` heading
  - Definition paragraph
  - `- **Defined**: \`qn:line\``line — omitted for prose-only; gets`(fuzzy)` suffix for fuzzy-anchored
  - `- **Used in**: \`path1\`, \`path2\`, \`path3\``line — capped at 3 inline; if more, append` (and N others)` with the overflow count
  - `- **Related**: term1, term2` line — omitted if `related_terms` is empty
  - `- **Aliases to AVOID**: synonym1, synonym2` line — omitted if `aliases_to_avoid` is empty/absent

Helper stdout on success is the rendered path (`docs/glossary.md`).

### Step B.4 — Retry semantics

- **Exit 0** → done; advance to Phase 5.
- **Exit 1** (I/O failure: cannot read bundles file, atomic write failed, OR CBM unreachable mid-validation while resolving a `code-anchored` / `fuzzy-anchored` entry's snippet) → retry once after the underlying I/O / CBM is back. Transient.
- **Exit 2** (validation rejection) → capture stderr verbatim, re-compose the entries array with the rejection reason as feedback, then re-invoke `set-glossary-entries`. Cap at 3 retries; on the 4th, surface failure to the user and continue with Phase 5 (the glossary is best-effort — its absence does not block the rest of the pipeline).
- If exit 2 stderr includes "bundles file is not valid JSON" (or similar JSON-decode signal pointing at `--bundles-file`), the bundles tmp file from Step B.1 is corrupted — re-run Step B.1 to regenerate it before retrying Step B.3. Re-composing entries will not fix this.

`build-glossary-bundles` itself is idempotent and re-runnable; if Step B.3 keeps failing because the bundle pool is bad, re-run Step B.1 with adjusted `--top-n` / `--bm25-threshold` to reshape the pool.

### Cost (Phase B)

Surface to the user before kicking off Step B.1:

- CBM: ~80 `query_graph` + ~20 `search_graph` fallbacks + ~80 `get_code_snippet` ≈ 1.5s total
- LLM: ~80 define-prompts × ~150 tokens ≈ 12K input + 6K output. Haiku ~$0.10; Sonnet ~$0.30

Phase B assumes CBM is indexed. Phase 1's `preflight` SUBCMD calls `index_repository` (see the `vue_extract` + `index_repository` field in Phase 1's "Captures stdout JSON" list); no additional reindex is required between Phase 4 and Phase B.

---

## Phase 5 — Verify

```bash
./.devforge/lib/generate_docs_helper verify-all
```

Exit 0 = every rendered concern + package doc passes `validate-doc`. Exit 2 = stderr enumerates failures; surface verbatim + STOP (the user re-runs the failed concern / package phase before continuing to Phase 6 Report).

---

## Phase 6 — Report

Print:

- Total concerns from preflight: `concern_counts.unchanged + .changed + .new + .empty`
- Concerns dispatched: count of `changed + new`
- Concerns skipped via stamp gate: `unchanged`
- Concerns rendered + validated: count of green
- Concerns failed after 3 retries: list with paths
- Packages dispatched (Phase 3): count + skipped count
- Package overview docs rendered + validated: N
- Package architecture docs rendered + validated: N
- Package-tier failures: list with paths
- Glossary (Phase B): rendered N entries; M entries marked `[TODO: human-define]` (list those terms); failed-after-retries: yes/no
