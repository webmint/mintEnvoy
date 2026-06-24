---
name: grill
description: Standalone adversarial design-grill — the design-level mirror of `/review`. Runs by invocation between `/plan` and `/breakdown` to attack the FINISHED design (`plan.md` + its `spec.md`) before `/breakdown` spends effort decomposing it. Dispatches the `devils-advocate` adversary (which resolves a three-ring codebase blast radius and self-gated web-verification), cross-examines every attack with a non-author refutation pass (architect excluded), writes `specs/[feature]/grill.md`, and recommends a 4-way disposition (PROCEED / REVISE-PLAN / RE-ENTER-UPSTREAM / KILL). Opt-in — never an auto-gate.
argument-hint: "[plan-file-or-feature]"
disable-model-invocation: true
---

# /grill — Adversarial Design Grill

`/grill` is a standalone, opt-in pipeline stage positioned BETWEEN `/plan` and `/breakdown`. It is the design-level mirror of `/review`: `/plan` builds the design, and `/grill` attacks the FINISHED design (`plan.md` and the `spec.md` it implements) before `/breakdown` spends effort decomposing it and `/implement` writes the code — while killing a fatally-flawed design is still cheap. It dispatches the `devils-advocate` adversary in ADVERSARIAL DESIGN-GRILL MODE, validates every attack against the actual artifacts to discard ungrounded ones, cross-examines the survivors with a refutation pass (default-dismiss unless the defect is demonstrable from quoted evidence), writes a findings report to `specs/[feature]/grill.md`, and recommends a 4-way disposition. Read-only on source — it never modifies source, never modifies the plan or spec; it WIP-commits only its OWN artifacts (the report + seed + state) in an install-repo-only, fail-soft `[WIP]` commit that folds into `/finalize`'s squash. State + render shape are owned by `.devforge/lib/grill_helper`; the orchestrator composes values via verb subcommands.

The genuine gap it fills: `/plan` *compares* 2–3 alternatives and the architect picks a winner, but nobody ever attacks the winner — comparison is optimization, not refutation. By charter the architect is an OPTIMIZER / decision authority ("decide HOW", "own the final architectural call"), not an adversary chartered to attack the design it chose. So the chosen design is never adversarially attacked anywhere in the pipeline. `/grill` is the only place it is.

**`/grill` produces FINDINGS PLUS a recommended DISPOSITION — but the disposition is a RECOMMENDATION, not a binding verdict.** The human owns the final call at the existing `/breakdown` approval gate. Unlike `/review` (pure findings-only, because `/verify` owns its verdict downstream), `/grill` carries a light disposition because there is no downstream design-`/verify` to own it. The four dispositions are PROCEED / REVISE-PLAN / RE-ENTER-UPSTREAM / KILL.

**Opt-in by construction — never an auto-gate.** `/grill` runs because the USER invoked it (like `/audit`). There is NO deterministic stakes-detector, NO forced gate on every `/plan` run, and NO place to "harden" it into an always-on check. It is RECOMMENDED for high-stakes plans (new architecture / new dependency / new external integration / new data model / security-relevant) and SKIPPED for mechanical ones — the human decides by choosing to invoke it. Skipping `/grill` leaves the `/plan → /breakdown` chain byte-unchanged.

Usage: `/grill` (auto-resolve the lowest-numbered feature under `specs/` that has a `plan.md`) · `/grill specs/001-auth` or `/grill specs/001-auth/plan.md` (an explicit feature dir or a `plan.md` path inside it).

## Maintainer note

This file lives at `src/commands/grill/main.md` in the AIDevTeamForge template repo and is the SSOT for the `/grill` command. Do NOT inject project-specifics — this spec is substituted + emitted into target projects by the build. Helper paths use the installed `.devforge/lib/...` location because that's where they resolve at runtime in the target project. Reference-file paths are written author-relative (`references/<file>.md`); the emitter rewrites them to `.claude/commands/grill/references/<file>.md` at install time.

## Outputs of this command

The files this command writes under the repo are:

- `specs/[feature]/grill.md` — the rendered design-grill report. Produced by the helper's `render-report` verb in PHASE 6; carries the surviving findings AND the recommended 4-way disposition. Idempotent: re-running `/grill` on the same feature OVERWRITES `grill.md` (the helper does an atomic write).
- `specs/[feature]/grill-seed.json` — written in PHASE 7 when the user chooses the matching re-entry at the human gate — `Revise plan` on a REVISE-PLAN recommendation (`target_stage=plan`, for `/plan`), or `Re-enter upstream` on a RE-ENTER-UPSTREAM recommendation (an upstream stage `spec` / `discovery` / `research`, for `/specify` / `/discover` / `/research`). Produced by the helper's `write-seed` verb; the structured BACKWARD handoff the named re-entry command consumes on re-entry so the re-run is directed, not a repeat. Not written for Proceed, Kill, or a cross-pick (the user picking a re-entry that does not match the recommendation).

Per-feature run state lives in `specs/[feature]/grill-state.json` (helper-owned, advanced via `check-status-and-flip --feature-dir <feature>`).

At the end of PHASE 6, `/grill` WIP-commits its own report artifacts — `grill.md` and the per-feature `grill-state.json` — via `.devforge/lib/artifact_helper commit-artifacts`. When the user authorizes a matching re-entry at the PHASE-7 human gate, the `grill-seed.json` written there is WIP-committed in that same matching arm. Each commit lands in the INSTALL repo only (never the wrapper-mode source/product repo) and is fail-soft (a git failure warns and `/grill` continues — the report is already written). The `[WIP]` commit folds into `/finalize`'s squash, so the final PR is unchanged.

### Intermediate scratch files (orchestrator-written, helper-consumed) — all under `$WORKDIR`

The helper cannot dispatch agents or call the codebase-memory-mcp (CBM) graph (a subprocess has no Task/MCP tools), so the orchestrator captures each verb's stdout to an intermediate scratch file that the next verb reads (most verbs take a `--<name> <path>` flag, not stdin). All live under `$WORKDIR` (`${TMPDIR:-/tmp}/forge-grill`) and are scratch state for one run — the whole directory is removed at the end (the single PHASE-7 `rm -rf "$WORKDIR"`). Because `$WORKDIR` is outside the work tree, the files need no leading dot and no gitignore handling. Several verbs print a DICT (e.g. `consume-tmp`'s `{status, findings}`) but the next verb's `--findings` requires a BARE ARRAY — those steps include a one-line `python3 -c` extraction (shown inline at each phase).

