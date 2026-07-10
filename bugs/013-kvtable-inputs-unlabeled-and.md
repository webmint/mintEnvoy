# Bug 013: KVTable inputs unlabeled and no focus indicator

**Status**: Open
**Severity**: Critical
**Source**: manual
**Feature**: N/A
**AC**: N/A
**Reported**: 2026-07-10
**Fixed**: 

## Description

KVTable Key/Value/Description cell inputs have no programmatic label — no aria-label and no associated <label> — so screen readers announce no accessible name (WCAG 2.1 SC 1.3.1 Info and Relationships / SC 4.1.2 Name, Role, Value). Additionally, .kv-cell input sets outline:none (KVTable.css:11) with no :focus-within fallback on the cell, so keyboard focus is invisible (SC 2.4.7 Focus Visible). Pre-existing (not introduced by feature 016; surfaced by the 016 /review accessibility audit). Suggested fix: add aria-label to each input (Key/Value/Description) and a :focus-within outline on .kv-cell. CSS in src/renderer/src/components/organisms/KVTable.css.

## Expected Behavior

_Expected behavior not specified — see spec AC._

## Actual Behavior

_Actual behavior not specified — see verification evidence._

## File(s)

| File | Detail |
|------|--------|
| src/renderer/src/components/organisms/KVTable.tsx |  |

## Evidence

Reported by user.

## Related Issues

_None — standalone bug._

## Fix Notes

_Filled in after resolution._
