---
name: verify
description: Post-implementation acceptance-criteria verification + assembled mechanical checks for one feature. Runs after `/review` drains a feature's tasks and before `/summarize`/`/finalize`. Proves each AC item PASS/FAIL/PARTIAL (via the ac-verifier agent or code-reading, per `ac_verification_mode`), runs the assembled-feature type-check/lint/build/test together as a REPORT, folds in `/review`'s findings, renders the single APPROVED / NEEDS WORK / REJECTED verdict to `specs/[feature]/verification.md`, and on APPROVED flips the spec `**Status**:` to Complete + ticks the passed AC boxes.
argument-hint: '[spec-file]'
disable-model-invocation: true
---

# /verify — Acceptance-Criteria Verification + Verdict

`/verify` is the pipeline step run after `/review` and before `/summarize`/`/finalize`. It owns the ONE job nothing else in the pipeline owns: **the verdict**. `/review` is findings-only; `/verify` is where the spec's acceptance criteria are proven, the assembled feature is mechanically checked together (the cross-task version of `/implement`'s per-task gate), `/review`'s findings are folded in, and a single APPROVED / NEEDS WORK / REJECTED verdict is rendered and acted on. State + render shape are owned by `.devforge/lib/verify_helper`; the orchestrator composes values via verb subcommands and dispatches the `ac-verifier` agent.

**`/verify` OWNS the verdict — unlike `/review`, which produces findings only.** `/verify` does NOT run a finder ensemble or a refutation pass — that is `/review`'s job. `/verify` relies on `/review` for cross-task code-quality / consistency reasoning and adds three things on top: AC conformance, assembled mechanical checks, and the verdict. It does NOT fix code (it reports + decides) and it does NOT re-review.

Usage: `/verify` (auto-resolve the most-recently-modified `specs/NNN-*` feature) · `/verify specs/001-auth` or `/verify specs/001-auth/spec.md` (an explicit feature dir or a spec file inside it).

## Maintainer note

This file lives at `src/commands/verify/main.md` in the AIDevTeamForge template repo and is the SSOT for the `/verify` command. Do NOT inject project-specifics — this spec is substituted + emitted into target projects by the build. Helper paths use the installed `.devforge/lib/...` location because that's where they resolve at runtime in the target project. Reference-file paths are written author-relative (`references/<file>.md`); the emitter rewrites them to `.claude/commands/verify/references/<file>.md` at install time.

## Outputs of this command

The files this command writes under the repo are:

- `specs/[feature]/verification.md` — the rendered verification report (AC table, code-quality block, folded review findings, issues, and the verdict). Produced by the helper's `render-report` verb in PHASE 5. Idempotent: re-running `/verify` on the same feature OVERWRITES `verification.md` (the helper does an atomic write).
- `specs/[feature]/spec.md` — **mutated only on an APPROVED verdict** (PHASE 6): the spec `**Status**:` line flips to `Complete` and the passed AC checkboxes tick `- [ ]` → `- [x]`. This is the deliberate write-back that `/summarize` and `/finalize` gate on. On NEEDS WORK / REJECTED the spec is left unchanged.
- `bugs/NNN-<slug>.md` — **written only on a NEEDS WORK verdict** (PHASE 9), one file per issue the user elects to file, in the `.devforge/storage-rules.md` bug format (`Source: verify`). Sequential `NNN` numbering scanned from the existing `bugs/` directory.

Per-feature run state lives in `specs/[feature]/verify-state.json` (helper-owned, advanced via `check-status-and-flip --feature-dir <feature>`).

### Intermediate scratch files (orchestrator-written, helper-consumed) — all under `$WORKDIR`

The helper cannot dispatch agents (a subprocess has no Task/MCP tools), so the orchestrator captures each verb's stdout to an intermediate scratch file that the next verb reads (most verbs take a `--<name> <path>` flag, not stdin). All live under `$WORKDIR` (`${TMPDIR:-/tmp}/forge-verify`) and are scratch state for one run — the whole directory is removed by the single PHASE-9 `rm -rf "$WORKDIR"`. Because `$WORKDIR` is outside the work tree, the files need no leading dot and no gitignore handling.

