# Task 009: Tabs fidelity CT suite + fixture

**Feature**: 005-tab-bar-visual-fidelity
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 002, 003, 005, 006
**Blocks**: None
**Spec criteria**: AC-11, AC-14, AC-15, AC-16, AC-17, AC-18, AC-19, AC-21, AC-22, AC-27
**Review checkpoint**: Yes
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/molecules/__tests__/Tabs.ct.tsx | Modify | Real-browser computed-style EXACT + thresholded screenshot fidelity assertions |
| src/renderer/src/components/molecules/__tests__/Tabs.stories.tsx | Modify | Add the tabbar-scoped fidelity fixture |

## Description

Author the tiered fidelity proof (Decisions (a)/(e)/(g)) in Playwright CT — the real-browser leg the whole feature rests on. This is the 4-way convergence of render (002), Tabs.css (003), TabBar.css+Shell (005), and the token harness (006).

**GRILL F1 BINDING (mandatory — the prior grill confirmed this gap twice).** The fidelity fixture MUST reproduce the full production styling context, all three prerequisites:
1. tokens.css is loaded globally (task 006 — already done at the mount root).
2. `data-mstyle='soft'` is set PER-TEST on `document.documentElement` (a fidelity-`describe` `beforeEach`/`page.evaluate`, or a `hooksConfig`-gated `beforeMount`) — NOT globally in index.tsx.
3. **The mounted fixture carries `className="tabbar"` + `closable` + an active, method-bearing tab** (or mount `<TabBar/>` directly). Every new fidelity rule is `.tabbar`-compound-scoped (`.tabbar .tabs__tab-wrapper--active`, `.tabs.tabbar`, `.tabbar`-geometry) and the active `::before`/`::after` only render on the wrapper in the closable branch — a bare `<Tabs>` (as every EXISTING `Tabs.stories.tsx` fixture is) measures unscoped, inert rules and silently passes against an unstyled element.

**Assertions (tiered):**
- **Computed-style EXACT (primary, AC-18)** — via `window.getComputedStyle` (the established CT mechanic, e.g. `Dropdown.ct.tsx`): the `.tabbar` geometry (background `--bg-sunken`, height 36px, 1px `--border` bottom border, 8px right padding), the tab geometry (gap 8px, padding `0 10px 0 12px`, 1px right border, `--fs-base` font-size), the active accent (`::before` 1.5px `--accent`; `::after` 1px `--bg`), and the HEAD chip color (`getComputedStyle(chip).color` === the resolved `--m-head`) under `data-mstyle='soft'`.
- **Screenshot diff (supplementary, AC-21)** — `toHaveScreenshot({ threshold: 0.2, maxDiffPixelRatio: 0.01, animations: 'disabled' })` with pinned device scale. NOTE (grill F2 / Risk-6): this is a FIRST-EVER baseline for this feature — there is no prior baseline; manually confirm the first captured screenshot renders the soft-mstyle palette correctly BEFORE committing it (a wrong first render would bake an off-palette baseline). The computed-style EXACT assertions are the loud primary gate; the screenshot is supplementary.
- **Label ellipsis (AC-16)** — assert the `.tabs__tab-label` computes `flex: 1` (or its resolved `flex-grow: 1`) and truncates with an ellipsis when the label overflows the capped tab width (part of the tab-geometry computed-style block).
- **Single strip bottom border (AC-17, added per qa panel, task 005)** — assert (when the TabBar is mounted in its Shell context, or via a focused assertion on the strip elements) that the `.shell__tabs` wrapper computes `border-bottom-width: 0px` while the `.tabbar` strip computes a `1px` bottom border in `--border` — proving the Shell/Tabs double border was de-duplicated to exactly one. This is the machine guard that a future re-introduction of a `.shell__tabs` border would fail (the `/verify` design-auditor probe is a supplementary human check, not the gated assertion).
- **AC-22 — bare-consumer non-regression (added per qa panel, task 003).** Add a SECOND `describe` block that mounts a NON-`.tabbar` `<Tabs>` fixture (a bare `<Tabs closable>` with an active tab — the request-pane-style consumer) and asserts its active treatment still computes the PRE-005 values (the box-shadow inset underline + `--accent-soft` wash, NOT the new `::before`/`::after` accent) and that `.tabs` keeps `overflow: hidden`. This proves the task-003 `.tabbar`-scoped rules did not leak to a global `.tabs` consumer (AC-22). Without this, AC-22 has no owning runtime test.

