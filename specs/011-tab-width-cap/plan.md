# Plan: tab-width-cap

**Date**: 2026-06-30
**Spec**: specs/011-tab-width-cap/spec.md
**Status**: Approved

## Specialist Consultation

**Invocations**:
- Phase 0 alternatives: no — N/A (alternatives were settled by the research report: relocate cap to cell, with the flex-layer and label-bump alternatives ruled out; no fresh 2+-alternative discovery needed).
- Phase 1.3 architecture decisions: yes (mandatory).
- Specialists consulted (orchestrator-relayed on the architect's request, or directly): none requested — see table.

**Architect-authored sections** (transcribed verbatim from architect return):
- Layer Map: rows 1-3
- Key Design Decisions: rows 1-5
- Risk Assessment seeds: rows 1-3 (merged with spec §9 risks)
- Constitution Compliance flags: §3.6 / §4 / §2.2 / §6.1 — all SATISFIED / not-at-risk

| Specialist | Sub-question | Input summary | Verdict | Cites |
| --- | --- | --- | --- | --- |
| (none) | — | — | — | — |

The architect determined no plan-time specialist consult was warranted: pure presentation-layer CSS, single package, no security/data/API/dependency/novel-UX surface. The one runtime concern (cap clipping the active accent/chevron; ellipsis firing under the real `.tabbar` cascade) is routed to a `design-auditor` runtime pass at `/review` and the Playwright CT computed-style probe — not a plan-time consult.

## Summary

Relocate the working-tabs width cap from the LABEL onto the tab CELL: add `max-width:220px` to the `.tabbar .tabs__tab-wrapper` rule in Tabs.css (the design `.tab` cell, contract §5) and remove the divergent `max-width:200px` from `.tabbar .tabs__tab-label` in TabBar.css, reusing the base `.tabs__tab-label` ellipsis rule (Tabs.css:196). A Playwright CT computed-style assertion (wrapper resolves to 220px) plus a long-title no-growth test, reusing the existing TabbarFidelityFixture, proves it in a real browser. Pure CSS, `.tabbar`-scoped, zero behaviour change.

## Technical Context

**Architecture**: Renderer presentation layer only — the Tabs molecule's `.tabbar`-scoped CSS block (Tabs.css) and the TabBar organism's strip-chrome CSS (TabBar.css), with co-located Playwright CT. No main / preload / lib / store / data-model / API layer is touched.
**Error Handling**: N/A — declarative CSS; no fallible operation added.
**State Management**: Unchanged — no store, descriptor, or component-state change; deriveLabel and tabsStore stay byte-identical.

## Constitution Compliance

- §3.6 Search-before-building / DRY: **compliant** — reuses the base ellipsis rule (Tabs.css:196), adds only the missing cell cap; no new truncation CSS.
- §4 Prefer design tokens / no inline styles: **compliant** — class-based rule; the `220px` literal matches the established prior-art (`200px` literal) for a component geometric cap (no per-component width token exists); no inline style.
- §2.2 Renderer tier import direction: **compliant** — CSS-only, no imports added or moved.
- §6.1 Minimal changes: **compliant** — exactly one declaration added + one removed + the co-located fidelity test.

## Implementation Approach

### Layer Map

| Layer | What | Files (existing or new) |
|-------|------|------------------------|
| Renderer — molecule styles (Tabs primitive, `.tabbar`-scoped block) | Add `max-width:220px` to the `.tabbar .tabs__tab-wrapper` cell rule (the design `.tab` cell); base `.tabs__tab-label` ellipsis rule reused unchanged | src/renderer/src/components/molecules/Tabs.css |
| Renderer — organism styles (TabBar strip chrome) | Remove the divergent `.tabbar .tabs__tab-label { max-width:200px }` cap so the single cap lives on the cell | src/renderer/src/components/organisms/TabBar.css |
| Renderer — co-located Playwright CT (fidelity + behavior) | Add computed-style assertion (wrapper `max-width` resolves to 220px) to the existing wrapper-geometry block; add a long-title fixture + a no-growth test (cell ≤220px, label shows ellipsis); reuse TabbarFidelityFixture | src/renderer/src/components/molecules/__tests__/Tabs.ct.tsx, src/renderer/src/components/molecules/__tests__/Tabs.stories.tsx |

### Key Design Decisions

| Decision | Chosen Approach | Why | Alternatives Rejected |
|----------|----------------|-----|----------------------|
| Which element carries the width cap | Cap the CELL (`.tabbar .tabs__tab-wrapper`) at 220px; remove the label cap | Contract §5 places `max-width` on the `.tab` cell; capping the cell makes width independent of method-chip width and fires the existing label ellipsis (AC-1/AC-6/AC-7). Not a departure — aligns code to the contract | Bump label cap to 220px in place: leaves cell width = chip+label+padding (varies with chip, can exceed 220px), fails AC-6/AC-9 |
| Where the cap rule lives | In Tabs.css, inside the existing `.tabbar`-scoped override block (NOT TabBar.css) | The `.tabbar` cell-geometry overrides (gap/padding/border at Tabs.css:421) already live here; the cap belongs with them. `.tabbar`-scoping keeps bare `<Tabs>` consumers uncapped (AC-3). Consistent with the feature-005 `.tabbar`-scoping precedent — not a departure | Put the rule in TabBar.css: splits cell-geometry across two files, breaks the Tabs.css-owns-`.tabbar`-cell-geometry grouping |
| Truncation machinery for the relocated cap | Reuse the base `.tabs__tab-label` ellipsis rule (Tabs.css:196 — nowrap/overflow-hidden/text-overflow-ellipsis/flex:1) | §3.6 search-before-building: the canonical rule already matches contract B1 and fires once the cell is capped. Removing the label cap drops only its `max-width`, not the ellipsis triple (which lives on the base rule) | Add fresh truncation declarations: duplicates an existing rule, violates DRY/§3.6 |
| `max-width:220px` literal vs a token | Literal `220px` (resolved contract value) with a comment citing contract §5 | Not a departure — the prior cap was also a literal `200px`; tokens.css has no per-component width token; the contract asserts geometric caps as resolves-to-the-literal. The comment satisfies AC-10 | New width token in tokens.css: out of scope, single call-site, over-engineers a one-off cap |
| Test strategy for the cap | Playwright CT computed-style equality (220px) + long-title fixture no-growth test, reusing TabbarFidelityFixture | §3.4: jsdom cannot resolve computed layout, so the cap is proven in a real browser. The fixture already loads tokens.css/TabBar.css/Shell.css/soft-mstyle, reproducing the cascade (closes the research Open Uncertainty). Long-title fixture avoids the short-title false-pass (§9 Risk). Satisfies AC-7/AC-8/AC-9 | Vitest/jsdom unit test: cannot resolve computed `max-width`/layout — false signal |

### File Impact

| File | Action | What Changes |
|------|--------|-------------|
| src/renderer/src/components/molecules/Tabs.css | Modify | Add `max-width: 220px;` to the `.tabbar .tabs__tab-wrapper` rule (≈:421), with a comment citing design-fidelity-contract §5 and noting the cap moved off the label onto the cell (AC-1, AC-6, AC-10) |
| src/renderer/src/components/organisms/TabBar.css | Modify | Remove the `max-width: 200px;` declaration from `.tabbar .tabs__tab-label` (≈:88); the base Tabs.css:196 rule retains the overflow/ellipsis/nowrap, so the rule's remaining declarations (if any) stay or the now-redundant block is dropped (AC-2) |
| src/renderer/src/components/molecules/__tests__/Tabs.stories.tsx | Modify | Add a long-title fixture variant (or extend TabbarFidelityFixture) so a tab's title overflows the 220px cell, enabling the no-growth/ellipsis assertion |
| src/renderer/src/components/molecules/__tests__/Tabs.ct.tsx | Modify | Add a computed-style assertion that `.tabbar .tabs__tab-wrapper` `max-width` resolves to 220px in the existing AC-15 wrapper-geometry block; add a no-growth test (long-title tab stays ≤220px and its label computed `text-overflow` is ellipsis) (AC-7, AC-8, AC-9) |

### Documentation Impact

No documentation changes expected — internal CSS-fidelity implementation only. The docs/architecture.md "`.tabbar` visual contract spans two CSS files" hazard already documents the Tabs.css/TabBar.css split this change works within; the cap relocation does not alter that narrative.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Unscoped cap leaks to bare `<Tabs>` consumers (section-tabs, PrimitivesDemo) and regresses them | Low | Med | Add the cap only inside the `.tabbar`-scoped selector (005 precedent); AC-3 asserts bare consumers stay uncapped; no change to the base `.tabs__tab-wrapper` |
| Removing the label cap also drops its overflow/ellipsis/nowrap, breaking truncation if the base rule lacks them | Low | Low | Confirm the base Tabs.css:196 ellipsis triple is present before removal; keep the AC-16 label flex/overflow CT assertions green; assert ellipsis on the long-title fixture |
| The 220px cap clips the active accent pseudo-element or the overflow chevron | Low | Med | Rely on the existing `.tabs.tabbar { overflow:visible }` rule; keep the 005 active-pseudo + screenshot CT assertions green; design-auditor runtime pass at /review confirms no clipping |
| A short-title CT fixture never triggers truncation → false pass on the no-growth assertion | Med | Low | Add an explicit long-title fixture; assert both the 220px cap and the rendered ellipsis; baseline the width CT with realistic content, not empty-vs-filled |
| A future method-chip width change makes the title truncate sooner inside the fixed cell | Low | Low | Accepted — the cell cap is fixed and the label flexes; chip width is bounded; earlier truncation is the intended overflow behaviour |

## Dependencies

None. No package to install, no service to configure, no environment variable. Reuses the existing Tabs.css, TabBar.css, tokens.css, and the established Playwright CT fidelity harness (TabbarFidelityFixture).

## Supporting Documents

- [Research](../../research/2026-06-29-tabbar-tab-grows-with.md) — root cause + recommended approach (relocate cap to cell); no new research.md generated (no Phase 0 signals — pure CSS, no new library/integration/architecture-alternative).

## Handoff note for /breakdown

The spec §2 records that no current CT assertion pins the old 200px label cap (only the AC-16 label flex/overflow assertions exist). If `/breakdown` finds any assertion that pins the removed 200px label cap, re-point it to the 220px wrapper cap rather than leaving an assertion against a deleted rule.
