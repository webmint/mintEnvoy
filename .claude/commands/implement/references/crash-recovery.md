# Crash recovery (`/implement` PHASE 0)

This reference defines the interrupted-session recovery handled by PHASE 0 of `main.md`. A `/implement` run can be interrupted mid-task by a power loss, terminal crash, or network drop. Two artefacts make a mid-task interruption recoverable: the per-task empty checkpoint commit (`[checkpoint] pre-task NNN`, PHASE 2 — created in the **source** repo) and the `.devforge/wip.md` marker (in the install root). The `**Checkpoint**` SHA the marker records is the source repo HEAD captured at task start, so recovery resets the source repo, not the wrapper.

## The WIP marker

`.devforge/wip.md` is written by PHASE 2 before each task starts and cleared after the approved per-task commit (or on skip / rollback). It is markdown — human-readable and machine-parseable. The fields (written by the `_implement/_wip.py` helper module):

```markdown
# WIP Marker — /implement

**Command**: /implement
**Feature**: <feature_dir>
**Task**: <task_number>
**Title**: <task_title>
**Agent**: <agent_name>
**Phase**: <phase>
**Checkpoint**: <checkpoint_sha or "(none)">
```

- **`Command`** is MANDATORY and is always `/implement` when this command writes the marker. It is the discriminator that lets the recovery branch detect a marker left by a different command.
- **`Phase`** records the phase that was about to run (`dispatch` / `verify` / `review` / `forcing_functions` / `gate`), so `resume` can re-enter at the right point.
- **`Checkpoint`** is the **source** repo HEAD snapshotted at task start (`preflight`'s `head_sha`) — the rollback target for `rollback` and for the `skip` reset. In wrapper mode the source repo is the nested repo at `<install_root>/PROJECT_ROOT`; in standalone mode (`PROJECT_ROOT == "."`) it is the single repo. `wip.md` itself lives in the install root and records this source SHA alongside the source branch.

## Sole-detector rule

**PHASE 0 is the SOLE interrupted-session detector.** It runs once, at loop start, before the first `resolve-next-task`. Per-task preflight (PHASE 2) does NOT offer recovery — it only ASSERTS that no stale `wip.md` remains at per-task entry, and exits 2 pointing back to the recovery branch if one is unexpectedly present. This keeps recovery logic in one place; a `wip.md` reaching preflight means PHASE 0 either cleared it or ended the turn, so its presence there is an invariant violation, not a recovery opportunity.

## The four recovery options

When PHASE 0 reads a `wip.md` whose `**Command**:` is `/implement`, it asks via `AskUserQuestion` (single-line question, options `["resume", "rollback", "skip", "manual"]`):

- **`resume`** → re-enter the recorded task at its `**Phase**:` field. Rebuild context from the marker fields (`Feature`, `Task`, `Title`, `Agent`, `Checkpoint`) and continue the loop from that phase. Use when the interruption was transient and the working-tree edits are intact.
- **`rollback`** → `git -C <source_root> reset --hard <Checkpoint>` (in the **source** repo, discarding the empty checkpoint and any task edits), clear `wip.md`, then re-resolve from PHASE 1. Resolve `<source_root>` as `<install_root>/PROJECT_ROOT` from `.devforge/project-config.json` (`.` → standalone, source==install). Use to retry the task cleanly from its start state.
- **`skip`** → `git -C <source_root> reset --hard <Checkpoint>` in the **source** repo (so the partial edits do not bleed forward), mark the task skipped via `implement_helper mark-skipped --task-file <resolved-task-file> --index <feature>/tasks/README.md --number NNN` (the helper sets `**Status**: Skipped` in the task file and rewrites the matching `tasks/README.md` index row — it does NOT touch git or `wip.md`), then clear `wip.md`, advance to PHASE 1. PHASE 0 runs before `resolve-next-task`, so resolve the task file by globbing `<Feature>/tasks/<Task>-*.md` from the marker's `Feature` + `Task` number (match the number prefix; do not reconstruct the slug). `resolve-next-task` treats `Skipped` as satisfied for dependency resolution, so downstream tasks are not permanently blocked.
- **`manual`** → keep all state and `wip.md` in place; end the turn for hand inspection. Use when the working tree needs a human look before deciding.

## Command-mismatch detection

When PHASE 0 reads a `wip.md` whose `**Command**:` is anything OTHER than `/implement` (a marker left by a different command), it does NOT proceed. It tells the user a previous session of a different command was interrupted and to resolve that session first, then ends the turn. Running `/implement` against another command's marker would corrupt that command's recovery state — the mismatch guard prevents it.
