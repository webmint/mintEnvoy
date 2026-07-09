---
generated_by: /generate-docs (Phase B — glossary)
last_indexed: 2026-07-09
total_terms: 45
---

# Project Glossary

Terms surfaced in `docs/` and cross-referenced against the CBM-indexed code graph. Code-anchored entries link to a canonical definition; prose-only entries have no code symbol but appear in narrative.

## BrowserWindow

The Electron window primitive the main process constructs (900x670, deferred show) to host the renderer.

- **Used in**: `architecture.md`, `glossary.md`, `main/index.md` (and 1 others)
- **Related**: Main, Electron

## Chromium

The browser engine underlying the Electron renderer.

- **Used in**: `architecture.md`, `glossary.md`
- **Related**: Electron, Renderer

## className

The space-separated CSS class string built by the cx() helper, which filters out falsy tokens.

- **Used in**: `architecture.md`, `glossary.md`
- **Related**: Renderer

## contextBridge

The Electron API the preload uses to expose a safe, typed object to the renderer under contextIsolation.

- **Used in**: `glossary.md`, `preload/index.md`
- **Related**: Preload, contextIsolation, electronAPI

## contextIsolation

The Electron security setting isolating renderer JS from Node/Electron internals; the preload bridge is the only sanctioned crossing.

- **Used in**: `architecture.md`, `glossary.md`, `main/index.md` (and 2 others)
- **Related**: Preload, contextBridge, IPC

## CT

Playwright component testing — *.ct.tsx specs rendering components in-browser with screenshot baselines.

- **Used in**: `architecture.md`, `glossary.md`
- **Related**: Playwright

## Divider

The ARIA splitter drag-handle molecule separating resizable panes; writes CSS vars during drag.

- **Used in**: `architecture.md`, `renderer/src/index.md`
- **Related**: PaneSplit, Sidebar, Shell

## Dropdown

The molecule wrapping Radix DropdownMenu for controlled dropdown menus.

- **Used in**: `architecture.md`, `glossary.md`, `overview.md` (and 1 others)
- **Related**: Radix, Modal

## Electron

The desktop runtime hosting mintEnvoy; splits the app into main, preload, and renderer processes.

- **Used in**: `architecture.md`, `glossary.md`, `main/index.md` (and 3 others)
- **Related**: Main, Preload, Renderer, BrowserWindow

## electronAPI

The @electron-toolkit helper object exposed to the renderer through the preload bridge.

- **Used in**: `architecture.md`, `preload/index.md`
- **Related**: Preload, contextBridge

## envVars

The stable seam returning the active environment's valid variable-name set (currently an empty set).

- **Used in**: `architecture.md`, `renderer/src/index.md`
- **Related**: varTokens

## HMR

Hot module replacement for the renderer during development, wired via electron-vite.

- **Used in**: `architecture.md`, `main/index.md`
- **Related**: Vite, Renderer

## httpMethods

The single-source readonly METHODS tuple and its derived HttpMethod union type.

- **Used in**: `architecture.md`, `renderer/src/index.md`
- **Related**: requestSpec, RequestBar

## Icon

The inline-SVG icon atom rendering a project-owned icon via currentColor.

- **Used in**: `architecture.md`, `glossary.md`, `overview.md` (and 1 others)
- **Related**: IconName, SVG

## IconName

The union type of valid project icon names, resolved safely through icons-glue.

- **Used in**: `architecture.md`, `glossary.md`
- **Related**: Icon

## IPC

Inter-process communication between the Electron main and renderer processes, mediated exclusively by the preload bridge.

- **Used in**: `architecture.md`, `glossary.md`, `overview.md`
- **Related**: Preload, contextBridge, Main

## KVTable

The organism editing key/value rows (params/headers) with {{variable}} token cells, bound to the active tab.

- **Used in**: `architecture.md`, `renderer/src/index.md`
- **Related**: varTokens, tabsStore, requestSpec

## Main

The Electron main process — owns BrowserWindow creation, app lifecycle, and native OS wiring.

- **Used in**: `architecture.md`, `glossary.md`, `overview.md`
- **Related**: Electron, BrowserWindow, Preload

## mintEnvoy

The desktop API client this project builds — an Electron + React 19 + TypeScript app for composing and sending HTTP requests.

- **Used in**: `architecture.md`, `glossary.md`, `overview.md`
- **Related**: Electron, Renderer

## Modal

The molecule wrapping Radix Dialog for controlled modal dialogs.

- **Used in**: `architecture.md`, `glossary.md`, `overview.md` (and 1 others)
- **Related**: Radix, Dropdown

## PaneSplit

The request/response vertical split organism driven by the --pane-ratio CSS variable.

- **Used in**: `architecture.md`, `renderer/src/index.md`
- **Related**: Shell, Divider

## Playwright

The component-test runner exercising components in a real browser.

- **Used in**: `architecture.md`, `glossary.md`
- **Related**: CT, Vitest

## Preload

