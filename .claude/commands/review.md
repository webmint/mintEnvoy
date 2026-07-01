---
name: review
description: Feature-level emergent cross-task review. Runs after `/implement` drains a feature's tasks and before `/verify`. Dispatches a 5-finder ensemble (code-reviewer, architect, qa-reviewer, security-reviewer, performance-analyst) in emergent-cross-task mode over the assembled feature diff — plus design-auditor for a runtime design-fidelity check when the feature has a design reference and manifest — cross-examines every finding with a refutation pass, and writes a findings-only `specs/[feature]/review.md` for `/verify` to consume.
argument-hint: '[spec-file/feature-dir]'
disable-model-invocation: true
---

# /review — Feature-Level Emergent Cross-Task Review

`/review` is the pipeline step run after `/implement` drains a feature's tasks and before `/verify`. It catches the ONE review job nothing else in the pipeline owns: **emergent cross-task issues** that the `/implement` per-task panel STRUCTURALLY cannot see because it reviews each task's diff in isolation. It dispatches a 5-finder ensemble — `code-reviewer`, `architect`, `qa-reviewer`, `security-reviewer`, `performance-analyst` — in EMERGENT-CROSS-TASK MODE over the ASSEMBLED feature diff (every task's changes together, the union of the feature's accumulated WIP commits), and — when the feature has a `design/reference.html` and a `specs/[feature]/design-manifest.json` — ALSO dispatches `design-auditor` for the runtime design-fidelity check (PHASE 2.5), validates every finding against the actual source to discard hallucinations, cross-examines the survivors with a refutation pass (default-dismiss unless the defect is demonstrable as emergent at feature scope), and writes a findings-only report to `specs/[feature]/review.md`. Read-only on source — it never modifies source; it WIP-commits only its OWN artifacts (`review.md` + `review-state.json`) in an install-repo-only, fail-soft `[WIP]` commit that folds into `/finalize`'s squash. State + render shape are owned by `.devforge/lib/review_helper`; the orchestrator composes values via verb subcommands.

**`/review` produces FINDINGS ONLY — it does NOT render a verdict.** The verdict is `/verify`'s job: `/verify` consumes `specs/[feature]/review.md` (folding its findings into the verdict, and warning if it is missing), and `/audit` reads recent `specs/*/review.md` files for its recurring-issue scan. Do not add a pass/fail line, an approval line, or a "ready to ship" judgment.

Usage: `/review` (auto-resolve the most-recently-modified `specs/NNN-*` feature) · `/review specs/001-auth` or `/review specs/001-auth/spec.md` (an explicit feature dir or a spec file inside it).

## Maintainer note

This file lives at `src/commands/review/main.md` in the AIDevTeamForge template repo and is the SSOT for the `/review` command. Do NOT inject project-specifics — this spec is substituted + emitted into target projects by the build. Helper paths use the installed `.devforge/lib/...` location because that's where they resolve at runtime in the target project. Reference-file paths are written author-relative (`references/<file>.md`); the emitter rewrites them to `.claude/commands/review/references/<file>.md` at install time.

## Outputs of this command

The ONLY file this command writes under the repo is:

- `specs/[feature]/review.md` — the rendered feature-review report. Produced by the helper's `render-report` verb in PHASE 4; FINDINGS ONLY (no verdict). Idempotent: re-running `/review` on the same feature OVERWRITES `review.md` (the helper does an atomic write). `/verify` consumes it next.

Per-feature run state lives in `specs/[feature]/review-state.json` (helper-owned, advanced via `check-status-and-flip --feature-dir <feature>`).

At the end of PHASE 4, `/review` WIP-commits its own artifacts — `review.md` and the per-feature `review-state.json` — via `.devforge/lib/artifact_helper commit-artifacts`. The commit lands in the INSTALL repo only (never the wrapper-mode source/product repo) and is fail-soft (a git failure warns and `/review` continues — the report is already written). The `[WIP]` commit folds into `/finalize`'s squash, so the final PR is unchanged.

### Intermediate scratch files (orchestrator-written, helper-consumed) — all under `$WORKDIR`

The helper cannot dispatch agents (a subprocess has no Task/MCP tools), so the orchestrator captures each verb's stdout to an intermediate scratch file that the next verb reads (most verbs take a `--<name> <path>` flag, not stdin). All live under `$WORKDIR` (`${TMPDIR:-/tmp}/forge-review`) and are scratch state for one run — the whole directory is removed at the end (the single PHASE-4 `rm -rf "$WORKDIR"`). Because `$WORKDIR` is outside the work tree, the files need no leading dot and no gitignore handling. Several verbs print a DICT (e.g. `consume-tmp`'s `{status, findings}`) but the next verb's `--findings` requires a BARE ARRAY — those steps include a one-line `python3 -c` extraction (shown inline at each phase).

