---
concern: main
files: 1
last_indexed: 2026-06-22
package: .
source_stamp: 246d3c55692bd3e5
---


# main

## Purpose

Electron main-process entry point. Creates the application BrowserWindow with the preload bridge attached, drives app lifecycle (ready, activate, window-all-closed), and routes new-window requests to the system browser via shell.openExternal. Loads the Vite dev-server URL in development and the bundled HTML in production.

## Structure

```text
src/main/
└── index.ts
```
