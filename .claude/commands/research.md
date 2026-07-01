---
name: research
description: Investigate a bug or enhancement against the codebase; produce a structured research report grounded in CBM + docs.
disable-model-invocation: true
---

# /research — Codebase Research

`/research` is repeatable per ticket. It clarifies a vague bug or enhancement input into a structured symptom memo, runs an orchestrator-direct investigation that consults the CBM graph + `docs/` corpus, composes a research report with mandatory ≥2 hypothesis enumeration, and saves the rendered report to `research/YYYY-MM-DD-<topic-slug>.md`. State + render shape are owned by `.devforge/lib/research_helper`; the orchestrator composes values via setter subcommands. No subagent dispatch — every phase runs in the main thread. Phase 0's hard gate ensures the one-time setup chain (`/init-forge` → `/generate-docs` → `/configure` → `/constitute`) has completed before any investigation fires.

Usage: `/research "<topic>"` (e.g. `/research "items not sorted in admin products view"` or `/research "make export faster on large datasets"`).

## Outputs of this phase

- `.devforge/research-state.json` — SymptomMemo (Phase 1 state). Owned + shaped by the helper; initialized at Phase 0.3 (`reset-memo`, `set-topic`), then mutated via Phase-1 setter subcommands.
- `.devforge/research-report.json` — ResearchReport (Phase 2 + 3 state). Owned + shaped by the helper; mutated only via Phase-2/3 setter subcommands.
- `<install_root>/research/YYYY-MM-DD-<topic-slug>.md` — rendered report. Helper's `render` writes to stdout; orchestrator saves it via the Phase 4 save prompt. Filename slug is auto-derived by the helper from the topic.
- `<install_root>/research/YYYY-MM-DD-<topic-slug>/handoff.json` — the specify-bound handoff, written by Phase 4's `finalize-handoff` on save (nested alongside the flat `.md` file).

On save, Phase 4 `[WIP]`-commits the rendered report + its `handoff.json` into the install repo via `.devforge/lib/artifact_helper commit-artifacts` (install-repo-only, fail-soft) so the work is git-safe the moment it is written; the commit folds into `/finalize`'s squash.

## Phase 0 — Pre-flight gate

Two preflight checks run in order. Both must pass before Phase 1 begins.

### Phase 0.1 — Setup-chain artefact check

```bash
.devforge/lib/research_helper preflight
```

Helper checks four artefacts under `<install_root>`:

- `.devforge/init.yaml` (produced by `/init-forge`)
- `docs/architecture.md` (produced by `/generate-docs`)
- `.devforge/configure.yaml` (produced by `/configure`)
- `constitution.md` (produced by `/constitute`)

Exit 0 → all present + non-empty; proceed. Exit 2 → at least one missing or empty; helper emits a `BLOCKED:` message on stderr naming each missing artefact + producer command. On exit 2: copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then end the turn. The user must run the missing predecessor command(s) and re-invoke `/research`.

### Phase 0.2 — CBM index refresh

```bash
.devforge/lib/generate_docs_helper preflight
```

This refreshes the CBM index stamp so Phase 2 graph queries see current code. Skip the call when `.devforge/.preflight-stamp` is fresher than 60 seconds — the stamp is already current. Check freshness with:

```bash
[ -f .devforge/.preflight-stamp ] && \
  [ "$(( $(date +%s) - $(stat -f %m .devforge/.preflight-stamp 2>/dev/null || stat -c %Y .devforge/.preflight-stamp) ))" -lt 60 ]
```

Exit 0 → stamp fresh; skip the helper call. Non-zero → run `.devforge/lib/generate_docs_helper preflight`. Helper non-zero exit: copy stderr VERBATIM and end the turn; user re-runs `/generate-docs` or `index_repository` and re-invokes `/research`.

### Phase 0.3 — Topic argument

If `$ARGUMENTS` is non-empty, treat it as the topic. If empty, ask the user via AskUserQuestion: `"What's the topic? (bug or enhancement, one sentence)"` — single-line question text, free-text answer. Then reset helper state and stamp topic + date:

```bash
.devforge/lib/research_helper reset-memo
.devforge/lib/research_helper reset-report
.devforge/lib/research_helper set-topic --value "<topic>"
.devforge/lib/research_helper set-verbatim-prompt --value "<full raw $ARGUMENTS>"
.devforge/lib/research_helper set-date --value $(date -u +%Y-%m-%d)
```

`reset-memo` + `reset-report` write fresh-defaults state. `set-topic` auto-derives `topic_slug` for the eventual filename. `set-date` enforces `YYYY-MM-DD`. `set-verbatim-prompt` persists the full original prompt the user passed to `/research` — the complete `$ARGUMENTS`, NOT the one-sentence topic `set-topic` records. `$ARGUMENTS` may carry a multi-sentence prompt (e.g. a symptom plus a trailing "Suspected cause:" hypothesis); the topic is a curated paraphrase, so the un-paraphrased boundary input would otherwise be lost after Phase 0.3. Persisting it here is what lets Phase 4's `finalize-handoff` carry it into the handoff as `Intent.verbatim_prompt`, so a downstream stage can tell what the user ACTUALLY asked from what this command INTERPRETED (per plan 18 Step 1). When `$ARGUMENTS` was empty and the topic came from the AskUserQuestion fallback above, pass that same user reply as `--value` — it is the verbatim input in that branch.

Fresh-every-run: `reset-memo` + `reset-report` ALWAYS run at Phase 0.3, unconditionally. Any prior `.devforge/research-state.json` + `.devforge/research-report.json` are overwritten with fresh defaults. `/research` does not resume mid-flight prior runs — every invocation starts clean. If the user killed a prior run mid-investigation, that work is lost; re-answer the rubric from scratch.

### Phase 0.4 — Suspected-cause classification (pre-rubric, runs before Phase 1)

A `/research` prompt often carries a mechanism guess alongside the symptom — a trailing "Suspected cause: …" clause (or an equivalent lead-in: "I think it's …", "probably because …", "root cause is …", "this is caused by …"). Scan the verbatim prompt persisted by `set-verbatim-prompt` for any such lead-in BEFORE the six-dimension rubric runs. A user- or research-supplied mechanism guess is a CLAIM TO DISPROVE, not a fact: it MUST NOT silently become the `desired` dimension, any other rubric dimension, or the eventual recommended approach. It belongs in the hypothesis lane.

When a suspected-cause clause is present, hold the verbatim mechanism text in working memory now (so it is not lost during the rubric) and carry it forward as one of the candidates Phase 2.5 enumerates. There is no pre-rubric setter for a standalone hypothesis — the suspected cause is persisted by the existing Phase 2.6 `record-hypothesis` call (which requires `--cause`, `--falsifier`, and `--runtime-probe-needed`), alongside the ≥2 enumerated candidates. The point of capturing it here is to guarantee the guessed mechanism enters Phase 2.5 as a hypothesis to disprove — with its own falsifier (the observation that would refute the guessed mechanism) — rather than bleeding into a rubric dimension. This pre-rubric classifier is the home Step 5's binary-classification gate routes `hypothesis` statements into (per plan 18 Step 5 — the user-facing front door over this same lane); treating the suspected cause as a falsifiable hypothesis is what makes it a typed, gate-detectable claim rather than free prose. The captured mechanism feeds Phase 2.5 hypothesis enumeration; it never enters `symptom` / `desired` or any rubric dimension.

When the prompt carries NO suspected-cause lead-in, this step is a no-op — proceed directly to Phase 0.5.

### Phase 0.5 — Intake-interrogation gate (user-facing front door, runs before Phase 1)

Phase 0.4 silently classified a suspected cause and held it in working memory for the hypothesis lane; Phase 0.5 is the USER-FACING front door over that same machinery. It surfaces the framework's interpretation of the verbatim prompt for ONE confirmation before the Phase 1 rubric commits investigation cost — this is the gate that closes the over-solve failure (plan 18 Step 5: in the original failure the user never saw, and so could never correct, the framework's interpretation). Phase 0.5 does NOT re-run Phase 0.4's detection logic — it reuses the detection decision Phase 0.4 made in working memory (the `hypothesis`-vs-`requirement` split) and adds the minimality challenge + echo-back + confirmation on top. Phase 0.5 Step 1 is where that decision is first persisted, via `record-intake-classification`; Phase 0.4 makes no helper call for the classification.

**PROPORTIONALITY (HARD requirement — not advice).** The gate is PROPORTIONATE, inheriting the same proportionality the Phase 1 rubric already carries (its turn caps + accept-gaps coverage exit). Auto-classify the easy parts; surface to the user ONLY the high-stakes ambiguities — conflations (a requirement mixed with a hypothesis), scope-expanders (an extra distinction or state not in the stated desired outcome), and big-design-driving hypotheses (a mechanism guess that would shape the architecture). It is NOT a 20-question inquisition. A clean prompt — no hypothesis, no scope-expander, one obvious minimal fix — passes with ONE echo-back confirmation and ZERO interrogation. Over-interrogating a trivial bug is itself the over-build failure mode this gate exists to fight.

#### Step 1 — Binary-classify each statement

Partition the verbatim prompt (the field `set-verbatim-prompt` persisted in Phase 0.3) into statements and classify each as one of TWO classes: `requirement` (the desired outcome — what the user asked for) vs `hypothesis` (a suspected cause or mechanism guess). Reuse Phase 0.4's detection: a `"Suspected cause:"` lead-in (or equivalent — "I think it's …", "probably because …", "root cause is …") was already detected there and held in working memory for the hypothesis lane; it will be persisted via `record-hypothesis` at Phase 2.6. Here that same statement is ALSO tagged `hypothesis` for the echo-back. Everything else is a `requirement`. Record each statement:

```bash
.devforge/lib/research_helper record-intake-classification \
    --statement "<the prompt statement, verbatim or lightly paraphrased>" \
    --kind <requirement|hypothesis> \
    --minimal-fix "<see Step 2 — pass on requirement statements>"
```

The setter is idempotent on `--statement`: re-recording the same statement overwrites its prior `--kind` + `--minimal-fix` (this is the mechanism the `correct` branch in Step 3 uses). `--kind` must be exactly `requirement` or `hypothesis` (the helper rejects any other value with exit 2). On a clean single-requirement prompt this is ONE call with `--kind requirement`; do not manufacture extra statements to classify.

#### Step 2 — Minimality challenge

Compose the SIMPLEST change that satisfies the stated desired outcome ALONE, and pass it as `--minimal-fix` on the requirement statement. Any addition beyond that simplest change — a guessed mechanism, an extra distinction, a new state — is an "extra" the user must CONSCIOUSLY opt into; it is never assumed into the minimal fix. Concretely for the trip-wire this gate exists to catch: a prompt whose desired outcome is "render an empty section plus an error toast on load failure, never leak the prior items" yields the minimal fix "branch the render on load-failure; show empty + toast" — with NO inline-items mechanism and NO empty-vs-failure split, because neither is in the stated desired outcome. `--minimal-fix` is optional on the setter (omit it on `hypothesis` statements — their minimal fix is "verify first", not a code change), but for the requirement statement carrying the desired outcome it is REQUIRED: it is the surface the user confirms or corrects.

#### Step 3 — Echo-back + ONE confirmation

Render the echo-back block and surface it for confirmation:

```bash
.devforge/lib/research_helper render-intake-echo
```

The helper owns the block shape — `## Intake interpretation` with a `### Requirements (what you asked for)` section (each requirement + its `Minimal scope:` line), a `### Hypotheses to verify — NOT requirements` section (omitted entirely when no hypothesis was classified — the proportionality rule), and a `### Minimal scope` section. The hypotheses section is where a suspected cause surfaces as "hypothesis to verify, not a requirement." Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase) — this is the established verbatim-echo convention; the orchestrator does NOT re-shape the block.

Then ask via AskUserQuestion `"Is this interpretation right?"` with options `["confirm", "correct"]`. End the turn. The user's reply opens the next turn.

