# /finalize — tech-writer doc targets + results-block format

This file is **orientation only** for the `/finalize` orchestrator. It documents two things `main.md` composes inline (there is no helper verb for either): (1) the LIVE `docs/` locations the PHASE-2 tech-writer brief retargets to, and (2) the PHASE-4 "Feature Finalized" results block. Do not treat the blocks below as verbatim fill-in templates — they describe the shape the orchestrator produces.

## Doc targets — the LIVE locations, NEVER `docs/features/`

`/finalize` dispatches `tech-writer` in its Normal/surgical mode (D1). Under the Plan-F docs layout the per-feature `docs/features/<name>.md` tier is dropped — `tech-writer.md`'s own "**When to update which doc** (Plan F layout — the legacy `docs/features/`, `docs/api/`, `docs/guides/` tiers are dropped)" section names the live destinations, and the brief retargets the agent to exactly those:

- `docs/<package>/<concern>/index.md` — update the Hazards section when the feature introduced a hazard worth documenting in an existing concern.
- `docs/<package>/architecture.md` — update the `## Patterns` section (with cite-back) when the feature changed an architecture pattern within a package.
- `docs/architecture.md` — update the project-tier architecture doc when the feature changed cross-package architecture.

NEVER point the agent at `docs/features/`, `docs/api/`, or `docs/guides/` — those tiers are dropped under Plan F (see `tech-writer.md`'s Plan-F notes). A new concern (a new `src/` subfolder), a new API surface, or a new domain term is NOT hand-authored here — those are left to `/generate-docs` on its next run, which is why PHASE 4 prints a soft `/generate-docs` reminder for structural doc drift this surgical pass does not cover.

### Why both `/finalize` and `/generate-docs` touch `docs/`

`/finalize`'s tech-writer pass does TARGETED, feature-driven surgical updates at feature-completion time (Normal mode, scoped to the feature's changed files). `/generate-docs` does stamp-gated whole-codebase regeneration (tech-writer Skeleton-Fill mode). Both exist on purpose: `/finalize` keeps a shipped feature's docs current without forcing a whole-repo regen; `/generate-docs` is the canonical structural author. The PHASE-4 reminder is the soft pointer between them.

## Results block — PHASE 4 "Feature Finalized"

After the squash confirms, the orchestrator presents a block of this shape (values composed from the `squash` verb's per-repo outcome JSON, the PHASE-1 change data, and the PHASE-0/2 docs + summary state):

```
## Feature Finalized

**Commit**: [short hash] [commit message]
**Files**: [N] files changed
**Docs**: [updated <targets> | skipped — <reason> | tech-writer failed — <error>]
**Summary**: [included in squash | not found — /summarize was not run]

Feature is ready for PR.
```

Composition rules:

- **Commit** — the install/wrapper repo's new `head_sha` (shortened) + the `message_used` from the `squash` verb's `install_repo` outcome. In wrapper mode add a second `**Source commit**:` line from the `source_repo` outcome (the `[TICKET-ID] - Description` commit, traceless per D5).
- **Files** — the `file_count` from PHASE-1 change data.
- **Docs** — `updated <docs targets>` when the PHASE-2 tech-writer wrote and `[WIP]`-committed docs; `skipped — <reason>` when the agent justifiably found no docs needed; `tech-writer failed — <error>` when the agent errored (the squash still ran).
- **Summary** — `included in squash` when `specs/[feature]/summary.md` existed at PHASE 0 (its `[WIP]` commit folds into the squash); `not found — /summarize was not run` when the PHASE-0 soft-warn fired.
- When the squash was SKIPPED (already-pushed guard) or NO-OP'd (nothing to finalize), report that outcome in place of the **Commit** line instead of a clean-commit hash — never claim a squash that did not happen.

## What this block is NOT

- **No verdict.** `/finalize` renders no APPROVED / NEEDS WORK / REJECTED — the verdict is `/verify`'s. Do not add a verdict line.
- **No findings.** `/finalize` runs no finder ensemble and no refutation pass — findings are `/review`'s. Do not add a findings list.
- **No next-pipeline-command pointer.** `/finalize` is terminal — its "next step" is "create a PR", already named in the block. Do not point at a downstream command.
