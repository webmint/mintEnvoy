# Task 002: create-divider

**Feature**: 003-app-shell-layout
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 001
**Blocks**: 003, 004
**Spec criteria**: AC-4, AC-9, AC-16
**Review checkpoint**: No
**Context docs**: docs/renderer/architecture.md

## Files

| File                                              | Action | Description                                        |
| ------------------------------------------------- | ------ | -------------------------------------------------- |
| src/renderer/src/components/organisms/Divider.tsx | Create | Hand-rolled pointer-event WAI-ARIA splitter        |
| src/renderer/src/components/organisms/Divider.css | Create | Divider styles (semantic classes, tokens.css vars) |

## Description

Create the reusable hand-rolled divider — a presentational, decoupled splitter the Sidebar (003) and PaneSplit (004) mount. It does NOT import the store: it takes `value`/`min`/`max`/`onCommit` props so the mounter wires it to the relevant store action. During drag it writes a CSS custom property (rAF-batched) for smooth resize with no per-pointermove React re-render; on pointer release it clamps to `[min, max]` and calls `onCommit(clamped)`. It exposes the WAI-ARIA window-splitter pattern. Hand-rolled per the established Tabs-molecule precedent (no library — keeps the settingsStore the single source of truth). Styling: semantic classes bound to tokens.css, no inline styles, animations behind `prefers-reduced-motion`.

## Change Details

- Create `src/renderer/src/components/organisms/Divider.tsx`:
  - Props: `{ orientation: 'vertical' | 'horizontal'; value: number; min: number; max: number; ariaLabel: string; cssVar: string; onCommit: (value: number) => void }`.
  - Pointer drag: `onPointerDown` captures the pointer (`setPointerCapture`) so release-outside-window still fires `pointerup`; `pointermove` computes the new value and writes `cssVar` on the target via `requestAnimationFrame` (no `setState` per move); `pointerup` clamps to `[min, max]` and calls `onCommit`.
  - Keyboard: `tabindex=0`; Arrow keys step the value (clamped) and call `onCommit`; Home/End jump to `min`/`max`.
  - ARIA: `role="separator"`, `aria-orientation`, `aria-valuenow={value}`, `aria-valuemin={min}`, `aria-valuemax={max}`, `aria-label`.
  - The Divider clamps to `[min, max]` INTERNALLY before every `onCommit` (keyboard + pointer paths both), so mounters do not re-clamp.
  - JSDoc on the component + props (AC-11).
- Create `src/renderer/src/components/organisms/Divider.css`: semantic classes (`.divider`, `.divider--vertical`, etc.) bound to tokens.css custom properties; `@media (prefers-reduced-motion: reduce)` gating.

## Contracts

### Expects (checked before execution)

- `SIDEBAR_MIN`/`SIDEBAR_MAX`/`PANE_MIN`/`PANE_MAX` and `clampSidebarWidth`/`clampPaneRatio` are exported from `settingsStore.ts` (task 001).
- `cx()` is available at `src/renderer/src/lib/cx.ts`.

### Produces (checked after execution)

- `Divider` is exported from `src/renderer/src/components/organisms/Divider.tsx`.
- The rendered element carries `role="separator"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`, and `tabindex={0}`.
- The component clamps to `[min, max]` internally before calling `onCommit` (pointer + keyboard paths).
- Drag writes a CSS custom property via `requestAnimationFrame`; no `useState` is set on `pointermove`.
- `Divider.css` uses semantic class names bound to tokens.css; no inline `style={{` attributes.

## Done When

- [x] `Divider` drags via pointer events with an rAF CSS-var write and commits a clamped value on release.
- [x] Arrow/Home/End keyboard resize works and commits clamped values; `role="separator"` + aria-valuenow/min/max present.
- [x] No inline styles; animations gated behind `prefers-reduced-motion`.
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-23T17:13:32Z
**Files changed**: src/renderer/src/components/organisms/Divider.tsx, src/renderer/src/components/organisms/Divider.css
**Contract**: Expects 2/2 | Produces 5/5
**Notes**: Repairs: drag+commit CSS-var write targets document.documentElement (shared with Shell/007, resolves shadowing); added onPointerCancel + rAF unmount cleanup; Home/End use min/max. qa edge cases recorded for task 011.
