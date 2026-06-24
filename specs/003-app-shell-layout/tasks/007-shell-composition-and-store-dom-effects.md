# Task 007: shell-composition-and-store-dom-effects

**Feature**: 003-app-shell-layout
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 003, 004, 005, 006
**Blocks**: 008
**Spec criteria**: AC-2, AC-3, AC-6, AC-7, AC-10, AC-11, AC-14, AC-15
**Review checkpoint**: Yes
**Context docs**: docs/renderer/architecture.md

## Files

| File                                            | Action | Description                                                                              |
| ----------------------------------------------- | ------ | ---------------------------------------------------------------------------------------- |
| src/renderer/src/components/organisms/Shell.tsx | Create | Shell composition + typed named slots + store→`<html>` effect + CSS-var write            |
| src/renderer/src/components/organisms/Shell.css | Create | Shell grid/layout; semantic classes bound to tokens.css; `prefers-reduced-motion` gating |

## Description

Create the Shell organism — the structural substrate of the shell. It composes Titlebar + Sidebar + PaneSplit + Statusbar into the window layout, exposes the four typed named mount slots, and mirrors the store to the DOM: a single effect writes `data-theme`/`data-accent`/`data-mstyle` on `<html>`, and the Shell writes `--sidebar-width`/`--pane-ratio` as CSS custom properties on its own root. This task is the structural + store→DOM layer ONLY; the imperative behaviors (window-resize re-clamp, Cmd-B, focus-return) are task 008 on top of this surface. Styling: semantic classes bound to tokens.css, no inline styles.

## Change Details

- Create `src/renderer/src/components/organisms/Shell.tsx`:
  - Props (typed named slots): `{ sidebar?: ReactNode; tabs?: ReactNode; panes?: { request?: ReactNode; response?: ReactNode }; modals?: ReactNode }`. Shell renders each slot into its mount point and never inspects contents (AC-7).
  - Compose `<Titlebar>`, `<Sidebar>{sidebar}</Sidebar>`, `<PaneSplit request={...} response={...}>`, `<Statusbar>`, plus a `modals` mount point. Pass `tabs` into the appropriate region.
  - Read `theme`/`accent`/`mstyle`/`sidebarWidth`/`paneRatio` via settingsStore selectors.
  - A single `useEffect` subscribed to `theme`/`accent`/`mstyle` writes `document.documentElement.dataset.theme/accent/mstyle` (effect is the only writer; attributes overwritten, not stacked). `data-accent` is set but visually inert this task (no `[data-accent]` CSS) (AC-10).
  - Write `--sidebar-width` (px) and `--pane-ratio` from the store onto `document.documentElement` (`<html>`) — the SAME element the Divider writes during live drag (grill/review: a Shell-own-root var would SHADOW the `<html>` value the Divider writes mid-drag, freezing live drag; co-locating both on `<html>` alongside the data-theme/data-accent/data-mstyle attributes resolves it). Set the custom properties via `style.setProperty`, not arbitrary inline visual styles (AC-6).
  - Hold a `toggleRef` and pass it to `<Titlebar toggleRef={toggleRef} />` (the ref is consumed by task 008's focus-return; created here as part of composition).
  - JSDoc on the component + slot prop types (AC-11).
- Create `src/renderer/src/components/organisms/Shell.css`: CSS grid for titlebar/sidebar/main/statusbar; consumes `--sidebar-width`/`--pane-ratio`; semantic classes bound to tokens.css; `@media (prefers-reduced-motion: reduce)` gating; NO inline styles, NO reference-export cruft (no `data-om-*`, `__OmT`, `tweaks-panel`).

## Contracts

### Expects (checked before execution)

- `Sidebar` (003), `PaneSplit` (004), `Titlebar` accepting `toggleRef` (005), `Statusbar` (006) are exported.
- `settingsStore` exposes `theme`, `accent`, `mstyle`, `sidebarWidth`, `paneRatio` (task 001).

### Produces (checked after execution)

- `Shell` is exported from `src/renderer/src/components/organisms/Shell.tsx`.
- `Shell` accepts typed named slots `sidebar`, `tabs`, `panes`, `modals` and renders them without inspecting contents.
- An effect writes `document.documentElement.dataset.theme`, `.accent`, and `.mstyle` from the store.
- `Shell` sets `--sidebar-width` and `--pane-ratio` custom properties on its root from the store.
- `Shell` creates a `toggleRef` and passes it to `<Titlebar toggleRef=...>`.
- Shell source + `Shell.css` contain no inline `style={{` visual attributes and no `data-om-*`/`__OmT`/`tweaks-panel` cruft.

## Done When

- [x] Shell composes the four organisms into the layout and renders the four named slots without inspecting contents.
- [x] The store→`<html>` effect sets `data-theme`/`data-accent`/`data-mstyle`; `--sidebar-width`/`--pane-ratio` set on the Shell root.
- [x] `toggleRef` is created and passed to Titlebar.
- [x] No inline styles; no reference-export cruft; animations gated behind `prefers-reduced-motion`.
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-23T19:42:52Z
**Files changed**: src/renderer/src/components/organisms/Shell.tsx, src/renderer/src/components/organisms/Shell.css
**Contract**: Expects 2/2 | Produces 6/6
**Notes**: Shell composes 4 organisms + typed named slots; store->html dataset effect + --sidebar-width(px)/--pane-ratio(bare) on documentElement; toggleRef -> Titlebar. Hygiene: removed cast, nullish tabs guard. qa granularity -> task 011.
