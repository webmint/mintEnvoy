# Task 002: define the project-owned icon set and lookup

**Feature**: 001-ui-primitives
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 001
**Blocks**: 003
**Spec criteria**: AC-1, AC-13, AC-21, AC-19
**Review checkpoint**: No
**Context docs**: None

## Files

| File                                       | Action | Description                                                         |
| ------------------------------------------ | ------ | ------------------------------------------------------------------- |
| src/renderer/src/components/atoms/icons.ts | Create | Project-owned typed icon-path set + `IconName` string-literal union |
| src/renderer/src/lib/icons-glue.ts         | Create | `resolveIcon(name)` lookup with safe fallback for unknown name      |

## Description

Create the data + lookup foundation for the Icon component: a project-owned SVG path set (the existing ~40 icons, 16x16 viewBox, 1.5px stroke) keyed by a typed `IconName` union, plus a thin `resolveIcon` helper that returns a safe fallback for an unknown name. This is the typed contract every Icon render depends on. No icon-library dependency (constitution §7).

## Change Details

- In `src/renderer/src/components/atoms/icons.ts`:
  - Define `ICONS` as a record mapping each icon name to its inline SVG path data.
  - Derive `export type IconName = keyof typeof ICONS` (typed string-literal union — no bare `string`, constitution §3.1).
- In `src/renderer/src/lib/icons-glue.ts`:
  - Export `resolveIcon(name: string)` returning the matched path data for a known `IconName`, or a documented fallback for an unknown name (never throws).
  - Import the icon data via the `@renderer` alias. This `lib/` module MUST NOT import from `components/` (constitution §2.3 dependency direction; AC-19).

## Contracts

### Expects (checked before execution)

- `src/renderer/src/components/atoms/` and `src/renderer/src/lib/` are creatable (greenfield; no existing icon module).

### Produces (checked after execution)

- `icons.ts` exports `ICONS` and a typed `IconName` union covering the project icon set.
- `icons-glue.ts` exports `resolveIcon` that returns a fallback for an unknown name and never throws.
- `icons-glue.ts` contains no import from `components/` (dependency-direction guard).

## Done When

- [x] `IconName` is a typed union (no bare `string`); `resolveIcon` returns a fallback for an unknown name
- [x] Unit test: `resolveIcon('__nonexistent__')` returns the fallback without throwing (AC-13)
- [x] `atoms/` directory now exists (AC-21)
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-21T17:15:00Z
**Files changed**: src/renderer/src/components/atoms/icons.ts, src/renderer/src/lib/icons-glue.ts, src/renderer/src/lib/**tests**/icons-glue.test.ts
**Contract**: Expects 1/1 | Produces 3/3
**Notes**: 41 icons extracted from design export (clean path data); IconName typed union; resolveIcon uses Object.hasOwn type guard + frozen non-throwing fallback. 8/8 tests.
