# Project Constitution — mintenvoy

Generated: 2026-06-25
Last updated: 2026-06-25
Mode: Existing Codebase

> Sections marked `[universal]` are pre-populated with rules that apply to ALL projects.
> Sections marked `[project-specific]` are populated by `/constitute` based on your codebase or interview answers.

---

## 1. Project Identity

**Name**: mintenvoy
**Type**: desktop app
**Domain**: Desktop API client for composing and sending HTTP requests, built on Electron's three-process model (main / preload / renderer) with a reusable headless UI-primitive library — Icon, Dropdown, Modal, Toast, Tabs.
**Stack**: TypeScript, React 19, Electron multi-process (main / preload / renderer), zustand state, Radix UI primitives, undici HTTP, electron-store persistence, electron-updater auto-update; bundled by electron-vite + Vite, packaged by electron-builder.

---

## 2. Architecture Rules (NON-NEGOTIABLE)

These rules MUST be followed in every code change. Violating these rules requires explicit user approval.

### 2.1 Process Boundaries

Electron's three-process security model: a Node.js main process, a contextIsolation-safe preload bridge, and a browser-only React renderer — each with a fixed import boundary.

| Layer | Path | Contains | Imports from |
|-------|------|----------|--------------|
| Main process | src/main/ | BrowserWindow, app lifecycle, IPC host | Node, Electron (freely) |
| Preload bridge | src/preload/ | contextBridge API surface to window | @electron-toolkit/preload only |
| Renderer | src/renderer/ | React UI, stores, design tokens | browser/React + preload window globals |
- [extracted] main may use Node/Electron freely; it never imports renderer code
- [extracted] preload is the only bridge — it exposes APIs to the renderer via contextBridge and depends on neither renderer UI nor main internals
- [extracted] renderer depends only on browser/React APIs and preload-exposed window globals — never on Node, Electron, or main
- [enforced] contextBridge exposure runs only under a process.contextIsolated guard and is wrapped in try/catch

**CORRECT** — renderer talks to the platform only through preload globals

```ts
// renderer — reach the platform via a preload-exposed global
const versions = window.electron.process.versions
```

**WRONG** — renderer must never import Node/Electron directly

```ts
// renderer — FORBIDDEN: direct Node/Electron import
import { ipcRenderer } from 'electron'
```

### 2.2 Renderer Tier Organization

The renderer is a small atomic-design system; component tiers and the leaf lib layer import in one direction only.
- [extracted] renderer component tiers flow downward only: organisms → molecules → atoms; no sibling-tier or upward imports
- [extracted] renderer lib (cx, icons-glue, toastStore, settingsStore, tabsStore, requestSpec) is leaf-level — components depend on lib, lib depends on nothing renderer-external
- [extracted] requestSpec is imported by tabsStore but stays a pure data module — no component imports
- [extracted] Domain placement: shared/domain-agnostic components belong in `molecules/`; single-domain-bound components belong in `organisms/<domain>/`; create an `organisms/<domain>/` subfolder only when a domain reaches ≥2 components (no empty future domain folders); no barrel/index files

**EXAMPLE** — renderer module structure

```text
src/
├── main/        # Node.js main process — BrowserWindow, app lifecycle, IPC host
├── preload/     # contextIsolation-safe bridge (contextBridge → window globals)
└── renderer/src/
    ├── components/
    │   ├── atoms/      # Icon
    │   ├── molecules/  # Dropdown, Modal, Toast (Radix); Tabs (hand-rolled WAI-ARIA); Divider (WAI-ARIA splitter)
    │   └── organisms/  # shell/ (Shell, Titlebar, Statusbar, PaneSplit); Sidebar, TabBar (domain singletons)
    ├── lib/    # cx, icons-glue, toastStore, settingsStore, tabsStore, requestSpec
    └── styles/ # tokens.css design tokens
```

### 2.3 Import & Path Rules

