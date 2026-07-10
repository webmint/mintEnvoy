# Task 005: Font-load fidelity CT and regenerate baselines

**Feature**: 016-load-design-fonts
**Agent**: qa-engineer
**Status**: Complete
**Depends on**: 002, 003
**Blocks**: None
**Spec criteria**: AC-4, AC-7, AC-11, AC-12
**Review checkpoint**: Yes
**Context docs**: specs/016-load-design-fonts/design-manifest.json

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/**/__tests__/ (font-load CT) | Create/Modify | Loaded-typeface assertion + baseline regen |

## Description

Prove the fonts actually load and render, and refresh the screenshot baselines the typeface change invalidates. This is a convergence checkpoint (depends on both the font-loading task and the sans-reorder task). The assertion checks the LOADED typeface at runtime — NOT a pixel-diff against `design/reference.html`, because `reference.html` on macOS renders San Francisco for sans (its `--font-sans` is also `-apple-system`-first), so a pixel-diff would assert the wrong glyphs.

## Change Details

- Add a Playwright CT (reusing the established fidelity-CT fixture pattern: import `tokens.css`, and now also `fonts.css`, so `@font-face` is loaded in the fixture) that asserts:
  - `document.fonts` reports Inter and JetBrains Mono loaded (e.g. `document.fonts.check("16px Inter")` / `check("16px 'JetBrains Mono'")` after `document.fonts.ready`).
  - `getComputedStyle(<sans element>).fontFamily` resolves with `Inter` first (the design-manifest container-floor pair `body` ↔ `app-root`); `getComputedStyle(<mono element>).fontFamily` resolves with `JetBrains Mono` first (the `.method` ↔ `request-bar-method` pair).
  - Add the `data-testid` values the manifest names (`app-root`, `request-bar-method`) to the built elements if they are not already present.
- Regenerate the affected CT screenshot baselines: because a real typeface now renders, delete the stale baseline PNGs for affected components then regenerate (do NOT rely on `--update-snapshots` alone — sub-tolerance color/typeface diffs leave stale baselines untouched).

## Contracts

### Expects (checked before execution)
- `fonts.css` loads Inter + JetBrains Mono (Task 002 Produces).
- `--font-sans` is reordered Inter-first and `base.css` body uses `var(--font-sans)` (Task 003 Produces).

### Produces (checked after execution)
- A CT test asserting `document.fonts` has Inter + JetBrains Mono loaded AND `getComputedStyle().fontFamily` resolves to Inter (sans) / JetBrains Mono (mono).
- The affected CT screenshot baselines are regenerated (stale PNGs deleted + re-created).

## Done When

- [x] A CT asserts Inter + JetBrains Mono are in `document.fonts` and computed `fontFamily` resolves to them for a sans and a mono element
- [x] The test does NOT pixel-diff against `design/reference.html` for the sans typeface
- [x] Affected CT screenshot baselines regenerated (stale PNGs removed then regenerated)
- [x] `npm run typecheck && npm run lint && npm run build` pass; the CT suite passes
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-09T18:59:15Z
**Files changed**: playwright/index.tsx, src/renderer/src/__tests__/font-load.ct.tsx, __snapshots__/components/molecules/__tests__/Tabs.ct.tsx-snapshots/tabbar-fidelity-chromium-darwin.png, __snapshots__/components/organisms/__tests__/RequestBar.ct.tsx-snapshots/request-bar-fidelity-chromium-darwin.png
**Contract**: Expects 2/2 | Produces 2/2
**Notes**: font-load.ct.tsx asserts document.fonts loaded Inter+JetBrains Mono (400/700) + computed fontFamily resolves to them (not pixel-diff vs reference, per D4). Passes. Harness (playwright/index.tsx) imports fonts.css for production parity; regenerated Tabs+RequestBar baselines (Dropdown byte-identical). CT: font-load 1, RequestBar 34, Tabs 102, Dropdown 19 pass. PRE-EXISTING out-of-scope defect: KVTable.stories.tsx @renderer/styles/tokens.css alias trap breaks full test:ct build (bug-010 area) — recommend /report-bug. Impl in main thread.
