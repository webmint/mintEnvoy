# Task 006: Record Tabs contract extension in feature-002 lineage

**Feature**: 004-working-tabs-state-machine
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 004
**Blocks**: None
**Spec criteria**: AC-29
**Review checkpoint**: No
**Context docs**: specs/002-tabs-primitive/spec.md

## Files

| File                             | Action | Description                                                                       |
| -------------------------------- | ------ | --------------------------------------------------------------------------------- |
| specs/002-tabs-primitive/spec.md | Modify | Record the opt-in `closable`/`onClose` contract extension in the 002 spec lineage |

## Description

The feature-002 Tabs primitive was specified as selection-only. Task 004 gives it an opt-in interactive close affordance — a real, backward-compatible contract change. AC-29 requires this be **recorded in the feature-002 spec lineage as a contract change**, not left as a silent prop addition. Add a short lineage note to `specs/002-tabs-primitive/spec.md` pointing at feature 004 and describing the extension and its backward-compatibility guarantee.

This is a documentation-only edit — no source code changes. It runs after task 004 so the contract it records is settled.

## Change Details

- In `specs/002-tabs-primitive/spec.md`:
  - Add a clearly-marked lineage / contract-change note (e.g. a `## Contract Lineage` or equivalent section, or an addendum near the relevant AC) stating: feature `004-working-tabs-state-machine` extended the Tabs primitive with opt-in, default-off `closable`/`onClose` props (sibling `tabIndex={-1}` ✕ + Delete/Backspace close path); the extension is backward-compatible by construction (`closable=false` keeps the 002 selection-only path byte-identical, proven by the AC-11/AC-12 regression in feature 004); cite feature 004's spec/plan as the source of the change.
  - Do not alter the original 002 acceptance criteria text — append the lineage record, preserving the original spec.

## Contracts

### Expects (checked before execution)

- The closable/onClose contract from task 004 is implemented (so the lineage note records a real, settled change).
- `specs/002-tabs-primitive/spec.md` exists.

### Produces (checked after execution)

- `specs/002-tabs-primitive/spec.md` contains a lineage note recording the feature-004 `closable`/`onClose` contract extension as a backward-compatible contract change (AC-29).

## Done When

- [x] `specs/002-tabs-primitive/spec.md` carries a lineage note recording the closable/onClose contract extension (AC-29)
- [x] the note cites feature 004 and states the default-off backward-compatibility guarantee
- [x] original 002 acceptance-criteria text is preserved (append-only)
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-25T06:12:42Z
**Files changed**: specs/002-tabs-primitive/spec.md
**Contract**: Expects 2/2 | Produces 1/1
**Notes**: Appended '## 10. Contract Lineage' to specs/002-tabs-primitive/spec.md (append-only) recording the feature-004 closable/onClose extension + backward-compat guarantee + AC-22/AC-23 citations. Panel repair: corrected a wrong AC citation (AC-24 -> AC-22 for the keyboard close path). AC-29 satisfied.
