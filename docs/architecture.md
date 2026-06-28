---
last_indexed: 2026-06-22
source_stamp: 0b70347c45e28304
---

# Architecture — mintenvoy

> Commands named in backticks (e.g. `constitute`, `onboard`) are invoked with the `/` prefix in Claude Code (e.g. `/constitute`).
>
> **Project**: mintenvoy — see the project primer (`CLAUDE.md`) for stack facts (language, framework, build/lint/typecheck commands) and, for multi-package projects, the `## Packages` table with per-package detail. This file captures architectural **decisions, rules, and flow** — the "why" behind the setup, not the "what".

---

## Architectural Decisions

_Populated by `constitute` — records WHY decisions were made, not just what. Format: **Decision** — rationale + tradeoffs considered._

## Layer Boundaries & Dependency Rules

_Populated by `constitute` (for new/greenfield projects — chosen patterns) or `onboard` (for brownfield projects — extracted from existing code). Documents which layers exist, what imports from what, and which directions are forbidden._

### Renderer — UI Primitives Layer (established by feature 001-ui-primitives)

The renderer process has a three-sublayer structure beneath feature components:

| Sublayer                 | Contents                                                                                                                                                                                                                          | Path                                      |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| Presentation — atoms     | Inline SVG `Icon` component + typed `IconName` string-literal union over the project-owned 40-icon set                                                                                                                            | `src/renderer/src/components/atoms/`      |
| Presentation — molecules | `Dropdown`, `Modal`, `Toast` — thin wrappers over Radix UI primitives, styled via semantic classes. `Tabs` — controlled selection-only tab-strip; hand-rolled WAI-ARIA engine (see Patterns § below for the departure rationale). `Divider` — hand-rolled WAI-ARIA splitter (domain-agnostic; used by `PaneSplit`). | `src/renderer/src/components/molecules/`  |
| Presentation — organisms | `Shell` (root composition layer), `Titlebar`, `Statusbar`, and `PaneSplit` — grouped under `organisms/shell/` (app-shell domain). `Sidebar`, `TabBar`, and `RequestBar` — flat domain singletons directly under `organisms/`. Organisms compose molecules/atoms; they never import across the same tier. | `src/renderer/src/components/organisms/`  |
| Support — lib/ (thin)    | `toastStore` (zustand queue + imperative `toast()` API), `settingsStore` (zustand SSOT for theme/accent/mstyle/sidebarWidth/paneRatio/sidebarCollapsed + clamp helpers), `icons-glue` (Icon lookup/fallback), shared `cx()` className helper, `httpMethods` (ordered `METHODS` tuple + `HttpMethod` union — method SSOT consumed by `requestSpec`, `RequestBar`, and `Tabs`) | `src/renderer/src/lib/`          |

**Dependency direction**: organisms import from molecules and atoms; molecules and atoms import from lib/; `lib/` must NOT import from `components/`. No sibling-tier imports (organisms must not import other organisms). All intra-renderer imports use the `@renderer` alias — no deep relative paths across sublayer boundaries.

**Overlay substrate**: Radix `radix-ui` unified package owns focus-trap, keyboard navigation, and positioning for Dropdown/Modal/Toast. The project adds only what Radix does not provide (the toast queue, Icon, and styling).

**Toast queue pattern**: a single module-level zustand `toastStore` owns the toast stack (enqueue, auto-dismiss, manual-dismiss, hover/focus-pause). `Toast.tsx` renders the store's queue via Radix `Toast.Root`/`Toast.Viewport`. A single `ToastProvider` + `ToastViewport` is mounted once at the App root (`App.tsx`) — multiple instances would split the queue.

**Shell app-state pattern**: a single module-level zustand `settingsStore` is the SSOT for all shell view state. `Shell.tsx` is the sole writer of `document.documentElement` data-attributes (`data-theme`, `data-accent`, `data-mstyle`) and CSS custom properties (`--sidebar-width`, `--pane-ratio`); the `Divider` also writes these same CSS vars during live drag at rAF cadence. No other component sets these attrs or vars directly.