- `$WORKDIR/preflight.json` — the `preflight` stdout (`source_root`, `framework`, `language`, `wrapper_mode`, …). Written in PHASE 0, read by the orchestrator for the `--source-root` / `--framework` values it threads into later verbs.
- `$WORKDIR/scope.json` — the `resolve-feature-scope` stdout (`files`, `files_for_finders`, `file_count`, `scope_block`). Written in PHASE 1, read by the orchestrator to extract the changed-file count + the scope block.
- `$WORKDIR/scope-block.txt` — the `scope_block` STRING extracted from `$WORKDIR/scope.json`. Written in PHASE 1, passed to every `render-agent-brief --scope-block` and `render-verify-brief --scope-block` (those verbs take a pre-rendered scope-block FILE, not the scope JSON).
- `$WORKDIR/tmp-<finder>.md` — per-finder findings, written by each dispatched finder in PHASE 2 (the brief's `--tmp-path` names this exact path), consumed by `consume-tmp` in the same phase. Swept by the end-of-run `rm -rf "$WORKDIR"`.
- `$WORKDIR/parsed-<finder>.json` — `consume-tmp` stdout per finder (a DICT: `status` + `findings` array). Written + read per finder in PHASE 2.
- `$WORKDIR/findings-<finder>.json` — the bare `findings` array extracted from `parsed-<finder>.json`. Written in PHASE 2, read by `validate-findings --findings`.
- `$WORKDIR/validated-<finder>.json` — `validate-findings` stdout per finder (`passed` + `discarded` + `discard_counts`). Written + read in PHASE 2.
- `$WORKDIR/validated.json` — every present finder's validated `passed` findings concatenated into ONE bare array. Written in PHASE 2, read by `route-refutation --findings` and `apply-verdicts --findings`.
- `$WORKDIR/refutation-routes.json` — `route-refutation` stdout (a list of `{refuter, findings}` cross-examination groups assigning each finding a non-author refuter). Written in PHASE 3, read by the orchestrator to drive the per-group `render-verify-brief` + refuter-dispatch loop.
- `$WORKDIR/refute-<refuter>.json` — one refuter group's bare-array `findings` subset, extracted by the orchestrator from `refutation-routes.json`. Written + read per refuter in PHASE 3, passed to `render-verify-brief --findings`.
- `$WORKDIR/verdicts-<refuter>.md` — per-refuter raw markdown verdicts, written by each dispatched refuter in PHASE 3 (the `render-verify-brief` `--tmp-path` names this exact path), consumed by `consume-verdicts --verdicts` in the same phase. Swept by the end-of-run `rm -rf "$WORKDIR"`.
- `$WORKDIR/parsed-verdicts-<refuter>.json` — `consume-verdicts` stdout per refuter (a DICT: `status` + a `verdicts` array). Written + read per refuter in PHASE 3; its `.verdicts` array is extracted and concatenated into `verdicts.json`.
- `$WORKDIR/verdicts.json` — every refuter's `parsed-verdicts-<refuter>.json` `verdicts` array concatenated into ONE bare array. Written in PHASE 3, read by `apply-verdicts --verdicts`.
- `$WORKDIR/partition.json` — `apply-verdicts` stdout (a DICT: `confirmed` + `dismissed` + `uncertain` + `contested` buckets, with `contested` already `[CONTESTED]`-tagged). Written in PHASE 3, read by `render-report --partition` and `render-inline-summary --partition` in PHASE 4.

## Reference files

Read `.claude/commands/review/references/refutation-preamble.md` in full at PHASE 3 (it is the refuter brief text, injected verbatim by `render-verify-brief`). The other two finder references — `anti-relitigation-preamble.md` and `emergent-issue-checklist.md` — are read and injected by the `render-agent-brief` verb itself; the orchestrator does NOT read or paraphrase them. `report-format.md` documents the report skeleton the helper produces (orientation only; the helper owns the actual render).

- `.claude/commands/review/references/anti-relitigation-preamble.md` — the emergent-cross-task scope-discipline preamble (PHASE 2, every finder; injected by `render-agent-brief`).
- `.claude/commands/review/references/emergent-issue-checklist.md` — the cross-task issue checklist + the `## Finding N` output contract (PHASE 2, every finder; injected by `render-agent-brief`).
- `.claude/commands/review/references/refutation-preamble.md` — the REFUTATION / second-opinion preamble + the per-finding verdict output contract (PHASE 3, every refuter). Load-bearing prompt text — `render-verify-brief` injects it verbatim into each refuter brief; do not paraphrase, summarize, or templatize it.
- `.claude/commands/review/references/report-format.md` — the report skeleton `render-report` produces (orientation for PHASE 4; the helper owns the actual render).

## Helper interaction model

Every mechanical step is a normal Bash tool call to `.devforge/lib/review_helper <verb> ...`. Each verb prints JSON (or a rendered block) to stdout. Most verbs that consume a prior verb's output take a `--<name> <path>` flag (not stdin), so capture stdout to the named `$WORKDIR/*.json` scratch file with `>` and pass that path into the next call — the per-phase fences below show the exact redirects. Re-establish `WORKDIR="${TMPDIR:-/tmp}/forge-review"` at the top of every Bash block that touches scratch (the variable does not survive across Bash calls — see PHASE 0). On any non-zero exit, copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then follow the recovery note for that phase. The helper owns file structure, validation, and atomic writes; the orchestrator owns finder/refuter dispatch, the verbatim prompt text, user-facing prose, and phase pacing.

## PHASE 0 — Preflight + feature resolution

Cheapest guards first; preflight before any feature I/O.

### 0.1 — Preflight gate

```bash
.devforge/lib/review_helper preflight --workspace-root . > /tmp/review-preflight-check.json
```

`preflight` checks the 4-command setup chain (`/init-forge → /generate-docs → /configure → /constitute`) and the populated-constitution guard. It ALWAYS writes its JSON context block to stdout BEFORE any gate check, then exits **2** with a user-facing stderr message when (a) a setup-chain artefact is missing or (b) `constitution.md` is absent or still carries an unpopulated sentinel. On exit 2, copy the helper's stderr VERBATIM as a fenced code block and end the turn — the user runs the named missing command first. On exit 0, the stdout JSON carries `source_root` (the project's Source Root — `.` for a standalone install, the inner project subdir in wrapper mode), `framework` (the Framework / Language string), `language`, and `wrapper_mode`. (`$WORKDIR` is not established until 0.3, so this gate call captures to a fixed `/tmp` path; 0.3 re-runs `preflight` into `$WORKDIR/preflight.json` once the scratch dir exists. `preflight` is read-only and cheap, so running it twice is harmless.) Carry `source_root` and `framework` forward: PHASE 1 passes `source_root` to `resolve-feature-scope --source-root`, PHASE 3 passes it to `render-verify-brief --source-root`, and PHASE 4 passes both to `render-report`.

