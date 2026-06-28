# Task 001: add-httpmethods-source-and-retype-method

**Feature**: 009-request-bar
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: None
**Blocks**: 002, 004
**Spec criteria**: AC-2, AC-5, AC-22, AC-23, AC-29
**Review checkpoint**: No
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/lib/httpMethods.ts | Create | `METHODS` const (7 methods, display order) + `HttpMethod` type |
| src/renderer/src/lib/requestSpec.ts | Modify | re-point `method` from `string` to `HttpMethod` imported from httpMethods |

## Description

Establish a single source of truth for the HTTP method list and its type, then re-point the RequestSpec model's `method` field to it. This is the type contract every downstream task depends on (the method Dropdown items, the `updateActiveSpec` patch, and the `onSend` payload all reference `HttpMethod`). Doing the create + re-point in one task avoids a transient state where two method types coexist (plan risk: "lift the type into httpMethods and re-point in one change").

## Change Details

- Create `src/renderer/src/lib/httpMethods.ts`:
  - `export const METHODS = ['GET','POST','PUT','PATCH','DELETE','OPTIONS','HEAD'] as const` — array order IS the Dropdown display order.
  - `export type HttpMethod = (typeof METHODS)[number]`.
  - Pure const+type module: NO imports of any component or store; no Node/Electron imports. Document both exports with JSDoc.
- In `src/renderer/src/lib/requestSpec.ts`:
  - `import type { HttpMethod } from './httpMethods'` (or `@renderer/lib/httpMethods`).
  - Change `RequestSpec.method` from `method: string` to `method: HttpMethod`.
  - Leave `makeBlankRequest()` unchanged — its `method: 'GET'` seed is a valid `HttpMethod` member.

## Contracts

### Expects (checked before execution)
- `src/renderer/src/lib/requestSpec.ts` exports `interface RequestSpec` whose `method` field is typed `string`.
- No `HttpMethod` type and no `METHODS` constant exist anywhere in `src/renderer/`.

### Produces (checked after execution)
- `src/renderer/src/lib/httpMethods.ts` exports a `METHODS` const containing the 7 methods and a `HttpMethod` type.
- `src/renderer/src/lib/requestSpec.ts` imports `HttpMethod` from httpMethods and `RequestSpec.method` is typed `HttpMethod`.
- `makeBlankRequest` still returns a spec whose `method` is `'GET'`.

## Done When

- [x] `httpMethods.ts` exports `METHODS` (7 entries, GET-first) and `HttpMethod`
- [x] `RequestSpec.method` is `HttpMethod`; `makeBlankRequest` GET seed type-checks
- [x] `httpMethods.ts` imports nothing renderer-external (lib-leaf)
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-28T09:39:25Z
**Files changed**: src/renderer/src/lib/httpMethods.ts, src/renderer/src/lib/requestSpec.ts
**Contract**: Expects 2/2 | Produces 3/3
**Notes**: Created httpMethods.ts (METHODS+HttpMethod); re-pointed RequestSpec.method string->HttpMethod. Note: Tabs.tsx KNOWN_METHODS duplicate left for follow-up (out of scope).