- `$WORKDIR/preflight.json` — the `preflight` stdout (`source_root`, `framework`, `language`, `wrapper_mode`, …). Written in PHASE 0, read by the orchestrator for the `--source-root` / `--framework` values it threads into later verbs.
- `$WORKDIR/scope.json` — the `resolve-feature-scope` stdout (`files`, `files_for_finders`, `file_count`, `scope_block`). Written in PHASE 1, read by the orchestrator to extract the changed-file count + the file list.
- `$WORKDIR/files.json` — the `files_for_finders` ARRAY extracted from `$WORKDIR/scope.json`. Written in PHASE 1, passed to `check-hygiene --files` (which takes a file PATH containing a JSON array). The same array, inlined as a single-line JSON string, is the `verify-touched --files` argument (which takes an inline JSON-array STRING, not a path).
- `$WORKDIR/review.json` — the `read-review-findings` stdout (`missing`, `confirmed`, `contested`, `summary`). Written in PHASE 2, passed to `compute-verdict --review-findings`, `render-report --review-findings`, and `render-inline-summary --review-findings`.
- `$WORKDIR/ac-config.json` — the `read-ac-config` stdout (`ac_verification_mode`, `ac_runtime_url`, `ac_runtime_api_base`, `ac_runtime_cli_command`). Written in PHASE 3, read by the orchestrator to pick the AC-mode branch and to compose the `ac-verifier` brief.
- `$WORKDIR/acs.json` — the `parse-acs` stdout (the structured AC list — `id`, `text`, `checked`, `subsection` per AC). Written in PHASE 3, passed to `merge-ac-results --acs`.
- `$WORKDIR/ac-report.md` — the `ac-verifier` agent's `## AC Verification Report` (its `### Results` table). Written BY THE AGENT via Bash redirection in PHASE 3, consumed by `merge-ac-results --agent-report`.
- `$WORKDIR/ac-results.json` — the `merge-ac-results` stdout (the AC list extended with `status` + `evidence` per AC). Written in PHASE 3, passed to `compute-verdict --ac-results`, `render-report --ac-results`, `render-inline-summary --ac-results`, and `flip-spec-status --ac-results`.
- `$WORKDIR/hygiene.json` — the `check-hygiene` stdout (`scope_creep`, `leftover_artifacts`, `scope_creep_checked`, `files_checked`, `files_unreadable`). Written in PHASE 4, passed to `compute-verdict --hygiene` and `render-report --hygiene`.
- `$WORKDIR/verdict.json` — the `compute-verdict` stdout (`verdict`, `reasons`, `blockers`). Written in PHASE 5, passed to `render-report --verdict` and `render-inline-summary --verdict`.
- `$WORKDIR/issues.json` — the bug-issue array the orchestrator composes from the verdict blockers + AC failures + folded findings on a NEEDS WORK verdict. **Orchestrator-written via the Write tool** (NOT a helper-verb stdout — no verb produces it), in PHASE 9, passed to `file-bugs --issues`. Skipped entirely on a `none` election (the `file-bugs` call is not made — see PHASE 9 for the shape).

## Reference files

- `.claude/commands/verify/references/report-format.md` — the `verification.md` skeleton the helper produces (orientation for PHASE 5; the helper's `render-report` owns the actual render — do not hand-author the report).

## Helper interaction model

Every mechanical step is a normal Bash tool call to `.devforge/lib/verify_helper <verb> ...` (and ONE call to the installed `.devforge/lib/implement_helper verify-touched` in PHASE 4, reused as a report). Each verb prints JSON (or a rendered block) to stdout. Most verbs that consume a prior verb's output take a `--<name> <path>` flag (not stdin), so capture stdout to the named `$WORKDIR/*.json` scratch file with `>` and pass that path into the next call — the per-phase fences below show the exact redirects. Re-establish `WORKDIR="${TMPDIR:-/tmp}/forge-verify"` at the top of every Bash block that touches scratch (the variable does not survive across Bash calls — see PHASE 0). On any non-zero exit, copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then follow the recovery note for that phase. The helper owns file structure, validation, and atomic writes; the orchestrator owns the `ac-verifier` dispatch, the MCP-availability probe, user-facing prose, and phase pacing.

## PHASE 0 — Preflight + feature resolution + scratch

Cheapest guards first; preflight before any feature I/O.

### 0.1 — Preflight gate

```bash
.devforge/lib/verify_helper preflight --workspace-root . > /tmp/verify-preflight-check.json
```

`preflight` checks the 4-command setup chain (`/init-forge → /generate-docs → /configure → /constitute`) and the populated-constitution guard. It ALWAYS writes its JSON context block to stdout BEFORE any gate check, then exits **2** with a user-facing stderr message when (a) a setup-chain artefact is missing or (b) `constitution.md` is absent or still carries an unpopulated sentinel. On exit 2, copy the helper's stderr VERBATIM as a fenced code block and end the turn — the user runs the named missing command first. On exit 0, the stdout JSON carries `source_root` (the project's Source Root — `.` for a standalone install, the inner project subdir in wrapper mode), `framework` (the Framework / Language string), `language`, and `wrapper_mode`. (`$WORKDIR` is not established until 0.3, so this gate call captures to a fixed `/tmp` path; 0.3 re-runs `preflight` into `$WORKDIR/preflight.json` once the scratch dir exists. `preflight` is read-only and cheap, so running it twice is harmless.) Carry `source_root` and `wrapper_mode` forward: PHASE 1 branches on `wrapper_mode` to decide whether to pass `--source-root` / `--install-root` to `resolve-feature-scope` (standalone omits both; wrapper mode passes both), PHASE 4 passes `source_root` to `check-hygiene --source-root`, and PHASE 5 passes both to `render-report`.

### 0.2 — Resolve the feature directory

Resolve the feature dir from `$ARGUMENTS`:

