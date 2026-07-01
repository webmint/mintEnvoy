# Task 002: Create tabsStore zustand slice

**Feature**: 004-working-tabs-state-machine
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 001
**Blocks**: 003, 007
**Spec criteria**: AC-1, AC-4, AC-13, AC-14, AC-15, AC-16, AC-17, AC-18, AC-19, AC-20, AC-21, AC-28, AC-9, AC-10
**Review checkpoint**: No
**Context docs**: specs/004-working-tabs-state-machine/data-model.md

## Files

| File                              | Action | Description                                                                            |
| --------------------------------- | ------ | -------------------------------------------------------------------------------------- |
| src/renderer/src/lib/tabsStore.ts | Create | zustand slice `{ tabs, activeTabId }` + 5 actions + never-zero/neighbor/dedupe helpers |

## Description

Create the `tabsStore` zustand slice — the working-tabs lifecycle state machine. Mirror the in-repo convention exactly (`settingsStore.ts`/`toastStore.ts`): a single module-level `create<TabsState>((set) => ...)` instance, camelCase + `Store` suffix (§3.3), state mutated only through actions. Hold a flat `{ tabs: Tab[]; activeTabId: string }` where **array order IS tab order** (§7, Option A — no normalized map).

`Tab = { id; collectionRequestId: string | null; spec: RequestSpec; dirty: boolean }`. `id` via `crypto.randomUUID()` (browser global — NOT `node:crypto`, §2.1) at every tab-create site. `collectionRequestId` is the dedupe-leg-1 key (distinct from `id`); `null` for new-blank tabs.

Actions: `openFromCollection(input: OpenFromCollectionInput)`, `newBlank()`, `close(tabId)`, `selectActive(tabId)`, `markClean(tabId)`. Extract small helpers (dedupe-match, neighbor-selection) to keep each action under ~40 lines (§3.6). Handle both paths (§3.2): `close`/`markClean`/`selectActive` on an unknown id are defensive no-ops (no throw, no empty catch).

The store initializes with one seeded blank tab so the never-zero invariant holds from construction (no empty state ever).

## Change Details

- In `src/renderer/src/lib/tabsStore.ts` (new):
  - Import `RequestSpec`, `makeBlankRequest` from `@renderer/lib/requestSpec` (alias, §2.3 — never a deep relative path).
  - Export `interface Tab { id: string; collectionRequestId: string | null; spec: RequestSpec; dirty: boolean }`.
  - Export `interface OpenFromCollectionInput { collectionRequestId: string; spec: RequestSpec }`.
  - Export `interface TabsState { tabs: Tab[]; activeTabId: string; openFromCollection: (input: OpenFromCollectionInput) => void; newBlank: () => void; close: (tabId: string) => void; selectActive: (tabId: string) => void; markClean: (tabId: string) => void }`.
  - Export `const tabsStore = create<TabsState>((set) => ({ ... }))`.
  - Initial state: one fresh `makeBlankRequest()`-wrapped Tab (`dirty:false`, `collectionRequestId:null`, fresh uuid); `activeTabId` set to that tab's id.
  - `openFromCollection`: two-leg dedupe — leg 1 match `input.collectionRequestId === tab.collectionRequestId` (both non-null); leg 2 fall through to exact verbatim non-empty `input.spec.url === tab.spec.url` (an empty url never matches, so blank tabs stay distinct, AC-15). On a hit, set `activeTabId` to the matched tab (no append, AC-13/AC-14). On a miss, append a new Tab carrying `input.collectionRequestId` + `input.spec` (`dirty:false`, fresh uuid) and activate it.
  - `newBlank`: append a Tab wrapping `makeBlankRequest()` (`collectionRequestId:null`, `dirty:false`, fresh uuid) and activate it (AC-16).
  - `close`: remove the tab by id. If the closed tab was active and others remain, set `activeTabId` to the right neighbor (else the left when the closed tab was last in order) — AC-18. **Closing a non-active tab leaves `activeTabId` unchanged** (neighbor logic scoped strictly to the active-closed branch). If it was the last remaining tab, spawn a fresh seeded `makeBlankRequest()` Tab and activate it so `tabs.length >= 1` always (never-zero, AC-17). Clean and dirty tabs close through the SAME unconditional path — a dirty tab is dropped silently, no confirm (AC-19).
  - `selectActive`: set `activeTabId` to the given id when it references an open tab; no-op otherwise (AC-21).
  - `markClean`: set the matching tab's `dirty` to `false`, leaving all other tabs unchanged; no-op on an unknown id (AC-20).
  - JSDoc the store, every action, and the exported types (AC-28).
  - Reuses the existing `zustand` dependency — introduce no new state-management library (AC-4).
  - Renderer-only: no `electron`/`node:` import (AC-10); `lib/` imports nothing from `components/` (§2.3). No inline `style={{...}}` (AC-9).

## Contracts

### Expects (checked before execution)

- `requestSpec.ts` (task 001) exports `RequestSpec` and `makeBlankRequest`.
- `zustand` is declared in `package.json` (existing dependency; `settingsStore.ts`/`toastStore.ts` use `create`).

### Produces (checked after execution)

- `src/renderer/src/lib/tabsStore.ts` exports `tabsStore`, `Tab`, `OpenFromCollectionInput`, `TabsState`.
- `tabsStore` exposes the literal action names `openFromCollection`, `newBlank`, `close`, `selectActive`, `markClean`.
- `tabsStore.getState().tabs.length >= 1` at construction (never-zero seeded init).
- `Tab` carries `collectionRequestId` (matched by dedupe leg 1, distinct from `id`).

## Done When

- [x] `tabsStore` is a module-level `create<TabsState>` instance with `{ tabs, activeTabId }` + the 5 actions
- [x] `openFromCollection` dedupes by `collectionRequestId` first, then verbatim non-empty `url`; empty url never matches (AC-13/14/15)
- [x] `newBlank` appends a `makeBlankRequest()` seed tab; auth not mirrored into headers (AC-16)
- [x] `close` honors never-zero spawn + right-then-left neighbor on active-close, and leaves `activeTabId` unchanged on non-active-close (AC-17/18)
- [x] dirty and clean tabs close through one unconditional path (AC-19); `markClean`/`selectActive` correct + no-op on unknown id (AC-20/21)
- [x] tab ids via `crypto.randomUUID()`; no `node:`/`electron` import; `lib/` imports no `components/` (AC-10, §2.3)
- [x] exported store/actions/types carry JSDoc (AC-28)
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-24T22:24:13Z
**Files changed**: src/renderer/src/lib/tabsStore.ts
**Contract**: Expects 2/2 | Produces 4/4
**Notes**: Created tabsStore: flat {tabs,activeTabId} + 5 actions + 4 pure helpers. Two-leg dedupe (empty-url-never-matches), never-zero atomic spawn, right-then-left neighbor, non-active-close leaves activeTabId unchanged, crypto.randomUUID. qa round-1 test-scope gaps (close unknown-id no-op, dedupe leg precedence) folded into task 003 scope; panel clean round 2.
