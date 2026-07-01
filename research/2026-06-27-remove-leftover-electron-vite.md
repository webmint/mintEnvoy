# Research: Remove leftover electron-vite ping/pong debug handler in main process

**Date**: 2026-06-27
**Topic**: Remove leftover electron-vite ping/pong debug handler in main process
**Mode**: Bug
**Verdict**: Root cause confirmed

## Summary

Bug 002 is a leftover electron-vite scaffold debug handler at src/main/index.ts:54 — ipcMain.on('ping', () => console.log('pong')) — registered inside the app.whenReady().then() block. A project-wide search confirms it is dead: zero ipcRenderer/send/invoke callers exist across src/preload and src/renderer, and it is the only ipcMain handler in the codebase. Root cause is confirmed: scaffold boilerplate never cleaned up after project init, violating the no-debug-artifacts (console.log) constitution rule. Recommended fix is to delete the handler and its // IPC test comment; the change is local to one file with no behavioral surface. No remaining uncertainty.

## Symptom

| Dimension       | Value                                                                                                                                                                                  |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Symptom         | Leftover electron-vite scaffold debug handler ipcMain.on('ping', () => console.log('pong')) at src/main/index.ts:54; constitution forbids leaving debug artifacts (console.log) behind |
| Affected area   | Electron main process IPC setup — src/main/index.ts, inside app.whenReady().then()                                                                                                     |
| Repro / Current | On app launch, app.whenReady() registers a no-op 'ping' IPC handler that logs 'pong' to the main-process console; dead scaffold with no renderer caller                                |
| Desired         | Handler fully removed: delete line 54 and its line 53 // IPC test comment; no replacement                                                                                              |
| Scope           | one place (evidence: src/main/index.ts:54)                                                                                                                                             |

## Codebase Findings (WHERE)

| Surface                                                     | File:line            | Relevance                                                                                                                                                                                                                                                            | Framing   |
| ----------------------------------------------------------- | -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| leftover ping/pong IPC debug handler                        | src/main/index.ts:54 | no-op scaffold handler ipcMain.on('ping', () => console.log('pong')); sole ipcMain handler in src/ (sweep confirmed); violates no-debug-artifacts constitution rule; deletion target                                                                                 | primary   |
| createWindow — nearest named symbol in file                 | src/main/index.ts:6  | createWindow is the only named Function in src/main/index.ts; invoked at line 56 inside the same app.whenReady().then() block beside the dead handler; no helper carries the 'ping' value, confirming the bug is local dead-code removal with no value-flow fix-path | primary   |
| renderer/preload 'ping' caller search (runner-up falsifier) | (none)               | runner-up falsifier (live IPC contract) NOT found project-wide: 0 ipcRenderer/send/invoke matches across src/preload + src/renderer; disproves the runner-up framing                                                                                                 | runner-up |

## Root Cause Hypothesis (WHY)

**Primary hypothesis**: Leftover electron-vite scaffold boilerplate (the standard 'IPC test' ping/pong sample) was never removed after project scaffolding; verified dead (0 callers project-wide), serves no purpose, and violates the no-debug-artifacts constitution rule

**Confidence**: Confirmed

### Structured root cause

| Field                | Value                                                                                                                                                                     |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| trigger              | electron-vite project scaffolding inserted the sample 'ping' IPC handler at project init                                                                                  |
| root_cause           | Scaffold/boilerplate cleanup was not performed during initial project setup, leaving dead debug code (console.log) that violates the no-debug-artifacts constitution rule |
| contributing_factors | 1. Handler lives inside an anonymous app.whenReady().then() callback, not a named symbol, so it is easy to overlook 2. No lint rule flags console.log in the main process |

## Runner-up framing

| Field                 | Value                                                                                                                          |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Frame                 | The 'ping' handler is a live IPC contract that a renderer/preload caller depends on; removing it would break an IPC round-trip |
| Falsifier             | A renderer or preload call to ipcRenderer.send('ping') or ipcRenderer.invoke('ping')                                           |
| Confidence vs primary | lower                                                                                                                          |

## Hypothesis Enumeration

