# Task 006: create-statusbar

**Feature**: 003-app-shell-layout
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: None
**Blocks**: 007
**Spec criteria**: AC-2
**Review checkpoint**: No
**Context docs**: None

## Files

| File                                                | Action | Description                                          |
| --------------------------------------------------- | ------ | ---------------------------------------------------- |
| src/renderer/src/components/organisms/Statusbar.tsx | Create | Presentational bottom statusbar                      |
| src/renderer/src/components/organisms/Statusbar.css | Create | Statusbar styles (semantic classes, tokens.css vars) |

## Description

Create the presentational bottom statusbar region of the shell. Static/presentational this task — its content surface is for downstream features; the shell only provides the region. Styling via semantic classes bound to tokens.css, no inline styles.

## Change Details

- Create `src/renderer/src/components/organisms/Statusbar.tsx`:
  - Props: `{ children?: ReactNode }` (optional content region).
  - Render a `<footer>`/`<div role="status">`-style bar with semantic classes; render `children` if provided.
  - JSDoc on the component + props (AC-11).
- Create `src/renderer/src/components/organisms/Statusbar.css`: semantic classes bound to tokens.css; no inline styles.

## Contracts

### Expects (checked before execution)

- `cx()` is available at `src/renderer/src/lib/cx.ts`.
- The organisms directory exists (created by an earlier organisms task or this one).

### Produces (checked after execution)

- `Statusbar` is exported from `src/renderer/src/components/organisms/Statusbar.tsx`.
- `Statusbar.css` uses semantic class names bound to tokens.css; no inline `style={{` attributes.

## Done When

- [x] `Statusbar` renders a bottom bar styled from tokens.css; renders optional children.
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-23T19:31:57Z
**Files changed**: src/renderer/src/components/organisms/Statusbar.tsx, src/renderer/src/components/organisms/Statusbar.css
**Contract**: Expects 2/2 | Produces 2/2
**Notes**: Presentational footer role=status + children slot. qa items recorded to task 011.
