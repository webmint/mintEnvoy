# Task 009: Wire TabBar into Shell tabs slot via App.tsx

**Feature**: 004-working-tabs-state-machine
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 007
**Blocks**: None
**Spec criteria**: AC-27, AC-7, AC-5, AC-6
**Review checkpoint**: No
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/App.tsx | Modify | Inject `<Shell tabs={<TabBar />} />` at the composition root (replacing the test-fixture feeder) |

## Description

Mount the real `TabBar` into Shell's existing `tabs` slot at the **composition root** — `App.tsx` — by passing `tabs={<TabBar />}` to `<Shell>`. Shell stays slot-agnostic: it does NOT import TabBar and is NOT modified (no organism→sibling-organism coupling, per Risk 2). This satisfies AC-27 (the shell renders the TabBar) while keeping the existing slot contract intact.

This is the integration step — assembling the feature into the running app. The assembled build (`npm run build`) must pass (AC-7).

## Change Details

- In `src/renderer/src/App.tsx`:
  - Import `TabBar` from `@renderer/components/organisms/TabBar`.
  - Pass `tabs={<TabBar />}` to the existing `<Shell />` element (i.e. `<Shell tabs={<TabBar />} />`).
  - Do NOT modify `Shell.tsx` — the `tabs?: ReactNode` slot already exists; Shell renders whatever it is handed.
  - Preserve the existing `ToastProvider`/`ToastViewport` structure unchanged.

## Contracts

### Expects (checked before execution)
- `TabBar` (task 007) is exported from `@renderer/components/organisms/TabBar`.
- `Shell` exposes the optional `tabs?: ReactNode` slot (feature 003, `ShellProps`).

### Produces (checked after execution)
- `src/renderer/src/App.tsx` renders `<Shell tabs={<TabBar />} />` (TabBar mounted into the shell tabs slot — AC-27).
- `Shell.tsx` is unchanged and does not import `TabBar`.
- The assembled app builds cleanly (`npm run build`) — AC-7.

## Done When

- [x] `App.tsx` passes `tabs={<TabBar />}` to `<Shell>` (AC-27)
- [x] `Shell.tsx` is NOT modified and does not import TabBar (Risk 2 — slot-agnostic)
- [x] `npm run build` passes on the assembled app (AC-7)
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-25T07:13:33Z
**Files changed**: src/renderer/src/App.tsx, src/renderer/src/__tests__/app-toast-mount.test.tsx
**Contract**: Expects 2/2 | Produces 3/3
**Notes**: App.tsx mounts <Shell tabs={<TabBar/>}/> (AC-27); Shell.tsx untouched/slot-agnostic (Risk 2). Assembled build green (AC-7), typecheck/lint clean (AC-5/6). Panel repair: added an AC-27 assertion to app-toast-mount.test.tsx (asserts a role=tablist mounts into .shell__tabs) closing the optional-prop silent-regression gap.
