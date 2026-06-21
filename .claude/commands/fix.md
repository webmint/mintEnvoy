---
name: fix
description: Proposal-only gated remediation of pipeline-surfaced findings for one feature. OFFERED (never auto-invoked) when `/review` surfaces findings, when `/verify` returns NEEDS WORK, or conversationally when the user raises a defect the model code-confirms in-window. Intakes the surfaced findings, triages + scopes them, then delegates to `/implement`'s back-half engine (scope-aware verify + self-repair → four-reviewer panel → forcing-functions gate → two-stage hard gate → WIP commit). Never invents a defect, never accepts a free-text bug description, never writes `bugs/`.
argument-hint: "[spec-file/feature-dir]"
disable-model-invocation: true
allowed-tools:
  - Bash(.devforge/lib/fix_helper preflight *)
  - Bash(.devforge/lib/fix_helper in-fix-window *)
  - Bash(.devforge/lib/fix_helper read-findings *)
  - Bash(.devforge/lib/fix_helper resolve-scope *)
  - Bash(.devforge/lib/implement_helper verify-touched *)
  - Bash(.devforge/lib/implement_helper merge-review-panel *)
  - Bash(.devforge/lib/implement_helper run-forcing-functions-gate *)
  - Bash(.devforge/lib/implement_helper wip-commit *)
  - Bash(git diff *)
  - Bash(git -C * diff *)
---

# /fix — Gated Remediation of Pipeline Findings

`/fix` is a thin, gated **remediation** command — the "remediate now" arm of a two-arm fix-or-file offer. It is OFFERED (PROPOSED), never auto-invoked (every forge command sets `disable-model-invocation: true`), in exactly three in-window situations: `/review` surfaces findings, `/verify` returns NEEDS WORK, or the user raises a defect the model code-confirms while the active feature is post-`/implement`/pre-`/summarize`. When invoked it intakes the already-diagnosed, already-located findings, triages + scopes them, then points `/implement`'s already-shipped back-half engine at the finding instead of at a fresh task.

**`/fix` reuses `/implement`'s back half — it does NOT re-implement it.** PHASES 3–6 below CALL the installed `implement_helper` verbs (`verify-touched`, `merge-review-panel`, `run-forcing-functions-gate`, `wip-commit`) exactly as `/implement` PHASES 5–7 wire them. Those verbs are single-source-of-truth binaries; this spec orchestrates them, it copies none of their machinery (no `PACKAGE_STACKS` logic, no self-repair-cap logic, no panel-merge logic lives here). State + render shape are owned by `.devforge/lib/fix_helper` and `.devforge/lib/implement_helper`; the orchestrator composes values via verb subcommands and dispatches the implementing agent + the four review-panel agents.

**`/fix` never invents a defect.** It consumes pipeline-produced findings (`specs/[feature]/review.md`, `specs/[feature]/verification.md` NEEDS-WORK issues) or a single user-raised + code-confirmed in-window defect. It does NOT accept a free-text "describe a bug" input — a cold, standalone bug a developer notices independently goes hand-fix / full-chain, never `/fix`. And it never writes or closes `bugs/` files: run `/report-bug` to file a bug — the separate "defer" arm of the offer.

Usage: `/fix` (auto-resolve the most-recently-modified `specs/NNN-*` feature) · `/fix specs/001-auth` or `/fix specs/001-auth/spec.md` (an explicit feature dir or a spec file inside it).

## Maintainer note

This file lives at `src/commands/fix/main.md` in the AIDevTeamForge template repo and is the SSOT for the `/fix` command. Do NOT inject project-specifics — this spec is substituted + emitted into target projects by the build. Helper paths use the installed `.devforge/lib/...` location because that's where they resolve at runtime in the target project. Reference-file paths are written author-relative (`references/<file>.md`); the emitter rewrites them to `.claude/commands/fix/references/<file>.md` at install time.

## Outputs of this command

`/fix` writes NO report file of its own. Its only durable output is the same one `/implement` produces per approved task:

- A `[WIP] fix: <title>` commit (standalone) or `[TICKET-ID] - <title>` commit (wrapper mode, ticket derived from the source branch), written by `implement_helper wip-commit` in task-less mode (PHASE 6) carrying the remediation diff. WIP commits accumulate and are squashed by `/finalize`.

`/fix` does NOT write `specs/[feature]/*.md`, does NOT mutate the spec or the task files, and does NOT write or close any `bugs/` file. The feature's `review.md` / `verification.md` (its inputs) are read-only here. Re-verifying the remediated diff is `/verify`'s job (PHASE 7 points there).