### 0.2 — Resolve the feature directory

Resolve the feature dir from `$ARGUMENTS`:

- When `$ARGUMENTS` names a feature directory (`specs/NNN-<slug>`) or a file inside one (e.g. `specs/001-auth/spec.md`), use that feature directory (strip a trailing filename to the `specs/NNN-<slug>` dir).
- When `$ARGUMENTS` is empty, auto-resolve the most-recently-modified `specs/NNN-*` directory (the feature most likely just finished `/implement`).

If no `specs/NNN-*` directory exists, tell the user there is no feature to review (run `/specify` → `/plan` → `/breakdown` → `/implement` first) and end the turn. Carry the resolved feature dir forward as `<feature>` — every subsequent `--feature` / `--feature-dir` flag takes it.

### 0.3 — Initialize run state + scratch dir

```bash
.devforge/lib/review_helper check-status-and-flip --feature-dir <feature> --to phase0
```

`check-status-and-flip` advances `specs/[feature]/review-state.json` to the named phase so an interrupted run can report where it stopped. Call it once at the start of each major phase with `--feature-dir <feature> --to <phase>` (`phase0`, `phase1`, `phase2`, `phase3`, `phase4`), and once at the very end of PHASE 4 with `--to phase4 --status complete`. Keep these lightweight (one call per boundary, no parsing of the output beyond the non-zero-exit check). `--to` accepts any label, so these phase names are a convention, not a helper-enforced enum. (Note: the review state verb keys on `--feature-dir`, NOT `--workspace-root` — its state file is per-feature, not per-workspace.)

Then establish + clear the scratch working directory:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-review"
rm -rf "$WORKDIR" && mkdir -p "$WORKDIR"
```

**All intermediate scratch for this run lives in `$WORKDIR` (the fixed literal `${TMPDIR:-/tmp}/forge-review`), OUTSIDE the repo.** The literal is `forge-review`, NOT `forge-audit` — `/audit` may run concurrently, and a shared workdir would corrupt both runs. `$WORKDIR` is outside the work tree, so the scratch files need no leading dot, no gitignore handling, and no per-file `rm` list. The `rm -rf "$WORKDIR" && mkdir -p "$WORKDIR"` clears any stale scratch from a prior crashed run.

**CRITICAL — `$WORKDIR` is a FIXED LITERAL you re-derive in every Bash block; it does NOT persist across calls.** The orchestrator runs each Bash tool call in a FRESH shell, so shell variables (including `$WORKDIR`) do NOT carry from one Bash call to the next. So every Bash block that touches scratch MUST begin by re-establishing `WORKDIR="${TMPDIR:-/tmp}/forge-review"` and then reference `"$WORKDIR/..."`. The literal is identical in every block, so each block reconstructs the same directory.

Now re-capture the preflight context into `$WORKDIR` so later blocks can re-read its `source_root` / `framework` values (the gate already passed in 0.1; this just persists the context to the scratch dir):

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-review"
.devforge/lib/review_helper preflight --workspace-root . > "$WORKDIR/preflight.json"
```

## PHASE 1 — Resolve feature scope

```bash
.devforge/lib/review_helper check-status-and-flip --feature-dir <feature> --to phase1
```

Compute the assembled-feature diff — the union of every change the feature made, across all the WIP commits `/implement` accumulated (squashed only by `/finalize`, which has not run yet). This is exactly the cross-task surface the per-task panel never saw. Substitute `<feature>` and the `source_root` from `$WORKDIR/preflight.json` (PHASE 0) — `source_root` is `"."` for a standalone install and the inner project subdir path in wrapper mode; pass it verbatim to `--source-root`:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-review"
.devforge/lib/review_helper resolve-feature-scope --feature <feature> --source-root <source-root> > "$WORKDIR/scope.json"
```

`resolve-feature-scope` runs `git diff --name-only $(git merge-base <base> HEAD)..HEAD` with `cwd = source-root` and emits JSON to stdout; the `>` redirect captures it to `$WORKDIR/scope.json`. The base ref auto-detects via `origin/HEAD → main → develop → master`; pass `--base <ref>` when auto-detection fails (the exit-2 stderr message says so). In wrapper mode also pass `--install-root <install-root>` (the forge install root where `.devforge/` lives) so the emitted finder paths are install-root-relative. Stdout JSON carries `files` (sorted source-relative changed paths), `files_for_finders` (the same list, source-root-prefixed in wrapper mode), `file_count`, and `scope_block` (the pre-rendered human-readable scope summary). On a non-zero exit (not a git repo, bad ref, no auto-detectable base), copy the helper's stderr VERBATIM and end the turn.

**Empty-diff stop.** If `file_count` is `0` (HEAD == merge-base — the feature has no changes yet, or it is already squashed/merged), there is nothing to review: tell the user the feature diff is empty (no changes between the base and HEAD, so no assembled surface to review), clean up (`rm -rf "$WORKDIR"`), and end the turn gracefully. This is not an error — it is an empty feature.

Extract the `scope_block` STRING into its own file — both the finder briefs (PHASE 2) and the refuter briefs (PHASE 3) take a pre-rendered scope-block FILE via `--scope-block`, not the scope JSON:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-review"
python3 -c "import json; open('$WORKDIR/scope-block.txt','w').write(json.load(open('$WORKDIR/scope.json'))['scope_block'])"
```

Carry `file_count` forward — PHASE 4 passes it to `render-report --scope-files`.

