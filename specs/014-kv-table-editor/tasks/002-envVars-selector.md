# Task 002: envVars validVars selector

**Feature**: 014-kv-table-editor
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: None
**Blocks**: 003
**Spec criteria**: AC-3, AC-20, AC-27, AC-32, AC-33
**Review checkpoint**: No
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/lib/envVars.ts | Create | ∅-defaulting active-environment `validVars` selector (frozen empty `ReadonlySet`). |
| src/renderer/src/lib/__tests__/envVars.test.ts | Create | Vitest unit suite for the ∅-default + stable-identity contract. |

## Description

Create the thin boundary selector that supplies the active environment's `validVars` set. The environment store (task T14) does NOT exist yet and is spec §6 out-of-scope, so this selector is the stable SEAM the KVTable binds to: in v1 it always returns a module-level frozen EMPTY set. It must degrade gracefully (constitution §3.2) — never throw, never return `undefined`/`null`. The returned reference must be STABLE across calls (a hoisted frozen sentinel), so a zustand selector consuming it never trips an `Object.is` identity loop (R7/R12).

This is intentionally minimal — it types and stabilizes the injection point ONLY; it does NOT implement, import, or scaffold the env store (that is T14, out of scope).

## Change Details

- In `src/renderer/src/lib/envVars.ts`:
  - Hoist a module-level frozen empty set: `const EMPTY_SET: ReadonlySet<string> = Object.freeze(new Set<string>())` (or `new Set()` frozen once at module load — the point is one shared frozen instance, never a fresh set per call).
  - Export `export function envVars(): ReadonlySet<string>` returning `EMPTY_SET` in v1. JSDoc noting the T14 seam + the stable-identity contract (AC-27).
  - No `any`; no Node/electron import (AC-32); imports nothing from `components/`.
- In `src/renderer/src/lib/__tests__/envVars.test.ts`:
  - Assert `envVars()` returns an empty set (`.size === 0`).
  - Assert `envVars() === envVars()` (stable reference across calls — the anti-identity-loop guard).
  - Assert the returned set is frozen / not mutable in a way that would let a caller pollute the shared sentinel.

## Contracts

### Expects (checked before execution)
- `src/renderer/src/lib/` exists (renderer lib leaf dir).
- The Vitest test stack is configured (feature 001).

### Produces (checked after execution)
- `envVars.ts` exports `function envVars(): ReadonlySet<string>` returning a module-level frozen empty set in v1.
- Repeated calls return the SAME set reference (`envVars() === envVars()`).
- `envVars.test.ts` asserts empty + stable-identity + frozen and passes under `npx vitest run`.

## Done When

- [x] `envVars` is exported returning a frozen empty `ReadonlySet<string>` with a stable reference across calls.
- [x] Unit tests pass (`npx vitest run src/renderer/src/lib/__tests__/envVars.test.ts`).
- [x] The module never throws / returns undefined, and imports nothing from `components/` or Node/electron.
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-05T10:23:08Z
**Files changed**: src/renderer/src/lib/envVars.ts, src/renderer/src/lib/__tests__/envVars.test.ts
**Contract**: Expects 2/2 | Produces 3/3
**Notes**: Panel-clean single round. Frozen ∅-sentinel; ReadonlySet type is the compile-time immutability guard (Object.freeze-on-Set is defensive only). 3 Vitest cases green.
