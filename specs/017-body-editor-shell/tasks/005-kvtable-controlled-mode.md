# Task 005: KVTable controlled-mode prop union

**Feature**: 017-body-editor-shell
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: None
**Blocks**: 008, 011
**Spec criteria**: AC-11
**Review checkpoint**: No
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/organisms/KVTable.tsx | Modify | Add a controlled `{rows,onRowsChange}` prop arm alongside the field-bound arm |

## Description

Extend `KVTable` so it can be driven either by the existing store-bound `field` arm (`'params'`/`'headers'`) OR by a controlled `{rows, onRowsChange}` arm (for x-www-form-urlencoded mode, wired at App root — task 008). The retained optional `validVars?` prop (gating the `.missing` highlight) applies to both arms. Field mode must stay fully preserved — this is a discriminated-prop extension, NOT a rewrite; the existing params/headers behavior is protected by CT regression (task 011).

## Change Details

- In `src/renderer/src/components/organisms/KVTable.tsx`:
  - Change the props type to `({ field: 'params' | 'headers' } | { rows: readonly Row[]; onRowsChange: (r: Row[]) => void }) & { validVars?: ReadonlySet<string> }`.
  - Runtime-narrow the two arms via `'rows' in props` (NOT a type-level XOR / `?:never` — see plan §3.1; exclusivity is enforced at runtime, every call site passes exactly one shape).
  - In the `rows`/`onRowsChange` dispatcher (`writeRows`), add an early-return that calls `props.onRowsChange(nextRows)` in controlled mode BEFORE the `field === 'params'` branch.
  - Guard the store-read `rows` selector so `tab.spec[field]` is indexed ONLY in field mode; in controlled mode the rows come from `props.rows`.
  - Keep the `validVars` default (`envVars()`) behavior and the `.missing` highlight gate intact.
  - Do NOT refactor KVTable's pre-existing `import type { Row } from '@renderer/lib/requestSpec'` (out of scope; type-only erases at compile — plan D4).

## Contracts

### Expects (checked before execution)
- KVTable currently takes `{ field: 'params' | 'headers'; validVars? }`, reads rows from the store selector over `tab.spec[field]`, and dispatches via the `writeRows` function.
- `Row` is importable (existing type-only import).

### Produces (checked after execution)
- KVTable's props are the discriminated union `({field} | {rows, onRowsChange}) & { validVars? }`.
- `writeRows` early-returns through `props.onRowsChange` in controlled mode; the store-read selector is reached only in field mode.
- Field mode (`'params'`/`'headers'`) behavior is unchanged.

## Done When

- [x] `KVTable` accepts either `{ field }` or `{ rows, onRowsChange }`, narrowed by `'rows' in props`, with `validVars?` on both arms.
- [x] In controlled mode, a row edit calls `props.onRowsChange` and never indexes `tab.spec[field]` (AC-11).
- [x] In field mode, params/headers editing is byte-behavior-identical (verified by task 011 regression).
- [x] No `any` and no cast introduced (§3.1).
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-11T07:22:35Z
**Files changed**: src/renderer/src/components/organisms/KVTable.tsx
**Contract**: Expects 2/2 | Produces 3/3
**Notes**: KVTable props -> discriminated union ({field}|{rows,onRowsChange})&{validVars?}, narrowed via 'rows' in props. Both tabsStore hooks kept unconditional (selector returns frozen EMPTY_ROWS in controlled mode). writeRows early-returns via onRowsChange before store dispatch. Field mode byte-identical. 1 review-panel repair round added writeRows JSDoc documenting AC-11 negative invariant. AC-11 negative-arm spy requirement appended to tasks 008+011 briefs.
