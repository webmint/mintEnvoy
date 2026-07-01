# Task 006: mount-requestbar-in-app-request-pane

**Feature**: 009-request-bar
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 004
**Blocks**: None
**Spec criteria**: AC-21, AC-25, AC-26, AC-27
**Review checkpoint**: Yes
**Context docs**: None

## Files

| File                     | Action | Description                                       |
| ------------------------ | ------ | ------------------------------------------------- |
| src/renderer/src/App.tsx | Modify | mount RequestBar into the Shell request-pane slot |

## Description

Wire RequestBar into the app shell by adding the `panes.request` slot to the existing `<Shell tabs={<TabBar/>} />` element. This is the integration that puts the request bar on screen — a layer-boundary crossing into app composition (review checkpoint). Trivial, one-file edit; ToastProvider/Shell/TabBar wiring otherwise unchanged.

## Change Details

- In `src/renderer/src/App.tsx`:
  - Import `RequestBar` from `@renderer/components/organisms/RequestBar`.
  - Change `<Shell tabs={<TabBar />} />` to `<Shell tabs={<TabBar />} panes={{ request: <RequestBar /> }} />` (pass `onSend` if/when a consumer exists; default no-op means it may be omitted for now).
  - Do not touch the ToastProvider/ToastViewport wiring.

## Contracts

### Expects (checked before execution)

- `RequestBar` is exported from `src/renderer/src/components/organisms/RequestBar.tsx` (task 004).
- `App.tsx` renders `<Shell tabs={<TabBar />} />` and `Shell` accepts a `panes` prop with a `request` slot (existing — `ShellPanes`).

### Produces (checked after execution)

- `App.tsx` renders `<Shell ... panes={{ request: <RequestBar ... /> }} />`, mounting RequestBar into the request pane.

## Done When

- [x] App.tsx mounts RequestBar via `panes.request` on the existing Shell element
- [x] ToastProvider/TabBar wiring unchanged
- [x] `npm run build` succeeds
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-28T12:24:18Z
**Files changed**: src/renderer/src/App.tsx, src/renderer/src/**tests**/app-toast-mount.test.tsx
**Contract**: Expects 2/2 | Produces 1/1
**Notes**: App mounts RequestBar via panes.request on the existing <Shell tabs={<TabBar/>}/>. ADDITION: AC-21 containment test in app-toast-mount.test.tsx (.request-bar within .pane-split\_\_pane--request) added in review repair — fails if the panes prop is dropped. Build green.
