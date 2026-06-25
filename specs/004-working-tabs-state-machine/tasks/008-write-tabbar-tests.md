# Task 008: Write TabBar tests

**Feature**: 004-working-tabs-state-machine
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 007
**Blocks**: None
**Spec criteria**: AC-24, AC-25, AC-26
**Review checkpoint**: No
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/organisms/__tests__/TabBar.test.tsx | Create | Render/select/close/new-blank + label precedence + dirty marker |

## Description

Write the Vitest + Testing Library suite for the TabBar organism (task 007). Follow the established renderer test convention (co-located `__tests__/`, `.test.tsx`, jsdom). Reset `tabsStore` to a known state between tests so the module-level singleton does not leak across cases.

## Change Details

- In `src/renderer/src/components/organisms/__tests__/TabBar.test.tsx` (new):
  - Gesture routing — activating a tab calls `selectActive`; clicking a tab's ✕ calls `close`; clicking `+` calls `newBlank` (AC-24). Assert against store state changes (or spies on the actions).
  - Label precedence — a tab with a non-empty `name` labels by name; an empty-name tab with a non-empty `url` labels `method + ' ' + url`; an empty-name empty-url tab labels `Untitled` — all verbatim, no interpolation (AC-25).
  - Dirty marker — a dirty tab renders a marker alongside its label (via the badge slot) without replacing the label text; a clean tab renders no marker (AC-26).

## Contracts

### Expects (checked before execution)
- `TabBar` (task 007) is exported and composes the closable Tabs primitive wired to `tabsStore`.
- The renderer Vitest + Testing Library stack is configured (feature 001).

### Produces (checked after execution)
- `src/renderer/src/components/organisms/__tests__/TabBar.test.tsx` exists with cases covering gesture routing, label precedence, and the dirty marker.
- The TabBar suite passes.

## Done When

- [x] activate→`selectActive`, ✕→`close`, +→`newBlank` routing asserted (AC-24)
- [x] label precedence name→method+url→`Untitled` asserted verbatim (AC-25)
- [x] dirty marker alongside label (not replacing it) asserted; clean tab has none (AC-26)
- [x] suite passes under vitest
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-25T06:53:40Z
**Files changed**: src/renderer/src/components/organisms/__tests__/TabBar.test.tsx
**Contract**: Expects 2/2 | Produces 2/2
**Notes**: TabBar.test.tsx 14/14. AC-24 gesture routing (activate/close/newBlank + active-tab close->right-neighbor + already-active click no-op + collectionRequestId:null seed), AC-25 all 3 label-precedence branches verbatim, AC-26 dirty/clean marker. Singleton store reset in beforeEach. Panel repair: added the two active-tab routing cases qa flagged + collectionRequestId assertion.
