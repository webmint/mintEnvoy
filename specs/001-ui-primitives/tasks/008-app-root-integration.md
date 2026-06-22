# Task 008: mount overlay substrate at the App root

**Feature**: 001-ui-primitives
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 005, 006, 007
**Blocks**: None
**Spec criteria**: AC-12
**Review checkpoint**: Yes
**Context docs**: None

## Files

| File                     | Action | Description                                                            |
| ------------------------ | ------ | ---------------------------------------------------------------------- |
| src/renderer/src/App.tsx | Modify | Mount the single Radix Toast.Provider/Viewport + portal container once |

## Description

Wire the overlay substrate into the renderer root: mount a single Radix `Toast.Provider` + the `ToastViewport` (task 005) and establish the portal container so Modal/Dropdown portals mount to a stable node with sane z-order. Convergence task (depends on all three molecules) → review checkpoint. Confirm nested-overlay composition: a modal opening a dropdown, or a toast over a modal, composes so Escape closes only the topmost overlay and focus traps/return nest (AC-12 — largely Radix-provided; this task verifies it end to end).

## Change Details

- In `src/renderer/src/App.tsx`:
  - Wrap the app in a single `Toast.Provider` and render the `ToastViewport` from task 005 once.
  - Establish the portal mount container (default document body is fine if z-order holds) so Modal/Dropdown/Toast portals are not detached.
  - Add no business logic — integration only (presentation; no IPC).

## Contracts

### Expects (checked before execution)

- `Toast`/`ToastViewport` (task 005), `Modal` (task 006), and `Dropdown` (task 007) are exported and importable via `@renderer`.

### Produces (checked after execution)

- `App.tsx` mounts exactly one `Toast.Provider` + `ToastViewport`.
- A stable portal container exists for overlays; z-order/scrim renders correctly.
- Nested overlays compose: Escape closes only the topmost; focus trap/return nest.

## Done When

- [x] Interaction test: with a modal open that opens a dropdown, Escape closes only the topmost overlay; focus-trap/return nest correctly (AC-12)
- [x] Exactly one Toast.Provider/Viewport is mounted (no duplicate queues)
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-22T07:33:40Z
**Files changed**: src/renderer/src/App.tsx, src/renderer/src/__tests__/app-toast-mount.test.tsx, src/renderer/src/components/molecules/__tests__/nested-overlays.ct.tsx, src/renderer/src/components/molecules/__tests__/nested-overlays.stories.tsx
**Contract**: Expects 1/1 | Produces 3/3
**Notes**: App.tsx mounts exactly one ToastProvider+ToastViewport (boilerplate preserved; single-viewport test). AC-12 nested overlays compose (Escape topmost-only, focus nest, toast above scrim) via Radix DismissableLayer + CSS z-order. 110 vitest + 30 CT + build.
