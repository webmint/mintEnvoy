---
name: audit
description: Adversarial whole-codebase quality audit across the full spectrum — mislogic, system design, language/framework best practices, duplication, and constitution adherence; writes a dated report. `--passes N` runs the audit K times and unions the findings for wider recall — it defaults by mode (broad/hotspot → 2, narrow → 1) and an explicit `--passes N` (clamped 1–3) overrides.
argument-hint: '[--full | --uncommitted | --top N | path] [--passes N]'
disable-model-invocation: true
---

# /audit — Adversarial Codebase Audit

`/audit` is a standalone, on-demand whole-codebase audit for periodic "second opinion" quality reviews. It invokes the review-agent ensemble (`code-reviewer`, `architect`, `qa-reviewer`, `security-reviewer`) in ADVERSARIAL MODE to hunt the full quality spectrum — mislogic (lying code, control-flow bugs, cross-file contradictions), system design (layering drift, SOLID-at-scale, god components — software design, not visual), language/framework best practices (type-safety suppression, untyped boundaries, reactivity/lifecycle misuse, static perf-idiom smells), duplication (copy-paste and diverged variant copies), and constitution-principle adherence — validates every finding against the actual source to discard hallucinations, force-ranks the survivors, and writes a dated report to `audits/YYYY-MM-DD-audit.md`. Each agent declares a `Category` on every finding (one of `mislogic`, `system_design`, `best_practice`, `duplication`, `security`, `blind_spot`); the report buckets findings by that declared category. The `--passes N` flag (an explicit value is clamped to 1–3) runs the dispatch-and-validate loop K times and unions the per-pass findings into one report — widening observed-union recall for periodic deep "second-opinion" audits at K× the cost. When `--passes` is omitted, `resolve-mode` defaults it by scope mode (broad/hotspot → 2 for wider recall; narrow → 1); an explicit `--passes N` overrides the mode default. A resolved value of 1 is the single-pass behavior, unchanged. Read-only — it never modifies source, never auto-commits the report. State + render shape are owned by `.devforge/lib/audit_helper`; the orchestrator composes values via verb subcommands. **NOT part of any workflow chain — invoke manually after several specs ship, or on a periodic cadence.**

Usage: `/audit` (broad, default) · `/audit --full` (explicit broad) · `/audit --top N` (hotspot — top N risk-scored files) · `/audit --uncommitted` (working-tree changes) · `/audit path/to/file.ts` or `/audit src/auth/` (narrow). Add `--passes N` (clamped 1–3) to any mode to run the agent-dispatch + per-agent validation loop N times and merge the passes; when omitted it defaults by mode (broad/hotspot → 2, narrow → 1), and an explicit `--passes N` overrides.

## Maintainer note

This file lives at `src/commands/audit/main.md` in the AIDevTeamForge template repo and is the SSOT for the `/audit` command. Do NOT inject project-specifics — this spec is substituted + emitted into target projects by the build. Helper paths use the installed `.devforge/lib/...` location because that's where they resolve at runtime in the target project. Reference-file paths are written author-relative (`references/<file>.md`); the emitter rewrites them to `.claude/commands/audit/references/<file>.md` at install time.

## Outputs of this phase

ALL intermediate scratch lives in `$WORKDIR` — the fixed literal `${TMPDIR:-/tmp}/forge-audit`, OUTSIDE `audits/` (see Preflight for why + the re-establish-per-block rule). The ONLY files this command writes under `audits/` are:

- `audits/.state.json` — audit run state (phase + mode + scope + outpath). Owned + shaped by the helper; initialized at Preflight, advanced via `check-status-and-flip --workspace-root .`. Needs a STABLE known path so an interrupted run can find where it stopped; it is rewritten each phase, so a stray reap just gets recreated on the next `check-status-and-flip`. Lives at the workspace root's `audits/` directory.
- `audits/.gitignore` — helper-written on first run (ignores `.tmp-*.md`). Lives in `audits/` because that is the directory it governs. (Now effectively a no-op, kept for backward compatibility: agent temps live in `$WORKDIR`, not `audits/`, so the `.tmp-*.md` pattern matches nothing.)
- `audits/YYYY-MM-DD-audit.md` — the rendered audit report. Produced by the helper's `render-report` verb in Phase 5; collision suffix `-2`, `-3`, … on same-day re-runs. A non-dotfile, so the reaper leaves it alone. **Not committed, not staged** — the user decides whether to keep audit history in git.

### Intermediate scratch files (orchestrator-written, helper-consumed) — all under `$WORKDIR`

The helper cannot call CBM or dispatch agents (a subprocess has no MCP tools), so the orchestrator captures each verb's stdout to an intermediate scratch file that the next verb reads (most verbs take a `--<name> <path>` flag, not stdin). All live under `$WORKDIR` (`${TMPDIR:-/tmp}/forge-audit`) and are scratch state for one run — the whole directory is removed at the end (the single Phase-6 `rm -rf "$WORKDIR"`). Because `$WORKDIR` is outside the work tree, the files need no leading dot and no gitignore handling. Several verbs print a DICT (e.g. `{findings, consensus_map}`) but the next verb's `--findings` requires a BARE ARRAY — those steps include a one-line `python3 -c` extraction (shown inline at each phase). The per-agent scratch files (`$WORKDIR/parsed-<agent>.json`, `$WORKDIR/findings-<agent>.json`, `$WORKDIR/validated-<agent>.json`) follow the same one-run lifecycle.

