# Feature Summary: 003-app-shell-layout

**Status**: Complete · **Verdict**: APPROVED (`/verify`) · **Date**: 2026-06-24

## What was built

A single-window application shell and layout for the mintEnvoy desktop HTTP client. The app now opens into a real framed workspace — a titlebar across the top, a resizable sidebar on the left, a stacked request/response split in the middle, and a status bar along the bottom — replacing the old primitives-gallery placeholder. The user can drag the sidebar edge to resize it, drag the divider between request and response to rebalance the split, and press **Cmd-B** (or Ctrl-B) to collapse/restore the sidebar. Theme, accent, and method-style preferences are applied live to the whole window, and all layout dimensions persist for the session. The slots (sidebar, tabs, panes, modals) are empty mount points ready for later features to fill.

## Changes

- **Settings store** — a single in-memory source of truth for theme, accent, method-style, sidebar width, pane ratio, and collapsed state, with bounded clamp helpers (guarded against non-finite input).
- **Divider** — a hand-rolled, accessible resize handle (WAI-ARIA window-splitter: `role="separator"`, `aria-valuenow`, keyboard resize) driving live CSS-variable updates during drag, committing the clamped value on release.
- **Sidebar / PaneSplit** — the resizable sidebar (200–520px) and the request/response split (ratio 0.15–0.85), each mounting a Divider wired to the store; collapsing the sidebar unmounts it cleanly.
- **Titlebar / Statusbar** — a six-region titlebar (logo, workspace, command palette, env selector, account) with the sidebar-toggle button, and a presentational status footer (`role="status"`) — both styled to the design reference.
- **Shell** — composes the four organisms behind typed named slots, mirrors store state onto `<html>` (data-attributes + CSS variables), and owns the imperative behaviors: window-resize re-clamp, global Cmd-B toggle, and focus-return to the toggle on collapse.
- **App + window** — the Shell mounts as the renderer root inside the preserved toast substrate; the main-process window gained `minWidth: 720` as the OS-level floor for the no-overflow guarantee.
- **Tests** — 244 Vitest interaction tests across all organisms plus an App-level toast-routing regression; a Playwright CT suite (real-browser drag/capture/focus) also runs (92 CT tests pass after clearing a stale build cache).

## Files changed

31 files, +5565 / −34. Source (18 files):

- `src/renderer/src/lib/` — `settingsStore.ts`
- `src/renderer/src/components/organisms/` — `Shell`, `Titlebar`, `Sidebar`, `PaneSplit`, `Divider`, `Statusbar` (`.tsx` + `.css` each)
- `src/renderer/src/components/organisms/__tests__/` — `Shell.test.tsx`, `Shell.ct.tsx`, `Shell.stories.tsx`
- `src/renderer/src/App.tsx` — Shell wired in as root
- `src/main/index.ts` — BrowserWindow `minWidth: 720`

Plus the feature record under `specs/003-app-shell-layout/` (spec, plan, grill, tasks, review, verification) and a `.devforge` memory entry.

## Key decisions

- **New `components/organisms/` tier** below molecules — the shell frame is its own atomic-design layer, importing downward only.
- **`settingsStore` mirrors the `toastStore` shape** — single module-level zustand instance, selectors, in-memory SSOT (no persistence this feature).
- **Store → `<html>`** — one Shell effect writes `data-theme`/`data-accent`/`data-mstyle`; another writes `--sidebar-width` (px) and `--pane-ratio` (unitless) to `document.documentElement` — the same target the Divider writes during drag, so there is one CSS-var contract, not two.
- **Dividers drive layout via rAF-batched CSS-var writes during drag**, committing the clamped value to the store on release (no React state churn per pointer-move).
- **Clamp authority in JS** (sidebar 200–520px, ratio 0.15–0.85), re-applied on window resize; the main-process `minWidth: 720` is the complementary OS floor.
- **Cmd-B collapses to hidden while preserving the last sidebar width** for restore on reopen.
- **Typed named-slot API** — sidebar/tabs/panes/modals are optional `ReactNode` props the Shell renders without inspecting their contents.

## Deviations from plan

- **Divider px-vs-ratio (task 004, user-caught)** — the divider added a raw pixel delta to the unitless pane ratio (the "jumps/disappears" bug). Fixed by adding a `unit` prop (default `px`) and a `getDragExtent` px→ratio conversion; PaneSplit passes `unit=''`.
- **CSS-var write target (task 002)** — drag-time writes target `document.documentElement` (shared with the Shell's committed writes) to avoid a shadowing mismatch flagged at grill.
- **Task 010 agent** — reassigned `backend-engineer` → `frontend-engineer` (no backend stack exists; `src/main` is the Electron main process, owned by the app builder).
- **Post-implement fixes** (folded in via `/fix`, all gated): clamp NaN guard + idempotent CSS-var write + cross-organism consistency (6 review findings), and 8 CSS visual-fidelity corrections to match `design/styles.css` (fonts, account avatar, divider hover/height, pane border). The Statusbar-slot finding was deferred to a future `/specify` (adds API surface beyond the spec).

## Acceptance criteria

All 17 PASS (verified by `/verify`, mode `tests`):

- [x] AC-1 settingsStore module · [x] AC-2 Shell module · [x] AC-3 no cruft markers
- [x] AC-4 sidebar drag clamp 200–520px · [x] AC-5 Cmd-B toggle (preserves width) · [x] AC-6 store→`<html>` attrs + CSS vars
- [x] AC-7 named slots render children · [x] AC-8 Shell is App root (no PrimitivesDemo) · [x] AC-9 ARIA separator + keyboard resize
- [x] AC-10 accent → data-accent · [x] AC-16 pane drag clamp 0.15–0.85 · [x] AC-17 window-resize re-clamp (+ OS minWidth floor)
- [x] AC-11 doc comments · [x] AC-12 strict type-check · [x] AC-13 ESLint clean · [x] AC-14 no inline styles · [x] AC-15 no electron/node imports