## PHASE 2 — Finder dispatch + consume + validate

```bash
.devforge/lib/review_helper check-status-and-flip --feature-dir <feature> --to phase2
```

The 5 finders are `code-reviewer`, `architect`, `qa-reviewer`, `security-reviewer`, and `performance-analyst`. Each is dispatched in EMERGENT-CROSS-TASK MODE over the assembled feature diff. The anti-relitigation preamble (report ONLY emergent cross-task issues, NOT what the `/implement` per-task panel already forced fixed) and the emergent-issue checklist (the cross-task categories — security holes, assembled-data-flow performance, duplication/divergence, architectural drift — each naming the `Category` its findings carry, plus the `## Finding N` output contract) are injected VERBATIM into every finder brief by `render-agent-brief`; the orchestrator does not assemble or paraphrase them.

### 2.1 — Finder-existence check (graceful degradation)

Before dispatching, check which finders exist. For each of the five finders, an agent file is present when `.claude/agents/<finder>.md` exists. Skip any finder whose agent file is ABSENT and note it for the report's "Finders skipped (not installed)" line — a missing finder is never fatal (graceful degradation; mirror how `/audit` notes missing agents). Carry the PRESENT-finders list and the SKIPPED-finders list forward: PHASE 3's `route-refutation --finders` takes the present list, and PHASE 4's `render-report --finders` / `--finders-skipped` take both. If ALL five are missing, tell the user to re-run `update.sh` to (re)generate the reviewer agents and end the turn.

### 2.2 — Build each finder brief

For each PRESENT finder, render its brief, passing the scope-block file and the per-finder scratch temp path:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-review"
.devforge/lib/review_helper render-agent-brief --agent <finder> --scope-block "$WORKDIR/scope-block.txt" --references-dir .claude/commands/review/references --tmp-path "$WORKDIR/tmp-<finder>.md"
```

`render-agent-brief` reads `$WORKDIR/scope-block.txt` and the two reference files under `--references-dir` (`.claude/commands/review/references` — the installed location). `--tmp-path PATH` sets the EXACT path the brief tells the finder to write its findings to; pass `"$WORKDIR/tmp-<finder>.md"` so the temp lands in `$WORKDIR` (outside the repo). It assembles the brief in this order: the anti-relitigation preamble, the emergent-issue checklist (which already carries the full `## Finding N` output contract), the per-finder focus block, the scope block, and the closing Bash-write reminder. Pass the rendered brief as the Task tool PROMPT. Do NOT save briefs to extra files; pass the brief text straight to the Task prompt. Dispatching with `subagent_type: <finder>` ALREADY loads that finder's persona (`.claude/agents/<finder>.md`) as the subagent's system context — so do NOT prepend or re-inline the persona file into the brief; the brief carries only the review-specific instructions on top of it. The brief (via `--tmp-path`) instructs the finder to write its findings to `$WORKDIR/tmp-<finder>.md` in the fixed parseable `## Finding N` format the output contract specifies (so the helper can regex-parse them), and to write `# Status: failed` + a `# Reason:` line on partial failure, or `# Finding count: 0` when it finds nothing.

### 2.3 — Batched parallel dispatch

To avoid the context-exhaustion failure mode, dispatch in TWO batches, not all five at once. Each batch is multiple Task calls issued in a single turn (true parallel); wait for the batch to complete before the next.

- **Batch A** (parallel): `code-reviewer` + `architect` + `qa-reviewer` → each writes `$WORKDIR/tmp-<finder>.md` (the `--tmp-path` each brief carries).
- **Batch B** (parallel): `security-reviewer` + `performance-analyst` → each writes `$WORKDIR/tmp-<finder>.md`.

Only dispatch finders that exist (PHASE 2.1); skip the missing ones (already noted for the report). The finders are read-only and carry `Bash` but not `Write` in their tool allowlist, so each writes its `$WORKDIR/tmp-<finder>.md` via Bash shell redirection (the closing reminder in the brief gives the exact `cat > … << 'EOF'` command) — no Write tool needed.

### 2.4 — Consume + validate per finder, then combine