- When `$ARGUMENTS` names a feature directory (`specs/NNN-<slug>`) or a file inside one (e.g. `specs/001-auth/spec.md`), use that feature directory (strip a trailing filename to the `specs/NNN-<slug>` dir).
- When `$ARGUMENTS` is empty, auto-resolve the most-recently-modified `specs/NNN-*` directory (the feature most likely just finished `/review`).

If no `specs/NNN-*` directory exists, tell the user there is no feature to verify (run `/specify` → `/plan` → `/breakdown` → `/implement` → `/review` first) and end the turn. Carry the resolved feature dir forward as `<feature>` — every subsequent `--feature` / `--feature-dir` flag takes it; the spec file inside it is `<feature>/spec.md` (the `--spec` value PHASE 3 needs).

### 0.3 — Initialize run state + scratch dir

```bash
.devforge/lib/verify_helper check-status-and-flip --feature-dir <feature> --to phase0
```

`check-status-and-flip` advances `specs/[feature]/verify-state.json` to the named phase so an interrupted run can report where it stopped. Call it once at the start of each major phase with `--feature-dir <feature> --to <phase>` (`phase0` … `phase9`), and once at the very end of the run with `--to phase9 --status complete`. Keep these lightweight (one call per boundary, no parsing of the output beyond the non-zero-exit check). `--to` accepts any label, so these phase names are a convention, not a helper-enforced enum. The optional `--verdict <APPROVED|NEEDS WORK|REJECTED>` flag records the final verdict into `verify-state.json` and is passed ONLY on the terminal complete-flip (the Cleanup block) — every other phase-boundary call omits it, leaving the recorded verdict unchanged. (Note: the verb keys on `--feature-dir`, NOT `--workspace-root` — its state file is per-feature.)

Then establish + clear the scratch working directory:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
rm -rf "$WORKDIR" && mkdir -p "$WORKDIR"
```

**All intermediate scratch for this run lives in `$WORKDIR` (the fixed literal `${TMPDIR:-/tmp}/forge-verify`), OUTSIDE the repo.** The literal is `forge-verify`, NOT `forge-review` or `forge-audit` — `/review` and `/audit` may run concurrently, and a shared workdir would corrupt every run. `$WORKDIR` is outside the work tree, so the scratch files need no leading dot, no gitignore handling, and no per-file `rm` list. The `rm -rf "$WORKDIR" && mkdir -p "$WORKDIR"` clears any stale scratch from a prior crashed run.

**CRITICAL — `$WORKDIR` is a FIXED LITERAL you re-derive in every Bash block; it does NOT persist across calls.** The orchestrator runs each Bash tool call in a FRESH shell, so shell variables (including `$WORKDIR`) do NOT carry from one Bash call to the next. So every Bash block that touches scratch MUST begin by re-establishing `WORKDIR="${TMPDIR:-/tmp}/forge-verify"` and then reference `"$WORKDIR/..."`. The literal is identical in every block, so each block reconstructs the same directory.

Now re-capture the preflight context into `$WORKDIR` so later blocks can re-read its `source_root` / `framework` values (the gate already passed in 0.1; this just persists the context to the scratch dir):

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
.devforge/lib/verify_helper preflight --workspace-root . > "$WORKDIR/preflight.json"
```

## PHASE 1 — Resolve the assembled-feature scope

```bash
.devforge/lib/verify_helper check-status-and-flip --feature-dir <feature> --to phase1
```

Compute the assembled-feature diff — the union of every change the feature made, across all the WIP commits `/implement` accumulated (squashed only by `/finalize`, which has not run yet). This is the assembled surface the per-task `/implement` gate never saw together. Read `wrapper_mode` and `source_root` from `$WORKDIR/preflight.json` (PHASE 0) and branch on them:

