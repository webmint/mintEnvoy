# Spec: app-shell-layout

**Date**: 2026-06-23
**Status**: Complete
**Author**: Claude + User

## 1. Overview

A single-window app shell and layout for the mintEnvoy renderer: a titlebar (logo, workspace pill, sidebar toggle, command-palette trigger, environment selector, account pill), a resizable left sidebar (width clamped 200-520px), a main area split into request and response panes by a draggable horizontal divider (ratio clamped 0.15-0.85), and a statusbar. The shell sets theme, accent, and method-style as data-attributes on the document root and exposes empty named mount slots (sidebar, tabs, panes, modals) whose CONTENTS are out of scope. A net-new in-memory zustand settingsStore (mirroring the existing toastStore) is the single source of truth for sidebar width, pane ratio, theme, accent, and method-style; dividers are hand-rolled and clamped, and styling consumes the existing tokens.css contract with semantic class names (the design/reference.html markup is never copied).

## 2. Current State

Existing codebase, greenfield for the shell. The renderer root src/renderer/src/App.tsx:10 currently mounts the dev-only PrimitivesDemo gallery (lazy, gated behind import.meta.env.DEV). Feature 001-ui-primitives established the renderer tiers components/atoms + components/molecules + a thin lib/ (cx(), icons-glue, toastStore), and 002-tabs-primitive added the controlled selection-only Tabs molecule; there is NO components/organisms/ tier, no Shell, and no settings store — the only zustand store is src/renderer/src/lib/toastStore.ts. The design-token contract at src/renderer/styles/tokens.css already implements the [data-theme='dark'] override block and the [data-mstyle] method-style variant blocks on <html>, but has NO [data-accent] selector — accent is a single --accent custom property (with --accent-soft/--accent-hover derived via color-mix). Persistence is a main-process responsibility (electron-store appears only in config/docs, not in src); the renderer holds no settings store today. The renderer test stack (docs/architecture.md) is Vitest + @testing-library/react + user-event (jsdom) for interaction plus Playwright CT (@playwright/experimental-ct-react) for real-browser focus/keyboard, with tests co-located under **tests**/. The visual/behavior reference is design/reference.html with colors/spacing from design/tokens.json (look/behavior only — never its generated markup).

## 3. Desired Behavior

A new Shell organism under src/renderer/src/components/organisms/ becomes the App.tsx mount, replacing the PrimitivesDemo root (PrimitivesDemo stays in the repo dev-gated but unmounted). The Shell renders a titlebar (logo, workspace pill, sidebar toggle, command-palette trigger, environment selector, account pill), a resizable left sidebar, a request/response split, and a statusbar. A net-new src/renderer/src/lib/settingsStore.ts zustand store (mirroring toastStore: create(), single module-level instance, typed state + actions, reset for tests, no Node/electron imports) holds { theme, accent, mstyle, sidebarWidth, paneRatio, sidebarCollapsed } IN-MEMORY only and is the single source of truth. The Shell sets data-theme, data-accent, and data-mstyle on the document root (<html>) via an effect from the store, and writes sidebarWidth and paneRatio to CSS custom properties on its own root. A draggable vertical divider resizes the sidebar, clamped to 200-520px; a draggable horizontal divider resizes the request/response split, clamped to a ratio of 0.15-0.85. Dividers are hand-rolled pointer-event components (rAF-batched CSS-var write during drag, store committed on release) exposing the WAI-ARIA separator role with aria-valuenow and keyboard resize, and they handle pointer-release outside the window. Cmd-B toggles a sidebarCollapsed boolean that hides the sidebar entirely while preserving the last sidebarWidth for restore on reopen. When the OS window shrinks below the clamped minimums, the layout re-clamps sidebarWidth (200-520px) and paneRatio (0.15-0.85) so no pane goes negative or overflows. The four named mount slots (sidebar, tabs, panes, modals) accept arbitrary children and render them without the Shell knowing their contents. accent is persisted in the store and set as data-accent, but is visually inert this task (no [data-accent] CSS). Styling uses semantic class names bound to tokens.css with sibling .css files and no inline styles, animations respect prefers-reduced-motion, and behavior (divider drag+clamp, Cmd-B toggle, in-session survival of view settings) is covered by component tests; visual fidelity to design/reference.html is reviewed by design-auditor (never reproducing its markup or cruft).

