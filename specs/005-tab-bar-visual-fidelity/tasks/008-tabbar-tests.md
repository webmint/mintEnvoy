# Task 008: TabBar tests (migrate badge assertions, actions row)

**Feature**: 005-tab-bar-visual-fidelity
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 004
**Blocks**: None
**Spec criteria**: AC-4, AC-5, AC-20
**Review checkpoint**: No
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/organisms/__tests__/TabBar.test.tsx | Modify | Migrate the legacy ● badge assertions; add method-chip, dot-click, chevron cases |

## Description

Update the TabBar suite for the task-004 changes. The existing suite has a `describe('AC-26 — dirty marker (● badge)')` block asserting the unicode `'●'` badge — that is feature **004's** AC-26 (a 004 assertion being migrated), NOT 005's AC-26 (ESLint). Migrate those assertions:

1. **Dirty marker migration** — replace the `'●'` badge assertions with `tabs__tab-dirty`/`tabs__tab-close` assertions: a dirty tab renders the dot (not the `'●'` badge) and the label text is still present (AC-4 — dirty surfaced without replacing the label); clicking the dirty dot routes to the store `close` action.
2. **Method chip** — a tab whose spec method is set renders the leading `.method` chip.
3. **Static chevron** — the actions row renders the `+` new-tab button and the static "More tabs" chevron; clicking the chevron does nothing (no overflow behavior) (AC-20).
4. **deriveLabel preserved** — keep/confirm the existing AC-5 label-precedence assertions pass unchanged.

## Change Details

- In `src/renderer/src/components/organisms/__tests__/TabBar.test.tsx`:
  - Rewrite the `AC-26 — dirty marker (● badge)` block to assert `.tabs__tab-dirty` presence + label-text presence + dot-click→`close`, dropping the `'●'` text assertions.
  - Add a method-chip render assertion and a static-chevron assertion (present, click is a no-op).
  - Keep the label-precedence (004 AC-25) assertions.

## Contracts

### Expects (checked before execution)
- Task 004 maps `method`/`dirty` into the descriptor, removed the `'●'` badge, and added the `+`/spacer/chevron actions row.
- The existing `TabBar.test.tsx` has a `describe` asserting the `'●'` dirty badge.

### Produces (checked after execution)
- `TabBar.test.tsx` asserts the dirty dot (`tabs__tab-dirty`) + retained label text + dot-click→store `close`, with no `'●'` badge assertions remaining.
- Method-chip and static-chevron assertions exist; the label-precedence assertions still pass.
- The suite passes.

## Done When

- [x] No `'●'` badge assertions remain; dirty marker asserted via `tabs__tab-dirty` with the label text still present (AC-4)
- [x] Dot-click routes to the store `close` action
- [x] Method-chip + static-chevron (no-op click) assertions pass (AC-20)
- [x] Label-precedence assertions unchanged and green
- [x] The TabBar Vitest suite is green
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-26T12:47:50Z
**Files changed**: src/renderer/src/components/organisms/__tests__/TabBar.test.tsx
**Contract**: Expects 2/2 | Produces 2/2
**Notes**: Migrated badge→dot; suite fixed (TabBar.test 26 green, full project 336 green). 2 repair rounds: active-dirty dot-click neighbor test, scoped chip query, and a label-element assertion fixing a chip-confounded method+url precedence check.
