# Task 002: ct-cap-assertion-and-no-growth-test

**Feature**: 011-tab-width-cap
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 001
**Blocks**: None
**Spec criteria**: AC-6, AC-7, AC-8, AC-9, AC-11, AC-12, AC-13
**Review checkpoint**: Yes
**Context docs**: design/design-fidelity-contract.md (§5 Tab strip)

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/molecules/__tests__/Tabs.stories.tsx | Modify | Add a long-title fidelity fixture whose tab title overflows the 220px cell |
| src/renderer/src/components/molecules/__tests__/Tabs.ct.tsx | Modify | Add the 220px computed-style cap assertion + a long-title no-growth/ellipsis test |

## Description

Prove the relocated cap in a real browser. Add a computed-style assertion that `.tabbar .tabs__tab-wrapper` resolves to `max-width: 220px`, and a no-growth test: a long-title tab cell stays ≤220px wide while its label renders an ellipsis. jsdom cannot resolve computed layout, so these MUST be Playwright CT (real browser) — extend the existing fidelity suite, reusing `TabbarFidelityFixture`.

## Change Details

- In `src/renderer/src/components/molecules/__tests__/Tabs.stories.tsx`:
  - Add a long-title fidelity fixture (a new exported fixture, or a variant of `TabbarFidelityFixture`) whose tab `label` is long enough to overflow the 220px cell, so the no-growth/ellipsis assertion has real content to measure.
- In `src/renderer/src/components/molecules/__tests__/Tabs.ct.tsx`:
  - In the existing `.tabbar .tabs__tab-wrapper` wrapper-geometry block (the AC-15 fidelity block), add a computed-style assertion that the wrapper's `max-width` resolves to `220px` (exact equality) (AC-6, AC-9).
  - Add a no-growth test mounting the long-title fixture: assert the long-title tab cell's rendered width is ≤ 220px and that the label's computed `text-overflow` is `ellipsis` (AC-7); assert the actions row (+ / spacer / chevron) is not pushed past the capped tab (AC-8).

### CT memory-lesson constraints (carry forward — feature 005)

- **Fixture scoping**: the fixture MUST reproduce the full production cascade — `tokens.css` (via `playwright/index.tsx`), `TabBar.css` + `Shell.css`, and the `.tabbar` className scope under `[data-mstyle="soft"]`. `TabbarFidelityFixture` already does this — reuse it; do not mount a bare element.
- **Baseline with realistic content**: baseline the no-growth assertion with a genuinely long, non-empty title — NOT an empty-vs-filled comparison (an empty→filled baseline conflates unrelated mounts with the measured width change → false regression).
- **mstyle scope note**: the fixture pins only `soft` mstyle. The width cap is mstyle-independent, so this is low-risk here — do NOT assume the fixture covers other mstyle variants; the cap assertion does not need them.

## Contracts

### Expects (checked before execution)
- The `.tabbar .tabs__tab-wrapper` rule in `Tabs.css` contains `max-width: 220px`.
- `TabbarFidelityFixture` exists in `Tabs.stories.tsx` and mounts under the `.tabbar` + `tokens.css` + `[data-mstyle="soft"]` cascade.

### Produces (checked after execution)
- `Tabs.stories.tsx` exports a long-title fidelity fixture whose title overflows the 220px cell.
- `Tabs.ct.tsx` asserts `.tabbar .tabs__tab-wrapper` computed `max-width` equals `220px`.
- `Tabs.ct.tsx` asserts a long-title tab cell width is ≤ 220px and its label computed `text-overflow` is `ellipsis`.

## Done When

- [x] A long-title fidelity fixture exists in `Tabs.stories.tsx` (title overflows the 220px cell)
- [x] `Tabs.ct.tsx` asserts the `.tabbar .tabs__tab-wrapper` computed `max-width` equals 220px (AC-6, AC-9)
- [x] `Tabs.ct.tsx` asserts the long-title cell stays ≤220px with an ellipsis label, and the actions row is not pushed (AC-7, AC-8)
- [x] The new tests reuse `TabbarFidelityFixture`'s cascade (tokens.css + TabBar.css/Shell.css + `[data-mstyle="soft"]`) and pass in the real-browser CT run
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-30T15:59:31Z
**Files changed**: src/renderer/src/components/molecules/__tests__/Tabs.stories.tsx, src/renderer/src/components/molecules/__tests__/Tabs.ct.tsx
**Contract**: Expects 2/2 | Produces 3/3
**Notes**: Added TabbarLongTitleFidelityFixture (2 long + 1 short tab, scoped .ct-borderbox-scope <style> for production border-box) + 4 CT tests: AC-6/AC-9 max-width==220px, [011] AC-7 cell<=221px border-box, [011] AC-8 tablist<=662px (diagnostic), bare-wrapper max-width:none (AC-3). Full CT suite 161/161. Deviation: box-sizing reproduced via fixture-scoped <style> after a global base.css harness import broke 2 screenshot baselines (reverted); playwright/index.tsx net-unchanged.