- `$WORKDIR/preflight.json` — the `preflight` stdout (`source_root`, `framework`, `language`, `wrapper_mode`, `feature_gate_ok`, …). Written in PHASE 0, read by the orchestrator for the `--source-root` / `--framework` values it threads into later verbs.
- `$WORKDIR/manifest.json` — the `resolve-scope` stdout (the static `GrillScopeManifest`: `feature_dir`, `feature_id`, `plan_path`, `spec_path`, `handoff_path`, `constitution_path`, `claude_md_path`). Written in PHASE 1, read by `render-brief --manifest`.
- `$WORKDIR/scope-block.txt` — the human-readable scope block the orchestrator extracts from the manifest for the refuter briefs. Written in PHASE 1, passed to every `render-verify-brief --scope-block` (that verb takes a pre-rendered scope-block FILE, not the manifest JSON).
- `$WORKDIR/tmp-devils-advocate.md` — the adversary's findings, written by the dispatched `devils-advocate` agent in PHASE 2 (the brief's `--tmp-path` names this exact path), consumed by `consume-tmp` in PHASE 3. Swept by the end-of-run `rm -rf "$WORKDIR"`.
- `$WORKDIR/parsed-devils-advocate.json` — `consume-tmp` stdout (a DICT: `status` + `findings` array). Written + read in PHASE 3.
- `$WORKDIR/findings-devils-advocate.json` — the bare `findings` array extracted from `parsed-devils-advocate.json`. Written in PHASE 3, read by `validate-findings --findings`.
- `$WORKDIR/validated-devils-advocate.json` — `validate-findings` stdout (`passed` + `discarded` + `discard_counts`). Written + read in PHASE 3.
- `$WORKDIR/validated.json` — the adversary's validated `passed` findings as ONE bare array. Written in PHASE 3, read by `route-refutation --findings` and `apply-verdicts --findings`.
- `$WORKDIR/refutation-routes.json` — `route-refutation` stdout (a list of `{refuter, findings}` cross-examination groups assigning each finding a non-author refuter). Written in PHASE 4, read by the orchestrator to drive the per-group `render-verify-brief` + refuter-dispatch loop.
- `$WORKDIR/refute-<refuter>.json` — one refuter group's bare-array `findings` subset, extracted by the orchestrator from `refutation-routes.json`. Written + read per refuter in PHASE 4, passed to `render-verify-brief --findings`.
- `$WORKDIR/verdicts-<refuter>.md` — per-refuter raw markdown verdicts, written by each dispatched refuter in PHASE 4 (the `render-verify-brief` `--tmp-path` names this exact path), consumed by `consume-verdicts --verdicts` in the same phase. Swept by the end-of-run `rm -rf "$WORKDIR"`.
- `$WORKDIR/parsed-verdicts-<refuter>.json` — `consume-verdicts` stdout per refuter (a DICT: `status` + a `verdicts` array). Written + read per refuter in PHASE 4; its `.verdicts` array is extracted and concatenated into `verdicts.json`.
- `$WORKDIR/verdicts.json` — every refuter's `parsed-verdicts-<refuter>.json` `verdicts` array concatenated into ONE bare array. Written in PHASE 4, read by `apply-verdicts --verdicts`.
- `$WORKDIR/partition.json` — `apply-verdicts` stdout (a DICT: `confirmed` + `dismissed` + `uncertain` + `contested` buckets, with `contested` already `[CONTESTED]`-tagged). Written in PHASE 4, read by `render-report --partition` in PHASE 6.

## Reference files

Read `.claude/commands/grill/references/refutation-preamble.md` in full at PHASE 4 (it is the refuter brief text, injected verbatim by `render-verify-brief`). The two adversary references — `anti-relitigation-preamble.md` and `design-attack-checklist.md` — are read and injected by the `render-brief` verb itself; the orchestrator does NOT read or paraphrase them. `report-format.md` documents the report skeleton the helper produces (orientation only; the helper owns the actual render).

- `.claude/commands/grill/references/anti-relitigation-preamble.md` — the design-grill scope-discipline preamble (PHASE 2, the adversary; injected by `render-brief`). Bars relitigation of settled upstream decisions and states the "does fixing it destroy the plan?" upstream-routing test.
- `.claude/commands/grill/references/design-attack-checklist.md` — the design-level attack vectors + what to quote as Evidence for each (PHASE 2, the adversary; injected by `render-brief`). The `## Finding N` output contract itself is owned by `render-brief`, not this file.
- `.claude/commands/grill/references/refutation-preamble.md` — the REFUTATION / cross-examination preamble + the per-finding verdict output contract (PHASE 4, every refuter). Load-bearing prompt text — `render-verify-brief` injects it verbatim into each refuter brief; do not paraphrase, summarize, or templatize it.
- `.claude/commands/grill/references/report-format.md` — the report skeleton `render-report` produces (orientation for PHASE 6; the helper owns the actual render).

## Helper interaction model

Every mechanical step is a normal Bash tool call to `.devforge/lib/grill_helper <verb> ...`. Each verb prints JSON (or a rendered block) to stdout. Most verbs that consume a prior verb's output take a `--<name> <path>` flag (not stdin), so capture stdout to the named `$WORKDIR/*.json` scratch file with `>` and pass that path into the next call — the per-phase fences below show the exact redirects. Re-establish `WORKDIR="${TMPDIR:-/tmp}/forge-grill"` at the top of every Bash block that touches scratch (the variable does not survive across Bash calls — see PHASE 0). On any non-zero exit, copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then follow the recovery note for that phase. The helper owns file structure, validation, and atomic writes; the orchestrator owns the adversary/refuter dispatch, the CBM-graph traversal that the adversary performs (not the helper), the verbatim prompt text, user-facing prose, and phase pacing.

## PHASE 0 — Preflight + feature resolution

Cheapest guards first; preflight before any feature work. `/grill` runs only by invocation — there is no auto-gate; this preflight confirms the setup chain completed and the target feature has both a `spec.md` and a `plan.md`.

### 0.1 — Resolve the feature directory

Resolve the feature dir from `$ARGUMENTS`:

