---
name: pr-review
description: Personal-overlay PR review of a foreign-repo PR — fetch diff + ticket, run code-smell heuristics, compute blast radius via CBM, check scope drift, dispatch cavecrew-reviewer, render terse findings locally.
argument-hint: '<PR#>'
arguments: [pr_number]
disable-model-invocation: true
allowed-tools:
  - Bash(gh pr *)
  - Bash(gh issue *)
  - Bash(git rev-parse *)
  - Bash(git blame *)
  - Bash(git log *)
  - Bash(grep *)
  - Bash(.venv-test/bin/python *)
  - Bash(python *)
  - Bash(python3 *)
  - Read(.)
---

# /pr-review — Personal-Overlay PR Review

`/pr-review` is a private, reviewer-side command for inspecting a teammate's pull request against a foreign-repo codebase. The reviewer's forge install holds the overlay (`.devforge/` + `constitution.md` + concern docs + CBM index); the PR-authoring team is unaware of forge. Output stays in `.devforge/pr-reviews/<PR#>/` on the reviewer's machine — findings are NEVER posted to the PR automatically. The reviewer reads `findings.md`, then manually re-translates each finding into PR-comment-shaped language appropriate for the author's team.

State + render shape are owned by `.devforge/lib/pr_review_helper`; the orchestrator composes values via verb invocations and dispatches MCP / Task-tool work itself. The helper makes ZERO MCP calls and ZERO LLM calls — every CBM `trace_path`, every cavecrew dispatch, every state.findings append is the orchestrator's responsibility.

Usage: `/pr-review $pr_number` — e.g. `/pr-review 304`. The PR number is positional and required.

## Overview

The command orchestrates 11 helper verbs in fixed order, interleaving four LLM-side responsibilities:

1. Acting on `ensure-cbm-index`'s `mcp_tool_hint` to refresh the CBM graph when stale or absent.
2. Filling unfilled blast-radius probe specs via `mcp__codebase-memory-mcp__trace_path` after Phase 3.
3. Dispatching `cavecrew-reviewer` via the Task tool after Phase 6, parsing its findings, and appending them to `state.findings`. The orchestrator also fills `state.drift.coverage_matrix` + `state.drift.scope_creep_files` from cavecrew's scope-drift analysis at the same step.
4. Surfacing cost estimates + confidentiality reminders to the reviewer before any spend-heavy operation runs.

The four output artefacts (per PR) live under `.devforge/pr-reviews/<PR#>/`:

- `state.json` — canonical PRReviewState (intake → smells → blast → bundle → drift → findings). Owned by the helper; mutated only via verb invocations + the orchestrator's targeted `state.findings` / `state.drift.coverage_matrix` appends after dispatch.
- `brief.md` — fat reviewer brief assembled by `dispatch-review` (Phase 6); 10 canonical sections, ≤100 000 chars.
- `findings.md` — terse markdown report rendered by `finalize-output` (Phase 7); severity-sorted with a summary header (slop-score / blast-risk-score / drift-summary).
- `pr-review-bundle.json` — full state snapshot archived by `append-to-replay-corpus` (Phase 7.5) for regression replay; the corpus-wide index lives at `_corpus_index.json` in the same directory.

The LLM does NOT edit `state.json`, `brief.md`, `findings.md`, or `pr-review-bundle.json` via the Write tool. Helper verbs are the writers for everything except the post-dispatch `state.findings` + `state.drift` edits, which the orchestrator performs via direct JSON edits (documented in Phase 6.5).

## Arguments

- `$pr_number` — required, positional. The PR number on the foreign repo (e.g. `304`). The `--repo` flag passed to `intake` is derived from the reviewer's git remote (see Phase 1 — Intake); the slash command does not take a `--repo` argument.
- Ticket text — passed at Phase 1 via interactive prompt. Three sources, in order of preference:
  - User paste in chat (default — orchestrator captures the next user message as `ticket_text`).
  - User-supplied file path (orchestrator reads the file and passes `--ticket-file <path>` to `intake`).
  - Empty (proceed without ticket; scope-drift Phase 5 degrades to PR-body-only).

