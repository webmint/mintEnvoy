# Task 009: wire-shell-into-app

**Feature**: 003-app-shell-layout
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 008
**Blocks**: 011
**Spec criteria**: AC-8
**Review checkpoint**: Yes
**Context docs**: docs/renderer/architecture.md

## Files

| File                     | Action | Description                                                                         |
| ------------------------ | ------ | ----------------------------------------------------------------------------------- |
| src/renderer/src/App.tsx | Modify | Mount `<Shell>` inside the existing `<ToastProvider>`, preserving `<ToastViewport>` |

## Description

Wire the Shell in as the App's mounted content. CRITICAL (grill F2): the real App.tsx root is `<ToastProvider>` wrapping the dev-only PrimitivesDemo block AND a mandatory `<ToastViewport />` that every `toast()` portals into. Mount `<Shell>` INSIDE the existing `<ToastProvider>`, keeping `<ToastViewport />` — replace ONLY the dev-only PrimitivesDemo child with `<Shell>`. Do NOT delete the provider/viewport substrate (Radix Toast has no throwing guard — dropping it silently breaks every `toast()`). PrimitivesDemo stays in the repo, dev-gated behind `import.meta.env.DEV`, but unmounted.

## Change Details

- Read `src/renderer/src/App.tsx` first (constitution §6.2). Confirm the current structure: `<ToastProvider>` → (dev-gated `<PrimitivesDemo>`) + `<ToastViewport />`.
- In `src/renderer/src/App.tsx`:
  - Import `Shell` from `@renderer/components/organisms/Shell`.
  - Render `<Shell />` as the content child INSIDE the existing `<ToastProvider>`, in place of the PrimitivesDemo block.
  - Keep `<ToastViewport />` mounted as a sibling under `<ToastProvider>`.
  - Keep the `PrimitivesDemo` import dev-gated (`import.meta.env.DEV`) but no longer mounted at the root (preserve the lazy/dev-gate pattern so production still tree-shakes it).
  - Use the `@renderer` alias, not deep relative paths (constitution §2.3).

## Contracts

### Expects (checked before execution)

- `Shell` is exported from `src/renderer/src/components/organisms/Shell.tsx` with its behaviors (tasks 007, 008).
- `App.tsx` currently mounts `<ToastProvider>` + `<ToastViewport />` (existing code).

### Produces (checked after execution)

- `App.tsx` renders `<Shell />` as a child of `<ToastProvider>`.
- `<ToastViewport />` remains mounted under `<ToastProvider>` (the substrate is preserved).
- The `PrimitivesDemo` reference remains dev-gated behind `import.meta.env.DEV` and is not mounted at the root.
- `App.tsx` imports `Shell` via the `@renderer` alias.

## Done When

- [x] App renders `<Shell />` inside the preserved `<ToastProvider>`/`<ToastViewport />`.
- [x] A `toast()` call still renders with the Shell mounted (substrate intact).
- [x] PrimitivesDemo stays dev-gated and unmounted; production build still tree-shakes it.
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-23T20:08:01Z
**Files changed**: src/renderer/src/App.tsx
**Contract**: Expects 2/2 | Produces 4/4
**Notes**: Shell mounted inside preserved ToastProvider; ToastViewport kept (grill F2); PrimitivesDemo removed from App (file retained), lint-clean. F2 test sharpened to App-level in task 011.
