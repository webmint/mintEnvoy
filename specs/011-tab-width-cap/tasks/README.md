# Tasks: 011-tab-width-cap

**Spec**: specs/011-tab-width-cap/spec.md
**Plan**: specs/011-tab-width-cap/plan.md
**Generated**: 2026-06-30
**Total tasks**: 2

## Dependency Graph

```
001 (relocate-width-cap-to-tab-cell) ──→ 002 (ct-cap-assertion-and-no-growth-test)
```

## Task Index

| # | Title | Agent | Depends on | Status |
|---|-------|-------|-----------|--------|
| 001 | relocate-width-cap-to-tab-cell | frontend-engineer | None | Complete |
| 002 | ct-cap-assertion-and-no-growth-test | frontend-engineer | 001 | Complete |

## Additions to Spec

None — the plan's File Impact (4 files) maps cleanly onto the two tasks; no files discovered during analysis beyond the plan.

## Risk Assessment

| Task | Risk | Reason |
|------|------|--------|
| 001 | Low | Two-file CSS change (add cell cap + remove label cap); `.tabbar`-scoped so bare `<Tabs>` consumers are untouched. Only sub-risk: removing the label cap must keep the base ellipsis triple (it lives on the separate base `.tabs__tab-label` rule, so it does). |
| 002 | Med | CT false-pass risks: a short-title fixture would never trigger truncation (mitigated by the long-title fixture + realistic-content baseline); the cap could clip the active accent/chevron (the `.tabs.tabbar { overflow:visible }` rule guards this — keep the 005 active-pseudo/screenshot assertions green; a `design-auditor` runtime pass at /review is the final clipping check). |

**Contract-chain deferral (documented):** `verify-contract-chain` flags 001's `Produces` as orphans and 001's `Expects` as unsatisfied. These are expected and accepted: 001's `Produces` map to spec ACs (AC-1/AC-2/AC-10), not to a downstream `Expects` — the helper cannot see spec ACs; and 001's `Expects` describe existing-codebase state (the pre-change Tabs.css/TabBar.css rules documented in spec §2) — the helper cannot see the codebase. The single real `001 → 002` link (the 220px cell cap) is now stated verbatim-identical across 001 `Produces` and 002 `Expects`. No missing producer or consumer task exists.

## Review Checkpoints

| Before Task | Reason | What to Review |
|-------------|--------|----------------|
| 002 | High-risk + fidelity convergence | The cap-relocation from 001 is in place; review that the CT asserts the 220px cell cap by computed-style equality, the long-title fixture genuinely overflows, the ellipsis fires, and no accent/chevron clipping was introduced. |

## Specialist Consultation

| Specialist | Sub-question | Input summary | Verdict | Cites |
| --- | --- | --- | --- | --- |
| architect | Validate task atomicity, dependency ordering, and contract-chain integrity for the 2-task split | Confirmed the 2-task split (001 CSS relocation, 002 CT proof) and `001→002` graph; required 3 fixes: semantic-only contract identifiers (no line numbers), AC-3 rests on 001's `.tabbar`-scoping (dropped the optional bare-consumer CT from 002), and carry the three feature-005 CT memory lessons into 002 as constraints | accepted | specs/011-tab-width-cap/plan.md §Key Design Decisions; spec §5 |
