# Plan: remove-ping-handler

**Date**: 2026-06-27
**Spec**: specs/007-remove-ping-handler/spec.md
**Status**: Approved

## Specialist Consultation

**Invocations**:

- Phase 0 alternatives: no — N/A (no 2+ alternatives compared; disposition is a single provably-dead-code deletion)
- Phase 1.3 architecture decisions: yes (mandatory)
- Specialists consulted (orchestrator-relayed on the architect's request, or directly): none — see table

**Architect-authored sections** (transcribed verbatim from architect return):

- Layer Map: row 1
- Key Design Decisions: rows 1-3
- Risk Assessment seeds: rows 1-2
- Constitution Compliance flags: none

| Specialist | Sub-question | Input summary | Verdict | Cites         |
| ---------- | ------------ | ------------- | ------- | ------------- |
| (none)     | —            | —             | —       | own-reasoning |

## Summary

Delete the leftover electron-vite scaffold debug IPC handler from the Electron main process. The change removes the `// IPC test` comment and the `ipcMain.on('ping', () => console.log('pong'))` line inside `app.whenReady().then()`, and drops the now-unused `ipcMain` token from the line-1 electron import. The handler is provably dead (research: zero ipcRenderer/send/invoke callers project-wide, sole ipcMain handler), so the change has no behavioral surface beyond removing the debug artifact.

## Technical Context

**Architecture**: Electron main process only (`src/main/index.ts`) — Node/Electron layer per constitution §2.1. Preload and renderer are untouched.
**Error Handling**: N/A — pure deletion of a no-op handler; no fallible operation added or removed.
**State Management**: N/A — no state involved.

## Constitution Compliance

- §4 Never Do — "Never commit debug artifacts (console.log)": compliant — this change discharges the rule by removing the only console.log in the main process.
- §6.1 Minimal Changes: compliant — deletes only the dead handler, its comment, and the unused import token; nothing else.
- §2.1 Process Boundaries: compliant — only main-process code changes; preload/renderer import boundaries untouched.

## Implementation Approach

### Layer Map

| Layer                         | What                                                                                                                                                          | Files (existing or new) |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| Main process (Electron, Node) | Delete the dead `ipcMain.on('ping', …)` handler + its `// IPC test` comment inside `app.whenReady().then()`; remove `ipcMain` from the line-1 electron import | src/main/index.ts       |

### Key Design Decisions

| Decision                        | Chosen Approach                                                                                           | Why                                                                                                                                                 | Alternatives Rejected                                                            |
| ------------------------------- | --------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| Disposition of the dead handler | Delete handler + comment + unused `ipcMain` import                                                        | Provably dead (research: 0 ipcRenderer/send/invoke callers, sole ipcMain handler); satisfies the constitution's "never commit debug artifacts" rule | Replace with a real IPC handler (§6 OOS); leave in place (violates hygiene rule) |
| Scope of import edit            | Remove only the `ipcMain` token; keep `app, shell, BrowserWindow` byte-identical                          | Minimal-change rule; removing the now-unused import is required to pass lint/typecheck (AC-5)                                                       | Rewrite/reorder the whole import line (unnecessary churn)                        |
| Rest of boot flow               | Leave createWindow / app.whenReady / browser-window-created / activate / window-all-closed byte-identical | Behavior-preservation constraint §7; AC-2 requires lifecycle unchanged                                                                              | Any incidental refactor of the whenReady block (out of scope)                    |

### File Impact

| File              | Action | What Changes                                                                                                                                                                                                                                 |
| ----------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| src/main/index.ts | Modify | Line 1: drop `ipcMain` from `import { app, shell, BrowserWindow, ipcMain } from 'electron'`. Inside `app.whenReady().then()`: delete the `// IPC test` comment and the `ipcMain.on('ping', () => console.log('pong'))` line. No other edits. |

### Documentation Impact

No documentation changes expected — internal implementation only. (docs/main/index.md documents lifecycle + window creation and never mentioned the ping handler; §6 marks docs changes out of scope.)

## Risk Assessment

| Risk                                                                                                                           | Likelihood | Impact | Mitigation                                                                                                                                       |
| ------------------------------------------------------------------------------------------------------------------------------ | ---------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| Edit regresses the main↔preload↔renderer process boundary                                                                      | Low        | Low    | Edit confined to src/main/; no preload/renderer files touched; typecheck + lint + build gate the change; lint catches any residual unused import |
| Accidentally removing a still-needed import (`app`/`shell`/`BrowserWindow`) or altering the whenReady block, breaking app boot | Low        | Low    | Delete only the `ipcMain` token + the two ping lines; typecheck + build + smoke-launch confirm the window still opens (mirrors spec §9 risk)     |

## Dependencies

None — no packages to install, services to configure, or environment variables. Pure source deletion.

## Supporting Documents

- Research: research/2026-06-27-remove-leftover-electron-vite.md (root-cause-confirmed; cited in spec §2 — no new research.md needed, zero signals detected at Phase 0)
