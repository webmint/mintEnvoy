# Task 005: build the Toast component over Radix Toast

**Feature**: 001-ui-primitives
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 004, 001
**Blocks**: 008, 009
**Spec criteria**: AC-8, AC-9, AC-10, AC-18, AC-14, AC-15, AC-21
**Review checkpoint**: No
**Context docs**: specs/001-ui-primitives/research.md

## Files

| File                                            | Action | Description                                                  |
| ----------------------------------------------- | ------ | ------------------------------------------------------------ |
| src/renderer/src/components/molecules/Toast.tsx | Create | Renders Radix Toast.Root/Viewport from toastStore items      |
| (Toast stylesheet under molecules/)             | Create | Semantic-class styling bound to tokens.css custom properties |

## Description

Build the Toast molecule: subscribe to `toastStore` and render each queued item as a Radix `Toast.Root` inside a `Toast.Viewport`, exposing a `ToastViewport`/provider surface for App-root mounting (task 008). Radix supplies a11y + animation; the store owns the queue. Hover/focus pause wires to the store's `pauseTimer`/`resumeTimer`; manual dismiss calls `dismiss(id)`. Semantic-class styling bound to tokens.css; no inline styles; reduced-motion respected. Import via `@renderer` alias (no deep relative paths; constitution §2.3 / AC-19).

## Change Details

- In `src/renderer/src/components/molecules/Toast.tsx`:
  - Read `toasts` from `toastStore`; render each as `Toast.Root` with `Toast.Description` + `Toast.Close` (from the `radix-ui` Toast namespace).
  - Wire `onPause`/`onResume` (hover/focus) to `pauseTimer`/`resumeTimer`; `Toast.Close` → `dismiss(id)`.
  - Export the `ToastViewport` (and provider wrapper if needed) for App-root mount.
  - Semantic classes bound to tokens; gate animation behind `prefers-reduced-motion` (AC-14); no `style={{ }}` (AC-18).
  - Document exported component + props (AC-15).

## Contracts

### Expects (checked before execution)

- `toastStore`, `toast()`, and the store actions exist (task 004).
- The `radix-ui` package and its `Toast` namespace are installed (task 001).

### Produces (checked after execution)

- `Toast.tsx` exports a Toast view (e.g. `ToastViewport`) rendering Radix `Toast.Root` per `toastStore` item.
- Hover/focus pause is wired to `pauseTimer`/`resumeTimer`; close is wired to `dismiss`.
- No inline `style={{ }}`; styling via semantic classes bound to tokens.
- Exported component + props documented (AC-15).

## Done When

- [x] Interaction test: enqueueing via `toast()` renders a Radix toast; it auto-dismisses (AC-8); hovering pauses (AC-9); closing one leaves the rest (AC-10)
- [x] No `style={{` in the component source (AC-18)
- [x] `molecules/` directory now exists (AC-21)
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-21T19:27:23Z
**Files changed**: src/renderer/src/components/molecules/Toast.tsx, src/renderer/src/components/molecules/Toast.css, src/renderer/src/components/molecules/__tests__/Toast.test.tsx, src/renderer/src/components/molecules/__tests__/Toast.ct.tsx, src/renderer/src/components/molecules/__tests__/Toast.stories.tsx
**Contract**: Expects 2/2 | Produces 4/4
**Notes**: ToastProvider+ToastViewport over Radix Toast (duration=Infinity, store owns timing). message escaped JSX text (CWE-79 closed). hover/focus->pause, close->dismiss, variant->token colors. 72/72 vitest + 6/6 Playwright CT (AC-14 reduced-motion).
