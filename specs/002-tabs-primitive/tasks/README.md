# Tasks: 002-tabs-primitive

**Spec**: /Users/mykolakudlyk/Projects/private/mintEnvoy/specs/002-tabs-primitive/spec.md
**Plan**: /Users/mykolakudlyk/Projects/private/mintEnvoy/specs/002-tabs-primitive/plan.md
**Generated**: 2026-06-22
**Total tasks**: 3

## Dependency Graph

```
001 (build-tabs-primitive-component) ──→ 002 (write-tabs-tests)
                                     ──→ 003 (register-tabs-in-primitivesdemo)
```

## Task Index

| # | Title | Agent | Depends on | Status |
|---|-------|-------|-----------|--------|
| 001 | build-tabs-primitive-component | frontend-engineer | None | Complete |
| 002 | write-tabs-tests | qa-engineer | 001 | Complete |
| 003 | register-tabs-in-primitivesdemo | frontend-engineer | 001 | Complete |

## Additions to Spec

- `src/renderer/src/components/molecules/__tests__/Tabs.stories.tsx` — NOT in the plan's File Impact, added during breakdown (Phase 2 architect validation). Every molecule's `.ct.tsx` imports its mount fixtures from a co-located `*.stories.tsx` (Playwright CT requires components defined outside the test file — see `Dropdown.stories.tsx`/`Dropdown.ct.tsx`). The CT test in task 002 is non-functional without it. Covered by task 002.

## Risk Assessment

| Task | Risk | Reason |
|------|------|--------|
| 001 | High | The hand-rolled WAI-ARIA tablist (manual roving tabindex + Arrow/Home/End/wrap + disabled-skip + no-selection guard) is net-new a11y logic with no Radix engine to lean on — the highest-failure-probability surface (plan Risk Assessment rows 1 & 3). Departs from the "wrap Radix" precedent. |
| 002 | Med | Larger interaction-test surface — the reimplemented keyboard/disabled/no-selection branches must all be covered, and the CT axe assertion is the authoritative check that the hand-rolled path emits no dangling `aria-controls` (plan Risk row 2; the AC-7 guarantee). |
| 003 | Low | Mechanical — follows the existing `XSection` registration pattern in PrimitivesDemo.tsx. |

**Contract-chain disposition**: `verify-contract-chain` exited 2 with advisory-only findings — all are the helper's documented blind spots, reviewed and benign: (a) 001's `Produces` (exports, `role="tablist"`, css selectors) are consumed by 002/003 `Expects` (real chain — the helper missed the link on literal-token wording) or terminate at a spec AC (AC-2/4/5–10) the helper cannot see; (b) the "unsatisfied" `Expects` (`cx` at `cx.ts:18`, `tokens.css`, `molecules/` + Dropdown precedent, Vitest/CT config from 001) are existing-codebase state, all verified in Phase 1. No real orphan or break. AC-coverage gate: 15/15 covered.

## Review Checkpoints

| Before Task | Reason | What to Review |
|-------------|--------|----------------|
| 001 | high risk | The hand-rolled tablist: tablist/tab roles + aria-selected tied to activeId, roving tabindex (single tab-stop), Arrow/Home/End wrap + disabled-skip, no-selection guard, actions slot outside the tablist, no inline styles, no node/electron/Radix import |
| 002 | high risk | Test coverage of every AC-5/6/7/8/9/10 branch; the Playwright CT axe assertion proves zero a11y violations (no dangling aria-controls — the core AC-7 risk) |

## Specialist Consultation

Record one row per specialist consulted during breakdown planning. The architect is the decision-authority and synthesizer; specialists supply domain input only.

| Specialist | Sub-question | Input summary | Verdict | Cites |
| --- | --- | --- | --- | --- |
| architect | Validate task atomicity / dependency ordering / contract-chain integrity for the 3-task draft; validate agent on the design-decision task | Confirmed 3-task split, ordering (001→002, 001→003), and contracts. BLOCKING fix: task 002 must add `Tabs.stories.tsx` (CT fixture required outside test file) + an AC-8 actions-slot assertion; task 003 Produces must add the `TabsSection` invocation. Confirmed 001=frontend-engineer (design pre-locked by plan). | modified | Dropdown.ct.tsx (stories-fixture import); spec.md AC-8; plan.md Key Design Decisions |
