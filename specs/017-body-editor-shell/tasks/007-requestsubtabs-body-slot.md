# Task 007: RequestSubTabs body slot

**Feature**: 017-body-editor-shell
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: None
**Blocks**: 008
**Spec criteria**: AC-3
**Review checkpoint**: No
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/organisms/RequestSubTabs.tsx | Modify | Add a `body?` slot prop + wire the `body` panel key (was falling to emptyState) |

## Description

Add a `body?: ReactNode` named slot prop to `RequestSubTabs` and wire the `body` panel key to render it, mirroring the existing `params`/`headers` slot pattern. Currently the `body` key falls through to the shared `emptyState`. All other sub-tabs (params, auth, headers, tests, code) must render exactly as before (AC-3). No sibling-organism import (§2.2) — the slot arrives as a `ReactNode` prop.

## Change Details

- In `src/renderer/src/components/organisms/RequestSubTabs.tsx`:
  - Add `body?: ReactNode` to the component's props type + doc the new prop.
  - In the panel-content branch (where `key === 'params'` → `params ?? emptyState`, `key === 'headers'` → `headers ?? emptyState`, else `emptyState`), add a `key === 'body'` → `body ?? emptyState` branch.
  - Leave scroll/focus preservation, badge derivation, and every other panel branch untouched.

## Contracts

### Expects (checked before execution)
- `RequestSubTabs` accepts `params?`/`headers?` slot props and renders `params ?? emptyState` / `headers ?? emptyState`; the `body` key currently falls to `emptyState`.
- The shared `emptyState` element and the mount-all `hidden`-toggle panel loop exist.

### Produces (checked after execution)
- `RequestSubTabs` accepts `body?: ReactNode`.
- The `body` panel renders `body ?? emptyState`.
- The params/auth/headers/tests/code panels are unchanged.

## Done When

- [x] `RequestSubTabs` accepts a `body?: ReactNode` prop and renders it in the `body` panel, falling to `emptyState` when absent.
- [x] All non-body sub-tabs render unchanged (AC-3).
- [x] No sibling-organism import added (§2.2); no inline styles.
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-11T08:07:21Z
**Files changed**: src/renderer/src/components/organisms/RequestSubTabs.tsx
**Contract**: Expects 2/2 | Produces 3/3
**Notes**: Added body?: ReactNode slot prop + else-if key==='body' branch rendering body ?? emptyState, mirroring params/headers. Non-body panels untouched (AC-3). No sibling-organism import. typecheck/lint/build clean, panel clean iteration 0.
