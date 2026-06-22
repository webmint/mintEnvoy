---
name: finalize
description: The terminal PR-prep step for a completed feature. Runs after `/summarize`. Dispatches the tech-writer agent for surgical `docs/` updates (retargeted to live `docs/<package>/` locations), then squashes the feature's accumulated `[WIP]`/`[checkpoint]` commits into one clean commit (in wrapper mode also the source repo). MUTATING: rewrites local git history and writes `docs/`. The squash is gated behind explicit user confirmation. Terminal — its next step is "create a PR".
argument-hint: "[spec-file]"
disable-model-invocation: true
---

# /finalize — Terminal PR-Prep (Surgical Docs + History Squash)

`/finalize` is the LAST step in the pipeline `… /implement → /review → /verify → /summarize → /finalize`. It owns the ONE job nothing else in the pipeline owns: **the terminal PR-prep step** — surgical feature-completion docs plus git history cleanup. `/verify` owns the verdict, `/review` owns findings, `/summarize` owns the PR-ready narrative; `/finalize` owns the clean commit and the surgical docs that ship with it. State + render shape are owned by `.devforge/lib/finalize_helper`; the orchestrator dispatches the `tech-writer` agent, composes the commit subjects, gets the user's squash confirmation, and paces the phases.

**`/finalize` DISPATCHES an agent AND MUTATES — the inverse of `/summarize` on both axes.** It dispatches the `tech-writer` agent (in Normal/surgical mode) and it rewrites local git history (the squash) and writes `docs/`. It does NOT verify (that is `/verify`), does NOT find issues (that is `/review`), and does NOT synthesize the PR narrative (that is `/summarize`). It runs NO finder ensemble, NO refutation pass, and renders NO verdict. The destructive squash is gated behind an explicit user confirmation.

`/finalize` is TERMINAL: there is no next-pipeline-command pointer. After it runs, the user's next step is to create a PR.

Usage: `/finalize` (auto-resolve the most-recently-modified `specs/NNN-*` feature) · `/finalize specs/001-auth` or `/finalize specs/001-auth/spec.md` (an explicit feature dir or a spec file inside it).

## Maintainer note

This file lives at `src/commands/finalize/main.md` in the AIDevTeamForge template repo and is the SSOT for the `/finalize` command. Do NOT inject project-specifics — this spec is substituted + emitted into target projects by the build. Helper paths use the installed `.devforge/lib/...` location because that's where they resolve at runtime in the target project. Reference-file paths are written author-relative (`references/<file>.md`); the emitter rewrites them to `.claude/commands/finalize/references/<file>.md` at install time.

## Outputs of this command

The things this command writes under the repo are:

- `docs/` — surgical, feature-driven documentation updates authored by the `tech-writer` agent (PHASE 2), retargeted to the LIVE `docs/<package>/<concern>/index.md` Hazards, `docs/<package>/architecture.md`, and `docs/architecture.md` locations (the dropped Plan-F per-feature tier is never resurrected — see `.claude/commands/finalize/references/results-and-docs.md`). The agent may justifiably write nothing.
- A single clean feature commit (PHASE 3) — the install/wrapper repo's `[WIP]`/`[checkpoint]` commits squashed into one `feat(<feature-name>): <title>` commit (with attribution per config). In wrapper mode the source repo is ALSO squashed into one `[TICKET-ID] - Description` commit with NO AI traces (D5).
- An interim `[WIP]` docs commit (PHASE 2, only when tech-writer wrote docs) — folded into the squash, so it leaves no separate commit in the final history (D8).

`/finalize` is STATELESS: it writes no run-state file. The squash is a single idempotent operation — re-running it on an already-finalized feature no-ops ("Nothing to finalize").

### Intermediate scratch files (orchestrator-written, helper-consumed) — all under `$WORKDIR`

The helper cannot dispatch agents (a subprocess has no Task/MCP tools), so each phase captures a verb's stdout JSON to an intermediate scratch file under `$WORKDIR` that a later phase reads. All live under `$WORKDIR` (`${TMPDIR:-/tmp}/forge-finalize`) and are scratch state for one run — the whole directory is removed by the single PHASE-4 `rm -rf "$WORKDIR"`. Because `$WORKDIR` is outside the work tree, the files need no leading dot and no gitignore handling.

