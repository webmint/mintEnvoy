# Task 001: relocate-width-cap-to-tab-cell

**Feature**: 011-tab-width-cap
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: None
**Blocks**: 002
**Spec criteria**: AC-1, AC-2, AC-3, AC-4, AC-5, AC-10, AC-11, AC-12, AC-13
**Review checkpoint**: No
**Context docs**: design/design-fidelity-contract.md (§5 Tab strip)

## Files

| File                                             | Action | Description                                                                                                    |
| ------------------------------------------------ | ------ | -------------------------------------------------------------------------------------------------------------- |
| src/renderer/src/components/molecules/Tabs.css   | Modify | Add `max-width: 220px` to the `.tabbar .tabs__tab-wrapper` rule + a comment citing design-fidelity-contract §5 |
| src/renderer/src/components/organisms/TabBar.css | Modify | Remove the `max-width: 200px` declaration from the `.tabbar .tabs__tab-label` rule                             |

## Description

Relocate the working-tabs width cap from the LABEL onto the tab CELL, matching design-fidelity-contract §5 (which puts `max-width` on the `.tab` cell, not the label). Today the `.tabbar .tabs__tab-wrapper` cell (the design `.tab` equivalent) has no `max-width`, so it grows with title length; the only cap is a divergent `max-width: 200px` on `.tabbar .tabs__tab-label`. Add the 220px cap to the cell wrapper and remove the 200px label cap. The base `.tabs__tab-label` rule already carries the ellipsis triple (`white-space:nowrap` / `overflow:hidden` / `text-overflow:ellipsis` / `flex:1`), which fires once the cell is capped — reuse it, write no new truncation CSS.

This is CSS-only and `.tabbar`-scoped: do NOT touch `TabBar.tsx`, `Tabs.tsx`, `deriveLabel`, the descriptor contract, the a11y engine, or `tabsStore`. Both edits land together — removing the label cap without adding the cell cap would ship an uncapped tab.

## Change Details

- In `src/renderer/src/components/molecules/Tabs.css` (the `.tabbar .tabs__tab-wrapper` rule, ≈ near line 421 — locate by selector, not line):
  - Add `max-width: 220px;` to the rule body.
  - Add a comment citing `design-fidelity-contract §5` and noting the cap moved off the label onto the cell (satisfies AC-10).
- In `src/renderer/src/components/organisms/TabBar.css` (the `.tabbar .tabs__tab-label` rule, ≈ near line 88 — locate by selector, not line):
  - Remove the `max-width: 200px;` declaration. The base `.tabs__tab-label` rule in `Tabs.css` retains `overflow:hidden` / `text-overflow:ellipsis` / `white-space:nowrap`, so truncation is preserved. If removing `max-width` leaves the `.tabbar .tabs__tab-label` rule with no declarations, drop the now-empty rule block.

## Contracts

### Expects (checked before execution)

- The `.tabbar .tabs__tab-wrapper` rule exists in `Tabs.css` and carries no `max-width`.
- The `.tabbar .tabs__tab-label` rule with a `max-width: 200px` declaration exists in `TabBar.css`.
- The base `.tabs__tab-label` rule in `Tabs.css` carries the `white-space:nowrap` + `overflow:hidden` + `text-overflow:ellipsis` declarations.

### Produces (checked after execution)

- The `.tabbar .tabs__tab-wrapper` rule in `Tabs.css` contains `max-width: 220px`.
- The `.tabbar .tabs__tab-label` rule in `TabBar.css` contains no `max-width: 200px` declaration.
- The base `.tabs__tab-label` ellipsis declarations in `Tabs.css` are unchanged.
- No change to `TabBar.tsx`, `Tabs.tsx`, or any non-CSS file (deriveLabel and the descriptor contract stay byte-identical).

## Done When

- [x] `.tabbar .tabs__tab-wrapper` in `Tabs.css` has `max-width: 220px` with a §5-citing comment
- [x] `.tabbar .tabs__tab-label` in `TabBar.css` no longer declares `max-width: 200px`
- [x] The cap is `.tabbar`-scoped — no change to the base `.tabs__tab-wrapper` rule, so bare `<Tabs>` consumers stay uncapped (AC-3)
- [x] No `.tsx` / JS file changed (deriveLabel, descriptor, a11y, tabsStore unchanged — AC-4, AC-5)
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-30T07:04:57Z
**Files changed**: src/renderer/src/components/molecules/Tabs.css, src/renderer/src/components/organisms/TabBar.css
**Contract**: Expects 3/3 | Produces 4/4
**Notes**: Cap relocated to .tabbar .tabs**tab-wrapper (220px) with §5 comment; .tabbar .tabs**tab-label removed in TabBar.css. Deviation: removed the whole redundant rule (its post-cap declarations duplicated base .tabs\_\_tab-label) instead of only the max-width line, per review-panel cleanup; TabBar.css file-block header rewritten Label-truncation -> Tab-width-cap.
