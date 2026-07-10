# Tasks: 016-load-design-fonts

**Spec**: specs/016-load-design-fonts/spec.md
**Plan**: specs/016-load-design-fonts/plan.md
**Generated**: 2026-07-09
**Total tasks**: 5

## Dependency Graph

```
001 (add @fontsource deps) ──→ 002 (create fonts.css + import) ──→ 003 (reorder --font-sans + base.css) ──→ 005 (font-load CT + baselines)
                                              ├──→ 004 (document self-hosted fonts)
                                              └──→ 005 (font-load CT + baselines)
```

## Task Index

| # | Title | Agent | Depends on | Status |
|---|-------|-------|-----------|--------|
| 001 | Add @fontsource dependencies | frontend-engineer | None | Complete |
| 002 | Create fonts.css @font-face + import in main.tsx | frontend-engineer | 001 | Complete |
| 003 | Reorder --font-sans + point base.css body at token | frontend-engineer | 002 | Complete |
| 004 | Document self-hosted fonts | frontend-engineer | 002 | Complete |
| 005 | Font-load fidelity CT + regenerate baselines | qa-engineer | 002, 003 | Complete |

## Additions to Spec

None — all task files map to the plan's File Impact rows. (The `src/main/index.ts` / CSP row in the plan is context-only, NO change.)

## Specialist Consultation

| Specialist | Sub-question | Input summary | Verdict | Cites |
| --- | --- | --- | --- | --- |
| architect | Validate atomicity, ordering, contract chain, implementability of the 5-task decomposition | CONFIRM with revise-draft notes: cite AC-2 on 001; add woff2-filename-enumeration + vite-resolvable-relative-url() done-conditions to 002. Graph acyclic, contracts chain, no escalations | modified | specs/016-load-design-fonts/plan.md; own-reasoning |
| (none) | — | — | — | — |

## Risk Assessment

| Task | Risk | Reason |
|------|------|--------|
| 001 | Low | Mechanical dep add; only risk is bundle-size (latin/static weights bound it) |
| 002 | Med | The `url()` specifier form is the real build-failure watch-item — must be a vite-resolvable relative path to node_modules, not a bare `@fontsource/...` specifier (vite silently fails to bundle those). Done-When covers it |
| 003 | Med | Edits the doc-labeled "generated" tokens.css (DEPARTURE, justified — no pipeline exists); value-only reorder, AC-13 gate asserts no @font-face lands there |
| 004 | Low | Single doc-note edit |
| 005 | Med | Convergence checkpoint; baseline regen must rm stale PNGs (—update-snapshots alone leaves sub-tolerance diffs stale, per prior lesson); assert loaded typeface not pixel-diff vs reference (reference renders SF for sans on macOS) |

**Contract-chain gate deferral (documented)**: `verify-contract-chain` reports advisory ORPHAN-PRODUCES / UNSATISFIED-EXPECTS findings. These are false positives from the helper's limited view — it cannot see spec ACs or existing-codebase state. The chain is intact: 001→002→003→005 and 002→004 are correctly edged; each cross-task `Expects` paraphrases the upstream task's `Produces` (e.g. 003/005 "fonts.css loads Inter + JetBrains Mono (Task 002 Produces)"); terminal `Produces` (deps, token edits, docs, tests) map to spec ACs. The Phase-2 architect explicitly validated contract-chain integrity. No revision needed.

## Review Checkpoints

| Before Task | Reason | What to Review |
|-------------|--------|----------------|
| 005 | Convergence (depends on 002 + 003) + high-risk baseline regen | fonts.css url() actually bundles (built woff2 resolve); --font-sans Inter-first + base.css body use the token; CT asserts loaded typeface not a reference pixel-diff; stale baselines deleted before regen |