- `$WORKDIR/mode.json` — the `resolve-mode` stdout (mode + scope_arg + uncommitted). Written in Phase 1.1, read by `resolve-scope --mode-result`.
- `$WORKDIR/callers.json` — `{file: caller_count}` or `{file: [caller_qns]}` per-file inbound-edge payload from CBM. Written by the orchestrator in Phase 2.1 (hotspot only), read by `compute-hotspots --callers`.
- `$WORKDIR/hotspot.json` — the ranked `HotspotResult` from `compute-hotspots` stdout. Written in Phase 2.1 (hotspot only), read by `resolve-scope --hotspot` and `render-hotspot-summary --hotspot`.
- `$WORKDIR/scope.json` — the `resolve-scope` stdout (`files`, `file_count`, `pipeline`, `scope_oversize`). Written in Phase 2.2, read by `render-scope-block --scope` and `render-agent-brief --scope`.
- `$WORKDIR/context.md` — the optional `--extra-context-file` payload (constitution rules, MEMORY.md pitfalls, recurring list). Written by the orchestrator in Phase 3.1, read by every `render-agent-brief --extra-context-file`.
- `$WORKDIR/tmp-<agent>.md` — per-agent findings, written by each adversarial agent in Phase 3 (the brief's `--tmp-path` names this exact path), consumed in Phase 4.1. Swept by the end-of-run `rm -rf "$WORKDIR"`.
- `$WORKDIR/recurring.json` — `[{file, fingerprint}]` past-review findings the orchestrator extracts from recent `specs/*/review.md`. Written in Phase 4.3 (broad + hotspot + directory/uncommitted; NOT single-file), read by `map-recurring-issues --recurring`.
- `$WORKDIR/parsed-<agent>.json` — `consume-tmp` stdout (a DICT: `status` + `findings` array). Written + read per agent in Phase 4.1.
- `$WORKDIR/findings-<agent>.json` — the bare `findings` array extracted from `parsed-<agent>.json`. Written in Phase 4.1, read by `validate-findings --findings`.
- `$WORKDIR/validated-<agent>.json` — `validate-findings` stdout per agent (`passed` + `discarded` + `discard_counts`). Written + read in Phase 4.1.
- `$WORKDIR/validated.json` — the four agents' validated `passed` findings concatenated into ONE bare array. Written in Phase 4.1, read by `compute-consensus --findings`.
- `$WORKDIR/tmp-<agent>-p<pass>.json`-style per-pass scratch: `$WORKDIR/parsed-<agent>-p<pass>.json`, `$WORKDIR/findings-<agent>-p<pass>.json`, `$WORKDIR/validated-<agent>-p<pass>.json` — **multi-pass only (`--passes >= 2`).** The per-pass analogues of the three per-agent scratch files above, one set per `<agent>` per `<pass>` (the `-p<pass>` suffix is the only difference). Written + read inside the Phase 3 + 4.1 K-loop.
- `$WORKDIR/validated-p<pass>.json` — **multi-pass only.** One pool file per pass: that pass's four agents' validated `passed` arrays concatenated into ONE bare array. Written at the end of each K-loop iteration, read by `merge-passes --pools` (globbed). Holds ALL of the pass's agents so the merge can compute both cross-agent and cross-pass corroboration.
- `$WORKDIR/merged.json` — **multi-pass only.** `merge-passes` stdout: the BARE merged working array unioning every pass pool (the multi-pass analogue of single-pass's `consensus-findings.json`). Written after the K-loop, read by `route-refutation --findings` + `apply-verdicts --findings` (Phase 4.2.5). REPLACES `compute-consensus` in the multi-pass branch — there is no `consensus.json`/`consensus-findings.json` in a multi-pass run.
- `$WORKDIR/consensus.json` — `compute-consensus` stdout (a DICT: `findings` merged working list + `consensus_map`). Written in Phase 4.2. **Single-pass only (`--passes 1`).**
- `$WORKDIR/consensus-findings.json` — the bare `findings` array extracted from `consensus.json`. Written in Phase 4.2, read by `route-refutation --findings` + `apply-verdicts --findings` (single-pass). **Single-pass only** — multi-pass uses `merged.json` in its place.
- `$WORKDIR/refutation-routes.json` — `route-refutation` stdout (a list of `{refuter, findings}` cross-examination groups assigning each finding a non-author refuter). Written in Phase 4.2.5, read by the orchestrator to drive the per-group `render-verify-brief` + refuter-dispatch loop.
- `$WORKDIR/refute-<refuter>.json` — one refuter group's bare-array `findings` subset, extracted by the orchestrator from `refutation-routes.json`. Written + read per refuter in Phase 4.2.5, passed to `render-verify-brief --findings`.
- `$WORKDIR/verdicts-<refuter>.md` — per-refuter raw markdown verdicts, written by each dispatched refuter agent in Phase 4.2.5 (the `render-verify-brief` `--tmp-path` names this exact path), consumed by `consume-verdicts --verdicts` in the same sub-phase. Swept by the end-of-run `rm -rf "$WORKDIR"`.
- `$WORKDIR/parsed-verdicts-<refuter>.json` — `consume-verdicts` stdout per refuter (a DICT: `status` + a `verdicts` array). Written + read per refuter in Phase 4.2.5; its `.verdicts` array is extracted and concatenated into `verdicts.json`.
- `$WORKDIR/verdicts.json` — every refuter's `parsed-verdicts-<refuter>.json` array concatenated into ONE bare array. Written in Phase 4.2.5, read by `apply-verdicts --verdicts`.
- `$WORKDIR/applied-verdicts.json` — `apply-verdicts` stdout (a DICT: `confirmed` + `dismissed` + `uncertain` + `contested` buckets, with `contested` already `[CONTESTED]`-tagged). Written in Phase 4.2.5, read by the orchestrator to build `verified.json` (confirmed ∪ contested) and to carry the dismissed + uncertain appendix buckets into the Phase 4.5 report dict.
- `$WORKDIR/verified.json` — the bare HEADLINE working array = the `confirmed` bucket UNIONED with the `contested` bucket from `applied-verdicts.json` (so high-stakes `[CONTESTED]` findings get ranked and can appear in the Top-N). Written in Phase 4.2.5, read by `map-recurring-issues --findings` (and `force-rank-top10` on the single-file skip). Replaces `consensus-findings.json` / `merged.json` as the 4.3+ working list. The `dismissed` + `uncertain` appendix buckets are NOT in this file — they are carried separately into the Phase 4.5 report dict.
- `$WORKDIR/recurring-mapped.json` — `map-recurring-issues` stdout (a DICT: `findings` recurring-tagged + `recurring_status`). Written in Phase 4.3.
- `$WORKDIR/working.json` — the bare recurring-tagged `findings` array extracted from `recurring-mapped.json`. Written in Phase 4.3, read by `force-rank-top10 --findings`.
- `$WORKDIR/ranked.json` — `force-rank-top10` stdout (a DICT: `top` = ordered `[{finding, score}]`). Written in Phase 4.4, read by the orchestrator when building the report dict's `top10`.
- `$WORKDIR/report.json` — the assembled `render_report` input dict. Written in Phase 4.5, read by `render-report --report` (Phase 5) and `render-inline-summary --report` (Phase 6).

## Reference files

Read these in full at the phase where each is needed. The adversarial preamble + mislogic checklist + best-practices checklist are load-bearing prompt text — inject them VERBATIM into every agent invocation; do not paraphrase, summarize, or templatize them.

- `.claude/commands/audit/references/adversarial-preamble.md` — the ADVERSARIAL AUDIT MODE preamble (Phase 3, every agent).
- `.claude/commands/audit/references/mislogic-checklist.md` — the Mislogic Hunt Checklist (Phase 3, every agent).
- `.claude/commands/audit/references/best-practices-checklist.md` — the system-design + language/framework best-practices + duplication + constitution-principle adherence hunt checklist (Phase 3, every agent). Injected verbatim alongside the mislogic checklist; each section names the `Category` its findings carry.
- `.claude/commands/audit/references/refutation-preamble.md` — the REFUTATION / second-opinion preamble + the per-finding verdict output contract (Phase 4.2.5, every refuter). Load-bearing prompt text — `render-verify-brief` injects it verbatim into each refuter brief; do not paraphrase, summarize, or templatize it.
- `.claude/commands/audit/references/report-format.md` — the report skeleton `render-report` produces (orientation for Phase 5; the helper owns the actual render).
- `.claude/commands/audit/references/hotspot-scoring.md` — the risk-score formula, weights, defaults, and knobs for `--top N` mode (Phase 2, hotspot only).

## Helper interaction model

Every mechanical step is a normal Bash tool call to `.devforge/lib/audit_helper <verb> ...`. Each verb prints JSON (or a rendered block) to stdout. Most verbs that consume a prior verb's output take a `--<name> <path>` flag (not stdin), so capture stdout to the named `$WORKDIR/*.json` scratch file with `>` and pass that path into the next call — the per-phase fences below show the exact redirects. Re-establish `WORKDIR="${TMPDIR:-/tmp}/forge-audit"` at the top of every Bash block that touches scratch (the variable does not survive across Bash calls — see Preflight). On any non-zero exit, copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then follow the recovery note for that phase. The helper owns file structure, validation, and atomic writes; the orchestrator owns agent dispatch, the verbatim prompt text, user-facing prose, and phase pacing.

## Preflight — CBM refresh + state load

```bash
.devforge/lib/generate_docs_helper preflight
```

`/audit` is standalone and not part of the docs pipeline; this call is invoked here only to keep the CBM index fresh, which hotspot scoring (Phase 2.1) depends on. Refreshes the CBM index stamp so Phase 2 hotspot scoring and per-agent reference resolution see current code. Skip the call when `.devforge/.preflight-stamp` is fresher than 60 seconds — the stamp is already current. Check freshness with:

```bash
[ -f .devforge/.preflight-stamp ] && \
  [ "$(( $(date +%s) - $(stat -f %m .devforge/.preflight-stamp 2>/dev/null || stat -c %Y .devforge/.preflight-stamp) ))" -lt 60 ]
```

Exit 0 → stamp fresh; skip the helper call. Non-zero → run `.devforge/lib/generate_docs_helper preflight`. CBM is REQUIRED only for hotspot mode (Phase 2 gates on it per `.claude/commands/audit/references/hotspot-scoring.md`); narrow + broad modes degrade gracefully when CBM is absent.

Then initialize run state:

```bash
.devforge/lib/audit_helper check-status-and-flip --workspace-root . --to preflight
```

`check-status-and-flip` advances `audits/.state.json` to the named phase so an interrupted run can report where it stopped. Call it once at the start of each major phase with `--to <phase>` (`preflight`, `phase1`, `phase2`, `phase3`, `phase4`, `phase5`), and once at the very end of Phase 6 with `--to phase6 --status complete`. The per-phase calls are shown at each phase heading below; keep them lightweight (one call per boundary, no parsing of the output beyond the non-zero-exit check). `--to` accepts any label, so these phase names are a convention, not a helper-enforced enum.

Then establish + clear the scratch working directory:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-audit"
rm -rf "$WORKDIR" && mkdir -p "$WORKDIR"
```

**All intermediate scratch for this run lives in `$WORKDIR` (the fixed literal `${TMPDIR:-/tmp}/forge-audit`), OUTSIDE `audits/`.** This sidesteps an external process that reaps dot-prefixed files under `audits/` mid-run (it deleted pass-1 scratch in a 2-pass run; the non-dotfile dated report always survives). `$WORKDIR` is OUTSIDE the repo, so the scratch files need no leading dot (the dot-for-gitignore trick is unnecessary outside the work tree) and no Phase-6 `rm` list to keep them out of commits. The `rm -rf "$WORKDIR" && mkdir -p "$WORKDIR"` clears any stale scratch from a prior crashed run so an old pass pool cannot pollute this run's merge.

**CRITICAL — `$WORKDIR` is a FIXED LITERAL you re-derive in every Bash block; it does NOT persist across calls.** The orchestrator runs each Bash tool call in a FRESH shell, so shell variables (including `$WORKDIR`) do NOT carry from one Bash call to the next. A `mktemp -d` random dir would be unrecoverable on the next call because its name would be lost. So every Bash block that touches scratch MUST begin by re-establishing `WORKDIR="${TMPDIR:-/tmp}/forge-audit"` and then reference `"$WORKDIR/..."`. The literal is identical in every block, so each block reconstructs the same directory. Do NOT attempt to carry `$WORKDIR` across Bash calls — re-establish it at the top of each block.

## PHASE 1 — Load Context & Guard

```bash
.devforge/lib/audit_helper check-status-and-flip --workspace-root . --to phase1
```

Cheapest guards first; mode determination before any mode-conditional I/O.

### 1.1 — Resolve mode from `$ARGUMENTS`

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-audit"
.devforge/lib/audit_helper resolve-mode -- "$ARGUMENTS" > "$WORKDIR/mode.json"
```

Pass the raw argument string as a single positional after the `--` end-of-options separator. The `--` is REQUIRED: without it, argparse treats a leading `--full` / `--top` / `--uncommitted` as an unknown top-level flag and exits 2 before the subcommand runs. With `--`, the whole `$ARGUMENTS` string (including any leading dashes) is taken as the positional the verb parses. Stdout JSON carries the resolved `mode` (`narrow` / `hotspot` / `broad`), `scope_arg` (the path or the `--top N` value, or empty), and `uncommitted` (bool). Capture it to `$WORKDIR/mode.json` — `resolve-scope` (Phase 2.2) reads this exact file via `--mode-result`. (`$WORKDIR` was created in Preflight; re-establish the literal at the top of this block — the variable does not survive from Preflight's Bash call.) Empty `$ARGUMENTS` and `--full` both resolve to `broad`; `--top N` resolves to `hotspot`; a path or `--uncommitted` resolves to `narrow`. On unparseable input (e.g. more than one positional path) the verb sets a non-empty `error` field, writes the same message to stderr, and exits 2 — copy stderr VERBATIM and end the turn; the user re-invokes with a single valid argument shape.

Stdout also carries `passes` (int — the resolved pass count) and `passes_clamp_note` (string; empty unless the value was clamped). `resolve-mode` resolves `passes` as follows: when `--passes N` is given, it is the parsed value clamped to the range 1–3; when `--passes` is OMITTED, the verb defaults it by the resolved `mode` — `broad` → 2, `hotspot` → 2, `narrow` → 1. So the default is mode-conditional (commonly 2 for broad/hotspot, 1 for narrow), and an explicit `--passes N` always overrides that default. When `passes_clamp_note` is non-empty the verb has ALREADY written it to stderr (stdout stays pure JSON, exit 0); surface that note to the user as an FYI and continue the run with the clamped `passes` value — clamping is not an error. Carry `passes` forward.

**`passes` selects your EXECUTION STRUCTURE — decide it now, before Phase 3.** This is a fork, not an annotation you can defer. It keys on the RESOLVED `passes` value from `resolve-mode` (the mode-conditional default — commonly 2 for broad/hotspot and 1 for narrow — unless an explicit `--passes N` overrode it), NOT on a hardcoded constant:

- **`passes == 1` (the narrow-mode default, and any scope explicitly run with `--passes 1`):** run Phases 1→6 linearly; `merge-passes` is NEVER invoked; skip every "When `passes >= 2`:" branch below. This is the single-pass pipeline and it runs verbatim as written.
- **`passes >= 2` (the broad/hotspot default, and any scope explicitly run with `--passes 2`/`3`):** Phases 1–2 run once, then Phase 3 + Phase 4.1 become a LOOP BODY repeated `passes` times, then a single `merge-passes` replaces consensus, then Phases 4.3→6 run once. The controlling structure is defined in **Phase 3.0 (Multi-pass loop control)**, which you MUST read and follow before dispatching any agent — the per-iteration mechanics live inline in 3.1, 3.2, and 4.1, but 3.0 owns the loop shape.

Carry the `passes` value forward and commit to the matching structure before Phase 3.

### 1.2 — Agent-existence check (fail-fast)

```bash
.devforge/lib/audit_helper check-agents
```

Detects which of the four audit-capable agents exist in `.claude/agents/`: `code-reviewer`, `architect`, `qa-reviewer`, `security-reviewer`. The result is always JSON on **stdout** — `present` + `missing` lists plus an `all_missing` boolean; nothing is written to stderr. The verb exits **3** when `all_missing` is true (zero agents installed): copy the stdout JSON VERBATIM as a fenced block and end the turn — the user must re-run `update.sh` to (re)generate the agent files. When 1–3 exist (exit 0), proceed and carry the `missing` list forward for the report's "Agents skipped (not installed)" section.

### 1.3 — Preflight context + constitution guard

```bash
.devforge/lib/audit_helper preflight-context
```

Reads `constitution.md`, `CLAUDE.md` (Source Root, project type, framework, language), and `.claude/memory/MEMORY.md` (pitfalls, past incidents, lessons), and emits a structured context block on stdout for downstream phases. This verb is best-effort and ALWAYS exits 0 — the constitution guard is a JSON-field check, NOT an exit code: if the stdout JSON has `"constitution_populated": false` (the file is absent or still contains a populate-marker), STOP — tell the user VERBATIM "⛔ constitution.md has not been populated yet. Run `/constitute` before using `/audit`." and end the turn.

The context block carries the Source Root. `audits/` always lives at the **workspace root** (the directory containing `CLAUDE.md`), NEVER under Source Root, even in wrapper mode.

## PHASE 2 — Determine Scope

```bash
.devforge/lib/audit_helper check-status-and-flip --workspace-root . --to phase2
```

### 2.1 — Hotspot scoring (hotspot mode only)

For `--top N` mode, score every candidate file and take the top N. Read `.claude/commands/audit/references/hotspot-scoring.md` in full first — it defines the risk formula, default weights (`w_c=0.5, w_k=0.4, w_s=0.1`), the `--weights` knob, and the CBM-required gate.

**Step A — build the caller payload.** Caller counts come from CBM and must be supplied to the helper as a file — a subprocess helper cannot call MCP, so the orchestrator (which has the MCP tools) produces them. First enumerate the candidate source files (the same set the helper scores — tracked source files), then for each file resolve its inbound-edge count via CBM (`trace_path` inbound / `search_graph`, aggregated per file, per `.claude/commands/audit/references/hotspot-scoring.md`). Write the result to `$WORKDIR/callers.json` as a `{file: caller_count}` object — each value is EITHER a strict integer (the inbound-edge count) OR a list of caller qualified-names (the helper dedupes the list and uses its length). The two forms may be mixed across files; this mirrors the helper's `load_callers` contract. Files absent from the payload count as 0 at the merge step.

**Step B — score.** Capture the ranked result to `$WORKDIR/hotspot.json`:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-audit"
.devforge/lib/audit_helper compute-hotspots --top "$N" --callers "$WORKDIR/callers.json" [--weights c=0.5,k=0.4,s=0.1] > "$WORKDIR/hotspot.json"
```

The verb prints the ranked `HotspotResult` (top list + next-10 + per-file metrics) as JSON to stdout; the `>` redirect captures it into `$WORKDIR/hotspot.json`. The helper computes git churn (90-day commit count) and LOC itself, normalizes each metric min-max, and applies the weighted sum.

**CBM-required stop.** If `compute-hotspots` exits 2, the CBM caller payload is missing or unreadable — STOP, copy the helper's stderr VERBATIM, and tell the user to build the codebase-memory index first. Hotspot mode REQUIRES CBM (Decision 8); there is no grep fallback and scoring does not proceed without it. (Narrow + broad modes never reach this step and degrade gracefully when CBM is absent.)

**Step C — render the table.** On success, show the human-readable Top-N + Next-10 table:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-audit"
.devforge/lib/audit_helper render-hotspot-summary --hotspot "$WORKDIR/hotspot.json"
```

This reads `$WORKDIR/hotspot.json` and produces the top-N table plus the "Next 10 Candidates" tail (positions N+1..N+10); display it to the user. The same next-10 list also reaches the report via `render-report` (it embeds `next_candidates` in hotspot mode — Phase 4.5 copies it from `$WORKDIR/hotspot.json` into the report dict), so this is the inline preview, not the only place it appears. Skip 2.1 entirely for narrow + broad modes.

### 2.2 — Resolve the file set

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-audit"
.devforge/lib/audit_helper resolve-scope --mode-result "$WORKDIR/mode.json" > "$WORKDIR/scope.json"
```

`resolve-scope` reads the `$WORKDIR/mode.json` written in Phase 1.1 and turns the mode into an ordered file list; the `>` redirect captures its stdout to `$WORKDIR/scope.json` (read by `render-scope-block` and `render-agent-brief` below). For hotspot mode, also pass the ranked result so the helper extracts the top-N file list from it:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-audit"
.devforge/lib/audit_helper resolve-scope --mode-result "$WORKDIR/mode.json" --hotspot "$WORKDIR/hotspot.json" > "$WORKDIR/scope.json"
```

Directory narrow scope walks the subtree via `git ls-files <dir>` (tracked, gitignore-respecting, polyglot-safe; filesystem fallback for non-git roots). Stdout JSON includes the resolved `files` list, `file_count`, the `pipeline` depth (`simplified` for single-file; `full` for directory + uncommitted + hotspot + broad — Decision 10), and a `scope_oversize` flag (true when `file_count` exceeds `--scope-limit`, default 200 — Decision 11). Carry `files`, `file_count`, and `pipeline` forward — Phase 4 reads `pipeline` to gate recurring-issues mapping, and Phase 4.5 copies `files` into the report dict, renaming it to the report dict's `scope_files` key. On a non-empty `error` field, copy stderr VERBATIM and end the turn.

### 2.3 — Big-directory guard

If `resolve-scope` reports `scope_oversize: true`, gate before agent dispatch via AskUserQuestion (Decision 11). Question text is single-line; substitute `{N}` and `{path}` from the helper output:

> Auditing {N} files in {path} approaches broad-mode scope without --full's recurring-issues breadth. How do you want to proceed?

Options (2–4; AskUserQuestion auto-injects "Other"):

- `Risk-targeted sample` — re-run as `/audit --top 25` (recommended for periodic checks).
- `Whole codebase` — re-run as `/audit --full` (broad, with recurring-issues).
- `Proceed anyway` — continue with the current narrow scope.

On `Risk-targeted sample` or `Whole codebase`: tell the user the exact command to re-invoke and end the turn. On `Proceed anyway`: continue. When `scope_oversize` is false, proceed silently — no prompt.

### 2.4 — Render the scope block

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-audit"
.devforge/lib/audit_helper render-scope-block --scope "$WORKDIR/scope.json" --source-root <source-root>
```

Reads `$WORKDIR/scope.json` from 2.2 and produces the human-readable scope summary used in the report header (Phase 5). Substitute `<source-root>` with the Source Root from Phase 1.3 (the helper renders it into the block; `render-agent-brief` in Phase 3 takes the same `--source-root` so each agent reads from the correct location).

### 2.5 — Multi-pass cost guard (`--passes >= 2` only — Decision 7)

When `passes == 1`, skip this step entirely — there is no extra cost to gate, and the single-pass flow proceeds to Phase 3 unchanged.

When `passes >= 2`, estimate the multi-pass dispatch cost before any agent runs: the per-run agent-dispatch count is `passes × <agents present>` (the `present` count from Phase 1.2) `× <partitions>` (1 for ordinary scopes; the number of scope partitions for very large scopes per Phase 3.2). If `passes * file_count` (the `file_count` from `$WORKDIR/scope.json`, Phase 2.2) exceeds the `--scope-limit` threshold (the same default value (200) as 2.3's `--scope-limit`, but evaluated independently — `scope_oversize` from `$WORKDIR/scope.json` is NOT used here; the orchestrator computes `passes * file_count > scope_limit` directly), gate via AskUserQuestion before dispatching. The gate condition is `passes * file_count`; the `{dispatches}` estimate (`passes × agents × partitions`) is only the user-visible number shown in the question text, NOT the gate condition. Question text is single-line; substitute `{passes}`, `{N}` (= `file_count`), and `{dispatches}` (= the estimated total dispatch count above):

> Running {passes} audit passes over {N} files (~{dispatches} agent dispatches) is a large multi-pass run. How do you want to proceed?

Options (2–4; AskUserQuestion auto-injects "Other"):

- `Fewer passes` — re-run with `--passes 2` (or `--passes 1` for the standard single-pass audit).
- `Risk-targeted sample` — re-run as `/audit --top 25 --passes {passes}` (score the riskiest files, keep the passes).
- `Proceed anyway` — continue with `{passes}` passes over the current scope.

On `Fewer passes` or `Risk-targeted sample`: tell the user the exact command to re-invoke and end the turn. On `Proceed anyway`: continue to Phase 3. When `passes * file_count` is at or under the threshold, proceed silently — no prompt.

## PHASE 3 — Launch Adversarial Agents

```bash
.devforge/lib/audit_helper check-status-and-flip --workspace-root . --to phase3
```

Read `.claude/commands/audit/references/adversarial-preamble.md`, `.claude/commands/audit/references/mislogic-checklist.md`, and `.claude/commands/audit/references/best-practices-checklist.md` in full now. Their content is load-bearing and must reach each agent VERBATIM.

### 3.0 — Multi-pass loop control (when `passes >= 2`)

**Skip this entire subsection when `passes == 1`** — the single-pass flow runs 3.1 → 3.2 → Phase 4 linearly, exactly as written, and never reaches a merge.

When `passes >= 2`, this phase and Phase 4.1 are NOT a straight read — they are the body of an explicit loop you run `passes` times. Phases 1–2 already ran ONCE (mode, agents, context, and scope are stable across passes — do NOT re-resolve them); only agent dispatch (3.1 + 3.2) and per-agent consume+validate (Phase 4.1) repeat. Run this loop literally:

```bash
# passes >= 2 — execute this loop. Phases 1–2 already done ONCE.
# WORKDIR="${TMPDIR:-/tmp}/forge-audit" — re-establish at the top of each Bash block.
for pass in 1..passes:
    run 3.1 + 3.2  → dispatch all present agents → $WORKDIR/tmp-<agent>-p<pass>.md
    run 4.1 (multi-pass branch) → per-pass consume+validate → $WORKDIR/validated-p<pass>.json
# ONLY after the loop completes (all `passes` pools written):
run 4.2 (multi-pass branch) → merge-passes --pools "$WORKDIR/validated-p*.json" → $WORKDIR/merged.json
run 4.2.5 (refutation) ONCE on $WORKDIR/merged.json → $WORKDIR/verified.json
continue with 4.3 → 4.4 → 4.5 → Phase 5 → Phase 6 (ONCE)
```

**DO NOT run `merge-passes`, `compute-consensus`, refutation, recurring-mapping, ranking, or the report until you have completed all `passes` iterations of 3.1+3.2+4.1.** The merge consumes every pass's pool at once; reaching it after a single pass discards the recall the `--passes` flag exists to buy. **Refutation (4.2.5) runs exactly ONCE, after the K-loop AND the merge, on the single deduped `$WORKDIR/merged.json` working list — it is NOT inside the per-pass loop body** (the loop body is only 3.1+3.2+4.1; refutation judges each distinct merged finding once, not once per pass). Each iteration's agent temp files and validated pool MUST use the `-p<pass>` suffix (`$WORKDIR/tmp-<agent>-p<pass>.md`, `$WORKDIR/validated-p<pass>.json`) so passes do not overwrite each other.

**NO cleanup during the loop.** Do NOT run `rm`, or delete ANY file under `$WORKDIR`, at any point before Phase 5 has written the report. Every pass's scratch (`$WORKDIR/tmp-<agent>-p<pass>.md`, the per-pass pools `$WORKDIR/validated-p<pass>.json`, `$WORKDIR/mode.json`, `$WORKDIR/scope.json`, and every other file listed in the Intermediate-scratch inventory) MUST persist through the entire loop and the merge — `merge-passes` reads all per-pass pools at once AFTER the loop, so a pool deleted mid-loop is silently dropped from the union (this is the failure that produces a report built from later passes only, with "Multi-pass-confirmed findings: 0"). Cleanup happens exactly ONCE: the single `rm -rf "$WORKDIR"` at the very end of Phase 6 (after the inline summary). There is no earlier cleanup, ever. (Because `$WORKDIR` is outside `audits/`, the external reaper that deletes dot-prefixed files under `audits/` mid-run cannot touch any pass pool — moving scratch out of `audits/` is what makes the loop reaper-immune.)

The per-iteration mechanics live inline: 3.1 + 3.2 are the dispatch step of this loop body, Phase 4.1 (multi-pass branch) is the per-pass consume+validate step, and Phase 4.2 (multi-pass branch) is the single post-loop merge. Read those branches as steps of THIS loop, not as phases you reach by reading straight through. Phase 4.2.5 (refutation) is NOT a loop step — it runs once after the merge, on the merged working list, exactly as in single-pass (read it straight through after 4.2).

### 3.1 — Build each agent brief

First compute the **scope-aware finding cap** from the `file_count` in `$WORKDIR/scope.json` (Phase 2.2): `cap = min(60, max(30, file_count * 2))`. This raises the per-agent budget on dense scopes so exhaustive enumeration (the contract tells each agent to report every grounded instance of a recurring pattern, not one representative) is not choked by the flat 30-finding floor; it stays at 30 for small scopes and is bounded at 60 so a huge scope cannot blow up one agent's context. For example, a 29-file directory → `cap = 58`; a 5-file scope → `cap = 30`.

For each agent present (from Phase 1.2), passing the computed cap and the per-agent scratch temp path:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-audit"
.devforge/lib/audit_helper render-agent-brief --agent <agent> --scope "$WORKDIR/scope.json" --source-root <source-root> --finding-cap <cap> --tmp-path "$WORKDIR/tmp-<agent>.md"
```

`render-agent-brief` reads `$WORKDIR/scope.json` and the reference files under `--references-dir` (default `.claude/commands/audit/references` — leave it unset, that is the installed location). `--finding-cap` (default 30) is substituted into the output contract + closing reminder wherever the cap is named. `--tmp-path PATH` sets the EXACT path the brief tells the agent to write its findings to; pass `"$WORKDIR/tmp-<agent>.md"` so the temp lands in `$WORKDIR` (outside `audits/`, reaper-immune). If `--tmp-path` is omitted the brief defaults to the legacy `audits/.tmp-<agent>.md` location, so pass it every time. It assembles the structured brief in this order: the adversarial preamble, the mislogic checklist, the best-practices checklist (all three read verbatim from the reference files), the agent-specific focus block, the scope block (plus any `--extra-context-file` content appended to it), the output contract, and the closing mode reminder. The closing reminder is the LAST instruction in the brief so the most-recent instruction wins over the agent's baked-in polite tone.

**Constitution excerpts via `--extra-context-file` — standard for `/audit`.** The best-practices checklist's "Constitution-principle adherence" hunt only works when the constitution rules are present in the agent's brief — an agent cannot check the code against principles it cannot see. So the orchestrator SHOULD assemble a context file containing the project's constitution rules and pass it via `--extra-context-file <path>` to every agent, so each can hunt constitution-principle violations and tag them `[CONSTITUTION-VIOLATION]`. `preflight-context` (Phase 1.3) only reports whether the constitution is populated (the `constitution_populated` flag), NOT its text — so the orchestrator reads `constitution.md` directly (it lives at the workspace root, the CWD; Phase 1.3 confirms it is populated) and writes the relevant rules to a scratch file `$WORKDIR/context.md` (outside `audits/`, swept by the end-of-run `rm -rf "$WORKDIR"`), then passes that path via `--extra-context-file "$WORKDIR/context.md"`. MEMORY.md pitfalls and the recurring-issues list are still-optional additions to the same context file. When no constitution rules reach the brief, agents report none from the constitution-adherence section (per the checklist), and the rest of the full-spectrum hunt is unaffected.

Pass the rendered brief as the Task tool PROMPT. Do NOT save briefs (or any other intermediate) to extra files like `$WORKDIR/brief-*.txt`; pass the brief text straight to the Task prompt. The only files written under `$WORKDIR` are the documented scratch in the Intermediate-scratch inventory above — creating undocumented files pollutes the directory. Dispatching with `subagent_type: <agent>` ALREADY loads that agent's persona (`.claude/agents/<agent>.md`) as the subagent's system context — so do NOT prepend or re-inline the persona file into the brief. The persona comes from `subagent_type`; the brief carries only the audit-specific instructions on top of it. (This deviates from the stale draft, which manually prepended the persona; that predates Task subagents, which load it automatically.) The brief (via `--tmp-path`) instructs the agent to write its findings to `$WORKDIR/tmp-<agent>.md` in the fixed parseable format the output contract specifies (so Phase 4 can regex-parse them), and to write a temp file with `# Status: failed` + a `# Reason:` line on partial failure, or `# Status: complete` + `# Finding count: 0` when it finds nothing.

### 3.2 — Batched parallel dispatch

To avoid the context-exhaustion failure mode (CHANGELOG 1.27.0 for `/verify`), dispatch in two batches, not all four at once. Each batch is multiple Task calls issued in a single turn (true parallel); wait for both to complete before the next batch.

- **Batch A** (parallel): `code-reviewer` + `architect` → both write `$WORKDIR/tmp-<agent>.md` (the `--tmp-path` each brief carries).
- **Batch B** (parallel): `qa-reviewer` + `security-reviewer` → both write `$WORKDIR/tmp-<agent>.md` (the `--tmp-path` each brief carries).

Only dispatch agents that exist; skip the missing ones (already noted for the report). For very large scopes, run one scope partition through Batch A → Batch B before the next — do not fan out every partition in parallel.

**When `passes >= 2` — per-pass dispatch specifics** (this is the dispatch step of the 3.0 loop body; 3.0 owns the loop shape). For each `pass` iteration:

- Dispatch the present agents with the IDENTICAL two-batch parallel shape above (Batch A `code-reviewer` + `architect`, then Batch B `qa-reviewer` + `security-reviewer`), at the FULL scope-aware finding cap each pass (Decision 6 — do NOT divide the cap across passes; every pass gets the full budget computed in Phase 3.1). The only difference from single-pass: each agent writes to a per-pass temp file `$WORKDIR/tmp-<agent>-p<pass>.md`, named by passing `--tmp-path "$WORKDIR/tmp-<agent>-p<pass>.md"` on that pass's `render-agent-brief` call (substitute the literal pass number for `<pass>`). All per-pass temps live in `$WORKDIR`, outside `audits/`, so the reaper cannot touch them and the end-of-run `rm -rf "$WORKDIR"` sweeps them all at once.
- The brief is IDENTICAL across passes — recall gain comes from inherent agent nondeterminism, not from varied prompts. (Per-pass brief diversity is OQ-B, to be resolved by the Step-8 A/B test; do NOT vary briefs here.)

## PHASE 4 — Consolidate, Verify, & Rank

```bash
.devforge/lib/audit_helper check-status-and-flip --workspace-root . --to phase4
```

Stream agent outputs through the helper one at a time — do NOT load all findings from all agents into context at once. Every finding is validated against the actual source before it is accepted; adversarial mode invites hallucination and grounding is the antidote.

### 4.1 — Consume + validate per agent, then combine

For each agent in `code-reviewer`, `architect`, `qa-reviewer`, `security-reviewer` that wrote a temp file, parse it, extract the `findings` array, then validate that array:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-audit"
.devforge/lib/audit_helper consume-tmp --tmp "$WORKDIR/tmp-<agent>.md" --agent <agent> > "$WORKDIR/parsed-<agent>.json"
# Extract the .findings array from the parsed dict into a bare JSON array:
python3 -c "import json; print(json.dumps(json.load(open('$WORKDIR/parsed-<agent>.json'))['findings']))" > "$WORKDIR/findings-<agent>.json"
.devforge/lib/audit_helper validate-findings --findings "$WORKDIR/findings-<agent>.json" --repo-root . --source-root <source-root> > "$WORKDIR/validated-<agent>.json"
```

`consume-tmp` reads the agent temp file (`--tmp`) and regex-parses it into a result dict with `status` (`complete` / `clean` / `failed` / `missing`) and a `findings` array. `validate-findings` requires a BARE JSON array of finding dicts (it rejects a dict with exit 2), so extract `.findings` from the parsed dict first — the `python3 -c` line above does that. When `status` is `failed` or `missing`, record `{name: <agent>, reason: <reason>}` for the report dict's `agents_failed` and skip the agent (its `findings` array is empty, so it contributes nothing). `validate-findings` runs the anti-hallucination guard — file exists, line in range, evidence non-empty, pattern present, evidence quote grounded — and emits, per agent, a `passed` array (the findings that survived) plus a `discard_counts` tally (`file_missing`, `line_oob`, `evidence_empty`, `pattern_missing`, `quote_mismatch`). (Pass `--source-root` only when Source Root is a subdirectory; for `SOURCE_ROOT="."` omit it.)

After all four agents are validated, concatenate the `passed` array out of every `$WORKDIR/validated-<agent>.json` dict into one combined bare array and write it to `$WORKDIR/validated.json` (e.g. `python3 -c "import json,glob; out=[]; [out.extend(json.load(open(p)).get('passed',[])) for p in sorted(glob.glob('$WORKDIR/validated-*.json'))]; print(json.dumps(out))" > "$WORKDIR/validated.json"`). This combined array is what the next three steps operate on — cross-agent consensus only works when every agent's survivors are in one list. Also sum each agent's `discard_counts` (each `validated-<agent>.json`'s `discard_counts`) by failure class into one aggregate dict (the five keys above); Phase 4.5 copies the aggregate into the report dict.

**When `passes >= 2` — per-pass consume+validate, then pool.** This is the validate step of the 3.0 loop body — run it once per pass, inside the loop, BEFORE the post-loop merge (not after). In every command in this loop body, substitute `<pass>` with the current pass number (`1`, `2`, …) and `<agent>` with each agent name BEFORE running — running a command with a literal `<pass>` glob (e.g. `$WORKDIR/validated-*-p<pass>.json`) matches no files and silently yields an EMPTY pool, producing a misleadingly clean report with no error. Verify each per-pass pool file `$WORKDIR/validated-p<pass>.json` is non-empty before the merge (or legitimately empty because that pass's agents found nothing). For each pass, consume + validate each agent EXACTLY as the single-pass steps above do, but read the pass's temp file and write per-pass scratch names (the `-p<pass>` suffix is the only change):

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-audit"
.devforge/lib/audit_helper consume-tmp --tmp "$WORKDIR/tmp-<agent>-p<pass>.md" --agent <agent> > "$WORKDIR/parsed-<agent>-p<pass>.json"
python3 -c "import json; print(json.dumps(json.load(open('$WORKDIR/parsed-<agent>-p<pass>.json'))['findings']))" > "$WORKDIR/findings-<agent>-p<pass>.json"
.devforge/lib/audit_helper validate-findings --findings "$WORKDIR/findings-<agent>-p<pass>.json" --repo-root . --source-root <source-root> > "$WORKDIR/validated-<agent>-p<pass>.json"
```

The `status == failed`/`missing` handling and the per-agent `discard_counts` summing are unchanged — record `agents_failed` and sum the aggregate across ALL agent×pass `validated-<agent>-p<pass>.json` files (multi-pass aggregates over the full grid, not just four files). Then, after THIS pass's agents are validated, concatenate that pass's four agents' `passed` arrays into ONE bare array `$WORKDIR/validated-p<pass>.json` — the pass's "pool" (one file per pass, holding all of the pass's agents so the merge can compute both cross-agent and cross-pass corroboration):

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-audit"
python3 -c "import json,glob; out=[]; [out.extend(json.load(open(p)).get('passed',[])) for p in sorted(glob.glob('$WORKDIR/validated-*-p<pass>.json'))]; print(json.dumps(out))" > "$WORKDIR/validated-p<pass>.json"
```

(Mirrors the single-pass `validated.json` concatenation, but globs only THIS pass's per-agent files via the `-p<pass>` suffix.) Do NOT write `$WORKDIR/validated.json` in the multi-pass branch — the per-pass pool files feed the merge instead, and `compute-consensus` does not run (see 4.2).

**Each pass's scratch is consumed into its own pool within that pass's 4.1 and then LEFT IN PLACE — do NOT delete it when starting the next pass.** This pass's per-agent temps (`$WORKDIR/tmp-<agent>-p<pass>.md`) and its pool (`$WORKDIR/validated-p<pass>.json`) MUST survive untouched until the run ends: `merge-passes` (4.2) globs every `$WORKDIR/validated-p*.json` pool at once after the loop, so deleting pass N's pool before launching pass N+1 drops pass N from the union entirely. NEITHER the per-pass temps NOR the per-pass pools may be deleted mid-loop — the single end-of-run `rm -rf "$WORKDIR"` (Phase 6, after the inline summary) sweeps every pass's temps AND pools at once, at the very end of the run, never mid-loop.

**Loop-close:** if `pass < passes`, return to Phase 3.1 NOW for the next pass iteration (increment `pass`, re-dispatch agents, re-consume+validate). Do NOT proceed to 4.2 until all `passes` pool files `$WORKDIR/validated-p1.json` … `$WORKDIR/validated-p<passes>.json` exist — one per completed iteration of the 3.0 loop.

### 4.2 — Cross-agent consensus

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-audit"
.devforge/lib/audit_helper compute-consensus --findings "$WORKDIR/validated.json" > "$WORKDIR/consensus.json"
```

Reads the combined `$WORKDIR/validated.json` BARE ARRAY from 4.1 (it is already the concatenated `passed` arrays — no extraction needed). Exact-match grouping only (no LLM "is this similar" judgment) — the helper groups by `(file, line, category)`, so findings about the same bug at the same spot collapse to ONE representative even when worded differently (and a single agent's redundant re-reports of the same bug collapse too); the representative keeps the group's highest severity and carries a `merged_count` (how many raw findings collapsed into it). Corroboration is gated on ≥2 DISTINCT agents in a group: only then is the representative tagged `[CROSS-AGENT]`, bumped one severity level, and recorded in `consensus_map`. A group with only same-agent duplicates is deduped silently — no tag, no bump, not in `consensus_map`. The helper owns the group key, the severity bump, and the gate; do not semantically dedupe in the orchestrator. Stdout (captured to `$WORKDIR/consensus.json`) is a DICT carrying `findings` (the merged working list, each with `merged_count`) and `consensus_map` (`"<file>:<line>:<category>" -> [agent names]`, only for the ≥2-distinct-agent groups). The report dict's `consensus` key is derived from `consensus_map` — see Phase 4.5; the report annotates `(raised by N)` on any finding whose `merged_count > 1`.

Extract the merged `findings` array into a bare array for the next step (`map-recurring-issues` / `force-rank-top10` both require a bare array, not this dict):

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-audit"
python3 -c "import json; print(json.dumps(json.load(open('$WORKDIR/consensus.json'))['findings']))" > "$WORKDIR/consensus-findings.json"
```

**When `passes >= 2` — merge replaces consensus.** Do NOT run `compute-consensus` in the multi-pass branch. **Only after ALL `passes` iterations of the Phase 3.0 loop are complete — i.e. the `passes` pool files `$WORKDIR/validated-p1.json` … `$WORKDIR/validated-p<passes>.json` all exist — proceed:** union every pass pool with a single `merge-passes` call:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-audit"
.devforge/lib/audit_helper merge-passes --pools "$WORKDIR/validated-p*.json" > "$WORKDIR/merged.json"
```

`merge-passes` takes one-or-more pool paths (`--pools` is `nargs="+"`; the single quoted glob token is expanded, and the resolved paths are deduped + sorted so pass order is deterministic). Each pool file is EITHER a bare JSON array of finding dicts OR a `{"passed":[...]}` object — the per-pass `validated-p<pass>.json` pools are bare arrays. It unions all pools via tolerant location clustering and writes the BARE merged array to `$WORKDIR/merged.json`. Each merged finding carries `pass_count` (int) and is tagged `[MULTI-PASS:k]` when seen in ≥2 passes and `[CROSS-AGENT]` when ≥2 distinct agents appear in its cluster (severity is already bumped inside the merge — the orchestrator does not re-bump). On no-match / unreadable / malformed-JSON the verb exits 2 with a clean stderr message — copy stderr VERBATIM and end the turn.

`$WORKDIR/merged.json` is the multi-pass analogue of single-pass's `consensus-findings.json` (the BARE working array) and is what 4.2.5+ operate on. **Intentional tradeoff — no `consensus_map` in the multi-pass branch:** because `compute-consensus` is skipped, there is no `consensus_map`, so the multi-pass report dict sets `consensus` to `{}` (Phase 4.5). Cross-agent corroboration is not lost — it surfaces via the `[CROSS-AGENT]` tag and the already-applied severity bump on each merged finding; cross-pass corroboration surfaces via the `[MULTI-PASS:k]` tag plus the new Summary line (Phase 5). This is by design: the unified merge already did both cross-agent and cross-pass corroboration in one pass, so a separate consensus map would be redundant. Skip the `consensus.json`/`consensus-findings.json` steps above entirely.

### 4.2.5 — Refutation (cross-examination)

Refutation runs ONCE on the deduped working list, AFTER consensus (single-pass) or the merge (multi-pass) and BEFORE recurring-mapping. It is NOT per-pass — in multi-pass it runs a single time on `$WORKDIR/merged.json` after the whole Phase-3.0 loop + merge complete, never inside the loop. Its job is to invert the pipeline default from "assume a bug" to "assume correct unless proven": each finding is cross-examined by a non-author finder whose default verdict is NOT-a-bug, and only the survivors (`confirmed`) flow downstream to recurring-mapping and ranking. Read `.claude/commands/audit/references/refutation-preamble.md` in full now — it is the refuter brief text and the verdict output contract, injected by `render-verify-brief` and load-bearing.

The working list this sub-phase reads is the bare array `$WORKDIR/consensus-findings.json` (single-pass) or `$WORKDIR/merged.json` (**when `passes >= 2`**). Establish `$WORKING_FINDINGS` ONCE here, before Step A, and use it in BOTH the Step A `route-refutation` call and the Step D `apply-verdicts` call so the single-pass/multi-pass choice is made in exactly one place:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-audit"
# WORKING_FINDINGS = the deduped working array this sub-phase routes + partitions.
# Single-pass: $WORKDIR/consensus-findings.json (from 4.2). When passes >= 2: $WORKDIR/merged.json (from the 4.2 merge).
WORKING_FINDINGS="$WORKDIR/consensus-findings.json"   # set to "$WORKDIR/merged.json" when passes >= 2
```

The four steps below are a per-author dispatch loop.

**Step A — route each finding to a non-author refuter.** Pass the working list plus the present-finders list (the `present` array from the Phase-1.2 `check-agents` JSON, as a comma-separated list) and capture the routing map:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-audit"
# PRESENT_FINDERS = comma-joined "present" list from Phase 1.2 check-agents (ONLY finders that exist)
.devforge/lib/audit_helper route-refutation --findings "$WORKING_FINDINGS" --finders "$PRESENT_FINDERS" > "$WORKDIR/refutation-routes.json"
```

`route-refutation` groups the working list by each finding's `agent` (the representative author after consensus/merge dedup) and assigns each group the FIRST present finder, by the fixed priority order `[code-reviewer, architect, qa-reviewer, security-reviewer]`, that is NOT the author. Stdout (captured to `$WORKDIR/refutation-routes.json`) is a list of `{refuter, findings}` groups — each group is one refuter and the bare-array subset of findings routed to it. When the author is the only present finder, that sole finder self-refutes (degraded independence — note it in the report); the helper owns that edge case, the orchestrator does not special-case it. On a non-zero exit, copy the helper's stderr VERBATIM and end the turn.

**Step B — dispatch each refuter over its routed subset, in batches.** For each `{refuter, findings}` group in the routing map, write that group's `findings` subset to a scratch file (e.g. `$WORKDIR/refute-<refuter>.json`, a one-line `python3 -c` extraction of the group's `findings` from `$WORKDIR/refutation-routes.json`) and render that refuter's brief over its assigned subset:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-audit"
.devforge/lib/audit_helper render-verify-brief --findings "$WORKDIR/refute-<refuter>.json" --refuter <refuter> --references-dir .claude/commands/audit/references --scope "$WORKDIR/scope.json" --source-root <source-root> --tmp-path "$WORKDIR/verdicts-<refuter>.md"
```

`render-verify-brief` assembles the refuter prompt — the refutation preamble (read verbatim from `.claude/commands/audit/references/refutation-preamble.md` under `--references-dir`, the installed location) plus the assigned findings to cross-examine — and `--tmp-path` sets the EXACT path the brief tells the refuter to write its verdicts to; pass `"$WORKDIR/verdicts-<refuter>.md"` so the verdict file lands in `$WORKDIR` (reaper-immune). Substitute `<source-root>` with the Source Root from Phase 1.3. Pass the rendered brief as the Task tool PROMPT. Dispatching with `subagent_type: <refuter>` ALREADY loads that finder's persona — so do NOT prepend or re-inline the persona; the refutation preamble in the brief carries only the cross-examination instructions on top of it (the same persona-via-`subagent_type` model 3.1 uses). The brief instructs the refuter to write its fixed-format markdown verdicts to `$WORKDIR/verdicts-<refuter>.md` via Bash shell redirection (the refuter is a finder carrying `Bash`, so it writes the file exactly as the finders write `$WORKDIR/tmp-<agent>.md` in Phase 3 — no Write tool needed). **Dispatch the refuter groups in two batches** (mirroring the Phase 3.2 Batch A / Batch B pattern — multiple Task calls in a single turn, wait for the batch to complete before the next) to avoid context exhaustion; do not fan out all refuter groups at once. Each refuter judges ONLY its routed findings (a bounded set), not the whole working list. On a non-zero `render-verify-brief` exit, copy the helper's stderr VERBATIM and end the turn.

**Step C — parse each refuter's verdicts, then merge.** For each refuter dispatched, parse its verdict file into a bare verdict array, then concatenate all refuters' parsed arrays into one bare array:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-audit"
.devforge/lib/audit_helper consume-verdicts --verdicts "$WORKDIR/verdicts-<refuter>.md" --refuter <refuter> > "$WORKDIR/parsed-verdicts-<refuter>.json"
# After every refuter is parsed, extract each .verdicts array and concatenate into ONE bare array:
python3 -c "import json,glob; out=[]; [out.extend(json.load(open(p)).get('verdicts',[])) for p in sorted(glob.glob('$WORKDIR/parsed-verdicts-*.json'))]; print(json.dumps(out))" > "$WORKDIR/verdicts.json"
```

`consume-verdicts` regex-parses one refuter's fixed-format markdown verdict file (the `## Verdict N` blocks the refutation contract specifies) into a DICT carrying `status` (`complete` / `failed` / `missing`) and a `verdicts` array — the same dict shape `consume-tmp` returns. Pass `--refuter <refuter>` so a verdict missing the `# Refuter:` header is still attributed. The `python3 -c` line extracts each parsed dict's `.verdicts` array and concatenates every refuter's verdicts into `$WORKDIR/verdicts.json` — the merged verdict array `apply-verdicts` consumes (mirroring the per-agent `.passed`→`validated.json` concat in 4.1). When a refuter's `status` is `failed` or `missing`, its `verdicts` array is empty so it contributes nothing to the merge; the findings that refuter was routed are then absent from the verdict set, and `apply-verdicts` handles an unjudged finding per its own contract. On a non-zero `consume-verdicts` exit, copy the helper's stderr VERBATIM and end the turn.

**Step D — apply the verdicts and partition.** Partition the working list against the merged verdicts:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-audit"
# $WORKING_FINDINGS — established at the top of 4.2.5 — is the same working list Step A routed.
.devforge/lib/audit_helper apply-verdicts --findings "$WORKING_FINDINGS" --verdicts "$WORKDIR/verdicts.json" > "$WORKDIR/applied-verdicts.json"
# verified.json is the HEADLINE working set = the confirmed bucket UNIONED with the contested bucket
# (contested findings are already [CONTESTED]-tagged by apply-verdicts), so they get ranked and can
# appear in the Top-N flagged [CONTESTED]. dismissed + uncertain are the appendix — captured separately below.
python3 -c "import json; d=json.load(open('$WORKDIR/applied-verdicts.json')); print(json.dumps(d['confirmed'] + d['contested']))" > "$WORKDIR/verified.json"
```

`apply-verdicts` keys each verdict to its working-list finding by the `(file, line, pattern, agent)` tuple (the same tuple Phase 4.5 uses to match ranked findings back to ids) and partitions category-aware per the refutation design: it prints a DICT with four buckets — `confirmed` (survivors that earned their place), `dismissed` (the default verdict on undemonstrable findings), `uncertain` (low-stakes `mislogic` / `system_design` / `best_practice` / `duplication` / `blind_spot` findings the refuter could not resolve → the report appendix), and `contested` (high-stakes `security` / `[CONSTITUTION-VIOLATION]` findings the refuter returned `uncertain` on, plus any "dismiss" verdict on a grounded `[CONSTITUTION-VIOLATION]` — `apply-verdicts` tags each `[CONTESTED]`). The helper owns the verdict→bucket partition and the category routing; the orchestrator does not re-derive verdicts. `$WORKDIR/verified.json` is the HEADLINE working set = the `confirmed` bucket UNIONED with the `contested` bucket — contested findings are high-stakes findings the refuter could not confirm (or a dismissed grounded `[CONSTITUTION-VIOLATION]`), and the design requires them in the headline, so they join `verified.json` (already `[CONTESTED]`-tagged by `apply-verdicts`) rather than the appendix. The `confirmed + contested` array is the bare working list recurring-mapping (4.3) and force-rank (4.4) read in place of the raw working list, so the ranked Top-N can surface a high-stakes `[CONTESTED]` finding. Carry the `dismissed` and `uncertain` buckets forward from this `apply-verdicts` stdout (`$WORKDIR/applied-verdicts.json`) — those two are the appendix; Phase 4.5 reads them into the report dict's dismissed / uncertain fields (built in a later step; this sub-phase only captures them to the named scratch). On a non-zero `apply-verdicts` exit, copy the helper's stderr VERBATIM and end the turn.

### 4.3 — Recurring-issues mapping (broad + hotspot + directory/uncommitted; skip single-file)

**Gate (Decision 10).** Recurring-issues mapping runs in broad, hotspot, and narrow-DIRECTORY/uncommitted modes; it is skipped ONLY for narrow SINGLE-FILE. The signal is the `pipeline` field from `resolve-scope` (Phase 2.2): `simplified` (single file) → SKIP this whole step (the file is its own context); `full` (directory + uncommitted + hotspot + broad) → run it.

**Step A — build the recurring payload.** Glob `specs/*/review.md` modified within the last 90 days, take the 5 most recent, and extract their Critical findings ONLY (cap 25 total across all reviews). Write them to `$WORKDIR/recurring.json` as a `[{file, fingerprint}]` list. If no reviews qualify, write `[]` and note "No recent reviews to cross-reference." in the eventual summary. Track which review files you consulted — that list becomes the report dict's `recurring_reviews_consulted`.

**Step B — map.** The `--findings` input is the working list — the bare array `$WORKDIR/verified.json` (the headline set: confirmed ∪ contested) written at the end of 4.2.5, NOT raw `validated.json` and NOT the pre-refutation `consensus-findings.json` / `merged.json` (recurring tags must layer on top of the headline working list, so a dismissed or low-stakes-uncertain finding — neither of which is in `verified.json` — is never recurring-tagged). The same `verified.json` is the working list in both single-pass and multi-pass — 4.2.5 already collapsed the consensus / merge distinction into one headline array.

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-audit"
.devforge/lib/audit_helper map-recurring-issues --findings "$WORKDIR/verified.json" --recurring "$WORKDIR/recurring.json" > "$WORKDIR/recurring-mapped.json"
```

It maps each past finding against the working list — RESOLVED / RECURRING / RECURRING-SPREAD — by exact match, tags matched findings, and bumps their severity. This is the audit's differentiator over `/review`: it sees drift across features. Stdout (captured to `$WORKDIR/recurring-mapped.json`) is a DICT carrying `findings` (the working list, now recurring-tagged) and `recurring_status` (a `[{past, status}]` list). Derive the report dict's `recurring_resolved` / `recurring_unresolved` by splitting `recurring_status` on `status` (`RESOLVED` → resolved; `RECURRING` / `RECURRING-SPREAD` → unresolved). Algorithmic merging only — exact-match keys in the helper, never LLM semantic judgment. Extract the recurring-tagged `findings` array into a bare array for 4.4:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-audit"
python3 -c "import json; print(json.dumps(json.load(open('$WORKDIR/recurring-mapped.json'))['findings']))" > "$WORKDIR/working.json"
```

When this step is SKIPPED (single-file `simplified` pipeline), use `$WORKDIR/verified.json` from 4.2.5 (the headline set: confirmed ∪ contested — same file in single-pass and multi-pass) as the working list for 4.4 instead, and set the report dict's `recurring_resolved`, `recurring_unresolved`, and `recurring_reviews_consulted` to `[]`.

### 4.4 — Force-rank the Top N

The `--findings` input is the bare-array working list from the previous step — `$WORKDIR/working.json` when 4.3 ran, else `$WORKDIR/verified.json` (the single-file skip case — the headline set confirmed ∪ contested, same file in single-pass and multi-pass). Add `--narrow` ONLY for the single-file `simplified` pipeline (Top 5 instead of Top 10):

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-audit"
.devforge/lib/audit_helper force-rank-top10 --findings "$WORKDIR/working.json" [--narrow] > "$WORKDIR/ranked.json"
```

Scores survivors by severity × confidence × cross-agent × recurring weights and returns the ordered top slice. Deterministic given the working list. Stdout (captured to `$WORKDIR/ranked.json`) is a DICT carrying `top` — an ordered `[{finding, score}]` list (length 10, or 5 with `--narrow`). The report dict's `findings` and `top10` are BOTH derived from the SAME bare-array working list you just ranked (`$WORKDIR/working.json`, or `$WORKDIR/verified.json` on the single-file skip — the headline set confirmed ∪ contested, same file in single-pass and multi-pass) plus this ranking — see Phase 4.5.

### 4.5 — Assemble the report dict

Assemble the `render_report` input dict and write it to `$WORKDIR/report.json`. This is the single bundle `render-report` and `render-inline-summary` both consume.

**Finding-id assignment first.** The helper auto-assigns `finding_id` (`F-001`, `F-002`, …) in document order only at render time, so to build the `top10` and `consensus` keys (both keyed by finding_id) the orchestrator must assign the SAME ids up front. Take the FULL bare-array working list — `$WORKDIR/working.json` when 4.3 ran, else `$WORKDIR/verified.json` (the headline set confirmed ∪ contested, same file in single-pass and multi-pass) — and assign `finding_id` = `F-001`, `F-002`, … in that exact order. This id-assigned list is the report dict's `findings` — the ranked headline set, which already carries the `[CONTESTED]` tags `apply-verdicts` applied to its contested members (Phase 4.2.5 Step D); no extra tagging happens here. (The `dismissed` and `uncertain` appendix buckets captured in Phase 4.2.5's `$WORKDIR/applied-verdicts.json` are carried into the report dict's `dismissed` / `uncertain` fields by the rows added to the source table below; `render-report` consumes those keys to render the Dismissed / Worth-a-Glance appendix. There is no separate `contested` report-dict key — contested findings ride inside `findings`, `[CONTESTED]`-tagged.)

Then build the rest, each value sourced from an earlier step:

| Key                           | Source                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `mode`                        | Phase 1.1 `$WORKDIR/mode.json` `mode`                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `audit_date`                  | today's date `YYYY-MM-DD` (also passed via `--date` in Phase 5)                                                                                                                                                                                                                                                                                                                                                                                        |
| `scope_description`           | Phase 2.4 `render-scope-block` stdout                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `scope_files`                 | Phase 2.2 `$WORKDIR/scope.json` `files` field (renamed to `scope_files` in the report dict)                                                                                                                                                                                                                                                                                                                                                            |
| `agents_run`                  | Phase 1.2 `check-agents` `present`                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `agents_skipped`              | Phase 1.2 `check-agents` `missing`                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `agents_failed`               | Phase 4.1 — agents whose `consume-tmp` `status` was `failed` or `missing`, as `[{name, reason}]`                                                                                                                                                                                                                                                                                                                                                       |
| `findings`                    | the id-assigned full working list (above) — the ranked headline set (`$WORKDIR/verified.json` = confirmed ∪ contested; contested members already `[CONTESTED]`-tagged by `apply-verdicts`)                                                                                                                                                                                                                                                             |
| `dismissed`                   | Phase 4.2.5 — the `dismissed` bucket from `$WORKDIR/applied-verdicts.json` (the appendix; undemonstrable findings the refuter knocked down). Consumed by `render-report` for the Dismissed / Worth-a-Glance appendix                                                                                                                                                                                                                                   |
| `uncertain`                   | Phase 4.2.5 — the `uncertain` bucket from `$WORKDIR/applied-verdicts.json` (the appendix; low-stakes findings the refuter could not resolve). Consumed by `render-report` for the Dismissed / Worth-a-Glance appendix                                                                                                                                                                                                                                  |
| `top10`                       | the `finding_id`s of `$WORKDIR/ranked.json`'s `top` entries, in order — match each `top[i].finding` to its assigned id by `(file, line, pattern, agent)`. Ranked from `findings` (confirmed ∪ contested), so a high-stakes `[CONTESTED]` finding can appear here                                                                                                                                                                                       |
| `consensus`                   | `$WORKDIR/consensus.json` `consensus_map` re-keyed from its `"<file>:<line>:<category>"` keys → finding_id: for each group (one `consensus_map` entry, the ≥2-distinct-agent groups only), the matching finding's assigned `finding_id` maps to that group's agent list. **When `passes >= 2`: `{}` (empty) — there is no `consensus_map` in the multi-pass branch; cross-agent corroboration surfaces via the `[CROSS-AGENT]` tag instead (see 4.2)** |
| `recurring_resolved`          | Phase 4.3 — `recurring_status` entries with `status == "RESOLVED"` (skipped → `[]`)                                                                                                                                                                                                                                                                                                                                                                    |
| `recurring_unresolved`        | Phase 4.3 — `recurring_status` entries with `status` in `RECURRING` / `RECURRING-SPREAD` (skipped → `[]`)                                                                                                                                                                                                                                                                                                                                              |
| `recurring_reviews_consulted` | Phase 4.3 Step A consulted review paths (skipped → `[]`)                                                                                                                                                                                                                                                                                                                                                                                               |
| `discard_counts`              | Phase 4.1 aggregate across all four agents                                                                                                                                                                                                                                                                                                                                                                                                             |
| `source_root`                 | Phase 1.3 `preflight-context`                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `framework`                   | Phase 1.3 `preflight-context`                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `language`                    | Phase 1.3 `preflight-context`                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `next_candidates`             | Phase 2.1 `$WORKDIR/hotspot.json` `next_candidates` (hotspot only; omit otherwise)                                                                                                                                                                                                                                                                                                                                                                     |
| `passes_run`                  | Phase 1.1 `passes` (**multi-pass only — set to `N` when `passes >= 2`** so the Phase 5 `--passes-run` flag and the Summary's multi-pass line render; omit on single-pass (if present and set to `1`, the render is byte-identical — both forms are correct; omitting it is the conventional single-pass form))                                                                                                                                         |

The key names above are the exact ones `render_report` reads — do not rename or add keys it does not consume. (`render-inline-summary` reads the same dict plus an optional `out_path`; set `out_path` to the path `render-report` prints, before calling Phase 6.)

## PHASE 5 — Write Report

```bash
.devforge/lib/audit_helper check-status-and-flip --workspace-root . --to phase5
```

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-audit"
.devforge/lib/audit_helper render-report --report "$WORKDIR/report.json" --audits-dir audits --date <YYYY-MM-DD>
```

Reads the assembled `$WORKDIR/report.json` from Phase 4.5, renders the full audit markdown (skeleton documented in `.claude/commands/audit/references/report-format.md`), and writes it to `audits/YYYY-MM-DD-audit.md` at the workspace root, appending `-2`, `-3`, … on a same-day collision. `--audits-dir audits` is the report's OUTPUT directory and stays `audits` — the report is the one artifact that lives in `audits/` (it is a non-dotfile, so the reaper leaves it alone), while its input dict comes from `$WORKDIR`. The helper creates `audits/` and a first-run `audits/.gitignore` (`.tmp-*.md`) as needed (the `.gitignore` is now effectively a no-op, kept for backward compatibility — agent temps live in `$WORKDIR`, not `audits/`). Stdout reports the exact written path.

**When `passes >= 2`**, add `--passes-run <N>` (the `passes` value) so the Summary emits a `- Passes run: N | Multi-pass-confirmed findings: <count>` line (count = findings with `pass_count >= 2`):

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-audit"
.devforge/lib/audit_helper render-report --report "$WORKDIR/report.json" --audits-dir audits --date <YYYY-MM-DD> --passes-run <N>
```

`--passes-run` defaults to 1; single-pass omits the flag and the Summary renders byte-identical to a pre-multi-pass run (no multi-pass line). Pass it ONLY when `passes >= 2`.

No cleanup happens here. All scratch lives in `$WORKDIR` (outside `audits/`), and `$WORKDIR` is removed in a single `rm -rf` at the very end of Phase 6 — after `render-inline-summary` (Phase 6) has read `$WORKDIR/report.json`. (The `cleanup-tmps` verb still exists in the helper but is no longer called: with no scratch landing in `audits/`, sweeping `audits/.tmp-*.md` has nothing to do — the workdir `rm -rf` supersedes it.)

**Do NOT commit. Do NOT stage.** Let the user decide whether to keep the audit in git history. (The run is marked `complete` only at the very end of Phase 6, once the report is written AND the summary is shown — see below.)

## PHASE 6 — Present Inline Summary

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-audit"
.devforge/lib/audit_helper render-inline-summary --report "$WORKDIR/report.json"
```

`render-inline-summary` reads the same report dict as `render-report` (set its `out_path` to the path `render-report` printed in Phase 5 so the block can cite the file). It prints the count-first inline block — total findings by severity, cross-agent consensus count, recurring-unresolved count, agents skipped, findings discarded by validation, the Top 5 priorities, and the report path. This follows the audit-format discipline (count first; the most important findings named). Copy the helper's stdout VERBATIM into your final user-facing message as a fenced code block, then tell the user the report is not committed — review, then commit if they want audit history in git, or delete.

**Multi-pass partial degradation (`--passes >= 2`, OQ-D — degrade, don't fail).** If a pass produced zero validated findings (every agent in it was empty or failed), `merge-passes` still unions whatever pool files DO exist (it globs `$WORKDIR/validated-p*.json`), so the run completes on the passes that contributed. When fewer than N passes contributed findings, note "ran K of N passes" in your final user-facing message alongside the inline summary so the user knows the recall budget was not fully spent. Keep this light — one sentence; do not build elaborate recovery.

Finally, delete the entire scratch working directory in one step — `render-inline-summary` above was the last reader of `$WORKDIR/report.json`, so nothing else needs the scratch:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-audit"
rm -rf "$WORKDIR"
```

This single `rm -rf` sweeps every scratch file at once — single-pass (`mode.json`, `scope.json`, the per-agent `parsed-*`/`findings-*`/`validated-*`, `validated.json`, `consensus.json`, `consensus-findings.json`, the refutation scratch `refutation-routes.json`/`refute-<refuter>.json`/`verdicts-<refuter>.md`/`parsed-verdicts-<refuter>.json`/`verdicts.json`/`applied-verdicts.json`/`verified.json` (refutation runs once; no per-pass analogues), `recurring.json`, `recurring-mapped.json`, `working.json`, `ranked.json`, `report.json`, the agent temps `tmp-<agent>.md`) AND multi-pass (the per-pass `*-p<pass>` analogues, the pools `validated-p<pass>.json`, `merged.json`, and the per-pass temps `tmp-<agent>-p<pass>.md`). Because `$WORKDIR` is outside the repo, there is no gitignore concern and no per-file `rm` list to maintain. (The `cleanup-tmps` verb that previously swept `audits/.tmp-*.md` in Phase 5 is superseded — no scratch lands in `audits/` anymore, so it is not called.)

Then mark the run complete so an interrupted re-run can distinguish a finished audit from a stopped one:

```bash
.devforge/lib/audit_helper check-status-and-flip --workspace-root . --to phase6 --status complete
```

## Important rules

1. **Read-only** — no source modifications, no fixes, no auto-commit of the report.
2. **Standalone** — `/audit` is never invoked by another command, never part of any chain, never auto-triggered.
3. **Evidence-first adversarial mode** — every finding must be grounded in a verbatim quote from real code; `validate-findings` discards ungrounded ones, and the refutation stage (Phase 4.2.5) cross-examines each finding before ranking, dismissing the false positives that survive grounding. A real quote of correct code is not a finding.
4. **Constitution violations are always Critical** — never downgraded, regardless of confidence.
5. **Critique code, not people** — findings describe what is wrong with the code, never who is wrong.
6. **Algorithmic merging only** — consensus groups by exact-match `(file, line, category)` keys and recurring tags by exact-match keys, both in the helper, never LLM semantic judgment.
7. **Dated reports, not overwritten** — same-day re-runs append a numeric suffix; history is preserved.
8. **Not committed** — all intermediate scratch lives in `$WORKDIR` (`${TMPDIR:-/tmp}/forge-audit`), outside the repo, so it never reaches a commit; the report in `audits/` is left unstaged for the user's keep/delete decision.
9. **Context-aware batching** — two-batch dispatch + stream consolidation; never fan out all agents on all files at once, never load all findings into context at once.
10. **Skip missing agents gracefully** — note them in the report; fail only if all four are missing.
11. **Wrapper-mode aware** — pass Source Root to every agent for source files; `audits/` always lives at the workspace root.
12. **Cleanup is last, never mid-run** — no `rm` or deletion of ANY file under `$WORKDIR` until Phase 5 has written the report; in multi-pass, all per-pass scratch (`tmp-<agent>-p<pass>.md`, `validated-p<pass>.json`) persists through the whole loop + merge and is swept only at the very end by the single `rm -rf "$WORKDIR"` in Phase 6 (after the inline summary).