### Intermediate scratch files (orchestrator-written, helper-consumed) — all under `$WORKDIR`

The helper cannot dispatch agents (a subprocess has no Task/MCP tools), so the orchestrator captures each verb's stdout to an intermediate scratch file that the next verb reads. All live under `$WORKDIR` (`${TMPDIR:-/tmp}/forge-fix`) and are scratch state for one run — the whole directory is removed by the single Cleanup `rm -rf "$WORKDIR"`. Because `$WORKDIR` is outside the work tree, the files need no leading dot and no gitignore handling.

- `$WORKDIR/preflight.json` — the `preflight` stdout (`source_root`, `framework`, `language`, `wrapper_mode`, `setup_chain_ok`, …). Written in PHASE 0, read by the orchestrator for the `source_root` / `wrapper_mode` values it threads forward.
- `$WORKDIR/findings.json` — the `read-findings` stdout (`items`, `sources`). Written in PHASE 0, read by the orchestrator to triage (PHASE 1) and passed to `resolve-scope --items` (PHASE 1).
- `$WORKDIR/items.json` — the bare `items` ARRAY extracted from `$WORKDIR/findings.json` (plus any case-3 item the orchestrator appends), written in PHASE 1 and passed to `resolve-scope --items` (which takes a file PATH containing the working list).
- `$WORKDIR/scope.json` — the `resolve-scope` stdout (`files`, `file_count`, `empty`). Written in PHASE 1, read by the orchestrator to build the inline `verify-touched --files` JSON-array string.
- `$WORKDIR/mechanical.json` — the `verify-touched` stdout (`status`, `iteration`, `failed_command`, `output`, …). Written + re-written across the PHASE 3 self-repair loop.

The PHASE 4 review panel writes its per-reviewer scratch to `${TMPDIR:-/tmp}/forge-implement-review/` — the SAME path `/implement` PHASE 6 uses (not under `$WORKDIR/forge-fix`). That directory is the bridge to `merge-review-panel`; the Cleanup block removes it alongside `$WORKDIR`.

## Reference files

- `.claude/commands/fix/references/triage.md` — how to triage a working-list item (defect-repair vs feature/architecture change) and the PHASE-1 D7 `/specify` bounce criteria. Read it in full at PHASE 1.

## Helper interaction model

Every mechanical step is a normal Bash tool call to `.devforge/lib/fix_helper <verb> ...` (the front half) or `.devforge/lib/implement_helper <verb> ...` (the reused back half). Each verb prints JSON (or a rendered block) to stdout. Verbs that consume a prior verb's output take a `--<name> <path>` flag (not stdin), so capture stdout to the named `$WORKDIR/*.json` scratch file with `>` and pass that path into the next call — the per-phase fences below show the exact redirects. Re-establish `WORKDIR="${TMPDIR:-/tmp}/forge-fix"` at the top of every Bash block that touches scratch (the variable does not survive across Bash calls — see PHASE 0). On any non-zero exit, copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then follow the recovery note for that phase. The helper owns file structure, validation, and atomic writes; the orchestrator owns the agent dispatch, user-facing prose, and phase pacing.

`/fix` keeps NO per-feature run state of its own (there is no `check-status-and-flip` verb — `/fix` has no multi-phase back-half state; the back-half loops are owned by `implement_helper`). So unlike `/review` and `/verify`, no phase-boundary state-flip call appears below.

## PHASE 0 — Preflight + feature resolution + findings intake (the D2 boundary)

Cheapest guards first; preflight before any feature I/O.

### 0.1 — Preflight gate

```bash
.devforge/lib/fix_helper preflight --workspace-root . > /tmp/fix-preflight-check.json
```

`preflight` checks the 4-command setup chain (`/init-forge → /generate-docs → /configure → /constitute`) and the populated-constitution guard. It ALWAYS writes its JSON context block to stdout BEFORE any gate check, then exits **2** with a user-facing stderr message when (a) a setup-chain artefact is missing or (b) `constitution.md` is absent or still carries an unpopulated sentinel. On exit 2, copy the helper's stderr VERBATIM as a fenced code block and end the turn — the user runs the named missing command first. On exit 0, the stdout JSON carries `source_root` (the project's Source Root — `.` for a standalone install, the inner project subdir in wrapper mode), `framework`, `language`, and `wrapper_mode`. (`$WORKDIR` is not established until 0.3, so this gate call captures to a fixed `/tmp` path; 0.3 re-runs `preflight` into `$WORKDIR/preflight.json` once the scratch dir exists. `preflight` is read-only and cheap, so running it twice is harmless.) Carry `source_root` and `wrapper_mode` forward: PHASE 2 briefs the implementing agent under the source root, and PHASE 3 passes `source_root` context to the implementing agent during self-repair.

