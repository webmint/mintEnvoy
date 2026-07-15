# Task 011: KVTable CT regression — field + controlled modes

**Feature**: 017-body-editor-shell
**Agent**: qa-engineer
**Status**: Complete
**Depends on**: 005
**Blocks**: None
**Spec criteria**: AC-11
**Review checkpoint**: No
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/organisms/__tests__/KVTable.stories.tsx | Modify | Add a controlled-mode (`{rows,onRowsChange}`) fixture |
| src/renderer/src/components/organisms/__tests__/KVTable.ct.tsx | Modify | Extend with controlled-mode coverage; keep field-mode + `.missing` regression |

## Description

Extend the existing KVTable CT suite (already ~759 lines, covering field-mode fidelity + field independence) to prove the prop-union extension (task 005) did NOT regress field mode and that the new controlled `{rows, onRowsChange}` arm works, including the retained `validVars` `.missing` highlight. This is a targeted append, not a rewrite.

## Change Details

- In `src/renderer/src/components/organisms/__tests__/KVTable.stories.tsx`:
  - Add a controlled-mode fixture that binds `{rows, onRowsChange}` to a local harness (rows held in local state, `onRowsChange` updates them) so a controlled edit round-trips through the callback.
- In `src/renderer/src/components/organisms/__tests__/KVTable.ct.tsx`:
  - Add controlled-mode cases: a row edit calls `onRowsChange` with the next rows; the rendered rows reflect the controlled `rows` prop (not the store).
  - **AC-11 negative arm (carried from task 005 review)**: a controlled-mode edit must ALSO assert the store is NEVER written — spy on `tabsStore`'s `updateActiveSpec` (or diff the store state before/after) and assert it was NOT called during a controlled-mode edit. The positive `onRowsChange` assertion alone does not cover the "never index the store" half of AC-11.
  - Confirm field mode (`params` + `headers`) still edits via the store and renders unchanged (regression).
  - Confirm the `validVars` `.missing` highlight fixture still marks unknown tokens in both modes (F4 retained prop).

## Contracts

### Expects (checked before execution)
- KVTable accepts the `({field} | {rows, onRowsChange}) & {validVars?}` prop union (task 005).
- The existing `KVTable.ct.tsx` + `KVTable.stories.tsx` field-mode + `.missing` coverage is present.

### Produces (checked after execution)
- `KVTable.stories.tsx` exports a controlled-mode fixture.
- `KVTable.ct.tsx` covers controlled-mode edit round-trip + field-mode regression + `.missing` highlight retention.

## Done When

- [x] Controlled-mode edit calls `onRowsChange` and renders from the `rows` prop (AC-11).
- [x] Controlled-mode edit does NOT write the store — `updateActiveSpec` spy asserts zero calls (AC-11 negative arm; carried from task 005 review).
- [x] Field-mode params/headers editing is proven unchanged (regression green).
- [x] The `validVars` `.missing` highlight still fires in both modes.
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-14T12:02:33Z
**Files changed**: src/renderer/src/components/organisms/__tests__/KVTable.stories.tsx, src/renderer/src/components/organisms/__tests__/KVTable.ct.tsx
**Contract**: Expects 2/2 | Produces 2/2
**Notes**: Extended KVTable CT: +2 controlled fixtures +3 controlled tests (onRowsChange round-trip; AC-11 NEGATIVE arm via live store-params readout staying 0 = updateActiveSpec never called; validVars .missing retained in controlled mode). 26/26 CT pass. Authored main-thread (subagent CT-stall pattern). IN-SCOPE FIXES: (1) removed broken '@renderer/styles/tokens.css' import from KVTable.stories.tsx (ct-tokens-import-alias-trap) that masked the ENTIRE KVTable CT as 'did not run' since feature 014 - the latent bug flagged in task 010; (2) fixing it unmasked 2 pre-existing broken delete-focus tests (force-clicked reveal-on-hover delete button without hovering) - added .hover(), field regression now genuinely green first time. Field regression = 23 pre-existing tests all pass.
