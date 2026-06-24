---
concern: preload
files: 2
last_indexed: 2026-06-22
package: .
source_stamp: 1e135b48fa921023
---

# preload

## Purpose

contextIsolation-safe preload bridge between the Electron main process and the renderer. Exposes the @electron-toolkit electronAPI plus a project api object on the window via contextBridge when context isolation is enabled, falling back to direct DOM-global assignment when it is not. The companion .d.ts augments the Window type so the renderer sees the exposed globals.

## Structure

```text
src/preload/
├── index.d.ts  # Ambient Window augmentation for electron + api globals
└── index.ts
```