- **Standalone install** (`source_root` is `"."`): pass `--feature <feature>` ONLY. Omit `--source-root` and `--install-root` — the helper defaults `source_root` to CWD and `install_root` to `source_root`, which is correct here.
- **Wrapper mode** (`source_root` is NOT `"."` per `preflight.json`): pass `--feature <feature> --source-root <source-root> --install-root <install-root>`. `--source-root` is the code repo (the inner project subdir, the `source_root` value); `--install-root` is the forge install root where `.devforge/` lives (the wrapper root — typically the cwd `.`). **Both flags are mandatory in wrapper mode.** If `--install-root` is omitted the helper defaults it to `source_root` — then `abs_source == abs_install`, the wrapper-mode path-prefixing never fires, and `files_for_finders` is silently NOT source-root-prefixed, so the finder paths the later verbs read from the install root point at nonexistent files. Never omit `--install-root` in wrapper mode.

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
# Standalone (source_root == "."): --feature only.
# Wrapper mode (source_root != "." per preflight.json): ALSO pass
#   --source-root <source-root> --install-root <install-root>
# so files_for_finders is source-root-prefixed, not silently left unprefixed.
.devforge/lib/verify_helper resolve-feature-scope \
  --feature <feature> \
  [--source-root <source-root> --install-root <install-root>  # wrapper mode only] \
  > "$WORKDIR/scope.json"
```

`resolve-feature-scope` runs `git diff --name-only $(git merge-base <base> HEAD)..HEAD` with `cwd = source-root` and emits JSON to stdout; the `>` redirect captures it to `$WORKDIR/scope.json`. The base ref auto-detects via `origin/HEAD → main → develop → master`; pass `--base <ref>` when auto-detection fails (the exit-2 stderr message says so). In wrapper mode the `--install-root` passed above (the forge install root where `.devforge/` lives) is what makes the emitted file paths install-root-relative — see the per-mode branch above. Stdout JSON carries `files` (sorted source-relative changed paths), `files_for_finders` (the same list, source-root-prefixed in wrapper mode), `file_count`, and `scope_block` (a pre-rendered human-readable scope summary, labelled "Verification Scope"). On a non-zero exit (not a git repo, bad ref, no auto-detectable base), copy the helper's stderr VERBATIM and end the turn.

**Empty-diff stop.** If `file_count` is `0` (HEAD == merge-base — the feature has no changes yet, or it is already squashed/merged), there is nothing to verify: tell the user the feature diff is empty (no changes between the base and HEAD, so no assembled surface to verify), clean up (`rm -rf "$WORKDIR"`), and end the turn gracefully. This is not an error — it is an empty feature.

Extract the `files_for_finders` ARRAY into its own file — `check-hygiene --files` (PHASE 4) takes a file PATH containing a JSON array, and the same array inlined as a single-line string is the `verify-touched --files` argument:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
python3 -c "import json; json.dump(json.load(open('$WORKDIR/scope.json'))['files_for_finders'], open('$WORKDIR/files.json','w'))"
```

Carry `file_count` forward for the user-facing prose.

## PHASE 2 — Read /review findings

```bash
.devforge/lib/verify_helper check-status-and-flip --feature-dir <feature> --to phase2
```

Fold in `/review`'s findings — `/review` is findings-only; `/verify` reads `specs/[feature]/review.md` and incorporates its confirmed + high-stakes `[CONTESTED]` findings into the verdict. `/verify` does NOT re-derive these findings (no finder ensemble, no refutation pass — that is `/review`'s job).

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
.devforge/lib/verify_helper read-review-findings --feature <feature> > "$WORKDIR/review.json"
```

`read-review-findings` accepts the feature directory (it appends `/review.md`) and parses `specs/[feature]/review.md` into a folded-findings dict: `missing`, `confirmed` (the confirmed-findings list), `contested` (the `[CONTESTED]`-tagged list), and `summary` (severity + partition counts). On a non-zero exit, copy the helper's stderr VERBATIM and end the turn.

**Missing-review warning (proceed weakened).** If the stdout JSON has `"missing": true`, warn the user: _no review report was found — run `/review` first for a complete verdict; proceeding with AC + mechanical checks only._ Do NOT stop — `compute-verdict` handles a missing review report as a non-blocking note (the verdict is computed from AC + mechanical + hygiene, and the missing report is recorded in the verdict reasons). Keep `$WORKDIR/review.json` and pass it forward unchanged.

## PHASE 3 — Acceptance-criteria verification

```bash
.devforge/lib/verify_helper check-status-and-flip --feature-dir <feature> --to phase3
```

Prove each AC item PASS / FAIL / PARTIAL. The verification METHOD is selected by `ac_verification_mode`; in every mode the orchestrator dispatches the `ac-verifier` agent, and the agent's `## Verification modes` section owns the per-mode behavior. `/verify` reports AC failures — it NEVER fixes them; remediation happens separately (via `/fix` for a NEEDS-WORK finding, or a fresh `/specify` → `/plan` → `/breakdown` cycle for a spec-level change), not in `/verify`.

### 3.1 — Read the AC config + parse the spec's ACs

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
.devforge/lib/verify_helper read-ac-config --root . > "$WORKDIR/ac-config.json"
.devforge/lib/verify_helper parse-acs --spec <feature>/spec.md > "$WORKDIR/acs.json"
```

`read-ac-config` reads the four `ac_*` keys from `.devforge/project-config.json` and emits `ac_verification_mode` (one of `code-only` | `tests` | `runtime-assisted` | `off`, defaulting to `off` when unset), `ac_runtime_url`, `ac_runtime_api_base`, and `ac_runtime_cli_command` (each defaulting to `""` when unset). Read the `ac_verification_mode` value — it is both the AC-mode branch selector below AND the `--ac-mode` flag PHASE 5 threads into `compute-verdict` and `render-report`. `parse-acs` parses the spec's `## Acceptance Criteria` section into a structured AC list (one dict per `- [ ] **AC-N**: …` checkbox, with `id` / `text` / `checked` / `subsection`); an empty list (no ACs in the spec) is valid, not an error.

### 3.2 — Probe Chrome MCP availability (runtime-assisted only)