Stream finder outputs through the helper one at a time — do NOT load all findings from all finders into context at once. For each PRESENT finder that wrote a temp file, parse it, extract the `findings` array, then validate that array against the actual source:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-review"
.devforge/lib/review_helper consume-tmp --tmp "$WORKDIR/tmp-<finder>.md" --agent <finder> > "$WORKDIR/parsed-<finder>.json"
# Extract the .findings array from the parsed dict into a bare JSON array:
python3 -c "import json; print(json.dumps(json.load(open('$WORKDIR/parsed-<finder>.json'))['findings']))" > "$WORKDIR/findings-<finder>.json"
.devforge/lib/review_helper validate-findings --findings "$WORKDIR/findings-<finder>.json" --repo-root . > "$WORKDIR/validated-<finder>.json"
```

`consume-tmp` reads the finder temp file (`--tmp`) and regex-parses it into a result dict with `status` (`complete` / `clean` / `failed` / `missing`) and a `findings` array. `validate-findings` requires a BARE JSON array of finding dicts (it rejects a dict with exit 2), so extract `.findings` from the parsed dict first — the `python3 -c` line above does that. When `status` is `failed` or `missing`, record `{name: <finder>, reason: <reason>}` so you can note it, and skip the finder (its `findings` array is empty, so it contributes nothing). `validate-findings` runs the anti-hallucination guard — file exists, line in range, evidence non-empty, pattern present, evidence quote grounded — and emits, per finder, a `passed` array (the findings that survived) plus a `discard_counts` tally. (`--repo-root .` is the repo root for resolving relative paths. Pass `--source-root <rel>` ONLY when the project's Source Root is a SUBDIRECTORY of the repo — e.g. `--source-root src` — so the validator resolves finding paths against it; for a standalone `source_root == "."` install, omit `--source-root`. This is the validator's optional repo-subdir flag, distinct from `resolve-feature-scope`'s absolute `--source-root`.)

### 2.5 — Design-fidelity conformance (CONDITIONAL — fires only when the feature has a design reference + manifest)

This sub-step adds the runtime design-fidelity check the 5-finder ensemble does not perform. It DISPATCHES `design-auditor` ONLY when BOTH a `design/reference.html` (the workspace-root design artifact the feature's UI implements against) AND a `specs/[feature]/design-manifest.json` (the per-element disposition manifest `/breakdown` produces) exist. When `design/reference.html` is absent, this feature is not UI-against-a-reference work — skip the sub-step SILENTLY. When `design/reference.html` is present but the manifest is absent, a design reference exists yet the manifest was not produced — emit a loud WARN naming the void runtime-conformance guarantee, then skip the dispatch (the mechanical three-branch guard below). Only when both are present does this sub-step dispatch `design-auditor`. `design-auditor` runs the RUNTIME conformance half only (computed-style diff for the tokenizable axes + screenshot diff scoped to MATCH regions, scoped per the manifest disposition); the STATIC provenance half (no hardcoded color literals / no `var(--x, <literal>)` fallbacks) is a separate write-time gate at `/implement` and is NOT re-run here.

**Existence guard.** Check `design/reference.html` and `specs/[feature]/design-manifest.json` mechanically (substitute `[feature]` with the resolved feature dir):

```bash
test -f design/reference.html && echo HAS_REF
test -f specs/[feature]/design-manifest.json && echo HAS_MANIFEST
```

Branch on the result:

- **Neither `HAS_REF`** (no `design/reference.html`) → this is a genuine non-UI feature, not design-against-a-reference work. Skip to the combine step below SILENTLY (no WARN — a non-UI feature must never trip this).
- **`HAS_REF` but no `HAS_MANIFEST`** (a `design/reference.html` is present but this feature's `specs/[feature]/design-manifest.json` is absent) → emit a loud, operator-visible WARN: this feature has a design reference but no design-manifest, so the `design-auditor` runtime design-fidelity check will NOT run here and visual drift from `design/reference.html` is unchecked at review time. The remedy is to re-run `/breakdown` PHASE 2.5 to produce this feature's manifest. THEN skip to the combine step below — this is a WARN, not a halt; do NOT dispatch `design-auditor`, and do NOT add it to the present-finders list or the skipped-finders list.
- **`HAS_REF` and `HAS_MANIFEST`** (both present) → proceed. Then check `.claude/agents/design-auditor.md` exists — if it is absent, skip the dispatch and note `design-auditor` for the report's "Finders skipped (not installed)" list (the same graceful-degradation path as 2.1; a missing agent is never fatal).

**Dispatch.** Dispatch `design-auditor` with `subagent_type: design-auditor` — its persona (`.claude/agents/design-auditor.md`) is loaded by the dispatch and already carries the full hybrid mechanism, the manifest-scoped comparison, and the Chrome-MCP availability probe, so the brief stays thin. Pass a brief that names the assembled-feature scope (the same `$WORKDIR/scope-block.txt` the finders received), the design reference path (`design/reference.html`), and the manifest path (`specs/[feature]/design-manifest.json`), and instructs the agent to write its findings to `$WORKDIR/tmp-design-auditor.md` in the same `## Finding N` format the other finders use (so `consume-tmp` can parse it), with `# Finding count: 0` when it finds no mismatch and `# Status: failed` + a `# Reason:` line on partial failure. When Chrome MCP is unavailable the agent declares runtime fidelity NOT machine-covered (per its Rule 1) rather than failing — surface that declaration in the report; it is not a blocker.

