---
name: implement
argument-hint: ''
description: Drain an approved feature's breakdown tasks one at a time — dispatch the assigned agent, verify, autonomous four-reviewer review panel, forcing-functions gate, then a per-task human hard gate before any commit.
disable-model-invocation: true
allowed-tools:
  - Bash(.devforge/lib/implement_helper resolve-next-task *)
  - Bash(.devforge/lib/implement_helper preflight *)
  - Bash(.devforge/lib/implement_helper capture-touched-files *)
  - Bash(.devforge/lib/implement_helper verify-touched *)
  - Bash(.devforge/lib/implement_helper merge-review-panel *)
  - Bash(.devforge/lib/implement_helper run-forcing-functions-gate *)
  - Bash(.devforge/lib/implement_helper wip-commit *)
  - Bash(.devforge/lib/implement_helper mark-complete *)
  - Bash(.devforge/lib/implement_helper mark-skipped *)
  - Bash(.devforge/lib/implement_helper update-session-state *)
  - Bash(.devforge/lib/cbm_sync_helper write *)
  - Bash(test -f *)
  - Bash(git commit --allow-empty *)
  - Bash(git -C * commit --allow-empty *)
  - Bash(git diff *)
  - Bash(git -C * diff *)
  - Bash(git reset --hard *)
  - Bash(git -C * reset --hard *)
---

# /implement — Per-Task Execution Loop

`/implement` is repeatable per feature. It drains the lowest-numbered incomplete feature's breakdown tasks one at a time, in dependency order. Each task runs through dispatch → scope-aware verify → an autonomous four-reviewer review panel → a forcing-functions gate, then **stops at a per-task hard gate** where the orchestrator (the LLM following this spec) shows the diff and asks the user to approve, repair, skip, or stop. **Nothing the agent produced is committed until `approve`.** On `approve`, one per-task WIP commit lands and the loop auto-advances to the next task. The loop exits only on user `stop` or when the feature has no incomplete tasks left.

The orchestrator runs the loop in the main thread. Subagent dispatch via the Task tool is reserved for the implementing engineer (per task) and the four read-only review-panel agents (`code-reviewer`, `qa-reviewer`, `security-reviewer`, `performance-analyst`), fanned out in parallel per review-panel round. The helper (`.devforge/lib/implement_helper`) owns task resolution, scope-aware verification, the self-repair and review-panel counters, the forcing-functions gate, the per-task commit, completion marking, and session-state — the orchestrator composes values and drives the loop.

Usage: `/implement` — no arguments. The command resolves the lowest-numbered incomplete feature and walks its tasks in dependency order; there is no `N`, range, or `all` form. Per-task human approval is logically incompatible with batch forms.

## Outputs of this phase

- A per-task WIP commit per approved task (`[WIP] task: <title> (Task NNN)` in non-wrapper mode; `[TICKET-ID] - <title> (Task NNN)` in wrapper mode). WIP commits are squashed by `/finalize`.
- Updated `tasks/<NNN>-<title>.md` (Status `Complete`, ticked Done-When boxes, filled Completion Notes) + `tasks/README.md` index row per approved task. When verification was scoped (PHASE 5 `tooling_unavailable` → `scope-and-approve`), the type-check / lint / test Done-When boxes are left unticked and annotated `_(unverified — see Completion Notes)_` instead of ticked.
- A pre-task `[checkpoint] pre-task NNN` empty commit + `.devforge/wip.md` marker per task (the crash-recovery affordance; `wip.md` is cleared on commit, skip, or rollback).
- Refreshed `.devforge/session-state.md` + an appended `.devforge/memory.md` line per approved task.

## Context in the Workflow

```
/research (optional) → /specify → /plan → /breakdown → /implement → /review → /verify → /summarize → /finalize
```

`/implement` runs AFTER `/breakdown` produces the task set, BEFORE `/review`. It consumes the structured `specs/NNN-<feature>/breakdown-handoff.json` (the producer-side handoff written by `/breakdown`) as its read contract: the orchestrator never re-derives task structure from the markdown task files — it reads the machine contract via `resolve-next-task` and the markdown task body via Read.

## What this command does NOT do

- **No feature-level docs.** `tech-writer` is NOT invoked here, and no per-task `docs/` regeneration runs. Inline documentation (docstrings / JSDoc) is the implementing agent's job, verified by `code-reviewer` during the review panel. Feature-level `docs/` generation happens at `/finalize`. Do not add `tech-writer` or per-task `docs/` regeneration to this loop.
- **No batch task targeting.** There is no `/implement N` form (see Usage).

---

## PHASE 0: Crash-recovery branch (once, at loop start)

**This branch runs once, before the first `resolve-next-task`, and is the SOLE interrupted-session detector.** Per-task preflight (PHASE 2) only asserts that `wip.md` is absent; it does not offer recovery. See `.claude/commands/implement/references/crash-recovery.md` for the full mechanics.

Read `.devforge/wip.md`.