- When `$ARGUMENTS` names a feature directory (`specs/NNN-<slug>`) or a `plan.md` inside one (e.g. `specs/001-auth/plan.md`), use that feature directory (strip a trailing `plan.md` filename to the `specs/NNN-<slug>` dir).
- When `$ARGUMENTS` is empty, auto-resolve the lowest-numbered `specs/NNN-*` directory that contains a `plan.md` (PHASE 1's `resolve-scope` performs this auto-detection — so when `$ARGUMENTS` is empty you may leave the feature unresolved here and let `resolve-scope --feature` auto-detect it, then carry forward the `feature_dir` it returns).

Carry the resolved feature dir forward as `<feature>` — every subsequent `--feature` / `--feature-dir` flag takes it. (When the feature was left for `resolve-scope` to auto-detect, set `<feature>` from the manifest's `feature_dir` after PHASE 1.)

### 0.2 — Preflight gate

```bash
.devforge/lib/grill_helper preflight --workspace-root . --feature-dir <feature> > /tmp/grill-preflight-check.json
```

`preflight` checks the 4-command setup chain (`/init-forge → /generate-docs → /configure → /constitute`), the populated-constitution guard, AND the feature gate (the target `<feature>` has BOTH `spec.md` and `plan.md` — the required preconditions for `/grill`, which runs between `/plan` and `/breakdown`). It ALWAYS writes its JSON context block to stdout BEFORE any gate check, then exits **2** with a user-facing stderr message when (a) a setup-chain artefact is missing, (b) `constitution.md` is absent or still carries an unpopulated sentinel, or (c) the feature is missing `spec.md` or `plan.md`. On exit 2, copy the helper's stderr VERBATIM as a fenced code block and end the turn — the user runs the named missing command first (`/specify` then `/plan` for a missing feature artefact). On exit 0, the stdout JSON carries `source_root` (the project's Source Root — `.` for a standalone install, the inner project subdir in wrapper mode), `framework`, `language`, and `wrapper_mode`. (`$WORKDIR` is not established until 0.3, so this gate call captures to a fixed `/tmp` path; 0.3 re-runs `preflight` into `$WORKDIR/preflight.json` once the scratch dir exists. `preflight` is read-only and cheap, so running it twice is harmless.) Carry `source_root` and `framework` forward: PHASE 4 passes `source_root` to `render-verify-brief --source-root`, and PHASE 6 passes both to `render-report`.

When `$ARGUMENTS` was empty and the feature was left for `resolve-scope` to auto-detect, you cannot pass `--feature-dir` here yet; in that case omit `--feature-dir` (the feature gate is skipped for this call), run the setup-chain + constitution gate, and re-run `preflight --feature-dir <feature>` once PHASE 1 has resolved the feature, before dispatching the adversary in PHASE 2.

### 0.3 — Initialize run state + scratch dir

This sub-phase only establishes `$WORKDIR` and re-runs preflight into it — it does NOT advance the phase counter (PHASE 1 below opens with the `check-status-and-flip --to scope` boundary advance). The phase counter is advanced by `check-status-and-flip`, which writes `specs/[feature]/grill-state.json` to the named phase so an interrupted run can report where it stopped: call it ONCE at the start of each major phase with `--feature-dir <feature> --to <phase>` (`scope`, `attack`, `validate`, `refute`, `classify`, `report`), and once at the very end of PHASE 6 with `--to report --status complete`. Keep these lightweight (one call per boundary, no parsing of the output beyond the non-zero-exit check). `--to` accepts any label, so these phase names are a convention, not a helper-enforced enum. (Note: the grill state verb keys on `--feature-dir`, NOT `--workspace-root` — its state file is per-feature, not per-workspace.)

Establish + clear the scratch working directory:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
rm -rf "$WORKDIR" && mkdir -p "$WORKDIR"
```

**All intermediate scratch for this run lives in `$WORKDIR` (the fixed literal `${TMPDIR:-/tmp}/forge-grill`), OUTSIDE the repo.** The literal is `forge-grill`, NOT `forge-audit` or `forge-review` — `/audit` or `/review` may run concurrently, and a shared workdir would corrupt both runs. `$WORKDIR` is outside the work tree, so the scratch files need no leading dot, no gitignore handling, and no per-file `rm` list. The `rm -rf "$WORKDIR" && mkdir -p "$WORKDIR"` clears any stale scratch from a prior crashed run.

**CRITICAL — `$WORKDIR` is a FIXED LITERAL you re-derive in every Bash block; it does NOT persist across calls.** The orchestrator runs each Bash tool call in a FRESH shell, so shell variables (including `$WORKDIR`) do NOT carry from one Bash call to the next. So every Bash block that touches scratch MUST begin by re-establishing `WORKDIR="${TMPDIR:-/tmp}/forge-grill"` and then reference `"$WORKDIR/..."`. The literal is identical in every block, so each block reconstructs the same directory.

Now re-capture the preflight context into `$WORKDIR` so later blocks can re-read its `source_root` / `framework` values (the gate already passed in 0.2; this just persists the context to the scratch dir):

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
.devforge/lib/grill_helper preflight --workspace-root . --feature-dir <feature> > "$WORKDIR/preflight.json"
```

## PHASE 1 — Resolve scope (static manifest)

```bash
.devforge/lib/grill_helper check-status-and-flip --feature-dir <feature> --to scope
```

Resolve the target `plan.md` and assemble the STATIC path manifest the adversary attacks against. This resolves the target ONLY — it does NOT compute the three-ring codebase blast radius. A Python helper cannot call the CBM graph (the same constraint that makes `/audit`'s ORCHESTRATOR drive the MCP while its helpers only consume the scratch chain); the three-ring blast-radius traversal therefore belongs to the ATTACK step (PHASE 2), performed by the `devils-advocate` agent which holds the CBM graph tools, NOT to `resolve-scope`.

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
.devforge/lib/grill_helper resolve-scope --feature <feature> --workspace-root . > "$WORKDIR/manifest.json"
```

`resolve-scope` resolves the feature (an explicit `specs/NNN-*` dir or `plan.md` path via `--feature`, else auto-detects the lowest-numbered feature under `specs/` that has a `plan.md`) and emits the `GrillScopeManifest` JSON to stdout; the `>` redirect captures it to `$WORKDIR/manifest.json`. Stdout JSON carries `feature_dir`, `feature_id`, `plan_path`, `spec_path` (both required and existence-checked), `handoff_path` (the upstream specify handoff if present, else `null`), `constitution_path`, and `claude_md_path` — the existence-checked paths the adversary will read directly (the helper does NOT read file CONTENTS; the agent reads them). On a non-zero exit (feature not found, missing `plan.md` / `spec.md`), copy the helper's stderr VERBATIM and end the turn. When PHASE 0 left the feature for auto-detection, set `<feature>` from the manifest's `feature_dir` now and re-run the PHASE-0.2 `preflight --feature-dir <feature>` gate before dispatching.

Extract the human-readable scope block into its own file — the refuter briefs (PHASE 4) take a pre-rendered scope-block FILE via `--scope-block`, not the manifest JSON. The scope block is a short plain-text summary of what is under attack (the feature id + the plan/spec paths):

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
python3 -c "import json; m=json.load(open('$WORKDIR/manifest.json')); open('$WORKDIR/scope-block.txt','w').write('Feature: {0}\nplan.md: {1}\nspec.md: {2}\n'.format(m['feature_id'], m['plan_path'], m['spec_path']))"
```

Carry the manifest's `feature_dir` forward as `<feature>` (every later `--feature` flag takes it) and note `plan_path` + `spec_path` for the PHASE-6 `--scope-files` count (the static manifest scopes the plan + its referenced specs, so the scope-file count is small — pass `2` unless the manifest later grows a file list).

## PHASE 2 — Attack (dispatch the adversary)

```bash
.devforge/lib/grill_helper check-status-and-flip --feature-dir <feature> --to attack
```

`/grill` dispatches a SINGLE adversary — the `devils-advocate` agent — NOT a multi-finder ensemble. The architect is NOT in the ensemble: it authored the design, and by charter it is an OPTIMIZER / decision authority that "decides HOW" and owns the final call, not an adversary chartered to attack the design it chose. The adversary reads the artifacts the manifest names AND resolves the three-ring codebase blast radius ITSELF via its CBM graph tools — the command does NOT pre-traverse the codebase.

### 2.1 — Adversary-existence check

The adversary agent is present when `.claude/agents/devils-advocate.md` exists. If it is ABSENT, tell the user to re-run `update.sh` to (re)generate the `devils-advocate` agent and end the turn — `/grill` cannot run without its single finder (there is no graceful-degradation fallback; the adversary IS the command). When present, carry `devils-advocate` forward as the single present finder — it is the author passed into PHASE 4's `route-refutation --finders` (alongside the refuters PHASE 4.0 determines) and the lone finder PHASE 6 passes to `render-report --finders`.

### 2.2 — Build the adversary brief

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
.devforge/lib/grill_helper render-brief --manifest "$WORKDIR/manifest.json" --references-dir .claude/commands/grill/references --tmp-path "$WORKDIR/tmp-devils-advocate.md"
```

`render-brief` reads `$WORKDIR/manifest.json` and the two reference files under `--references-dir` (`.claude/commands/grill/references` — the installed location): `anti-relitigation-preamble.md` and `design-attack-checklist.md`. `--tmp-path PATH` sets the EXACT path the brief tells the adversary to write its findings to; pass `"$WORKDIR/tmp-devils-advocate.md"` so the temp lands in `$WORKDIR` (outside the repo). It assembles the brief in this order: the anti-relitigation preamble, the design-level attack checklist, the read-context block (the manifest paths), the three-ring blast-radius traversal instruction (carrying the Ring-1 cap default), the output contract (the `## Finding N` field shape, with the finding cap substituted), and the closing reminder (the Bash-write command + grounding rule). Optional `--ring1-cap N` (default 15) and `--finding-cap N` (default 30) tune the traversal cap and finding budget — leave them unset to use the defaults baked into the helper. Pass the rendered brief as the Task tool PROMPT. Do NOT save the brief to an extra file; pass the brief text straight to the Task prompt. Dispatching with `subagent_type: devils-advocate` ALREADY loads the adversary's persona (`.claude/agents/devils-advocate.md`) as the subagent's system context — so do NOT prepend or re-inline the persona file into the brief; the brief carries only the grill-specific instructions on top of it.

### 2.3 — Dispatch the adversary

Dispatch ONE Task call with `subagent_type: devils-advocate` and the rendered brief as the prompt. The adversary then, on its own:

- **Reads the design artifacts** the manifest names — `plan.md` (the HOW under attack), `spec.md` (the WHAT — TRACE context so a grounded attack can be attributed to the upstream stage that introduced it), the recon dossier (`handoff_path`, if present), and `constitution.md`.
- **Resolves the three-ring codebase blast radius via its CBM graph tools** (the command does NOT pre-traverse): **Ring 0** (read in full) — the existing files the plan's File Impact table declares it will MODIFY, plus their tests; **Ring 1** (read in full, ONE hop, CAPPED at the brief's Ring-1 default) — the direct callers/callees of Ring-0 files via `trace_path`, with a Ring-0 hub EXCEEDING the cap read at its highest-centrality slice and the large fan-out EMITTED as a finding (never silently dropped); **Ring 2** (QUERY only, NOT read into context) — the whole repo via `search_graph` / `search_code` / `get_architecture`, pulling only the specific `get_code_snippet` a hit points to (this is how duplicate-by-new-file and layer/boundary violations get grounded WITHOUT reading the repo). Read NARROW (Ring 0 + one hop), query WIDE (Ring 2).
- **Self-gated web-verification** — fires ONLY when the plan names an external dependency (library / version / API / pattern); a pure-internal-logic plan skips it automatically. The adversary VERIFIES the plan's claim against current docs via `context7` (with `WebFetch` / `WebSearch` only for CVEs/advisories context7 does not cover). VERIFY the claim, do NOT re-DISCOVER alternatives — a "better option exists" hit routes upstream (a `/discover` re-entry signal), it is not adopted into the plan.

The adversary is read-only and carries `Bash` (not `Write`), so it writes its findings to `$WORKDIR/tmp-devils-advocate.md` via Bash shell redirection (the closing reminder in the brief gives the exact `cat > … << 'EOF'` command) in the fixed parseable `## Finding N` format the output contract specifies — and writes `# Status: failed` + a `# Reason:` line on partial failure, or `# Finding count: 0` when it finds nothing. The orchestrator does NOT dispatch CBM or context7 calls on the adversary's behalf — the adversary holds those tools and runs them inside its own Task turn.

## PHASE 3 — Validate (the grounding gate)

```bash
.devforge/lib/grill_helper check-status-and-flip --feature-dir <feature> --to validate
```

Parse the adversary's findings, extract the `findings` array, then validate that array against the actual source to discard ungrounded attacks:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
.devforge/lib/grill_helper consume-tmp --tmp "$WORKDIR/tmp-devils-advocate.md" --agent devils-advocate > "$WORKDIR/parsed-devils-advocate.json"
# Extract the .findings array from the parsed dict into a bare JSON array:
python3 -c "import json; print(json.dumps(json.load(open('$WORKDIR/parsed-devils-advocate.json'))['findings']))" > "$WORKDIR/findings-devils-advocate.json"
.devforge/lib/grill_helper validate-findings --findings "$WORKDIR/findings-devils-advocate.json" --repo-root . > "$WORKDIR/validated-devils-advocate.json"
```

`consume-tmp` reads the adversary temp file (`--tmp`) and regex-parses it into a result dict with `status` (`complete` / `clean` / `failed` / `missing`) and a `findings` array. `validate-findings` requires a BARE JSON array of finding dicts (it rejects a dict with exit 2), so extract `.findings` from the parsed dict first — the `python3 -c` line above does that. When `status` is `failed` or `missing`, note the reason for the report and treat the findings list as empty (the adversary contributed nothing). `validate-findings` runs the anti-hallucination guard — file exists, line in range, evidence non-empty, pattern present, evidence quote grounded — and emits a `passed` array (the findings that survived) plus a `discard_counts` tally. `Finding.file` is polymorphic — it holds `plan.md`, `spec.md`, the constitution path, OR a real source file in the Ring-0/Ring-1 blast radius — and the SAME validator validates them all because all of those resolve under `source_root`. (`--repo-root .` is the repo root for resolving relative paths. Pass `--source-root <rel>` ONLY when the project's Source Root is a SUBDIRECTORY of the repo — e.g. `--source-root src` — so the validator resolves finding paths against it; for a standalone `source_root == "."` install, omit `--source-root`.) A web-only attack (no `source_root` file, Evidence = a re-fetchable citation) carries its grounding in the citation rather than a verbatim source quote — the refutation pass (PHASE 4) judges it on the captured citation.

Extract the validated `passed` array into the working list `$WORKDIR/validated.json`:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
python3 -c "import json; print(json.dumps(json.load(open('$WORKDIR/validated-devils-advocate.json')).get('passed', [])))" > "$WORKDIR/validated.json"
```

This array is the working list the refutation pass (PHASE 4) reads. **If `$WORKDIR/validated.json` is an empty array `[]`** (the adversary produced no grounded attack), there is nothing to refute or classify: SKIP PHASE 4 entirely (do not call `route-refutation`), write an empty partition to `$WORKDIR/partition.json` yourself, set the disposition to PROCEED (no surviving attack threatens the design), and proceed to PHASE 6 with an empty refuters list:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
printf '%s' '{"confirmed": [], "dismissed": [], "uncertain": [], "contested": []}' > "$WORKDIR/partition.json"
```

In the PHASE-6 `render-report` call, pass `--refuters ""` (no refuter ran), `--finders-skipped ""` (PHASE 4.0 was skipped along with the rest of PHASE 4, so no refuter was found absent — nothing was consulted because there was nothing to refute), `--disposition PROCEED`, and a `--rationale` stating the adversary found no grounded design defect. The report then renders a clean, no-findings grill with a PROCEED disposition.

## PHASE 4 — Refute (cross-examination)

```bash
.devforge/lib/grill_helper check-status-and-flip --feature-dir <feature> --to refute
```

Refutation runs ONCE on the working list, AFTER validation and BEFORE classification. Its job is to invert the default from "assume a defect" to "assume correct unless proven": each finding is cross-examined by a non-author refuter whose default verdict is NOT-a-defect, and only the survivors flow to the classification + report. The refuters are the architect-EXCLUDED priority `[code-reviewer, qa-reviewer, security-reviewer]` — the architect is NEVER a refuter (it authored the design and must judge neither the attacks on it nor the refutation). Read `.claude/commands/grill/references/refutation-preamble.md` in full now — it is the refuter brief text and the verdict output contract, injected verbatim by `render-verify-brief`.

The steps below are a per-refuter dispatch loop, opened by a present-refuter determination.

### 4.0 — Determine the present refuters

`route-refutation` can only SELECT a refuter that is passed to it in `--finders`; the priority list `[code-reviewer, qa-reviewer, security-reviewer]` only RANKS among the agents passed, it does not make any of them present. So before routing, determine which refuters are installed: for EACH agent in the architect-excluded priority order `[code-reviewer, qa-reviewer, security-reviewer]`, test whether `.claude/agents/<name>.md` exists (the same presence test PHASE 2.1 uses for `devils-advocate`). Build two comma-lists from the result — `<present-refuters>` (the installed ones, in priority order) and `<skipped-refuters>` (the absent ones). These three are plan-15 standard core reviewers and are normally all installed, so `<skipped-refuters>` is normally empty. Carry both lists forward: 4.1 passes `<present-refuters>` into `route-refutation --finders`, and PHASE 6 passes `<skipped-refuters>` into `render-report --finders-skipped`.

### 4.1 — Route each finding to a non-author refuter

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
.devforge/lib/grill_helper route-refutation --findings "$WORKDIR/validated.json" --finders "devils-advocate,<present-refuters>" > "$WORKDIR/refutation-routes.json"
```

`route-refutation` selects a refuter for each finding from the agents passed in `--finders`, choosing the FIRST in the architect-excluded priority order `[code-reviewer, qa-reviewer, security-reviewer]` that is present in `--finders` AND is not the finding's author. `devils-advocate` is passed because it is the author — the `!= author` rule then excludes it from refuting its own findings; the present refuters (4.0's `<present-refuters>`) must be passed too or none can be selected and the finding falls back to author self-refutation. The architect is never passed and never a refuter. Because `<present-refuters>` is passed in `--finders` alongside `devils-advocate`, the author (`devils-advocate`) is in the pool but never chosen (excluded by the `!= author` rule), and `code-reviewer` — first in the priority list — receives all findings when it is present. Stdout (captured to `$WORKDIR/refutation-routes.json`) is a list of `{refuter, findings}` groups — each group is one refuter and the bare-array subset of findings routed to it. On a non-zero exit, copy the helper's stderr VERBATIM and end the turn.

