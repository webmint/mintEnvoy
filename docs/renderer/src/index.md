---
concern: src
files: 89
last_indexed: 2026-07-09
package: .
parent_concern: renderer
source_stamp: 655524082efc56ac
---


# src

## Purpose

The React 19 renderer application, organized by atomic design: atoms (Icon), molecules (Divider, Dropdown, Modal, Tabs, Toast — Dropdown and Modal wrap Radix primitives), and organisms (RequestBar, RequestSubTabs, KVTable, TabBar, Sidebar, plus the app shell: Titlebar, Statusbar, PaneSplit, Shell). State lives in module-level zustand stores under lib/ (tabsStore, toastStore, settingsStore); lib/ also holds the renderer-only request domain model (requestSpec), pure utilities (cx, httpMethods), and the display-only {{variable}} tokeniser (varTokens) plus its envVars seam and icons-glue resolver. App.tsx composes the Shell and mounts the single ToastProvider; main.tsx is the React root. All modules are renderer-pure (no node/electron imports) and bind color and geometry to design tokens.

## Structure

```text
src/renderer/src/
├── __tests__
│   ├── App.test.tsx
│   ├── app-toast-mount.test.tsx
│   ├── setup.ts
│   ├── smoke.ct.tsx
│   └── smoke.test.tsx
├── components
│   ├── __tests__
│   │   └── PrimitivesDemo.test.tsx
│   ├── atoms
│   │   ├── __tests__
│   │   │   ├── Icon.ct.tsx
│   │   │   └── Icon.test.tsx
│   │   ├── Icon.css  # Icon atom styles (color via currentColor)
│   │   ├── Icon.tsx  # Inline SVG icon atom (currentColor, accessible)
│   │   └── icons.ts  # Project icon set — 16x16 currentColor paths
│   ├── molecules
│   │   ├── __tests__
│   │   │   ├── Divider.ct.tsx
│   │   │   ├── Divider.stories.tsx
│   │   │   ├── Divider.test.tsx
│   │   │   ├── Dropdown.ct.tsx
│   │   │   ├── Dropdown.stories.tsx
│   │   │   ├── Dropdown.test.tsx
│   │   │   ├── Modal.ct.tsx
│   │   │   ├── Modal.stories.tsx
│   │   │   ├── Modal.test.tsx
│   │   │   ├── Tabs.ct.tsx
│   │   │   ├── Tabs.stories.tsx
│   │   │   ├── Tabs.test.tsx
│   │   │   ├── Toast.ct.tsx
│   │   │   ├── Toast.stories.tsx
│   │   │   ├── Toast.test.tsx
│   │   │   ├── nested-overlays.ct.tsx
│   │   │   └── nested-overlays.stories.tsx
│   │   ├── Divider.css  # Divider styles bound to design tokens
│   │   ├── Divider.tsx  # ARIA splitter drag-handle for resizable panes
│   │   ├── Dropdown.css  # Dropdown styles from design tokens
│   │   ├── Dropdown.tsx  # Controlled dropdown wrapping Radix DropdownMenu
│   │   ├── Modal.css  # Modal styles from design tokens
│   │   ├── Modal.tsx  # Controlled modal wrapping Radix Dialog
│   │   ├── Tabs.css  # Tabs styles from design tokens
│   │   ├── Tabs.tsx  # Hand-rolled controlled horizontal tab-strip
│   │   ├── Toast.css  # Toast styles from design tokens
│   │   └── Toast.tsx  # Toast queue view (Radix, subscribes toastStore)
│   ├── organisms
│   │   ├── __tests__
│   │   │   ├── KVTable.ct.tsx
│   │   │   ├── KVTable.stories.tsx
│   │   │   ├── RequestBar.ct.tsx
│   │   │   ├── RequestBar.stories.tsx
│   │   │   ├── RequestBar.test.tsx
│   │   │   ├── RequestSubTabs.ct.tsx
│   │   │   ├── RequestSubTabs.stories.tsx
│   │   │   ├── RequestSubTabs.test.tsx
│   │   │   └── TabBar.test.tsx
│   │   ├── shell
│   │   │   ├── __tests__
│   │   │   │   ├── Shell.ct.tsx
│   │   │   │   ├── Shell.stories.tsx
│   │   │   │   └── Shell.test.tsx
│   │   │   ├── PaneSplit.css  # PaneSplit styles from design tokens
│   │   │   ├── PaneSplit.tsx  # Request/response vertical split via --pane-ratio
│   │   │   ├── Shell.css  # Shell layout styles from design tokens
│   │   │   ├── Shell.tsx  # Root shell: Titlebar + Sidebar + panes + Statusbar
│   │   │   ├── Statusbar.css  # Statusbar styles from design tokens
│   │   │   ├── Statusbar.tsx  # Bottom status footer (children slot)
│   │   │   ├── Titlebar.css  # Titlebar styles from design tokens
│   │   │   └── Titlebar.tsx  # Top chrome: logo, env selector, palette trigger
│   │   ├── KVTable.css  # KVTable styles from design tokens
│   │   ├── KVTable.tsx  # Key/value row table editor with var-token cells
│   │   ├── RequestBar.css  # RequestBar styles from design tokens
│   │   ├── RequestBar.tsx  # Request bar: method, URL, Send/Save/Share
│   │   ├── RequestSubTabs.css  # RequestSubTabs styles from design tokens
│   │   ├── RequestSubTabs.tsx  # Per-request 6-sub-tab switcher (always-mounted)
│   │   ├── Sidebar.css  # Sidebar styles from design tokens
│   │   ├── Sidebar.tsx  # Resizable left sidebar region with Divider
│   │   ├── TabBar.css  # TabBar styles from design tokens
│   │   └── TabBar.tsx  # Working-tabs strip bound to tabsStore
│   ├── .DS_Store
│   ├── PrimitivesDemo.css  # Dev gallery layout styles
│   └── PrimitivesDemo.tsx  # Dev-only visual QA gallery of all primitives
├── lib
│   ├── __tests__
│   │   ├── envVars.test.ts
│   │   ├── icons-glue.test.ts
│   │   ├── tabsStore.test.ts
│   │   ├── toastStore.test.ts
│   │   └── varTokens.test.ts
│   ├── cx.ts  # className merge util (filters falsy tokens)
│   ├── envVars.ts  # Active-env variable name set (T14 seam, empty stub)
│   ├── httpMethods.ts  # HTTP method tuple + derived HttpMethod type
│   ├── icons-glue.ts  # Safe icon-name resolver bridge over icons.ts
│   ├── requestSpec.ts  # Renderer-only HTTP request domain model + guards
│   ├── settingsStore.ts  # zustand store for shell view state
│   ├── tabsStore.ts  # zustand store: working-tabs lifecycle machine
│   ├── toastStore.ts  # zustand store: toast notification queue
│   └── varTokens.ts  # Display-only {{variable}} tokeniser (no resolve)
├── test-utils
│   └── simulateDrag.ts  # Test helper: synthesize pointer drag events
├── App.tsx  # Root component: composes Shell + ToastProvider
├── env.d.ts  # Ambient TS env/asset type declarations
└── main.tsx  # React root mount (renderer entry)
```