When `ac_verification_mode` is `runtime-assisted`, probe Chrome DevTools MCP availability BEFORE composing the agent brief: make ONE lightweight `mcp__chrome-devtools__list_pages` call. If it returns a result, set `CHROME_MCP_AVAILABLE` to `true`; if the tool is unavailable or the call errors, set it to `false`. The agent uses `CHROME_MCP_AVAILABLE` to reclassify unobservable `frontend` items to code-reading fallback. For the other three modes (`tests`, `code-only`, `off`), do NOT probe — set `CHROME_MCP_AVAILABLE` to `false` (those modes never use the browser channel).

### 3.3 — Dispatch the ac-verifier agent

Dispatch the `ac-verifier` agent in ALL four modes. Compose its brief from the inputs its `## Input` section names — the AC list, the mode, the three runtime values, the MCP-availability flag, and the changed-files list — and instruct it to write its `### Results` report to `$WORKDIR/ac-report.md`:

- **Acceptance criteria** — the structured AC list from `$WORKDIR/acs.json` (the `id` + `text` of each AC).
- **`ac_verification_mode`** — the value from `$WORKDIR/ac-config.json`.
- **`ac_runtime_url`**, **`ac_runtime_api_base`**, **`ac_runtime_cli_command`** — the three runtime values from `$WORKDIR/ac-config.json` (each may be empty).
- **`CHROME_MCP_AVAILABLE`** — `true`/`false` from the 3.2 probe.
- **Changed files** — the `files` list from `$WORKDIR/scope.json` (the assembled-feature diff; the agent code-reads these for any AC it cannot observe at runtime).

Dispatch with `subagent_type: ac-verifier` (this loads the agent's persona from `.claude/agents/ac-verifier.md` as the subagent's system context — do NOT prepend or re-inline the persona into the brief; the brief carries only the inputs above on top of it). Instruct the agent to write its `## AC Verification Report` (its `### Results` table) to `$WORKDIR/ac-report.md` via Bash shell redirection — the agent carries `Bash`, so it writes the file with a `cat > "$WORKDIR/ac-report.md" << 'EOF' … EOF` heredoc; no Write tool needed. The four modes map to PHASE-3 behavior as:

- **`runtime-assisted`** — the agent verifies each AC against the running app (browser channel via `ac_runtime_url` for `frontend` ACs, API channel via `ac_runtime_api_base` for `backend` ACs, `ac_runtime_cli_command` to launch the runtime), and code-reads any item that cannot be observed (MCP down per `CHROME_MCP_AVAILABLE=false`, or the relevant `ac_runtime_*` value empty).
- **`tests`** — the agent verifies each AC by **code-reading** the changed files (the same per-AC method as `code-only`); it does NOT receive live test outcomes at dispatch time, because it is dispatched here in PHASE 3, before PHASE 4 runs the suite. The assembled test suite is executed **independently** by the orchestrator in PHASE 4 (the `verify-touched` test leg), and a non-`pass` mechanical status is an independent blocker that `compute-verdict` already enforces in PHASE 5 (regardless of the AC table). The fine-grained test-outcome→AC mapping is **deferred** (OQ-1 — resolve at the testForge20 e2e); the agent does NOT map PHASE-4 outcomes.
- **`code-only`** — the agent judges each AC by reading the changed files and records `PASS (code)` / `FAIL (code)` / `PARTIAL (code)`. No runtime probing, no test execution.
- **`off`** — the agent skips behavioral verification but applies a code-reading floor (a per-AC status by reading the changed files) and notes that ACs were verified by code only. The verdict explicitly flags this (and treats AC failures as advisory, not blocking — see PHASE 5).

### 3.4 — Merge the agent's results into the AC list

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
.devforge/lib/verify_helper merge-ac-results --acs "$WORKDIR/acs.json" --agent-report "$WORKDIR/ac-report.md" > "$WORKDIR/ac-results.json"
```

`merge-ac-results` reads the structured AC list (`--acs`) and the agent's markdown report (`--agent-report`), extracts the agent's `### Results` table, and emits the AC list extended with `status` (`PASS` / `FAIL` / `PARTIAL` / `MANUAL` / `PASS (code)` / `FAIL (code)` / `PARTIAL (code)`, or `UNVERIFIED` when the agent produced no row for an AC) and `evidence` (the agent's Evidence cell) per AC. On a non-zero exit (missing required flag, or the `--acs` file is not a JSON list), copy the helper's stderr VERBATIM and end the turn.

## PHASE 4 — Assembled mechanical checks + hygiene

```bash
.devforge/lib/verify_helper check-status-and-flip --feature-dir <feature> --to phase4
```

Run the assembled-feature type-check / lint / build / test together — the cross-task version of `/implement`'s per-task gate. `/verify` REUSES the installed `implement_helper verify-touched` binary, treats its result as a REPORT, and does **NOT** loop on `self_repair` — the self-repair loop is `/implement`'s job; `/verify` reports failures, never fixes.

### 4.1 — Run the assembled mechanical check (report-only)

