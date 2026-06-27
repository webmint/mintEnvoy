# Tasks: 006-reorganize-flat-components

**Spec**: /Users/mykolakudlyk/Projects/private/mintEnvoy/specs/006-reorganize-flat-components/spec.md
**Plan**: /Users/mykolakudlyk/Projects/private/mintEnvoy/specs/006-reorganize-flat-components/plan.md
**Generated**: 2026-06-26
**Total tasks**: 3

## Dependency Graph

```
001 (Move Divider to molecules) ──→ 002 (Move shell group to organisms/shell) ──→ 003 (Update classification sites)
```

## Task Index

| # | Title | Agent | Depends on | Status |
|---|-------|-------|-----------|--------|
| 001 | Move Divider to molecules and rewrite its importers | frontend-engineer | None | Complete |
| 002 | Move shell-domain group and Shell test trio into organisms/shell | frontend-engineer | 001 | Complete |
| 003 | Update constitution and architecture-doc classification sites | frontend-engineer | 002 | Complete |

## Additions to Spec

- `src/renderer/src/components/organisms/__tests__/Shell.ct.tsx` — moves with the Shell test trio (task 002). Not named in spec §4, surfaced during planning (DISCOVERY 1): it imports `./Shell.stories` relatively, so it must move with `Shell.stories.tsx` to keep that coupling valid.
- `src/renderer/src/components/organisms/__tests__/Shell.test.tsx` + `Shell.stories.tsx` Divider-import rewrite is scheduled in **task 001** (in place), not task 002 — the architect Phase-2 validation found these are 2 of the 4 Divider importers, so deferring them would break task 001's own boundary (tsc + Vitest could not resolve `Divider`).
- `docs/architecture.md` carries more moved-path citation sites than spec §4 named (module-structure tree, prose tier description, and two `Shell.tsx:250`/`Divider.tsx:250` code-comment markers, beyond the AC-10 table + mermaid). Task 003 updates all five in lockstep.

## Risk Assessment

| Task | Risk | Reason |
|------|------|--------|
| 001 | Med | Moving Divider deletes its old path; all four importers (PaneSplit, Sidebar, Shell.test.tsx, Shell.stories.tsx) must be rewritten or tsc/Vitest break at this boundary. Caught by typecheck + the grep done-condition. |
| 002 | High | The largest move (~13 files). A missed `@renderer` rewrite, a dropped sibling `.css`, or a broken `Shell.ct.tsx → ./Shell.stories` relative coupling breaks the renderer import graph or silently degrades visuals (the 005 `Tabs.stories.tsx`→`Shell.css` brittleness). Caught by typecheck (both configs) + build + the full CT suite + the old-path grep. Review checkpoint set. |
| 003 | Low | Docs-only; no import graph or runtime impact. Residual risk is classification-site drift — the `docs/architecture.md` code-comment markers are not covered by AC-10/AC-11, so the task's own `grep -nE 'organisms/(…)' constitution.md docs/architecture.md` done-condition is the backstop. |

**Contract-chain gate (advisory deferral):** `verify-contract-chain` exits 2 on this breakdown, but every finding is a known false-positive of its verbatim string-matcher, and the helper self-annotates each as such. The contracts here are file-existence and import-path facts: the "orphan Produces" all map to spec ACs (AC-2/3/4/11) the gate cannot see, and the "unsatisfied Expects" are either pre-existing codebase state (e.g. task 001 expects `organisms/Divider.tsx` to exist at start) or cross-task hand-offs whose wording differs from the upstream Produces (task 001 produces "importers point to `molecules/Divider`" → task 002 expects "(from 001) … `molecules/Divider`"). The semantic chain 001→002→003 is sound and was validated by the Phase-2 architect consultation. No structural defect; deferred.

## Review Checkpoints

| Before Task | Reason | What to Review |
|-------------|--------|----------------|
| 002 | High-risk (largest move; import-graph + CSS-coupling exposure) | Confirm all four shell components + their `.css` landed under `organisms/shell/`, the test trio relocated together with `Shell.ct.tsx`'s relative import intact, every `@renderer` importer (App, Shell, the two fixtures, Tabs.stories) rewritten, no barrel file created, and the old-path grep is clean before proceeding to the docs task. |

## Specialist Consultation

| Specialist | Sub-question | Input summary | Verdict | Cites |
| --- | --- | --- | --- | --- |
| (none) | — | — | — | — |

The mandatory Phase-2 architect consultation found and corrected a contract-chain defect: draft task 001 rewrote only 2 of the 4 Divider importers, leaving `Shell.test.tsx:28` + `Shell.stories.tsx:14` importing a deleted path — which would fail task 001's own boundary verify. The revision folds those two in-place rewrites into task 001. No additional specialists were consulted (single renderer stack; all-mechanical, statically-detectable refactor). Architect verdict: REVISE 001, CONFIRM 002 + 003. Cites: src/renderer/src/components/organisms/__tests__/Shell.test.tsx:28, Shell.stories.tsx:14.
