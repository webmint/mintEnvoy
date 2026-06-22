# Task 007: build the Dropdown/popover component over Radix

**Feature**: 001-ui-primitives
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 001
**Blocks**: 008, 009
**Spec criteria**: AC-2, AC-3, AC-4, AC-5, AC-11, AC-18, AC-14, AC-15
**Review checkpoint**: No
**Context docs**: specs/001-ui-primitives/research.md

## Files

| File                                               | Action | Description                                                  |
| -------------------------------------------------- | ------ | ------------------------------------------------------------ |
| src/renderer/src/components/molecules/Dropdown.tsx | Create | Dropdown/popover wrapping Radix DropdownMenu/Popover         |
| (Dropdown stylesheet under molecules/)             | Create | Semantic-class styling bound to tokens.css custom properties |

## Description

Build the Dropdown/popover molecule wrapping Radix `DropdownMenu` (and/or `Popover`): anchored to a trigger, keyboard navigation between items (Arrow/Home/End), focus return to the trigger on close, click-outside + Escape dismiss, and edge-aware flip/shift positioning to stay within the viewport. Controlled via `open` + `onOpenChange`. Radix supplies the behavior; this task wires + styles via semantic classes bound to tokens.css (no inline styles). Import via `@renderer` alias (constitution §2.3 / AC-19); reduced-motion respected.

## Change Details

- In `src/renderer/src/components/molecules/Dropdown.tsx`:
  - Wrap `DropdownMenu.Root`/`Trigger`/`Portal`/`Content`/`Item` (from the `radix-ui` DropdownMenu namespace); use Radix `Content` side/align + `collisionPadding` for edge-aware flip/shift (AC-5).
  - Props: `open`, `onOpenChange`, trigger, items/children (controlled; AC-11).
  - Keyboard nav (Arrow/Home/End) + typeahead are Radix defaults (AC-2); click-outside + Escape dismiss (AC-4); focus returns to trigger on close (AC-3).
  - Semantic classes bound to tokens; no `style={{ }}` (AC-18); gate animation behind `prefers-reduced-motion` (AC-14).
  - Document exported component + props (AC-15).

## Contracts

### Expects (checked before execution)

- The `radix-ui` package and its `DropdownMenu`/`Popover` namespace are installed (task 001).

### Produces (checked after execution)

- `Dropdown.tsx` exports a controlled `Dropdown` (`open` + `onOpenChange`) wrapping Radix DropdownMenu/Popover.
- Open menu supports Arrow/Home/End focus movement; click-outside + Escape dismiss; focus returns to the trigger on close; content flips/shifts to stay in the viewport.
- No inline `style={{ }}`; styling via semantic classes bound to tokens.
- Exported component + props documented (AC-15).

## Done When

- [x] Interaction test: Arrow/Home/End move focus between items (AC-2); click-outside + Escape dismiss (AC-4); focus returns to trigger on close (AC-3); `onOpenChange` fires (AC-11)
- [x] Edge-aware flip/shift verified (collision handling keeps content in-viewport) (AC-5)
- [x] No `style={{` in the component source (AC-18)
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-22T01:04:44Z
**Files changed**: src/renderer/src/components/molecules/Dropdown.tsx, src/renderer/src/components/molecules/Dropdown.css, src/renderer/src/components/molecules/__tests__/Dropdown.test.tsx, src/renderer/src/components/molecules/__tests__/Dropdown.ct.tsx, src/renderer/src/components/molecules/__tests__/Dropdown.stories.tsx
**Contract**: Expects 1/1 | Produces 4/4
**Notes**: Dropdown over Radix DropdownMenu; edge-aware; keyboard nav+activation; dismiss+focus-return; escaped labels. 19 vitest + 26 CT.
