# Tasks: 010-request-bar-fidelity

**Spec**: specs/010-request-bar-fidelity/spec.md
**Plan**: specs/010-request-bar-fidelity/plan.md
**Generated**: 2026-06-28
**Total tasks**: 3

## Dependency Graph

```
001 (markup: labels + ⌘↵ keycap) ──→ 002 (CSS fidelity rewrite) ──→ 003 (CT fidelity suite)
                                  └────────────────────────────────→ 003
```

## Task Index

| # | Title | Agent | Depends on | Status |
|---|-------|-------|-----------|--------|
| 001 | restyle-requestbar-markup-labels-keycap | frontend-engineer | None | Complete |
| 002 | rewrite-requestbar-css-fidelity | frontend-engineer | 001 | Complete |
| 003 | add-ct-fidelity-suite | qa-engineer | 001, 002 | Complete |

## Additions to Spec

None — all five touched files (RequestBar.tsx, RequestBar.css, RequestBar.ct.tsx, RequestBar.stories.tsx, RequestBar.test.tsx) were already in the plan's File Impact / spec's §4 Affected Areas.

## Specialist Consultation

| Specialist | Sub-question | Input summary | Verdict | Cites |
| --- | --- | --- | --- | --- |
| architect | Atomicity/bundling (001 vs 002), dependency ordering (001→002→003), contract-chain integrity, agent assignment on design-decision tasks | Confirmed decomposition as-is: keep 001 (markup) and 002 (CSS) separate — distinct verification surfaces (001 unit-testable, 002 verified downstream in 003), asymmetric review risk (002 carries the Med-risk (0,3,0) specificity decision), coupling handled by the 001→002 dependency edge not bundling. Ordering acyclic + correctly directed (DOM→CSS→CT). Contracts trace cleanly, semantic identifiers only, AC union spans 1-19 with no orphans. Agents confirmed: 001/002 frontend-engineer, 003 qa-engineer. No specialist relay needed. | accepted | specs/010-request-bar-fidelity/plan.md; src/renderer/src/components/organisms/RequestBar.tsx; src/renderer/src/components/organisms/RequestBar.css |

## Risk Assessment

| Task | Risk | Reason |
|------|------|--------|
| 001 | Low | Presentational markup only — labels + a `canSend`-gated aria-hidden `<kbd>`; no logic touched. Main risk is the aria-label drop breaking `getByRole` name queries, mitigated by keeping visible label text === prior accessible name + the unit asserts. |
| 002 | Med | The `(0,3,0)` ancestor-scoped method-select override must out-specify the soft-chip `[data-mstyle='soft'] .method.{METHOD}` (0,3,0) by source order, declaring background/border only (no color) so per-method colour falls through; a specificity/source-order miss silently drops colour or leaks the tint. Mitigated by the bg-only override + 003's loud computed-style CT assert on both bg and colour. Source-order fragility: tokens.css imports before component CSS (confirmed). |
| 003 | Med | CT fidelity flakiness — Radix dismiss arm-race + the data-mstyle/tokens fixture context + jsdom's inability to resolve computed styles. Mitigated by real-browser Playwright CT, reusing the existing fixture scope + two-step dismiss gate, and clearing playwright/.cache + .vite + dist when a build error names a clean file. Convergence point (depends on 001 + 002). |

> Contract-chain deferral (advisory findings, documented per Phase 3.5): `verify-contract-chain` flagged orphan-Produces / unsatisfied-Expects, all marked advisory by the helper. They are false-positives: every orphan Produces maps to a spec AC (the `verify-ac-coverage` gate confirms all 19 ACs covered), and every unsatisfied Expects traces to confirmed feature-009 codebase state (the `canSend` predicate, the icon-only Save/Share with `aria-label`, the `cx('request-bar__method','method',method)` trigger, the `tokens.css` custom-properties and `[data-mstyle='soft'] .method.{METHOD}` rules) or to an upstream task's Produces (002/003 Expects → 001/002 Produces) that the helper's string matcher does not link because the Expects are worded as "Task 00N landed: …". No real orphan or missing producer exists; the chain is intact.

> Carried risk (not a contract-chain/AC-coverage gap): the exact reference geometry values (Q-1) are code-confirmed against design/styles.css but not yet runtime-confirmed; a `design-auditor` runtime screenshot + computed-style diff against design/reference.html (filled state) should run during task 003 / `/implement` before the fidelity ACs lock to the concrete numbers (plan §9 Risk-6).

## Review Checkpoints

| Before Task | Reason | What to Review |
|-------------|--------|----------------|
| 002 | High-risk (Med) — the `(0,3,0)` specificity override | Confirm the method-select override declares background/border/border-radius only (NO color), is anchored `.request-bar .request-bar__method.method`, wins the cascade by source order, and writes no data-mstyle; all new rules scoped under `.request-bar`. |
| 003 | Convergence (depends on 001 + 002) + High-risk fidelity verification | Confirm the computed-style assertions cover the enumerated props (incl. method-select bg/border + per-method colour, keycap presence/absence), the screenshot threshold is set, the fixture exercises the filled state, and all existing behaviour/unit suites stay green. |
