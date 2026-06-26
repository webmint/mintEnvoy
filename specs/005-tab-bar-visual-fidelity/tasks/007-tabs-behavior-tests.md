# Task 007: Tabs behavior tests (byte-identical, dirty-XOR-close)

**Feature**: 005-tab-bar-visual-fidelity
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 002
**Blocks**: None
**Spec criteria**: AC-2, AC-3, AC-6, AC-9, AC-10, AC-12, AC-13
**Review checkpoint**: No
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/molecules/__tests__/Tabs.test.tsx | Modify | Add byte-identical regression, dirty-XOR-close, method-chip, keyboard-close cases |

## Description

Cover the task-002 behavior changes with Vitest + Testing Library. (These test the engineer's own feature behavior — inline-per-engineer, not a separate qa-engineer task.) Add cases:

1. **Byte-identical non-closable** — rendering `<Tabs>` WITHOUT `closable` produces no `tabs__tab-dirty`/`tabs__tab-close` node, no Delete/Backspace handler effect, and the same single roving tab stop as the 002 path (AC-2, AC-3). (This migrates/keeps the legacy 004 byte-identical regression intent.)
2. **Dirty-XOR-close** — a `closable` tab with `dirty: true` renders `tabs__tab-dirty` and NO `tabs__tab-close`; a clean tab renders `tabs__tab-close` and NO dot. Clicking the dirty dot fires `onClose` with the tab id (AC-12, AC-13).
3. **Roving integrity** — the dirty dot is not a tab stop; exactly one `tabIndex=0` tab regardless of dirty/closable (AC-3).
4. **Keyboard close on dirty** — Delete (and Backspace) on a focused dirty tab fires `onClose` (gated on `closable`, not on `dirty`) (AC-6).
5. **Method chip** — a descriptor with `method: 'GET'` renders a `.method` chip carrying the `GET` class before the label; an unknown method renders the chip without a color class.

## Change Details

- In `src/renderer/src/components/molecules/__tests__/Tabs.test.tsx`:
  - Add a `describe` for the closable dirty-XOR-close behavior with the cases above.
  - Add/keep the closable=false byte-identical regression assertions.
  - Look up close affordances by role/class (`tabs__tab-close`, `tabs__tab-dirty`) and the close `aria-label` (`Close <label>`), not by the old `✕` glyph text.

## Contracts

### Expects (checked before execution)
- Task 002 renders dirty-XOR-close (`tabs__tab-dirty` / `tabs__tab-close`), the method chip, and keeps Delete/Backspace gated on `closable`.
- The existing `Tabs.test.tsx` uses Vitest + Testing Library + user-event (jsdom).

### Produces (checked after execution)
- `Tabs.test.tsx` asserts: closable=false byte-identical (no dirty/close node, one roving stop); dirty→dot-not-close + dot-click→onClose; clean→close-not-dot; Delete/Backspace closes a dirty tab; method chip class.
- The suite passes.

## Done When

- [x] closable=false byte-identical assertions pass (AC-2, AC-3)
- [x] dirty-XOR-close + dot-click→onClose + clean-close cases pass (AC-12, AC-13)
- [x] Delete/Backspace-closes-dirty-tab case passes (AC-6)
- [x] method-chip case passes
- [x] `npx vitest run src/renderer/src/components/molecules/__tests__/Tabs.test.tsx` is green
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-26T12:09:58Z
**Files changed**: src/renderer/src/components/molecules/__tests__/Tabs.test.tsx
**Contract**: Expects 2/2 | Produces 2/2
**Notes**: 75 vitest green (+29 cases). 2 repair rounds: null-guards on dirty-dot queries, onChange-not-called on keyboard-close, Delete/Backspace×dirty/clean matrix, lowercase-method case. Non-blocking: line 1069 inline querySelector! left unguarded (structural deref, reviewer-approved).