If `$pr_number` is empty or non-numeric, end the turn with `"/pr-review requires a PR number, e.g. /pr-review 304"`. Do not invoke any helper verb.

## Pre-conditions

Three preflight checks run in order. All must pass before Phase -1 begins.

### Pre-condition 1 — `gh` binary present

```bash
command -v gh >/dev/null
```

Non-zero → end the turn with: `"gh CLI not found. Install from https://cli.github.com/ then re-run /pr-review."` No further phases run.

### Pre-condition 2 — `gh` authenticated

```bash
gh auth status >/dev/null 2>&1
```

Non-zero → end the turn with: `"gh is not authenticated. Run gh auth login then re-run /pr-review."` No further phases run.

### Pre-condition 3 — CBM MCP availability check (warn-only)

If `mcp__codebase-memory-mcp__*` tools are not loaded in this session, surface to the reviewer as plain prose: `"CBM MCP not available in this session — Phase 3 blast-radius probe specs will be emitted but not filled. Run /pr-review again with CBM loaded for full blast-radius analysis, OR proceed with helper-only output."` Then continue — CBM unavailability is not a hard stop; the helper-side probe specs are still useful for the reviewer.

After all three preflight checks, surface the confidentiality reminder (see `## Confidentiality`) to the reviewer as plain prose. Then proceed to Phase -1.

## Workflow

### Phase -1 — CBM index ensure

```bash
.devforge/lib/pr_review_helper ensure-cbm-index --target .
```

Helper invokes `cbm_sync_helper check` and emits a structured JSON dict on stdout. Capture the JSON; do not pipe through summarization. The dict carries six keys: `status, next_action, mcp_tool_hint, cost_estimate_usd (null except on absent), cbm_state_token, target_path`. The `status` field is one of `ok` / `stale` / `absent` / `not-a-git-repo`. The `next_action` field is one of `none` / `run-detect-changes` / `run-index-repository` / `setup-cbm`. The `mcp_tool_hint` field is the literal MCP tool name to dispatch (or null when no MCP op makes sense).

Branch on `status`:

- **`ok`** → continue to Phase 0.
- **`stale`** → surface the helper's JSON to the reviewer verbatim as a fenced code block, then dispatch `mcp__codebase-memory-mcp__detect_changes` per the `mcp_tool_hint`. After the MCP call returns, run `.devforge/lib/cbm_sync_helper write` to refresh the stamp. Continue to Phase 0.
- **`absent`** → surface the helper's JSON to the reviewer verbatim as a fenced code block. The dict carries `cost_estimate_usd` (rule-of-thumb $1 per 1000 source files, capped at 10 000 files). Quote that estimate to the reviewer as plain prose alongside the JSON, then ask via AskUserQuestion: `"CBM index missing; estimated indexing cost ~$<value> USD. Run index_repository?"`with options`["index", "skip"]`. Single-line question text. End the turn. The reviewer's reply opens the next turn. On `index`: dispatch `mcp**codebase-memory-mcp**index_repository`per the`mcp_tool_hint`, then run `.devforge/lib/cbm_sync_helper write`. Continue to Phase 0. On `skip`: continue to Phase 0; Phase 3.5 blast-radius fill will skip (no graph to query).
- **`not-a-git-repo`** → surface the helper's JSON to the reviewer verbatim as a fenced code block. End the turn with: `"Target is not a git repository. /pr-review requires a git working tree."` No further phases run.

### Phase 0 — Forge-state tier detection

```bash
.devforge/lib/pr_review_helper detect-forge-state --target .
```

Helper performs a pure-filesystem scan and emits JSON with `tier` (one of `full` / `partial` / `none`) + `manifest` (paths to `constitute_json`, `constitution_md`, `concern_doc_dirs`, `adr_dir`). Capture the JSON. Surface the `tier` value to the reviewer as plain prose:

- **`full`** → "Forge tier: full (constitute.json + constitution.md + concern docs). Phase 4 bundle will include every overlay source."
- **`partial`** → "Forge tier: partial (at least one of constitute.json or constitution.md present, but not the full set). Phase 4 bundle will include what exists."
- **`none`** → "Forge tier: none (no forge overlay detected on this target). Phase 4 bundle will be constitution-less; reviewer dispatch falls back to PR-only context."

