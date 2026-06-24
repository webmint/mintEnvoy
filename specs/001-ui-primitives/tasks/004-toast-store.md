# Task 004: build the zustand toastStore and imperative toast() API

**Feature**: 001-ui-primitives
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 001
**Blocks**: 005
**Spec criteria**: AC-22, AC-8, AC-9, AC-10, AC-15, AC-19
**Review checkpoint**: No
**Context docs**: None

## Files

| File                               | Action | Description                                                                     |
| ---------------------------------- | ------ | ------------------------------------------------------------------------------- |
| src/renderer/src/lib/toastStore.ts | Create | Module-level zustand store + imperative `toast()` API (queue/auto/manual/pause) |

## Description

Build the toast queue: a single module-level zustand store owning a stack of transient notifications, plus an imperative `toast(message, opts)` API that enqueues via the store. State machine: enqueue → auto-dismiss after a duration; hover/focus pauses the timer; manual dismiss removes one item leaving the rest. All mutation through store actions (constitution §4); never mutate state outside actions. This `lib/` module MUST NOT import from `components/` (constitution §2.3; AC-19).

## Change Details

- In `src/renderer/src/lib/toastStore.ts`:
  - Define a zustand store with state `toasts: Toast[]` and actions `enqueue`, `dismiss(id)`, `pauseTimer(id)`, `resumeTimer(id)`.
  - Export `toast(message, opts)` that calls `toastStore.getState().enqueue(...)` — a single module-level store instance (avoid per-consumer instantiation; toast singleton risk).
  - Auto-dismiss after `opts.duration`; `pauseTimer`/`resumeTimer` back hover/focus pause.
  - Document the exported store, the `toast()` API, and the `Toast` item type (AC-15).
  - No import from `components/`; no `node`/`electron` import (AC-19).

## Contracts

### Expects (checked before execution)

- `zustand` is available (task 001 / existing dependency).

### Produces (checked after execution)

- `toastStore.ts` exports a module-level `toastStore` and a `toast(message, opts)` function.
- The store exposes `enqueue`, `dismiss`, `pauseTimer`, `resumeTimer` actions; auto-dismiss is timer-driven.
- `toast()` enqueues through a single store instance (no per-call store creation).
- No import from `components/`; no `node`/`electron` import.

## Done When

- [x] Unit test: `toast('x')` enqueues one item (AC-22); auto-dismiss removes it after its duration (AC-8)
- [x] Unit test: `pauseTimer` halts auto-dismiss while paused (AC-9); `dismiss(id)` removes only that item, leaving others (AC-10)
- [x] Exported store + `toast()` + item type documented (AC-15)
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-21T18:59:37Z
**Files changed**: src/renderer/src/lib/toastStore.ts, src/renderer/src/lib/**tests**/toastStore.test.ts
**Contract**: Expects 1/1 | Produces 4/4
**Notes**: Single module-level zustand toastStore + imperative toast() (+info/success/warning/error). enqueue/dismiss/pauseTimer/resumeTimer; auto-dismiss via setTimeout (handles in module Map, not state); pause preserves remaining. crypto.randomUUID ids. 55/55 tests incl multi-cycle pause/resume. Forward note: task 005 must render message as escaped JSX text.