### 4.2 — Dispatch each refuter over its routed subset, in batches

For each `{refuter, findings}` group, write that group's `findings` subset to a scratch file (a one-line `python3 -c` extraction from `$WORKDIR/refutation-routes.json`) and render that refuter's brief over its assigned subset:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
.devforge/lib/grill_helper render-verify-brief --findings "$WORKDIR/refute-<refuter>.json" --refuter <refuter> --references-dir .claude/commands/grill/references --scope-block "$WORKDIR/scope-block.txt" --source-root <source-root> --tmp-path "$WORKDIR/verdicts-<refuter>.md"
```

`render-verify-brief` assembles the refuter prompt — the refutation preamble (read verbatim from `.claude/commands/grill/references/refutation-preamble.md` under `--references-dir`, the installed location) plus the assigned findings to cross-examine — reading the pre-rendered scope block from `$WORKDIR/scope-block.txt` (PHASE 1). `--tmp-path` sets the EXACT path the brief tells the refuter to write its verdicts to; pass `"$WORKDIR/verdicts-<refuter>.md"`. Substitute `<source-root>` with the `source_root` from `$WORKDIR/preflight.json` (PHASE 0). Pass the rendered brief as the Task tool PROMPT. Dispatching with `subagent_type: <refuter>` ALREADY loads that refuter's persona — so do NOT prepend or re-inline the persona; the refutation preamble in the brief carries only the cross-examination instructions on top of it. The brief instructs the refuter to write its fixed-format `## Verdict N` markdown to `$WORKDIR/verdicts-<refuter>.md` via Bash shell redirection (the refuter is a read-only reviewer carrying `Bash`, so it writes the file via redirection — no Write tool needed). **Dispatch the refuter groups in batches** (multiple Task calls in a single turn, wait for the batch before the next); do not fan out all refuter groups at once. Each refuter judges ONLY its routed findings (a bounded set), not the whole working list. On a non-zero `render-verify-brief` exit, copy the helper's stderr VERBATIM and end the turn.

