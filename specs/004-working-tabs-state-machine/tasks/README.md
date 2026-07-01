# Tasks: 004-working-tabs-state-machine

**Spec**: /Users/mykolakudlyk/Projects/private/mintEnvoy/specs/004-working-tabs-state-machine/spec.md
**Plan**: /Users/mykolakudlyk/Projects/private/mintEnvoy/specs/004-working-tabs-state-machine/plan.md
**Generated**: 2026-06-24
**Total tasks**: 10

## Dependency Graph

```
001 (RequestSpec model) ──→ 002 (tabsStore slice) ──→ 003 (tabsStore tests)
                                                   └─→ 007 (TabBar organism) ──→ 008 (TabBar tests)
                                                                              └─→ 009 (App wiring)
004 (Tabs closable extension) ──→ 005 (Tabs closable tests)
                              ├─→ 006 (002 contract lineage)
                              ├─→ 007 (TabBar organism)
                              └─→ 010 (PrimitivesDemo variant)
```

Two independent roots: the **slice chain** (001→002→{003,007}) and the **primitive chain** (004→{005,006,010}). They converge at **007 (TabBar)**, which depends on both the slice (002) and the closable primitive (004). 009 (wiring) is the final integration step.

## Task Index

| #   | Title                                                 | Agent             | Depends on | Status   |
| --- | ----------------------------------------------------- | ----------------- | ---------- | -------- |
| 001 | Create RequestSpec domain model                       | frontend-engineer | None       | Complete |
| 002 | Create tabsStore zustand slice                        | frontend-engineer | 001        | Complete |
| 003 | Write tabsStore unit suite + serialization contract   | frontend-engineer | 002        | Complete |
| 004 | Extend Tabs primitive with opt-in closable/onClose    | frontend-engineer | None       | Complete |
| 005 | Extend Tabs tests for closable extension              | frontend-engineer | 004        | Complete |
| 006 | Record Tabs contract extension in feature-002 lineage | frontend-engineer | 004        | Complete |
| 007 | Create TabBar organism                                | frontend-engineer | 002, 004   | Complete |
| 008 | Write TabBar tests                                    | frontend-engineer | 007        | Complete |
| 009 | Wire TabBar into Shell tabs slot via App.tsx          | frontend-engineer | 007        | Complete |
| 010 | Register closable Tabs variant in PrimitivesDemo      | frontend-engineer | 004        | Complete |

## Specialist Consultation

| Specialist | Sub-question                                                                                                                                      | Input summary                                                                                                                                                                                                                                                                                                                                                                                 | Verdict  | Cites                                                                                                                                                               |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| architect  | Atomicity/bundling, dependency ordering+direction, contract-chain integrity, agent assignment, axe-core mapping (mandatory Phase 2 decision hook) | Approved set with 4 revisions: split AC-29 lineage out of the primitive task (separate T006); reassign test tasks qa-engineer→frontend-engineer (matches 001/002/003 convention, §3.4, no QA-owned tier); map AC-22 a11y to structural DOM assertions, NOT axe-core (not a dependency); fill blank Expects edges (007/010) + fix 009 dep to 007-only. Confirmed Auth union stays two-variant. | modified | specs/004-.../plan.md; src/renderer/src/components/molecules/**tests**/Tabs.ct.tsx (structural-assertion pattern); package.json (no axe-core); constitution.md §3.4 |

(All four architect revisions were applied to the task set before it was written. No further specialist was consulted — no consultation requests were emitted; the one domain question, roving-focus restoration, was settled by frontend-engineer at /plan.)

## Additions to Spec

- **AC-22 "axe pass" → structural DOM assertions.** The spec/plan prose mentions an "axe pass" for the `closable=true` a11y check, but axe-core is NOT a project dependency and the existing `Tabs.ct.tsx` (feature 002) establishes structural DOM assertions (role/tabIndex/aria-selected) as the project a11y-test pattern. Task 005 verifies AC-22/AC-12 via structural assertions; axe-core is intentionally NOT introduced (would violate §6.3 "no new dependency"). No source file additions beyond the plan's File Impact table were discovered.

## Risk Assessment

| Task | Risk     | Reason                                                                                                                                                                                                                                                                                                                                     |
| ---- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 001  | Low      | Greenfield plain types + factory; serialization shape is the only cross-task contract (pinned by 003).                                                                                                                                                                                                                                     |
| 002  | Med      | Lifecycle state machine — dedupe/neighbor/never-zero logic must satisfy AC-13–21 exactly; defensive no-ops on unknown ids.                                                                                                                                                                                                                 |
| 003  | Low      | Test authoring against a settled slice contract.                                                                                                                                                                                                                                                                                           |
| 004  | **High** | Per-tab ✕ extension must not break the 002 roving-tabindex a11y (Risk 1): nested-interactive-in-role=tab, lost focus on close, dangling tabindex. Mitigated by sibling `tabIndex={-1}` ✕ (not a roving stop), `useLayoutEffect` focus restoration, the three MUST-NOT guardrails, and the 005 byte-identical regression + structural a11y. |
| 005  | Low      | Test authoring; covers the 004 regression + CT focus/keyboard.                                                                                                                                                                                                                                                                             |
| 006  | Low      | Append-only documentation edit to the 002 spec lineage.                                                                                                                                                                                                                                                                                    |
| 007  | Med      | Convergence (depends on slice + closable primitive); dependency-direction discipline (Risk 2 — must not import a sibling organism; lib stays leaf).                                                                                                                                                                                        |
| 008  | Low      | Test authoring against the settled TabBar contract.                                                                                                                                                                                                                                                                                        |
| 009  | Low      | One-prop composition-root injection; Shell stays slot-agnostic (Risk 2). Assembled build must pass.                                                                                                                                                                                                                                        |
| 010  | Low      | Dev-only gallery entry, tree-shaken from production.                                                                                                                                                                                                                                                                                       |

Contract-chain gate note: `verify-contract-chain` exited 2 with advisory-only findings. Every genuine cross-task edge traces (002←001, 003←002, 005/006/010←004, 007←002+004, 008/009←007); the flagged "orphan Produces" all map to terminal spec ACs (AC-1/2/3/7/8/11/12/22–27/29) the helper cannot see, and the flagged "unsatisfied Expects" are existing 001/002/003 substrate (lib/ leaf layer, zustand, the Vitest/CT stack, the 002 Tabs primitive, the Shell `tabs?` slot, PrimitivesDemo) confirmed present in Phase 1. The chain is semantically intact; no missing producer/consumer.

Build-cache note (plan Risk 4): if a build/test error names a clean source file as the import source, clear the cache (`playwright/.cache`, `node_modules/.vite`, `dist`) and re-run BEFORE editing source or filing a bug. Hygiene note (plan Risk 5): keep this branch's commits to the feature's src + test files; avoid repo-wide reformatting.

## Review Checkpoints

| Before Task | Reason                                      | What to Review                                                                                                                                                                                                                                                                         |
| ----------- | ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 004         | High risk (Risk 1)                          | The closable extension preserves the 002 roving-tabindex a11y — ✕ is a sibling `tabIndex={-1}` (not a roving stop, not `role=tab`, not in `buttonRefs`); `closable=false` path is byte-identical; `useLayoutEffect` focus restoration has no dangling tabindex / no mouse-user hijack. |
| 007         | Convergence + first presentation-layer task | TabBar correctly composes both upstream contracts (slice selectors/actions + closable primitive); dependency direction is clean (imports Tabs molecule + lib only, never a sibling organism); label precedence + dirty marker via badge slot are correct.                              |
