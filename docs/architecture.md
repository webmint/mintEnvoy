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

The renderer process has a two-sublayer structure beneath feature components:

| Sublayer | Contents | Path |
| --- | --- | --- |
| Presentation — atoms | Inline SVG `Icon` component + typed `IconName` string-literal union over the project-owned 40-icon set | `src/renderer/src/components/atoms/` |
| Presentation — molecules | `Dropdown`, `Modal`, `Toast` — thin wrappers over Radix UI primitives, styled via semantic classes | `src/renderer/src/components/molecules/` |
| Support — lib/ (thin) | `toastStore` (zustand queue + imperative `toast()` API), `icons-glue` (Icon lookup/fallback), shared `cx()` className helper | `src/renderer/src/lib/` |

**Dependency direction**: presentation imports from lib/; `lib/` must NOT import from `components/`. All intra-renderer imports use the `@renderer` alias — no deep relative paths across sublayer boundaries.

**Overlay substrate**: Radix `radix-ui` unified package owns focus-trap, keyboard navigation, and positioning for Dropdown/Modal/Toast. The project adds only what Radix does not provide (the toast queue, Icon, and styling).

**Toast queue pattern**: a single module-level zustand `toastStore` owns the toast stack (enqueue, auto-dismiss, manual-dismiss, hover/focus-pause). `Toast.tsx` renders the store's queue via Radix `Toast.Root`/`Toast.Viewport`. A single `ToastProvider` + `ToastViewport` is mounted once at the App root (`App.tsx`) — multiple instances would split the queue.

**Styling**: semantic class names bound to `tokens.css` CSS custom properties; no inline styles. Per-component CSS files live alongside the component under `atoms/` and `molecules/`.

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

## Architecture Overview

mintEnvoy is structured around Electron's three-process security model. The **main** process (Node.js) owns the application lifecycle and creates the single BrowserWindow with sandbox-friendly webPreferences and a preload script attached. The **preload** bridge runs with context isolation and is the only place permitted to expose privileged Electron APIs to the UI, doing so through contextBridge under a process.contextIsolated guard. The **renderer** is a React 19 single-page UI that must never import Node or Electron modules — it talks to the platform exclusively through the globals the preload bridge exposes on window.

Within the renderer, the code is organized as a small design-system: an Icon atom, Dropdown/Modal/Toast molecules built on Radix primitives, and a shared lib layer (className merge, safe icon resolution, and a module-level zustand toast store). UI styling is driven by CSS custom-property design tokens rather than inline styles. A dev-only PrimitivesDemo gallery is dynamically imported behind import.meta.env.DEV so it is tree-shaken out of production builds.

The toolchain is electron-vite (three build targets: main, preload, renderer) for bundling and electron-builder for OS packaging, with Vitest + Playwright component tests covering the primitive library.

## Module / Package Structure

```text
src/
├── main/        # Node.js main process — BrowserWindow, app lifecycle, IPC host
├── preload/     # contextIsolation-safe bridge (contextBridge → window globals)
└── renderer/    # React 19 UI (no Node/Electron imports)
    └── src/
        ├── components/
        │   ├── atoms/      # Icon
        │   ├── molecules/  # Dropdown, Modal, Toast (Radix-based)
        │   └── PrimitivesDemo.tsx  # dev-only gallery
        ├── lib/    # cx, icons-glue, toastStore
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

## Conventions

**Naming**
- Components in PascalCase one-per-file (Icon.tsx, Dropdown.tsx, Modal.tsx, Toast.tsx)
- lib helpers and stores in camelCase modules (cx.ts, icons-glue.ts, toastStore.ts)

**File Organization**
- Renderer UI grouped by atomic-design tier: components/atoms, components/molecules
- Co-located tests under __tests__/ next to the code they cover, with .test.tsx (Vitest) and .ct.tsx (Playwright CT) split
- Component styles in a sibling .css file (Icon.css, Dropdown.css) — no inline styles

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
- Shared UI state held in module-level zustand stores (toastStore) exporting a single instance
- State mutated only through store actions; an imperative toast() API wraps the store for fire-and-forget use

## Layers

- Main process — Node.js lifecycle, native window creation, IPC host; docs/main/
- Preload bridge — contextIsolation-safe API surface exposed to the renderer; docs/preload/
- Renderer — React UI: primitive library, toast store, design tokens; docs/renderer/

## Cross-Cuts

### Renderer process isolation

Renderer-side modules carry no Node or Electron imports; the lib layer imports only via the @renderer alias and the renderer reaches the platform through preload-exposed window globals. This keeps context isolation intact (constitution §2.3 / §4).

<!-- src/renderer/src/lib/icons-glue.ts:13 -->
```typescript
import { ICONS, type IconName } from '@renderer/components/atoms/icons'
// has NO node / electron imports (renderer-only)
```

### Dev-only code elimination

The PrimitivesDemo gallery is loaded via a dynamic import() gated on import.meta.env.DEV. Vite replaces DEV with false in production, making the import statically unreachable so Rollup drops both the module and its CSS side-effect from the production bundle.

<!-- src/renderer/src/App.tsx:10 -->
```typescript
const PrimitivesDemo = import.meta.env.DEV
  ? lazy(() => import('./components/PrimitivesDemo'))
  : null
```

## Dependency Direction Rules

- main may use Node/Electron freely; it never imports renderer code
- preload is the only bridge — it exposes APIs to the renderer via contextBridge and depends on neither renderer UI nor main internals
- renderer depends only on browser/React APIs and preload-exposed window globals — never on Node, Electron, or main
- renderer lib (cx, icons-glue, toastStore) is leaf-level: components depend on lib, lib depends on nothing renderer-external

## Dependency Overview

```mermaid
graph TD
  main[main process] -->|attaches preload| preload[preload bridge]
  preload -->|exposes window.electron / window.api| renderer[renderer UI]
  renderer --> components[components: atoms + molecules]
  components --> lib[lib: cx / icons-glue / toastStore]
  components --> radix[radix-ui]
  components --> tokens[styles/tokens.css]
```