- **Absent** → no interrupted task. Proceed directly to PHASE 1 (`resolve-next-task`).
- **Present with `**Command**: /implement`** → a `/implement` task was interrupted mid-flight. Ask the user via `AskUserQuestion`:
  - Question: `"Interrupted /implement task found — how to proceed?"` — single-line text.
  - Options: `["resume", "rollback", "skip", "manual"]`.
  - **`resume`** → re-enter the recorded task at its `**Phase**:` field (dispatch / verify / review / forcing_functions / gate). The marker carries `**Feature**`, `**Task**`, `**Title**`, `**Agent**`, `**Checkpoint**` — use them to rebuild context, then continue the loop from that phase.
  - **`rollback`** → `git -C <source_root> reset --hard <checkpoint_sha>` (the `**Checkpoint**:` field, which is the **source** repo HEAD), then clear `wip.md` (the orchestrator removes the file), then proceed to PHASE 1 to re-resolve. Resolve `<source_root>` from `.devforge/project-config.json` `PROJECT_ROOT` (`.` → standalone, source==install) — see PHASE 2 "Workspace resolution".
  - **`skip`** → `git -C <source_root> reset --hard <checkpoint_sha>` (the `**Checkpoint**:` field, the **source** repo HEAD) so the partial edits do not bleed into the next task, then mark the task skipped via the helper, then clear `wip.md`, then proceed to PHASE 1. PHASE 0 runs before `resolve-next-task`, so resolve the task file by globbing `<Feature>/tasks/<Task>-*.md` (the `**Feature**` and `**Task**` number from the marker — match on the number prefix, do not reconstruct the slug) and use `<Feature>/tasks/README.md` as the index, then call:

    ```bash
    .devforge/lib/implement_helper mark-skipped --task-file <resolved-task-file> --index <feature>/tasks/README.md --number NNN
    ```

    The helper sets `**Status**: Skipped` in the task file and rewrites the matching `tasks/README.md` index row (it does NOT touch git or `wip.md`); exit 2 means the task file or index row was not found — copy its stderr VERBATIM into a fenced code block and resolve before re-running. `resolve-next-task` treats `Skipped` as satisfied for dependency resolution, so downstream tasks are not permanently blocked.

  - **`manual`** → keep all state and `wip.md` in place; tell the user `"/implement paused for manual inspection. Re-run /implement when ready."` and end the turn.

- **Present with a `**Command**:`value other than`/implement`** → a different command was interrupted. Do NOT proceed. Tell the user `"A previous session of a different command was interrupted (see .devforge/wip.md). Resolve that session first before running /implement."` and end the turn.

---

## PHASE 1: Resolve the next task

Resolve the lowest-numbered incomplete feature's lowest dependency-ready task via the helper:

```bash
.devforge/lib/implement_helper resolve-next-task
```

The helper scans `specs/*/` for features with a `breakdown-handoff.json`, reads each task's `**Status**:` line, picks the lowest-numbered feature with ≥1 incomplete task (Status not `Complete` and not `Skipped`), and within it the lowest-numbered task whose `depends_on` are all `Complete` or `Skipped`. It emits one JSON object on stdout with a `state` field:

- **`{"state": "task", ...}`** (exit 0) → a runnable task. The object carries `feature_dir`, `number`, `title`, `agent`, `depends_on`, `touched_files`, `expects`, `produces`, `ac_addressed`, `doc_refs`, `review_checkpoint`, plus the resolved on-disk paths and progress snapshot: `task_file` (absolute path to the task's `tasks/NNN-*.md`, or `null` if the file is missing), `index_file` (absolute path to `tasks/README.md`, or `null` if missing), `completed_count` (int), and `total_count` (int) for the active feature. Capture all of these; they drive the rest of the loop. **Null-path guard:** if `task_file` is `null` OR `index_file` is `null`, STOP — do NOT proceed to PHASE 2. The task is scheduled in the breakdown handoff but its task file or index is missing on disk (a `/breakdown` setup failure). Tell the user which is missing (the `null` field) and that the breakdown must be re-run or repaired before `/implement` can advance. Otherwise proceed to PHASE 2.
- **`{"state": "all-complete"}`** (exit 0) → every feature's tasks are `Complete` or `Skipped` (or there are no features with a breakdown handoff). Tell the user `"✅ All feature tasks complete. Next: run /review → /verify → /summarize → /finalize"` and end the loop.
- **`{"state": "blocked", ...}`** (exit 2) → a feature has incomplete tasks but none are dependency-ready (an unmet dependency or a cycle). Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase); the JSON carries `feature_dir`, `reason`, and `blocking_tasks`. Tell the user the dependency graph cannot advance and end the loop.

---

## PHASE 2: Preflight + checkpoint + WIP marker

Run pre-task checks via the helper:

```bash
.devforge/lib/implement_helper preflight
```