- On `confirm`: proceed to Phase 1.
- On `correct`: the user names what was misclassified (a statement that should flip `requirement`↔`hypothesis`, or a minimal fix that scoped too wide). Re-record the affected statement(s) via `record-intake-classification` (the idempotent overwrite on `--statement`), then re-run `render-intake-echo` and echo the corrected block ONCE more. Then ask via AskUserQuestion `"Is this interpretation right?"` with options `["confirm", "correct"]` (same options — this is the ONE bounded correction). End the turn. On the next reply: `confirm` → proceed to Phase 1; `correct` (or any other reply) → proceed to Phase 1 regardless. The gate allows AT MOST one correction pass — it does not loop, so even a second `correct` advances to Phase 1 rather than re-entering this branch.

When the prompt is a clean single-requirement bug with no hypothesis and one obvious minimal fix, Steps 1-2 are a single `record-intake-classification --kind requirement --minimal-fix "…"` call and Step 3 is one echo-back the user confirms in a single turn — zero interrogation, per the proportionality requirement above.

### Phase 0.6 — Re-entry from `/grill` (conditional — skip if no seed)

Before beginning the investigation, check for a `/grill` re-entry seed. Glob `specs/*/grill-seed.json`. If any matched file has a `target_stage` equal to `"research"` (this command's stage), you are re-entering from a `/grill` RE-ENTER-UPSTREAM verdict — the design-time grill proved a plan defect was rooted in THIS research investigation's conclusion, and the re-run must be DIRECTED so it does not re-derive the invalidated conclusion. Read that seed and treat it as a binding directive for this run. Read it DIRECTLY: parse the matched file's flat JSON inline — do NOT call any grill helper or `grill_helper` verb (the orchestrator reads the file itself, so this block stays valid even if `/grill` is ever removed). The seed carries these fields:

- `feature` — the feature this seed was emitted for; read it from the seed and state it up front in your re-entry message (do NOT infer it from the file path).
- `prior_conclusion` — what the previous research investigation concluded; it was invalidated, so do NOT re-derive it.
- `invalidating_evidence` — how `/grill` proved it wrong, grounded in the plan / spec / code.
- `must_satisfy` — what this re-run must now additionally satisfy; address it explicitly.
- `carried_findings` — prior findings to carry forward; stay monotonic (never re-surface a finding a prior pass already disproved).

State up front in your first user-facing message that you are running in grill-re-entry mode for the named `feature`, and name how this run addresses `must_satisfy`. Then run Phases 1–4 normally, with the seed's directive constraining the investigation.

This block only READS the seed's directive. It does NOT delete the seed or change its `cycle_count` — seed lifecycle (deleting or incrementing `cycle_count` after consumption) is handled by the next `/grill` run, which reads `carried_findings` to stay monotonic. That is a v1 simplification; do not add seed-deletion logic here.

When no `specs/*/grill-seed.json` file matches `target_stage == "research"` (the normal case — `/grill` is opt-in, and no seed is ever produced unless a `/grill` run reaches a RE-ENTER-UPSTREAM verdict), this block is a no-op: proceed directly to Phase 1.

## Phase 1 — Symptom clarification (rubric Q&A)

Convert the vague topic into a structured symptom memo across 6 dimensions. The helper owns the rubric; the orchestrator drives one dimension at a time, picking the highest-uncertainty dimension to ask next.

**MANDATORY: never skip the rubric.** Even when `$ARGUMENTS` contains a pre-filled ticket that appears to address all 6 dimensions, ask each dimension question separately and wait for the user's answer in its own turn. Pre-filled input is a STARTING POINT for the `symptom` dimension only — never a license to auto-fill the remaining 5 in one pass. User commitment is per-dimension; that is the forcing function this phase exists for. The rubric is not optional, not advisory, not skippable based on input completeness.

**MANDATORY: never fabricate a user mode.** Do not write — in any user-facing message, internal narration, or tool-call rationale — phrases like "user requested no-questions mode", "user wants free-form", "user said skip the rubric", "no-prompt mode", or any equivalent. No such mode exists. No such request is in scope. If you find yourself about to justify a shortcut by attributing intent to the user, STOP — you are rationalizing a fabrication. Run the rubric.

### Rubric dimensions

| Dimension            | Captures                                                 | Bug-mode example                                     | Enhancement-mode example                                                 |
| -------------------- | -------------------------------------------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------ |
| `symptom`            | What's wrong (bug) or what needs to change (enhancement) | "Items not sorted in admin products view"            | "Export is slow on large datasets"                                       |
| `affected_area`      | Which UI / module / feature surface                      | "Admin > Products > List page"                       | "ExportService background job"                                           |
| `repro_or_current`   | Repro steps (bug) or current behavior (enhancement)      | "Open list with 50+ items, scroll"                   | "5 min runtime on 100K rows; synchronous"                                |
| `desired`            | Expected behavior (bug) or target behavior (enhancement) | "Alphabetical by name, A→Z"                          | "Under 30s OR async with progress"                                       |
| `scope`              | One place / feature-wide / cross-cutting                 | "one place"                                          | "feature-wide"                                                           |
| `unchanged_behavior` | What must NOT regress                                    | "Filter + pagination on same page must keep working" | "Existing small-dataset exports must stay synchronous + complete in ≤2s" |

Per-dimension state enum: `Clear` / `Partial` / `Missing` (default `Missing`). Turn cap: 2 follow-ups per dimension before the helper auto-marks `Partial`.

### Pre-rubric docs scan (orchestrator-only)

Before asking the first dimension question, read the project docs corpus to seed `affected_area` candidates:

- `docs/architecture.md` — project-tier architecture
- `docs/glossary.md` — term grounding

Use CBM for the package + concern lookups; do NOT use raw `Read`/`Grep`/`Glob`:

1. `get_architecture` (CBM) — pulls the rendered architecture md from the graph.
2. `search_graph` with `label="File"` + `name_pattern=<regex on file_path>` — locate candidate package roots that match topic tokens. The argument name is `name_pattern`, NOT `file_pattern`; the wrong name returns silent 0 hits.

Surface 2-3 candidate packages or modules in the next `affected_area` prompt as suggestions.

### Per-dimension question protocol

For each of the 6 dimensions, in highest-uncertainty-first order:

1. **Ask one question.**
   - For `scope`: closed-choice. Use AskUserQuestion with options `["one place", "feature-wide", "cross-cutting"]`. Question text is single-line.
   - For the other five (`symptom`, `affected_area`, `repro_or_current`, `desired`, `unchanged_behavior`): plain prose prompt — paragraph context (if needed) printed as prose ABOVE the question; the question itself is a single line ending with `?`. Wait for free-text reply. Do NOT use AskUserQuestion for these (the answer is open-ended free text).

2. **Persist the answer.** Call the dimension's setter:

   ```bash
   .devforge/lib/research_helper set-<dimension> \
       --value "<user's answer>" \
       --state <Clear|Partial|Missing>
   ```

   Subcommand names: `set-symptom`, `set-affected-area`, `set-repro-or-current`, `set-desired`, `set-scope` **(see narrow-framing gate below — requires `--evidence` when value is `"one place"`)**, `set-unchanged-behavior`. Default `--state` is `Clear` — pass `--state Partial` when the answer leaves a gap. For follow-up turns on the same dimension, add `--increment-turn` so the helper tracks the bounded-turn cap.

   **`set-scope` evidence requirement (narrow-framing gate).** When the user picks `"one place"` from the closed-choice options, `set-scope` requires an additional `--evidence` flag carrying a `file:line` citation that proves the symptom is localized to that single site:

   ```bash
   .devforge/lib/research_helper set-scope \
       --value "one place" \
       --evidence "<path:line of the single symptom site>" \
       --state Clear
   ```

   `--evidence` is REQUIRED whenever `--value` normalizes to `"one place"` (case-insensitive, whitespace-stripped). It must be a real `file:line` citation in `path/to/file.ext:NNN` form — the `(none)` sentinel is rejected because narrow framing demands a concrete locality citation. Without `--evidence`, the helper exits with code 2 and stderr `set-scope: --evidence is required when --value == 'one place'.` plus the rationale (narrowing scope gates Phase 2 exploration depth, so the LLM must commit to a verifiable locality before downstream phases run). When `--evidence "(none)"` is passed, the helper also exits with code 2 and stderr `set-scope: --evidence cannot be '(none)' when --value == 'one place'; narrow framing requires a concrete file:line citation.` The citation should typically be the symptom site identified from the Phase 0 pre-rubric docs scan or from `$ARGUMENTS` if the user supplied a specific file in their topic. For `--value "feature-wide"` or `--value "cross-cutting"`, `--evidence` is not required (broader framings are the safer defaults; narrowing is the risky direction).

   **Recovery on rejection.** If the helper rejects the call (exit 2), copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). Then choose a recovery path based on which rejection fired:
   - Missing or empty `--evidence` → (a) ask the user one follow-up to supply the locality citation if their original answer didn't include a file path, OR (b) re-prompt with the original `AskUserQuestion` options and let them pick a broader framing.
   - `--evidence "(none)"` rejected → only path (b) applies: the user/LLM deliberately passed the sentinel, so re-prompting for a real `file:line` citation OR a broader framing is the only forward path; do not retry with `(none)`.
     Do not retry the setter call without a citation — the gate will reject again.

3. **Run helper-side conflict check.**

   ```bash
   .devforge/lib/research_helper check-conflicts
   ```

   Stdout is a JSON array of detected direct contradictions (token-overlap rule). If the array is non-empty: block via AskUserQuestion `"Which to keep — the new answer or the prior one?"` with the two competing values as options. Then record the resolution:

   ```bash
   .devforge/lib/research_helper record-conflict-resolution \
       --index <0-based index from check-conflicts output> \
       --resolution "user-chose-<new|prior>" \
       --rewrite-dimension <dimension_name>  # underscore form, e.g. affected_area
   ```

   `--rewrite-dimension` clears the loser's value so the user must re-answer it on the next pass.

4. **Run LLM-side drift check.** Compare the just-set answer against the previously-confirmed dimensions held in memory from prior turns. Classify as one of:
   - `direct` — already handled by the helper in step 3; skip here.
   - `drift` — new answer expands scope beyond an earlier confirmed boundary (e.g., `affected_area` was `"one component"` earlier, but the new answer indicates feature-wide). Do not block. Hold the observation in memory; surface it to the user at the next natural pause (after the coverage echo or before mode detection) as a plain-prose note: `"Heads up — your <new dimension> answer suggests <observed drift>. Adjust <affected dimension> or continue?"` Wait for the user's reply before advancing.
   - `refinement` — new answer is a superset of the earlier one (e.g., `"Admin > Products"` → `"Admin > Products + Admin > Orders"`). Re-call the affected dimension's setter with the superset value to overwrite (e.g., `set-affected-area --value "Admin > Products + Admin > Orders" --state Clear`). No user prompt.
   - `mode-flip` — symptom signaled bug-shape, the new answer signals enhancement-shape (or vice versa). Ask via AskUserQuestion `"Treat this as a bug or an enhancement?"` with options `["bug", "enhancement"]`, then call `detect-mode --override <choice>`.
   - `none` — no drift; advance to the next dimension.

   Direct contradictions are persisted by the helper in `memo.conflicts` (step 3 above). Drift, refinement, and mode-flip classifications live in the orchestrator's working memory only — they are not written to `memo.conflicts` by the helper, and the orchestrator must carry them across turns within the same `/research` run by reading prior assistant messages in the conversation.

5. **Advance.** Pick the next highest-uncertainty dimension and return to step 1.

### Coverage check + exit

After all 6 dimensions have been asked at least once OR the user explicitly accepts gaps:

```bash
.devforge/lib/research_helper symptom-coverage
```