Continue to Phase 1 regardless of tier — `none` is not a hard stop, just a signal that the brief will be thinner.

### Phase 1 — Intake (PR data + ticket text)

Derive the `--repo` argument from the reviewer's git remote:

```bash
gh repo view --json owner,name --jq '.owner.login + "/" + .name'
```

Capture the `owner/name` string. If this command fails, end the turn with: `"Cannot derive repo from gh — ensure you're inside a git checkout with a GitHub remote."` No further phases run.

Resolve ticket text via AskUserQuestion: `"Ticket text source for PR $pr_number?"` with options `["paste-now", "from-file", "skip"]`. Single-line question text. End the turn. The reviewer's reply opens the next turn.

- **`paste-now`** → in the next turn, prompt as plain prose: `"Paste the ticket body (Linear / Jira / GitHub issue text). End with an empty line."` The reviewer's reply is the ticket text. Pass it via `--ticket-text "<content>"`.
- **`from-file`** → in the next turn, prompt as plain prose: `"Enter the absolute path to the ticket file."` The reviewer's reply is the path. Pass it via `--ticket-file <path>`.
- **`skip`** → no `--ticket-text` / `--ticket-file` flag. Phase 5 scope-drift will degrade to PR-body-only.

Invoke intake:

```bash
.devforge/lib/pr_review_helper intake --pr $pr_number --repo <owner>/<repo> [--ticket-text "..." | --ticket-file <path>] --target .
```

Helper invokes `gh pr view --json` + `gh pr diff`, builds the initial `PRReviewState`, writes it atomically to `.devforge/pr-reviews/$pr_number/state.json`, and emits a summary JSON dict with keys `status`, `state_path`, `pr_number`, `repo`, `files_changed`, `additions`, `deletions`, `title`, `ticket_text_length`. Surface the summary JSON to the reviewer verbatim as a fenced code block.

On non-zero exit, copy stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase). End the turn. The reviewer fixes the upstream cause (auth, PR number, network) and re-invokes `/pr-review`.

### Phase 2 — Code-smell + slop heuristics

```bash
.devforge/lib/pr_review_helper detect-smells --pr $pr_number --target .
```

Helper runs the full 8-heuristic catalog over `state.diff` + `state.commit_subjects` + (for advanced heuristics) the target filesystem. The 8 heuristics are: `empty_pr_body`, `atomic_dump`, `hedge_defensive`, `verbose_commit_msg`, `duplication_ratio`, `literal_archaeology_adapter`, `argument_duplication`, `hallucinated_api`. Each heuristic emits zero or more findings; the helper appends them to `state.smells` and writes state back atomically. Stdout is a summary JSON with keys `status`, `state_path`, `smells_count`, `by_severity` (`high` / `medium` / `low` / `nit` buckets).

Surface the summary JSON to the reviewer verbatim as a fenced code block. On non-zero exit, copy stderr VERBATIM and end the turn.

### Phase 3 — Compute blast-radius probe specs

```bash
.devforge/lib/pr_review_helper compute-blast-radius --pr $pr_number --target .
```

Helper parses the diff and identifies changed symbols per language (Python `def`/`class`/`async def`; TS/JS `function`/`class`/`interface`/`type`/typed-or-untyped `const = fn`; Vue implicit component from basename + script-block scan; Go `func`/`type ... struct/interface`; Java method/class; Ruby `def`/`class`; Rust `fn`/`struct`/`enum`/`trait`). For each unique `(symbol, file)`, the helper emits a probe-spec entry with `filled=false`. The probe-spec list is capped at 100 entries. Re-running this verb REPLACES `state.blast` wholesale (not append).

Stdout is a summary JSON with keys `status`, `state_path`, `pr_number`, `symbols_extracted`, `by_language`, `by_kind`, `next_action`, `capped`. Surface the summary JSON to the reviewer verbatim as a fenced code block.

### Phase 3.5 — Fill blast-radius probe specs (LLM-side)

