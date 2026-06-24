# Task 001: create-settings-store

**Feature**: 003-app-shell-layout
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: None
**Blocks**: 002, 003, 004, 005, 007, 008
**Spec criteria**: AC-1, AC-6, AC-10, AC-11, AC-15
**Review checkpoint**: No
**Context docs**: None

## Files

| File                                  | Action | Description                                                       |
| ------------------------------------- | ------ | ----------------------------------------------------------------- |
| src/renderer/src/lib/settingsStore.ts | Create | zustand store + types + actions + clamp bounds/helpers + defaults |

## Description

Create the net-new in-memory zustand `settingsStore` — the single source of truth for the shell's view state. Mirror the existing `toastStore`'s shape: `create()`, a single module-level instance, typed state, per-field selector usage. NB toastStore exposes `clearAll()`, NOT `reset()`, and its tests wrap `getState().clearAll()` in a local `resetStore()` helper — settingsStore adds its OWN `reset()` action rather than mirroring a symbol toastStore lacks. State is mutated ONLY through actions. No Node/electron imports (renderer-only, in-memory; disk persistence is §6 out of scope).

Export the clamp bounds and pure clamp helpers here so the Divider (002) and the Shell window-resize listener (008) consume one canonical clamp definition.

## Change Details

- Create `src/renderer/src/lib/settingsStore.ts`:
  - `export type Theme = 'light' | 'dark'`; `export type Mstyle = 'soft' | 'chip' | 'outline' | 'dot' | 'bar'`; `export type Accent = string` (accent identifier; visually inert this task).
  - `export interface SettingsState` with fields `{ theme, accent, mstyle, sidebarWidth, paneRatio, sidebarCollapsed }` PLUS the actions.
  - Actions: `setTheme`, `setAccent`, `setMstyle`, `setSidebarWidth(px)` (clamps via `clampSidebarWidth`), `setPaneRatio(r)` (clamps via `clampPaneRatio`), `toggleSidebar()` (flips `sidebarCollapsed`; does NOT zero `sidebarWidth`), `reset()` (restores defaults).
  - Exported bounds: `export const SIDEBAR_MIN = 200`, `SIDEBAR_MAX = 520`, `PANE_MIN = 0.15`, `PANE_MAX = 0.85`.
  - Exported helpers: `export function clampSidebarWidth(px: number): number` (clamps to [SIDEBAR_MIN, SIDEBAR_MAX]); `export function clampPaneRatio(r: number): number` (clamps to [PANE_MIN, PANE_MAX]).
  - Defaults: `{ theme: 'light', accent: 'mint', mstyle: 'soft', sidebarWidth: 260, paneRatio: 0.5, sidebarCollapsed: false }`.
  - `export const settingsStore = create<SettingsState>((set) => ({ ...defaults, ...actions }))`.
  - JSDoc on the interface, each action, and the exported helpers (AC-11).

## Contracts

### Expects (checked before execution)

- `zustand` is a project dependency (used by `src/renderer/src/lib/toastStore.ts`).
- `src/renderer/src/lib/toastStore.ts` exists as the zustand-shape reference (`create()`, single module-level instance).

### Produces (checked after execution)

- `settingsStore` is exported from `src/renderer/src/lib/settingsStore.ts` via `create()`.
- `SettingsState` interface is exported with fields `theme`, `accent`, `mstyle`, `sidebarWidth`, `paneRatio`, `sidebarCollapsed`.
- Actions `setSidebarWidth`, `setPaneRatio`, `toggleSidebar`, `reset`, `setTheme`, `setAccent`, `setMstyle` are exported on the store.
- `SIDEBAR_MIN`, `SIDEBAR_MAX`, `PANE_MIN`, `PANE_MAX`, `clampSidebarWidth`, `clampPaneRatio` are exported.
- The module contains no `from 'electron'` or `from 'node:'` import.

## Done When

- [x] `settingsStore` + `SettingsState` + the clamp bounds/helpers are exported and typed (no `any`).
- [x] `toggleSidebar()` flips `sidebarCollapsed` without mutating `sidebarWidth`; `reset()` restores the documented defaults.
- [x] `clampSidebarWidth`/`clampPaneRatio` clamp to the exported bounds.
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-23T16:45:18Z
**Files changed**: src/renderer/src/lib/settingsStore.ts
**Contract**: Expects 2/2 | Produces 5/5
**Notes**: Added Number.isFinite guard to clamp helpers (qa/security repair) so task 008 resize cannot write NaN.
