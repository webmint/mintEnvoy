# Task 001: Create RequestSpec domain model

**Feature**: 004-working-tabs-state-machine
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: None
**Blocks**: 002, 003
**Spec criteria**: AC-2, AC-16, AC-28, AC-9, AC-10
**Review checkpoint**: No
**Context docs**: specs/004-working-tabs-state-machine/data-model.md

## Files

| File                                | Action | Description                                                                         |
| ----------------------------------- | ------ | ----------------------------------------------------------------------------------- |
| src/renderer/src/lib/requestSpec.ts | Create | RequestSpec/Row/Auth types, `isBearerAuth` guard, `makeBlankRequest()` seed factory |

## Description

Create the renderer-only RequestSpec domain model: the `RequestSpec`, `Row`, and `Auth` types, an `isBearerAuth` type guard, and a `makeBlankRequest()` seed factory. Every entity is a plain, JSON-serializable object — no class instances, Symbols, or functions on the data shape (actions live on the store wrapper in task 002, never here). This is the upstream contract the tabsStore slice (task 002) and its serialization test (task 003) consume.

`Auth` is a discriminated union on a literal `type` field with **exactly two members in scope** — `{ type: 'none' }` and `{ type: 'bearer'; token: string }`. Do NOT declare any third variant (basic/apikey/digest/oauth2/etc.) — those are §6 out of scope; the union is extensible but seeded with two members only. Narrow `bearer` via the `isBearerAuth` guard, never via `any` or a cast (§3.1).

`makeBlankRequest()` returns the seed default: `method='GET'`, `url=''`, `name=''`, `params=[]`, `body={lang:'',type:'',text:''}`, a single enabled `Accept: application/json` header, and `auth={ type:'bearer', token:'{{apiKey}}' }` with the `{{apiKey}}` literal verbatim. Auth is NOT mirrored into `headers[]`.

## Change Details

- In `src/renderer/src/lib/requestSpec.ts` (new):
  - Export `interface Row { enabled: boolean; key: string; value: string; description: string }`.
  - Export the `Auth` discriminated union: `type NoneAuth = { type: 'none' }`, `interface BearerAuth { type: 'bearer'; token: string }`, `type Auth = NoneAuth | BearerAuth`.
  - Export `function isBearerAuth(auth: Auth): auth is BearerAuth` returning `auth.type === 'bearer'`.
  - Export `interface RequestSpec { method: string; url: string; name: string; params: Row[]; headers: Row[]; body: { lang: string; type: string; text: string }; auth: Auth }`.
  - Export `function makeBlankRequest(): RequestSpec` returning the seed default above (Accept value reproduced from the prototype SEED at `design/reference.html:13485`; `{{apiKey}}` literal verbatim). Build a fresh object on every call (no shared mutable reference) so two blank tabs never alias the same `headers`/`params` arrays.
  - JSDoc every exported symbol (type, guard, factory) — AC-28.
  - Renderer-only: no `electron` or `node:` imports (AC-10). No inline `style={{...}}` (AC-9 — N/A in a .ts module, but the source must not introduce any).

## Contracts

### Expects (checked before execution)

- The renderer `lib/` leaf layer exists (`src/renderer/src/lib/` — siblings `settingsStore.ts`, `toastStore.ts`, `cx.ts`).
- No `requestSpec` module exists yet (greenfield create).

### Produces (checked after execution)

- `src/renderer/src/lib/requestSpec.ts` exists and exports the literal identifiers `RequestSpec`, `Row`, `Auth`, `BearerAuth`, `isBearerAuth`, `makeBlankRequest`.
- `makeBlankRequest` returns `auth` with the literal string `'{{apiKey}}'` and a single header whose `key` is `'Accept'` and `value` is `'application/json'`.
- The `Auth` union declares exactly two members (`'none'`, `'bearer'`) — no third variant.

## Done When

- [x] `src/renderer/src/lib/requestSpec.ts` exports `RequestSpec`, `Row`, `Auth`, `isBearerAuth`, `makeBlankRequest`
- [x] `makeBlankRequest()` produces the exact seed defaults (GET / empty url+name+body / Accept:application/json header / bearer `{{apiKey}}`); auth NOT mirrored into headers
- [x] `Auth` is a two-member discriminated union narrowed by `isBearerAuth`; no `any`
- [x] All exported symbols carry JSDoc (AC-28)
- [x] No `electron`/`node:` import (AC-10)
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-24T22:06:49Z
**Files changed**: src/renderer/src/lib/requestSpec.ts
**Contract**: Expects 2/2 | Produces 3/3
**Notes**: Created requestSpec.ts: Row/Auth(none|bearer)/RequestSpec types, isBearerAuth guard, makeBlankRequest factory. Seed defaults exact; fresh-object-per-call. qa round-1 coverage notes (isBearerAuth both-branches, makeBlankRequest reference-independence) resolved by widening task 003 test scope; panel clean round 2.