### 4.3 — Parse each refuter's verdicts, then merge

For each refuter dispatched, parse its verdict file into a verdict array, then concatenate all refuters' parsed arrays into one bare array:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
.devforge/lib/grill_helper consume-verdicts --verdicts "$WORKDIR/verdicts-<refuter>.md" --refuter <refuter> > "$WORKDIR/parsed-verdicts-<refuter>.json"
# After every refuter is parsed, extract each .verdicts array and concatenate into ONE bare array:
python3 -c "import json,glob; out=[]; [out.extend(json.load(open(p)).get('verdicts',[])) for p in sorted(glob.glob('$WORKDIR/parsed-verdicts-*.json'))]; print(json.dumps(out))" > "$WORKDIR/verdicts.json"
```

`consume-verdicts` regex-parses one refuter's fixed-format markdown verdict file (the `## Verdict N` blocks the refutation contract specifies) into a DICT carrying `status` (`complete` / `failed` / `missing`) and a `verdicts` array. Pass `--refuter <refuter>` so a verdict missing the `# Refuter:` header is still attributed. The `python3 -c` line extracts each parsed dict's `.verdicts` array and concatenates every refuter's verdicts into `$WORKDIR/verdicts.json` — the merged verdict array `apply-verdicts` consumes. When a refuter's `status` is `failed` or `missing`, its `verdicts` array is empty so it contributes nothing to the merge; `apply-verdicts` handles an unjudged finding per its own contract. On a non-zero `consume-verdicts` exit, copy the helper's stderr VERBATIM and end the turn.

