# Task 010: set-window-minwidth

**Feature**: 003-app-shell-layout
**Agent**: frontend-engineer

<!-- Reassigned from backend-engineer: this project has no backend stack and never generated a backend-engineer agent. src/main is the Electron main/Node process of a single TS app, owned here by the app builder (frontend-engineer). The original backend-engineer label was a generic-table misfit (no "Electron main process" row). -->

**Status**: Complete
**Depends on**: None
**Blocks**: None
**Spec criteria**: AC-17
**Review checkpoint**: No
**Context docs**: None

## Files

| File              | Action | Description                                                                           |
| ----------------- | ------ | ------------------------------------------------------------------------------------- |
| src/main/index.ts | Modify | Add BrowserWindow `minWidth` so the window can't shrink below the sidebar clamp floor |

## Description

Set a `minWidth` on the main BrowserWindow so the OS window cannot be dragged narrower than the static sidebar clamp floor. Today `src/main/index.ts` creates the window with `width: 900` and NO `minWidth`, so a window narrower than 200px would force the 200px-floored sidebar wider than the whole window (the overflow AC-17 forbids). `minWidth ≈ 720` (sidebar max 520 + a ~200px minimum pane area) makes the renderer's static 200-520px clamp + AC-17 no-overflow jointly satisfiable at runtime. Main-process window config is the main process's responsibility (constitution §2.1); this is the runtime guarantee complementing the renderer's JS clamp (task 008).

## Change Details

- Read `src/main/index.ts` first (constitution §6.2). Locate the `new BrowserWindow({ ... width: 900 ... })` options (around line 9-10).
- Add `minWidth: 720` to the BrowserWindow constructor options (alongside the existing `width`).
- Do not change other window options; renderer code is untouched.

## Contracts

### Expects (checked before execution)

- `src/main/index.ts` constructs a `BrowserWindow` with a `width` option and no `minWidth` today.

### Produces (checked after execution)

- The `BrowserWindow` options in `src/main/index.ts` include `minWidth: 720`.

## Done When

- [x] The main BrowserWindow is created with `minWidth: 720`.
- [x] No other window options changed; no renderer files touched.
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-23T20:39:40Z
**Files changed**: src/main/index.ts
**Contract**: Expects 1/1 | Produces 1/1
**Notes**: Added minWidth:720 to BrowserWindow (AC-17 OS floor). Reassigned backend-engineer->frontend-engineer (no backend stack; main process owned by app builder).
