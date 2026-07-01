# Task 002: add-tabsstore-updateactivespec-action

**Feature**: 009-request-bar
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 001 (ordering — keeps the lib type state consistent; not a hard symbol dependency)
**Blocks**: 004
**Spec criteria**: AC-4, AC-9, AC-10, AC-23, AC-30
**Review checkpoint**: No
**Context docs**: None

## Files

| File                                             | Action | Description                                               |
| ------------------------------------------------ | ------ | --------------------------------------------------------- |
| src/renderer/src/lib/tabsStore.ts                | Modify | add `updateActiveSpec(patch)` action + extend `TabsState` |
| src/renderer/src/lib/**tests**/tabsStore.test.ts | Modify | add `updateActiveSpec` unit cases                         |

## Description

Add the missing spec-edit write path to the tab store: a generic `updateActiveSpec(patch: Partial<RequestSpec>)` action that shallow-merges the patch into the active tab's spec and sets `dirty=true` — but ONLY when a value actually changes. This is the action RequestBar writes method+url through (constitution §4: mutate state only via store actions). Existing lifecycle actions (openFromCollection/newBlank/close/selectActive/markClean) are untouched.

## Change Details

- In `src/renderer/src/lib/tabsStore.ts`:
  - Add `updateActiveSpec: (patch: Partial<RequestSpec>) => void` to the `TabsState` interface, with JSDoc.
  - Implement in the `create<TabsState>` body: resolve the active tab via `activeTabId` internally (callers pass no tab id); compute the merged spec `{ ...tab.spec, ...patch }`; if the merge changes no value vs the current spec, return without setting state (no dirty flip, no re-render churn); otherwise replace that tab with `{ ...tab, spec: merged, dirty: true }`, leaving all other tabs unchanged.
  - Import `RequestSpec` type from `./requestSpec` (store may import the data module per §5.2 — only _components_ may not).
- In `src/renderer/src/lib/__tests__/tabsStore.test.ts`:
  - Add cases: (a) `updateActiveSpec({url})` on a clean tab sets that tab dirty and updates url; (b) a no-op patch equal to the current value does NOT flip dirty; (c) the write targets only the active tab — other tabs' specs and dirty flags are unchanged.

## Contracts

### Expects (checked before execution)

- `tabsStore` exposes `tabs: Tab[]`, `activeTabId: string`, and `markClean(tabId)` (existing state — spec §2).
- `RequestSpec` type is importable from `./requestSpec`.

### Produces (checked after execution)

- `TabsState` declares `updateActiveSpec(patch: Partial<RequestSpec>): void`.
- `updateActiveSpec` sets the active tab `dirty=true` on a value-changing patch and leaves `dirty` unchanged on a no-op patch.
- `tabsStore.test.ts` contains assertions for dirty-on-change, no-op-no-flip, and per-tab isolation.

## Done When

- [x] `updateActiveSpec` merges into the active tab spec and flips dirty only on actual change
- [x] No-op patch (same values) leaves dirty untouched
- [x] Existing tabsStore actions unchanged (openFromCollection/newBlank/close/selectActive/markClean)
- [x] `npx vitest run src/renderer/src/lib/__tests__/tabsStore.test.ts` passes
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-28T10:19:53Z
**Files changed**: src/renderer/src/lib/tabsStore.ts, src/renderer/src/lib/**tests**/tabsStore.test.ts
**Contract**: Expects 2/2 | Produces 3/3
**Notes**: updateActiveSpec: internal active-tab resolution, .every() no-op guard (dirty only on real change), per-tab immutable merge. 35 tabsStore tests (4 added in review repair: mixed-key, field-preservation, unknown-tab, empty-patch).
