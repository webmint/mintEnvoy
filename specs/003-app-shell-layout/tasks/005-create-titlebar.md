# Task 005: create-titlebar

**Feature**: 003-app-shell-layout
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 001
**Blocks**: 007
**Spec criteria**: AC-5
**Review checkpoint**: No
**Context docs**: None

## Files

| File                                               | Action | Description                                                           |
| -------------------------------------------------- | ------ | --------------------------------------------------------------------- |
| src/renderer/src/components/organisms/Titlebar.tsx | Create | Presentational titlebar + sidebar-toggle button (focus-return target) |
| src/renderer/src/components/organisms/Titlebar.css | Create | Titlebar styles (semantic classes, tokens.css vars)                   |

## Description

Create the presentational titlebar: logo, workspace pill, sidebar-toggle button, command-palette trigger (button/slot only — palette behavior out of scope), environment selector, account pill. The sidebar-toggle button calls `toggleSidebar()`. It is also the focus-return target for collapse (grill F3): the button must be reachable by ref from the Shell so Shell can move focus to it when the sidebar collapses. Expose it via a forwarded ref prop `toggleRef`.

## Change Details

- Create `src/renderer/src/components/organisms/Titlebar.tsx`:
  - Props: `{ toggleRef?: Ref<HTMLButtonElement> }`.
  - Render presentational regions: logo, workspace pill, the sidebar-toggle `<button ref={toggleRef}>` (onClick → `settingsStore.getState().toggleSidebar()`, `aria-label="Toggle sidebar"`), command-palette trigger button, environment selector, account pill. These are static/presentational this task (their data + behavior are §6 out of scope).
  - JSDoc on the component + props (AC-11).
- Create `src/renderer/src/components/organisms/Titlebar.css`: semantic classes bound to tokens.css; no inline styles.

## Contracts

### Expects (checked before execution)

- `settingsStore` exposes `toggleSidebar` (task 001).

### Produces (checked after execution)

- `Titlebar` is exported from `src/renderer/src/components/organisms/Titlebar.tsx`.
- `Titlebar` accepts a `toggleRef: Ref<HTMLButtonElement>` prop that is attached to the sidebar-toggle `<button>` (the named focus-return mechanism for grill F3).
- The sidebar-toggle button's `onClick` calls `toggleSidebar()`.
- `Titlebar.css` uses semantic class names bound to tokens.css; no inline `style={{` attributes.

## Done When

- [x] Titlebar renders all six regions; the sidebar-toggle button toggles `sidebarCollapsed` via `toggleSidebar()`.
- [x] `toggleRef` is forwarded onto the sidebar-toggle `<button>` so the Shell can focus it on collapse.
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-23T19:22:55Z
**Files changed**: src/renderer/src/components/organisms/Titlebar.tsx, src/renderer/src/components/organisms/Titlebar.css
**Contract**: Expects 1/1 | Produces 4/4
**Notes**: 6-region presentational titlebar; toggle button -> toggleSidebar + toggleRef (F3). Repairs: React type imports, motion comment, placeholder comments. qa items recorded to task 011.