### 0.2 — Resolve the feature directory

Resolve the feature dir from `$ARGUMENTS`:

- When `$ARGUMENTS` names a feature directory (`specs/NNN-<slug>`) or a file inside one (e.g. `specs/001-auth/spec.md`), use that feature directory (strip a trailing filename to the `specs/NNN-<slug>` dir).
- When `$ARGUMENTS` is empty, auto-resolve the most-recently-modified `specs/NNN-*` directory (the feature most likely just finished `/review` or `/verify`).

If no `specs/NNN-*` directory exists, tell the user there is no feature to remediate (run `/specify` → `/plan` → `/breakdown` → `/implement` → `/review` first) and end the turn. Carry the resolved feature dir forward as `<feature>` — every subsequent `--feature` flag takes it.

### 0.3 — Window gate (the case-3 sealed-feature STOP) + scratch dir

`/fix` only remediates a feature whose WIP commits are still open — post-`/implement`, pre-`/summarize`. Confirm the window before any further work:

```bash
.devforge/lib/fix_helper in-fix-window --feature <feature>
```

`in-fix-window` emits JSON `{in_window, reason}` and uses its EXIT CODE as the gate: **exit 0** = in-window (proceed), **exit 1** = out-of-window. On exit 1 (`reason` is `summary_present` or `spec_complete` → the feature is SEALED; `no_tasks_dir` / `no_task_files` → not yet implemented; `not_all_tasks_complete` → `/implement` is still mid-flight), STOP: do NOT remediate in place. Tell the user the feature is out of the fix window — a sealed feature (post-`/summarize`/`/finalize`) must be remediated in a fresh cycle, so run `/report-bug` to file a bug and defer it, then start a new `/specify` → … → `/implement` cycle rather than fixing in place. (A `not_all_tasks_complete` window means `/implement` has not drained the feature; finish `/implement` first.) Report the `reason` to the user so they know which out-of-window state applies, then end the turn. On exit 2 (a `--feature` argument error), copy the helper's stderr VERBATIM as a fenced code block and end the turn.

Then establish + clear the scratch working directory:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-fix"
rm -rf "$WORKDIR" && mkdir -p "$WORKDIR"
```

**All intermediate scratch for this run lives in `$WORKDIR` (the fixed literal `${TMPDIR:-/tmp}/forge-fix`), OUTSIDE the repo.** The literal is `forge-fix`, NOT `forge-verify` / `forge-review` / `forge-audit` — those commands may run concurrently, and a shared workdir would corrupt every run. `$WORKDIR` is outside the work tree, so the scratch files need no leading dot, no gitignore handling, and no per-file `rm` list. The `rm -rf "$WORKDIR" && mkdir -p "$WORKDIR"` clears any stale scratch from a prior crashed run.

**CRITICAL — `$WORKDIR` is a FIXED LITERAL you re-derive in every Bash block; it does NOT persist across calls.** The orchestrator runs each Bash tool call in a FRESH shell, so shell variables (including `$WORKDIR`) do NOT carry from one Bash call to the next. So every Bash block that touches scratch MUST begin by re-establishing `WORKDIR="${TMPDIR:-/tmp}/forge-fix"` and then reference `"$WORKDIR/..."`. The literal is identical in every block, so each block reconstructs the same directory.

Now re-capture the preflight context into `$WORKDIR` so later blocks can re-read its `source_root` / `wrapper_mode` values (the gate already passed in 0.1; this just persists the context to the scratch dir):

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-fix"
.devforge/lib/fix_helper preflight --workspace-root . > "$WORKDIR/preflight.json"
```