Cross-module renderer imports resolve through a path alias, never deep relative chains; Node/Electron stay out of the renderer entirely.
- [enforced] renderer imports cross-module code via the @renderer path alias rather than deep relative paths
- [enforced] renderer modules import no Node/Electron APIs

---

## 3. Code Quality Standards

### 3.1 Type Safety [project-specific]

TypeScript strict mode across both node and web configs; untyped boundaries narrow rather than cast.
- [enforced] TypeScript strict mode is on (tsconfig strict) — no implicit any
- [enforced] type-check passes for both configs before task completion (npm run typecheck:node && npm run typecheck:web)
- [universal] prefer unknown + a type guard over any at untyped boundaries

**CORRECT** — narrow unknown through a type guard

```ts
function parse(raw: string): RequestSpec {
  const data: unknown = JSON.parse(raw)
  if (isRequestSpec(data)) return data
  return makeBlankRequest()
}
```

**WRONG** — any defeats strict mode

```ts
const data = JSON.parse(raw) as any  // bypasses type safety
```

### 3.2 Error Handling [project-specific]

Boundary lookups degrade gracefully; bridge exposure logs on failure rather than swallowing.
- [extracted] boundary lookups degrade gracefully instead of throwing (resolveIcon returns a fallback entry)
- [extracted] contextBridge exposure is wrapped in try/catch and logs on failure rather than swallowing
- [universal] never swallow errors — handle, re-throw, or log with a reason; no empty catch blocks

### 3.3 Naming Conventions [project-specific]

Components PascalCase one-per-file; lib helpers and stores camelCase; styles in sibling .css.

| What | Convention | Example |
|------|------------|---------|
| Component | PascalCase, one per file | Icon.tsx, Modal.tsx |
| lib helper/store | camelCase module | cx.ts, toastStore.ts |
| Component style | sibling .css file | Icon.css, Shell.css |
| Test file | __tests__/ co-located | Icon.test.tsx, Icon.ct.tsx |
- [extracted] components in PascalCase, one per file (Icon.tsx, Dropdown.tsx)
- [extracted] lib helpers and stores in camelCase modules (cx.ts, toastStore.ts)

### 3.4 Testing Requirements [project-specific]

Vitest unit + Playwright component tests, co-located by tier.
- [extracted] co-located tests under __tests__/ next to the code, split .test.tsx (Vitest) and .ct.tsx (Playwright CT)
- [universal] cover the acceptance criteria including edge and error paths

### 3.5 Documentation & Code Discovery [universal]

New code is documented; structural code exploration routes through the codebase-memory graph, not raw file reads.
- [universal] all new functions/variables carry clear documentation
- [enforced] structural code queries route through codebase-memory-mcp tools (search_graph / trace_path / get_code_snippet / search_code / query_graph) — NOT raw Read/Grep/Glob over source files; CBM hooks block raw discovery at PreToolUse on the first match per session
- [universal] docs/ is LLM-context-source first, dev-greppable second; concern prose lives in docs/<pkg>/<concern>/index.md; structural metadata stays in CBM, never embedded in docs/

### 3.6 Simplicity & Reuse [universal]

Keep changes minimal and reuse before building.
- [universal] SOLID, DRY, KISS — single responsibility; don't repeat logic 3+ times; keep it simple
- [universal] search the codebase for an existing utility/helper/component before writing anything generic

---

## 4. Patterns & Anti-Patterns

### Always Do (Universal)
- [universal] Validate external input at module boundaries; trust internal code
- [universal] Handle both success and error paths for every fallible operation
- [universal] Read a file before modifying it

