# Task 004: create-panesplit

**Feature**: 003-app-shell-layout
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 001, 002
**Blocks**: 007
**Spec criteria**: AC-16
**Review checkpoint**: No
**Context docs**: None

## Files

| File                                                | Action | Description                                                    |
| --------------------------------------------------- | ------ | -------------------------------------------------------------- |
| src/renderer/src/components/organisms/PaneSplit.tsx | Create | Request/response split + pane mount slots + horizontal Divider |
| src/renderer/src/components/organisms/PaneSplit.css | Create | Pane-split styles; `--pane-ratio` consumption                  |

## Description

Create the main-area request/response split. It consumes the `--pane-ratio` CSS custom property to size the two panes, renders the `request` and `response` mount slots (arbitrary children, contents out of scope), and mounts the horizontal `Divider` wired to `setPaneRatio`. The divider clamps the ratio to 0.15-0.85.

## Change Details

- Create `src/renderer/src/components/organisms/PaneSplit.tsx`:
  - Props: `{ request?: ReactNode; response?: ReactNode }` (the two pane mount slots).
  - Read `paneRatio` via a settingsStore selector.
  - Render the request pane, the horizontal `Divider`, and the response pane; the panes size from `var(--pane-ratio)`.
  - Mount `Divider` with `orientation="horizontal"`, `value={paneRatio}`, `min={PANE_MIN}`, `max={PANE_MAX}`, `cssVar="--pane-ratio"`, `onCommit={settingsStore.getState().setPaneRatio}`, `ariaLabel="Resize request and response panes"`.
  - JSDoc on the component + props (AC-11).
- Create `src/renderer/src/components/organisms/PaneSplit.css`: panes sized via `var(--pane-ratio)`; semantic classes bound to tokens.css; no inline styles.

## Contracts

### Expects (checked before execution)

- `settingsStore` exposes `paneRatio`, `setPaneRatio`, `PANE_MIN`, `PANE_MAX` (task 001).
- `Divider` is exported and clamps internally before `onCommit` (task 002).

### Produces (checked after execution)

- `PaneSplit` is exported from `src/renderer/src/components/organisms/PaneSplit.tsx`.
- `PaneSplit` renders its `request` and `response` slots without inspecting their contents.
- `PaneSplit` mounts the horizontal `Divider` wired to `setPaneRatio`.
- `PaneSplit.css` consumes `var(--pane-ratio)`; no inline `style={{` attributes.

## Done When

- [x] The split sizes from `--pane-ratio`; dragging its Divider clamps to 0.15-0.85 and commits via `setPaneRatio`.
- [x] The request and response mount slots render arbitrary children.
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-23T19:07:19Z
**Files changed**: src/renderer/src/components/organisms/PaneSplit.tsx, src/renderer/src/components/organisms/PaneSplit.css, src/renderer/src/components/organisms/Divider.tsx
**Contract**: Expects 2/2 | Produces 4/4
**Notes**: Stacked split, flex from unitless --pane-ratio. Fixed Divider px-on-unitless-var bug: added Divider unit prop (default px), PaneSplit passes unit='' (user-confirmed). Sidebar unchanged.
