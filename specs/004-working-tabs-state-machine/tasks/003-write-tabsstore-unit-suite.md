# Task 003: Write tabsStore unit suite + serialization contract

**Feature**: 004-working-tabs-state-machine
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 002
**Blocks**: None
**Spec criteria**: AC-8, AC-13, AC-14, AC-15, AC-16, AC-17, AC-18, AC-19, AC-20, AC-21
**Review checkpoint**: No
**Context docs**: specs/004-working-tabs-state-machine/data-model.md

## Files

| File                                             | Action | Description                                                                                             |
| ------------------------------------------------ | ------ | ------------------------------------------------------------------------------------------------------- |
| src/renderer/src/lib/**tests**/tabsStore.test.ts | Create | Vitest unit suite: every lifecycle action + dirty/markClean + invariants + Q-2 JSON round-trip contract |

## Description

Write the Vitest unit suite that gates the tabsStore slice and pins the RequestSpec serialization contract. Follow the established renderer test convention (Vitest + jsdom, co-located under `__tests__/`, `.test.ts`) used by feature 001/002/003. Reset the store to a known state between tests (re-seed `tabsStore.setState` or use a fresh initial snapshot) so tests do not leak the module-level singleton state.

Cover every lifecycle action and invariant, and pin the Q-2 cross-task serialization contract (Risk 3) so the out-of-scope persistence task does not force rework: assert `JSON.parse(JSON.stringify(spec))` deep-equals `spec` for a `makeBlankRequest()` spec.

## Change Details

- In `src/renderer/src/lib/__tests__/tabsStore.test.ts` (new):
  - `openFromCollection` — leg-1 dedupe by `collectionRequestId` activates the existing tab, appends nothing (AC-13); leg-2 dedupe by verbatim non-empty `url` activates the existing tab, appends nothing (AC-14); two empty-url tabs stay distinct (AC-15); a genuine miss appends + activates and stores `collectionRequestId` so the next call matches leg 1.
  - `openFromCollection` leg PRECEDENCE — with two open tabs where tab A matches the input by `collectionRequestId` (leg 1) and tab B matches the same input by verbatim `url` (leg 2), the input activates tab A (leg 1 wins), NOT tab B. Guards against a leg-order swap silently activating the wrong tab.
  - `newBlank` — appends a tab with seed defaults (GET / empty url+name+body / `dirty:false` / bearer `{{apiKey}}` / single enabled Accept:application/json header) and does NOT mirror auth into `headers[]` (AC-16).
  - `close` — never-zero: closing the last tab spawns a fresh seeded GET so `tabs.length` stays >= 1 (AC-17); active-close selects the right neighbor, or left when the closed tab was last (AC-18); **closing a non-active tab leaves `activeTabId` unchanged** (dedicated test, per data-model invariant); dirty and clean tabs both close through the same path with no confirm (AC-19); **`close` on an unknown id is a no-op** (no throw, no state mutation — the third defensive no-op alongside `selectActive`/`markClean`).
  - `markClean` — clears the target tab's `dirty` and leaves all other tabs unchanged (AC-20); no-op on an unknown id.
  - `selectActive` — sets `activeTabId` to an open id (AC-21); no-op on an unknown id.
  - Serialization (Q-2) — `JSON.parse(JSON.stringify(makeBlankRequest()))` deep-equals `makeBlankRequest()` (plain-serializable; pins the persistence cross-task contract).
  - `isBearerAuth` guard (both branches) — `isBearerAuth({ type: 'bearer', token: 't' })` is `true` and `isBearerAuth({ type: 'none' })` is `false` (the only runtime narrowing path for the auth union; guards against a `!== 'none'` vs `=== 'bearer'` regression).
  - `makeBlankRequest` reference-independence — two successive `makeBlankRequest()` calls return structurally-independent objects (`a.headers !== b.headers`, `a.params !== b.params`, `a.auth !== b.auth`); pins the no-shared-mutable-reference invariant so a DRY "optimization" to a shared seed constant cannot silently alias tab state.

## Contracts

### Expects (checked before execution)

- `tabsStore` (task 002) exports the store + `Tab`/`OpenFromCollectionInput`/`TabsState`, with all 5 actions.
- `makeBlankRequest` (task 001) is importable for the seed + serialization assertions.
- The renderer Vitest stack (vitest + @testing-library) is configured (feature 001).

### Produces (checked after execution)

- `src/renderer/src/lib/__tests__/tabsStore.test.ts` exists with `describe`/`it` blocks covering AC-13 through AC-21 and the JSON round-trip.
- `npx vitest run src/renderer/src/lib/__tests__/tabsStore.test.ts` passes (AC-8).

## Done When

- [x] Every lifecycle action + dirty/markClean + invariants is covered (AC-13–AC-21)
- [x] Two-leg dedupe (collectionRequestId then verbatim url) and empty-url-stays-distinct are asserted
- [x] `activeTabId`-unchanged-on-non-active-close has a dedicated test
- [x] dedupe leg precedence asserted (leg-1 `collectionRequestId` match wins over a different leg-2 `url`-matching tab)
- [x] `close` on an unknown id is asserted to be a no-op
- [x] Q-2 serialization round-trip (`JSON.parse(JSON.stringify(spec))` deep-equals `spec`) is pinned
- [x] `isBearerAuth` is asserted for both branches (true for bearer, false for none)
- [x] `makeBlankRequest()` reference-independence asserted (successive calls return non-aliased headers/params/auth)
- [x] `npx vitest run src/renderer/src/lib/__tests__/tabsStore.test.ts` passes (AC-8)
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-24T23:07:35Z
**Files changed**: src/renderer/src/lib/**tests**/tabsStore.test.ts
**Contract**: Expects 3/3 | Produces 2/2
**Notes**: 28-test Vitest suite, all green. Covers AC-13..21 + leg-precedence + unknown-id no-ops + serialization round-trip + isBearerAuth both-branches + makeBlankRequest reference-independence. Round-1 panel repair (genuine): removed §3.1 as-cast on JSON.parse, added params:[] + full-state-invariance assertions + dirty-non-active test, dropped redundant afterEach. AC-8 verified by direct vitest run (28 passed).