The contextIsolation-safe bridge process exposing a typed IPC surface (electronAPI plus a project api) from main to the renderer.

- **Used in**: `architecture.md`, `overview.md`
- **Related**: contextIsolation, contextBridge, electronAPI, IPC

## PrimitivesDemo

The dev-only gallery rendering every UI primitive for visual QA.

- **Used in**: `glossary.md`, `overview.md`
- **Related**: Icon, Dropdown, Modal, Tabs, Toast

## Radix

The radix-ui primitive library providing accessible focus-trap, keyboard nav, and positioning for overlay molecules.

- **Used in**: `architecture.md`, `glossary.md`, `overview.md` (and 1 others)
- **Related**: Dropdown, Modal, Toast

## Renderer

The Electron renderer process — the entire React 19 UI plus its generated design tokens; runs node/electron-free.

- **Used in**: `architecture.md`, `glossary.md`, `overview.md`
- **Related**: Electron, Shell, tabsStore

## RequestBar

The organism rendering the request submission row (method, URL, Send/Save/Share) bound to the active tab's RequestSpec.

- **Used in**: `architecture.md`, `renderer/src/index.md`
- **Related**: requestSpec, tabsStore, RequestSubTabs

## requestSpec

The renderer-only, JSON-serializable HTTP request domain model (types, guards, and makeBlankRequest).

- **Used in**: `architecture.md`, `renderer/src/index.md`
- **Related**: tabsStore, RequestBar, httpMethods

## RequestSubTabs

The organism switching a request's six always-mounted sub-tabs (Params, Auth, Headers, Body, Tests, Code).

- **Used in**: `architecture.md`, `renderer/src/index.md`
- **Related**: Tabs, RequestBar

## settingsStore

The module-level zustand store for shell view state — the single source of truth for shell UI.

- **Used in**: `architecture.md`, `renderer/src/index.md`
- **Related**: Shell, tabsStore

## Shell

The root composition organism assembling Titlebar, Sidebar, panes, and Statusbar.

- **Used in**: `architecture.md`, `renderer/src/index.md`
- **Related**: Titlebar, Statusbar, PaneSplit, Sidebar

## Sidebar

The resizable left-sidebar organism consuming --sidebar-width and mounting a Divider.

- **Used in**: `architecture.md`, `renderer/src/index.md`
- **Related**: Shell, Divider

## Statusbar

The presentational bottom status footer of the shell (children slot).

- **Used in**: `architecture.md`, `renderer/src/index.md`
- **Related**: Shell

## SVG

The inline vector format for project icons (16x16, currentColor stroke).

- **Used in**: `architecture.md`, `glossary.md`
- **Related**: Icon

## TabBar

The working-tabs strip organism bound to tabsStore.

- **Used in**: `architecture.md`, `renderer/src/index.md`
- **Related**: tabsStore, Tabs

## Tabs

The hand-rolled controlled horizontal tab-strip molecule; selection-only.

- **Used in**: `architecture.md`, `renderer/src/index.md`
- **Related**: TabBar, RequestSubTabs

## tabsStore

The module-level zustand store driving the working-tabs lifecycle state machine (UUID-stamped tabs).

- **Used in**: `architecture.md`, `renderer/src/index.md`
- **Related**: TabBar, requestSpec, settingsStore

## Titlebar

The top-chrome organism: logo, workspace pill, sidebar toggle, palette trigger, env selector, account pill.

- **Used in**: `architecture.md`, `renderer/src/index.md`
- **Related**: Shell

## Toast

The notification molecule rendering the toast queue via Radix; subscribes to toastStore.

- **Used in**: `architecture.md`, `glossary.md`, `overview.md` (and 1 others)
- **Related**: toastStore, ToastProvider, ToastViewport, Radix

## ToastProvider

The single Radix provider mounted once at App root so any enqueue renders into one ToastViewport.

- **Used in**: `architecture.md`, `glossary.md`, `renderer/src/index.md`
- **Related**: Toast, ToastViewport, toastStore

## toastStore

The module-level zustand store owning the toast stack (enqueue, auto/manual dismiss, hover-pause).

- **Used in**: `architecture.md`, `renderer/src/index.md`
- **Related**: Toast, ToastProvider, tabsStore

## ToastViewport

The single Radix viewport where queued toasts render.

- **Used in**: `architecture.md`, `glossary.md`
- **Related**: Toast, ToastProvider

## varTokens

The display-only tokeniser splitting text into plain and {{variable}} segments; it never resolves values.

- **Used in**: `architecture.md`, `renderer/src/index.md`
- **Related**: KVTable, RequestBar, envVars

## Vite

The bundler (via electron-vite) that builds all three Electron processes.

- **Used in**: `glossary.md`, `overview.md`
- **Related**: Vitest, HMR

## Vitest

The unit-test runner for renderer logic and components.

- **Used in**: `architecture.md`, `glossary.md`, `overview.md`
- **Related**: Playwright, Vite
