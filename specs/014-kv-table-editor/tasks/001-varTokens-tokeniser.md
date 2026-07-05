# Task 001: varTokens tokeniser

**Feature**: 014-kv-table-editor
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: None
**Blocks**: 003
**Spec criteria**: AC-2, AC-9, AC-12, AC-22, AC-27, AC-32, AC-33
**Review checkpoint**: No
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/lib/varTokens.ts | Create | Pure non-greedy `{{…}}` tokeniser returning ordered plain/var segments. |
| src/renderer/src/lib/__tests__/varTokens.test.ts | Create | Vitest unit suite locking the tokeniser edge rules. |

## Description

Create a pure, renderer-only, display-only tokeniser that splits a cell's text into an ordered list of plain-text and `{{variable}}` segments. It only PARSES for highlighting — it never resolves or substitutes a variable's value (resolution is spec §6 out-of-scope). It has no React/DOM dependency and imports nothing renderer-external, so it is unit-testable in isolation.

Parsing rules (all locked by unit tests):

- **Non-greedy, shortest match**: `{{a}}{{b}}` yields two var segments `a` and `b`, not one spanning `a}}{{b`. Nested `{{a{{b}}}}` takes the shortest `{{a{{b}}` → the inner content is `a{{b` (shortest closing wins).
- **Empty `{{}}`** and **unclosed `{{abc`** (no closing `}}`) are PLAIN text, not var segments (a var requires both delimiters and a non-empty inner).
- **Trimmed name**: `{{ x }}` produces a var segment whose `name` is `x` (inner text trimmed).
- **Unicode / dots / dashes allowed** in names: `{{user.id}}`, `{{user-id}}`, `{{café}}` are valid var segments — the tokeniser must NOT constrain names to `\w`.
- The same function is applied independently to key text and value text (the caller decides which cells to tokenise; the tokeniser is field-agnostic).

## Change Details

- In `src/renderer/src/lib/varTokens.ts`:
  - Export a discriminated-union segment type: `export type VarSegment = { kind: 'plain'; text: string } | { kind: 'var'; name: string }`.
  - Export `export function tokenizeVars(text: string): VarSegment[]` implementing the rules above. Adjacent plain runs may be coalesced; an empty input returns `[]` (or a single empty-plain segment — pick one and lock it in the test).
  - JSDoc on the exported type + function (AC-27).
  - No `any`; no Node/electron import (AC-32).
- In `src/renderer/src/lib/__tests__/varTokens.test.ts`:
  - Vitest cases: single var, adjacent `{{a}}{{b}}`, nested `{{a{{b}}}}` shortest-match, empty `{{}}` → plain, unclosed `{{abc` → plain, `{{ x }}` → trimmed name `x`, unicode/dot/dash names, mixed plain+var, plain-only, empty string.

## Contracts

### Expects (checked before execution)
- `src/renderer/src/lib/` exists (renderer lib leaf dir — established by feature 001).
- The Vitest + jsdom test stack is configured (feature 001; `*.test.ts` under `__tests__`).

### Produces (checked after execution)
- `varTokens.ts` exports `type VarSegment = { kind: 'plain'; text: string } | { kind: 'var'; name: string }` and `function tokenizeVars(text: string): VarSegment[]`.
- `tokenizeVars` treats empty `{{}}` and an unclosed `{{` as plain text, and trims the inner name of a valid `{{ name }}` token.
- `varTokens.test.ts` exercises empty/unclosed/nested-shortest/unicode/dot/dash + key-vs-value-independent cases and passes under `npx vitest run`.

## Done When

- [x] `tokenizeVars` and `VarSegment` are exported from `varTokens.ts` with JSDoc.
- [x] All edge-rule unit tests pass (`npx vitest run src/renderer/src/lib/__tests__/varTokens.test.ts`).
- [x] The module has no React/DOM/Node/electron import.
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-04T20:06:49Z
**Files changed**: src/renderer/src/lib/varTokens.ts, src/renderer/src/lib/__tests__/varTokens.test.ts
**Contract**: Expects 2/2 | Produces 3/3
**Notes**: Panel-clean in 2 rounds; round-1 qa Medium gap (untested whitespace-only {{   }} branch) fixed by adding tests — 16 Vitest cases, all green. Implementation unchanged across rounds.
