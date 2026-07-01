# Spec: remove-ping-handler

**Date**: 2026-06-27
**Status**: Complete
**Design source**: none
**Author**: Claude + User

## 1. Overview

Remove the leftover electron-vite scaffold debug handler from the Electron main process. The bug (bugs/002-leftover-ping-debug-artifact.md) is a dead no-op IPC handler — ipcMain.on('ping', () => console.log('pong')) — that violates the project's no-debug-artifacts rule. This spec deletes the handler, its // IPC test comment, and the now-unused ipcMain import.

## 2. Current State

src/main/index.ts:54 registers ipcMain.on('ping', () => console.log('pong')) inside the app.whenReady().then() block, preceded by a // IPC test comment at src/main/index.ts:53. ipcMain is imported on src/main/index.ts:1 (import { app, shell, BrowserWindow, ipcMain } from 'electron') and is used ONLY at line 54. Research (research/2026-06-27-remove-leftover-electron-vite.md) confirmed via CBM search_code that this is the sole ipcMain handler in src/ and that zero ipcRenderer/send/invoke callers exist across src/preload and src/renderer — the handler is provably dead. git log shows it dates from the initial scaffold commit (8ff7b01). docs/main/index.md documents the main-process responsibilities (lifecycle + window creation) and does not mention any ping handler. No test infrastructure exists for the main process (docs/architecture.md).

## 3. Desired Behavior

src/main/index.ts no longer registers the 'ping' IPC handler: the ipcMain.on('ping', ...) statement (line 54) and its preceding // IPC test comment (line 53) are deleted, and ipcMain is removed from the line 1 electron import so no unused import remains. The app boot flow is otherwise unchanged — createWindow, app.whenReady, the browser-window-created/activate/window-all-closed handlers, and BrowserWindow creation all behave exactly as before. No console output is produced for a 'ping' message because the handler no longer exists. typecheck, lint, and build all pass.

## 4. Affected Areas

| Area                        | Files             | Impact                                                                                                                                   |
| --------------------------- | ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Electron main process entry | src/main/index.ts | Delete the ipcMain.on('ping', ...) handler (line 54) + its // IPC test comment (line 53); remove ipcMain from the line 1 electron import |

## 5. Acceptance Criteria

Each AC must be testable and unambiguous. **Cover each category that applies. Mark non-applicable categories with "N/A — [reason]".**

### 5.1 Tooling / artifact presence and absence

- [x] **AC-1**: The mintenvoy main process shall not register a 'ping' IPC handler.
  > Verification: ! grep -qF "ipcMain.on('ping'" src/main/index.ts

### 5.2 Behavior preservation

- [x] **AC-2**: WHEN the application starts, the mintenvoy main process shall create the BrowserWindow and complete its ready-event lifecycle exactly as before the change.

### 5.3 Behavior change

- [x] **AC-3**: WHEN the main process initializes, the mintenvoy main process shall register no 'ping' IPC listener and emit no 'pong' log message.

### 5.4 CI / pipeline

N/A — No CI/pipeline changes — source-only dead-code removal in src/main/index.ts

### 5.5 Hooks / gates

N/A — No hooks or gates added or changed by this removal

### 5.6 Documentation

N/A — docs/main/index.md does not document the ping handler; no docs/ update is required after removal

### 5.7 Hygiene

- [x] **AC-4**: The main process entry file shall contain no console-log debug artifact.
  > Verification: ! grep -qF 'console.log' src/main/index.ts
- [x] **AC-5**: The mintenvoy codebase shall pass lint and type-check with no unused import remaining in the main process entry file.
  > Verification: npm run lint && npm run typecheck

## 6. Out of Scope

**Coverage rule (v3)**: For each Phase 1.5 finding, the finding either (a) becomes an AC in §5, (b) becomes a Constraint in §7, (c) is explicitly listed here as out of scope, OR (d) is in §9 Risks with documented mitigation. Unlanded finding = hard error — re-verify Phase 1.5 enumeration is complete before saving.

- NOT included: Replacing the dead handler with a real application IPC handler (research approach 2 — no current IPC need) — F-claude-2
- NOT included: Adding test infrastructure for the main process to cover this removal (none exists today) — F-architecture-2
- NOT included: Any docs/ changes — the ping handler is undocumented, so no documentation update is needed — F-index-3
- NOT included: Manually updating the bugs/002-leftover-ping-debug-artifact.md record lifecycle (Open to Fixed is a manual step outside this spec) — F-claude-3
- NOT included: Touching renderer or preload code, or any other ipcMain handler (none exist; ping is the sole undocumented dead scaffold) — F-index-1

## 7. Technical Constraints

- Must follow: Keep the change minimal: delete only the dead handler, its // IPC test comment, and the now-unused ipcMain import — do not modify unrelated main-process code
- Must not break: App boot and window-creation flow (createWindow, the app ready event, browser-window-created, activate, and window-all-closed handlers) must not regress

## 8. Open Questions

- **DP-existing_behavior-1** [no DP in category existing_behavior]: no relevant decision point for existing_behavior
- **DP-data_flow_state-1** [no DP in category data_flow_state]: no relevant decision point for data_flow_state
- **DP-edge_cases-1** [no DP in category edge_cases]: no relevant decision point for edge_cases
- **DP-ui_ux_details-1** [no DP in category ui_ux_details]: no relevant decision point for ui_ux_details
- **DP-breaking_changes-1** [no DP in category breaking_changes]: no relevant decision point for breaking_changes
- **DP-tooling_configuration-1** [no DP in category tooling_configuration]: no relevant decision point for tooling_configuration

## 9. Risks

| Risk                                                                                                             | Likelihood | Impact | Mitigation                                                                                                                                              |
| ---------------------------------------------------------------------------------------------------------------- | ---------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Deleting the handler accidentally removes a still-needed import or alters the whenReady block, breaking app boot | Low        | Low    | Remove only ipcMain from the line 1 import (other imports stay); typecheck + lint + build gate the change; smoke-launch confirms the window still opens |