| Hypothesis                                                                                                                                                                 | Falsifier (what would disprove it)                                                                                | Runtime probe needed? |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | --------------------- |
| Leftover electron-vite scaffold boilerplate: the standard 'IPC test' ping/pong sample handler was never removed after project scaffolding; it has no caller and no purpose | A renderer/preload caller or a test references the 'ping' channel                                                 | no                    |
| The handler is an intentional health-check/keepalive IPC consumed elsewhere in the app                                                                                     | No ipcRenderer.send('ping')/invoke('ping') caller exists anywhere in preload/renderer (already confirmed: 0 hits) | no                    |

## Approaches (HOW to change)

### Delete the dead handler

- **Description**: Remove line 54 (ipcMain.on('ping', ...)) and the line 53 // IPC test comment from src/main/index.ts. No replacement.
- **Addresses hypothesis**: A, B
- **Does NOT cover**: (none)
- **Pros**: Minimal one-statement diff; Removes constitution-violating console.log; No behavioral surface — handler is provably dead
- **Cons**: None of substance
- **Complexity**: Low

### Replace with a real IPC handler

- **Description**: Keep the registration site but swap the no-op ping/pong for an actual application IPC handler wired to a preload/renderer caller.
- **Addresses hypothesis**: A
- **Does NOT cover**: B
- **Pros**: Reuses the scaffold structure
- **Cons**: Out of scope for bug 002 — no current IPC need; Adds code the spec did not ask for; Still leaves the bug (dead pong log) unless the old body is removed
- **Complexity**: Med

**Recommended approach**: Delete the dead handler — Static search proves src/main/index.ts:54 is unreachable — zero ipcRenderer/send/invoke references exist across src/preload and src/renderer (the value is classified unclassified, with no payload-shape consumer). Deleting that one statement is the minimal change meeting the desired outcome while preserving unchanged_behavior; createWindow and the app.whenReady boot flow stay untouched. This is deletion of unreachable code, not new code, so no canonical-pattern reuse applies.

**Single-layer justification:**
The symptom is one unreachable statement in the main-process entry file with no callers, no value-flow consumers, and no cross-layer dependents (verified: 0 ipcRenderer references project-wide). The change is local to src/main/index.ts; no other layer is involved.

**Cites:**

- ping

**Proposed call shape:**

```
createWindow()
```

## Constitution Constraints

| Rule                                                      | Impact on this change                                                                                                                 |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Never commit debug artifacts (no console.log left behind) | Directly mandates removal — the ipcMain.on('ping', () => console.log('pong')) handler is exactly the debug artifact this rule forbids |
| Minimal changes                                           | Constrains the fix to deleting the single dead statement + its comment; forbids the replace-with-real-IPC expansion (approach 2)      |

## Complexity Assessment

| Dimension        | Rating | Notes                                                                   |
| ---------------- | ------ | ----------------------------------------------------------------------- |
| Codebase changes | Low    | Delete 2 lines (handler + // IPC test comment) in one file              |
| Risk             | Low    | Handler is dead (0 callers verified); removal has no behavioral surface |
| Verify cost      | Low    | grep confirms 'ping' gone; typecheck + build pass; app boots            |

## Value Semantics

| Value | Classification | Evidence                                                                                                                    | Stability |
| ----- | -------------- | --------------------------------------------------------------------------------------------------------------------------- | --------- |
| ping  | unclassified   | dead IPC channel — 0 ipcRenderer/invoke callers project-wide (src/preload + src/renderer); no payload-shape consumer exists | —         |

## Next step

Copy the block below into a new `/specify` session manually. No automation — user controls when (or if) `/specify` runs.

```
/specify "Leftover electron-vite scaffold debug handler ipcMain.on('ping', () => console.log('pong')) at src/main/index.ts:54; constitution forbids leaving debug artifacts (console.log) behind — Handler fully removed: delete line 54 and its line 53 // IPC test comment; no replacement"

Research reference: research/2026-06-27-remove-leftover-electron-vite.md
Key facts:
- Mode: Bug
- Symptom: Leftover electron-vite scaffold debug handler ipcMain.on('ping', () => console.log('pong')) at src/main/index.ts:54; constitution forbids leaving debug artifacts (console.log) behind
- Desired: Handler fully removed: delete line 54 and its line 53 // IPC test comment; no replacement
- Recommended approach: Delete the dead handler
- Hypothesis addressed: A, B
- Hypotheses NOT covered: (none)
- Open uncertainties: 0 (see research doc §Open Uncertainties)
```
