---
concern: main
files: 1
last_indexed: 2026-07-09
package: .
source_stamp: 3367f88a950516ad
---


# main

## Purpose

Boots the Electron main process: constructs the 900x670 BrowserWindow (min-width 720, menu bar auto-hidden, deferred show until ready-to-show) wired to the contextIsolation-safe preload bridge, and routes window-open requests to the system browser via shell.openExternal. Owns app-lifecycle wiring (ready, window-all-closed, activate) and electron-vite HMR for the renderer.

## Structure

```text
src/main/
└── index.ts
```