**Working-tabs state machine pattern**: a single module-level zustand `tabsStore` owns the open-request tab list (`tabs: Tab[]`, array order = visual order), the active tab pointer (`activeTabId`), and the full lifecycle — `openFromCollection` (id-then-url two-leg dedupe), `newBlank`, `close` (never-zero: spawns a replacement when the last tab closes; right-then-left neighbor selection when the active tab closes), `selectActive`, `markClean(tabId)`, and `updateActiveSpec(patch)` (shallow-merges a partial `RequestSpec` patch into the active tab's spec; no-op when every key already equals the current value, so the dirty flag is never flipped spuriously). `TabBar` is the lifecycle subscriber — it wires `openFromCollection`, `newBlank`, `close`, and `selectActive` to the Tabs molecule. `RequestBar` is the spec-edit subscriber — it reads the active tab's `method`, `url`, and `dirty` fields via per-field selectors and writes them back via `updateActiveSpec`; Save calls `markClean`. The never-zero invariant is a construction-time guarantee: the store initialises with one seeded blank tab and `close` always spawns a replacement before removing the last entry. `requestSpec.ts` is a pure data module in lib/ — exports types only (`RequestSpec`, `Row`, `Auth` discriminated union, `isBearerAuth` type guard) and `makeBlankRequest()` seed factory; it carries no actions and no store state (constitution §3.1 / §4).

**Styling**: semantic class names bound to `tokens.css` CSS custom properties; no inline styles. Per-component CSS files live alongside the component under `atoms/`, `molecules/`, and `organisms/`.

## Data Flow

_Populated by `onboard` (for brownfield — scan findings) or by tech-writer as features are built. Captures how data moves through the system end-to-end._

## Cross-cutting Concerns

_Populated as relevant: authentication/authorization approach, error propagation strategy, logging/observability, transaction boundaries, caching strategy, feature flagging. Filled in by `constitute` or discovered by `onboard`._

## Testing

### Renderer Test Stack

Renderer test stack: Vitest + @testing-library/react + user-event (jsdom) for interaction tests; Playwright component tests (`@playwright/experimental-ct-react`) for real-browser focus/keyboard fidelity.

- **Unit / interaction tests**: `vitest run` — configured in `vitest.config.ts` at the repo root; environment is `jsdom`; globals enabled; setup file imports `@testing-library/jest-dom` matchers; `@renderer` alias mirrors `electron.vite.config.ts`.
- **Component tests (real browser)**: `playwright test -c playwright.config.ts` — configured in `playwright.config.ts`; uses `@playwright/experimental-ct-react` to mount components in Chromium for keyboard/focus fidelity.
- Test files live under `src/renderer/src/**/*.{test,spec}.{ts,tsx}` (Vitest) and `src/renderer/src/**/*.ct.{ts,tsx}` (Playwright CT).
- No test infrastructure exists for the main or preload processes; add if needed.

**Hazard: Radix overlay CT — click-outside must wait for listener readiness.** `DismissableLayer` (the dismiss engine inside Radix Dropdown, Modal, and similar overlay primitives) defers its `pointerdown` handler via `setTimeout(0)`. A `page.mouse.click` issued before that macrotask executes silently misses the listener and the overlay stays open — producing intermittent false-pass failures. The required gate before any outside click in a Radix overlay CT: (1) await all overlay animations to finish; (2) yield one `setTimeout(0)` macrotask boundary to arm the listener. Step 1 is a no-op under `prefers-reduced-motion: reduce` (no animations run), but step 2 alone suffices to arm the listener in that case. Apply this two-step gate to every Playwright CT that dismisses a Radix overlay (Dropdown, Modal, and any future Tooltip, Popover, or Select CTs).

<!-- src/renderer/src/components/molecules/__tests__/Dropdown.ct.tsx:198-201 -->

```typescript
await menu.evaluate((el) => Promise.all(el.getAnimations().map((a) => a.finished)))
// Macrotask-boundary readiness floor: guarantees Radix DismissableLayer's
// setTimeout(0)-deferred pointerdown listener has fired (not a fixed delay).
await page.evaluate(() => new Promise((resolve) => setTimeout(resolve, 0)))
```

## Architecture Overview

mintEnvoy is structured around Electron's three-process security model. The **main** process (Node.js) owns the application lifecycle and creates the single BrowserWindow with sandbox-friendly webPreferences and a preload script attached. The **preload** bridge runs with context isolation and is the only place permitted to expose privileged Electron APIs to the UI, doing so through contextBridge under a process.contextIsolated guard. The **renderer** is a React 19 single-page UI that must never import Node or Electron modules — it talks to the platform exclusively through the globals the preload bridge exposes on window.

Within the renderer, the code is organized as a small design-system with three atomic-design tiers: an Icon atom; Dropdown/Modal/Toast/Tabs/Divider molecules (Dropdown/Modal/Toast wrap Radix; Tabs hand-rolls its WAI-ARIA engine and also supports opt-in closable, method-chip, and dirty-state affordances — see Patterns §; Divider is a hand-rolled WAI-ARIA splitter); and organisms — Shell, Titlebar, Statusbar, and PaneSplit (grouped under organisms/shell/) plus flat singletons Sidebar, TabBar (the working-tabs strip), and RequestBar (the method-dropdown + URL-input + Send/Save/Share bar for the active tab) — that compose the single-window app shell. A shared lib layer provides className merge, safe icon resolution, three module-level zustand stores (toastStore for the toast queue; settingsStore as the view-state SSOT; tabsStore as the working-tabs lifecycle state machine), `httpMethods` (ordered `METHODS` tuple + `HttpMethod` union — the method SSOT), and the requestSpec domain model (RequestSpec types + makeBlankRequest factory). UI styling is driven by CSS custom-property design tokens rather than inline styles. A dev-only PrimitivesDemo gallery is dynamically imported behind import.meta.env.DEV so it is tree-shaken out of production builds.

The toolchain is electron-vite (three build targets: main, preload, renderer) for bundling and electron-builder for OS packaging, with Vitest + Playwright component tests covering the primitive library.

## Module / Package Structure

```text
src/
├── main/        # Node.js main process — BrowserWindow (minWidth: 720), app lifecycle, IPC host
├── preload/     # contextIsolation-safe bridge (contextBridge → window globals)
└── renderer/    # React 19 UI (no Node/Electron imports)
    └── src/
        ├── components/
        │   ├── atoms/      # Icon
        │   ├── molecules/  # Dropdown, Modal, Toast (Radix-based); Tabs (hand-rolled WAI-ARIA; opt-in closable, method-chip, dirty-state); Divider (WAI-ARIA splitter)
        │   ├── organisms/
        │   │   ├── shell/  # Shell, Titlebar, Statusbar, PaneSplit (app-shell domain)
        │   │   ├── RequestBar.tsx   # request submission bar; method dropdown + URL input + Send/Save/Share; wired to tabsStore.updateActiveSpec
        │   │   ├── RequestBar.css
        │   │   ├── Sidebar.tsx
        │   │   └── TabBar.tsx   # working-tabs strip
        │   └── PrimitivesDemo.tsx  # dev-only gallery
        ├── lib/    # cx, icons-glue, toastStore, settingsStore, tabsStore, requestSpec, httpMethods
        └── styles/ # tokens.css design tokens
```

## Patterns

### cx — falsy-filtering className merge

**Applies in**: Every renderer component that composes conditional class tokens (Icon, Dropdown, Modal, Toast)

Build className strings with cx() instead of open-coded array filter/join or template literals; falsy tokens are dropped so conditional classes compose cleanly.

<!-- src/renderer/src/lib/cx.ts:18 -->

```typescript
export function cx(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(' ')
}
```

### resolveIcon — total, never-throwing icon lookup

**Applies in**: Any consumer resolving a possibly-unvalidated icon name (Icon component and callers)

Resolve icon names through resolveIcon, which validates against the known set and returns a FALLBACK_ENTRY for unknown names rather than throwing — boundary input is never trusted to be a valid key.

<!-- src/renderer/src/lib/icons-glue.ts:64 -->

```typescript
export function resolveIcon(name: string): IconEntry {
  if (isIconName(name)) {
    return {
      name,
      markup: ICONS[name]
    }
  }
  return FALLBACK_ENTRY
}
```

### Shell — store→`<html>` CSS-var contract (established by feature 003-app-shell-layout)

**Applies in**: `Shell.tsx` (committed values) and `Divider.tsx` (live-drag values)

The shell theme, accent, method-style, and layout dimensions are surfaced to CSS through two mechanisms that both write to `document.documentElement`:

- Data-attributes (`data-theme`, `data-accent`, `data-mstyle`): written by Shell's Effect 1 on every store change. No other component writes these attributes.
- CSS custom properties (`--sidebar-width` in `px`, `--pane-ratio` unitless): written by Shell's Effect 2 on commit, and overwritten directly by Divider's rAF callback during live drag. Both writers target the same element so CSS selectors resolve consistently.

All CSS layout rules that depend on sidebar width or pane ratio must read from `document.documentElement` CSS custom properties, not from React state.

<!-- src/renderer/src/components/organisms/shell/Shell.tsx:250 -->

```typescript
  useEffect(() => {
    const { style } = document.documentElement
    const nextWidth = `${sidebarWidth}px`
    if (style.getPropertyValue('--sidebar-width') !== nextWidth) {
      style.setProperty('--sidebar-width', nextWidth)
    }
    const nextRatio = `${paneRatio}`
    if (style.getPropertyValue('--pane-ratio') !== nextRatio) {
      style.setProperty('--pane-ratio', nextRatio)
    }
  }, [sidebarWidth, paneRatio])
```

### Divider — ratio-valued drag mapping (hazard: raw px delta must not be added to a unitless ratio)

**Applies in**: `PaneSplit.tsx` (horizontal Divider for pane ratio)

When a Divider's `value` is a unitless ratio (0–1) rather than pixels, pointer pixel deltas must be divided by the container's pixel extent before being added to the ratio. Adding raw px to a ratio produces a nonsense value and breaks layout silently — the Divider crossed 0.02 via a 200 px drag, not 200. The `getDragExtent` prop solves this: the mounter returns the container's current pixel width/height, and Divider computes `valueDelta = pixelDelta / extent`.

Rule: any Divider whose `value` is not 1:1 with pointer pixels **must** supply `getDragExtent` and **must** set `unit=''` (unitless CSS var write) and a small `keyboardStep` (e.g. `0.02`).

<!-- src/renderer/src/components/molecules/Divider.tsx:250 -->

```typescript
    const extent = getDragExtent ? getDragExtent() : null
    const valueDelta = extent ? pixelDelta / extent : pixelDelta
    const candidate = drag.startValue + valueDelta
```

### Tabs — hand-rolled WAI-ARIA tablist (documented departure from the Radix-wrap rule)

**Applies in**: `src/renderer/src/components/molecules/Tabs.tsx`

The Tabs primitive does NOT wrap Radix Tabs, departing from the Dropdown/Modal/Toast "buy the a11y engine from Radix" convention. The reason: Radix `Tabs.Trigger` deterministically emits `aria-controls` pointing at a sibling `Tabs.Content`; with no Content mounted (the primitive is selection-only and never renders panels) that attribute dangles and fails WCAG/axe. Instead, Tabs hand-rolls the small WAI-ARIA APG Tabs pattern — `role="tablist"` containing `role="tab"` buttons with manual roving tabindex, Arrow/Home/End key handling with wrap-around, and disabled-tab skipping. The component veneer (flat descriptor-array API, `cx()` BEM classes, sibling CSS file, exported types) still mirrors the Dropdown/Modal/Toast shape; only the a11y engine diverges.

**Opt-in closable extension (feature 004)**: `closable` and `onClose` props are default-off — when absent the primitive is byte-identical to the selection-only contract and no close DOM node or extra keyboard handler is added. When `closable={true}`, a sibling `<button tabIndex={-1}>` renders next to each `role="tab"` button as a pointer-only close target (never a roving tab stop, never `role="tab"`). Delete/Backspace on the focused tab also fires `onClose`. `onClose` is signal-only — it emits the tab id and never mutates the tab list; the store (or parent) owns the lifecycle. The primitive's only post-close responsibility is roving-focus integrity on the next render.

**Rule of thumb for future molecules**: prefer wrapping Radix when the primitive mounts matching Content alongside its trigger/control; hand-roll only when the WAI-ARIA pattern is small and the primitive is explicitly panel-decoupled (selection-only, content rendered elsewhere).

<!-- src/renderer/src/components/molecules/Tabs.tsx:1 -->

```typescript
/**
 * Tabs — hand-rolled, controlled, horizontal-only, selection-only tab-strip.
 * ...
 * The a11y engine is intentionally hand-rolled (`role="tablist"` containing
 * `role="tab"` buttons with manual roving tabindex) instead of wrapping Radix
 * Tabs. Radix `Tabs.Trigger` deterministically emits `aria-controls` pointing at
 * a sibling `Tabs.Content`; with no Content mounted (selection-only) that
 * attribute dangles and fails AC-7.
 */
```

**Feature-005 opt-in extensions to `TabDescriptor`**: two new fields, both backward-compatible (absent = byte-identical output to the pre-005 contract).

- `method?: string` — renders a `<span aria-hidden="true">` chip before the label using global class names `.method` and `.{METHOD}` (e.g. `.GET`, `.DELETE`); unknown methods use the base `.method` class only (uncolored). See hazards below.
- `dirty?: boolean` — in the closable branch, replaces the ✕ button with a non-focusable `<span class="tabs__tab-dirty">` dot; Delete/Backspace on the focused tab still fires `onClose` regardless of dirty state.

**Hazard: `.tabbar` visual contract spans two CSS files.** `TabBar` passes `className="tabbar"` to the Tabs primitive. The full visual treatment is split: `Tabs.css` carries a `.tabbar`-scoped override block (compound selectors prefixed with `.tabbar`) that changes geometry, active treatment, hover fill, tablist flex, and overflow; `TabBar.css` carries strip chrome (height, background, bottom border). Both files must be read together when debugging or changing TabBar appearance.

<!-- src/renderer/src/components/molecules/Tabs.css:392 -->

```css
/* .tabbar-scoped overrides (feature-005, AC-22)
 * ALL rules below use compound selectors (.tabbar .tabs__*, .tabs.tabbar) so
 * they ONLY apply when .tabbar is present on the outer container. */
.tabs.tabbar {
  overflow: visible;
}
```

**Hazard: global `.method`/`.{METHOD}` class names inside a BEM primitive.** The method chip renders with unprefixed global class names (`.method`, `.GET`, `.POST`, etc.), not BEM-scoped names such as `.tabs__method` — by design, so the color rules in `tokens.css` can apply wherever a chip appears. Adding a `.method` or `.{METHOD}` rule in any stylesheet affects all chip instances project-wide, not just `Tabs`.

**Hazard: HEAD method rendering degrades under `chip` mstyle.** `tokens.css` defines `[data-mstyle='soft'] .method.HEAD` (pink background + text), but no other mstyle variant has a HEAD-specific rule. The global `.method.HEAD { color: var(--m-head) }` (specificity 0,2,0) is overridden by `[data-mstyle='chip'] .method { color: #fff }` (same specificity, later in file) — under `chip`, HEAD renders as white text with no background (invisible on typical tab surfaces). Under `outline`/`dot`/`bar`/`text`, HEAD inherits the global pink via `.method.HEAD` but receives no dedicated background. Callers must not assume HEAD is always visually distinct across all mstyle values.

<!-- src/renderer/styles/tokens.css:109 -->

```css
.method.HEAD {
  color: var(--m-head);
}
```

**Hazard: `aria-hidden="true"` on the method chip (a11y tradeoff).** The chip is `aria-hidden` to prevent double-announcement on URL-only tabs, where `deriveLabel` in `TabBar.tsx` already embeds the method in the label text (e.g. `"GET https://api.example.com"`). For **named tabs** — where `label` is a human-readable request name that does not include the method string — the chip is entirely invisible to assistive technology. Callers who need AT users to hear the method for named tabs must embed it in `label`.

## Conventions

**Naming**

- Components in PascalCase one-per-file (Icon.tsx, Dropdown.tsx, Modal.tsx, Toast.tsx)
- lib helpers and stores in camelCase modules (cx.ts, icons-glue.ts, toastStore.ts)

**File Organization**

- Renderer UI grouped by atomic-design tier: components/atoms, components/molecules, components/organisms
- Co-located tests under **tests**/ next to the code they cover, with .test.tsx (Vitest) and .ct.tsx (Playwright CT) split
- Component styles in a sibling .css file (Icon.css, Dropdown.css, Shell.css) — no inline styles

**Import Style**

- Renderer imports cross-module code via the @renderer path alias rather than deep relative paths
- Renderer modules import no Node/Electron APIs

**Error Handling**

- Boundary lookups degrade gracefully instead of throwing (resolveIcon returns a fallback entry)
- contextBridge exposure is wrapped in try/catch and logs on failure rather than swallowing

**Styling**

- Design tokens defined as CSS custom properties in styles/tokens.css and consumed by component stylesheets
- Animations gated behind @media (prefers-reduced-motion: reduce)
- No inline styles — class-based styling composed with cx()

**State Management**

- Shared UI state held in module-level zustand stores (toastStore, settingsStore, tabsStore) exporting a single instance each
- State mutated only through store actions; an imperative toast() API wraps toastStore for fire-and-forget use
- Shell view state (theme, accent, mstyle, sidebarWidth, paneRatio, sidebarCollapsed) lives exclusively in settingsStore — Shell.tsx is the sole writer of the corresponding document.documentElement attrs/vars
- Working-tabs lifecycle (open, dedupe, close, dirty, spec-edits) lives exclusively in tabsStore. TabBar is the lifecycle subscriber (wires open/close/select to the Tabs molecule); RequestBar is the spec-edit subscriber (writes method + url via `updateActiveSpec`; clears dirty via `markClean` on Save)

## Layers

- Main process — Node.js lifecycle, native window creation (minWidth: 720 enforces the OS-level no-overflow floor), IPC host; docs/main/
- Preload bridge — contextIsolation-safe API surface exposed to the renderer; docs/preload/
- Renderer — React UI: organisms (app shell), molecules + atoms (primitive library), lib stores (toastStore, settingsStore), design tokens; docs/renderer/

## Cross-Cuts

### Renderer process isolation

Renderer-side modules carry no Node or Electron imports; the lib layer imports only via the @renderer alias and the renderer reaches the platform through preload-exposed window globals. This keeps context isolation intact (constitution §2.3 / §4).

<!-- src/renderer/src/lib/icons-glue.ts:13 -->

```typescript
import { ICONS, type IconName } from '@renderer/components/atoms/icons'
// has NO node / electron imports (renderer-only)
```

### Dev-only code elimination

The PrimitivesDemo gallery is loaded via a dynamic import() gated on import.meta.env.DEV. Vite replaces DEV with false in production, making the import statically unreachable so Rollup drops both the module and its CSS side-effect from the production bundle. App.tsx mounts `<Shell>` inside `<ToastProvider>` and no longer hosts the PrimitivesDemo lazy-import directly; the gallery continues to exist at `src/renderer/src/components/PrimitivesDemo.tsx` and is consumed from its test and story files. As of feature 009-request-bar, `Shell` receives `tabs={<TabBar />}` and `panes={{ request: <RequestBar /> }}` as props.

<!-- src/renderer/src/App.tsx:6 -->

```typescript
function App(): React.JSX.Element {
  return (
    <ToastProvider>
      <Shell tabs={<TabBar />} panes={{ request: <RequestBar /> }} />
      <ToastViewport />
    </ToastProvider>
  )
}
```

## Dependency Direction Rules

- main may use Node/Electron freely; it never imports renderer code
- preload is the only bridge — it exposes APIs to the renderer via contextBridge and depends on neither renderer UI nor main internals
- renderer depends only on browser/React APIs and preload-exposed window globals — never on Node, Electron, or main
- renderer component tiers flow downward only: organisms → molecules → atoms; no sibling-tier or upward imports
- renderer lib (cx, icons-glue, toastStore, settingsStore, tabsStore, requestSpec, httpMethods) is leaf-level: components depend on lib, lib depends on nothing renderer-external; requestSpec is imported by tabsStore but is still a pure data module (no component imports); httpMethods is imported by requestSpec, RequestBar, and Tabs — it imports nothing itself

## Dependency Overview

```mermaid
graph TD
  main[main process] -->|attaches preload| preload[preload bridge]
  preload -->|exposes window.electron / window.api| renderer[renderer UI]
  renderer --> organisms[components/organisms: shell/(Shell / Titlebar / Statusbar / PaneSplit) / Sidebar / TabBar / RequestBar]
  organisms --> molecules[components/molecules: Dropdown / Modal / Toast / Tabs / Divider]
  molecules --> atoms[components/atoms: Icon]
  atoms --> lib[lib: cx / icons-glue / toastStore / settingsStore / tabsStore / requestSpec]
  organisms --> lib
  molecules --> lib
  molecules --> radix[radix-ui]
  organisms --> tokens[styles/tokens.css]
  molecules --> tokens
  atoms --> tokens
```