## 4. Affected Areas

| Area                                   | Files                                                                                                                                                                                                                                                                                                               | Impact                                                                                                                                                                                                                        |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Shell organism tree                    | src/renderer/src/components/organisms/Shell.tsx, src/renderer/src/components/organisms/Titlebar.tsx, src/renderer/src/components/organisms/Sidebar.tsx, src/renderer/src/components/organisms/PaneSplit.tsx, src/renderer/src/components/organisms/Statusbar.tsx, src/renderer/src/components/organisms/Divider.tsx | Create new — net-new components/organisms/ tier holding the shell layout tree (titlebar, resizable sidebar, request/response split, statusbar) + hand-rolled clamped Divider; named mount slots for sidebar/tabs/panes/modals |
| settingsStore (in-memory view state)   | src/renderer/src/lib/settingsStore.ts                                                                                                                                                                                                                                                                               | Create new — zustand store mirroring toastStore; single source of truth for { theme, accent, mstyle, sidebarWidth, paneRatio, sidebarCollapsed } + actions; in-memory only (disk persistence deferred)                        |
| App.tsx mount root                     | src/renderer/src/App.tsx                                                                                                                                                                                                                                                                                            | Modify — swap the dev-only PrimitivesDemo root for the Shell organism; PrimitivesDemo stays dev-gated (import.meta.env.DEV) but unmounted                                                                                     |
| Shell stylesheets                      | src/renderer/src/components/organisms/Shell.css, src/renderer/src/components/organisms/Titlebar.css, src/renderer/src/components/organisms/Sidebar.css, src/renderer/src/components/organisms/PaneSplit.css, src/renderer/src/components/organisms/Statusbar.css                                                    | Create new — sibling per-component stylesheets using semantic class names bound to tokens.css custom properties; no inline styles; sidebarWidth/paneRatio driven via CSS vars                                                 |
| tokens.css theme/method-style contract | src/renderer/styles/tokens.css                                                                                                                                                                                                                                                                                      | Reuse (read-only) — shell sets data-theme + data-mstyle on <html> which tokens.css already implements; data-accent is set but visually inert (no [data-accent] block); no edits this task                                     |
| Shell component tests                  | src/renderer/src/components/organisms/**tests**/Shell.test.tsx, src/renderer/src/components/organisms/**tests**/Shell.ct.tsx                                                                                                                                                                                        | Create new — Vitest + Testing Library interaction tests and Playwright CT for divider drag/clamp, Cmd-B toggle, in-session setting survival, slot rendering, divider a11y                                                     |

## 5. Acceptance Criteria

Each AC must be testable and unambiguous. **Cover each category that applies. Mark non-applicable categories with "N/A — [reason]".**

### 5.1 Tooling / artifact presence and absence

- [x] **AC-1**: The renderer shall provide a settingsStore module under the lib directory.
  > Verification: test -f src/renderer/src/lib/settingsStore.ts
- [x] **AC-2**: The renderer shall provide a Shell organism component module under the organisms directory.
  > Verification: test -f src/renderer/src/components/organisms/Shell.tsx
- [x] **AC-3**: The renderer source shall contain no reference-export cruft markers.
  > Verification: ! grep -rEn 'data-om-|\_\_OmT|tweaks-panel' src/renderer/src

### 5.2 Behavior preservation

N/A — Greenfield shell — no prior shell/layout behavior to preserve; the App.tsx root swap is a behavior change covered in 5.3, and PrimitivesDemo is dev-only.

### 5.3 Behavior change