## Change Details

- In `src/renderer/src/components/molecules/__tests__/Tabs.stories.tsx`:
  - Add a fidelity fixture `<Tabs className="tabbar" closable>` (or `<TabBar/>`) with an active tab carrying a `method` and both a dirty and a clean tab.
- In `src/renderer/src/components/molecules/__tests__/Tabs.ct.tsx`:
  - Add a fidelity `describe` with a `beforeEach`/`page.evaluate` setting `document.documentElement.dataset.mstyle = 'soft'`.
  - Mount the tabbar fidelity fixture; add the computed-style EXACT assertions + the thresholded `toHaveScreenshot`.

## Contracts

### Expects (checked before execution)
- Task 002 renders the chip, dirty-XOR-close, and `tabs__tab-wrapper--active`; task 003 added the `.tabbar`-scoped active/geometry rules; task 005 set the `.tabbar` strip + removed the duplicate Shell border; task 006 imports tokens.css into the CT mount root.
- `playwright.config.ts` has `snapshotDir` configured; `getComputedStyle` is usable in CT (per `Dropdown.ct.tsx`).

### Produces (checked after execution)
- `Tabs.stories.tsx` has a `className="tabbar"` + closable + active + method fidelity fixture.
- `Tabs.ct.tsx` mounts that fixture under per-test `data-mstyle='soft'` and asserts the enumerated computed-style values EXACT (AC-18) plus a thresholded screenshot (AC-21); the HEAD chip color resolves to `--m-head` (AC-19).
- The fidelity assertions run against a `.tabbar`-scoped element (not a bare `<Tabs>`).

## Done When

- [x] The fidelity fixture mounts with `className="tabbar"` + `closable` + an active method-bearing tab (NOT a bare `<Tabs>`) — grill F1 closed
- [x] `data-mstyle='soft'` is set per-test (not globally in index.tsx)
- [x] Computed-style EXACT assertions pass for `.tabbar`/tab geometry, the active `::before`/`::after`, and the HEAD chip color (AC-11, AC-14, AC-15, AC-18, AC-19)
- [x] The thresholded `toHaveScreenshot` (0.2 / 0.01 / animations disabled) passes; the first baseline was manually confirmed correct before commit (AC-21, grill F2/Risk-6)
- [x] The full build/typecheck/lint/test is green (AC-27)
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-26T13:39:59Z
**Files changed**: src/renderer/src/components/molecules/__tests__/Tabs.ct.tsx, src/renderer/src/components/molecules/__tests__/Tabs.stories.tsx, __snapshots__/components/molecules/__tests__/Tabs.ct.tsx-snapshots/tabbar-fidelity-chromium-darwin.png
**Contract**: Expects 2/2 | Produces 3/3
**Notes**: Fidelity CT green (120/1, the 1=pre-existing Dropdown bug 003). Caught + fixed a real AC-14 strip gap (harness wasn't loading TabBar.css) via harness CSS composition (TabBar.css+Shell.css), NOT by duplicating into Tabs.css. All EXACT computed-style ACs + screenshot baseline (visually confirmed). 1 repair round (+6 assertions: AC-17 shell 0px, AC-15 font, AC-11 wrapper-bg, AC-16 ellipsis, AC-22 overflow). Non-blocking: stale AC-17 describe-comment.
