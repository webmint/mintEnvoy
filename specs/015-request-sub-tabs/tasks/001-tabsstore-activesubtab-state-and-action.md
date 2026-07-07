# Task 001: tabsStore activeSubTab state and action

**Feature**: 015-request-sub-tabs
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: None
**Blocks**: 003
**Spec criteria**: AC-4, AC-7, AC-8, AC-16, AC-19, AC-20, AC-21
**Review checkpoint**: No
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/lib/tabsStore.ts | Modify | Add `SubTabKey` union + `VALID_KEYS`; add `activeSubTab` field (default `'params'`) to the `Tab` record, seeded in BOTH `makeBlankTab` and `makeCollectionTab`; add `setActiveSubTab(tabId, key)` action |
| src/renderer/src/lib/__tests__/tabsStore.test.ts | Create | Unit test `setActiveSubTab` (per-tab set, key validation, unknown-id no-op) + additive-field defaults |

## Description

Extend the tabs store with per-request-tab sub-tab state (D2). Add a `SubTabKey` string-literal union and a `VALID_KEYS` runtime array, put an `activeSubTab: SubTabKey` field (default `'params'`) on the `Tab` record — seeded in BOTH tab constructors — and add a `setActiveSubTab(tabId, key)` action that validates the key, no-ops on an unknown `tabId`, and isolates the write to the one tab (mirroring the existing `markClean`/`selectActive`/`updateActiveSpec` no-op + per-tab-map convention). This is the state backbone RequestSubTabs (003) reads and writes; it must not disturb the existing TabBar/RequestBar consumers (AC-4).

## Change Details

- In `src/renderer/src/lib/tabsStore.ts`:
  - Add and export `type SubTabKey = 'params' | 'auth' | 'headers' | 'body' | 'tests' | 'code'` with a doc comment (AC-19).
  - Add and export `const VALID_KEYS: readonly SubTabKey[] = ['params','auth','headers','body','tests','code']` (consumed by 003's normalization).
  - Add `activeSubTab: SubTabKey` to the `Tab` interface with a doc comment.
  - Seed `activeSubTab: 'params'` in `makeBlankTab()` (tabsStore.ts:138) AND `makeCollectionTab()` (tabsStore.ts:153) — both construct a `Tab`, so both need the field or the type breaks.
  - Add `setActiveSubTab(tabId: string, key: SubTabKey): void` to the `TabsState` interface (with doc comment, AC-19) and implement it in `create<TabsState>(...)`: no-op when `tabId` matches no tab (mirror `markClean`); no-op when `key` is not in `VALID_KEYS`; otherwise `set` a new `tabs` array replacing only the matched tab's `activeSubTab` (per-tab isolation, all other tabs propagated unchanged).
- In `src/renderer/src/lib/__tests__/tabsStore.test.ts`:
  - Test a fresh tab defaults `activeSubTab === 'params'`.
  - Test `setActiveSubTab(activeTabId, 'headers')` sets only that tab's key and leaves other tabs' `activeSubTab` unchanged.
  - Test `setActiveSubTab('nonexistent', 'body')` is a no-op.
  - Test an out-of-union key is rejected (no-op) — cast through `unknown` to exercise the runtime guard.

## Contracts

### Expects (checked before execution)
- `Tab`, `makeBlankTab`, `makeCollectionTab`, and `TabsState` are declared in `src/renderer/src/lib/tabsStore.ts`.
- The store's existing actions (`markClean`, `selectActive`, `updateActiveSpec`) use the unknown-id no-op + per-tab-map pattern.

### Produces (checked after execution)
- `SubTabKey` is exported from `tabsStore.ts`.
- `VALID_KEYS` is exported from `tabsStore.ts`.
- `Tab` carries an `activeSubTab` field; `makeBlankTab` and `makeCollectionTab` both seed it to `'params'`.
- `setActiveSubTab` appears in `tabsStore.ts` as a `TabsState` action, validates the key, and no-ops on an unknown `tabId`.
- `tabsStore.test.ts` covers `setActiveSubTab` set / unknown-id no-op / invalid-key no-op.

## Done When

- [x] `SubTabKey`, `VALID_KEYS`, `Tab.activeSubTab`, and `setActiveSubTab` exist and are documented in `tabsStore.ts`.
- [x] Both `makeBlankTab` and `makeCollectionTab` seed `activeSubTab: 'params'`.
- [x] `tabsStore.test.ts` passes (set, per-tab isolation, unknown-id no-op, invalid-key no-op).
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-06T10:37:35Z
**Files changed**: src/renderer/src/lib/tabsStore.ts, src/renderer/src/lib/__tests__/tabsStore.test.ts, src/renderer/src/__tests__/fixtures/requestSpec.ts
**Contract**: Expects 2/2 | Produces 5/5
**Notes**: Also seeded activeSubTab in makeCollectionTab + the makeTab test fixture (every Tab constructor must seed the additive field). QA round-1 test gaps closed in a repair pass.
