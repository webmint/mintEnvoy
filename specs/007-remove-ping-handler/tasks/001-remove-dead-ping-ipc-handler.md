# Task 001: Remove dead ping IPC handler from main process

**Feature**: 007-remove-ping-handler
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: None
**Blocks**: None
**Spec criteria**: AC-1, AC-2, AC-3, AC-4, AC-5
**Review checkpoint**: No
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/main/index.ts | Modify | Remove the dead ping/pong IPC handler, its comment, and the now-unused ipcMain import token |

## Description

Delete the leftover electron-vite scaffold debug IPC handler from the Electron main process. The handler `ipcMain.on('ping', () => console.log('pong'))` is provably dead (research confirmed zero ipcRenderer/send/invoke callers across src/preload and src/renderer; it is the sole ipcMain handler in the codebase) and leaves a `console.log` debug artifact, which the constitution forbids. Remove it, its preceding `// IPC test` comment, and the `ipcMain` token from the line-1 electron import (it becomes unused once the handler is gone, so leaving it would fail lint/typecheck). Make no other change — the rest of the boot flow must stay byte-identical.

## Change Details

- In `src/main/index.ts`:
  - Line 1: change `import { app, shell, BrowserWindow, ipcMain } from 'electron'` to `import { app, shell, BrowserWindow } from 'electron'` (drop only the `ipcMain` token; keep `app`, `shell`, `BrowserWindow` byte-identical).
  - Inside the `app.whenReady().then(() => { ... })` block: delete the `// IPC test` comment line and the `ipcMain.on('ping', () => console.log('pong'))` line immediately below it.
  - Do NOT touch `createWindow`, the `app.whenReady` callback structure, `browser-window-created`, `activate`, or `window-all-closed` handlers — they stay byte-identical.

## Contracts

### Expects (checked before execution)
- `import { app, shell, BrowserWindow, ipcMain } from 'electron'` appears in `src/main/index.ts`
- `ipcMain.on('ping'` appears in `src/main/index.ts`
- `function createWindow` appears in `src/main/index.ts`

### Produces (checked after execution)
- `ipcMain` no longer appears anywhere in `src/main/index.ts`
- `console.log` no longer appears anywhere in `src/main/index.ts`
- `function createWindow` still appears in `src/main/index.ts` (unchanged)
- `app.whenReady().then` and `app.on('window-all-closed'` still appear in `src/main/index.ts` (unchanged)

## Done When

- [x] The `ipcMain.on('ping', ...)` handler and its `// IPC test` comment are removed from `src/main/index.ts`
- [x] `ipcMain` is removed from the line-1 electron import; the app boot flow (createWindow, app.whenReady, window-all-closed) is otherwise unchanged
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-27T15:38:45Z
**Files changed**: src/main/index.ts
**Contract**: Expects 3/3 | Produces 4/4
**Notes**: Dead ping/pong IPC handler + // IPC test comment removed; ipcMain dropped from line-1 electron import. Boot flow (createWindow, app.whenReady, window-all-closed) unchanged. typecheck+lint+build pass.
