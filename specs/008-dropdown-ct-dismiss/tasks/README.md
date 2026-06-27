# Tasks: 008-dropdown-ct-dismiss

**Spec**: /Users/mykolakudlyk/Projects/private/mintEnvoy/specs/008-dropdown-ct-dismiss/spec.md
**Plan**: /Users/mykolakudlyk/Projects/private/mintEnvoy/specs/008-dropdown-ct-dismiss/plan.md
**Generated**: 2026-06-27
**Total tasks**: 1

## Dependency Graph

```
001 (Gate Dropdown click-outside CT tests on overlay readiness)  [no dependencies]
```

## Task Index

| # | Title | Agent | Depends on | Status |
|---|-------|-------|-----------|--------|
| 001 | Gate Dropdown click-outside CT tests on overlay readiness | frontend-engineer | None | Complete |

## Additions to Spec

None — the single task edits exactly the one file in the plan's File Impact (`Dropdown.ct.tsx`). No cascading files discovered; the fixture (`Dropdown.stories.tsx`) and production `Dropdown.tsx` stay untouched.

## Risk Assessment

| Task | Risk | Reason |
|------|------|--------|
| 001 | Low | Single-file, test-only change applying the plan's settled readiness-API decision; no production/process surface. Residual risks (all Low, one Low/Med — macrotask-turn sufficiency) are carried from plan §Risk Assessment and mitigated there (the animation-completion await crosses far past one macrotask turn in CT; AC-5 repeated-run check catches residual flake). Implementer note: keep a SINGLE corner click — do NOT drift to a `toPass()` retry loop (plan Decision 2). |

**Contract-chain deferral (Phase 3.5 advisory)**: `verify-contract-chain` reports orphan Produces + unsatisfied Expects on task 001. Both are the expected single-task case and are accepted: task 001 is the only (terminal) task, so its Produces feed spec ACs directly (confirmed by `verify-ac-coverage`: all 8 ACs covered, not a downstream Expects), and its Expects describe pre-existing codebase state (the two tests + `menu`/`trigger` locators already present in `Dropdown.ct.tsx`, verified by reading the file). No missing producer/consumer task.

## Review Checkpoints

| Before Task | Reason | What to Review |
|-------------|--------|----------------|
| (none) | Single task; no convergence, no layer crossing, no High-risk task | The `/implement` per-task hard gate covers review of the one task. |

## Specialist Consultation

| Specialist | Sub-question | Input summary | Verdict | Cites |
| --- | --- | --- | --- | --- |
| architect | Atomicity / ordering / contract-chain for the 1-task decomposition + agent assignment | One task correct (do not split per case); deps clean; contracts trace; fixed two Expects defects (AC-3/AC-4 labels swapped, non-verbatim focus-return test name); frontend-engineer accepted | accepted | specs/008-dropdown-ct-dismiss/plan.md; src/renderer/src/components/molecules/__tests__/Dropdown.ct.tsx:185,236 |
| (none) | — | — | — | — |

The architect emitted zero consultation requests — a fully-diagnosed, test-only timing fix on a single renderer CT file is generalist scope.
