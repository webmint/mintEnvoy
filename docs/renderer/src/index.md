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

The React 19 renderer application, organized by atomic design: atoms (Icon, EmptyPanel), molecules (Divider, Dropdown, Modal, Tabs, Toast — Dropdown and Modal wrap Radix primitives), and organisms (RequestBar, RequestSubTabs, KVTable, BodyEditor, TabBar, Sidebar, plus the app shell: Titlebar, Statusbar, PaneSplit, Shell). State lives in module-level zustand stores under lib/ (tabsStore, toastStore, settingsStore); lib/ also holds the renderer-only request domain model (requestSpec), pure utilities (cx, httpMethods), the display-only {{variable}} tokeniser (varTokens) plus its envVars seam and icons-glue resolver, and the renderer-pure two-pass JSON + {{var}} body tokeniser (jsonTokens). App.tsx composes the Shell and mounts the single ToastProvider; main.tsx is the React root. All modules are renderer-pure (no node/electron imports) and bind color and geometry to design tokens.

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
│   │   ├── EmptyPanel.css  # EmptyPanel styles from design tokens
│   │   ├── EmptyPanel.tsx  # Shared "Panel not yet available" placeholder atom
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
│   │   │   ├── BodyEditor.ct.tsx
│   │   │   ├── BodyEditor.stories.tsx
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
│   │   ├── BodyEditor.css  # BodyEditor styles bound to design tokens
│   │   ├── BodyEditor.tsx  # Body-type ARIA radiogroup + mount-all mode switch + textarea/pre/gutter code area (memo-wrapped)
│   │   ├── KVTable.css  # KVTable styles from design tokens
│   │   ├── KVTable.tsx  # Key/value row table editor; field mode (params/headers) + controlled render-prop mode (urlencoded)
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
│   │   ├── jsonTokens.test.ts
│   │   ├── requestSpec.test.ts
│   │   ├── tabsStore.test.ts
│   │   ├── toastStore.test.ts
│   │   └── varTokens.test.ts
│   ├── cx.ts  # className merge util (filters falsy tokens)
│   ├── envVars.ts  # Active-env variable name set (T14 seam, empty stub)
│   ├── httpMethods.ts  # HTTP method tuple + derived HttpMethod type
│   ├── icons-glue.ts  # Safe icon-name resolver bridge over icons.ts
│   ├── jsonTokens.ts  # Renderer-pure two-pass JSON + {{var}} body tokeniser (compose())
│   ├── requestSpec.ts  # Renderer-only HTTP request domain model; Body tagged record + guards
│   ├── settingsStore.ts  # zustand store for shell view state
│   ├── tabsStore.ts  # zustand store: working-tabs lifecycle machine; re-exports Body types + BLANK_BODY
│   ├── toastStore.ts  # zustand store: toast notification queue
│   └── varTokens.ts  # Display-only {{variable}} tokeniser (no resolve)
├── test-utils
│   ├── fidelityAssert.ts  # CT computed-style fidelity helpers; fail-closed when live-renderer channel absent
│   └── simulateDrag.ts  # Test helper: synthesize pointer drag events
├── App.tsx  # Root component: composes Shell + ToastProvider
├── env.d.ts  # Ambient TS env/asset type declarations
└── main.tsx  # React root mount (renderer entry)
```

## Hazards

**Hazard: Vite CSS `url()` does not resolve bare `@fontsource/...` specifiers.** In `fonts.css` each `@font-face src:` must use a RELATIVE path from that file into `node_modules` — not a bare package specifier. Vite's CSS pipeline resolves relative paths and fingerprints and emits the woff2 into the renderer bundle; a bare specifier (e.g. `url('@fontsource/inter/files/inter-latin-400-normal.woff2')`) is treated as a literal URL string, the woff2 is never bundled, and fonts fail to load silently. Apply the same relative-path pattern whenever adding a new weight or typeface via `@fontsource`.

<!-- src/renderer/src/assets/fonts.css:21-21 -->
```css
src: url('../../../../node_modules/@fontsource/inter/files/inter-latin-400-normal.woff2') format('woff2');
```

**Hazard: Form elements do not inherit `body` font-family without an explicit reset.** The UA stylesheet overrides `font-family` on `button`, `input`, `select`, and `textarea` — even when `body` declares one via a CSS custom property. The reset in `base.css` is load-bearing: removing it causes all form controls to render in the OS system font rather than Inter, regardless of what `--font-sans` is set to.

<!-- src/renderer/src/assets/base.css:45-50 -->
```css
button,
input,
select,
textarea {
  font-family: inherit;
}
```

**Hazard: `JSON.parse(text)` inside `compose()` is the malformed-JSON degrade detector — do not remove.** `jsonTokens.ts` calls `JSON.parse(text)` before invoking the structural scanner (`scanJsonTokens`). Although the parse result is discarded, the call is not redundant: `scanJsonTokens` assumes valid JSON and produces garbled output on malformed input. The `catch` block — which returns a single plain segment covering the whole text — is the intentional AC-17 degrade path. Removing the `JSON.parse` call (e.g. as "dead code") eliminates that gate and allows `scanJsonTokens` to run on invalid input.

<!-- src/renderer/src/lib/jsonTokens.ts:364-372 -->
```typescript
  try {
    JSON.parse(text) // Validation only — result is discarded; tokenisation uses our own scanner.
    jsonTokens = scanJsonTokens(text)
  } catch {
    // Malformed JSON: JSON.parse threw a SyntaxError. Return a single plain segment
    // covering the whole text (AC-17). This catch IS the error-handling path — not an
    // empty catch; returning here is the intentional degrade.
    return [{ kind: 'plain', text }]
  }
```

**Hazard: BodyEditor's mount-all/hidden pattern preserves DOM-local state only — mode values live in the store.** All 6 body-mode panels are always mounted; inactive panels carry the HTML `hidden` attribute. This preserves DOM-local state (scroll position, caret position) across mode switches, but it does NOT preserve mode values. `body.raw.text`, `body.raw.lang`, and `body.urlencoded.rows` are owned by the tagged-record `Body` in the store (`tab.spec.body`). Mode values survive switches because the `Body` record always carries both `raw` and `urlencoded` sub-objects simultaneously — the store is the SSOT, not the DOM.