Pass the assembled changed-files list as an inline JSON-array STRING (NOT a path — `verify-touched --files` takes the array literally, distinct from `check-hygiene --files`, which takes a file path):

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
FILES_JSON="$(cat "$WORKDIR/files.json")"
.devforge/lib/implement_helper verify-touched --files "$FILES_JSON" --root . --iteration 0 > "$WORKDIR/mechanical.json"
```

`verify-touched` resolves the source root from `PROJECT_ROOT` inside `.devforge/project-config.json` (via `--root .`), matches each touched file to its package via `PACKAGE_STACKS` (longest-path-prefix wins), and runs that package's commands in the fixed order static checks (type-check + lint) → build → tests, with `cwd = <source-root>`. **`--iteration 0`** is passed deliberately: it asks for ONE pass. Read the top-level `status` field from `$WORKDIR/mechanical.json` — it is one of `pass`, `self_repair`, `failed`, `isolation_failure`, or `tooling_unavailable`. **Do NOT re-run on `self_repair`** — capture the `status` string verbatim and carry it forward as the `--mechanical-status` value for PHASE 5 (`compute-verdict` treats any status other than `pass` / `""` as a mechanical failure that blocks APPROVED; `self_repair` here means "a check failed and would have been retried under `/implement`", which for `/verify` is a reported failure). The verb itself returns exit 0 for `pass` / `self_repair` and exit 2 for `failed` / `isolation_failure` / `tooling_unavailable`; a non-zero exit is still a valid REPORTED status (the JSON `status` is the report), so do NOT end the turn on it — read the `status`, carry it forward, and continue.

### 4.2 — Scope-creep + leftover-artifact hygiene

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
.devforge/lib/verify_helper check-hygiene --files "$WORKDIR/files.json" --scope-baseline <scope-baseline> --source-root <source-root> > "$WORKDIR/hygiene.json"
```

