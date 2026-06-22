# Task 006: build the Modal component over Radix Dialog

**Feature**: 001-ui-primitives
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 001
**Blocks**: 008, 009
**Spec criteria**: AC-6, AC-7, AC-3, AC-11, AC-18, AC-14, AC-15
**Review checkpoint**: No
**Context docs**: specs/001-ui-primitives/research.md

## Files

| File                                            | Action | Description                                                          |
| ----------------------------------------------- | ------ | -------------------------------------------------------------------- |
| src/renderer/src/components/molecules/Modal.tsx | Create | Modal wrapping Radix Dialog (focus trap, scrim, Escape, scroll lock) |
| (Modal stylesheet under molecules/)             | Create | Semantic-class styling bound to tokens.css custom properties         |

## Description

Build the Modal molecule wrapping Radix `Dialog`: focus trap while open, a scrim/overlay, Escape close, body scroll lock, and focus return to the trigger on close. Controlled via `open` + `onOpenChange` props (caller owns state). Radix supplies focus-trap/scrim/Escape/scroll-lock; this task wires them and styles via semantic classes bound to tokens.css (no inline styles; functional overlay styles such as full-viewport scrim are the consumer's responsibility per Radix). Import via `@renderer` alias (constitution §2.3 / AC-19); reduced-motion respected.

## Change Details

- In `src/renderer/src/components/molecules/Modal.tsx`:
  - Wrap `Dialog.Root`/`Dialog.Trigger`/`Dialog.Portal`/`Dialog.Overlay`/`Dialog.Content`/`Dialog.Close` (from the `radix-ui` Dialog namespace).
  - Props: `open`, `onOpenChange`, `children` (controlled; AC-11).
  - Ensure the overlay scrim covers the viewport and body scroll is locked while open (AC-6); Escape closes (AC-7, Radix default); focus returns to trigger on close (AC-3, Radix default — verify).
  - Semantic classes bound to tokens; no `style={{ }}` (AC-18); gate animation behind `prefers-reduced-motion` (AC-14).
  - Document exported component + props (AC-15).

## Contracts

### Expects (checked before execution)

- The `radix-ui` package and its `Dialog` namespace are installed (task 001).

### Produces (checked after execution)

- `Modal.tsx` exports a controlled `Modal` (`open` + `onOpenChange`) wrapping Radix Dialog.
- While open: focus is trapped, a scrim renders, body scroll is locked; Escape closes; focus returns to the trigger on close.
- No inline `style={{ }}`; styling via semantic classes bound to tokens.
- Exported component + props documented (AC-15).

## Done When

- [x] Interaction test: opening traps focus + renders scrim + locks scroll (AC-6); Escape closes (AC-7); focus returns to trigger on close (AC-3); `onOpenChange` fires on user-driven open/close (AC-11)
- [x] No `style={{` in the component source (AC-18)
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-21T20:56:29Z
**Files changed**: src/renderer/src/components/molecules/Modal.tsx, src/renderer/src/components/molecules/Modal.css, src/renderer/src/components/molecules/__tests__/Modal.test.tsx, src/renderer/src/components/molecules/__tests__/Modal.ct.tsx, src/renderer/src/components/molecules/__tests__/Modal.stories.tsx, src/renderer/src/main.tsx, src/renderer/styles/tokens.css
**Contract**: Expects 1/1 | Produces 4/4
**Notes**: Modal over Radix Dialog (controlled, focus-trap/scrim/scroll-lock/Escape/focus-return). title required (a11y). CROSS-CUTTING: tokens.css was never imported -> added to main.tsx so all token styling works; added --scrim token. 90 vitest + 12 CT (focus-trap cycle, scroll-lock release, click-outside, reduced-motion).