- [x] **AC-4**: WHEN the user drags the sidebar divider, the Shell shall resize the sidebar and clamp its width to 200-520px.
- [x] **AC-5**: WHEN the user presses Cmd-B, the Shell shall toggle the sidebar collapsed state, hiding or showing the sidebar while preserving the last sidebar width for restore on reopen.
- [x] **AC-6**: WHILE a view setting is held in the settingsStore, the Shell shall reflect data-theme, data-accent, and data-mstyle on the document root and the sidebar width and pane ratio as CSS custom properties for the duration of the session.
- [x] **AC-7**: WHEN a named mount slot is given children, the Shell shall render those children without depending on their contents.
- [x] **AC-8**: WHEN App.tsx renders, the Shell shall be the mounted renderer root in place of the PrimitivesDemo gallery.
- [x] **AC-9**: WHILE a divider has keyboard focus, the Shell shall expose the WAI-ARIA separator role with aria-valuenow and support keyboard resize.
- [x] **AC-10**: WHEN the accent value changes, the Shell shall set data-accent on the document root, producing no visual change this task.
- [x] **AC-16**: WHEN the user drags the request and response divider, the Shell shall resize the split and keep the pane ratio within its clamped range.
- [x] **AC-17**: IF the window shrinks below the clamped minimums, THEN the Shell shall re-clamp the sidebar width and the pane ratio to their valid ranges so that no pane is negative or overflows.

### 5.4 CI / pipeline

N/A — No CI pipeline changes in scope; gates run via existing npm scripts, not a new pipeline stage.

### 5.5 Hooks / gates

N/A — No new git hooks or commit gates introduced by this feature.

### 5.6 Documentation

- [x] **AC-11**: The exported Shell components, the settingsStore state and actions, and the slot prop types shall carry documentation comments.

### 5.7 Hygiene

- [x] **AC-12**: The renderer source shall pass strict type-checking.
  > Verification: npm run typecheck:web
- [x] **AC-13**: The codebase shall pass ESLint without new errors.
  > Verification: npm run lint
- [x] **AC-14**: The Shell component sources shall contain no inline style attributes.
  > Verification: ! grep -rEn 'style=[{][{]' src/renderer/src/components/organisms
- [x] **AC-15**: The Shell and settingsStore sources shall not import the electron or node modules directly.
  > Verification: ! grep -rEn "from '(electron|node:)" src/renderer/src/components/organisms src/renderer/src/lib/settingsStore.ts

## 6. Out of Scope

**Coverage rule (v3)**: For each Phase 1.5 finding, the finding either (a) becomes an AC in §5, (b) becomes a Constraint in §7, (c) is explicitly listed here as out of scope, OR (d) is in §9 Risks with documented mitigation. Unlanded finding = hard error — re-verify Phase 1.5 enumeration is complete before saving.

- NOT included: Slot CONTENTS — the sidebar tree, tab bodies, request/response editors, and modal bodies that mount into the named slots — are separate downstream tasks; the shell ships empty slots only. — F-spec-6
- NOT included: On-disk / electron-store persistence of view settings — the settingsStore is in-memory only this task; disk persistence is deferred to a later persistence-port task (wired through a typed main-process IPC, not the renderer store).
- NOT included: Defining accent palette CSS ([data-accent] selector blocks) — accent is persisted and set as data-accent but is visually inert this task; authoring accent palettes is a later task.
- NOT included: Command-palette overlay + search behavior — the titlebar exposes only a trigger button/slot; the palette itself is out of scope.
- NOT included: Environment selector, workspace pill, and account pill behavior — dropdown data, environment switching, and auth — are out of scope; these are static presentational slots this task.
- NOT included: Multi-window support — the shell is a single-window layout.
- NOT included: Keyboard shortcuts other than Cmd-B — any other shortcut belongs to its own feature.
- NOT included: Reproducing design/reference.html markup or its generated cruft (data-om-\*, \_\_OmT wrappers, inline styles, tweaks-panel) — reference is for look/behavior only.
- NOT included: Authoring or editing design-token files — the shell consumes src/renderer/styles/tokens.css and design/tokens.json as-is; no token edits.

## 7. Technical Constraints