`check-hygiene` reads the changed-files list (`--files`, a file PATH containing the JSON array written in PHASE 1) and flags two things across the assembled diff: scope-creep (changed files outside the planned scope) and leftover artifacts (debug prints, bare TODOs, commented-out code). For `--scope-baseline`, pass `<feature>/breakdown-handoff.json` when that file exists (its tasks' `touched_files` union is the planned scope); pass the literal string `none` when it is absent (the helper then skips the scope-creep check and reports only leftover artifacts). Pass the `source_root` from `$WORKDIR/preflight.json` to `--source-root` so the changed files are read from the right tree. Stdout JSON carries `scope_creep`, `leftover_artifacts`, `scope_creep_checked`, `files_checked`, and `files_unreadable`. On a non-zero exit (missing `--files`, or it is not a JSON list), copy the helper's stderr VERBATIM and end the turn.

## PHASE 5 — Verdict + report + inline summary

```bash
.devforge/lib/verify_helper check-status-and-flip --feature-dir <feature> --to phase5
```

Compute the deterministic verdict, write `verification.md`, and print the count-first inline summary.

### 5.1 — Compute the verdict

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
.devforge/lib/verify_helper compute-verdict --ac-results "$WORKDIR/ac-results.json" --review-findings "$WORKDIR/review.json" --hygiene "$WORKDIR/hygiene.json" --mechanical-status <mechanical-status> --ac-mode <ac-mode> > "$WORKDIR/verdict.json"
```

`compute-verdict` is deterministic: it reads the merged AC results (`--ac-results`), the folded review findings (`--review-findings`), the hygiene result (`--hygiene`), the `verify-touched` status string (`--mechanical-status`, the `status` carried from PHASE 4.1), and the AC mode (`--ac-mode`, the `ac_verification_mode` from PHASE 3.1), and emits `verdict` (APPROVED / NEEDS WORK / REJECTED), `reasons` (explanation lines), and `blockers` (structured blocker dicts). **Constitution violations always block APPROVED** (D7): a confirmed `[CONSTITUTION-VIOLATION]` from the review findings forces REJECTED, and a contested one forces at least NEEDS WORK. Under `ac_verification_mode=off`, AC failures are advisory (noted in `reasons`, not blocking); under all other modes a FAIL/PARTIAL AC is a blocker. On a non-zero exit, copy the helper's stderr VERBATIM and end the turn.

### 5.2 — Render the report

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
DATE="$(date +%Y-%m-%d)"
.devforge/lib/verify_helper render-report --verdict "$WORKDIR/verdict.json" --ac-results "$WORKDIR/ac-results.json" --review-findings "$WORKDIR/review.json" --hygiene "$WORKDIR/hygiene.json" --mechanical-status <mechanical-status> --feature <feature> --date "$DATE" --ac-mode <ac-mode>
```

`render-report` reads the verdict + the AC results + the folded review findings + the hygiene result, renders the full verification markdown (skeleton documented in `.claude/commands/verify/references/report-format.md`), and writes it to `specs/[feature]/verification.md` via an atomic write, OVERWRITING any prior `verification.md`. `--feature` and `--date` are REQUIRED (the helper never calls the clock — `--date` is `YYYY-MM-DD`). Stdout is the written path. On a non-zero exit, copy the helper's stderr VERBATIM and end the turn.

### 5.3 — Print the inline summary

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
.devforge/lib/verify_helper render-inline-summary --verdict "$WORKDIR/verdict.json" --ac-results "$WORKDIR/ac-results.json" --review-findings "$WORKDIR/review.json" --mechanical-status <mechanical-status> --feature <feature>
```

`render-inline-summary` prints the count-first `## Verification Complete` block — the verdict, the AC pass/fail/unverified counts, the mechanical result, the folded-finding counts, the key reasons, and the next-step pointer. (It does NOT accept `--hygiene` or `--ac-mode` — those are `render-report`-only; the inline summary draws hygiene + mode context from the verdict's `reasons`/`blockers`, which already factor them in, rather than from the raw hygiene/mode data.) Copy the helper's stdout VERBATIM into your user-facing message as a fenced code block (this follows the count-first audit-format discipline). Read the `verdict` from `$WORKDIR/verdict.json` — it drives PHASE 6, PHASE 8, and PHASE 9.

## PHASE 6 — Spec-status flip (APPROVED only)

```bash
.devforge/lib/verify_helper check-status-and-flip --feature-dir <feature> --to phase6
```

**Only on an APPROVED verdict** — flip the spec `**Status**:` to Complete and tick the passed AC boxes. On NEEDS WORK or REJECTED, do NOTHING here (the spec status is left unchanged) and skip straight to PHASE 7.

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
.devforge/lib/verify_helper flip-spec-status --feature <feature> --ac-results "$WORKDIR/ac-results.json"
```

`flip-spec-status` FIRST cross-checks that every task file under `specs/[feature]/tasks/*.md` (excluding `README.md`) has `**Status**: Complete` or `Skipped`; only when all tasks are satisfied does it flip the spec `**Status**:` line to `Complete` and tick each passed AC's `- [ ]` → `- [x]` (a passed AC is one whose merged `status` is `PASS` or `PASS (code)`). The atomic write mutates `spec.md`. Stdout JSON carries `flipped` (bool), `blocker` (a message string, or `null` on success), `ticked` (the AC ids ticked this call), and `spec_path`. **If `flipped` is `false`**, the spec was NOT changed — report the `blocker` message to the user verbatim (e.g. a task is still `In Progress`) and keep the spec status unchanged; the verdict stays APPROVED in `verification.md` but the lifecycle flip is held until the blocker clears. On a non-zero exit, copy the helper's stderr VERBATIM and end the turn.

## PHASE 7 — Memory update

```bash
.devforge/lib/verify_helper check-status-and-flip --feature-dir <feature> --to phase7
```

Append feature-level lessons to `.devforge/memory.md` — what the ASSEMBLED feature taught, and what verification caught that the per-task `/implement` gate missed. Keep it LIGHT: feature-level only, not a per-task re-log (per-task lessons are already written by `/implement`). This is orchestrator prose-writing — use the Write tool to append a short dated entry to `.devforge/memory.md` (read the file first; append, do not overwrite). Skip silently when there is nothing feature-level worth recording.

## PHASE 8 — Present + next step

```bash
.devforge/lib/verify_helper check-status-and-flip --feature-dir <feature> --to phase8
```

Tell the user where `verification.md` was written and the next step, branched on the verdict:

- **APPROVED** — the spec is Complete (PHASE 6, unless a flip blocker was reported); next is `/summarize` then `/finalize`.
- **NEEDS WORK** — offer the user a two-arm fix-or-file choice for the blocking issues (these are ALTERNATIVES, not a pipeline): **(A)** run `/fix` to remediate the blockers now (a gated remediation loop reusing `/implement`'s back-half verify + review-panel + commit — re-running `/verify` afterward re-checks the ACs against the remediated diff), or **(B)** file bugs to defer (PHASE 9 — the batch bug-filing path below). `/verify` only PROPOSES `/fix` — it never runs it, and it writes no `bugs/` file itself except via the PHASE-9 `file-bugs` path the user elects; the user types `/fix` to take arm A, or proceeds into PHASE 9 to take arm B. Do NOT suggest re-running `/implement` here — `/implement` drains approved tasks, which does not fix a NEEDS-WORK finding; `/fix` does.
- **REJECTED** — the feature has a spec-level problem; revise the spec via `/specify` → `/plan` → `/breakdown`, then re-implement.

On APPROVED or REJECTED, skip PHASE 9 and go straight to the cleanup block below.

## PHASE 9 — Issue report + batch bug-filing (NEEDS WORK only)

```bash
.devforge/lib/verify_helper check-status-and-flip --feature-dir <feature> --to phase9
```

**Only on a NEEDS WORK verdict.** Present the blocking issues to the user (the verdict `blockers` + the failing ACs + the folded Critical/High review findings — the same set surfaced in `verification.md`), then offer to file bugs: **all** (file one bug per issue), **select** (the user names which to file), or **none** (skip filing). When the user elects to file some or all, compose the issue array and write it to scratch, then call `file-bugs`:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
DATE="$(date +%Y-%m-%d)"
.devforge/lib/verify_helper file-bugs --issues "$WORKDIR/issues.json" --bugs-dir bugs --feature-spec <feature>/spec.md --date "$DATE"
```

Compose `$WORKDIR/issues.json` as a JSON array of issue dicts and write it with the Write tool (it is orchestrator-composed — no helper verb emits it). Each dict carries `title`, `severity` (the storage-rules vocabulary `Critical` | `Warning` | `Info` — map review/AC severities to it), `description`, `expected`, `actual`, `files` (a list of `{path, detail}`), `evidence`, and `ac_ref` (`AC-N` or `N/A`):

```json
[
  {
    "title": "Order total ignores discount code",
    "severity": "Critical",
    "description": "Applying a valid discount code leaves the cart total unchanged.",
    "expected": "Total reflects the discount after the code is applied.",
    "actual": "Total is unchanged; the discount is parsed but never subtracted.",
    "files": [
      { "path": "src/cart/total.ts", "detail": "applyDiscount() computes but discards the delta" }
    ],
    "evidence": "AC-3 FAIL: expected $90.00, observed $100.00 (see verification.md)",
    "ac_ref": "AC-3"
  }
]
```

Write that array to `$WORKDIR/issues.json`, then make the `file-bugs` call above. `file-bugs` scans the existing `bugs/` directory for the highest `NNN` prefix, assigns sequential numbers from there, and writes one `bugs/NNN-<slug>.md` per issue in the `.devforge/storage-rules.md` format (`Source: verify`). `--date` is REQUIRED (`YYYY-MM-DD`). Stdout is the JSON array of paths written; report them to the user. On a non-zero exit, copy the helper's stderr VERBATIM and end the turn. When the user elects **none**, do NOT compose `issues.json` and SKIP the `file-bugs` call entirely (do not invoke it with an empty path).

## Cleanup

Clean up the scratch directory in one step — nothing else needs the scratch after the report + summary + (optional) bug-filing:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-verify"
rm -rf "$WORKDIR"
```

Then mark the run complete so an interrupted re-run can distinguish a finished verification from a stopped one, recording the run's verdict into state via `--verdict`. Use `<verdict>` — the literal APPROVED / NEEDS WORK / REJECTED value the orchestrator read from `$WORKDIR/verdict.json` in PHASE 5.3 (the `verdict` field) and has held since; the cleanup `rm -rf "$WORKDIR"` above already deleted `$WORKDIR/verdict.json`, so inline the verdict value you already hold — do NOT re-read the scratch file here:

```bash
.devforge/lib/verify_helper check-status-and-flip --feature-dir <feature> --to phase9 --status complete --verdict "<verdict>"
```

## Important rules

1. **`/verify` OWNS the verdict** — unlike `/review` (findings only), `/verify` renders the single APPROVED / NEEDS WORK / REJECTED verdict via the deterministic `compute-verdict` verb. The verdict is `/verify`'s defining job.
2. **`/verify` does NOT fix code** — it reports AC failures, mechanical-check failures, and hygiene flags, and renders a verdict; it never edits source. Remediation happens separately (via `/fix` for a NEEDS-WORK finding, or a fresh `/specify` → `/plan` → `/breakdown` cycle for a spec-level change), not in `/verify`. The `verify-touched` reuse is report-only at `--iteration 0` with NO self-repair loop.
3. **`/verify` does NOT re-review** — it has no finder ensemble and no refutation pass (those are `/review`'s job, and the `_shared` refutation engine is deliberately NOT reused here). `/verify` folds in `/review`'s already-refuted findings via `read-review-findings` and points to the `/review` report for cross-task code-quality reasoning.
4. **Constitution violations always block APPROVED** (D7) — a confirmed `[CONSTITUTION-VIOLATION]` from the review findings forces REJECTED; a contested one forces at least NEEDS WORK. `compute-verdict` enforces this structurally; never override it.
5. **`/verify` WRITES BACK to the spec** — on APPROVED (and only after the task cross-check passes), `flip-spec-status` flips `spec.md`'s `**Status**:` to Complete and ticks the passed AC boxes. This is the deliberate departure: `/verify` is the only review/verify command that mutates its input, because it owns the Complete lifecycle transition `/summarize` and `/finalize` gate on. On NEEDS WORK / REJECTED the spec is untouched.
6. **Missing review report is non-fatal** — if `specs/[feature]/review.md` is absent, warn the user (run `/review` first) and proceed with AC + mechanical + hygiene only; `compute-verdict` records the missing report in the verdict reasons.
7. **Empty feature diff is non-fatal** — `file_count == 0` (HEAD == merge-base) means there is nothing to verify; stop gracefully after cleanup (PHASE 1).
8. **Wrapper-mode aware** — in wrapper mode, `resolve-feature-scope` requires both `--source-root` (the inner code repo) AND `--install-root` (the wrapper root where `.devforge/` lives); `verify-touched --root` and `check-hygiene --source-root` each take `source_root`; `specs/[feature]/`, `bugs/`, and `verification.md` always live at the workspace root.
9. **Cleanup is last** — all intermediate scratch lives in `$WORKDIR` (`${TMPDIR:-/tmp}/forge-verify`), outside the repo, and is swept by the single `rm -rf "$WORKDIR"` in the Cleanup block, never mid-run.