### 4.4 — Apply the verdicts and partition

Partition the FULL working list against the merged verdicts:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
.devforge/lib/grill_helper apply-verdicts --findings "$WORKDIR/validated.json" --verdicts "$WORKDIR/verdicts.json" > "$WORKDIR/partition.json"
```

`apply-verdicts` reads the SAME `$WORKDIR/validated.json` working list PHASE 4.1 routed (NOT a refutation-derived subset) and the merged verdicts, keys each verdict to its working-list finding by the `(file, line, pattern, agent)` tuple, and partitions category-aware per the D7 routing. It prints a DICT (captured to `$WORKDIR/partition.json`) with four buckets:

- `confirmed` — survivors the refuter demonstrated as genuine design defects; they earn the report headline.
- `dismissed` — the default verdict on undemonstrable findings (incl. relitigation the refuter knocked down); they go to the report's Dismissed / Worth-a-Glance appendix. (A dismissed `[CONSTITUTION-VIOLATION]` does NOT land here — see `contested`.)
- `uncertain` — a finding the refuter could not resolve that is NOT high-stakes (its category is not `security` AND it carries no `[CONSTITUTION-VIOLATION]` tag); it rides the Dismissed / Worth-a-Glance appendix.
- `contested` — HIGH-stakes findings the refuter could not confirm: a `security` finding or any `[CONSTITUTION-VIOLATION]` finding the refuter returned `uncertain` on, PLUS any `dismiss` verdict on a grounded `[CONSTITUTION-VIOLATION]`. `apply-verdicts` tags each `[CONTESTED]`. These are surfaced IN the report headline, flagged — never buried.

The helper owns the verdict→bucket partition and the category routing; the orchestrator does not re-derive verdicts. On a non-zero `apply-verdicts` exit, copy the helper's stderr VERBATIM and end the turn.

## PHASE 5 — Classify (the "destroys-the-plan?" test)

```bash
.devforge/lib/grill_helper check-status-and-flip --feature-dir <feature> --to classify
```

This is ORCHESTRATOR REASONING, not a helper verb — there is no `classify` verb. Read the `confirmed` and `contested` buckets from `$WORKDIR/partition.json` (the surviving grounded findings). For EACH surviving grounded finding, apply the two-question decision tree:

- **Q1 — "Does a different HOW (a re-plan against the SAME spec) fix the defect?"**
  - YES → **REVISE-PLAN** (plan-local — fixing it leaves the plan intact; a different HOW satisfies the same WHAT).
  - NO (no HOW survives the fix — this is what "destroys the plan" means) → go to Q2.
- **Q2 — "Would a corrected WHAT or grounding (re-`/specify` / re-`/discover` / re-`/research`) yield a viable design?"**
  - YES → **RE-ENTER-UPSTREAM** — attributed to the NEAREST introducing stage (trace via `spec.md` + the dossier: a bad requirement already in the research handoff → `research`; introduced at discovery → `discovery`; introduced at `/specify` → `spec`; nearest-stage-first, NOT a blanket rewind to research).
  - NO (nothing rescues it — the feature is infeasible, unjustified, or should be bought not built) → **KILL**.

PROCEED is the no-surviving-attack / all-accepted-as-risk case — outside this YES/NO tree (the empty-`validated.json` branch in PHASE 3 already routes there; reach it here too when every survivor is accepted as risk).

Synthesize ONE recommended disposition for the whole run (the most severe survivor's routing wins: KILL > RE-ENTER-UPSTREAM > REVISE-PLAN > PROCEED) plus a `rationale` paragraph naming the surviving findings that drove it. For a **RE-ENTER-UPSTREAM** OR a **REVISE-PLAN** disposition, ALSO compose the re-entry-seed inputs PHASE 7's matching re-entry arm needs for its `write-seed` call (the seed is written only if the user picks the matching re-entry at the human gate):

- `target_stage` — the SEED TOKEN, NOT the slash-command name. For RE-ENTER-UPSTREAM it is the nearest upstream stage `spec` | `discovery` | `research`; for REVISE-PLAN it is `plan`. `write-seed --target-stage` accepts all four (`spec` | `discovery` | `research` | `plan`); it rejects any other value with exit 2.
- `prior_conclusion` — for RE-ENTER-UPSTREAM, what that upstream stage concluded that is now invalidated; for REVISE-PLAN, the flawed plan decision the revision must replace.
- `invalidating_evidence` — the grounded grill finding that invalidates it.
- `must_satisfy` — for RE-ENTER-UPSTREAM, what the re-run must additionally satisfy; for REVISE-PLAN, the fix the revised plan must meet.
- `cycle_count` — the bounded-compounding-loop counter (1 for a first grill, incremented when this run itself re-entered from a prior seed).
- `carried_findings` — prior findings carried forward, monotonic (empty on a first grill; for REVISE-PLAN, the remaining confirmed findings the revision must address).
- `provenance` — a pointer to this `specs/[feature]/grill.md` / the plan path.

Carry the disposition + rationale forward to PHASE 6 (the report), and carry the seed inputs (for RE-ENTER-UPSTREAM or REVISE-PLAN) forward to PHASE 7's matching re-entry arm — that arm writes the seed only if the user's pick matches the recommendation.

## PHASE 6 — Report

```bash
.devforge/lib/grill_helper check-status-and-flip --feature-dir <feature> --to report
```

Capture today's date, then render the report from the partition + the PHASE-5 disposition:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
DATE="$(date +%Y-%m-%d)"
.devforge/lib/grill_helper render-report --partition "$WORKDIR/partition.json" --feature <feature> --date "$DATE" --finders "devils-advocate" --finders-skipped "<skipped-refuters>" --refuters "<refuters-csv>" --source-root <source-root> --framework "<framework>" --scope-files <file-count> --disposition <DISPOSITION> --rationale "<rationale>"
```