- `$WORKDIR/preflight.json` — the `preflight` stdout (`source_root`, `wrapper_mode`, `spec_status`, `spec_complete`, `has_wip_commits`, `wip_commit_count`, `framework`, `language`, …). Written in PHASE 0, read by the orchestrator for the `source_root` + `wrapper_mode` values it branches on, and for the WIP/checkpoint no-op signal.
- `$WORKDIR/changes.json` — the `gather-change-data` stdout (`files`, `files_for_finders`, `file_count`, `scope_block`, `merge_base`, `source_changes`). Written in PHASE 1, read by the orchestrator for the tech-writer brief and the PHASE-4 file count.
- `$WORKDIR/squash-base.json` — the `resolve-squash-base` stdout (`install_squash_base`, `source_squash_base`, `strategy`, `is_feature_branch`, `default_branch`). Written in PHASE 3, read by the orchestrator to confirm a base exists before presenting the squash for confirmation.
- `$WORKDIR/pushed.json` — the `check-pushed` stdout (`is_pushed`, `commit_count`, `branch`, `no_upstream`). Written in PHASE 3, read by the orchestrator for the already-pushed guard.
- `$WORKDIR/squash.json` — the `squash` stdout (`confirmed`, `install_repo`, `source_repo`, `error`). Written in PHASE 3, read by the orchestrator for the PHASE-4 results block.

## Reference files

- `.claude/commands/finalize/references/results-and-docs.md` — the LIVE `docs/` targets the PHASE-2 tech-writer brief retargets to (and the dropped Plan-F tiers it must never resurrect) plus the PHASE-4 "Feature Finalized" results-block shape (orientation only — both are composed inline; there is no helper verb for either).

## Helper interaction model

Every mechanical step is a normal Bash tool call to `.devforge/lib/finalize_helper <verb> ...`. Each verb prints JSON to stdout; capture it to the named `$WORKDIR/*.json` scratch file with `>` and read that file in the phase that needs it — the per-phase fences below show the exact redirects. Re-establish `WORKDIR="${TMPDIR:-/tmp}/forge-finalize"` at the top of every Bash block that touches scratch (the variable does not survive across Bash calls — see PHASE 0). On any non-zero exit, copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then follow the recovery note for that phase. The helper owns the preflight/gate, the change-data + squash-base + already-pushed computation, the ticket-ID derivation, and the squash execution (including the in-helper already-pushed refusal and the `--confirm` gate); the orchestrator owns the tech-writer dispatch, the docs `[WIP]` commit, the explicit squash confirmation, the results block, and phase pacing. **No verdict is rendered and no finder ensemble runs anywhere in this flow.**

## PHASE 0 — Preflight + feature resolution + the spec-Complete gate + no-op detection + scratch

Cheapest guards first; preflight before any feature I/O.

### 0.1 — Resolve the feature directory

Resolve the feature dir from `$ARGUMENTS`:

- When `$ARGUMENTS` names a feature directory (`specs/NNN-<slug>`) or a file inside one (e.g. `specs/001-auth/spec.md`), use that feature directory (strip a trailing filename to the `specs/NNN-<slug>` dir).
- When `$ARGUMENTS` is empty, auto-resolve the most-recently-modified `specs/NNN-*` directory (the feature most likely just finished `/summarize`).

If no `specs/NNN-*` directory exists, tell the user there is no feature to finalize (run `/specify` → `/plan` → `/breakdown` → `/implement` → `/review` → `/verify` → `/summarize` first) and end the turn. Carry the resolved feature dir forward as `<feature>` — the spec file inside it is `<feature>/spec.md` (the `--spec` value 0.2 needs).

### 0.2 — Preflight + the spec-Complete gate + the no-op signal

```bash
.devforge/lib/finalize_helper preflight --workspace-root . --spec <feature>/spec.md > /tmp/finalize-preflight-check.json
```

`preflight` checks the 4-command setup chain (`/init-forge → /generate-docs → /configure → /constitute`) AND the spec `**Status**: Complete` gate, AND detects the `[WIP]`/`[checkpoint]` commits that back the "Nothing to finalize" no-op. It ALWAYS writes its JSON context block to stdout BEFORE any gate check, then exits:

- **2** — a setup-chain artefact is missing. On exit 2, copy the helper's stderr VERBATIM as a fenced code block and end the turn — the user runs the named missing command first.
- **3** — the spec is not `**Status**: Complete` (or the spec is absent). `/finalize` runs AFTER `/verify` flips the spec to Complete on an APPROVED verdict, so a non-Complete spec means `/verify` has not yet approved this feature. On exit 3, copy the helper's stderr VERBATIM as a fenced code block and end the turn (the message names the current spec status and instructs the user to run `/verify` first).
- **0** — both gates pass. The stdout JSON carries `source_root` (the project's Source Root — `.` for a standalone install, the inner project subdir in wrapper mode), `wrapper_mode`, `spec_status`, `spec_complete`, `has_wip_commits` (the no-op signal), `wip_commit_count`, `framework`, and `language`.

(`$WORKDIR` is not established until 0.4, so this gate call captures to a fixed `/tmp` path; 0.4 re-runs `preflight` into `$WORKDIR/preflight.json` once the scratch dir exists. `preflight` is read-only and cheap, so running it twice is harmless.) Carry `source_root`, `wrapper_mode`, and `has_wip_commits` forward. These values are available from the 0.2 capture, OR — simpler — read them from `$WORKDIR/preflight.json` after 0.4 re-runs `preflight` (both are identical; reading from `$WORKDIR` after 0.4 is the path later phases use).

### 0.3 — The "Nothing to finalize" no-op + the missing-summary soft-warn

Read `has_wip_commits` from the preflight stdout (the 0.2 JSON):

- **No-op gate.** If `has_wip_commits` is `false`, there are no `[WIP]`/`[checkpoint]` commits to squash. Tell the user _Nothing to finalize — no `[WIP]`/`[checkpoint]` commits remain; the feature may have already been finalized._ and end the turn. This is the idempotent no-op (re-running `/finalize` on an already-finalized feature lands here), not an error.
- **Missing-summary soft-warn.** Check whether `specs/[feature]/summary.md` exists. If it is absent, warn the user (do NOT stop): _No `summary.md` found — run `/summarize` first for the richest feature record. Proceeding without a summary._ Then continue — `/finalize` does not require `summary.md`; its presence only means the summary's `[WIP]` commit folds into the squash. Carry the present/absent state forward for the PHASE-4 results block (`Summary: included in squash | not found`).

### 0.4 — Establish the scratch dir + persist the context

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-finalize"
rm -rf "$WORKDIR" && mkdir -p "$WORKDIR"
```

**All intermediate scratch for this run lives in `$WORKDIR` (the fixed literal `${TMPDIR:-/tmp}/forge-finalize`), OUTSIDE the repo.** The literal is `forge-finalize`, NOT `forge-summarize`, `forge-verify`, `forge-review`, or `forge-audit` — those commands may run concurrently, and a shared workdir would corrupt every run. `$WORKDIR` is outside the work tree, so the scratch files need no leading dot, no gitignore handling, and no per-file `rm` list. The `rm -rf "$WORKDIR" && mkdir -p "$WORKDIR"` clears any stale scratch from a prior crashed run.

**CRITICAL — `$WORKDIR` is a FIXED LITERAL you re-derive in every Bash block; it does NOT persist across calls.** The orchestrator runs each Bash tool call in a FRESH shell, so shell variables (including `$WORKDIR`) do NOT carry from one Bash call to the next. So every Bash block that touches scratch MUST begin by re-establishing `WORKDIR="${TMPDIR:-/tmp}/forge-finalize"` and then reference `"$WORKDIR/..."`. The literal is identical in every block, so each block reconstructs the same directory.

Now re-capture the preflight context into `$WORKDIR` so later blocks can re-read its `source_root` / `wrapper_mode` values (the gates already passed in 0.2; this just persists the context to the scratch dir):

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-finalize"
.devforge/lib/finalize_helper preflight --workspace-root . --spec <feature>/spec.md > "$WORKDIR/preflight.json"
```

## PHASE 1 — Gather change data

Compute the assembled-feature change data — the union of every change the feature made across all the WIP commits `/implement` accumulated (squashed only by this command, below). Read `wrapper_mode` and `source_root` from `$WORKDIR/preflight.json` (PHASE 0) and branch on them:

- **Standalone install** (`source_root` is `"."`): pass `--feature-dir <feature>` ONLY. Omit `--source-root` and `--install-root` — the helper defaults both to `"."`, which is correct here.
- **Wrapper mode** (`source_root` is NOT `"."` per `preflight.json`): pass `--feature-dir <feature> --source-root <source-root> --install-root <install-root>`. `--source-root` is the code repo (the inner project subdir, the `source_root` value); `--install-root` is the forge install root where `.devforge/` lives (the wrapper root — typically the cwd `.`). **Both flags are mandatory in wrapper mode.** If `--install-root` is omitted the helper defaults it to `source_root` — then `abs_source == abs_install`, the wrapper-mode guard never fires, and `source_changes` is silently `null`, dropping the source-repo change set from the tech-writer brief.

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-finalize"
# Standalone (source_root == "."): --feature-dir only.
# Wrapper mode (source_root != "." per preflight.json): ALSO pass
#   --source-root <source-root> --install-root <install-root>
.devforge/lib/finalize_helper gather-change-data \
  --feature-dir <feature> \
  [--source-root <source-root> --install-root <install-root>  # wrapper mode only] \
  > "$WORKDIR/changes.json"
```

`gather-change-data` resolves the assembled-feature diff via the shared scope resolver (the same `_shared.feature_scope` resolver `/review`, `/verify`, and `/summarize` use, with the heading label "Finalize Scope"). The base ref auto-detects via `origin/HEAD → main → develop → master`; pass `--base <ref>` when auto-detection fails (the stderr message says so). Stdout JSON carries `files` (sorted source-relative changed paths), `files_for_finders` (the same list, source-root-prefixed in wrapper mode), `file_count`, `scope_block`, `merge_base`, and `source_changes` (non-null in wrapper mode — same keys scoped to the source repo, or `{"error": ...}` on a non-fatal source-side resolve failure). On a non-zero exit (not a git repo, bad ref, no auto-detectable base), copy the helper's stderr VERBATIM and end the turn.

Carry the `files` list and `file_count` forward: the file list is the tech-writer brief's changed-files input (PHASE 2), and `file_count` is the PHASE-4 results-block file count. In wrapper mode, include the source-repo `files` in the brief too (so the agent sees the actual code changes, not only the wrapper-side specs/docs) — but only when `source_changes` has no `error` key (PHASE 2 carries the explicit guard; `{"error": ...}` is itself non-null, so test for the key, not for non-null).

## PHASE 2 — Surgical docs (dispatch the tech-writer agent)

Dispatch the `tech-writer` agent in its Normal/surgical mode over the feature's changed files, RETARGETED to the LIVE Plan-F doc locations. `.claude/commands/finalize/references/results-and-docs.md` documents the exact targets — `docs/<package>/<concern>/index.md` Hazards, `docs/<package>/architecture.md`, and `docs/architecture.md` — and the dropped Plan-F tiers the agent must never resurrect. **Point the agent ONLY at those three live locations**; a new concern / API surface / domain term is left to `/generate-docs`, not hand-authored here.

Compose the agent's brief from the inputs its `#### Input You Receive` section names for `/finalize` — the feature `spec.md`, the feature's task files under `<feature>/tasks/`, and the aggregated list of changed files — plus the retarget instruction and the feature's `plan.md` for architecture context:

- **Feature spec** — `<feature>/spec.md` (what was built and why).
- **Plan** — `<feature>/plan.md` (architecture decisions and data flow).
- **Task files** — every `<feature>/tasks/*.md` except `README.md`.
- **Changed files** — the `files` list from `$WORKDIR/changes.json` (the assembled-feature diff). In wrapper mode, FIRST check whether `source_changes` has an `error` key; if it does, OMIT the source files from the brief and warn the user the source-repo scope could not be resolved; otherwise include the `source_changes.files` list too.
- **Retarget instruction** — "Run in Normal/surgical mode. Update only the LIVE Plan-F doc locations: `docs/<package>/<concern>/index.md` Hazards, `docs/<package>/architecture.md`, `docs/architecture.md`. Do NOT create or write under the dropped Plan-F per-feature / per-resource / per-guide tiers (see `.claude/commands/finalize/references/results-and-docs.md` for the exact dropped paths). Use your document-when / skip-when criteria; if no feature-level docs are warranted, say so and write nothing."

Dispatch with `subagent_type: tech-writer` (this loads the agent's persona from `.claude/agents/tech-writer.md` as the subagent's system context — do NOT prepend or re-inline the persona into the brief; the brief carries only the inputs and the retarget instruction above on top of it). This is the same orchestrator-dispatches-subagent pattern `/verify` uses for `ac-verifier` — one agent dispatch inside an orchestrator that keeps running afterward (NOT a whole-command fork).

Handle the three outcomes:

- **Docs written.** If the agent created or updated docs, `[WIP]`-commit them so they fold into the squash (D8 — docs BEFORE the squash). Stage and commit ONLY `docs/`:

```bash
git add docs/ && git commit -m "[WIP] Feature docs: <NNN-slug>"
```

Carry the written-docs targets forward for the PHASE-4 results block (`Docs: updated <targets>`).

- **Justified skip.** If the agent reports no feature-level docs are needed (internal refactoring, no public-facing change), accept the justification and write nothing. Carry the skip reason forward (`Docs: skipped — <reason>`).
- **Agent failure.** If the agent errors, times out, or hits a context limit, warn the user (_tech-writer failed: `<error>` — feature docs may be incomplete; proceeding with the squash, you may need to update docs manually after the PR_) and PROCEED to PHASE 3 — a docs failure does NOT block the squash. Carry the failure forward (`Docs: tech-writer failed — <error>`).

## PHASE 3 — Squash (confirmation-gated)

Squash the feature's `[WIP]`/`[checkpoint]` commits (including the PHASE-2 docs commit) into one clean commit. **The squash MUTATES local git history (D4); it runs only after the user confirms the proposed commit message(s).** Read `wrapper_mode` and `source_root` from `$WORKDIR/preflight.json`.

### 3.1 — Resolve the squash base

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-finalize"
# Standalone: --install-root . only.
# Wrapper mode: ALSO pass --source-root <source-root> so the source-repo base is computed.
.devforge/lib/finalize_helper resolve-squash-base \
  --install-root . \
  [--source-root <source-root>  # wrapper mode only] \
  > "$WORKDIR/squash-base.json"
```

`resolve-squash-base` computes the install/wrapper squash base (the `merge-base` on a feature branch; the oldest `[checkpoint]` commit's parent when on the default branch) and, in wrapper mode, the source-repo base (the `merge-base` scoped to `source_root`). Stdout JSON carries `install_squash_base` (or `null`), `source_squash_base` (`null` in standalone), `strategy` (`merge-base` / `checkpoint-parent` / `none`), `is_feature_branch`, and `default_branch`. The base ref auto-detects; pass `--default-branch <ref>` when auto-detection fails (the stderr message says so). On a non-zero exit (the oldest `[checkpoint]` is the repo's initial commit, or the default branch cannot be resolved), copy the helper's stderr VERBATIM and end the turn — the squash cannot proceed.

If `install_squash_base` is `null` and `strategy` is `none`, there is nothing to squash in the install repo (mirrors the PHASE-0 no-op, but for the on-default-branch path where no `[checkpoint]` commit was found). Tell the user there is nothing to squash and end the turn.

### 3.2 — Already-pushed guard

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-finalize"
.devforge/lib/finalize_helper check-pushed --repo-root . > "$WORKDIR/pushed.json"
```

`check-pushed` reports whether the current branch's commits are already on `origin/<branch>`. Stdout JSON carries `is_pushed` (`true` when `origin/<branch>..HEAD` is empty — all HEAD commits are already pushed), `commit_count`, `branch`, and `no_upstream` (`true` when there is no remote / upstream — treated as safe-to-squash). If `is_pushed` is `true`, SKIP the squash and warn the user (do NOT rewrite shared history): _the feature's commits have already been pushed to `origin/<branch>` — squash skipped to avoid rewriting shared history; consider an interactive rebase before opening the PR._ Then skip to PHASE 4 and report the skip in the results block. (The `squash` verb ALSO enforces this guard in-helper — it refuses a pushed repo even if called — but checking here lets the orchestrator skip the confirmation prompt entirely on a pushed branch.)

### 3.3 — Compose the commit message(s) + get explicit confirmation

Compose the commit subject(s) the squash will use:

- **Install/wrapper repo** — `feat(<feature-name>): <title>`, where `<feature-name>` is the feature slug (the `NNN-<slug>` directory's slug) and `<title>` is the feature's title, drawn from the spec's `## 1. Overview` section (the first 1-2 sentences, condensed to a commit-subject-length title). The `squash` verb APPENDS `COMMIT_ATTRIBUTION` per config — do NOT add attribution to the subject yourself. Before calling `squash --confirm` (3.4), assert the composed `<title>` (from the spec's `## 1. Overview`) is non-empty; if the Overview is blank, ask the user to supply a commit title before proceeding — an empty `--install-message` would produce a malformed `feat(scope):` commit (the helper does not validate non-emptiness).
- **Source repo (wrapper mode only)** — `[TICKET-ID] - Description`, where `TICKET-ID` is the Jira-style token from the source branch name (the helper reuses `_extract_ticket_id`; the token matches `[A-Z]+-[0-9]+`) and `Description` lifts from the spec's `## 1. Overview` first 1-2 sentences. This commit carries NO attribution, NO conventional-commit prefix, and NO AI traces (D5) — the helper enforces this; the message is used AS-IS.

Present the proposed message(s) to the user and ask for explicit confirmation before any history is rewritten — for example: _Proposed feature commit: `feat(001-auth): add email/password sign-in`_ (and, in wrapper mode, _Proposed source commit: `[AUTH-123] - Add email/password sign-in`_) _— confirm to squash, or edit the message(s)._ Wait for the user to confirm (or supply edited message(s)). Do NOT proceed to 3.4 without confirmation — the squash is destructive (D4 / OQ-1).

### 3.4 — Execute the squash

On confirmation, run `squash` with `--confirm` and the confirmed message(s):

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-finalize"
# Standalone: --install-root . + --install-message + --confirm.
# Wrapper mode: ALSO pass --source-root <source-root> + --source-message "[TICKET-ID] - Description".
.devforge/lib/finalize_helper squash \
  --install-root . \
  --install-message "feat(<feature-name>): <title>" \
  [--source-root <source-root> --source-message "[TICKET-ID] - Description"  # wrapper mode only] \
  --confirm \
  > "$WORKDIR/squash.json"
```

`squash` runs `git reset --soft <base> && git commit` for the install/wrapper repo (appending `COMMIT_ATTRIBUTION` per config) and, in wrapper mode, for the source repo (the `[TICKET-ID] - Description` message AS-IS, no attribution — D5). Stdout JSON carries `confirmed`, `install_repo`, `source_repo` (`null` in standalone), and a top-level `error`. Each per-repo outcome carries `head_sha`, `squash_base`, `message_used`, `attribution_applied`, `refused`, `refusal_reason`, `danger_state`, and `error`. Read the JSON and handle each outcome:

- **Success** — `head_sha` is set, `refused` / `error` / `danger_state` are falsey. Carry `head_sha` + `message_used` forward and PROCEED to PHASE 4.
- **Refused (already pushed / no base)** — `refused` is `true`; report `refusal_reason` verbatim and treat the repo as not squashed (this is the in-helper guard; the orchestrator's 3.2 check should already have caught the pushed case). Carry the refused state forward and PROCEED to PHASE 4 — the results block reports the skip in place of the commit hash (PHASE 4 + `.claude/commands/finalize/references/results-and-docs.md` require a skipped/refused squash to be reported; "never claim a squash that did not happen").
- **No-op** — when a repo had nothing to squash, the outcome's `refusal_reason` says so (e.g. "nothing to squash"); report it plainly and PROCEED to PHASE 4 (the results block reports the no-op in place of the commit hash, same as the refused case).
- **Danger state** — `danger_state` is `true` means `git reset --soft` succeeded but `git commit` FAILED, leaving the working tree staged but uncommitted. The verb exits 2 and the `error` field carries the manual-recovery instruction. Copy the helper's stderr VERBATIM as a fenced code block, surface the recovery instruction to the user, and end the turn — do NOT continue past a danger state.
- **Top-level error** — the verb exits 2 with a stderr message (e.g. an unresolvable squash base). Copy the stderr VERBATIM and end the turn.

Control flow is unambiguous: **success / refused / no-op → PROCEED to PHASE 4** (a clean commit, or a reported skip in its place); **danger state / top-level error → END the turn** (non-recoverable). A non-zero exit from `squash` is meaningful (refusal / danger / error) — read the JSON and follow the matching branch above: refusal still proceeds to PHASE 4 to report the skip, danger / error stop.

## PHASE 4 — Present results + cleanup

Present the "Feature Finalized" results block (the shape is documented in `.claude/commands/finalize/references/results-and-docs.md`), composed from the `$WORKDIR/squash.json` per-repo outcome, the PHASE-1 `file_count`, the PHASE-2 docs state, and the PHASE-0 summary present/absent state:

```
## Feature Finalized

**Commit**: [short head_sha] [message_used]
**Files**: [file_count] files changed
**Docs**: [updated <targets> | skipped — <reason> | tech-writer failed — <error>]
**Summary**: [included in squash | not found — /summarize was not run]

Feature is ready for PR.
```

In wrapper mode, add a `**Source commit**:` line from the `source_repo` outcome (the `[TICKET-ID] - Description` commit, traceless per D5). When the squash was SKIPPED (already-pushed guard, 3.2) or no-op'd, report that in place of the **Commit** line — never claim a clean commit that did not happen.

Then print a soft `/generate-docs` reminder for structural doc drift (OQ-3 — a soft pointer, NOT a gate): _Surgical docs are updated for this feature. If the feature added new packages, concerns, or domain terms, run `/generate-docs` to regenerate the structural docs this surgical pass does not cover._

`/finalize` is TERMINAL — there is NO next-pipeline-command pointer. The "ready for PR" line above IS the next step (create the PR).

Clean up the scratch directory — nothing else needs it after the results are presented:

```bash
WORKDIR="${TMPDIR:-/tmp}/forge-finalize"
rm -rf "$WORKDIR"
```

## Important rules

1. **Finalize does not verify code** — it assumes `/verify` has already approved. The PHASE-0 spec-`Complete` gate enforces this (`/verify` flips the spec to Complete on an APPROVED verdict; `/finalize` STOPS with "run `/verify` first" otherwise).
2. **Squash is the LAST operation** (D8) — the tech-writer docs are written and `[WIP]`-committed in PHASE 2, BEFORE the PHASE-3 squash, so they fold into the single clean commit.
3. **The squash MUTATES — and is confirmation-gated** (D4 / OQ-1) — `/finalize` rewrites local git history. The destructive squash runs only after the user confirms the proposed commit message(s), and only via `squash --confirm`. Without `--confirm` the verb emits a dry-run preview and mutates nothing.
4. **Never rewrite shared history** — when the feature's commits are already pushed (`check-pushed` `is_pushed` true), skip the squash and warn; the `squash` verb refuses a pushed repo in-helper as a second guard.
5. **Idempotent no-op** — when no `[WIP]`/`[checkpoint]` commits remain (PHASE-0 `has_wip_commits` false), `/finalize` no-ops gracefully ("Nothing to finalize"); re-running on an already-finalized feature lands here.
6. **Wrapper-mode dual squash, source traceless** (D5) — in wrapper mode `/finalize` squashes BOTH repos: the install/wrapper commit is `feat(scope):` + `COMMIT_ATTRIBUTION` per config; the source commit is `[TICKET-ID] - Description` with NO `Co-Authored-By`, NO conventional prefix, and NO AI traces, regardless of config. The helper enforces the source-repo no-attribution invariant.
7. **Docs retarget to LIVE locations** (D1) — the tech-writer dispatch updates `docs/<package>/<concern>/index.md` Hazards, `docs/<package>/architecture.md`, and `docs/architecture.md` only; the dropped Plan-F per-feature / per-resource / per-guide tiers are never resurrected (see `.claude/commands/finalize/references/results-and-docs.md`). Structural doc drift is left to `/generate-docs` (the PHASE-4 soft reminder).
8. **Renders no verdict, runs no finder ensemble** — `/finalize` is gate + docs + squash. It dispatches one agent (`tech-writer`); it runs no finder/refuter/verdict machinery (those belong to `/review` and `/verify`). Do not add any.
9. **Terminal** — `/finalize` is the last pipeline step. Its "next step" is "create a PR"; there is no downstream command pointer.