**Consume + validate** exactly as the finders are in 2.4 — including the same `validate-findings --source-root <rel>` rule (pass it only when the project's Source Root is a repo subdirectory) — so its survivors join `$WORKDIR/validated.json` on the SAME path:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-review"
.devforge/lib/review_helper consume-tmp --tmp "$WORKDIR/tmp-design-auditor.md" --agent design-auditor > "$WORKDIR/parsed-design-auditor.json"
python3 -c "import json; print(json.dumps(json.load(open('$WORKDIR/parsed-design-auditor.json'))['findings']))" > "$WORKDIR/findings-design-auditor.json"
.devforge/lib/review_helper validate-findings --findings "$WORKDIR/findings-design-auditor.json" --repo-root . > "$WORKDIR/validated-design-auditor.json"
```

When this sub-step runs, add `design-auditor` to the PRESENT-finders list carried forward (PHASE 3's `route-refutation --finders` and PHASE 4's `render-report --finders`) so its findings are refuted and reported on the same path as the ensemble's. When it is skipped (no reference/manifest, or the agent absent), do NOT add it — the present-finders list is unchanged.

### 2.6 — Combine validated findings

After every present finder AND (when 2.5 ran) `design-auditor` are validated, concatenate the `passed` array out of every `$WORKDIR/validated-<finder>.json` dict into one combined bare array and write it to `$WORKDIR/validated.json`:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-review"
python3 -c "import json,glob; out=[]; [out.extend(json.load(open(p)).get('passed',[])) for p in sorted(glob.glob('$WORKDIR/validated-*.json'))]; print(json.dumps(out))" > "$WORKDIR/validated.json"
```

This combined array is the working list the refutation pass (PHASE 3) reads — cross-examination operates on every finder's survivors in one list. **If `$WORKDIR/validated.json` is an empty array `[]`** (no finder produced a grounded finding), there is nothing to refute: SKIP PHASE 3 entirely (do not call `route-refutation` — there is no `refutation-routes.json` in this branch), write an empty partition to `$WORKDIR/partition.json` yourself, and proceed straight to PHASE 4 with an empty refuters list:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-review"
printf '%s' '{"confirmed": [], "dismissed": [], "uncertain": [], "contested": []}' > "$WORKDIR/partition.json"
```

In the PHASE-4 `render-report` call, pass `--refuters ""` (no refuter ran); `render-inline-summary` does not accept a `--refuters` flag, so omit it there. Every other flag is unchanged. The report then renders a clean, no-findings feature review.

## PHASE 3 — Refutation (cross-examination)

```bash
.devforge/lib/review_helper check-status-and-flip --feature-dir <feature> --to phase3
```

Refutation runs ONCE on the deduped working list, AFTER validation and BEFORE the report. Its job is to invert the pipeline default from "assume a bug" to "assume correct unless proven": each finding is cross-examined by a non-author refuter whose default verdict is NOT-a-bug, and only the survivors flow to the report headline. The refuters are `/audit`'s four priority agents — `code-reviewer`, `architect`, `qa-reviewer`, `security-reviewer`. **`performance-analyst` and `design-auditor` are FINDERS ONLY and NEVER refuters** — both are absent from the refuter priority list by design (a specialist surfaces findings — perf, or design fidelity — and a generalist refutes them), so a finding either authored still routes to the first non-author priority refuter, and neither is ever assigned to refute. Read `.claude/commands/review/references/refutation-preamble.md` in full now — it is the refuter brief text and the verdict output contract, injected verbatim by `render-verify-brief`.

The four steps below are a per-refuter dispatch loop.

### 3.1 — Route each finding to a non-author refuter

Pass the working list plus the PRESENT-finders list (PHASE 2.1, as a comma-separated list — e.g. `code-reviewer,architect,qa-reviewer,security-reviewer,performance-analyst`) and capture the routing map:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-review"
.devforge/lib/review_helper route-refutation --findings "$WORKDIR/validated.json" --finders "<present-finders-csv>" > "$WORKDIR/refutation-routes.json"
```

`route-refutation` groups the working list by each finding's `agent` (the authoring finder) and assigns each group the FIRST present finder, by the fixed priority order `[code-reviewer, architect, qa-reviewer, security-reviewer]`, that is NOT the author. `performance-analyst` and `design-auditor` are not in that priority list, so neither is ever selected as a refuter even when present — but a finding either authored is still routed (it falls through to the first priority refuter ≠ author). Stdout (captured to `$WORKDIR/refutation-routes.json`) is a list of `{refuter, findings}` groups — each group is one refuter and the bare-array subset of findings routed to it. When the author is the only present finder, that sole finder self-refutes (degraded independence — note it); the helper owns that edge case. On a non-zero exit, copy the helper's stderr VERBATIM and end the turn.

### 3.2 — Dispatch each refuter over its routed subset, in batches

For each `{refuter, findings}` group, write that group's `findings` subset to a scratch file (a one-line `python3 -c` extraction from `$WORKDIR/refutation-routes.json`) and render that refuter's brief over its assigned subset:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-review"
.devforge/lib/review_helper render-verify-brief --findings "$WORKDIR/refute-<refuter>.json" --refuter <refuter> --references-dir .claude/commands/review/references --scope-block "$WORKDIR/scope-block.txt" --source-root <source-root> --tmp-path "$WORKDIR/verdicts-<refuter>.md"
```

`render-verify-brief` assembles the refuter prompt — the refutation preamble (read verbatim from `.claude/commands/review/references/refutation-preamble.md` under `--references-dir`, the installed location) plus the assigned findings to cross-examine — reading the pre-rendered scope block from `$WORKDIR/scope-block.txt` (the same file the finder briefs used). `--tmp-path` sets the EXACT path the brief tells the refuter to write its verdicts to; pass `"$WORKDIR/verdicts-<refuter>.md"`. Substitute `<source-root>` with the `source_root` from `$WORKDIR/preflight.json`. Pass the rendered brief as the Task tool PROMPT. Dispatching with `subagent_type: <refuter>` ALREADY loads that finder's persona — so do NOT prepend or re-inline the persona; the refutation preamble in the brief carries only the cross-examination instructions on top of it. The brief instructs the refuter to write its fixed-format `## Verdict N` markdown to `$WORKDIR/verdicts-<refuter>.md` via Bash shell redirection (the refuter is a finder carrying `Bash`, so it writes the file exactly as the finders write `$WORKDIR/tmp-<finder>.md` in PHASE 2 — no Write tool needed). **Dispatch the refuter groups in batches** (mirroring the PHASE 2.3 Batch pattern — multiple Task calls in a single turn, wait for the batch before the next); do not fan out all refuter groups at once. Each refuter judges ONLY its routed findings (a bounded set), not the whole working list. On a non-zero `render-verify-brief` exit, copy the helper's stderr VERBATIM and end the turn.

### 3.3 — Parse each refuter's verdicts, then merge

For each refuter dispatched, parse its verdict file into a verdict array, then concatenate all refuters' parsed arrays into one bare array:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-review"
.devforge/lib/review_helper consume-verdicts --verdicts "$WORKDIR/verdicts-<refuter>.md" --refuter <refuter> > "$WORKDIR/parsed-verdicts-<refuter>.json"
# After every refuter is parsed, extract each .verdicts array and concatenate into ONE bare array:
python3 -c "import json,glob; out=[]; [out.extend(json.load(open(p)).get('verdicts',[])) for p in sorted(glob.glob('$WORKDIR/parsed-verdicts-*.json'))]; print(json.dumps(out))" > "$WORKDIR/verdicts.json"
```

`consume-verdicts` regex-parses one refuter's fixed-format markdown verdict file (the `## Verdict N` blocks the refutation contract specifies) into a DICT carrying `status` (`complete` / `failed` / `missing`) and a `verdicts` array. Pass `--refuter <refuter>` so a verdict missing the `# Refuter:` header is still attributed. The `python3 -c` line extracts each parsed dict's `.verdicts` array and concatenates every refuter's verdicts into `$WORKDIR/verdicts.json` — the merged verdict array `apply-verdicts` consumes. When a refuter's `status` is `failed` or `missing`, its `verdicts` array is empty so it contributes nothing to the merge; the findings that refuter was routed are then absent from the verdict set, and `apply-verdicts` handles an unjudged finding per its own contract. On a non-zero `consume-verdicts` exit, copy the helper's stderr VERBATIM and end the turn.

### 3.4 — Apply the verdicts and partition

Partition the FULL working list against the merged verdicts:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-review"
.devforge/lib/review_helper apply-verdicts --findings "$WORKDIR/validated.json" --verdicts "$WORKDIR/verdicts.json" > "$WORKDIR/partition.json"
```

`apply-verdicts` reads the SAME `$WORKDIR/validated.json` working list PHASE 3.1 routed (NOT a refutation-derived subset) and the merged verdicts, keys each verdict to its working-list finding by the `(file, line, pattern, agent)` tuple, and partitions category-aware per the D7 routing. It prints a DICT (captured to `$WORKDIR/partition.json`) with four buckets:

- `confirmed` — survivors the refuter demonstrated as genuine emergent defects; they earn the report headline.
- `dismissed` — the default verdict on undemonstrable findings; they go to the report's Dismissed / Worth-a-Glance appendix. (A dismissed `[CONSTITUTION-VIOLATION]` does NOT land here — see `contested`.)
- `uncertain` — a finding the refuter could not resolve that is NOT high-stakes (its category is not `security` AND it carries no `[CONSTITUTION-VIOLATION]` tag); it rides the Dismissed / Worth-a-Glance appendix. (A high-stakes uncertain finding goes to `contested` and the headline instead — see below.)
- `contested` — HIGH-stakes findings the refuter could not confirm: a `security` finding or any `[CONSTITUTION-VIOLATION]` finding the refuter returned `uncertain` on, PLUS any `dismiss` verdict on a grounded `[CONSTITUTION-VIOLATION]`. `apply-verdicts` tags each `[CONTESTED]`. These are surfaced IN the report headline, flagged — never buried, because a missed cross-task security hole or a wrongly-dismissed constitution violation is more costly than a false alarm.

The helper owns the verdict→bucket partition and the category routing; the orchestrator does not re-derive verdicts. On a non-zero `apply-verdicts` exit, copy the helper's stderr VERBATIM and end the turn.

## PHASE 4 — Report + summary

```bash
.devforge/lib/review_helper check-status-and-flip --feature-dir <feature> --to phase4
```

Capture today's date, then render the report from the partition:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-review"
DATE="$(date +%Y-%m-%d)"
.devforge/lib/review_helper render-report --partition "$WORKDIR/partition.json" --feature <feature> --date "$DATE" --finders "<present-finders-csv>" --refuters "<refuters-csv>" --source-root <source-root> --framework "<framework>" --scope-files <file-count> --finders-skipped "<skipped-finders-csv>"
```

`render-report` reads `$WORKDIR/partition.json` (the four buckets from PHASE 3.4) directly — there is no separate report-dict bundle. It renders the full review markdown (skeleton documented in `.claude/commands/review/references/report-format.md`) and writes it to `specs/[feature]/review.md` via an atomic write, OVERWRITING any prior `review.md` (idempotent). The flags:

- `--partition "$WORKDIR/partition.json"` — the apply-verdicts buckets.
- `--feature <feature>` — the resolved feature dir; `review.md` is written here.
- `--date "$DATE"` — `YYYY-MM-DD` (required for deterministic output; the helper never calls the clock).
- `--finders "<present-finders-csv>"` — the PRESENT finders invoked (PHASE 2.1), comma-separated.
- `--refuters "<refuters-csv>"` — the refuter agents that actually ran (the distinct `refuter` values from `$WORKDIR/refutation-routes.json`), comma-separated.
- `--source-root <source-root>` — the Source Root from `$WORKDIR/preflight.json`.
- `--framework "<framework>"` — the Framework / Language from `$WORKDIR/preflight.json`.
- `--scope-files <file-count>` — the `file_count` from `$WORKDIR/scope.json` (PHASE 1).
- `--finders-skipped "<skipped-finders-csv>"` — the finders skipped because their agent file was absent (PHASE 2.1), comma-separated (omit or pass empty when none).

The report leads with CONFIRMED findings (a force-ranked Top Priorities list + a by-file/by-category grouped listing), surfaces high-stakes `[CONTESTED]` findings IN that headline flagged, and drops dismissed + low-stakes uncertain findings to a `## Dismissed / Worth a Glance` appendix. It is FINDINGS ONLY — no verdict line. Stdout is a JSON ack `{path, confirmed, contested, dismissed, uncertain}`; the `path` is the written `specs/[feature]/review.md`. On a non-zero exit, copy the helper's stderr VERBATIM and end the turn.

Then render the inline summary and print it VERBATIM to the user:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-review"
.devforge/lib/review_helper render-inline-summary --partition "$WORKDIR/partition.json" --feature <feature> --finders-skipped "<skipped-finders-csv>"
```

`render-inline-summary` reads the same `$WORKDIR/partition.json` and prints the count-first `## Review Complete` block — findings by severity, the confirmed / contested / dismissed / uncertain counts, finders skipped, and the findings-only reminder. Copy the helper's stdout VERBATIM into your final user-facing message as a fenced code block (this follows the count-first audit-format discipline).

Then mark the run complete so an interrupted re-run can distinguish a finished review from a stopped one:

```bash
.devforge/lib/review_helper check-status-and-flip --feature-dir <feature> --to phase4 --status complete
```

Then WIP-commit `/review`'s own artifacts so the work is git-safe at this step. Run this UNCONDITIONALLY (every completed `/review` run wrote `review.md` in PHASE 4):

```bash
.devforge/lib/artifact_helper commit-artifacts --paths '["specs/<feature>/review.md", "specs/<feature>/review-state.json"]' --label 'review: <NNN>-<slug>'
```

Substitute `<feature>` with the resolved feature dir and `<NNN>-<slug>` with the feature id. `commit-artifacts` stages ONLY the named paths and makes a `[WIP] review: <NNN>-<slug>` commit in the INSTALL repo (never the wrapper-mode source/product repo). It is FAIL-SOFT: a git staging or commit failure warns on stderr and exits 1 (non-fatal — the report is already written, so note the warning and CONTINUE; do NOT end the turn); "nothing to commit" (paths already staged or absent) exits 0 silently as a benign no-op. The `[WIP]` commit reads only the named `specs/[feature]/` paths, NOT `$WORKDIR`, so it is safe to run before the scratch cleanup. The `[WIP]` commit folds into `/finalize`'s squash, leaving the final PR unchanged.

Then point the user to the next step: tell them `specs/[feature]/review.md` was written (findings only) and WIP-committed, and the next command is `/verify` — which consumes `review.md` and folds its findings into the acceptance-criteria verdict.

Then, ONLY when the report's confirmed-or-high-stakes findings set is non-empty (the inline summary just printed in PHASE 4.3 showed a non-zero `confirmed` or `contested` count — the same set the headline surfaced; use that printed count, do not re-read `$WORKDIR/partition.json`), ALSO offer the user a two-arm fix-or-file choice for those findings, ALONGSIDE the `/verify` next-step (it does not replace it — `/review` still points to `/verify`): **(A)** run `/fix` to remediate the surfaced findings now (a gated remediation loop reusing `/implement`'s back-half verify + review-panel + commit), or **(B)** file a bug to defer. `/review` only PROPOSES — it never runs `/fix` itself and writes no `bugs/` file (it stays findings-only); the user types `/fix` to take arm A, or files a bug to take arm B. When the report is findings-empty (both the `confirmed` and `contested` counts are zero), propose NOTHING here — no `/fix` offer on a clean report.

