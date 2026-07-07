---
concern: renderer
files: 39
last_indexed: 2026-06-22
package: .
source_stamp: b44087ca58806208
---

# renderer

## Purpose

React 19 renderer process — the user-facing UI. Houses the reusable UI-primitive library (Icon atom; Dropdown, Modal, Toast, Tabs, and Divider molecules — Dropdown/Modal/Toast wrap Radix UI, Tabs hand-rolls its WAI-ARIA engine and also supports opt-in closable, per-tab method-chip (HTTP-method color chip, `aria-hidden`), dirty-state affordances, and linkPanels (opt-in ARIA panel↔tab id linkage — off by default, byte-identical to the selection-only contract when absent; feature-015); Divider is a hand-rolled WAI-ARIA splitter), the single-window app shell (Shell, Titlebar, Statusbar, and PaneSplit — grouped under organisms/shell/ — plus Sidebar, TabBar, RequestBar, RequestSubTabs, and KVTable as flat organism singletons), the working-tabs strip organism (TabBar, composing Tabs and wired to tabsStore lifecycle actions), the request submission bar organism (RequestBar — method Dropdown + URL input + Send/Save/Share row, wired to the active tab's spec via tabsStore.updateActiveSpec and markClean), the per-request sub-tab switcher organism (RequestSubTabs — composes Tabs for a fixed 6-tab strip [Params/Auth/Headers/Body/Tests/Code], owns 6 always-mounted hidden-toggled tabpanels, derives read-only badges from the active spec, reads/writes per-tab activeSubTab via tabsStore; Params and Headers slot content arrives as slot props from App — no sibling-organism import), the controlled key-value grid organism (KVTable — mounted live into the Params and Headers slots of RequestSubTabs via the App composition root), three module-level zustand stores (toastStore for the toast queue; settingsStore as the SSOT for theme/accent/method-style/sidebarWidth/paneRatio/sidebarCollapsed; tabsStore as the working-tabs lifecycle state machine including the new `updateActiveSpec(patch)` action that shallow-merges spec edits with a no-op guard, plus `SubTabKey` union (the 6-slot sub-tab key: `'params'|'auth'|'headers'|'body'|'tests'|'code'`), additive `activeSubTab` field (default `'params'`) on the `Tab` record, and `setActiveSubTab(tabId, key)` action), the requestSpec domain model (RequestSpec — where `method` is typed as `HttpMethod` from httpMethods.ts, not a plain string — plus Row, Auth discriminated union, isBearerAuth type guard, makeBlankRequest factory), `httpMethods` (exported `METHODS` ordered tuple + `HttpMethod` union — the single source of truth for the HTTP method list, consumed by requestSpec, RequestBar, and Tabs), className-merge and safe icon-resolution helpers, design tokens as CSS variables, and a dev-only primitives gallery gated on import.meta.env.DEV. main.tsx mounts App into index.html; App now renders `<Shell>` with `tabs={<TabBar/>}` and a composed request pane — `<RequestBar/>` above `<RequestSubTabs params={<KVTable field='params'/>} headers={<KVTable field='headers'/>}/>` — inside ToastProvider. The layer carries no Node/Electron imports per the renderer-isolation rule.

## Structure

```text
src/renderer/
├── src
│   ├── __tests__
│   │   ├── app-toast-mount.test.tsx  # Test: App mounts toast provider + viewport
│   │   ├── setup.ts  # Vitest setup; jsdom + testing-library wiring
│   │   ├── smoke.ct.tsx  # Playwright CT smoke render
│   │   └── smoke.test.tsx  # Vitest smoke render test
│   ├── components
│   │   ├── __tests__
│   │   │   └── PrimitivesDemo.test.tsx  # Test: PrimitivesDemo renders all primitives
│   │   ├── atoms
│   │   │   ├── __tests__
│   │   │   │   ├── Icon.ct.tsx  # Playwright CT: Icon rendering
│   │   │   │   └── Icon.test.tsx  # Vitest: Icon a11y + variants
│   │   │   ├── Icon.css  # Icon atom styles incl. spin modifier
│   │   │   ├── Icon.tsx  # Inline SVG icon atom; aria-hidden unless labeled
│   │   │   └── icons.ts  # Project icon set; raw inner-SVG markup keyed by name
│   │   ├── molecules
│   │   │   ├── __tests__
│   │   │   │   ├── Divider.ct.tsx  # Playwright CT: Divider drag + keyboard resize
│   │   │   │   ├── Divider.stories.tsx  # Storybook: Divider fixture components for CT
│   │   │   │   ├── Divider.test.tsx  # Vitest: Divider isolation tests + a11y
│   │   │   │   ├── Dropdown.ct.tsx  # Playwright CT: Dropdown interaction
│   │   │   │   ├── Dropdown.stories.tsx  # Storybook stories for Dropdown
│   │   │   │   ├── Dropdown.test.tsx  # Vitest: Dropdown behavior + a11y
│   │   │   │   ├── Modal.ct.tsx  # Playwright CT: Modal focus trap
│   │   │   │   ├── Modal.stories.tsx  # Storybook stories for Modal
│   │   │   │   ├── Modal.test.tsx  # Vitest: Modal behavior + a11y
│   │   │   │   ├── Tabs.ct.tsx  # Playwright CT: Tabs keyboard/focus + axe a11y
│   │   │   │   ├── Tabs.stories.tsx  # Storybook stories for Tabs
│   │   │   │   ├── Tabs.test.tsx  # Vitest: Tabs behavior + a11y
│   │   │   │   ├── Toast.ct.tsx  # Playwright CT: Toast queue
│   │   │   │   ├── Toast.stories.tsx  # Storybook stories for Toast
│   │   │   │   ├── Toast.test.tsx  # Vitest: Toast queue behavior
│   │   │   │   ├── nested-overlays.ct.tsx  # Playwright CT: nested modal + dropdown
│   │   │   │   └── nested-overlays.stories.tsx  # Storybook: nested overlay scenarios
│   │   │   ├── Divider.css  # Divider handle styles; drag-cursor affordance
│   │   │   ├── Divider.tsx  # Hand-rolled WAI-ARIA splitter; rAF-batched CSS-var drag; store-free
│   │   │   ├── Dropdown.css  # Dropdown styles; reduced-motion-gated animation
│   │   │   ├── Dropdown.tsx  # Controlled dropdown menu over Radix DropdownMenu
│   │   │   ├── Modal.css  # Modal styles; overlay scrim + gated animation
│   │   │   ├── Modal.tsx  # Controlled modal dialog over Radix Dialog
│   │   │   ├── Tabs.css  # Tabs styles; token-bound BEM classes; reduced-motion guard; .tabbar-scoped override block (feature-005)
│   │   │   ├── Tabs.tsx  # Controlled tab-strip; hand-rolled WAI-ARIA tablist (no Radix); opt-in method-chip, dirty-state (feature-005), and linkPanels ARIA panel↔tab linkage (feature-015)
│   │   │   ├── Toast.css  # Toast queue styles per variant
│   │   │   └── Toast.tsx  # Toast queue UI; ToastProvider + ToastViewport
│   │   ├── organisms
│   │   │   ├── __tests__
│   │   │   │   ├── KVTable.ct.tsx  # Playwright CT: KVTable computed-style fidelity + keyboard + a11y
│   │   │   │   ├── KVTable.stories.tsx  # Storybook: KVTable fixture components for CT
│   │   │   │   ├── RequestBar.ct.tsx  # Playwright CT: RequestBar keyboard shortcuts + method-chip fidelity
│   │   │   │   ├── RequestBar.stories.tsx  # Storybook: RequestBar fixture components for CT
│   │   │   │   ├── RequestBar.test.tsx  # Vitest: RequestBar store bindings + Send/Save guards
│   │   │   │   ├── RequestSubTabs.ct.tsx  # Playwright CT: RequestSubTabs keyboard/focus-preserve/per-tab-state/per-theme fidelity/a11y
│   │   │   │   ├── RequestSubTabs.stories.tsx  # Storybook: RequestSubTabs fixture components for CT
│   │   │   │   ├── RequestSubTabs.test.tsx  # Vitest: RequestSubTabs badge derivation + defensive reads + store bindings
│   │   │   │   └── TabBar.test.tsx  # Vitest: TabBar render/select/close + tabsStore integration
│   │   │   ├── KVTable.css  # KVTable layout; cell focus ring; row hover; empty-state; token-bound
│   │   │   ├── KVTable.tsx  # Controlled key-value grid for editing a request's params/headers; self-subscribes to tabsStore via field prop
│   │   │   ├── RequestBar.css  # RequestBar layout; method-chip color classes; action-button states
│   │   │   ├── RequestBar.tsx  # Request submission bar; method Dropdown + URL input + Send/Save/Share; wired to tabsStore.updateActiveSpec/markClean
│   │   │   ├── RequestSubTabs.css  # .pane-tabs-scoped §6 fidelity override of the Tabs DOM + panel/empty-state layout
│   │   │   ├── RequestSubTabs.tsx  # Per-request sub-tab switcher; composes Tabs; owns 6 always-mounted hidden-toggled tabpanels; reads/writes activeSubTab via tabsStore
│   │   │   ├── shell
│   │   │   │   ├── __tests__
│   │   │   │   │   ├── Shell.ct.tsx  # Playwright CT: Shell + sub-organism interaction
│   │   │   │   │   ├── Shell.stories.tsx  # Playwright CT fixture components for Shell organisms
│   │   │   │   │   └── Shell.test.tsx  # Vitest: Shell + sub-organism contracts
│   │   │   │   ├── PaneSplit.css  # PaneSplit layout; flex driven by --pane-ratio CSS var
│   │   │   │   ├── PaneSplit.tsx  # Request/response split workspace; mounts horizontal Divider
│   │   │   │   ├── Shell.css  # Shell grid layout; CSS-var consumers --sidebar-width / --pane-ratio
│   │   │   │   ├── Shell.tsx  # Root app shell; composes organisms; owns store→<html> effects; mounts TabBar
│   │   │   │   ├── Statusbar.css  # Statusbar styles
│   │   │   │   ├── Statusbar.tsx  # Bottom statusbar strip
│   │   │   │   ├── Titlebar.css  # Titlebar styles; drag region for OS window move
│   │   │   │   └── Titlebar.tsx  # Top titlebar; sidebar-toggle button (forwarded toggleRef)
│   │   │   ├── Sidebar.css  # Sidebar layout; width from --sidebar-width CSS var
│   │   │   ├── Sidebar.tsx  # Collapsible sidebar; mounts vertical Divider; reads sidebarCollapsed
│   │   │   ├── TabBar.css  # TabBar strip styles
│   │   │   └── TabBar.tsx  # Working-tabs strip; composes closable Tabs; wired to tabsStore; renders + / spacer / overflow-chevron actions row
│   │   ├── PrimitivesDemo.css  # Styles for the dev-only primitives gallery
│   │   └── PrimitivesDemo.tsx  # Dev-only visual QA gallery for all UI primitives
│   ├── lib
│   │   ├── __tests__
│   │   │   ├── icons-glue.test.ts  # Vitest: icon resolver fallback path
│   │   │   ├── tabsStore.test.ts  # Vitest: tabsStore lifecycle actions + never-zero invariant + updateActiveSpec no-op guard
│   │   │   └── toastStore.test.ts  # Vitest: toast store actions
│   │   ├── cx.ts  # className merge util; drops falsy tokens
│   │   ├── httpMethods.ts  # METHODS ordered tuple + HttpMethod union type; method SSOT for requestSpec, RequestBar, and Tabs
│   │   ├── icons-glue.ts  # Safe icon-name resolver; never throws on unknown
│   │   ├── requestSpec.ts  # RequestSpec domain model; method typed as HttpMethod (not string); Row/Auth types; isBearerAuth guard; makeBlankRequest factory
│   │   ├── settingsStore.ts  # Module-level zustand store: theme/accent/mstyle/sidebarWidth/paneRatio/sidebarCollapsed
│   │   ├── tabsStore.ts  # Module-level zustand store: working-tabs lifecycle state machine (never-zero invariant); adds updateActiveSpec(patch) with no-op guard, SubTabKey union, activeSubTab field on Tab (default 'params'), and setActiveSubTab(tabId,key) action
│   │   └── toastStore.ts  # Module-level zustand store for the toast queue
│   ├── test-utils
│   │   └── simulateDrag.ts  # Pointer-event drag helper for jsdom tests (works around jsdom's PointerEvent ctor gap)
│   ├── App.tsx  # Root component; mounts Shell (tabs=TabBar, panes.request=RequestBar above RequestSubTabs with KVTable injected into Params/Headers slots) inside ToastProvider
│   ├── env.d.ts  # Vite/renderer ambient type declarations
│   └── main.tsx  # React entry; mounts App into #root under StrictMode
├── styles
│   └── tokens.css  # Design tokens (color, spacing) as CSS variables
└── index.html  # Renderer HTML shell; mount point for the React root
```
