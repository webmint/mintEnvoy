# Task 001: Migrate RequestSpec body to tagged record

**Feature**: 017-body-editor-shell
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: None
**Blocks**: 002, 006
**Spec criteria**: AC-4, AC-26
**Review checkpoint**: No
**Context docs**: specs/017-body-editor-shell/data-model.md

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/lib/requestSpec.ts | Modify | Body flat→tagged record + new body types; reseed `makeBlankRequest` |
| src/renderer/src/lib/__tests__/tabsStore.test.ts | Modify | Reseed old-shape body assert; add body sub-record reference-independence cases |

## Description

Migrate `RequestSpec.body` from the flat descriptor `{ lang; type; text }` to a **tagged record** `{ active, raw, urlencoded }` whose `active` field is the mode discriminant and whose `raw`/`urlencoded` sub-records are always present (so every value-bearing mode's value survives a mode switch — the grill F-001 fix backing AC-14). Add the supporting `BodyType`, `RawLang`, `RawBody`, `UrlencodedBody` types. Reseed `makeBlankRequest` to the new shape. Because the migration changes the compile-time shape, reseed the one existing test that asserts the old body shape (`tabsStore.test.ts`) in the SAME task so type-check + test stay green. Do NOT add an `isRawBody` guard — a tagged record needs no narrowing to reach `body.raw`/`body.urlencoded` (both always present); adding one would be dead code.

## Change Details

- In `src/renderer/src/lib/requestSpec.ts`:
  - Add `export type BodyType = 'none' | 'raw' | 'urlencoded' | 'form-data' | 'binary' | 'graphql'`.
  - Add `export type RawLang = 'json' | 'xml' | 'html' | 'text'`.
  - Add `export interface RawBody { lang: RawLang; text: string }` with a contract doc comment (retained raw-mode draft, persists across switches).
  - Add `export interface UrlencodedBody { rows: Row[] }` with a contract doc comment (reuses the existing `Row`).
  - Add `export interface Body { active: BodyType; raw: RawBody; urlencoded: UrlencodedBody }` with a contract doc comment explaining `active` is the discriminant and `raw`/`urlencoded` are always-present retained sub-records (AC-14); form-data/binary/graphql are payload-free `active` values (§6 OOS).
  - Change `RequestSpec.body` field type from `{ lang: string; type: string; text: string }` to `Body`; update its doc comment.
  - In `makeBlankRequest`, replace the `body` seed with `{ active: 'none', raw: { lang: 'json', text: '' }, urlencoded: { rows: [] } }`; update the seed-defaults doc block accordingly.
  - Do NOT add `isRawBody`.
- In `src/renderer/src/lib/__tests__/tabsStore.test.ts`:
  - Reseed the old-shape assertion (the `expect(spec.body).toEqual({ lang: '', type: '', text: '' })` line in the newBlank body-defaults test, currently near :232) to `expect(spec.body).toEqual({ active: 'none', raw: { lang: 'json', text: '' }, urlencoded: { rows: [] } })`.
  - Add reference-independence cases mirroring the existing headers/params/auth block: two `makeBlankRequest()` calls return distinct `body`, `body.raw`, `body.urlencoded`, and `body.urlencoded.rows` references.
  - The JSON round-trip serialization test needs no edit (every new field is a JSON primitive/array/plain-object).

## Contracts

### Expects (checked before execution)
- `RequestSpec.body` is currently the flat `{ lang: string; type: string; text: string }` in `requestSpec.ts` (near :82).
- `makeBlankRequest` seeds `body: { lang: '', type: '', text: '' }` (near :131).
- The existing `Row` interface is exported from `requestSpec.ts`.
- `tabsStore.test.ts` contains a newBlank body-defaults assertion of the old shape (near :232).

### Produces (checked after execution)
- `requestSpec.ts` exports `BodyType`, `RawLang`, `RawBody`, `UrlencodedBody`, and `Body`.
- `RequestSpec.body` is typed `Body`.
- `makeBlankRequest` returns `body: { active: 'none', raw: { lang: 'json', text: '' }, urlencoded: { rows: [] } }`.
- No `isRawBody` symbol exists.
- `tabsStore.test.ts` asserts the tagged-record body seed and includes body/`body.raw`/`body.urlencoded`/`body.urlencoded.rows` reference-independence cases.

## Done When

- [x] `Body`, `BodyType`, `RawLang`, `RawBody`, `UrlencodedBody` are exported from `requestSpec.ts`, each interface carrying a contract doc comment (AC-26).
- [x] `makeBlankRequest().body.active === 'none'` and the seed deep-equals the tagged-record shape (AC-4).
- [x] `tabsStore.test.ts` passes against the new seed shape and the added reference-independence cases pass.
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-10T22:40:23Z
**Files changed**: src/renderer/src/lib/requestSpec.ts, src/renderer/src/lib/__tests__/tabsStore.test.ts
**Contract**: Expects 4/4 | Produces 5/5
**Notes**: Flat body descriptor migrated to tagged record {active,raw,urlencoded}; makeBlankRequest reseeded; isRawBody omitted per design (dead code); test reseeded + 4 reference-independence cases. typecheck/lint/build clean, 45 tests pass.
