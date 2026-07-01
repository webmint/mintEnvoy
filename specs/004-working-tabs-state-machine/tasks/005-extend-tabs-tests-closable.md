# Task 005: Extend Tabs tests for closable extension

**Feature**: 004-working-tabs-state-machine
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 004
**Blocks**: None
**Spec criteria**: AC-11, AC-12, AC-22, AC-23
**Review checkpoint**: No
**Context docs**: None

## Files

| File                                                          | Action | Description                                                             |
| ------------------------------------------------------------- | ------ | ----------------------------------------------------------------------- |
| src/renderer/src/components/molecules/**tests**/Tabs.test.tsx | Modify | `closable=true` behavior + `closable=false` byte-identical regression   |
| src/renderer/src/components/molecules/**tests**/Tabs.ct.tsx   | Modify | CT: Delete/Backspace close + roving-focus restoration + structural a11y |

## Description

Extend the existing Tabs test files (do NOT rewrite the 002 suites — add cases) to gate the closable extension from task 004. Follow the established split: jsdom interaction/contract assertions in `Tabs.test.tsx`, real-browser focus/keyboard behavior in `Tabs.ct.tsx`.

**a11y is verified via structural DOM assertions, NOT axe-core.** axe-core is not a project dependency, and the existing `Tabs.ct.tsx` already establishes structural assertions (role/tabIndex/aria-selected checks) as the project a11y-test pattern. Do NOT add axe-core. The structural checks for AC-22/AC-12 are: the ✕ is a sibling to `role="tab"` with `tabIndex=-1` (not itself `role="tab"`), and exactly one tab has `tabIndex=0` regardless of `closable`.

## Change Details

- In `src/renderer/src/components/molecules/__tests__/Tabs.test.tsx`:
  - `closable=false` byte-identical regression — with the default, no close DOM node renders, no Delete/Backspace handler closes, and there is no extra roving tab stop (AC-11). Assert exactly one `tabIndex=0` (AC-12).
  - `closable=true` behavior — a sibling close control renders per tab with `tabIndex=-1` and is NOT `role="tab"`; clicking it fires `onClose` once with that tab's id and does NOT fire `onChange` (AC-22). Still exactly one roving tab stop (AC-12).
- In `src/renderer/src/components/molecules/__tests__/Tabs.ct.tsx`:
  - Delete/Backspace on the focused tab fires `onClose` with the focused tab's id (real browser keyboard, AC-22).
  - Roving-focus restoration — after the active tab is removed (re-render with a shorter `tabs` + new `activeId`), DOM focus lands on a neighbor tab, not `<body>`, with no dangling `tabIndex` (AC-23).
  - **onBlur internal-transfer guard** — clicking a tab's ✕ (focus moves from the `role=tab` button to its sibling ✕, both inside the tablist) must NOT clear the keyboard-restore guard; verify that after a mixed sequence (focus a tab → keyboard-close it) focus restoration to the neighbor still fires. Guards the `relatedTarget`-`contains` check in `onBlur` (a regression dropping it would silently break keyboard focus restoration).
  - **useLayoutEffect non-close guard** — re-render with a CHANGED `tabs` array but the SAME `activeId` while focus is inside the list (e.g. a tab added/relabeled, not closed) must NOT steal focus (the `document.activeElement === activeEl` guard holds). Guards against spurious focus theft on non-close re-renders.
  - Structural a11y assertions for the closable strip (✕ sibling tabIndex=-1, single roving stop) — NO axe-core.

## Contracts

### Expects (checked before execution)

- The closable/onClose Tabs contract from task 004 is present (`TabsProps.closable`, `TabsProps.onClose`, sibling ✕, Delete/Backspace path, `useLayoutEffect` focus restoration).
- The existing `Tabs.test.tsx` and `Tabs.ct.tsx` 002 suites are present and passing.

### Produces (checked after execution)

- `Tabs.test.tsx` contains a `closable=false` byte-identical regression and `closable=true` behavior cases.
- `Tabs.ct.tsx` contains Delete/Backspace close, roving-focus-restoration, and structural-a11y cases.
- The Tabs Vitest + CT suites pass.

## Done When

- [x] `closable=false` byte-identical regression asserts no close node / no Delete handler / no extra roving stop (AC-11)
- [x] `closable=true` asserts sibling ✕ `tabIndex=-1` not `role=tab`, onClose-on-click without onChange, single roving stop (AC-12, AC-22)
- [x] CT covers Delete/Backspace close (AC-22) and roving-focus restoration to a neighbor with no dangling tabindex (AC-23)
- [x] CT covers the onBlur internal-transfer guard (✕-click focus transfer does not break subsequent keyboard-close focus restoration)
- [x] CT/unit covers the non-close guard (tabs changes but activeId unchanged while focus in list → no focus theft)
- [x] a11y assertions are structural DOM checks — NO axe-core introduced
- [x] existing 002 Tabs cases remain green (no rewrite)
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-25T05:56:08Z
**Files changed**: src/renderer/src/components/molecules/**tests**/Tabs.test.tsx, src/renderer/src/components/molecules/**tests**/Tabs.ct.tsx, src/renderer/src/components/molecules/**tests**/Tabs.stories.tsx
**Contract**: Expects 2/2 | Produces 3/3
**Notes**: jsdom 52/52 + Tabs CT 32/32. AC-11 byte-identical regression, AC-12 single roving stop, AC-22 x-click/Delete/Backspace onClose (real browser), AC-23 focus restoration + onBlur internal-transfer guard (two-phase) + non-close guard. Panel repair: rewrote non-close-guard test to exercise the focus-INSIDE document.activeElement===activeEl branch (was wrongly focus-outside) as a CT test + new fixture; strengthened onBlur to two-phase; added disabled-tab aria-label + sibling-DOM-position assertions. Added Tabs.stories.tsx CT fixtures. 2 pre-existing unrelated Dropdown CT failures out of scope.
