# Task 003: create-sidebar

**Feature**: 003-app-shell-layout
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 001, 002
**Blocks**: 007
**Spec criteria**: AC-4, AC-5
**Review checkpoint**: No
**Context docs**: None

## Files

| File                                              | Action | Description                                                          |
| ------------------------------------------------- | ------ | -------------------------------------------------------------------- |
| src/renderer/src/components/organisms/Sidebar.tsx | Create | Resizable left sidebar shell + sidebar mount slot + vertical Divider |
| src/renderer/src/components/organisms/Sidebar.css | Create | Sidebar styles incl. collapsed state; `--sidebar-width` consumption  |

## Description

Create the resizable left-sidebar region. It consumes the `--sidebar-width` CSS custom property for its width, renders the `sidebar` mount slot (arbitrary children, contents out of scope), and mounts the vertical `Divider` wired to `setSidebarWidth`. When `sidebarCollapsed` is true, the sidebar AND its Divider are UNMOUNTED (conditional render, NOT `width:0`/`display:none`) so the focusable separator leaves the a11y tree cleanly and Arrow-key resize cannot mutate a hidden sidebar.

## Change Details

- Create `src/renderer/src/components/organisms/Sidebar.tsx`:
  - Props: `{ children?: ReactNode }` (the sidebar mount slot).
  - Read `sidebarCollapsed` + `sidebarWidth` via settingsStore selectors.
  - When `sidebarCollapsed` is true → render nothing (component returns `null` or the parent omits it); when false → render the sidebar container + the vertical `Divider`.
  - Mount `Divider` with `orientation="vertical"`, `value={sidebarWidth}`, `min={SIDEBAR_MIN}`, `max={SIDEBAR_MAX}`, `cssVar="--sidebar-width"`, `onCommit={settingsStore.getState().setSidebarWidth}`, `ariaLabel="Resize sidebar"`.
  - JSDoc on the component + props (AC-11).
- Create `src/renderer/src/components/organisms/Sidebar.css`: `.sidebar { width: var(--sidebar-width); }` + semantic classes bound to tokens.css; no inline styles.

## Contracts

### Expects (checked before execution)

- `settingsStore` exposes `sidebarWidth`, `sidebarCollapsed`, `setSidebarWidth` (task 001).
- `Divider` is exported and clamps internally before `onCommit` (task 002).

### Produces (checked after execution)

- `Sidebar` is exported from `src/renderer/src/components/organisms/Sidebar.tsx`.
- `Sidebar` renders its `children` into the sidebar mount slot without inspecting their contents.
- `Sidebar` mounts the vertical `Divider` wired to `setSidebarWidth` only while not collapsed; both unmount when `sidebarCollapsed` is true.
- `Sidebar.css` consumes `var(--sidebar-width)`; no inline `style={{` attributes.

## Done When

- [x] Sidebar width tracks `--sidebar-width`; dragging its Divider clamps to 200-520px and commits via `setSidebarWidth`.
- [x] When `sidebarCollapsed` is true the sidebar + its Divider are unmounted (not hidden via CSS).
- [x] The sidebar mount slot renders arbitrary children.
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-23T17:22:53Z
**Files changed**: src/renderer/src/components/organisms/Sidebar.tsx, src/renderer/src/components/organisms/Sidebar.css
**Contract**: Expects 2/2 | Produces 4/4
**Notes**: Collapse via early return null (unmounts sidebar+Divider); vertical Divider wired to setSidebarWidth; consumes --sidebar-width from documentElement. qa edge cases recorded to task 011.
