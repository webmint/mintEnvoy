# Task 004: Extend Tabs primitive with opt-in closable/onClose

**Feature**: 004-working-tabs-state-machine
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: None
**Blocks**: 005, 006, 007, 010
**Spec criteria**: AC-11, AC-12, AC-22, AC-23, AC-28
**Review checkpoint**: Yes
**Context docs**: docs/architecture.md

## Files

| File                                           | Action | Description                                                                                                                                  |
| ---------------------------------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| src/renderer/src/components/molecules/Tabs.tsx | Modify | Opt-in `closable`/`onClose` props (default-off); sibling `tabIndex={-1}` ✕; Delete/Backspace close path; `useLayoutEffect` focus restoration |
| src/renderer/src/components/molecules/Tabs.css | Modify | Close-✕ styling + dirty-marker styling (token-bound)                                                                                         |

## Description

**HIGHEST-RISK TASK (Risk 1).** Extend the feature-002 Tabs primitive with an opt-in, default-off per-tab close affordance — without breaking the existing selection-only roving-tabindex a11y. `closable=false` (the default) must keep the 002 path **byte-identical**: no Delete/Backspace handler attached, no extra close DOM node, no additional roving tab stop (AC-11). Exactly one roving tab stop per tab regardless of `closable` (AC-12).

When `closable` is true: render the ✕ as a **sibling `<button tabIndex={-1}>`** to the `role="tab"` element (a pointer target, NOT an extra roving stop, NOT `role="tab"`), and add a Delete/Backspace close path on the focused tab. `onClose` is **signal-only** — it emits the tab id on ✕-click or Delete/Backspace and mutates no list; the store (task 002) owns the lifecycle. The primitive's only post-close job is roving-focus integrity on the next render (AC-23).

**MUST NOT (plan Risk-1 guardrails — do not violate):**

- MUST NOT add the ✕ button to `buttonRefs`.
- MUST NOT give the ✕ `role="tab"`.
- MUST NOT switch `handleKeyDown` to a DOM selector (keep the index-based engine).

## Change Details

- In `src/renderer/src/components/molecules/Tabs.tsx`:
  - Add two optional props to `TabsProps`: `closable?: boolean` (default-off — treat `undefined`/`false` identically) and `onClose?: (id: string) => void`. JSDoc both as a recorded contract extension (AC-28/AC-29).
  - When `closable` is true, render a sibling `<button type="button" tabIndex={-1}>` ✕ next to each tab's `role="tab"` button (inside the same tab wrapper but OUTSIDE the roving engine — it is never added to `buttonRefs` and never gets `role="tab"`). On ✕ click → `onClose?.(tab.id)`; stop propagation so the click does not also fire `onChange`.
  - Add a Delete/Backspace branch to `handleKeyDown` that fires `onClose?.(tab.id)` for the focused tab when `closable` is true — only attach/act when `closable` is true so the `closable=false` path adds no handler behavior (AC-11). Keep the existing Arrow/Home/End index-based logic unchanged.
  - Add `useLayoutEffect` (NOT `useEffect`) keyed `[activeId, tabs]` + a `lastFocusWasInListRef` set via `onFocus`-capture on the tablist and cleared on `onBlur` when `relatedTarget` leaves the list. Restore `buttonRefs.current.get(activeId)?.focus()` ONLY when the ref guard is true AND `document.activeElement !==` the active tab element (no mouse-user hijack; closes the focus-falls-to-`<body>` gap, AC-23). `tabIndex={0}` cannot dangle — `rovingTabStopIndex` re-derives from `(tabs, activeId)` every render.
  - Renderer-only, no inline styles, no electron/node import (existing constraints preserved).
- In `src/renderer/src/components/molecules/Tabs.css`:
  - Add token-bound styling for the close ✕ (sibling control) and a dirty-marker style. Gate any transition behind `@media (prefers-reduced-motion: reduce)`. No inline styles.

## Contracts

### Expects (checked before execution)

- The existing selection-only Tabs primitive (`TabsProps`, `TabDescriptor`, the hand-rolled roving-tabindex engine: `handleKeyDown`, `rovingTabStopIndex`, `buttonRefs`) is present in `Tabs.tsx` (feature 002).

### Produces (checked after execution)

- `TabsProps` declares optional `closable` and `onClose`.
- With `closable` true, a sibling `<button>` with `tabIndex={-1}` (not `role="tab"`, not in `buttonRefs`) renders per tab and `onClose` fires on its click and on Delete/Backspace on the focused tab (AC-22).
- With `closable` falsy, no Delete/Backspace close behavior, no extra close DOM node, and no extra roving tab stop (AC-11); exactly one `tabIndex={0}` tab stop regardless of `closable` (AC-12).
- A `useLayoutEffect` restores roving focus to a neighbor on close without leaving a dangling tabindex (AC-23).

## Done When

- [x] `closable`/`onClose` are optional and default-off; `closable=false` path is byte-identical to the 002 contract (AC-11)
- [x] ✕ is a sibling `tabIndex={-1}` button, never in `buttonRefs`, never `role="tab"`; exactly one roving stop per tab (AC-12, AC-22)
- [x] `onClose` is signal-only (emits id on click + Delete/Backspace), mutates no list (AC-22)
- [x] `useLayoutEffect` focus restoration moves focus to a neighbor on close with no dangling tabindex and no mouse-user hijack (AC-23)
- [x] none of the three MUST-NOT guardrails violated
- [x] `closable`/`onClose` carry JSDoc as a recorded contract extension (AC-28)
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-25T05:29:48Z
**Files changed**: src/renderer/src/components/molecules/Tabs.tsx, src/renderer/src/components/molecules/Tabs.css
**Contract**: Expects 1/1 | Produces 4/4
**Notes**: Opt-in closable/onClose (default-off). closable=false byte-identical (002 suite 40/40 green). 3 Risk-1 guardrails honored (x not in buttonRefs, not role=tab, index-based handleKeyDown). Sibling tabIndex=-1 x, Delete/Backspace path, useLayoutEffect focus restoration w/ lastFocusWasInListRef mouse-guard. Panel repair: replaced as-Node cast with instanceof guard, removed dead empty :has() CSS; qa scope gaps (onBlur internal-transfer, non-close guard) folded into task 005.