- Must follow: The settingsStore is the single source of truth for sidebar width and pane ratio; drag handlers commit values via store actions, never by mutating state directly (constitution §5 State Management / §4 Always-Do).
- Must follow: Mirror the existing toastStore zustand shape: create(), a single module-level store instance, selector hooks for each field, and a reset for tests so component tests start from known defaults.
- Must follow: Reuse the existing renderer test stack (Vitest + @testing-library/react + user-event jsdom for interaction; Playwright CT for real-browser focus/keyboard) under **tests**/; introduce no new test infrastructure.
- Must follow: Style via semantic class names bound to tokens.css custom properties with sibling .css files; drive sidebarWidth/paneRatio through CSS custom properties; no inline styles; animations gated behind prefers-reduced-motion.
- Must follow: Implement the WAI-ARIA window-splitter pattern on each divider — role=separator with aria-valuenow/min/max, keyboard resize, and pointer-release-outside-window handling.
- Must follow: Clamp the sidebar width to 200-520px and the request/response pane ratio to 0.15-0.85 in JS, enforced both during drag and on window resize so no pane goes negative or overflows.
- Must not break: Keep contextIsolation intact and the renderer sandboxed — the settingsStore is in-memory only; later disk persistence goes through a typed main-process IPC wrapper, not the renderer store.
- Must satisfy NFR (16 ms): Divider drag must stay smooth — no setState-per-pointermove re-render storms; resize is rAF-batched and CSS-var-driven within the frame budget, with the store committed only on pointer release.
- Must follow constitution §3.1: strict is on; do not weaken it per-file. No 'any'. Type external/IPC input as 'unknown' and narrow with a type guard — the settingsStore state, actions, and slot props are fully typed.
- Must follow constitution §3.3: zustand store camelCase + Store suffix (settingsStore); React components PascalCase (Shell, Titlebar, Sidebar, PaneSplit, Statusbar, Divider).
- Must follow constitution §2.3: Renderer modules resolve through the @renderer alias; import via the alias, not deep relative paths; keep code in its process dir.
- Must follow constitution §6.3: Before writing anything generic/reusable, search for an existing utility — reuse the toastStore zustand pattern, cx(), the Icon atom, and the existing tokens.css contract rather than re-defining them.
- Must follow constitution §2.1: Renderer is sandboxed React UI; never import Node or electron directly in renderer code; the settingsStore stays renderer-side and in-memory.

## 8. Open Questions

- **Q-1**: Integration point RESOLVED (Phase 2 fit-check): the user's belief of persisting view settings 'via the existing settings store' is incorrect — no settings store exists; settingsStore is created net-new and in-memory this task, and disk persistence (electron-store/IPC) is deferred to a later persistence-port task.
- **Q-2**: Divider build-vs-buy is decided as hand-roll (zero-dep, keeps settingsStore as the single source of truth); react-resizable-panels is the documented fallback if the hand-rolled ARIA/keyboard/edge-case work proves more expensive than the derisk spike predicts — final confirmation at /plan.
- **DP-breaking_changes-1** [no DP in category breaking_changes]: no relevant decision point for breaking_changes
- **DP-tooling_configuration-1** [no DP in category tooling_configuration]: no relevant decision point for tooling_configuration

## 9. Risks

| Risk                                                                                                                                                                             | Likelihood | Impact | Mitigation                                                                                                                          |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| Hand-rolled divider accessibility (role=separator, aria-valuenow, keyboard resize, pointer-release-outside-window) is more code to get right than a library would give for free. | Med        | Med    | Derisk spike on the divider before locking the approach; axe + keyboard/SR pass; react-resizable-panels documented as the fallback. |
| Window-resize re-clamp math could yield negative or overflowing panes if the sidebar(200-520px) + pane-ratio(0.15-0.85) bounds are mis-handled on shrink.                        | Med        | Med    | Prototype the clamp/resize math against the window-shrink edge case; cover with a behavior test.                                    |
| Drag without rAF/CSS-var batching causes per-pointermove re-render storms and janky resize.                                                                                      | Med        | Low    | rAF-batched CSS-var write during drag; commit to the store only on pointer release; measure vs a setState-per-move baseline.        |
| data-accent is set but visually inert (no [data-accent] CSS), which can look wired-but-broken to a reviewer.                                                                     | Low        | Low    | Document the inert behavior in the spec/AC; accent palette CSS is an explicit later task.                                           |
| The named slot API could leak shell knowledge of slot contents, defeating the decoupling goal.                                                                                   | Low        | Med    | Mount the existing Tabs molecule into the tab slot as a content-decoupling proof; slots accept arbitrary children only.             |
| jsdom may not faithfully reproduce pointer-drag and focus fidelity for the dividers, hiding real interaction defects.                                                            | Low        | Med    | Run Playwright CT in a real browser for divider drag, keyboard resize, and focus behavior.                                          |