This phase runs ONLY when Phase -1's `status` was `ok` or `stale` AND the reviewer chose `index` at the `absent` branch. When CBM is unavailable, skip this phase entirely — `state.blast` carries unfilled probe specs into the brief, and the reviewer-side cavecrew dispatch handles them with reduced context.

Read `state.json` from `.devforge/pr-reviews/$pr_number/state.json`. For each entry in `state.blast` where `filled == false`:

- Read the entry's `mcp_hints` — the helper packs the symbol name + file path + language into this field.
- Dispatch `mcp__codebase-memory-mcp__trace_path` with `mode: "calls"` to populate `callers`.
- Dispatch `mcp__codebase-memory-mcp__trace_path` with `mode: "data_flow"` to populate `data_flow_targets`.
- When `search_graph` returns 0 hits for the symbol, fall through to `mcp__codebase-memory-mcp__search_code` with a literal-token regex over the affected package (per `feedback_cbm_discovery_chain_search_graph_then_code`). Catch inline reactive blocks (Vue `<script setup>`, React hooks, Svelte) that the graph indexer does not promote to named symbols.
- Heuristically locate tests that reference the symbol via `mcp__codebase-memory-mcp__search_code` with the symbol name as the literal token, scoped to test-pattern files (`**/*test*`, `**/*spec*`); populate `tests_referencing`.
- Set the entry's `filled` field to `true`.

After all entries are processed, write `state.json` back. The orchestrator performs this write via the Edit tool because no helper verb owns the per-entry blast fill — the canonical entry shape is locked by Phase 3's helper output, and Phase 3.5 fills declared fields only (no new keys). Do not introduce keys the helper did not declare.

Skipped-phase note: if Phase 3.5 is skipped (CBM unavailable), surface to the reviewer as plain prose: `"Phase 3.5 skipped: CBM unavailable. <N> blast-radius probe specs left unfilled; cavecrew brief will carry them as TODO entries."`

### Phase 4 — Bundle context (filesystem aggregation)

```bash
.devforge/lib/pr_review_helper bundle-context --pr $pr_number --target .
```

Helper aggregates the universal `src/constitution.md`, the per-target `.devforge/constitute.json`, concern overview/architecture docs for concerns touched by the diff, all ADRs under the detected ADR directory, and all repo-root `*-PLAN.md` files. Output is written to `state.bundle` (sub-keys `constitution_md`, `constitute_json`, `concern_docs`, `adrs`, `plan_files`). Stdout is a summary JSON with per-source gathered counts.

Surface the summary JSON to the reviewer verbatim as a fenced code block. On non-zero exit, copy stderr VERBATIM and end the turn.

### Phase 4.5 — Import research handoffs (filtered)

```bash
.devforge/lib/pr_review_helper import-handoffs --pr $pr_number --target .
```

Helper scans `<target>/research/**/handoff.json` for handoffs whose ticket-area tokens overlap with `state.ticket_text` + PR title. Matching handoffs are appended to `state.bundle.research_handoffs`. Stdout is a summary JSON with `matched` + `scanned` counts.

Surface the summary JSON to the reviewer verbatim as a fenced code block. Zero matches is not a failure — many PRs have no prior research; the field is left empty and Phase 6's brief carries no handoff section content.

### Phase 5 — Check scope drift (extract ticket bullets)

```bash
.devforge/lib/pr_review_helper check-scope-drift --pr $pr_number --target .
```

Helper applies 5 regex strategies in priority order to `state.ticket_text` (primary) + `state.pr_body` (secondary): `markdown_bullet` → `numbered_list` → `ac_marker` → `gwt` (Given/When/Then) → `sentence_fallback`. Extracted bullets are deduped (lowercased + stripped) and capped at 50. Output is written to `state.drift` with sub-keys `bullets`, `coverage_matrix=[]`, `scope_creep_files=[]`, `filled=false`. The empty `coverage_matrix` + `scope_creep_files` are LLM-fill targets at Phase 6.5; the helper does not populate them.

Stdout is a summary JSON with `bullets_extracted`, `by_source`, `by_extracted_via`, `capped`, `next_action`. Surface the summary JSON to the reviewer verbatim as a fenced code block.