### 0.4 — Intake the surfaced findings

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-fix"
.devforge/lib/fix_helper read-findings --feature <feature> > "$WORKDIR/findings.json"
```

`read-findings` parses `specs/[feature]/review.md` confirmed/contested findings AND the `specs/[feature]/verification.md` NEEDS-WORK issues into ONE working list. (Pass `--source review` or `--source verify` to restrict to one file; the default `both` unions them.) Stdout JSON carries `items` (the working list — each item a `{title, severity, files_cited, evidence, source}` dict) and `sources` (`review` / `verify` found-flags, the `verify_verdict` string, and `review_missing` / `verify_missing`). `read-findings` returns exit 0 even when both files are absent (`items` is `[]`); a non-zero exit is a `--feature` argument error — copy the helper's stderr VERBATIM and end the turn.

**Case-3 conversational defect.** When the `/fix` invocation followed a user-raised defect that you ALREADY code-confirmed before proposing `/fix` (not a `/review`/`/verify` finding on disk), that confirmed defect IS the working-list item. Carry it as a single item of the same shape — `{title, severity, files_cited, evidence, source: "conversation"}` — with `files_cited` set to the file(s) you read to confirm it and `evidence` set to the verbatim code you quoted. You will append it to the working list in PHASE 1. Do NOT fabricate this item: it exists only when the user pointed out the defect AND you confirmed it from the actual code in this conversation.

**Empty-list STOP (D2).** If `$WORKDIR/findings.json` `items` is `[]` AND no case-3 confirmed defect was supplied, there is nothing to remediate: tell the user there are no pipeline findings to fix — run `/review` or `/verify` first to surface findings, or (for a cold bug noticed independently) hand-fix it or take it through the full chain. `/fix` never invents a defect and never accepts a free-text bug description. Clean up (`rm -rf "$WORKDIR"`) and end the turn. This is not an error — it is an empty working list.

## PHASE 1 — Triage + scope-estimate (the D7 bounce)

Read `.claude/commands/fix/references/triage.md` in full now — it carries the defect-repair-vs-change classification and the D7 bounce criteria.

Triage the working list (the `items` from `$WORKDIR/findings.json`, plus the case-3 item if one was supplied). For each item, classify it per `.claude/commands/fix/references/triage.md`: a **defect repair** (the code is wrong against its own intent — a logic bug, a missing case, a contract violation, a security hole) stays in `/fix`; a **feature/architecture change** (the fix would add behavior, change a data model, introduce a dependency, or restructure a layer — i.e. it changes WHAT the system does, not just whether it does it correctly) does NOT belong in `/fix`.

**The D7 scope-escalation bounce.** If ANY working-list item would require a feature/architecture change rather than a defect repair, STOP and recommend `/specify`: tell the user the item is not a defect repair but a scope change (name which item + why, per `.claude/commands/fix/references/triage.md`), so it belongs in a fresh `/specify` → `/plan` → `/breakdown` cycle, not in a gated in-place fix. `/fix` remediates known defects with `/implement`'s gates; it does not grow the feature. End the turn — do not partially remediate. (When the working list MIXES defect repairs and a scope change, surface the scope change as the bounce and let the user decide whether to drop it from the set and re-run `/fix` on the defect-only remainder, or take the whole set through `/specify`.)

Otherwise — every item is a defect repair — resolve the narrow touched-file set. First extract the `items` array (appending the case-3 item if one was supplied) to its own file, then map it to the file set:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-fix"
# Extract the working list. When a case-3 item was supplied, append it here
# (write the combined array yourself with the Write tool instead of this line).
python3 -c "import json; json.dump(json.load(open('$WORKDIR/findings.json'))['items'], open('$WORKDIR/items.json','w'))"
.devforge/lib/fix_helper resolve-scope --items "$WORKDIR/items.json" > "$WORKDIR/scope.json"
```