`render-report` reads `$WORKDIR/partition.json` (the four buckets from PHASE 4) directly and renders the full grill markdown (skeleton documented in `.claude/commands/grill/references/report-format.md`), writing it to `specs/[feature]/grill.md` via an atomic write, OVERWRITING any prior `grill.md` (idempotent). The flags:

- `--partition "$WORKDIR/partition.json"` — the apply-verdicts buckets.
- `--feature <feature>` — the resolved feature dir; `grill.md` is written here.
- `--date "$DATE"` — `YYYY-MM-DD` (required for deterministic output; the helper never calls the clock).
- `--finders "devils-advocate"` — the single finder invoked.
- `--finders-skipped "<skipped-refuters>"` — in `/grill`, refuters are the only non-adversary agents, so the shared `--finders-skipped` flag (a report-labeling flag inherited from `/audit` + `/review`, where the report's "finders" ARE the refuter pool) carries them — the `<skipped-refuters>` comma-list PHASE 4.0 built: the refuter agents (code-reviewer / qa-reviewer / security-reviewer) the 4.0 presence check found ABSENT (no `.claude/agents/<name>.md`); the helper renders them on the report's "Finders skipped (not installed): …" line. This is normally empty — the refuters are plan-15 standard core reviewers normally all installed — so pass `""` when 4.0 found none skipped.
- `--refuters "<refuters-csv>"` — the refuter agents that actually ran: the distinct `refuter` values read from `$WORKDIR/refutation-routes.json`, comma-separated. In the normal grill case this is the same set as `<present-refuters>` (every present refuter is non-author and receives at least one finding when findings exist), but read it from the routes file rather than reusing `<present-refuters>` directly. Pass `""` when no refuter ran (the empty-`validated.json` branch).
- `--source-root <source-root>` — the Source Root from `$WORKDIR/preflight.json`.
- `--framework "<framework>"` — the Framework / Language from `$WORKDIR/preflight.json`.
- `--scope-files <file-count>` — the plan-scope file count (the static manifest scopes the plan + its referenced specs; pass `2` for the plan + spec).
- `--disposition <DISPOSITION>` — the PHASE-5 disposition: `PROCEED` | `REVISE-PLAN` | `RE-ENTER-UPSTREAM` | `KILL` (required, non-empty).
- `--rationale "<rationale>"` — the PHASE-5 rationale (required, non-empty).
- `--re-entry-target <stage>` — pass ONLY when `--disposition RE-ENTER-UPSTREAM`: the nearest stage `spec` | `discovery` | `research`. It MUST be absent for every other disposition (the helper rejects a non-RE-ENTER-UPSTREAM disposition that carries a `--re-entry-target`).

`render-report` validates the disposition (exit 2 on a bad value, or on a `--re-entry-target` that is missing for RE-ENTER-UPSTREAM or present for another disposition). The report leads with CONFIRMED findings (a force-ranked Top Priorities list + a by-file/by-category grouped listing), surfaces high-stakes `[CONTESTED]` findings IN that headline flagged, drops dismissed + low-stakes uncertain findings to a `## Dismissed / Worth a Glance` appendix, and renders the `## Disposition` section. Stdout is a JSON ack `{path, confirmed, contested, dismissed, uncertain}`; the `path` is the written `specs/[feature]/grill.md`. On a non-zero exit, copy the helper's stderr VERBATIM and end the turn.

**WIP-commit the grill report artifacts.** Now that `grill.md` is written, commit `/grill`'s own report outputs so the work is git-safe at this step. Run this UNCONDITIONALLY (every `/grill` run reaches here with a written `grill.md`). `grill-state.json` is always included — it lives under `specs/[feature]/` and is part of what this run wrote. The seed (`grill-seed.json`) is NOT committed here — it is not written until the PHASE-7 human gate, and only when the user authorizes a matching re-entry; that arm commits it itself:

```bash
.devforge/lib/artifact_helper commit-artifacts --paths '["specs/<feature>/grill.md", "specs/<feature>/grill-state.json"]' --label 'grill: <NNN>-<slug>'
```

Substitute `<feature>` with the resolved feature dir and `<NNN>-<slug>` with the feature id. `commit-artifacts` stages ONLY the named paths and makes a `[WIP] grill: <NNN>-<slug>` commit in the INSTALL repo (never the wrapper-mode source/product repo). It is FAIL-SOFT: a git staging or commit failure warns on stderr and exits 1 (non-fatal — the report is already written, so note the warning and CONTINUE; do NOT end the turn); "nothing to commit" (paths already staged or absent) exits 0 silently as a benign no-op. The `[WIP]` commit folds into `/finalize`'s squash, leaving the final PR unchanged.

Then mark the run complete so an interrupted re-run can distinguish a finished grill from a stopped one:

```bash
.devforge/lib/grill_helper check-status-and-flip --feature-dir <feature> --to report --status complete
```

## PHASE 7 — Human gate (the user owns the verdict)

The disposition is a RECOMMENDATION; the human makes the final call. Present the recommended disposition + its rationale (print the report's `## Disposition` block, or summarize it), tell the user `specs/[feature]/grill.md` was written, and capture the user's choice via AskUserQuestion so the next step is explicit:

> The grill recommends a disposition for this plan. What do you want to do?

Options (2–4; AskUserQuestion auto-injects "Other"):

- `Proceed` — the plan is sound; run `/breakdown`.
- `Revise plan` — re-run `/plan` or hand-patch `plan.md`, then optionally re-run `/grill`.
- `Re-enter upstream` — re-run the named upstream command (`/specify`, `/discover`, or `/research`).
- `Kill` — stop; the design is fatally flawed (re-run `/plan` with a wholly different approach).

(Always offer `Proceed` and `Kill` as the outer brackets, and `Revise plan` as an always-available choice (recommended when the disposition is REVISE-PLAN). Omit `Re-enter upstream` when the disposition is not RE-ENTER-UPSTREAM — it is only meaningful when the PHASE-5 disposition routed to an upstream stage.) Then act on the choice:

- **Proceed** → tell the user the next command is `/breakdown`. Write no seed.
- **Revise plan** → two cases, by whether this matches the recommendation:
  - **Matching (the recommendation was REVISE-PLAN)** → NOW write the re-entry seed from the PHASE-5 seed inputs, targeting `plan`, then WIP-commit it (see the seed-write + commit block below; pass `--target-stage plan`). Then tell the user to re-run `/plan`, which will detect and consume the emitted `grill-seed.json` (`target_stage="plan"`) so the revision is directed at the grill's confirmed findings, not a repeat (or hand-patch `plan.md`), then optionally re-`/grill`.
  - **Cross-pick (the recommendation was NOT REVISE-PLAN)** → write NO seed. Tell the user to re-run `/plan` manually (an undirected revision — there is no seed to consume) or hand-patch `plan.md`, then optionally re-`/grill`.
- **Re-enter upstream** → this option is offered only when the recommendation was RE-ENTER-UPSTREAM, so it is matching by construction. NOW write the re-entry seed from the PHASE-5 seed inputs, targeting the PHASE-5 nearest upstream stage (`spec` | `discovery` | `research`), then WIP-commit it (see the seed-write + commit block below; pass `--target-stage <stage>`). Then tell the user to re-run the named upstream command, which will detect and consume `grill-seed.json` so the re-run is directed, not a repeat. **Bounded loop:** after 2 kill→re-propose / re-entry cycles on the same feature (the seed's `cycle_count`), escalate to the user — "this feature may be intractable as framed — decide" — rather than looping again.
- **Kill** → stop; the design is abandoned. The recovery is a wholly new design via re-run `/plan`. Write no seed.

**Seed-write + commit block (matching re-entry arms only).** Run this ONLY inside the matching `Revise plan` or `Re-enter upstream` arm above — never for `Proceed`, `Kill`, or a cross-pick. `<stage>` is the arm's target stage: `plan` for a matching REVISE-PLAN, or the PHASE-5 nearest upstream stage (`spec` | `discovery` | `research`) for RE-ENTER-UPSTREAM. First write the seed:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
# <stage> is per-arm: `plan` for a matching Revise plan, or the upstream stage for Re-enter upstream.
.devforge/lib/grill_helper write-seed --feature <feature> --target-stage <stage> --prior-conclusion "<prior-conclusion>" --invalidating-evidence "<invalidating-evidence>" --must-satisfy "<must-satisfy>" --cycle-count <N> --carried-findings "<carried-csv>" --provenance "specs/[feature]/grill.md"
```

`write-seed` builds a `ReEntrySeed` from the PHASE-5 seed inputs and writes `specs/[feature]/grill-seed.json` via an atomic write. `--target-stage` (`spec` | `discovery` | `research` | `plan`), `--prior-conclusion`, `--invalidating-evidence`, `--must-satisfy`, and `--provenance` are all REQUIRED and non-empty (the schema rejects an empty value with exit 2). `--cycle-count` is an int ≥ 1 (default 1; increment when this run itself re-entered from a prior seed). `--carried-findings` is a comma-separated list of prior finding descriptions carried forward (monotonic compounding; may be empty). Stdout is a JSON ack `{path}`. On a non-zero exit, copy the helper's stderr VERBATIM and end the turn.

Then WIP-commit the seed so it is git-safe (mirrors the PHASE-6 report commit — install-repo-only, fail-soft):

```bash
.devforge/lib/artifact_helper commit-artifacts --paths '["specs/<feature>/grill-seed.json"]' --label 'grill-seed: <NNN>-<slug>'
```

Substitute `<feature>` with the resolved feature dir and `<NNN>-<slug>` with the feature id. `commit-artifacts` stages ONLY the named path and makes a `[WIP] grill-seed: <NNN>-<slug>` commit in the INSTALL repo (never the wrapper-mode source/product repo). It is FAIL-SOFT: a git staging or commit failure warns on stderr and exits 1 (non-fatal — the seed is already written, so note the warning and CONTINUE; do NOT end the turn); "nothing to commit" exits 0 silently as a benign no-op. The `[WIP]` commit folds into `/finalize`'s squash, leaving the final PR unchanged.

Finally, sweep the scratch directory — `render-report` was the last reader of `$WORKDIR/partition.json`, so nothing else needs the scratch:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-grill"
rm -rf "$WORKDIR"
```

## Important rules

1. **Opt-in, never an auto-gate** — `/grill` runs only by invocation (like `/audit`). There is NO stakes-detector, NO forced gate on every `/plan` run, and NO place to harden it into an always-on check. Skipping `/grill` leaves `/plan → /breakdown` byte-unchanged.
2. **The architect is absent** — it authored the design, so it is excluded from BOTH the attacker ensemble (the single finder is `devils-advocate`) AND the refuter priority list (`[code-reviewer, qa-reviewer, security-reviewer]`). The proposer never judges attacks on its own design.
3. **Read narrow, query wide, verify-not-rediscover** — the adversary reads Ring 0 + one-hop Ring 1, QUERIES Ring 2 (reading the whole codebase is `/audit`, OUT), and its web step VERIFIES the plan's claims (a "better option" hit routes upstream, it is not adopted).
4. **Evidence-first** — every finding must be grounded in a verbatim quote from the real plan / spec / dossier / code / constitution (or a re-fetchable web citation for a web claim); `validate-findings` discards ungrounded ones, and the refutation pass cross-examines each survivor before it reaches the headline.
5. **No relitigation** — the adversary attacks the CHOSEN design's demonstrable defects, not its taste; a "I would have built it differently" objection is dismissed by the refutation pass. A grounded defect inherited from upstream routes RE-ENTER-UPSTREAM, it does not become a plan attack.
6. **Constitution violations are always Critical** — never downgraded, regardless of confidence; a `[CONSTITUTION-VIOLATION]` the refuter dismissed is surfaced `[CONTESTED]` in the headline, never buried.
7. **The disposition is a RECOMMENDATION** — `/grill` recommends PROCEED / REVISE-PLAN / RE-ENTER-UPSTREAM / KILL; the human owns the final call at the `/breakdown` approval gate. The backward re-entry loop is bounded (escalate to the human after the cap).
8. **Read-only on source** — no source modifications, no fixes to the plan or spec. `/grill` does WIP-commit its OWN artifacts via `artifact_helper commit-artifacts` — `grill.md` + `grill-state.json` at the end of PHASE 6, and `grill-seed.json` in PHASE 7's matching re-entry arm when the user authorizes it — install-repo-only, fail-soft `[WIP]` commits that fold into `/finalize`'s squash; it never commits source or modifies the plan/spec.
9. **Wrapper-mode aware** — the adversary reads source files from the resolved Source Root (`source_root` from `preflight`); `specs/[feature]/` always lives at the workspace root.
10. **Cleanup is last** — all intermediate scratch lives in `$WORKDIR` (`${TMPDIR:-/tmp}/forge-grill`), outside the repo, and is swept by the single `rm -rf "$WORKDIR"` at the end of PHASE 7, never mid-run.
```