When zero bullets are extracted (empty ticket + empty PR body), surface to the reviewer as plain prose: `"Phase 5 extracted 0 bullets. Scope-drift findings will be empty; cavecrew brief will note ticket-absence as the cause."` Continue to Phase 6.

### Phase 6 — Dispatch review (assemble brief)

```bash
.devforge/lib/pr_review_helper dispatch-review --pr $pr_number --target .
```

Helper assembles the 10-section FAT reviewer brief and writes it atomically to `.devforge/pr-reviews/$pr_number/brief.md`. The 10 canonical sections in order: metadata, ticket text, linked issues, diff (mid-excerpt strategy when over 80 000-char cap), code-smell findings (from Phase 2), blast-radius probe specs (from Phase 3 + 3.5 fill), scope-drift bullets (from Phase 5), context bundle (constitution + constitute.json + concern docs + ADRs + plan files + research handoffs from Phase 4 + 4.5), reviewer instructions, notes.

Stdout is a summary JSON with keys `brief_path`, `brief_size_chars`, `sections_included`, plus per-section counts. Surface the summary JSON to the reviewer verbatim as a fenced code block. Brief size must be under 100 000 chars; per-section caps inside the helper enforce this.

### Phase 6.5 — Dispatch cavecrew-reviewer + append findings (LLM-side)

Read `brief.md` from `.devforge/pr-reviews/$pr_number/brief.md` in full. Then dispatch `cavecrew-reviewer` via the Task tool with the brief contents as the agent's prompt. Brief framing (encoded in the brief's `Reviewer instructions` section by `dispatch-review`): the PR author is unaware of forge standards; flag slop + drift + blast; cite source per finding (constitution / overlay / plan / ADR / smells-heuristic / blast-data); skip nits unless meaning-changing.

After cavecrew returns, parse its findings. Each finding has the schema `{severity, location, category, evidence, fix_hint, source_heuristic}` — declared in the brief's `Reviewer instructions` section and locked by the helper's `_dispatch.py`. The orchestrator's job is to:

1. Read `.devforge/pr-reviews/$pr_number/state.json`.
2. Append every cavecrew finding to `state.findings`. Note: Phase 2's heuristic findings live in `state.smells` (separate field); `state.findings` is populated exclusively by cavecrew at this phase.
3. Populate `state.drift.coverage_matrix` from cavecrew's per-bullet coverage assessment. Each entry: `{bullet_id, status (satisfied / partial / missing / unknown), evidence}`. The helper declared the shape; do not introduce new keys.
4. Populate `state.drift.scope_creep_files` — a list of file paths cavecrew identified as out-of-scope for the ticket.
5. Set `state.drift.filled = true`.
6. Write `state.json` back via the Edit tool.

Defensive default for `confidence` field: when cavecrew omits or returns `null` for a finding's `confidence` field, treat it as `0.0` (the helper's `_dispatch.py` uses `entry.get("confidence") or 0.0` for the same reason). Do not invent confidence values.

When cavecrew dispatch fails or returns zero findings, surface to the reviewer as plain prose: `"Cavecrew returned <N> findings. Proceeding to finalize-output with helper-side smells only."` State.findings retains its Phase 2 smells; state.drift.filled stays `false` (handled by the renderer in Phase 7).

### Phase 7 — Render findings.md

```bash
.devforge/lib/pr_review_helper finalize-output --pr $pr_number --target .
```