Stdout is JSON: `per_dimension` (map of `dim → {state, value, turns}`), `counts` (`{Clear, Partial, Missing}`), `mode`, `conflicts_open` (count of conflicts still `blocked-pending-user`). Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase) so the user sees per-dimension state before deciding to continue or accept gaps.

If the user wants to continue clarifying: return to the per-dimension protocol for any dimension whose state != `Clear`.

If the user accepts gaps: for each dimension with state ∈ `{Partial, Missing}`, record a gap marker, then finalize:

```bash
.devforge/lib/research_helper record-gap \
    --dimension <name> \
    --description "<one-line gap description>"

.devforge/lib/research_helper symptom-finalize --accept-gaps
```

If the user is clarifying all the way to `Clear`, finalize without the flag:

```bash
.devforge/lib/research_helper symptom-finalize
```

Exit code:

- `0` → memo accepted; advance to mode detection.
- non-zero → blocked. Stderr enumerates the reason (unresolved direct conflict OR Partial/Missing without `--accept-gaps`). Copy stderr VERBATIM, end the turn, address the cited issue on the next user reply.

### Mode detection

```bash
.devforge/lib/research_helper detect-mode
```

Stdout JSON: `{"mode": "bug" | "enhancement" | null, "source": "auto" | "override" | "ambiguous"}`. `source = "auto"` on a clear detection from symptom tokens; `source = "override"` when called with `--override`; `source = "ambiguous"` when symptom tokens are mixed-signal and no override was supplied (`mode` is `null` in that case). If `mode` is non-null: advance to Phase 2. If `mode` is null (mixed-signal symptom tokens), ask via AskUserQuestion `"Treat this as a bug or an enhancement?"` with options `["bug", "enhancement"]`, then:

```bash
.devforge/lib/research_helper detect-mode --override <user's choice>
```

### Stop discipline (mandatory)

After emitting any AskUserQuestion or free-text prompt in Phase 1, end the assistant turn. Do NOT advance to the next dimension, the next protocol step, or any helper setter call in the same turn. The user's reply opens the next turn; the next turn parses it and continues. Plain-prose prompts have no harness-level "wait for user" affordance — the LLM-level stop is the only mechanism preventing accidental auto-advance.

## Phase 2 — Investigation (orchestrator-inline)

Phase 2 runs in the main thread — NO subagent dispatch. Orchestrator-inline keeps the full session context intact, which is what the parallel-pattern sweep in Phase 2.4 needs to find sibling bug sites in the same file.

### Phase 2.1 — Cost gate

Before any CBM call, surface the estimated CBM call count + token cost based on `affected_area`. Rough rule of thumb: one-package scope ≈ 15-30 CBM calls; feature-wide ≈ 30-60 calls; cross-cutting ≈ 60-120 calls. Token cost is bounded — orchestrator-inline reuses the existing session context, no fresh subagent boot.

Ask via AskUserQuestion `"Investigation will scan roughly <N> CBM calls. Proceed?"` with options `["proceed", "cancel"]`. On `cancel`: copy a one-line note ("Investigation cancelled. Re-run /research from scratch when ready — prior state will be overwritten.") into the user-facing message and end the turn. On `proceed`: continue.

### Phase 2.2 — Read docs layer first

Read these via the CBM graph (md files are indexed; use `search_graph` with `label="File"` + `name_pattern=<regex on file_path>`, NOT `file_pattern`) before any source-code discovery:

- `docs/architecture.md`
- `docs/<affected_package>/architecture.md` (substitute `<affected_package>` from `memo.dimensions.affected_area.value`)
- `docs/<affected_package>/<closest_concern>/index.md` (closest concern derived from the affected-area phrase)
- `docs/glossary.md`

Docs ground the symptom in package + concern boundaries before code-level discovery fires.

### Phase 2.3 — CBM discovery chain (MANDATORY order)

Raw `Read` / `Grep` / `Glob` / `grep` / `find` / `cat` over source-file extensions are forbidden and will be blocked by runtime hooks. Chain:

1. **`search_graph`** — query for named symbols matching symptom tokens. Use `qn_pattern` for qualified-name regex; `name_pattern` for short-name regex; `label="File"` queries use `name_pattern` (regex on file_path), NOT `file_pattern`.
2. If `search_graph` returns 0 hits for an expected behavior → **`search_code`** — text or regex search with a literal token (e.g. `.sort(`, `.filter(`, `.localeCompare(`) over the affected package. This catches inline expressions buried inside framework reactive blocks (Vue `<script setup>`, React hooks, Svelte reactive blocks) that the graph indexer does not promote to named symbols.
3. **`trace_path`** — impact analysis on confirmed surfaces. Pick a `mode` from `calls` / `data_flow` / `cross_service`.
4. **`get_code_snippet`** — read source on the highest-confidence candidates. This is the only sanctioned source-read path; do not use raw `Read`.

Confidence calibration: 0 hits at `search_graph` alone means "no NAMED implementation"; 0 hits at `search_code` means "truly absent". Do not conflate these.

**`file:line` grounding (MANDATORY).** Every `file_path:line` you will later pass to `record-finding` MUST be copied verbatim from a `search_graph` or `search_code` result row's `file_path` + `line` fields. Never derive a line number from `get_code_snippet` output — `get_code_snippet` returns a code slice whose internal lines do NOT correspond to absolute file line numbers, and the LLM will drift by ±1 to ±N. Never reconstruct a line number from prose context. If you only have a snippet and need the line, re-run `search_code` for a literal token from the snippet to recover the authoritative `file:line` row. If that re-run returns 0 hits, widen the token (try a longer substring or a different literal from the same snippet) and retry once. If still 0 hits, fall back to the original result-row `file:line` you held before calling `get_code_snippet`, and note in `--relevance` that the line could not be re-confirmed.

### Phase 2.3b — Framing challenge (MANDATORY)

Phase 2.3 framing locks in. Without adversarial competition, Phase 2.4 / 2.4b / 2.4c inherit the chosen frame unchallenged — the LLM enumerates hypotheses _within_ the chosen frame, never _across_ competing frames. Phase 2.3b breaks the lock by forcing one alternative-framing commit BEFORE downstream searches run, so subsequent searches probe BOTH frames.

1. **State the PRIMARY framing** in one sentence based on Phase 2.3 evidence ("the bug is caused by X").

2. **State the strongest ALTERNATIVE framing** — a different root-cause hypothesis at the FRAMING level, not at the hypothesis level. Framing-level competition is distinct from the ≥2 hypothesis enumeration the helper enforces in Phase 2.5 — that enumeration produces hypotheses _within_ one frame. Two examples to disambiguate:

   - Same frame, two hypotheses (NOT what Phase 2.3b wants): primary frame "comparator field-name typo" → H1 "primary-id vs alternate-id mismatch" / H2 "type coercion drops the match". Both H1 + H2 live inside the same comparator-typo frame.
   - Different framings (what Phase 2.3b wants): primary "id-field mismatch (presentation-layer fix)" vs runner-up "shallow walk + missing structural classifier (cross-layer fix)". Different root causes, different fix layers, different surfaces.

3. **Identify the CONCRETE FALSIFIER** — the specific evidence that would prove the alternative framing OVER the primary. Phase 2.4 / 2.4b / 2.4c searches will probe FOR this evidence.

4. **Rate `confidence_vs_primary`** as one of `lower` / `comparable` / `higher` relative to the primary framing.

5. **Record via:**

   ```bash
   .devforge/lib/research_helper record-runner-up-framing \
       --frame "<one-sentence alternative root cause>" \
       --falsifier "<concrete evidence that would confirm THIS framing over the primary>" \
       --confidence-vs-primary "lower|comparable|higher"
   ```

   ONE call per `/research` run. Re-calling overwrites (last call wins).

**MANDATORY — never skip, even when the bug looks unambiguous.** The phase exists specifically to challenge "looks unambiguous" framings: the regression class this phase guards against is the LLM that commits to the first plausible frame in Phase 2.3 and stops considering alternatives.

**Downstream impact.** Phase 2.4 / 2.4b / 2.4c findings that support the runner-up frame are tagged `--framing runner-up` when persisted via `record-finding` in Phase 2.6; findings supporting the primary frame default to `--framing primary` (no tag needed). Phase 3's `verify` enforces two gates: check 12a (unconditional) rejects a report whose `runner_up_framing` is unset — Phase 2.3b is mandatory and must execute before `verify` runs; check 12b (conditional on `runner_up_framing` set) rejects a report with zero `--framing runner-up` findings — at least one runner-up-tagged finding (positive or negative) must follow.

### Phase 2.4 — Parallel-pattern sweep (MANDATORY)

Phase 2.4 searches MUST probe both framings recorded in Phase 2.3b. After identifying the primary-frame parallel-pattern surface, run a SECOND search targeting the runner-up frame's falsifier. Findings supporting the runner-up frame are tagged `--framing runner-up` when persisted via `record-finding` in Phase 2.6; findings supporting the primary frame default to `--framing primary` (no tag needed).

After the primary surface is located, run a parallel-pattern sweep over the SAME file before recording findings:

```
search_code(pattern="<primary-frame bug-pattern literal>")
```

The supported `search_code` argument is `pattern` only. Scope the sweep to the primary file by filtering the returned hits in the orchestrator — keep only rows whose `file_path` equals `<primary_file_path>`. Discard every hit outside that file. If `pattern` returns dozens of hits across the package, narrow it (add a containing identifier, include the file's base name as an OR-token in the regex) so the in-file rows surface near the top.

Then run a SECOND `search_code` targeting the runner-up frame's falsifier token PROJECT-WIDE (not in-file-only — the runner-up may surface in a different file):

```
search_code(pattern="<runner-up-falsifier literal>")
```

The falsifier literal comes from the `--falsifier` text recorded in Phase 2.3b — extract a literal code token from it (a method name, a property, a class identifier, a call shape). Both searches are MANDATORY; skipping the runner-up search leaves the runner-up frame's parallel-pattern evidence ungathered and biases the report toward the primary framing by default. If the runner-up search returns 0 hits, record a negative Finding via the Phase 2.6 setter with `--file-line="(none)"`, `--framing runner-up`, `--relevance="runner-up falsifier not found project-wide"`. If it returns hits, evaluate each and record supporting or disproving findings tagged `--framing runner-up`.

Example: primary surface is a `.sort()` at `ProductListView.vue:114` with status-only comparator (primary frame = "unstable comparator"); runner-up frame = "race between fetch and watch" with falsifier literal `watch(` or the fetch handler name. Sweep the primary file for any other `.sort(` / `.filter(` / `.map(` calls that touch the same data shape — there is often a parallel block (e.g. a sibling block at line 252-279) with the same bug; missing the parallel block lets it ship as a regression. Sweep project-wide for the runner-up falsifier literal — hits identify other places where the same race shape could occur. Record every parallel surface AND every runner-up hit as its own `Finding` row with the correct `--framing` tag.

This step is MANDATORY when `mode == "bug"` and the primary surface is an inline expression (sort / filter / comparator / validator). For enhancement mode, sweep is OPTIONAL.

### Phase 2.4b — Canonical-pattern search (MANDATORY)

Canonical-pattern search runs once per framing recorded in Phase 2.3b. The runner-up frame's canonical pattern may diverge from the primary's because the two frames imply different solution classes — search the codebase for the canonical pattern of EACH framing's desired fix. Findings supporting the runner-up frame are tagged `--framing runner-up` when persisted via `record-finding` in Phase 2.6; findings supporting the primary frame default to `--framing primary` (no tag needed).

Before composing approaches in Phase 3, search the codebase for **existing implementations of the DESIRED behavior** — not the bug. Phase 2.3/2.4 chain finds where the bug LIVES; this step finds how the codebase ALREADY SOLVES the same problem class. Reuse beats reinvention; "Search before building" is a constitution constraint in every project.

Run a project-wide `search_code` for the literal token that characterizes the **primary** framing's fix pattern:

```
search_code(pattern="<primary-frame solution-pattern literal>")
```

Then run a SECOND project-wide `search_code` for the literal token that characterizes the **runner-up** framing's fix pattern (the canonical implementation that would resolve the runner-up frame's falsifier):