`resolve-scope` takes the working list as a file PATH (`--items`; pass `-` to read stdin) and emits JSON `{files, file_count, empty}` — `files` is the deduplicated, sorted union of every path cited across the working-list items (the NARROW finding-targeted set, NOT the assembled-feature diff — that is `/verify`'s scope). On a non-zero exit (unreadable `--items`, invalid JSON, or a non-list), copy the helper's stderr VERBATIM and end the turn.

**Empty-scope guard.** If `scope.json` `empty` is `true` (the findings cited no files), the remediation has no file target to verify against. Tell the user the findings name no files to fix (so `/fix` cannot scope a verify gate) and that the finding(s) need a file citation — point them back to the `/review` / `/verify` report to add the missing location, or hand-fix. Clean up and end the turn.

Carry the `files` array forward — it is the inline JSON-array STRING the `verify-touched --files` argument takes in PHASE 3.

## PHASE 2 — Dispatch the implementing agent at the finding

Pick the implementing agent per the file-layer → agent mapping (the same mapping `/breakdown` uses — a file's package/layer determines its owning stack's implementer). **Architect guard:** the architect is a director and cannot write implementation code (per `.claude/agents/architect.md` Rule 1; its charter is to refuse-and-route coding work back to the owning stack's implementer). NEVER dispatch `architect` to remediate. If the finding spans multiple layers, split the remediation across the owning implementers (one agent per layer's files) rather than handing the whole thing to the architect; if no owning implementer agent is installed for a finding's layer, HALT and escalate to the human (run `/setup-wizard` to install the missing agent, or hand-fix) — never fall back to `architect`.

Brief the chosen agent with COMPLETE context — it sees only what you brief it with. The brief MUST carry:

- **The finding(s)** it is remediating — the `title`, `severity`, and `evidence` of each working-list item assigned to this agent.
- **The cited files** — the `files_cited` for those items (source-rooted: `<source_root>/<path>` in wrapper mode, repo-relative in standalone), as the scope constraint.
- **The constitution rules** (`constitution.md`) and the `.devforge/memory.md` pitfalls.
- **An explicit scope rule:** "Remediate ONLY the cited defect(s) — make the minimal change that fixes the finding; do not modify unrelated code, do not add features, do not refactor beyond the fix." A remediation that grows the change beyond the finding is itself a finding the PHASE 4 panel will flag.

The agent edits SOURCE files and writes its edits into the working tree; nothing is committed yet. In wrapper mode, state explicitly that the agent must NOT write forge artifacts (`.claude/`, `specs/`, `CLAUDE.md`, `constitution.md`, `bugs/`, …) into the source tree — those live at the install root, and PHASE 3's wrapper-isolation check fails the run if any appear inside the source root. In standalone mode the single repo legitimately contains those artifacts, so the isolation rule is moot.

## PHASE 3 — Scope-aware verify + self-repair

Run scope-aware verification over the remediated files, looping self-repair EXACTLY as `/implement` PHASE 5. `/fix` is a write-path command, so it REPAIRS (unlike `/verify`, which calls `verify-touched` report-only). Pass the `files` array from PHASE 1's `scope.json` as an inline JSON-array STRING and start the iteration counter at 0:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-fix"
FILES_JSON="$(python3 -c "import json; print(json.dumps(json.load(open('$WORKDIR/scope.json'))['files']))")"
.devforge/lib/implement_helper verify-touched --files "$FILES_JSON" --root . --iteration 0 > "$WORKDIR/mechanical.json"
```

`verify-touched` (the helper, not this spec) matches each file to its package via `PACKAGE_STACKS`, runs that package's static checks (type-check + lint) → build → tests with `cwd = <source_root>`, and owns the self-repair cap (3) — the orchestrator cannot extend it. It emits JSON with a top-level `status` field. Handle EACH status exactly as `/implement` PHASE 5 does:

- **`{"status": "pass", ...}`** (exit 0) → verification passed. Proceed to PHASE 4.
- **`{"status": "self_repair", ...}`** (exit 0) → a command failed and the cap is not yet reached. The object carries `iteration` (`N`), `failed_command`, and `output`. Relaunch the **same implementing agent** from PHASE 2 with the `failed_command` and `output` so it can fix the failure, then re-call `verify-touched` with `--iteration` set to `N + 1`. Repeat this autonomous self-repair leg — no human between iterations.
- **`{"status": "failed", ...}`** (exit 2) → the self-repair cap was reached; the remediation is blocked. Copy the helper's stdout VERBATIM into a fenced code block, then STOP and tell the user the fix could not be made to pass verification within the self-repair cap — they can repair manually with more direction and re-run `/fix`, or take the finding through the full chain. Clean up and end the turn (nothing has been committed).
- **`{"status": "isolation_failure", "artifacts": [...]}`** (exit 2, wrapper mode only) → the agent polluted the source tree with forge artifacts (the `artifacts` array lists the offending paths). Copy the helper's stdout VERBATIM, then instruct the implementing agent to REMOVE the misplaced artifacts from the source tree and re-run this PHASE-3 verify from `--iteration 0`. (Standalone never emits this status.)
- **`{"status": "tooling_unavailable", "failed_command": "...", "output": "..."}`** (exit 2) → a configured type-check, lint, or test command could not be executed (a missing binary or misconfigured command). This is a tooling/config problem, not a code error, and it is not self-repairable. Copy the helper's stdout VERBATIM, then STOP and tell the user to correct the configured command (owned by `/configure`) or install the missing tool, then re-run `/fix`. Clean up and end the turn. (`/fix` has no `scope-and-approve` path — unlike `/implement`, it does not own a per-task hard gate that can scope-and-approve unverified boxes; a fix that cannot be mechanically verified does not land.)

Exit 1 (missing/malformed `project-config.json`) — copy the helper's stderr VERBATIM into a fenced code block, then end the turn.

## PHASE 4 — Four-reviewer panel

After verify passes, run the bounded autonomous review-panel loop EXACTLY as `/implement` PHASE 6 — a panel of FOUR read-only reviewers (`code-reviewer`, `qa-reviewer`, `security-reviewer`, `performance-analyst`) ⇄ the implementing agent, ≤3 rounds (the helper-owned counter), NO human between rounds. The loop converges to a panel-clean verdict (every reviewer clean). All four reviewers are read-only and tools-locked (`Read, Grep, Glob, Bash`; no `Edit`/`Write`/`Agent`), so a parallel fan-out is safe and the only writer is the implementing agent during a repair leg.

Start the loop iteration counter at 0 and run:

1. **Fan out the four reviewers in parallel.** In ONE turn, dispatch `code-reviewer`, `qa-reviewer`, `security-reviewer`, and `performance-analyst` via the Task tool — four Task calls in the same turn, each with `subagent_type: <agent>` (which loads that reviewer's persona from `.claude/agents/<agent>.md`; do NOT re-inline the persona). Give EACH the same inputs: the remediated `files` (PHASE 1's scope), the constitution, and the finding(s) being remediated. The four results return UNORDERED, so key each returned markdown to the agent you dispatched it to. Each reviewer returns a markdown verdict carrying a `### Verdict:` line in its own vocabulary (`code-reviewer`: `APPROVE` / `REQUEST CHANGES` / `BLOCK`; `qa-reviewer`: `ADEQUATE` / `GAPS FOUND`; `security-reviewer`: `PASS` / `FAIL`; `performance-analyst`: `MEETS TARGETS` / `BOTTLENECKS FOUND`).
2. **Write each reviewer's returned markdown to a run-scoped scratch file** — write each with the Write tool to `${TMPDIR:-/tmp}/forge-implement-review/<agent>.md` (one file per reviewer, named for the agent). This is the SAME scratch path `/implement` PHASE 6 uses — reuse it unchanged. A bash subprocess cannot read a subagent's return value, so these files are the bridge to the merge helper.
3. **Merge the four verdicts** via the helper, passing the current iteration `N` and one `--reviewer <agent>:<path>` per reviewer (the path written in step 2):

   ```bash
   .devforge/lib/implement_helper merge-review-panel --iteration N --reviewer code-reviewer:<path> --reviewer qa-reviewer:<path> --reviewer security-reviewer:<path> --reviewer performance-analyst:<path>
   ```

   The helper parses each reviewer's `### Verdict:` line against that reviewer's vocabulary and emits JSON `{clean, escalate, iteration, per_reviewer}` (exit 0). `clean` is `true` IFF EVERY reviewer returned its own clean token (`code-reviewer` `APPROVE`, `qa-reviewer` `ADEQUATE`, `security-reviewer` `PASS`, `performance-analyst` `MEETS TARGETS`); one dirty reviewer keeps the loop going. `escalate` is `true` when `N >= 3` (the helper-owned cap). Exit 2 means one reviewer's verdict line was missing, was the unfilled template, or carried a token outside that reviewer's vocabulary — copy the helper's stderr VERBATIM (it names WHICH reviewer failed), then re-invoke ONLY that named reviewer for a properly-formed verdict, rewrite its scratch file, and re-run `merge-review-panel`.
4. Branch on the JSON:
   - **`clean: true`** → exit the panel loop. Carry any reviewer warnings into PHASE 6 Stage B. Proceed to the forcing-functions gate (PHASE 5).
   - **`clean: false` and `escalate: false`** → the autonomous repair leg (no human). Synthesize ALL findings across the four reviewers into ONE implementing-agent repair brief, relaunch the **implementing agent** ONCE with the synthesized findings, then re-run PHASE 3 (verify) over the same scope and **re-fan-out the FULL panel** (all four reviewers) at iteration `N + 1`. Full-panel re-review each round closes the cross-file-regression hole a repair could open.
   - **`clean: false` and `escalate: true`** → the cap was reached without converging. The remediation is blocked: STOP and tell the user the review panel could not be brought clean within the cap, surfacing the unresolved reviewer objection(s). They can repair manually with more direction and re-run `/fix`, or take the finding through the full chain. Clean up and end the turn (nothing has been committed).

## PHASE 5 — Forcing-functions gate

After the panel exits clean, run the constitution forcing-functions gate via the helper, exactly as `/implement` PHASE 6 tail:

```bash
.devforge/lib/implement_helper run-forcing-functions-gate
```

The helper reads the `forcing_functions` block from `.devforge/constitute.json` and invokes `constitute_helper verify-<rule>` for each enabled rule (`verify-magic-enum`, `verify-cross-layer-imports`, `verify-any-leak`). It emits JSON `{gate, rules_run, rules_failed, reports, aggregate_exit}` on stdout.

- **exit 0** → no enabled rule failed (or no rules are enabled). Proceed to PHASE 6.
- **exit 2** → one or more rules failed; the remediation is gate-blocked. Copy the helper's stdout JSON VERBATIM into a fenced code block (the stdout report carries the per-rule findings, NOT stderr). Then either send the implementing agent back to fix the flagged rule break and re-run PHASE 3 → PHASE 4 → PHASE 5, or STOP if it cannot be brought clean (nothing has been committed; clean up and end the turn).
- **exit 1** → config I/O or parse error (malformed `.devforge/constitute.json`, or an enabled rule with no known verb). Copy the helper's stderr VERBATIM into a fenced code block, then end the turn.

## PHASE 6 — Two-stage hard gate + WIP commit

This is the human gate, run EXACTLY as `/implement` PHASE 7 — **no content has been committed at this point** (the remediation sits in the working tree). Stage A surfaces any judgment-level calls the panel recorded one at a time (skipped when none), then Stage B always presents the diff for the final code read. The `approve` gate is reachable ONLY from a fully-clean panel (PHASE 4 `clean: true`) AND a passing forcing-functions gate (PHASE 5 exit 0) — there is no path that commits an open finding.

### Stage A — Decision questions (run ONLY if PHASE 4 recorded ≥1 judgment-level call)

For EACH recorded judgment item, ask ONE `AskUserQuestion` — sequentially, never batched; the question is a single line, the explanation lives in the option `description` fields. Option 1 is ALWAYS the agent's resolution, marked `(recommended)`. Choosing an alternative or `let me specify` is treated as a repair: relaunch the implementing agent with the chosen direction, re-run PHASE 3 (verify) → PHASE 4 (panel) → PHASE 5 (forcing-functions), and restart Stage A. `stop` keeps the working tree and ends the turn. Most remediations record zero judgment items → Stage A is skipped.

### Stage B — Final code read (ALWAYS)

Present the ready diff and the verification results. Show `git diff --stat` and the `git diff` (for a large diff, bound it: show `--stat` in full plus the diff for the highest-impact files, and tell the user the full diff is available on request). Summarize the PHASE 3 verify result, the PHASE 4 panel verdict (the four reviewers' clean verdicts plus any carried warnings), and the PHASE 5 forcing-functions result.

Then ask via `AskUserQuestion`:

- Question: `"Approve fix for <feature> — <short finding summary>?"` — single-line text.
- Options: `["approve", "repair", "stop"]`. (No `skip` — `/fix` remediates a chosen finding set; there is no "advance to the next task" to skip to. To abandon the remediation, use `stop`.)

End the turn. The user's reply opens the next turn.

- **`approve`** → commit the approved remediation as a `[WIP]` commit (the remediated `files` from PHASE 1's scope, staged precisely — never `git add -A`):

  ```bash
  WORKDIR="${TMPDIR:-/tmp}/forge-fix"
  .devforge/lib/implement_helper wip-commit --files "$(python3 -c "import json; print(json.dumps(json.load(open('$WORKDIR/scope.json'))['files']))")" --title "<short finding summary>"
  ```

  This is `wip-commit`'s **task-less mode** — `/fix` passes ONLY `--files` and `--title`, omitting `--task-file`/`--index`/`--number` (which are optional; when absent, the verb stages only the touched files and writes a fix-shaped message). The commit lands as a `[WIP] fix: <title>` commit in standalone mode, or a `[TICKET-ID] - <title>` commit on the source branch in wrapper mode. It never uses `git add -A` — in standalone mode it stages ONLY the touched `--files` in the single repo (no task file, no index); in wrapper mode it stages ONLY the source `touched_files` to the source repo on its branch (deriving the `[TICKET-ID]` from the source branch and SUPPRESSING attribution). It composes the message per the wrapper/non-wrapper convention (reading `WORKSPACE_MODE` + `COMMIT_ATTRIBUTION` from `.devforge/project-config.json`), commits, captures the new source HEAD SHA, and clears `.devforge/wip.md` (exit 0 → `{"committed": true, head_sha, message}`). Exit 1 (missing/malformed config, non-JSON or non-array `--files`, missing `--title`, or config/I/O error); exit 2 (git staging/commit failure — including an empty `--files '[]'`, which stages nothing and fails the commit) — copy the helper's stderr VERBATIM into a fenced code block and resolve before re-running. (`/implement` PHASE 7 still passes all of `--task-file`/`--index`/`--number` and is unaffected by this mode — its behavior is unchanged.)

  Proceed to PHASE 7.
- **`repair`** → ask the user via free-text follow-up for the repair direction, relaunch the implementing agent with those notes, then re-run PHASE 3 (verify) → PHASE 4 (panel) → PHASE 5 (forcing-functions) → return to this hard gate.
- **`stop`** → keep the working tree as-is; tell the user the remediation stopped with work uncommitted; clean up `$WORKDIR` and end the turn.

## PHASE 7 — Present + next step

The fix landed as a `[WIP]` commit (the remediation diff). Tell the user:

- The remediation is committed as a `[WIP]` commit (it will be squashed into the clean feature commit by `/finalize`).
- The next step is **`/verify`** — re-running `/verify` on this feature re-proves the acceptance criteria against the REMEDIATED diff and re-renders the verdict (the remediation may flip a NEEDS WORK to APPROVED). When the original findings came from `/review`, re-running `/review` then `/verify` re-checks the assembled feature.

Then clean up the scratch directories in one step — both `$WORKDIR` and the review-panel scratch dir (the same one `/implement` PHASE 6 uses):

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-fix"
rm -rf "$WORKDIR" "${TMPDIR:-/tmp}/forge-implement-review"
```

## Important rules

1. **Proposal-only, never auto-invoked** — `/fix` is OFFERED (PROPOSED) as the "remediate now" arm of a two-arm fix-or-file offer; the user types `/fix`. The model never runs it autonomously (`disable-model-invocation: true`).
2. **Consumes findings, never invents them** — `/fix` remediates pipeline-surfaced findings (`review.md` / `verification.md` NEEDS-WORK issues) or a single user-raised + code-confirmed in-window defect. It does NOT accept a free-text bug description (D2); an empty working list with no case-3 defect STOPS the run.
3. **In-window only** — `/fix` runs only on a feature whose WIP commits are still open (post-`/implement`, pre-`/summarize`, gated by `in-fix-window`). A sealed feature gets a fresh cycle, never an in-place fix.
4. **Defect repairs only — the D7 bounce** — a working-list item that needs a feature/architecture change (not a correctness repair) bounces to `/specify`; `/fix` does not grow the feature.
5. **The back half is CALLED, not COPIED (D6)** — PHASES 3–6 call `implement_helper verify-touched` / `merge-review-panel` / `run-forcing-functions-gate` / `wip-commit`; this spec copies none of their machinery (no `PACKAGE_STACKS`, self-repair-cap, or panel-merge logic). They are single-source-of-truth binaries; a caller cannot drift from them.
6. **The architect never codes** — never dispatch `architect` to remediate; route layer-mixed work to the owning stack's implementers, or escalate to the human when an owning implementer is missing (per `.claude/agents/architect.md` Rule 1).
7. **Writes only a `[WIP]` commit** — `/fix` writes NO report, mutates NO spec/task/`review.md`/`verification.md`, and writes or closes NO `bugs/` file (D4 — `/report-bug` is the separate "defer" arm). Its only durable output is the remediation `[WIP]` commit, squashed by `/finalize`.
8. **Nothing commits before `approve`** — the remediation + all self-repair / panel-repair edits sit in the working tree until the Stage B gate approves them. A blocked verify cap, an unconverged panel, or a failed forcing-functions gate ends the turn with nothing committed.
9. **Relay machine reports VERBATIM** — where a helper emits a user-facing finding report on stdout (blocked verify, forcing-functions exit 2), copy its stdout VERBATIM into a fenced code block; for helper failures, copy the stderr VERBATIM. Do not summarize or paraphrase.
10. **Cleanup is last** — all intermediate scratch lives in `$WORKDIR` (`${TMPDIR:-/tmp}/forge-fix`) plus the reused `${TMPDIR:-/tmp}/forge-implement-review/` panel dir, both outside the repo, swept by the single PHASE-7 (or `stop`-path) `rm -rf`.
```