The helper checks (in order): constitution populated (`constitution.md` lacks the `_Run /constitute to populate_` sentinel), a feature branch is checked out in the **source** repo (refuses `main`/`master`/`trunk` and the source repo's origin default branch — that is where code commits land), no stale `.devforge/wip.md` remains in the install root, and a readable git HEAD exists in the source repo. On success it emits JSON `{constitution_digest, memory_digest, head_sha, branch, source_branch, source_dirty_warning}` on stdout (exit 0). `head_sha` is the **source** repo HEAD; capture it as the task's **checkpoint SHA** — the rollback target for `skip` and recovery. (`constitution.md` and `.devforge/` are install-root artifacts; the helper reads them from the install root and runs the branch/HEAD/dirty git checks against the source repo, resolving `<source_root>` internally from the install-root `--root`.)

The `preflight` JSON also carries two source-repo fields the orchestrator must surface: `source_branch` (the source repo's current branch — equals `branch`) and `source_dirty_warning` (a string when the source repo had pre-existing uncommitted changes at task start, else `null`). When `source_dirty_warning` is non-null, relay it to the user as an advisory (the source repo was not clean when the task started, so its diff will be harder to read) and continue — it is NOT a stop (the helper kept exit 0 because precise touched-files staging means the dirty tree will not corrupt the per-task commit). When it is `null`, say nothing.

Exit 2 means a check failed — copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then end the turn. (A stale-`wip.md` exit 2 should not occur here: PHASE 0 is the recovery branch and either cleared the marker or ended the turn. If it does, the user must resolve `wip.md` before re-running.)

### Workspace resolution (two roots)

`/implement` operates across TWO roots. Resolve them once here, after `preflight`, and use them consistently for the rest of the loop:

- **Install root** — where `.devforge/`, `specs/`, `constitution.md`, and `wip.md` live (the wrapper repo). All `specs/`/`.devforge/` artifact ops stay at the install root.
- **Source root** — `<install_root>/PROJECT_ROOT`, where the code and its own git repo live. Read `PROJECT_ROOT` from `.devforge/project-config.json` and join it to the install root to compute `<source_root>`. ALL source-repo git ops (checkpoint, diff display, reset) run with `git -C <source_root>`.

When `PROJECT_ROOT` is `"."` (standalone), `<source_root>` equals the install root — a single repo, and every `git -C <source_root>` op below collapses to operating on the one repo (today's behavior). When `PROJECT_ROOT` is a non-trivial path (wrapper mode), the source git ops target the nested source repo while artifact ops stay at the install root. The helper subprocesses (`preflight`, `capture-touched-files`, `verify-touched`, `wip-commit`) resolve `<source_root>` internally from the install-root `--root`, so they are always called with the install-root path; only the orchestrator's own git ops below name `<source_root>` explicitly.

Then the orchestrator creates the pre-task checkpoint and writes the WIP marker:

1. Create the empty checkpoint commit in the **source** repo (its only purpose is a stable rollback anchor; it is squashed by `/finalize`):

   ```bash
   git -C <source_root> commit --allow-empty -m "[checkpoint] pre-task NNN"
   ```

   Substitute `NNN` with the resolved task `number` and `<source_root>` with the path resolved above. The checkpoint SHA written into `wip.md` (step 2 below) is preflight's `head_sha` — the **source** repo HEAD snapshotted before this empty commit (`preflight` already targeted the source repo per D3), the rollback target for `skip` and recovery. In standalone mode `<source_root>` is the install root, so this is a single-repo commit exactly as before.

2. Write `.devforge/wip.md` with the mandatory `**Command**: /implement` field plus `**Feature**`, `**Task**` (number), `**Title**`, `**Agent**`, `**Phase**` (set to the phase about to run, starting at `dispatch`), and `**Checkpoint**` (the checkpoint SHA captured above). The marker is the crash-recovery anchor read by PHASE 0 on the next run. See `.claude/commands/implement/references/crash-recovery.md` for the field layout.

---

## PHASE 3: Dispatch the implementing agent

Invoke the agent named in the resolved task's `agent` field via the Task tool. **Architect guard:** if that field is `architect`, HALT — the architect is a director and cannot write implementation code (per `.claude/agents/architect.md` Rule 1; its charter is to refuse-and-route coding work back to the owning stack's implementer). Re-run `/breakdown` (now fixed to never assign `architect` as a coder) to get the owning stack's implementer, or add the missing agent. Do not dispatch the architect to implement. **Missing-agent fallback:** if the assigned agent is absent from `.claude/agents/` (not all projects generate all agents), HALT and escalate to the human — split the task or re-run `/breakdown` to assign the owning stack's implementer. Never fall back to `architect`; it cannot write code.

The brief MUST give the agent complete context — it sees only what you brief it with (per `feedback_no_underspecification_when_delegating`). Assemble the brief per `.claude/commands/implement/references/agent-brief.md`: the task body (read the resolved `task_file` path from PHASE 1), the spec acceptance-criteria slice (`ac_addressed`), the constitution rules, the `.devforge/memory.md` pitfalls, the `touched_files` scope constraint, and an explicit "make ONLY the changes this task describes — do not modify unrelated code" rule. The agent writes its edits into the working tree; nothing is committed yet.

The agent edits **source** files. The handoff's `touched_files` are source-root-relative, so give the agent source-rooted paths (`<source_root>/<touched_file>`) and tell it to operate under the source root. State explicitly that the agent must NOT write forge artifacts (`.claude/`, `specs/`, `CLAUDE.md`, `constitution.md`, `.mcp.json`, `docs/overview.md`, `docs/architecture.md`, `bugs/`, `research/`) into the source tree — those live at the install root. In wrapper mode PHASE 5's wrapper-isolation check fails the task if any such artifact appears inside the source root. In standalone mode `<source_root>` is the install root, so source-rooted paths are just the repo-relative paths as today and the isolation rule is moot (the single repo legitimately contains those artifacts).

---

## PHASE 4: Capture touched files

Capture the files the agent changed since the checkpoint via the helper:

```bash
.devforge/lib/implement_helper capture-touched-files --checkpoint <checkpoint-sha>
```

Pass the checkpoint SHA from PHASE 2. The helper runs `git diff --name-only <checkpoint-sha>` (tracked changes) + the untracked-file column of `git status --porcelain` (new files the agent created) against the **source** repo (it resolves `<source_root>` internally from the install-root `--root`) and emits a JSON array of **source-root-relative** paths on stdout (exit 0). Capture this array as `<touched-files-json>`; PHASE 5, PHASE 6, and PHASE 7 all pass it on. In standalone mode the source repo is the install root, so the paths are repo-root-relative as today.

Exit 1 (git/subprocess failure) or exit 2 (invalid checkpoint SHA) — copy the helper's stderr VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then end the turn.

---

## PHASE 5: Scope-aware verify + autonomous self-repair

Run scope-aware verification over the touched files. Start the iteration counter at 0:

```bash
.devforge/lib/implement_helper verify-touched --files '<touched-files-json>' --iteration 0
```

The helper loads `PACKAGE_STACKS` from `.devforge/project-config.json` (install root), longest-path-prefix matches each source-relative touched file to its package's `type_check_command` + `lint_command` + `test_command` (files outside any package fall back to the primary-stack `TYPE_CHECK_COMMANDS[0]` / `LINT_COMMANDS[0]` / `TEST_COMMANDS[0]`), de-duplicates commands, and skips `"N/A"` and absent commands silently. It runs them in a fixed order: static checks (type-check + lint) first, then the build once, then tests last — so a failing build surfaces before any test runs, and a project with no test command configured runs no tests (backward-compatible). It runs every command with **cwd = `<source_root>`** (the stored commands are bare, e.g. `npm run check`, so the source cwd is what makes their relative paths resolve) — it resolves `<source_root>` internally from the install-root `--root`, so the orchestrator still passes the install-root path. In wrapper mode it also runs a wrapper-isolation check (see the `isolation_failure` status below). It emits JSON on stdout with a `status` field. **The helper owns the self-repair cap (3); the orchestrator cannot extend it.**

- **`{"status": "pass", ...}`** (exit 0) → verification passed. Proceed to PHASE 6.
- **`{"status": "self_repair", ...}`** (exit 0) → a command failed and the cap is not yet reached. The object carries `iteration` (`N`), `failed_command`, and `output`. Relaunch the **implementing agent** (the same `agent` from PHASE 3) with the `failed_command` and `output` so it can fix the failure, then re-call `verify-touched` with `--iteration` set to `N + 1`. Repeat this autonomous self-repair leg — no human between iterations.
- **`{"status": "failed", ...}`** (exit 2) → the self-repair cap was reached; the task is **gate-blocked**. Copy the helper's stdout VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase), then surface the blocked hard gate (PHASE 7 Stage B blocked path: `repair` / `skip` / `stop` only — never `approve`).
- **`{"status": "isolation_failure", "artifacts": [...]}`** (exit 2, wrapper mode only) → the agent polluted the **source** tree with forge artifacts (the `artifacts` array lists the offending paths, relative to `<source_root>`, e.g. `.claude`, `specs`, `CLAUDE.md`). This is NOT a self-repair loop and NOT the verify cap — handle it DISTINCTLY: copy the helper's stdout VERBATIM into a fenced code block, then surface the blocked hard gate (PHASE 7 Stage B blocked path: `repair` / `skip` / `stop` only — never `approve`). On `repair`, instruct the implementing agent to REMOVE the misplaced artifacts from the source tree (they belong at the install root, not inside `<source_root>`) before re-running PHASE 4 → PHASE 5. (Standalone never emits this status — the single repo legitimately contains `.claude/`, `specs/`, etc., so the helper skips the check.)
- **`{"status": "tooling_unavailable", "failed_command": "...", "output": "..."}`** (exit 2) → a configured type-check, lint, or test command could NOT be executed (a missing binary or a misconfigured command — e.g. `vue-tsc` not on PATH, or the test runner not installed; the helper detects any of three signals: shell exit 127, "command not found", or "not recognized as an internal or external command" (Windows cmd)). This is a tooling/config problem, NOT a code error, and it is NOT self-repairable — re-running the agent cannot install a tool. The helper short-circuits on it: no self-repair leg runs and the remaining verify commands are not run. Copy the helper's stdout VERBATIM into a fenced code block, then surface the **Tooling-unavailable path** (PHASE 7 — distinct from the Stage B blocked path; it CAN reach `approve` via `scope-and-approve`).

Exit 1 (missing/malformed `project-config.json`) — copy the helper's stderr VERBATIM into a fenced code block, then end the turn.

---

## PHASE 6: Autonomous review PANEL loop

After verify passes, run the bounded autonomous review-panel loop — a panel of FOUR read-only reviewers (`code-reviewer`, `qa-reviewer`, `security-reviewer`, `performance-analyst`) ⇄ implementing agent, ≤3 rounds (helper-owned counter), NO human between rounds. The loop converges to a panel-clean verdict (every reviewer clean) AND records each judgment-level call it made on the user's behalf as a structured decision item for PHASE 7 Stage A. See `.claude/commands/implement/references/review-loop.md` for the per-reviewer verdict mapping, the all-clean rule, the orchestrator-side findings synthesis + conflict identification, the mechanical-vs-judgment classification, the bias-toward-recording tie-breaker, and the three decision-item shapes.

All four reviewers are read-only and tools-locked (per the standardized roster — `Read, Grep, Glob, Bash`; no `Edit`/`Write`/`Agent`), so they cannot modify the tree: a parallel fan-out is safe, and the **only writer in PHASE 6 is the implementing agent during a repair leg** — the reviewers never collide ("stepping on each other" is impossible). A "conflict" in this loop therefore means two reviewers proposing INCOMPATIBLE changes to the same code region — a findings-level contradiction, never a write race.

Start the loop iteration counter at 0 and run:

1. **Fan out the four reviewers in parallel.** In ONE turn, dispatch `code-reviewer` (consumer `.claude/agents/code-reviewer.md`), `qa-reviewer`, `security-reviewer`, and `performance-analyst` via the Task tool — four Task calls in the same turn. Give EACH the same inputs: the `touched_files`, the constitution, and the task body. Each reviewer is independent and sees ONLY its own brief. The four results return UNORDERED, so key each returned markdown to the agent you dispatched it to (do not assume return order). Each reviewer returns a markdown verdict carrying a `### Verdict:` line in its own vocabulary (`code-reviewer`: `APPROVE` / `REQUEST CHANGES` / `BLOCK`; `qa-reviewer`: `ADEQUATE` / `GAPS FOUND`; `security-reviewer`: `PASS` / `FAIL`; `performance-analyst`: `MEETS TARGETS` / `BOTTLENECKS FOUND`).
2. **Write each reviewer's returned markdown to a run-scoped scratch file** (a tmp dir OUTSIDE the repo so the scratch never pollutes the source tree, mirroring how `/audit` uses a `${TMPDIR:-/tmp}/forge-audit` working dir): write each with the Write tool to `${TMPDIR:-/tmp}/forge-implement-review/<agent>.md` (one file per reviewer, named for the agent). A bash subprocess cannot read a subagent's return value, so these files are the bridge to the merge helper.
3. **Merge the four verdicts** via the helper, passing the current iteration `N` and one `--reviewer <agent>:<path>` per reviewer (the path written in step 2):

   ```bash
   .devforge/lib/implement_helper merge-review-panel --iteration N --reviewer code-reviewer:<path> --reviewer qa-reviewer:<path> --reviewer security-reviewer:<path> --reviewer performance-analyst:<path>
   ```

   The helper parses each reviewer's `### Verdict:` line against that reviewer's vocabulary and emits JSON `{clean, escalate, iteration, per_reviewer}` (exit 0), where `per_reviewer` is one `{agent, verdict, clean}` record per reviewer. `clean` is `true` IFF EVERY reviewer returned its own clean token (`code-reviewer` `APPROVE`, `qa-reviewer` `ADEQUATE`, `security-reviewer` `PASS`, `performance-analyst` `MEETS TARGETS`); one dirty reviewer keeps the loop going. `escalate` is `true` when `N >= 3` (the helper-owned `REVIEW_LOOP_CAP`). The helper does the deterministic verdict aggregation ONLY — it does NOT parse, merge, or conflict-detect findings; that is the orchestrator's job below. Exit 2 means one reviewer's verdict line was missing, was the unfilled slash-joined template, or carried a token outside that reviewer's vocabulary — copy the helper's stderr VERBATIM into a fenced code block (it names WHICH reviewer failed), then re-invoke ONLY that named reviewer for a properly-formed verdict, rewrite its scratch file, and re-run `merge-review-panel`. Do not treat a parse error as a verdict.

4. Branch on the JSON:
   - **`clean: true`** → exit the panel loop. Carry any reviewer warnings into PHASE 7 Stage B. Proceed to the forcing-functions gate below.
   - **`clean: false` and `escalate: false`** → the autonomous repair leg (no human). You hold the four reviewers' returned markdown; do all of the following, then re-fan-out:
     - **Synthesize ALL findings** across the four reviewers into ONE implementing-agent repair brief (per `.claude/commands/implement/references/agent-brief.md`'s PHASE 6 re-dispatch shape). One repair pass addresses all non-conflicting findings.
     - **Classify each cleared finding** mechanical-vs-judgment (per `.claude/commands/implement/references/review-loop.md`): a **judgment** call (changed the shape of the solution) is recorded as a decision item `{finding, agent_resolution, alternative}` for Stage A; a **mechanical** fix resolves silently. When unsure, record it.
     - **Identify conflicts** — two reviewers proposing INCOMPATIBLE changes to the same region. A CROSS-severity contradiction is NOT a conflict: the higher severity wins, and you apply it and proceed autonomously (the panel shares the unified `Critical / High / Medium / Info` severity scale, so severity is directly comparable). A COMPARABLE-severity genuine conflict is one you must NOT decide on the user's behalf → record it as a `conflict` decision item (it surfaces at Stage A) and do NOT autonomously repair that contested region this round.
     - Relaunch the **implementing agent** ONCE with the synthesized findings, then **re-fan-out the FULL panel** (all four reviewers over `touched_files` — no delta-scoping) at iteration `N + 1`. Full-panel re-review each round closes the cross-file-regression hole a repair could open.
   - **`clean: false` and `escalate: true`** → the cap was reached without converging. Exit the loop and record a `could-not-converge` decision item carrying the unresolved reviewer objection(s) for Stage A.

After the review panel exits clean, first run the design-manifest tripwire, then run the forcing-functions gate.

**Design-manifest tripwire (loud WARN, non-blocking).** Before the gate, check whether this feature has a design reference but is missing its disposition manifest:

```bash
test -f design/reference.html && ! test -f <feature_dir>/design-manifest.json && echo VOID
```

Substitute `<feature_dir>` with the resolved feature's `feature_dir` from PHASE 1 (`design/reference.html` is at the install root, where you run; `feature_dir` is the absolute `specs/NNN-*/` path). When the command prints `VOID` — a `design/reference.html` is present but this feature's `specs/<feature>/design-manifest.json` is absent — emit a loud, operator-visible WARN in your next user-facing message: this feature has a design reference but no design-manifest, so the forcing-functions gate's static design-token provenance check (`verify-design-tokens` Check 5 — MATCH-element token binding) is voided. Check 5 globs `specs/*/design-manifest.json` project-wide, so with this feature's manifest absent it either no-ops (no manifest on disk) or — if another feature's `design-manifest.json` is present — runs against the WRONG feature's MATCH refs, silently checking the wrong element set. The remedy is to re-run `/breakdown` PHASE 2.5 to produce this feature's manifest. Then CONTINUE to the gate — this is a WARN, not a halt; the task still proceeds. When the command prints nothing (no `design/reference.html`, or the manifest is present), say nothing and proceed silently — a genuine non-UI feature must not trip this WARN.

Then run the forcing-functions gate via the helper:

```bash
.devforge/lib/implement_helper run-forcing-functions-gate
```

The helper reads the `forcing_functions` block from `.devforge/constitute.json` and invokes `constitute_helper verify-<rule>` for each enabled rule (`verify-magic-enum`, `verify-cross-layer-imports`, `verify-any-leak`, and `verify-design-tokens` — the static design-token PROVENANCE check that backs the constitution's Design Fidelity principle in its Code Quality Standards material). The design-token check runs at WRITE TIME alongside the other detectors: when `forcing_functions.design_token_provenance.enabled` is `true` the helper dispatches `verify-design-tokens` automatically; when the rule is absent or disabled it is skipped (no-op), exactly like any other forcing-functions rule that does not apply. A design-token violation gate-blocks the task with the same blocking semantics as the other detectors. The orchestrator never enumerates individual verbs — this single `run-forcing-functions-gate` call owns the dispatch. It emits JSON `{gate, rules_run, rules_failed, reports, aggregate_exit}` on stdout. See `.claude/commands/implement/references/forcing-functions-gate.md`.

- **exit 0** → no enabled rule failed (or no rules are enabled). Proceed to PHASE 7.
- **exit 2** → one or more rules failed; the task is **gate-blocked**. Copy the helper's stdout JSON VERBATIM into your next user-facing message as a fenced code block (do not summarize or paraphrase) — the stdout report carries the per-rule findings, NOT stderr. Then surface the blocked hard gate (PHASE 7 Stage B blocked path: `repair` / `skip` / `stop` only — never `approve`).
- **exit 1** → config I/O or parse error (malformed `.devforge/constitute.json`, or an enabled rule with no known verb). Copy the helper's stderr VERBATIM into a fenced code block, then end the turn.

---

## PHASE 7: Hard gate (two stages)

This is the per-task human gate. **No content has been committed at this point** — the agent's work and all self-repair / review-panel edits sit in the working tree. The gate has two stages: Stage A surfaces recorded decisions one at a time (skipped entirely when none were recorded), then Stage B always presents the diff for the final code read.

**IMPORTANT — all findings fixed before `approve`.** Stage B (the `approve` gate) is reachable ONLY when the PHASE 6 panel verdict is fully clean (every reviewer returned its clean token) AND no unresolved finding or conflict remains. A RESOLVED judgment item (the finding is fixed; the human confirms the SHAPE at Stage A) is NOT an open finding and may reach Stage B; only genuinely unresolved findings or conflicts are blocked from `approve` — they route through a Stage A repair leg (which re-reviews to clean) or the gate-blocked path. There is no path that lets `approve` happen with an open finding.

### Stage A — Decision questions (run ONLY if PHASE 6 recorded ≥1 decision item, or escalated)

Iterate the recorded decision items. For EACH item, ask ONE `AskUserQuestion` — **sequentially, never batched** (per `feedback_askuserquestion_single_line_only`, the question is a single line; the explanation lives in the option `description` fields):

- Single-line question, e.g. `"Reviewer flagged <finding> — keep which resolution?"`.
- Options (each carrying a full `description` with the explanation): `["<agent's resolution> (recommended)", "<named alternative>", "let me specify", "stop"]`. Option 1 is ALWAYS the agent's resolution, marked `(recommended)`, so agreeing is one click.
  - **option 1 (the recommended resolution)** → keep that resolution; move to the next decision item.
  - **`<named alternative>` or `let me specify`** → treat as a repair. For `let me specify`, ask the user via free-text follow-up for the direction. Relaunch the implementing agent with the chosen direction, re-run PHASE 4 (capture-touched-files, from the same checkpoint SHA) → PHASE 5 (verify) → PHASE 6 (review panel), rebuild the decision set from the new loop, and restart Stage A.
  - **`stop`** → keep `.devforge/wip.md` + the working tree; tell the user the loop stopped at task `NNN`; end the loop.

For a `could-not-converge` item (recorded when PHASE 6 escalated at the cap with one or more reviewers still dirty), the question's options are `["send back with direction", "skip", "stop"]` — there is NO accept-the-finding-as-is option, because an open finding must never reach `approve` (the D4 guarantee above):

- **`send back with direction`** → free-text follow-up, then repair as above (relaunch the implementing agent → re-run PHASE 4 (capture) → PHASE 5 (verify) → PHASE 6 (review panel) → rebuild the decision set → restart Stage A). The loop continues under human direction; it does not ship the open finding.
- **`skip`** → take the Stage B `skip` path below.
- **`stop`** → keep `wip.md` + working tree; end the loop.

For a `conflict` item (recorded when PHASE 6 found a COMPARABLE-severity contradiction it must not decide on the user's behalf), the question names the contested finding on one line and offers the two reviewers' incompatible positions as the first two options, each explained in its `description`: `["<reviewer A's position>", "<reviewer B's position>", "let me specify", "stop"]`:

- **`<reviewer A's position>` / `<reviewer B's position>` / `let me specify`** → treat the chosen resolution as a repair direction. For `let me specify`, ask the user via free-text follow-up. Relaunch the implementing agent with the chosen resolution → re-run PHASE 4 (capture) → PHASE 5 (verify) → PHASE 6 (review panel) → rebuild the decision set → restart Stage A. The conflict is thus RESOLVED and re-reviewed to clean before Stage B — never approved open.
- **`stop`** → keep `wip.md` + working tree; end the loop.

Most tasks record zero decision items → Stage A is skipped entirely and the gate is just Stage B.

### Stage B — Final code read (ALWAYS)

Present the ready diff and the verification results. Show `git diff --stat` and the `git diff` (for a large diff, bound it: show `--stat` in full plus the diff for the highest-impact files, and tell the user the full diff is available on request). Summarize the PHASE 5 verify result, the PHASE 6 panel verdict — the four reviewers' clean verdicts (plus any carried warnings) — and the forcing-functions gate result.

Then ask via `AskUserQuestion`:

- Question: `"Approve task NNN — <title>?"` — single-line text (substitute the resolved `number` and `title`).
- Options: `["approve", "repair", "skip", "stop"]`.

End the turn. The user's reply opens the next turn.

- **`approve`** → run these steps IN ORDER, then loop:
  1. Mark the task complete FIRST (so the commit captures the completed task file + index). Before calling `mark-complete`, determine which Done-When conditions were NOT mechanically confirmed this run: when verification was scoped (the PHASE 5 `tooling_unavailable` → `scope-and-approve` path was taken), the type-check, lint, AND test Done-When conditions are unconfirmed; when `verify-touched` returned a clean `pass`, all conditions are confirmed. Pass each unconfirmed condition as a repeatable `--unverified-box "<distinguishing substring>"` — a substring that uniquely identifies that Done-When checkbox's line (read the condition text from the task file resolved in PHASE 1). To identify the verification boxes when the verification-scoped flag is set: scan the task file's `## Done When` section (the text between `## Done When` and the next `## ` heading); any checkbox line mentioning type-check / type errors / tsc / lint / linting / test / tests / spec / unit test / pytest / jest / vitest (case-insensitive) is a verification condition — pass that line's text WITHOUT the `- [ ] ` / `- [x] ` prefix as a `--unverified-box` substring (the helper match is plain case-sensitive substring containment, so the substring must reproduce the box text exactly; you are only widening which Done-When lines get detected as verification conditions, not how `mark-complete` matches). The verify gate short-circuits at the first unavailable tool and the remaining commands do not run, so under `scope-and-approve` the type-check, lint, AND test Done-When conditions are all conservatively left unverified (the gate did not complete) — erring toward not-claiming verification is the honest direction. If no such line exists, pass no `--unverified-box` argument. On a clean `pass`, pass NO `--unverified-box` arguments:

     ```bash
     .devforge/lib/implement_helper mark-complete --task-file <task_file> --index <index_file> --number NNN --files '<touched-files-json>' --expects-met <X/Y> --produces-met <X/Y> --notes "<deviations or (none)>" [--unverified-box "<substring>" ...]
     ```

     Pass the `task_file` and `index_file` paths emitted by PHASE 1's `resolve-next-task` — do not construct them.

     The helper sets `**Status**: Complete`, ticks the Done-When boxes, fills Completion Notes in `tasks/<NNN>-<title>.md`, and rewrites the Status cell of the matching `tasks/README.md` index row (exit 0 → `{"marked": true}`). Any Done-When checkbox whose line contains a passed `--unverified-box` substring is left UNticked and annotated `_(unverified — see Completion Notes)_` instead of ticked; with no `--unverified-box` argument every box ticks. Exit 2 means the task file or index row was not found, exit 1 an I/O error — copy the helper's stderr VERBATIM into a fenced code block and resolve before re-running.

  2. Commit the approved work:

     ```bash
     .devforge/lib/implement_helper wip-commit --files '<touched-files-json>' --task-file <task_file> --index <index_file> --number NNN --title "<task-title>"
     ```

     Pass the same `task_file` and `index_file` paths emitted by PHASE 1.

     The helper never uses `git add -A`. In **standalone** mode it stages the touched files + the task file + index together in the single repo and commits them. In **wrapper** mode (D1) it commits ONLY the source `touched_files` to the **source** repo on its branch (deriving the `[TICKET-ID]` from the source branch per D2) and leaves the wrapper artifacts — the `mark-complete` task `Status` edit + index row from step 1 — written to disk but **uncommitted** in the wrapper repo; expect the wrapper tree to stay dirty (it is already dirty from `/specify`//`plan`//`breakdown`, and `/finalize` later squashes the accumulated source WIP commits). Either way the helper composes the message per the wrapper/non-wrapper convention (reading `WORKSPACE_MODE` + `COMMIT_ATTRIBUTION` from `.devforge/project-config.json`), commits, captures the new source HEAD SHA, and clears `.devforge/wip.md` in the install root (exit 0 → `{"committed": true, ...}`, carrying `head_sha` and `message`). It resolves `<source_root>` internally from the install-root `--root`. Exit 1 (config/I/O) or exit 2 (git staging/commit failure) — copy the helper's stderr VERBATIM into a fenced code block and resolve before re-running.

  3. **CBM post-commit refresh (orchestrator MCP call — NOT a helper subprocess).** Because the loop drains dependency-ordered tasks, a later task's `Expects` reads the just-committed `Produces`; the codebase-memory-mcp graph would otherwise be stale. Call `mcp__codebase-memory-mcp__detect_changes` (incremental — re-indexes only the committed delta, including new inline docs), then advance the stamp:

     ```bash
     .devforge/lib/cbm_sync_helper write
     ```

     `detect_changes` targets the **source** code (the indexed project), since that is what the just-committed change touched. Subprocess helpers cannot reach MCP, so the `detect_changes` call is the orchestrator's responsibility; `cbm_sync_helper write` then advances the stamp, which stays in the install root at `.devforge/cbm-last-indexed-sha`. (Standalone: source code and install root are the one repo, so this is a single index refresh as today.)

  4. Update session-state + memory:

     ```bash
     .devforge/lib/implement_helper update-session-state --feature <feature-dir-name> --completed-count <completed_count + 1> --total-count <total_count> --last-task-number NNN --last-task-title "<task-title>" --recent-tasks '<json>' --recent-decisions '<json>'
     ```

     Pass `--total-count` as the `total_count` PHASE 1 emitted (completion does not change the task total). The `completed_count` PHASE 1 emitted is the **pre-completion** snapshot, so pass `--completed-count` as that value **plus 1** to account for the task just marked complete in step 1 — this is correct and cheaper than re-running `resolve-next-task` to re-scan disk. The helper overwrites `.devforge/session-state.md` (≤40 lines, sliding window of the last 3 task mods + last 3 decisions) and appends one outcome line to `.devforge/memory.md` (exit 0 → `{"updated": true}`).

  5. Loop: return to PHASE 1 (`resolve-next-task`) to pick the next task. The loop auto-advances — there is no per-task continue prompt; `stop` at this gate is the only loop exit besides `all-complete`.

- **`repair`** → ask the user via free-text follow-up for the repair direction, relaunch the implementing agent with those notes, then re-run PHASE 4 (capture-touched-files) → PHASE 5 (verify) → PHASE 6 (review panel + forcing-functions gate) → return to this hard gate.
- **`skip`** → discard the task's edits and advance:
  1. `git -C <source_root> reset --hard <checkpoint_sha>` (the PHASE 2 checkpoint SHA, which is the **source** repo HEAD) — this resets the **source** working tree to the task-start state so the skipped edits do not bleed into the next task's diff. (Standalone: `<source_root>` is the install root, so this resets the single repo as today.)
  2. Mark the task skipped via the helper:

     ```bash
     .devforge/lib/implement_helper mark-skipped --task-file <task_file> --index <index_file> --number NNN
     ```

     Pass the `task_file` and `index_file` paths emitted by PHASE 1. The helper sets `**Status**: Skipped` in the task file and rewrites the Status cell of the matching `tasks/README.md` index row via the same region-aware updater `mark-complete` uses (exit 0 → `{"marked_skipped": true}`); it does NOT touch git or Completion Notes. Exit 2 means the task file or index row was not found — copy the helper's stderr VERBATIM into a fenced code block and resolve before re-running.

  3. Clear `.devforge/wip.md` (the orchestrator removes the file).
  4. If this task's `produces` feed a downstream task's `expects`, warn the user before the skip lands that downstream tasks may be affected.
  5. Loop: return to PHASE 1. (`resolve-next-task` treats `Skipped` as satisfied for dependency resolution, so downstream tasks are not permanently blocked.)

- **`stop`** → keep `.devforge/wip.md` + the working tree as-is; tell the user the loop stopped at task `NNN` with work uncommitted; end the loop.

### Gate-blocked path (verify cap reached, wrapper-isolation failure, or forcing-functions exit 2)

When PHASE 5 reaches the self-repair cap, PHASE 5 returns `isolation_failure` (wrapper mode), or PHASE 6's forcing-functions gate exits 2, the task never reaches the `approve` prompt. Present the relayed findings (copied VERBATIM as above), then ask via `AskUserQuestion`:

- Question: `"Task NNN is gate-blocked — how to proceed?"` — single-line text.
- Options: `["repair", "skip", "stop"]` (no `approve` — the change is not green).
  - **`repair`** → free-text direction → relaunch the implementing agent → re-run PHASE 4 (capture-touched-files) → PHASE 5 → PHASE 6 → return here.
  - **`skip`** → the Stage B `skip` path above.
  - **`stop`** → keep `wip.md` + working tree; end the loop.

Because no content commit has happened, there is nothing to roll back — the working tree holds the partial work; the user repairs, skips, or stops.

### Tooling-unavailable path (PHASE 5 `tooling_unavailable`)

When PHASE 5 returns `tooling_unavailable`, a configured type-check, lint, or test command could not be executed, so the mechanical verify gate cannot complete. This is DISTINCT from the Gate-blocked path above: the change is not failing on a code error, it is unverifiable by the missing tool (the configured type-check, lint, or test command could not run) — so this path CAN reach `approve` (via `scope-and-approve`), whereas the Gate-blocked path never can. After relaying the helper's stdout VERBATIM (per PHASE 5), ask via `AskUserQuestion`:

- Question: `"Task NNN's type-check, lint, or test command can't run — how to proceed?"` — single-line text (substitute the resolved `number`).
- Options: `["fix-tooling", "scope-and-approve", "skip", "stop"]`. `fix-tooling` is the recommended option — fixing the tooling is the root cause and restores full mechanical verification.
  - **`fix-tooling`** (recommended) → tell the user to correct the configured command or install the missing tool, then re-run `/implement`. The command config is owned by `/configure` — point the user there to fix the type-check, lint, or test command. Leave `.devforge/wip.md` (and the PHASE 2 `[checkpoint]` commit) in place — do NOT clear them here. On the next `/implement` run PHASE 0 detects the marker and offers the crash-recovery prompt: `resume` re-enters the recorded task at its `**Phase**:` field — the verify leg (PHASE 5) re-runs from the top once the tooling is fixed; `rollback` discards the agent's work via the checkpoint SHA. End the turn.
  - **`scope-and-approve`** → the mechanical verify gate is acknowledged unavailable (the configured type-check, lint, or test command could not run) for this task. Proceed to **PHASE 6** — the review panel AND the forcing-functions gate still run, since they are independent of the type checker — then the normal **Stage B** hard gate. Carry a **verification-scoped** flag noting the type-check, lint, and test Done-When conditions are unconfirmed; Stage B's `mark-complete` (step 1) leaves those boxes unticked per the verification-scoped rule.
  - **`skip`** → the Stage B `skip` path above.
  - **`stop`** → keep `.devforge/wip.md` + the working tree; end the loop.

---

## IMPORTANT RULES

1. **Nothing commits before `approve`.** Agent work + self-repair + review-panel-repair edits sit in the working tree until the Stage B gate approves them. The only commits before `approve` are the empty `[checkpoint]` commit (PHASE 2) and — on `approve` — the single `wip-commit`.
2. **The helper owns every counter.** The self-repair cap (3, PHASE 5) and the review-panel cap (3, PHASE 6) are helper-owned; the orchestrator cannot extend them. At each cap the task is gate-blocked or escalates.
3. **One task at a time, dependency order.** `resolve-next-task` picks exactly one task; the loop drains the feature task-by-task. There is no batch mode.
4. **Decisions are pushed, never summarized.** Judgment calls and conflicts the review panel surfaced appear as sequential Stage A questions with the agent's resolution pre-selected (or the contested positions named) — never a text wall to scroll. Most tasks record zero decisions.
5. **Relay machine reports VERBATIM.** Where a helper emits a user-facing finding report on stdout (blocked verify, forcing-functions exit 2, blocked resolve), copy its stdout VERBATIM into a fenced code block. For helper failures, copy the stderr VERBATIM into a fenced code block. Do not summarize or paraphrase.
6. **Inline docs are the agent's job; feature docs wait for `/finalize`.** Do not invoke `tech-writer` or regenerate `docs/` in this loop (see "What this command does NOT do").