Finally, clean up the scratch directory in one step — `render-inline-summary` (PHASE 4.3) was the last reader of `$WORKDIR/partition.json` and the `commit-artifacts` step above reads only the `specs/[feature]/` paths, so nothing else needs the scratch:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-review"
rm -rf "$WORKDIR"
```

## Important rules

1. **Findings only, NO verdict** — `/review` never renders a pass/fail, an approval, or a "ready to ship" line. The verdict is `/verify`'s job; `/review` produces `specs/[feature]/review.md` and `/verify` consumes it.
2. **`review.md` is a pipeline artifact** — it feeds `/verify` (which folds its findings into the verdict and warns if it is missing) and `/audit`'s recurring-issue scan (which globs recent `specs/*/review.md` files). It must stay a markdown file at `specs/[feature]/review.md`.
3. **Emergent cross-task focus** — the finders report ONLY issues that emerge from the INTERACTION of multiple tasks, NOT what the `/implement` per-task panel already forced clean on each task's own diff. This is enforced by the anti-relitigation preamble injected into every finder brief; the refutation pass dismisses any single-task re-flag that slips through as undemonstrable-at-feature-scope.
4. **Idempotent** — re-running `/review` on the same feature OVERWRITES `specs/[feature]/review.md` (the helper's atomic write); there is no per-day suffixing — one feature, one review report.
5. **Constitution violations are always Critical** — never downgraded, regardless of confidence; a `[CONSTITUTION-VIOLATION]` the refuter dismissed is surfaced `[CONTESTED]` in the headline, never buried.
6. **Evidence-first** — every finding must be grounded in a verbatim quote from real cross-task code; `validate-findings` discards ungrounded ones, and the refutation pass cross-examines each survivor before it reaches the headline.
7. **Wrapper-mode aware** — finders read source files from the resolved Source Root (`--source-root` to `resolve-feature-scope`; `--install-root` for wrapper-mode path prefixing); `specs/[feature]/` always lives at the workspace root.
8. **Graceful degradation** — a **finder** whose `.claude/agents/<name>.md` is absent is skipped (PHASE 2.1) and noted (the report's "Finders skipped" line), never fatal; only ALL five mandatory ensemble finders missing stops the run with an `update.sh` re-run prompt. The conditional `design-auditor` (PHASE 2.5) is NOT one of the five — when it is absent (or its design reference/manifest is absent) the run continues without it; design-auditor absence alone never stops the run. There is no separate refuter-existence check: because `route-refutation --finders` receives only the present-finders list, an absent agent simply never serves as a refuter — refuter absence is handled automatically.
9. **Read-only on source** — no source modifications, no fixes. `/review` does WIP-commit its OWN artifacts (`review.md` + `review-state.json`) via `artifact_helper commit-artifacts` at the end of PHASE 4 — an install-repo-only, fail-soft `[WIP]` commit that folds into `/finalize`'s squash; it never commits or modifies source.
10. **Cleanup is last** — all intermediate scratch lives in `$WORKDIR` (`${TMPDIR:-/tmp}/forge-review`), outside the repo, and is swept by the single `rm -rf "$WORKDIR"` at the end of PHASE 4 (after the inline summary), never mid-run.