```
search_code(pattern="<runner-up-frame solution-pattern literal>")
```

Both searches are MANDATORY — the runner-up frame's canonical pattern may diverge from the primary's because the two frames imply different solution classes. Skipping the runner-up search leaves the runner-up frame without a canonical-reuse candidate, which biases Phase 3 toward the primary-frame recommendation by default.

Example (matching the Phase 2.4 example): if the primary frame is "sort comparator with no alphabetical tie-breaker", the primary solution-pattern literal is `localeCompare` (or `sortBy`, or whatever the project's canonical secondary-sort idiom is); if the runner-up frame is "fetch / watch race causes unstable input order", the runner-up solution-pattern literal is the project's canonical reactive-derivation idiom (e.g. `computed(` for Vue, `useMemo(` for React). Result rows from EITHER search = candidate canonical implementations elsewhere in the codebase. For each, judge whether it really solves the same problem class (look at the surrounding structure via `get_code_snippet`).

Record every confirmed canonical implementation as its own `Finding` row with:

- `--surface` = a label naming the helper / file role (e.g. "canonical sort helper", "existing localeCompare site")
- `--file-line` = exact `file_path:line` from the `search_code` result row (per Phase 2.3 grounding rule)
- `--relevance` = the literal phrase "canonical pattern — reusable" followed by a one-line note on what it does
- `--framing` = `primary` when the row supports the primary framing's canonical pattern; `runner-up` when it supports the runner-up framing's canonical pattern (per Phase 2.3b's downstream-impact rule)

These findings feed Phase 3:

- The recommended approach MUST cite the canonical pattern by exact file:line if one was found, and MUST recommend reusing it over writing a new helper. Fresh helper extraction is only justified when Phase 2.4b recorded `file_line = "(none)"` (no canonical found); in that case the `--rationale` must say so explicitly.
- When a canonical pattern was found, the Constitution Constraints section MUST include the "Search before building" rule with the canonical helper's file:line in the impact column. When no canonical was found, omit this entry — its absence is information.

If 0 canonical implementations are found for a framing (the codebase has no existing solution for that frame's problem class): record one `Finding` for THAT framing with `--surface="canonical-pattern search"`, `--file-line="(none)"`, `--relevance="no canonical pattern found project-wide for <framing's solution-pattern>; new helper extraction is justified"`, and the matching `--framing primary|runner-up` tag. Record the negative result independently per framing — a 0-result on the primary search does NOT mean the runner-up search is skipped, and vice versa. This makes the negative result explicit per framing so a reviewer can spot a miss. Note: `"(none)"` is the only sanctioned exception to the Phase 2.3 `file:line` grounding rule — it is a sentinel for an explicitly absent result, not a missing verification.

This step is MANDATORY for both bug and enhancement modes. Skipping it silently re-invents what already exists.

### Phase 2.4c — Helper-API surface enumeration (MANDATORY for bug mode; OPTIONAL for enhancement)

Helper-API surface enumeration runs once per framing recorded in Phase 2.3b. The runner-up frame may surface different fix-path helpers than the primary — the two frames imply different layer-stack entry points. Findings supporting the runner-up frame are tagged `--framing runner-up` when persisted via `record-finding` in Phase 2.6; findings supporting the primary frame default to `--framing primary` (no tag needed).

Without this step the LLM anchors on view-layer / minimal-change fixes when the helper layer already has the inputs to enforce an invariant. Phase 2.4c forces structural evidence — inbound callers, dead siblings, consumer-chain endpoints — onto the report before Phase 3 enumerates approaches.

**Definition of "fix-path helper".** A helper whose signature carries the symptom value, or any value the symptom value derives from.

**Stopping rule (layer-boundary, NOT same-package).** Trace AT MOST 2 layer boundaries above the symptom site, following the dependency-inversion direction (outer-to-inner; e.g., presentation-layer file → composable/store → domain helper → entity static; presentation → application → domain). Stop at framework/vendor packages (do not trace into framework internals, vendored SDKs, or shared utility libs). Cross application/domain package boundaries within the project workspace — this is the explicit point of the rule. The OLD same-package restriction is removed: cross-package traces within the project are NOT just allowed, they are REQUIRED when the symptom lives in a presentation-layer file (Vue / React component, view, page). Verify check 8b enforces this: when the primary finding's `file:line` resolves to a presentation-layer path AND every `fix_path_helpers` entry's `file_line` is in the same package as the symptom, `verify` exits non-zero with a `cross-layer rule` violation. Domain-layer symptoms (a bug whose symptom site is already inside `pkg-<domain>/`) remain same-package OK — no cross-layer trace is required for domain-internal bugs because the helper layer is already the symptom layer.

For each fix-path helper, run the four steps below in order.

**Step 1 — Record the helper itself.** Run `search_graph(label="Method", qn_pattern="<helper QN>")` (or `label="Function"` / `label="Class"` per the helper's kind) to confirm the helper exists in the codebase index and to capture its definition `file_path:line`. Both the helper's qualified name AND its definition `file:line` are required:

```bash
.devforge/lib/research_helper record-fix-path-helper \
    --helper-qn "<helper qualified name>" \
    --file-line "<helper definition file_path:line>"
```

`--file-line` MUST be copied verbatim from the `search_graph` result row's `file_path` + `line` fields — this is where the helper itself is DEFINED, NOT where it is CALLED FROM. The setter rejects the `(none)` sentinel for `--file-line` because layer-boundary detection requires a real path. The setter is dedupe-on-append: re-recording the same `--helper-qn` is a no-op (the existing `--file-line` is preserved).

**Anchor gate (Patch 5).** `--file-line` MUST also anchor to at least one already-recorded `findings[]` row's `--file-line` — either exact match OR same path with line number within ±5 (lenient to absorb minor CBM/trace offsets). This forces every fix-path helper to start from CBM evidence already in the report, not an invented file location. Recording sequence: run Phase 2.3 + 2.4 + 2.4b FIRST (which calls `record-finding` repeatedly), THEN Phase 2.4c (which calls `record-fix-path-helper`). When the helper has no anchoring finding, the setter exits with code 2 and stderr `record-fix-path-helper: --file-line <X> does not anchor to any recorded finding (no finding's file_line collides — exact match or same path within ±5 lines).` plus the current set of finding file_lines for reference.

**Sticky-reject (anti-adversarial).** Once a `(helper_qn, file_line)` pair is rejected by the anchor gate, the setter records it in `helper_rejection_log` and refuses ALL future retries of the same pair, even if a finding at that file_line is recorded post-hoc. This closes the adversarial path where the LLM would record a fabricated finding to unblock a rejected helper. Stderr: `record-fix-path-helper: this (helper_qn, file_line) combo was previously rejected as unanchored (...); cannot retry even if findings now contain a collision (sticky-reject closes the post-hoc-anchor adversarial path).` Workarounds (in order): (a) pick a DIFFERENT `--file-line` for the same helper that anchors to a finding AT THE TIME OF THE NEW CALL; (b) restart `/research` from scratch to clear rejection state. Note: changing the `--helper-qn` alone does NOT unblock — the anchor gate fires on the unanchored `--file-line` regardless of QN, so a new QN at the same unanchored file_line gets its own rejection log entry without making progress. Verify check 14 mirrors the anchor rule at verify time — catches direct-state-mutation bypass attempts.

**Recovery on anchor rejection.** When the helper rejects with the "does not anchor" stderr, copy the stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). Then either (a) return to Phase 2.3 / 2.4 to record the missing finding via `record-finding` FIRST + then call `record-fix-path-helper` with a DIFFERENT `--file-line` (the original combo is sticky-rejected — pick a closer-anchored helper site instead), or (b) reconsider whether the helper QN is the right fix-path target — if Phase 2.4c surfaced it via `trace_path` inbound walk, the trace_path result row's own `file_path:line` is the helper's call-site (which should already be in findings); re-anchor to that.

**Step 2 — Inbound caller enumeration.**

```
trace_path(<helper_qn>, mode=calls, direction=inbound)
```

Record EVERY caller (including the symptom site itself) via:

```bash
.devforge/lib/research_helper record-inbound-caller \
    --helper-qn "<helper_qn>" \
    --caller-qn "<caller_qn>" \
    --file-line "<path:line>"
```

The Phase 2.3 `file:line` grounding rule applies — `<path:line>` MUST be copied verbatim from the `trace_path` result row's `file_path` + `line` fields. Never reconstruct.

**Step 3 — Sibling-method enumeration.**

```
search_graph(label="Method", qn_pattern="<containing_class>\\.")
```

For each sibling returned, run `trace_path mode=calls direction=inbound`. Any sibling that appears to have an empty inbound set MUST be cross-verified via:

```
search_code(pattern="<method-name>(")
```

Only siblings with 0 inbound callers in `trace_path` AND 0 textual call sites in `search_code` are confirmed dead. Record each confirmed dead sibling via:

```bash
.devforge/lib/research_helper record-dead-sibling \
    --class-qn "<class qualified name>" \
    --method-qn "<method qualified name>" \
    --verified-via <trace_path|search_code>
```

`--verified-via` documents which evidence source confirmed the dead state. For any dead sibling discovered through this step, always pass `--verified-via search_code` — the textual cross-check is mandatory and `search_code` is the confirming evidence source. The `--verified-via trace_path` value exists for future cases where a graph-only trace is conclusive on its own; do not use it here. The helper accepts only those two literal values.

**Step 4 — Forward data-flow trace on the symptom value(s).** Extraction rule: from `memo.dimensions.desired.value`, pull every noun-phrase or token that maps to a code symbol (a method, property, class, named data field, or named payload value). If `desired.value` is expressed purely in user-facing terms with no identifiable code-symbols (e.g. 'list shows alphabetically'), skip Step 4 and note in the consumer-chain that desired is expressed in user terms only — Phase 2.5 classification will then default to `preference` (no payload-shape evidence available).

For each symbol cited in `memo.dimensions.desired.value`:

```
trace_path(<symptom-value-source>, mode=data_flow, direction=outbound)
```

Record the consumer-chain endpoint (the consumer that actually reads the value) via:

```bash
.devforge/lib/research_helper record-consumer-chain \
    --value "<symbol>" \
    --consumer-qn "<qualified name>" \
    --file-line "<path:line>" \
    --role "<one-line description of what the consumer does with this value>"
```

The Phase 2.3 `file:line` grounding rule applies to `--file-line` here as well.

**MANDATORY in bug mode.** Skipping is forbidden when `memo.mode == "bug"`. The helper's `verify` step enforces three gates on Phase 2.4c state: check 8 rejects an empty `fix_path_helpers` list in bug mode; check 8b (the cross-layer rule documented in the Stopping rule above) rejects a list where every `fix_path_helpers[].file_line` is in the same package as the primary symptom's file path when that symptom path is presentation-layer (Vue / React / views); check 9 rejects any `fix_path_helpers` entry that has no `inbound_callers` row. On non-zero exit from `verify` citing any of these checks, copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then return to Phase 2.4c and complete the missing steps before re-running `verify`. For check 8b specifically, the fix is to trace one helper UP through a package boundary (presentation → application or presentation → domain) and re-run Step 1 with that helper's qualified name and definition `file:line`.

For enhancement mode this phase is OPTIONAL — run it when the enhancement adds a new code path that touches an existing helper signature; skip when the enhancement is purely additive in a new module.

### Phase 2.4d — Click-handler-to-write-boundary trace (MANDATORY when bug mode + presentation-layer symptom)

Phase 2.4c surfaces helper-API surfaces; it does NOT force the LLM to read intermediate transformers/adapters/mappers that sit BETWEEN the user-action handler and the write-boundary call. Adapter functions advertise shape conversion via their names (`adapter`, `mapper`, `transformer`) and the LLM treats them as identity-preserving on the values they pass through — so a function that silently rewrites `id` to `Math.floor(10000 + Math.random() * 90000)` looks like a no-op from outside and gets skipped. Phase 2.4d closes that gap by forcing end-to-end reads of every intermediate on the call chain from handler to write-boundary.

**Gate.** This phase is MANDATORY when `memo.mode == "bug"` AND the primary finding's `file_line` resolves to a presentation-layer path (Vue / React / views — same `_is_presentation_layer` heuristic check 8b uses). Skip when: (bug mode AND primary finding is a domain-layer path) OR (enhancement mode regardless of layer).

**Step 1 — Identify the user-action handler.** The function on the symptom file that fires on the user's repro action (click handler, form submit, input change). Source: `repro_or_current` dimension prose + the `affected_area` file path. Run `search_code` for event-binding tokens in the symptom file:

```
search_code(pattern="@click=|onClick=|addEventListener|v-on:|onPress|onPanResponderMove|hx-on::|dispatchEvent|useClickHandler|useEventListener")
```

Pick the function bound to the user-action event. Record its qualified name.

**Heuristic-fragility fallback.** If no handler token is found via the `search_code` sweep (dynamic event binding with variable event type, composable-wrapped binding, framework-specific syntax not in the token list, programmatic dispatch), ask the user ONE direct prompt: _"I couldn't auto-detect the click/event handler that triggers the bug from the symptom file. Which function or method handles the user action that reproduces the bug? (give a function name or `file:line`)"_. Wait for the user answer, then proceed. Do NOT guess. Do NOT skip Phase 2.4d on heuristic miss — the user-fallback is the recovery path.

**Step 2 — Identify the write-boundary call.** The function the handler eventually calls that PERSISTS the operation. Write-boundary token list (covers REST + Redux + repository + WebSocket + GraphQL + IndexedDB + SSE + message-bus + Apollo cache + state-management actions):

```
addLine|dispatch|commit|mutate|mutation|repo.save|*.put|*.post|*.create|*.update|*.emit|*.send|*.publish|cache.writeQuery|cache.writeFragment|store.put|tx.add|tx.put|.dispatchEvent|eventBus.emit|bus.publish
```

Run `search_code` for those tokens in the symptom file. Pick the call whose receiver name matches one of the tokens AND whose argument list visibly carries the symptom value (the value cited in `memo.dimensions.symptom` or `memo.dimensions.desired`). Record its qualified name. If no token matches (project uses non-conventional write-boundary verbs not on the list — e.g., `tellSaga`, `enqueueWork`, `requestSync`), ask the user ONE direct prompt: _"I couldn't auto-detect the write-boundary call (the function that persists the operation) from the symptom file. Which function in the call chain actually persists the change? (give a function name or `file:line`)"_. Wait for the user answer, then proceed.

**Step 3 — Trace handler → write-boundary.** Run:

```
trace_path(<handler_qn>, mode=calls, direction=outbound)
```

Record the full path of intermediate function QNs (everything between the handler and the write-boundary call, exclusive on both ends). Use `mode=calls` always — CBM's `mode=data_flow` returns identical hop lists to `mode=calls` for first-party project code (pre-flight verified 2026-05-18) and provides no incremental signal.

**Handler-not-a-graph-node fallback.** Vue / SFC template files emit only File and Module nodes in the CBM graph — the handler defined in `<script setup>` may not resolve as a Function node. If `trace_path` returns empty OR `search_graph(name_pattern="<handler_name>")` returns 0 results, ask the user ONE direct prompt: _"I couldn't trace from `<handler>` to a write-boundary call via the code graph (Vue/template files often aren't indexed at function granularity). What intermediate functions does the handler call before reaching the persistence call? (list function names or `file:line` references)"_. Wait for the user answer, then proceed with the user-supplied chain.

**Step 4 — Read each intermediate end-to-end + record findings.** For EACH intermediate function on the path (excluding the handler and the write-boundary themselves), apply two cumulative filters to decide whether to call `get_code_snippet`:

1. **First-party filter.** Skip functions whose source file is in framework / vendor / SDK packages (Vue runtime, Pinia store internals, BLoC infrastructure, `node_modules/*`, `@vue/*`, `@pinia/*`). Read only first-party project workspace files.
2. **Shape-conversion-name filter (priority hint).** Preferentially read functions whose name matches a shape-conversion pattern (case-insensitive substring): `adapter|mapper|transformer|normalizer|converter|serializer|deserializer|encoder|decoder|wrapper|builder|formatter|parser`. These names advertise shape conversion but commonly hide value mutation. Pure-passthrough functions (handlers / dispatchers / forwarders whose names do NOT match the pattern) may be skipped at LLM discretion when the file body is large. The filter is a HINT, not a hard gate — when in doubt, read.

For each function read, look for value-mutation patterns: `Math.random`, `crypto.random`, `Date.now`, `uuid()`, manual id reassignment (`item.id = ...`, `obj[...] = ...`), `structuredClone` / destructuring that loses fields, type-coercion that drops precision.

Then record EACH intermediate function as a Finding row via:

```bash
.devforge/lib/research_helper record-finding \
    --surface "data-flow intermediate: <one-line role>" \
    --file-line "<path:line>" \
    --relevance "<one-line note — include the intermediate's qualified name here (or in --surface)>" \
    --framing "primary"
```

Either the `--relevance` or `--surface` text MUST contain the intermediate's qualified name as a substring — the `record-data-flow-chain` setter substring-matches each `intermediate_qns[i]` against existing findings' `relevance` AND `surface` fields and rejects intermediates with no referencing finding. Inline-call expressions also count as intermediates: when the write-boundary call argument list contains a function call expression (not just identifier passthrough), the call expression's callee MUST be added to `intermediate_qns` as well.

**Step 5 — Persist the chain.** After every intermediate has a recorded Finding:

```bash
.devforge/lib/research_helper record-data-flow-chain \
    --handler-qn "<handler qualified name>" \
    --write-boundary-qn "<write-boundary qualified name>" \
    --intermediate-qns '["<intermediate_qn_1>", "<intermediate_qn_2>", ...]'
```

`--intermediate-qns '[]'` is valid (direct handler→write-boundary call with no intermediates). The setter validates each intermediate_qn against existing findings; if any intermediate has no referencing Finding, the setter exits with code 2 — copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), record the missing Finding via `record-finding` first, then re-run `record-data-flow-chain`. Last-write-wins on subsequent calls.

**Verify enforcement.** The helper's `verify` step adds check 15: when bug mode + presentation-layer primary symptom, `data_flow_chain` must be non-null. On non-zero exit from `verify` citing check 15, copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then return to Phase 2.4d Step 1 to complete the missing trace.

### Phase 2.5 — Hypothesis enumeration (MANDATORY ≥2)

**MANDATORY value-semantics classification (run before hypothesis enumeration).** For every symbol extracted via the Phase 2.4c Step 4 extraction rule, classify it as one of:

- `preference` — per-user-action, per-toggle, per-request-context (e.g., a sort order the user picked, a filter the user set).
- `invariant` — per-identity, per-business-rule, payload-shape contract (e.g., an identifier required by the API contract, a flag the receiver dispatches on).
- `unclassified` — evidence insufficient to commit to either.

Evidence should cite a `consumer_chain` row recorded in Phase 2.4c — `--evidence` typically cites the consumer's `file:line` or its role string. (Helper does NOT validate the `--evidence` content beyond non-empty; the existence of a `consumer_chain` row for the same `--value` is what the helper enforces when `--classification invariant` is passed.) Call:

```bash
.devforge/lib/research_helper set-value-semantics \
    --value "<symbol>" \
    --classification <preference|invariant|unclassified> \
    --evidence "<text — typically a file:line or consumer name>" \
    --stable-across-calls <true|false|unknown>     # REQUIRED when --classification invariant
```

**`--stable-across-calls` (stability axis — REQUIRED for invariant).** A value being invariant by KIND (an `id`, a contract field, a payload-shape token) does NOT imply the value is STABLE across calls. An adapter / transformer / mapper between the user-action handler and the write-boundary may reassign the value per call (`Math.random()`, `Date.now()`, `uuid()`, manual id reassignment). The kind axis and the stability axis are independent — an invariant id that is randomized per call still satisfies "invariant by kind" but breaks any downstream comparator that expects stability.

Pass `--stable-across-calls true` when Phase 2.4d's data-flow chain shows every intermediate is identity-preserving on the value (no `Math.random` / `Date.now` / manual reassignment in any intermediate body). Pass `--stable-across-calls false` when at least one intermediate rewrites the value (and call `record-value-production-site` for the rewriter site FIRST — see below). Pass `--stable-across-calls unknown` ONLY when the symptom is domain-layer (no presentation-layer trace path applies); the helper REJECTS `unknown` for presentation-layer symptoms because Phase 2.4d's data-flow chain (already recorded) provides the structural evidence to investigate.

**Helper gates on `set-value-semantics --classification invariant`.** Four independent rejections (evaluated in this order — first failing gate emits the rejection):

1. `--stable-across-calls` is required — exit 2 if omitted.
2. `--stable-across-calls unknown` AND symptom is presentation-layer — exit 2 with: investigate the production site via Phase 2.4d data-flow chain (already recorded) before classifying.
3. No `consumer_chain` row for `--value` — exit 2 (unchanged from prior phase). Recovery: return to Phase 2.4c Step 4 and call `record-consumer-chain` first.
4. `--stable-across-calls false` requires at least one `value_production_sites` row for `--value` — exit 2. Recovery: call `record-value-production-site` first.

On any exit 2, copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). The helper writes nothing on rejection — the state file is untouched.

**Production-site recording (required before `--stable-across-calls false`).** When Phase 2.4d's intermediate-trace reveals a rewriter (an intermediate function whose body contains `Math.random`, `crypto.random`, `Date.now`, `uuid()`, or a manual id reassignment), record the rewriter site:

```bash
.devforge/lib/research_helper record-value-production-site \
    --value "<symbol>" \
    --file-line "<rewriter file:line — the exact line where the value is assigned/computed>" \
    --is-stable <true|false>
```

The setter is append-only with `(value, file_line)` distinct dedupe. A single value may have MULTIPLE production sites (e.g., three adapters all rewriting the same id field — record each via a separate call with distinct `--file-line`). The setter rejects the `(none)` sentinel — production site must be a real path. `--is-stable false` flags a randomization site (the value differs across calls — e.g., `Math.random`, `Date.now`, `uuid()`); `--is-stable true` flags a deterministic reassignment site (the value is reassigned but produces the same output for the same input — e.g., a normalization helper, a hash function, an enum-coercion).

Why this matters: an invariant value mis-classified as preference produces hypotheses framed "the UI didn't seed correctly" — wrong framing leads to view-layer fix recommendations in Phase 3. A stable-but-unstable invariant value mis-classified as just "invariant by kind" produces hypotheses framed "id field-name mismatch" or "type coercion" — wrong framing leads to comparator fixes in the symptom file while the actual rewriter at the production site continues to randomize the id every call. Classification + stability ground hypothesis enumeration in the right semantics.

Enumerate at least 2 candidate root causes for the symptom. For each, write a one-line falsifier (the observation that would disprove it) and mark whether falsification needs runtime data. Single-hypothesis output is rejected by the helper's `verify` gate.

**Hypothesis-citation gate (check 16).** In bug mode, when any `value_semantics` row has `--stable-across-calls false` (recorded above), at least one `record-hypothesis --cause` text MUST contain a `value_production_sites[].file_line` for one of those unstable values as a substring (word-boundary match on the `:line` suffix — `src/foo.ts:5` does NOT match `src/foo.ts:50`). The helper's `verify` step (check 16) exits with code 2 when no hypothesis cites any production-site file_line — the LLM must enumerate the production-site rewriter as a candidate root cause. Enhancement mode skips check 16 (no production-site-rewriter root cause enumeration is required). On exit 2 in bug mode, copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then add a hypothesis whose `--cause` text references the production-site `file:line` literally (e.g., `--cause "id is randomized per-call at src/helpers/strataFamilyToItemAdapters.ts:5 via Math.random()"`).

For any hypothesis whose falsifier needs runtime data (lifecycle race, framework lifecycle gap, vendor side-effect, network-shaped issue, timing-shaped issue), prepare a specific probe — a `console.log` probe, an `app.config.warnHandler` capture, a network-tab inspection, a breakpoint dump, etc.

### Phase 2.5b — Literal archaeology (MANDATORY when bug points at a hardcoded literal)

Phase 2.5 classifies value semantics + stability for symbols. It does NOT examine WHY a primitive literal exists at the bug site. A hardcoded `false` / `0` / `null` / `"string"` at the bug location has historical intent — placeholder, migrated from a legacy system, deliberate policy, forgotten across a later policy change, inherited verbatim by a refactor, or generated. Without that classification, the LLM treats the literal as "the bug" and proposes literal-replacement at the call site — which is the wrong fix layer when intent ∈ {placeholder, forgotten, inherited-refactor} (default-source belongs upstream: wrapper signature, state-init factory, or use-case default).

**Trigger.** Run Phase 2.5b when ALL of the following hold: (1) bug mode; (2) Phase 2.4d's data-flow chain trace reveals a hardcoded primitive literal at a finding's `file_line` (one of the intermediate functions passes or assigns the literal rather than a variable) OR the Phase 3 recommended approach you are about to draft will replace a primitive literal with a different value. When in doubt, run Phase 2.5b — check 17 will fire at verify if the approach replaces a literal and archaeology was skipped. "Primitive literal" = JS/TS `true|false`, Python `True|False`, `null|undefined|None`, decimal / hex / BigInt / scientific number, single-quoted / double-quoted / backtick-template string. Array / object / regex / function literals are OUT OF SCOPE — record them as ordinary findings instead.

**Steps.**

1. **Find the introducing commit.** Run `git log -S "<literal>" -- <file>` with `<literal>` quoted (escape shell metacharacters). The introducing commit is the OLDEST commit whose diff added the literal (last entry in the log output). Multi-commit history is OUT OF SCOPE; anchor on the oldest.

2. **Read the commit subject.** Run `git show --stat <introducing-commit-sha>` to see the commit's subject line and which files it touched.

3. **Confirm author + date via blame.** Run `git blame -L <start>,<end> <file>` around the literal's line; the blame entry's author + date confirm the introducing-commit fingerprint.

4. **Classify intent.** Pick ONE of the 6 enum values:

   | Intent               | When it applies                                                                                                                                                                          |
   | -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
   | `placeholder`        | Literal was a TODO / FIXME / temporary value (commit msg or surrounding code says "default for now", "TBD", etc.).                                                                       |
   | `migrated`           | Literal carried over from a legacy system (commit msg cites the migration; surrounding code references the legacy identifier).                                                           |
   | `deliberate`         | Literal was a considered policy choice with rationale in the commit message (commit msg explains WHY this value).                                                                        |
   | `forgotten`          | Literal added during a feature intro but never updated when a later policy was added (commit msg introduces the feature; a later commit adds the policy without revisiting the literal). |
   | `inherited-refactor` | A later refactor preserved the literal verbatim while restructuring around it (commit msg describes structural change, not value change).                                                |
   | `generated`          | Literal lives in a generated file (path matches `**/generated/**` or `**/node_modules/**`, OR file header has an `AUTO-GENERATED` marker).                                               |

5. **Record the archaeology.** Call:

   ```bash
   .devforge/lib/research_helper record-literal-archaeology \
       --literal "<literal as it appears in source>" \
       --file-line "<path:line>" \
       --introduced-by "<commit sha — 7 to 40 hex chars>" \
       --introduced-when "<YYYY-MM-DD>" \
       --commit-subject "<one-line subject from the commit>" \
       --intent <placeholder|migrated|deliberate|forgotten|inherited-refactor|generated>
   ```

   The setter dedupes on `(literal, file_line)` — re-recording the same pair is a no-op (first write wins on the `--intent` value). The setter rejects the `(none)` sentinel and unrecognized literal tokens. On exit 2, copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase).

**Per-intent recovery rule (drives Phase 3's recommended-approach drafting).**

- `intent ∈ {placeholder, forgotten, inherited-refactor}` → the fix layer is NOT the literal site. Escalate the default-source one layer up: literal at a call-site → default at the wrapper signature; literal at state init → default at the state-init factory function; literal in a use-case caller → default in the use-case method signature. Phase 3 must propose the upstream default, not literal replacement at the call site.
- `intent == migrated` → investigate the legacy system's behavior for the SAME literal before recommending. The legacy version likely had a different default OR an upstream policy that the migration dropped. Surface the legacy gap in Phase 3's rationale.
- `intent == deliberate` → literal replacement may be the right fix (LLM's instinct was correct), BUT the archaeology row + commit-msg cite are REQUIRED to justify overriding a documented deliberate choice. Phase 3 rationale must cite the introducing commit by SHA + subject.
- `intent == generated` → fix layer is the generator template, not the consumer. Trace back to the template file; propose the change there. Phase 3 should NOT recommend editing the generated file.

**Helper verify check 17.** When Phase 3 sets a recommended approach whose `--rationale` or whose linked approach's `--description` contains literal-replacement prose (`replace <X> with <Y>` / `change <X> to <Y>` / `<X> -> <Y>` / `swap the literal <X> with <Y>`) and no `literal_archaeology` row exists for `<X>` at a recorded finding's `file_line`, `verify` exits with code 2 citing check 17. Recovery: run the steps above + `record-literal-archaeology`, then re-run `verify`.

**Fallback when archaeology fails.** On a shallow git clone or a file not under git tracking: `git log -S` returns 0 commits OR `git blame` returns `(uncommitted)`. Treat the archaeology as inconclusive — pass `--intent forgotten` (the conservative classification — forces fix-layer escalation per the recovery rule) and add a one-line note in the recommended-approach rationale: `"archaeology inconclusive (shallow clone or untracked file); intent assumed forgotten per Phase 2.5b fallback rule"`.

### Phase 2.6 — Wire findings into helper

After the CBM chain + parallel-pattern sweep + canonical-pattern search + helper-API surface enumeration (Phase 2.4c) + hypothesis enumeration complete, call helper setters in this order. Phase 2.4c state (`fix_path_helpers`, `inbound_callers`, `dead_siblings`, `consumer_chain`, `value_semantics`) is already recorded in the report by its own setters — do not re-record those surfaces via `record-finding`. Compose values from the in-context findings; do not re-shape.

For each finding — one per code surface that bears on the symptom, including every parallel surface from Phase 2.4 AND every canonical-pattern row from Phase 2.4b. Apply the same `search_code` pre-verification loop to canonical rows. The `--file-line="(none)"` negative-result row from Phase 2.4b is exempt from `search_code` verification — `(none)` is the sentinel value, not a path to verify.

```bash
.devforge/lib/research_helper record-finding \
    --surface "<surface label>" \
    --file-line "<path:line>" \
    --relevance "<one-line how-it-relates>" \
    --framing "<primary|runner-up>"
```

`<path:line>` MUST be the exact `file_path:line` from a `search_graph` or `search_code` result row (per Phase 2.3 grounding rule). BEFORE every `record-finding` call, run a one-line verification: `search_code(pattern="<expected literal at that line>")` and confirm the result row's `file_path:line` matches the value you are about to pass. On mismatch, take the result row's line as authoritative and pass THAT to `--file-line`; the LLM's recollection is wrong (off-by-one drift is the failure this catches). Only after the verification matches: call `record-finding`. If the verification `search_code` returns 0 hits: widen the pattern (try an adjacent literal) and retry once. If still 0 hits, pass the original result-row `file:line` you already hold (from the Phase 2.3 chain) and note the unconfirmed status in `--relevance`. Do not skip the finding.

`--framing` is optional and defaults to `primary` when omitted. Pass `--framing runner-up` for findings that support the runner-up framing recorded in Phase 2.3b — including NEGATIVE findings (evidence disproving the runner-up). At least one finding must carry `--framing runner-up` for `verify` check 12b to pass (check 12b fires only once `runner_up_framing` is set; check 12a — the unconditional gate that demands `runner_up_framing` be set at all — is satisfied earlier by the Phase 2.3b `record-runner-up-framing` call). That one finding may be positive (evidence supporting the runner-up) or negative (evidence the runner-up's falsifier did not hold up).

For each hypothesis (≥2):

```bash
.devforge/lib/research_helper record-hypothesis \
    --cause "<cause text>" \
    --falsifier "<one-line falsifier>" \
    --runtime-probe-needed <yes|no>
```

Then the primary root cause + confidence:

```bash
.devforge/lib/research_helper set-root-cause-hypothesis --value "<text>"
.devforge/lib/research_helper set-confidence --value <Confirmed|Hypothesis|Speculative>
```

Bug-mode structured root cause (only when `memo.mode == "bug"` AND `confidence ∈ {Confirmed, Hypothesis}`):

```bash
.devforge/lib/research_helper set-trigger --value "<immediate event>"
.devforge/lib/research_helper set-root-cause-systemic --value "<underlying systemic flaw>"
.devforge/lib/research_helper record-contributing-factor --value "<factor>"
# repeat record-contributing-factor up to 3 times
```

**Probe feasibility classification (MANDATORY — all modes).** Before the verify-step block below, classify the probe's feasibility along five boolean axes. These flags feed the downstream `finalize-handoff` probe-tier classifier (tier 1 = LLM unit test, tier 1.5 = LLM standalone script, tier 2 = LLM via chrome MCP, tier 3 = user manual). Call:

```bash
.devforge/lib/research_helper set-probe-feasibility \
    --data-shape-only <true|false> \
    --auth-required <true|false> \
    --network-dependent <true|false> \
    --timing-dependent <true|false> \
    --is-test-code <true|false>
```

Flag semantics:

- `--data-shape-only` — verification depends only on data shapes / function outputs / state values, with no auth, network, or timing dependencies.
- `--auth-required` — verification needs an authenticated session (logged-in user, API token, etc.).
- `--network-dependent` — verification needs real network calls or external services (not stubbable).
- `--timing-dependent` — verification depends on race conditions, lifecycle ordering, or async timing.
- `--is-test-code` — the bug is in test code itself; probing the test would be circular, so the classifier forces tier 3 (user manual).

All five flags are required in one call. Each accepts exact lowercase `true` or `false` only (argparse exact-match; `True` / `TRUE` are rejected; on rejection, stderr will read `invalid choice` — verify lowercase and retry without JSON-escaping). `finalize-handoff` in Phase 4 rejects with exit 2 + `"finalize-handoff: probe_feasibility incomplete; missing flags: [...]"` when any flag is unset. Call `set-probe-feasibility` immediately after the structured root-cause block (before the verify-step) — the classifier must run before finalize-handoff, and early placement avoids accidental omission.

If any hypothesis carries `runtime_probe_needed=yes`, set the verify step (all three sub-fields required in one call):

```bash
.devforge/lib/research_helper set-verify-step \
    --probe "<log/instrumentation to add>" \
    --reproduction "<exact user action that triggers the symptom>" \
    --discriminator "<if X → H_n confirmed; if Y → H_m confirmed>"
```

**Probe-script (CONDITIONAL — fires when tier resolves to 1.5).** Run this sub-step ONLY when ALL of the following hold based on flags you just set + a one-line state read:

- `set-probe-feasibility` flags above: `data_shape_only=true` AND `auth_required=false` AND `network_dependent=false` AND `timing_dependent=false` AND `is_test_code=false`.
- `.devforge/init.yaml`'s `test_infra.status` is `"absent"` OR the `test_infra` block is missing entirely. Read via:

  ```bash
  grep -E "^  status:" .devforge/init.yaml || echo "(no test_infra block)"
  ```

  Interpret: a line `  status: absent` (or empty/missing output) satisfies the condition; `  status: present` does not.

If ALL conditions hold → tier will resolve to 1.5 in Phase 4 `finalize-handoff`; proceed with steps 1-4 below. Otherwise SKIP this entire sub-step.

1. Create a script file at `research/<report.date>-<memo.topic_slug>/probe-script.<ext>` (directly under that directory — no subdirs). Extension matches the chosen runtime:
   - `node` / `deno` / `bun` → `.mjs`
   - `python` → `.py`
   - `ruby` → `.rb`
2. Inline the buggy logic VERBATIM from the cited `file:line` locations recorded as findings in Phase 2.4d / 2.5. Do NOT reconstruct from memory — copy the source bytes. Prepend each inlined block with a `// SOURCE: <file>:<line>` comment (use the runtime's comment syntax — `#` for python/ruby) so the inlined-from contract is auditable.
3. The script's pass/fail assertion must map to the `--discriminator` set in the verify-step block above (one observable outcome per hypothesis).
4. Record the script:

   ```bash
   .devforge/lib/research_helper record-probe-script \
       --script-path "research/<report.date>-<memo.topic_slug>/probe-script.<ext>" \
       --runtime <node|python|ruby|deno|bun> \
       --inlines-from '["<path>:<line>", "<path>:<line>", ...]'
   ```

Validators (all rejected with exit 2 + stderr message prefixed `record-probe-script: ...`): `--script-path` file must exist on disk AND live DIRECTLY under `research/<report.date>-<memo.topic_slug>/` (no subdirs); `--runtime` must resolve via `shutil.which`; `--inlines-from` must be a non-empty JSON array of `<path>:<line>` tokens (each `<line>` must be digits-only). Strict-match idempotency: re-recording the same `--script-path` with a different `--runtime` or different `--inlines-from` is rejected exit 2 — to revise an entry, run `reset-report` and re-record from scratch, or choose a different `--script-path`. Exact re-record of the same triple is a no-op (exit 0 + stderr "already recorded" notice).

Skip-clause consequences. If you skip this sub-step but tier later resolves to 1.5 in Phase 4 `finalize-handoff`, the handoff.json will fall back to the deterministic default `research/<date>-<slug>/probe-script.mjs` — but no file exists at that path, leaving a dangling reference. If you record a probe script but tier resolves to ≠ 1.5, the recorded entry is silently ignored — `finalize-handoff` only reads `probe_scripts` when it classifies tier 1.5, so the entry stays in `research-report.json` unused and the written script file lingers on disk. Skip only when the trigger conditions above clearly don't hold; recording speculatively wastes work and leaves an unreferenced file behind.

Non-zero exit on any setter: capture stderr, fix the value (likely a JSON-escape issue on a multi-line string), retry up to 3 times. On the 4th failure, copy stderr VERBATIM to the user and end the turn; user must re-run `/research` from scratch — prior partial state will be overwritten.

## Phase 3 — Report drafting + render

Phase 3 is orchestrator-direct compose (NO subagent dispatch). Read memo + report state once for context, then call the Phase 3 setters listed below in order.

```bash
.devforge/lib/research_helper read-memo
.devforge/lib/research_helper read-report
```

### Setters (in order)

1. **Summary** (3-5 sentences: what was found, root cause, recommended approach, remaining uncertainty):

   ```bash
   .devforge/lib/research_helper set-summary --value "<3-5 sentences>"
   ```

2. **Approaches** (typically 2; each must cite which hypothesis indices it addresses + which it does NOT cover). Hypothesis index strings come from the order the hypotheses were recorded in Phase 2 — refer to them as `"A"`, `"B"`, ... For each approach:

   ```bash
   .devforge/lib/research_helper set-approach \
       --name "<approach name>" \
       --description "<1-2 sentences>" \
       --addresses-hypotheses '["A","B"]' \
       --does-not-cover '["C"]' \
       --pros '["pro-1", "pro-2"]' \
       --cons '["con-1", "con-2"]' \
       --complexity <Low|Med|High>
   ```

   **MANDATORY (when `value_semantics` contains an invariant row AND `dead_siblings` is non-empty):** at least one approach in the enumerated list MUST touch the helper signature or revive a dead sibling — and MUST cite the dead-sibling `method_qn` (or the literal token `signature`) explicitly in the approach's `--name`, `--description`, `--pros`, or `--cons`. The helper's `verify` step (check 10) enforces this: on non-zero exit citing "no approach mentions helper signature change or dead-sibling QN", copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then re-call `set-approach` (overwriting or adding) so at least one approach satisfies the check.

3. **Recommended approach** — name must match an existing approach. Helper additionally enforces "must not violate `memo.dimensions.unchanged_behavior.value`" via a cross-check; pick the approach + cite hypotheses accordingly:

   ```bash
   .devforge/lib/research_helper set-recommended-approach \
       --name "<must match an approach.name>" \
       --rationale "<why this approach + acknowledged uncertainty>" \
       --hypotheses-addressed '["A","B"]' \
       --hypotheses-not-covered '["C"]'
   ```

   **MANDATORY canonical-pattern citation.** If Phase 2.4b recorded any `Finding` row with `relevance` starting "canonical pattern — reusable", the `--rationale` MUST cite that pattern's `file:line` and state the recommended approach REUSES it (not reinvents). Only justify a fresh helper extraction when the canonical pattern's `file_line` was recorded as `(none)` in Phase 2.4b (no canonical found), and the `--rationale` must say so explicitly: "no canonical pattern exists project-wide; new helper justified".

   **MANDATORY (when `value_semantics` contains an invariant row):** `--rationale` MUST cite at least one of: a `consumer_chain` row's `consumer_qn`, an invariant row's `evidence` string, OR a `dead_siblings` row's `method_qn`. The helper's `verify` step (check 11) enforces this: on non-zero exit citing "rationale cites neither a consumer_chain entry, an invariant evidence string, nor a dead-sibling QN", copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then re-call `set-recommended-approach` with a `--rationale` that contains one of those tokens.

   **Single-layer recommendation gate (Patch 4).** When all `fix_path_helpers[].file_line` resolve to the same package (single-layer detection via `_extract_package`, same heuristic as check 8b), the recommendation is anchored to one layer-stack region. The helper requires TWO additional args to defend the choice:

   ```bash
   .devforge/lib/research_helper set-recommended-approach \
       --name "<must match an approach.name>" \
       --rationale "<why this approach + acknowledged uncertainty>" \
       --hypotheses-addressed '["A","B"]' \
       --hypotheses-not-covered '["C"]' \
       --single-layer-justification "<prose: why symptom is layer-local>" \
       --cites '["<recorded row token>","<recorded row token>"]'
   ```

   `--single-layer-justification` is free-text prose explaining why the symptom is genuinely layer-local. `--cites` is a JSON array of tokens, each of which MUST resolve to a recorded `consumer_chain.consumer_qn`, `value_semantics.value`, `value_semantics.evidence`, OR `dead_siblings.method_qn` — the helper rejects any cite token that doesn't match a recorded row. Without `--single-layer-justification`, the helper exits with code 2 and stderr `set-recommended-approach: --single-layer-justification is required when all fix_path_helpers resolve to the same package (<pkg>).` Without `--cites` (or with `--cites '[]'`), the helper exits with code 2 and stderr `set-recommended-approach: --cites is required (non-empty JSON array)…`. Verify check 13 catches the same conditions at verify time (covers out-of-order setter calls where `recommended_approach` was written before `fix_path_helpers` collapsed to single-layer).

   **Suppression (check 8b precedence).** When check 8b would fire — i.e., the primary symptom's `file:line` is in a presentation-layer file (.vue / .tsx / .jsx / views / components / pages) AND all helpers are in the same package as the symptom — the single-layer gate is SUPPRESSED at both setter time AND verify time. Rationale: check 8b vetoes verify unconditionally for presentation-layer same-package state, so supplying `--single-layer-justification` cannot rescue the report. The LLM's only recovery path in that case is to add a cross-layer helper via Phase 2.4c, not to defend the single-layer recommendation. Reading order: if `verify` reports `cross-layer rule` (check 8b), trace one more helper UP through a package boundary in Phase 2.4c — do NOT attempt to satisfy check 13.

   **Recovery on rejection.** If the helper rejects the call (exit 2), copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). Identify the rejection cause from the stderr text, fix the missing arg (supply justification, supply non-empty cites, or replace an unresolved cite with one that matches a recorded row), and re-call `set-recommended-approach`.

   **MANDATORY (when the recommended approach replaces a hardcoded literal):** if `--rationale` or the linked approach's `--description` will contain literal-replacement prose (`replace <X> with <Y>` / `change <X> to <Y>` / `<X> -> <Y>` / `swap the literal <X> with <Y>`) where `<X>` is a primitive literal, Phase 2.5b `record-literal-archaeology` for `<X>` at the bug's `file_line` MUST have been called BEFORE `set-recommended-approach`. Check 17 enforces this at verify time: on non-zero exit citing check 17, copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), run Phase 2.5b's git-archaeology steps + `record-literal-archaeology`, then re-run `verify`.

   **Proposed call-shape gate (Patch 9).** In bug mode, when EITHER `--single-layer-justification` is set OR `--rationale` (or the linked approach's `--description`) contains literal-replacement prose, `--proposed-call-shape` is REQUIRED. The shape must be the exact post-fix call as it would appear at the bug site (function name + parenthesized arg list, multi-line accepted — helper collapses whitespace). The helper parses the shape, splits the arg list on top-level commas, and rejects when the same identifier (bare name, dotted member access, or optional-chained `a?.b?.c`) appears more than once — argument duplication signals the default-source belongs at a different layer (wrapper signature / state initialization / use-case default) rather than at the call site. Example call:

   ```bash
   .devforge/lib/research_helper set-recommended-approach \
       --name "Wrapper default-param for flag" \
       --rationale "<why>" \
       --hypotheses-addressed '["A"]' \
       --hypotheses-not-covered '[]' \
       --single-layer-justification "<prose>" \
       --cites '["<token>"]' \
       --proposed-call-shape "loadData()"
   ```

   On argument duplication, the helper exits with code 2 and stderr `set-recommended-approach: --proposed-call-shape "<shape>" contains argument duplication ("<ident>" appears N times in the arg list). Same value passed multiple times in one call indicates the default-source belongs at a different layer (wrapper signature / state initialization / use-case default). Reconsider the fix layer and re-draft.` Recovery: escalate the default-source one layer up (wrapper signature, state-init factory, or use-case default), re-draft the approach so the call site no longer needs the duplicated arg, then re-call `set-recommended-approach` with a non-duplicating `--proposed-call-shape`. Parser failure (nested calls, unsupported syntax) is fail-soft: helper emits a stderr advisory `research_helper: set-recommended-approach: --proposed-call-shape "<shape>" could not be fully parsed (nested calls / unsupported syntax); argument-duplication check skipped, shape stored verbatim.` and proceeds to exit 0. Check 18 mirrors the duplication check at verify time (catches state-mutation bypass) — same recovery applies.

4. **Constitution constraints** — read `constitution.md` for rules that bear on the affected area + recommended approach. For each rule that constrains or enables the change:

   ```bash
   .devforge/lib/research_helper set-constitution-constraints \
       --rule "<rule reference, e.g. '§3.2 Error Handling'>" \
       --impact "<how it constrains or enables the approach>"
   ```

   **MANDATORY "Search before building" entry.** When Phase 2.4b found a canonical pattern, this section MUST include a `set-constitution-constraints` call with `--rule="Search before building"` (or the project's equivalent rule reference per `constitution.md`) and `--impact` containing the canonical pattern's `file:line` plus a one-line note that reuse beats reinvention. When no canonical was found, omit this entry — its absence is information.

5. **Complexity** (3 sub-fields in a single call):

   ```bash
   .devforge/lib/research_helper set-complexity \
       --codebase-changes <Low|Med|High> --codebase-notes "<estimated diff scope>" \
       --risk <Low|Med|High> --risk-notes "<what could regress>" \
       --verify-cost <Low|Med|High> --verify-notes "<probe + test effort>"
   ```

6. **Verdict** (mode-aware enum — helper rejects values outside the mode's allowed set):

   | Mode          | Allowed verdict values                                                                       |
   | ------------- | -------------------------------------------------------------------------------------------- |
   | `bug`         | `Root cause confirmed` / `Root cause hypothesis (needs repro)` / `Multiple plausible causes` |
   | `enhancement` | `Feasible` / `Feasible with caveats` / `Not Recommended`                                     |

   ```bash
   .devforge/lib/research_helper set-verdict --value "<verdict>"
   ```

7. **Next-step text** — only emits when verdict ∈ proceeding-set (`Root cause confirmed` / `Root cause hypothesis (needs repro)` for bug; `Feasible` / `Feasible with caveats` for enhancement). On other verdicts the call is a no-op and the rendered report omits the Next-Step section.

   ```bash
   .devforge/lib/research_helper set-next-step-text
   ```

### Verify

```bash
.devforge/lib/research_helper verify
```

Helper cross-checks: ≥2 hypotheses, recommended-approach name matches an approach, recommended-approach respects `unchanged_behavior`, verdict ∈ mode-allowed-set, structured root-cause fields populated when bug-mode + confidence ∈ {`Confirmed`, `Hypothesis`}, verify-step's 3 sub-fields populated when any hypothesis needs a runtime probe, all required sections populated. Check 8b (cross-layer rule) rejects a bug-mode report where the primary symptom's `file:line` resolves to a presentation-layer path AND every `fix_path_helpers[].file_line` is in the same package as the symptom — at least one helper must trace through a package boundary; see Phase 2.4c Stopping rule. Check 12a (unconditional) rejects a report whose `runner_up_framing` is unset — Phase 2.3b must execute before `verify`. Check 12b (conditional on `runner_up_framing` set) rejects a report where no finding row carries `framing == "runner-up"` — at least one finding (positive or negative — disproving the runner-up via its falsifier is a valid outcome) must be tagged `--framing runner-up` for the runner-up to be considered probed. Check 13 (single-layer recommendation gate) rejects a bug-mode report where all `fix_path_helpers[].file_line` resolve to one package AND `recommended_approach.single_layer_justification` / `cites` are missing or empty — supply both via `set-recommended-approach --single-layer-justification ... --cites '[...]'` (see Phase 3 step 3). Check 13 is suppressed when check 8b applies (presentation-layer symptom + same-package helpers); in that case the single-layer escape path cannot satisfy verify and the only recovery is adding a cross-layer helper. Check 14 (fix-path-helper anchor gate) rejects a bug-mode report where any `fix_path_helpers[]` entry's `file_line` does not anchor to a recorded finding (exact match OR same path within ±5 lines) — see Phase 2.4c Step 1 anchor gate. Check 17 (literal-archaeology gate) rejects a bug-mode report whose `recommended_approach.rationale` OR the linked approach's `description` contains literal-replacement prose (`replace <X> with <Y>` / `change <X> to <Y>` / `<X> -> <Y>` / `swap the literal <X> with <Y>`) where `<X>` is a recognizable primitive literal AND no `literal_archaeology` row exists for `<X>` at a `findings[].file_line` — recovery: run Phase 2.5b archaeology + `record-literal-archaeology`, then re-run `verify`. Check 18 (argument-duplication shape check) rejects a bug-mode report whose `recommended_approach.proposed_call_shape` contains the same identifier (bare / dotted / optional-chained) more than once in its arg list — argument duplication signals the default-source belongs at a different layer; recovery: escalate the default-source upstream (wrapper signature / state initialization / use-case default) and re-call `set-recommended-approach` with a non-duplicating `--proposed-call-shape`. Shapes that could not be parsed (nested calls, unsupported syntax) are treated as non-duplicating — same fail-soft rule as the setter gate. Exit 0 → pass; non-zero → at least one violation enumerated on stderr.

On non-zero exit: copy stderr VERBATIM, identify the missing or invalid setter from the cited violation, fix it by re-calling the relevant setter, and re-run `verify`. Cap at 3 fix iterations. On the 4th failure, surface to the user and end the turn — the user re-runs `/research` from scratch (all prior state will be overwritten).

### Hypothesis-suppression gate

After `verify` exits 0, run the dedicated hypothesis-suppression gate (this is a separate verb from `verify`, not one of its 18 checks):

```bash
.devforge/lib/research_helper verify-hypothesis-suppression
```

The gate defends the Phase 0.4 / Step 5 separation at finalize time: an UNVERIFIED suspected-cause hypothesis must not also reappear as design direction. Mechanically, the helper token-overlaps each unverified hypothesis's `--cause` text against `recommended_approach.rationale` (the text that becomes `plan_seeds.recommended_approach_summary` in the handoff) and exits 2 on any shared identifier/vocabulary token. A hypothesis is exempt from the gate ONLY when it is CONFIRMED, and confirmation requires BOTH conditions together: the session/probe grade is HIGH (tier 1 / 1.5 — not MEDIUM/LOW and not feasibility-discriminator-unresolved) AND the hypothesis is recorded as addressed in `recommended_approach.hypotheses_addressed` (matched by its label). Behaviorally: confirmed (HIGH-grade AND addressed) → exempt; anything else → gated. An unconfirmed hypothesis stays gated even in a HIGH-grade session — a runner-up that the session did not confirm but whose mechanism leaks into the rationale is still flagged, because HIGH grade alone is not confirmation without the addressed-label match. Exit 0 → clean (no recommended approach yet, or no unverified mechanism leaked); exit 1 → state unreadable; exit 2 → a leak was found.

**Scope of this check (do not over-trust it).** This is a MODERATE mechanical backstop: it catches a leaked mechanism when the recommended approach REUSES the cause's identifiers/vocabulary — the common case, since an approach summary usually names the API / symbol it changes. It does NOT catch pure semantic paraphrase: a recommended approach that encodes the same mechanism in entirely different words shares zero tokens and passes. Paraphrase leakage is caught by Step 5's echo-back human gate (plan 18 Step 5), not by this check.

On exit 2: copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). The recovery is exactly what the stderr names — move the mechanism into an open question via `record-gap` (record it against the `desired` dimension with a `"confirm <mechanism> before designing"` description), then remove the mechanism from the recommended approach by re-calling `set-recommended-approach` with a `--rationale` that no longer encodes the unverified cause. Re-run `verify-hypothesis-suppression` after the fix; cap at 3 iterations, then surface to the user and end the turn.

### Render

```bash
.devforge/lib/research_helper render
```

Helper walks the locked schema and emits the full research report markdown to stdout. The orchestrator does NOT compose this markdown; the helper owns the section order (Header → Metadata → Summary → Symptom → Codebase Findings (WHERE) → Root Cause Hypothesis (WHY) → optional Structured Root Cause → optional Runner-up framing → Hypothesis Enumeration → optional Recommended Verify Step → Approaches (HOW) → Constitution Constraints → Complexity Assessment → optional Value Semantics → optional Value Production Sites → optional Literal Archaeology → optional Open Uncertainties → optional Next Step), heading levels, and table shapes. The Runner-up framing section renders only when `runner_up_framing` is set (see Phase 2.3b). The Codebase Findings table includes a `Framing` column showing the per-finding tag (`primary` or `runner-up`).

Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). This is the user's first look at the rendered report.

The LLM does NOT edit the rendered report via Write or Edit at any point. The helper's `render` is the only writer; any post-render fix is applied by re-calling the relevant setter + `render` + `verify` in a new turn.

## Phase 4 — Save + recommend

### Ask to save

After echoing the rendered report, ask via AskUserQuestion `"Save this research to a file?"` with options `["save", "skip"]`.

End the turn. The user's reply opens the next turn.

### On save

Compute the filename from helper state: `research/<report.date>-<memo.topic_slug>.md` under `<install_root>`. Create the `research/` directory if it does not exist. If the target path already exists, append `-2`, `-3`, ... until a free name is found.

Write the rendered text captured in Phase 3 (the same bytes printed there) to the chosen path. Use the helper-rendered bytes verbatim — do not re-format or re-shape.

### Emit handoff.json (mandatory on save)

After the rendered `.md` is written:

1. Compute the handoff.json path: `research/<report.date>-<memo.topic_slug>/handoff.json` — nested inside a per-research subdirectory that sits alongside the flat `.md` file.
2. If the handoff path already exists (same-date, same-slug re-run), overwrite it — the prior artefact is stale for the same research session.
3. Create the per-research directory if it does not exist.
4. Invoke:

   ```bash
   .devforge/lib/research_helper finalize-handoff \
       --emit-handoff-json <computed path>
   ```

5. If the helper exits non-zero, tell the user `"Research .md saved at <abs md path> but handoff.json failed: <stderr>. Re-run finalize-handoff manually after fixing the missing state."` and end the turn.
6. If the helper exits 0, capture the stdout `wrote: <abs path>` for the closing message.

### WIP-commit the artifacts (mandatory on save)

After the rendered `.md` AND `handoff.json` are both written, `[WIP]`-commit them so the work is git-safe immediately. Compose `--paths` from the two paths you just wrote — the saved `.md` path (the same bytes-on-disk path from "On save", including any `-2`/`-3` suffix if the name collided) and the `handoff.json` path from the step above — and use the topic slug for the label:

```bash
.devforge/lib/artifact_helper commit-artifacts \
    --paths '["research/<saved-md-filename>.md", "research/<date>-<topic-slug>/handoff.json"]' \
    --label "research: <topic-slug>"
```

The helper stages those paths in the install repo and makes a `[WIP] research: <topic-slug>` commit; it is install-repo-only (never the source repo in wrapper mode). This call is UNCONDITIONAL — always run it once both files are written. It is FAIL-SOFT: a git staging or commit failure warns on stderr and exits 1 (non-fatal — the artifacts are already saved, so warn the user with the helper's stderr and continue to the closing message; do NOT abort the command or re-run the save); "nothing to commit" (paths already staged or absent) exits 0 silently as a benign no-op.

### On skip

The rendered report stays in the assistant message only. No file is written. `.devforge/research-state.json` and `.devforge/research-report.json` remain on disk until the next `/research` invocation overwrites them. No handoff.json fires on skip — re-run `/research` and save to produce both `.md` and handoff.json.

### Closing message

If a save happened AND the verdict is in the proceeding-set, the rendered report already contains a `## Next Step` section with a copy-pasteable `/specify "..."` block. Tell the user: `"/research is done. Open <path> to review. The 'Next Step' section at the bottom is a copy-pasteable block for a new /specify session — copy it manually when you're ready. Handoff schema artefact at <handoff path> — a future /specify Phase 0.4 will auto-discover and import it via `specify_helper import-handoff` (Step 6 of RESEARCH-HANDOFF-PLAN)."`

If a save happened AND the verdict is not in the proceeding-set, the report omits the Next-Step section. Tell the user: `"/research is done. Open <path> to review. The verdict was '<verdict>' — recommended next step is to address the cited uncertainties or follow the recommended verify probe before specifying a fix. Handoff artefact at <handoff path> records the research state for downstream tooling."`

If the user chose `skip`, tell the user: `"/research is done. The report is in the prior message; .devforge/research-state.json and .devforge/research-report.json hold the state but will be overwritten on the next /research invocation. No handoff.json was written — re-run /research and save to produce both .md and handoff.json."`
