# Task 002: Re-export Body types from tabsStore

**Feature**: 017-body-editor-shell
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 001
**Blocks**: 006
**Spec criteria**: AC-13
**Review checkpoint**: No
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/lib/tabsStore.ts | Modify | Re-export the body/Row types so BodyEditor never imports requestSpec directly |

## Description

Re-export the body domain types from `tabsStore.ts` so `BodyEditor` imports them from `@renderer/lib/tabsStore` rather than reaching into `requestSpec.ts` directly (AC-13 / constitution §5.2 — requestSpec stays component-invisible). No store logic, action signature, or write path changes.

## Change Details

- In `src/renderer/src/lib/tabsStore.ts`:
  - Add a type re-export of `Body`, `RawBody`, `UrlencodedBody`, `BodyType`, `RawLang`, and `Row` from `@renderer/lib/requestSpec` (e.g. `export type { Body, RawBody, UrlencodedBody, BodyType, RawLang, Row } from '@renderer/lib/requestSpec'`).
  - Leave `updateActiveSpec` and every other action untouched.

## Contracts

### Expects (checked before execution)
- `requestSpec.ts` exports `Body`, `RawBody`, `UrlencodedBody`, `BodyType`, `RawLang`, and `Row` (task 001).
- `tabsStore.ts` currently imports `RequestSpec` from `@renderer/lib/requestSpec` but re-exports none of the body/Row types.

### Produces (checked after execution)
- `tabsStore.ts` re-exports `Body`, `RawBody`, `UrlencodedBody`, `BodyType`, `RawLang`, and `Row`.
- The store's write path (`updateActiveSpec`) signature is unchanged.

## Done When

- [x] `import type { Body, RawBody, UrlencodedBody, BodyType, RawLang, Row } from '@renderer/lib/tabsStore'` type-checks (AC-13).
- [x] `updateActiveSpec` signature is byte-identical to before this task.
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-10T22:43:45Z
**Files changed**: src/renderer/src/lib/tabsStore.ts
**Contract**: Expects 2/2 | Produces 2/2
**Notes**: Added single type-only re-export of Body/RawBody/UrlencodedBody/BodyType/RawLang/Row from requestSpec; updateActiveSpec unchanged. typecheck/lint/build clean.
