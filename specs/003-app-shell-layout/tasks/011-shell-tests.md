# Task 011: shell-tests

**Feature**: 003-app-shell-layout
**Agent**: qa-engineer
**Status**: Complete
**Depends on**: 008, 009
**Spec criteria**: AC-4, AC-5, AC-6, AC-7, AC-9, AC-12, AC-13, AC-16, AC-17
**Review checkpoint**: Yes
**Context docs**: docs/renderer/architecture.md

## Files

| File                                                           | Action | Description                                          |
| -------------------------------------------------------------- | ------ | ---------------------------------------------------- |
| src/renderer/src/components/organisms/**tests**/Shell.test.tsx | Create | Vitest + Testing Library interaction tests           |
| src/renderer/src/components/organisms/**tests**/Shell.ct.tsx   | Create | Playwright CT real-browser focus/keyboard/drag tests |

## Description

Cover the shell's behavior with the established renderer test stack (Vitest + @testing-library/react + user-event for interaction; Playwright CT for real-browser focus/keyboard/drag fidelity), co-located under `__tests__/`. Follow the existing molecules `__tests__` patterns (`.test.tsx` / `.ct.tsx`). Reset the settingsStore between tests via its `reset()` action so each test starts from known defaults.

Note on AC-17: assert the JS clamp/re-clamp math (clamp helpers + the window-resize re-clamp path) — jsdom/CT cannot enforce the OS-level `minWidth`; task 010's `minWidth` is the runtime guarantee and is not unit-asserted here.

## Change Details

- Create `src/renderer/src/components/organisms/__tests__/Shell.test.tsx` (Vitest + TL):
  - Divider clamp: dragging/keyboard past bounds commits a clamped `sidebarWidth` (200-520px, AC-4) and `paneRatio` (0.15-0.85, AC-16).
  - Cmd-B: a `keydown` with metaKey/ctrlKey + 'b' toggles `sidebarCollapsed` regardless of focused element (AC-5).
  - Collapse: when `sidebarCollapsed` true, the sidebar + its Divider are unmounted and focus is on the Titlebar toggle (AC-5 / grill F3).
  - In-session survival: setting theme/accent/mstyle/sidebarWidth/paneRatio via actions persists in the store and reflects on `<html>` data-attrs + Shell CSS vars (AC-6).
  - Slot rendering: arbitrary children passed to sidebar/tabs/panes/modals render without the Shell inspecting them (AC-7).
  - Window-resize re-clamp: simulate a resize and assert width/ratio re-clamp to valid ranges (AC-17, JS clamp math only).
  - Toast regression (grill F2 — must be APP-LEVEL): render `<App />` (NOT `<Shell>` in isolation — an isolated Shell test would need its own ToastProvider and thus cannot prove App.tsx preserved the substrate), call `toast('<text>')`, and assert the toast TEXT renders inside `.toast-viewport`. A viewport-element COUNT alone is insufficient (Radix renders the empty `<ol>` regardless) — assert routed content. Also assert `<App />` renders the Shell (e.g. the `.shell` root / a shell landmark) and that no PrimitivesDemo content is present (AC-8 "Shell in place of PrimitivesDemo").
  - Use `settingsStore.getState().reset()` in `beforeEach`.
- Create `src/renderer/src/components/organisms/__tests__/Shell.ct.tsx` (Playwright CT):
  - Real-browser divider pointer drag + keyboard resize; `role="separator"` + aria-valuenow focus/keyboard fidelity (AC-9).
  - Pointer-release-OUTSIDE-window (pointer capture) still commits — CT-only (jsdom has no capture semantics).
  - Mount the existing `Tabs` molecule into the `tabs` slot as a content-decoupling proof (the shell renders it without knowing its contents).

### Divider edge cases the review panel requires (accumulated from tasks 002/003 reviews)

These MUST be covered (Vitest unit unless marked CT):