Helper reads `state.findings`, sorts by severity (`high` → `medium` → `low` → `nit`) then by location, computes the aggregate scores (slop-score capped at 100 via `_SLOP_WEIGHTS`, blast-risk-score computed as `min(len(state.blast) * 3, 60) + (max_inbound_callers_across_filled_probes * 2)`, capped at 100), and writes a markdown report atomically to `.devforge/pr-reviews/$pr_number/findings.md`. The report opens with a summary header (PR#, repo, PR title, generated timestamp, findings totals by severity + category, aggregate scores) followed by H3 finding blocks.

Stdout is a summary JSON with `status`, `findings_path`, `findings_total`, `by_severity`, `by_category`, `slop_score`, `blast_risk_score`, `drift_summary`. Surface the summary JSON to the reviewer verbatim as a fenced code block.

Then surface the rendered `findings.md` path to the reviewer as plain prose: `"Findings rendered to .devforge/pr-reviews/$pr_number/findings.md — review the file, then manually translate each finding into a PR comment in the author's team's preferred tone."`

### Phase 7.5 — Append to replay corpus

```bash
.devforge/lib/pr_review_helper append-to-replay-corpus --pr $pr_number --target .
```

Helper writes the full state snapshot atomically to `.devforge/pr-reviews/$pr_number/pr-review-bundle.json` and upserts the corpus-wide index at `.devforge/pr-reviews/_corpus_index.json` (schema_version `"1"`). Re-running this verb increments `review_count` and updates `last_reviewed_at`; `first_reviewed_at` is preserved.

Stdout is a summary JSON with `status`, `bundle_path`, `corpus_index_path`, `entry_action`, `review_count`, `findings_count`. Surface the summary JSON to the reviewer verbatim as a fenced code block.

End the turn with: `"/pr-review complete for PR $pr_number. Read findings.md, translate to PR comments, then move on."`

## Verify

Observable success criteria (the reviewer can check each in the order below):

- `.devforge/pr-reviews/$pr_number/state.json` exists. `jq '.findings | length' state.json` returns a non-negative integer; `jq '.smells | length' state.json` matches Phase 2's `smells_count`; `jq '.blast | length' state.json` matches Phase 3's `symbols_extracted`.
- `.devforge/pr-reviews/$pr_number/brief.md` exists and is non-empty. Its character count is ≤100 000 (cap enforced by `_dispatch.py`).
- `.devforge/pr-reviews/$pr_number/findings.md` exists and contains a `# PR Review Findings — PR #$pr_number` header.
- `.devforge/pr-reviews/$pr_number/pr-review-bundle.json` exists.
- `.devforge/pr-reviews/_corpus_index.json` contains an entry in its `entries` array where `pr_number == $pr_number` (verify via `jq '.entries[] | select(.pr_number == $pr_number)' _corpus_index.json`).
- Every helper verb invoked above exited 0. The orchestrator's `state.findings` + `state.drift` appends after Phase 6.5 left `state.json` parseable as JSON (verify via `jq '.' state.json >/dev/null`).
- Phase 3.5 either filled every blast probe (when CBM was available) or was skipped with the explicit reviewer-facing notice.

## Output

The reviewer's primary read target is `findings.md`. The full artefact set, with consumer:

| Artefact        | Path                                                    | Consumer                                                           |
| --------------- | ------------------------------------------------------- | ------------------------------------------------------------------ |
| Findings report | `.devforge/pr-reviews/$pr_number/findings.md`           | Reviewer reads + manually translates to PR comments                |
| Reviewer brief  | `.devforge/pr-reviews/$pr_number/brief.md`              | Cavecrew agent during Phase 6.5; reviewer may read for debugging   |
| Canonical state | `.devforge/pr-reviews/$pr_number/state.json`            | Helper verbs across phases; reviewer may inspect with `jq`         |
| Replay bundle   | `.devforge/pr-reviews/$pr_number/pr-review-bundle.json` | Regression-test replay corpus; future heuristic-catalog validation |
| Corpus index    | `.devforge/pr-reviews/_corpus_index.json`               | Reviewer cross-PR lookup; corpus-replay tooling                    |

Findings are NEVER posted to the PR automatically. The reviewer translates each finding into team-appropriate PR-comment language manually — this is the explicit design contract and the reason `/pr-review` is private-overlay rather than team-shared.

## Confidentiality

Diff text, PR body, ticket text, and linked-issue references are sent to Claude via MCP for `cavecrew-reviewer` dispatch and (during Phase 3.5) to the CBM index. This means the foreign-repo source code present in the diff transits Claude's inference path. **Verify NDA / employer policy / client approval before running `/pr-review` against any repository whose source you do not have explicit permission to share with a third-party LLM service.**

All output artefacts under `.devforge/pr-reviews/` stay on the reviewer's local machine. By default, the install script adds `.devforge/` to the target repo's `.gitignore` — verify the gitignore entry is present before running `/pr-review`. If `.devforge/` is committed (which would be a misconfiguration), every PR review you run leaks the diff + ticket + findings into the foreign repo's git history.

This reminder is surfaced to the reviewer as plain prose after the three pre-condition checks pass. The reviewer's continuation past that prompt is treated as confirmation; no AskUserQuestion gate is enforced (one-time prose reminder is sufficient for a private-overlay workflow).

## Cost

Per-invocation cost estimate (rough Haiku pricing — actual cost varies with diff size, brief size, and CBM index scale):

| Operation                                              | Cost range | When it fires                                                                            |
| ------------------------------------------------------ | ---------- | ---------------------------------------------------------------------------------------- |
| `cavecrew-reviewer` dispatch (Phase 6.5)               | $0.10–0.50 | Every run                                                                                |
| CBM `index_repository` (Phase -1, `absent` branch)     | $0.10–1.00 | First run against a new repo only; helper surfaces a per-target estimate before dispatch |
| CBM `detect_changes` (Phase -1, `stale` branch)        | <$0.01     | When the local stamp is behind the working tree                                          |
| CBM `trace_path` per blast probe (Phase 3.5)           | ~$0.001    | 100 probes ≈ $0.10                                                                       |
| Helper verbs (Phases -1 through 7.5, helper-side only) | $0         | Every run — helpers are pure-Python + filesystem                                         |

**Total typical cost: $0.50–2.00 per medium-sized PR review.** Phase -1's `absent` branch surfaces the per-target indexing cost estimate to the reviewer as plain prose before any spend; the reviewer can opt out via the `skip` branch.

## Storage

All per-PR artefacts live under `.devforge/pr-reviews/$pr_number/`:

```
.devforge/pr-reviews/
├── _corpus_index.json        # corpus-wide index (one entry per reviewed PR)
└── <PR#>/
    ├── state.json            # canonical PRReviewState
    ├── brief.md              # FAT reviewer brief (Phase 6 output)
    ├── findings.md           # rendered findings report (Phase 7 output)
    └── pr-review-bundle.json # full state snapshot (Phase 7.5 archive)
```

`.devforge/` is gitignored by default (install-script-enforced). Per-PR directories are NEVER deleted automatically — the reviewer manages retention by hand. Re-running `/pr-review` on the same PR overwrites `state.json` / `brief.md` / `findings.md` / `pr-review-bundle.json` for that PR and increments the corpus index's `review_count` field.

## IMPORTANT RULES

1. **Findings stay private.** `/pr-review` never posts to the PR. The reviewer translates findings to PR comments manually, in the author's team's preferred tone.
2. **Helper-owned shape.** State + brief + findings + bundle structure is locked by `pr_review_helper`. The orchestrator's only direct JSON edits are Phase 3.5's blast-probe fill and Phase 6.5's `state.findings` + `state.drift` append — both fill helper-declared fields only.
3. **No MCP from helpers.** Every CBM `trace_path` / `search_graph` / `search_code` / `index_repository` / `detect_changes` call is dispatched by the orchestrator, not by helper code. The helper-side surface is pure filesystem + subprocess (`gh`, `cbm_sync_helper`).
4. **CBM unavailable is degrade-not-stop.** When MCP tools are not loaded, Phase 3.5 is skipped, blast probe specs travel to cavecrew unfilled, and the reviewer is told explicitly. Phases -1 through 7.5 still run.
5. **Confidentiality is the reviewer's responsibility.** The pre-Phase-(-1) reminder is informational. No automated check enforces NDA / approval status — the reviewer's continuation past the reminder is treated as confirmation.
6. **Phase 6.5 finding-schema fields are locked.** `{severity, location, category, evidence, fix_hint, source_heuristic}` is the canonical shape. When cavecrew omits `confidence`, default to `0.0` (matches the helper's defensive default). Do not invent fields.
7. **Re-running is idempotent on the PR.** Re-invoking `/pr-review` on the same PR overwrites the per-PR artefacts and increments the corpus index's `review_count`; the corpus index's `first_reviewed_at` is preserved.
