# Tasks: 001-ui-primitives

**Spec**: /Users/mykolakudlyk/Projects/private/mintEnvoy/specs/001-ui-primitives/spec.md
**Plan**: /Users/mykolakudlyk/Projects/private/mintEnvoy/specs/001-ui-primitives/plan.md
**Generated**: 2026-06-21
**Total tasks**: 9

## Dependency Graph

```
001 (test stack + radix) ──→ 002 (icon set + lookup) ──→ 003 (Icon component) ─────────────┐
                         ──→ 004 (toastStore) ──→ 005 (Toast component) ──┐                 │
                         ──→ 006 (Modal component) ───────────────────────┤                 │
                         ──→ 007 (Dropdown component) ────────────────────┤                 │
                                                                          ├─→ 008 (App-root integration)
                                                                          └─→ 009 (demo route) ←─ 003,005,006,007
```

## Task Index

| #   | Title                                                   | Agent             | Depends on         | Status   |
| --- | ------------------------------------------------------- | ----------------- | ------------------ | -------- |
| 001 | set up renderer test stack and radix dependency         | frontend-engineer | None               | Complete |
| 002 | define the project-owned icon set and lookup            | frontend-engineer | 001                | Complete |
| 003 | build the inline SVG Icon component                     | frontend-engineer | 002                | Complete |
| 004 | build the zustand toastStore and imperative toast() API | frontend-engineer | 001                | Complete |
| 005 | build the Toast component over Radix Toast              | frontend-engineer | 004, 001           | Complete |
| 006 | build the Modal component over Radix Dialog             | frontend-engineer | 001                | Complete |
| 007 | build the Dropdown/popover component over Radix         | frontend-engineer | 001                | Complete |
| 008 | mount overlay substrate at the App root                 | frontend-engineer | 005, 006, 007      | Complete |
| 009 | build the dev-only primitives demo route                | frontend-engineer | 003, 005, 006, 007 | Complete |

## Additions to Spec

None — every task file maps to a file in the plan's File Impact table. The `App.tsx` modification (task 008) and per-component CSS were already enumerated in the plan, not discovered during decomposition.

## Specialist Consultation

| Specialist | Sub-question                                                                                                    | Input summary                                                                                                                                                                                                                                                                                    | Verdict  | Cites                                                            |
| ---------- | --------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------- | ---------------------------------------------------------------- |
| architect  | Task atomicity/bundling, dependency ordering & direction, contract-chain integrity for the 9-task decomposition | Confirmed graph acyclic + correctly directed, atomicity sound, all-frontend-engineer correct, no specialist needed; required 4 task-body revisions (AC-15→003/005/006/007 Produces; 009 dev-only-guard; AC-21→002/005; AC-19+§2.3 dep-direction constraint in 002/004/005/006/007) — all applied | accepted | specs/001-ui-primitives/plan.md, specs/001-ui-primitives/spec.md |

## Risk Assessment

> **Contract-chain gate note**: `verify-contract-chain` reports advisory orphan-Produces / unsatisfied-Expects findings for every task. These are literal-string-match false positives — the helper cannot see spec ACs (Produces map to ACs per the Spec-criteria headers + AC-coverage gate) nor existing-codebase/greenfield state (first-task Expects describe the boilerplate renderer + already-present `zustand`/`react`/`@renderer` alias). The dependency edges encode the real chain (002→003, 004→005, 005/006/007→008, 003/005/006/007→009); each downstream Expects names its upstream task. No real orphan or unsatisfied contract exists.

| Task                    | Risk | Reason                                                                                                                                                                                                                   |
| ----------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 001                     | High | No test framework exists; the Vitest + Playwright + radix-ui setup is gating — every interaction AC and all molecules depend on it (plan §9 risk 2). Riskiest-first.                                                     |
| 004                     | Med  | Toast queue is a design-decision state machine; toast-singleton boundary — multiple store instances would split the queue (plan §9 risk 7). Mitigation: single module-level store, `toast()` calls `getState().enqueue`. |
| 005                     | Med  | Radix Toast may not natively cover stacking + hover/focus pause + rapid-fire (plan §9 risk 1); store owns the queue, Radix renders items.                                                                                |
| 007                     | Med  | Edge-aware flip/shift + keyboard nav is the most behavior-dense molecule; styling Radix state via semantic classes may fight tokens (plan §9 risk 4).                                                                    |
| 008                     | Med  | Convergence + portal mount point: a detached portal node breaks z-order/scrim (plan §9 risk 8); nested-overlay Escape/focus composition (plan §9 risk 3).                                                                |
| 009                     | Low  | Demo route must be dev-only-guarded or it ships to production (plan §9 risk 9).                                                                                                                                          |
| 002, 004, 005, 006, 007 | Med  | Dependency-direction: `lib/` must not import from `components/`; all intra-renderer imports via `@renderer` alias (plan §9 risk 6 / §2.3 / AC-19) — named as a constraint in each task body.                             |
| 003, 005, 006, 007      | Low  | jsdom focus/keyboard fidelity gaps may hide a11y defects (plan §9 risk 5); Playwright component tests cover real-browser fidelity.                                                                                       |

## Review Checkpoints

| Before Task | Reason                                                 | What to Review                                                                                           |
| ----------- | ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------- |
| 001         | High-risk gating                                       | Test stack actually runs (a smoke test passes); radix-ui installed; `@renderer` alias resolves in Vitest |
| 003         | First presentation-layer task after the data layer     | Icon renders + falls back correctly; styling is semantic-class/token-bound with zero inline styles       |
| 008         | Convergence (depends on 005+006+007) + portal boundary | Single Toast.Provider mounted; nested overlays compose (Escape topmost-only, focus nest); z-order sane   |
| 009         | Convergence (depends on 003+005+006+007)               | Every primitive renders in its states; demo route is dev-only-guarded (not in production bundle)         |