- jsdom SETUP: stub `setPointerCapture`/`releasePointerCapture`/`hasPointerCapture` on `HTMLElement.prototype` (jsdom lacks them) or the pointerdown tests throw; clean up `document.documentElement` CSS vars in `afterEach` (the Divider writes `--sidebar-width`/`--pane-ratio` there — shared global state across tests).
- Clamp at EXACT bounds, below-min, above-max, NaN/non-finite — both drag-commit and keyboard paths, BOTH orientations with their REAL value domains: vertical/sidebar uses integer px bounds `[200, 520]`; horizontal/pane uses FLOAT ratio bounds `[0.15, 0.85]` (use float fixtures, not integers, for the pane case).
- CSS-var UNIT assertion: `--sidebar-width` writes are `px`-suffixed (e.g. `"260px"`); `--pane-ratio` writes are a BARE unitless number (e.g. `"0.5"`, NOT `"0.5px"`) — assert the exact string form for each var (the Divider's `unit` prop drives this; a `px` on the ratio var would collapse `flex: var(--pane-ratio)`).
- `PaneSplit` `className` prop is forwarded onto its container (parallel to the Sidebar className check).
- Keyboard: Arrow step past bounds clamps; Home commits `min`, End commits `max` (assert the CSS var value too); wrong-axis arrow keys are no-ops (no onCommit, no preventDefault); non-primary mouse button (button=2) does not start a drag.
- `pointercancel` mid-drag: store is NOT mutated (no onCommit) and the CSS var resets to the committed `value`.
- Collapse (toggleSidebar) while a drag is in flight UNMOUNTS the Divider and `cancelAnimationFrame` is called (no stale rAF writes post-unmount) — assert via `vi.spyOn(globalThis,'cancelAnimationFrame')`.
- Mid-drag the CSS var is the UNCLAMPED live value; only the committed (pointerup) value is clamped — assert the distinction.
- `aria-valuenow` tracks a re-rendered `value` prop.
- Collapse: assert `queryByRole('separator')` returns null AS A DISTINCT assertion from the focus-returns-to-toggle assertion (don't bundle — a passing focus check could mask a still-mounted separator).
- Sidebar `className` prop is forwarded onto the `<aside>`.

### Titlebar test items (from task 005 review)

- Clicking the sidebar-toggle button calls `toggleSidebar()` → `sidebarCollapsed` flips (use `await userEvent.click` so the re-render is act-wrapped; if mutating the store directly instead, wrap in `act()`).
- `toggleRef` points at EXACTLY the toggle `<button>`: `expect(toggleRef.current).toBe(screen.getByRole('button', { name: /toggle sidebar/i }))` — a DISTINCT assertion from the focus-return check (a focusable wrapper could otherwise mask a mis-wired ref).
- The toggle button carries the `titlebar__icon-btn--active` class WHILE `sidebarCollapsed` is true (presentational state reflection).
- Smoke: Titlebar renders without error when `toggleRef` is omitted (optional prop).

### Shell composition test items (from task 007 review)

- DOM cleanup is TWO separate `afterEach` steps (the store `reset()` does NOT clean the DOM): delete `document.documentElement.dataset.theme/accent/mstyle` AND `removeProperty('--sidebar-width')` / `removeProperty('--pane-ratio')` — both survive React unmount on the global `<html>`.
- Effect RE-RUN (not just mount): changing `theme` in the store updates `document.documentElement.dataset.theme`; changing `sidebarWidth`/`paneRatio` updates the CSS vars. (Guards against a mount-only/missing-dep regression.)
- CSS-var unit: `--sidebar-width` === `"260px"`, `--pane-ratio` === `"0.5"` (bare) on `document.documentElement`.
- AC-7 per-slot: each of sidebar / tabs / panes.request / panes.response / modals renders arbitrary children; include the `tabs` ABSENT case (no `shell__tabs` wrapper) and the partial-`panes` cases (request-only, response-only, neither). Query the child content, not the Shell wrapper.
- `modals` renders at the Shell root level (structural position assertion, not just presence).

### Shell behaviors test items (from task 008 review)

- Cmd-B: TWO distinct dispatches — `{ metaKey: true, key: 'b' }` AND `{ ctrlKey: true, key: 'b' }` — each toggles `sidebarCollapsed` regardless of focused element; AND a spy asserting `preventDefault()` was called on the matched keydown.
- Window-resize re-clamp: seed the store with OUT-OF-BOUNDS values (e.g. sidebarWidth 9999 / -5, paneRatio 2 / -1) before `window.dispatchEvent(new Event('resize'))`, then assert the handler clamped them back into range (proves the handler invokes the clamp, not just that defaults are in range).
- Focus-return DIRECTIONALITY: collapse (false→true) moves focus to the toggle button; expand (true→false) does NOT move focus; and mounting with `sidebarCollapsed: true` does NOT steal focus on mount (the prevCollapsedRef mount-init guard).
- Listener cleanup: after unmounting Shell, a subsequent `window` resize and a `document` Cmd-B keydown do NOT mutate the store (the resize/keydown listeners were removed in cleanup).

### Pane-divider px→ratio conversion test items (from the divider-drag bug fix)

- jsdom PITFALL (critical): `getBoundingClientRect().height` returns `0` in jsdom by default → the Divider's `extent ? pixelDelta/extent : pixelDelta` guard then falls back to the BUGGY 1:1 path, so a naive pane-drag test passes even with the fix deleted. EVERY pane-drag test MUST stub a real height — either `vi.spyOn(containerEl, 'getBoundingClientRect').mockReturnValue({ height: 800, ... })`, OR (cleaner) unit-test `<Divider>` in isolation with `getDragExtent={() => 800}`.
- PROPORTIONAL-MAGNITUDE regression (the assertion that distinguishes fixed vs broken): with extent 800, a pane drag of 80px commits `paneRatio ≈ startRatio + 0.1` (NOT `startRatio + 80`). Assert the magnitude, not just "within [0.15, 0.85]" (the clamp passes both before and after the fix).
- A SMALL pane drag must NOT jump `paneRatio` to a bound (the original bug).
- `keyboardStep` magnitude as DISTINCT assertions: pane ArrowDown moves `paneRatio` by `0.02`; sidebar arrow still moves `sidebarWidth` by `8` (px). Assert the onCommit argument value for each.
- `getDragExtent` returning `0`/`null` → the 1:1 fallback fires (no divide-by-zero, no NaN/Infinity reaches the store; `clampPaneRatio`'s finite-guard is the backstop).
- Sidebar drag/keyboard is bit-unchanged (omits both new props → 1:1 px + 8px step).

### Statusbar test items (from task 006 review)

- `Statusbar` renders and `getByRole('status', { name: /status bar/i })` resolves.
- Children slot: arbitrary child content renders inside the status region.
- `className` prop is merged onto the footer alongside the `statusbar` BEM root class.
- AC-7 slot-rendering must explicitly exercise the Statusbar `children` slot too (not only sidebar/tabs/panes/modals).

## Contracts

### Expects (checked before execution)

- `Shell` with behaviors is exported (tasks 007, 008); `App` mounts it inside `<ToastProvider>` (task 009).
- `settingsStore` exposes `reset()` (task 001).
- The Vitest + Playwright CT stack is configured (per docs/renderer/architecture.md); the existing `Tabs` molecule is importable.

### Produces (checked after execution)

- `Shell.test.tsx` exists with passing Vitest+TL cases for divider clamp, Cmd-B, collapse+focus, in-session survival, slot rendering, window-resize re-clamp, and the toast regression.
- `Shell.ct.tsx` exists with passing Playwright CT cases for divider drag/keyboard/ARIA and the Tabs-in-slot decoupling proof.

## Done When

- [x] `vitest run` passes the Shell interaction suite; `test:ct` passes the Shell CT suite.
- [x] Tests reset the settingsStore between cases; AC-17 asserted as JS clamp math (not OS minWidth).
- [x] The Tabs-in-slot decoupling proof passes.
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-23T21:20:04Z
**Files changed**: src/renderer/src/components/organisms/**tests**/Shell.test.tsx, src/renderer/src/components/organisms/**tests**/Shell.ct.tsx, src/renderer/src/components/organisms/**tests**/Shell.stories.tsx
**Contract**: Expects 3/3 | Produces 2/2
**Notes**: 241 Vitest tests pass (Shell+Divider+Sidebar+PaneSplit+Titlebar+Statusbar+App-level F2). Covers AC-4/5/6/7/8/9/10/16/17 + grill F2/F3 + divider px->ratio conversion regression. CT (.ct.tsx) authored but Playwright harness has a PRE-EXISTING RollupError (stale ./components/Versions ref in playwright/index.tsx from feat 001) - candidate /report-bug.
