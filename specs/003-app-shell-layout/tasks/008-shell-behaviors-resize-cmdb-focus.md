# Task 008: shell-behaviors-resize-cmdb-focus

**Feature**: 003-app-shell-layout
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 007
**Blocks**: 009, 011
**Spec criteria**: AC-5, AC-17
**Review checkpoint**: Yes
**Context docs**: None

## Files

| File                                            | Action | Description                                                                  |
| ----------------------------------------------- | ------ | ---------------------------------------------------------------------------- |
| src/renderer/src/components/organisms/Shell.tsx | Modify | Add window-resize re-clamp + global Cmd-B handler + on-collapse focus-return |

## Description

Add the Shell's imperative behaviors on top of the structural surface from task 007. Three behaviors, each AC-bearing: (1) a `window` `resize` listener that re-clamps `sidebarWidth` and `paneRatio` to their valid ranges via store actions so no pane goes negative/overflows (AC-17); (2) a document-level `Cmd-B` keydown handler that `preventDefault()`s and calls `toggleSidebar()` so the shortcut fires regardless of focus (AC-5); (3) focus-return coordination — on the false→true transition of `sidebarCollapsed`, move focus to the Titlebar toggle via the `toggleRef` created in 007 (resolves grill F3, the cross-organism focus-return). All listeners are added/removed in `useEffect` cleanups.

## Change Details

- In `src/renderer/src/components/organisms/Shell.tsx`:
  - Add a `useEffect` registering a `window` `resize` listener: on resize, re-derive clamped values via `clampSidebarWidth(sidebarWidth)` / `clampPaneRatio(paneRatio)` and commit them via `setSidebarWidth` / `setPaneRatio` (store actions only — no direct mutation). Remove the listener on cleanup.
  - Add a `useEffect` registering a `document`-level `keydown` listener: when `(e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'b'`, call `e.preventDefault()` then `toggleSidebar()`. Remove on cleanup. (Global scope so the shortcut fires regardless of focused element.)
  - Add focus-return: track the previous `sidebarCollapsed`; on a false→true transition, call `toggleRef.current?.focus()` so focus moves to the Titlebar sidebar-toggle button when the sidebar (and its Divider) unmount.
  - Keep all three as render-only/imperative effects; the authoritative state stays in the store.

## Contracts

### Expects (checked before execution)

- `Shell` exists, exposes the typed slots + the store→`<html>` effect, and holds a `toggleRef` passed to `<Titlebar>` (task 007).
- `settingsStore` exposes `setSidebarWidth`, `setPaneRatio`, `toggleSidebar`, `clampSidebarWidth`, `clampPaneRatio` (task 001).
- `Titlebar` attaches `toggleRef` to its sidebar-toggle `<button>` (task 005).

### Produces (checked after execution)

- `Shell` registers a `window` `resize` listener that re-clamps `sidebarWidth`/`paneRatio` via store actions (with effect cleanup).
- `Shell` registers a `document`-level keydown handler that `preventDefault()`s and calls `toggleSidebar()` on Cmd/Ctrl-B (with effect cleanup).
- `Shell` moves focus to `toggleRef.current` on the `sidebarCollapsed` false→true transition.

## Done When

- [x] Resizing the window re-clamps sidebar width (200-520px) and pane ratio (0.15-0.85) via store actions; no pane goes negative/overflows.
- [x] Cmd-B (and Ctrl-B) toggles the sidebar regardless of focus and calls `preventDefault()`.
- [x] On collapse, focus moves to the Titlebar toggle button (no focus stranded on `<body>`).
- [x] Every added listener is removed in its effect cleanup.
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-23T19:52:19Z
**Files changed**: src/renderer/src/components/organisms/Shell.tsx
**Contract**: Expects 3/3 | Produces 3/3
**Notes**: 3 effects: window-resize re-clamp (via store actions, AC-17), document Cmd-B/Ctrl-B toggle+preventDefault (AC-5), focus-return on false->true collapse edge via toggleRef (grill F3). All listeners cleaned up. Tidied resize double-clamp. qa granularity -> task 011.
