# Task 010: Register closable Tabs variant in PrimitivesDemo

**Feature**: 004-working-tabs-state-machine
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 004
**Blocks**: None
**Spec criteria**: AC-22
**Review checkpoint**: No
**Context docs**: None

## Files

| File                                           | Action | Description                                                                               |
| ---------------------------------------------- | ------ | ----------------------------------------------------------------------------------------- |
| src/renderer/src/components/PrimitivesDemo.tsx | Modify | Register a `closable` Tabs variant (and/or TabBar) for dev-only manual visual fidelity QA |

## Description

Add a dev-only gallery entry exercising the closable Tabs variant (from task 004) so the close affordance can be visually checked against `design/reference.html`. This is a manual-QA surface — the same dev-only, production-tree-shaken `PrimitivesDemo` gallery the other primitives use. It provides the visual fidelity check for the closable affordance (AC-22) that the structural tests cannot.

## Change Details

- In `src/renderer/src/components/PrimitivesDemo.tsx`:
  - Extend the existing `TabsSection` (or add a sibling demo row) with a `Tabs` instance rendered with `closable` enabled and an `onClose` handler (e.g. dropping the closed id from local demo state) plus a `+` actions-slot control, so the ✕ close control and dirty marker are visible for manual fidelity inspection.
  - Keep the existing request/response Tabs demo rows intact.
  - Respect the existing dev-only guard (`import.meta.env.DEV`) — the addition must remain tree-shaken from production builds. No inline styles.

## Contracts

### Expects (checked before execution)

- The closable/onClose Tabs contract from task 004 is present (`TabsProps.closable`, `TabsProps.onClose`, sibling ✕).
- `PrimitivesDemo.tsx` exists with the existing `TabsSection` and the `import.meta.env.DEV` guard.

### Produces (checked after execution)

- `PrimitivesDemo.tsx` renders a `closable`-enabled Tabs variant (with `onClose` + `+` control) in the dev-only gallery for manual fidelity QA (supports AC-22).
- The existing demo rows remain; the addition stays behind the dev-only guard.

## Done When

- [x] a `closable`-enabled Tabs variant (with `onClose` + `+` control) is registered in the dev gallery
- [x] existing PrimitivesDemo rows remain intact and the dev-only guard is respected
- [x] no inline styles added
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-25T07:19:03Z
**Files changed**: src/renderer/src/components/PrimitivesDemo.tsx
**Contract**: Expects 2/2 | Produces 2/2
**Notes**: Added 'Closable tabs (x + dirty marker)' demo row to TabsSection: <Tabs closable onClose .../> with local state, + control, neighbor-on-active-close, dirty-dot badge. Dev-only guard preserved, prod tree-shakes it. Existing rows untouched. Panel clean round 0. Supports AC-22 manual fidelity QA.