### Always Do (Project-Specific)
- [extracted] Shared UI state lives in module-level zustand stores (toastStore, settingsStore, tabsStore) — one instance each
- [extracted] Mutate state only through store actions
- [extracted] Shell view state (theme, accent, mstyle, sidebarWidth, paneRatio, sidebarCollapsed) lives exclusively in settingsStore — Shell.tsx is the sole writer of the matching document.documentElement attrs/vars
- [extracted] Working-tabs lifecycle (open, dedupe, close, dirty) lives exclusively in tabsStore — TabBar.tsx is the lifecycle subscriber (wiring open/dedupe/close/select actions to the Tabs molecule); RequestBar.tsx is the spec-edit subscriber (reading the active tab's spec and writing method+url via updateActiveSpec); TabBar's runtime behavior is unchanged
- [extracted] Compose conditional class tokens with cx() (falsy-filtering merge)
- [extracted] Resolve icon names through resolveIcon — total, never throws, returns a fallback entry

### Never Do (Universal)
- [universal] Never swallow errors silently
- [universal] Never commit secrets or debug artifacts (console.log, debugger, stray print)
- [universal] Never modify code outside the task scope

### Never Do (Project-Specific)
- [extracted] Never import Node/Electron in the renderer
- [extracted] Never expose privileged APIs outside the preload contextBridge
- [extracted] Never mutate zustand state outside a store action
- [extracted] Never write Shell document.documentElement vars/attrs from anywhere but Shell.tsx
- [extracted] Never add a raw px delta to a unitless ratio (Divider ratio-valued drag hazard)
- [extracted] Never use inline styles — class-based styling composed with cx()

### Prefer (Universal)
- [universal] Prefer composition over inheritance
- [universal] Prefer small, single-responsibility modules

### Prefer (Project-Specific)
- [extracted] Prefer wrapping Radix for new molecules (Dropdown/Modal/Toast); hand-rolled WAI-ARIA only as a documented departure (Tabs)
- [extracted] Prefer design tokens (CSS custom properties in tokens.css) over literal style values
- [extracted] Prefer the imperative toast() API for fire-and-forget toasts (wraps toastStore)
- [extracted] Prefer the @renderer alias over deep relative imports

---

## 5. Domain Rules

### 5.1 Key Entities

The core domain objects of the API client and its UI shell.
- [extracted] RequestSpec — the HTTP request domain model (method, url, headers, body); created blank via makeBlankRequest
- [extracted] Working tab — an open request in the tabs strip; lifecycle (open, dedupe, close, dirty) owned by tabsStore
- [extracted] Toast — a transient notification queued in toastStore, surfaced via the imperative toast() API
- [extracted] View state — theme, accent, mstyle, sidebarWidth, paneRatio, sidebarCollapsed; the Shell SSOT in settingsStore
- [extracted] UI primitives — Icon (atom); Dropdown/Modal/Toast/Tabs/Divider (molecules); Shell/Titlebar/Statusbar/PaneSplit (organisms/shell/), Sidebar/TabBar (organisms)

### 5.2 Domain Invariants

Lifecycle and ownership rules the domain state must hold.
- [extracted] A working tab is deduped on open — re-opening the same request focuses the existing tab instead of duplicating it
- [extracted] A working tab carries a dirty flag tracking unsaved edits
- [extracted] settingsStore is the single source of truth for Shell view state; Shell.tsx is the only writer of the matching document attrs/vars
- [extracted] requestSpec stays a pure data module — imported by tabsStore, never by components

---

## 6. Workflow Rules

### 6.1 Minimal Changes
- [universal] Every change impacts as little code as possible
- [universal] Never "fix" unrelated code you happen to see

### 6.2 Read Before Write
- [universal] Always read a file before modifying it

### 6.3 Search Before Building
- [universal] Search the codebase for an existing utility/helper/component before writing anything generic or reusable

### 6.4 One Task At A Time
- [universal] Execute tasks sequentially following the dependency graph

### 6.5 Pre-flight Check
- [universal] Read constitution.md and .devforge/memory.md before starting each task

### 6.6 Project-Specific Workflow
- [project-specific] Spec-driven flow is strict — specs are contracts; once approved, implementation must satisfy every acceptance criterion
- [project-specific] Hard gates block: spec approval → /plan; plan approval → /breakdown; breakdown approval → /implement; ACs verified in /verify
- [enforced] Lint + type-check must pass on all changed files before task completion
- [project-specific] Commits follow Conventional Commits and include the Co-Authored-By: Claude attribution trailer
