# Bug 008: missing main landmark

**Status**: Open
**Severity**: Warning
**Source**: manual
**Feature**: N/A
**AC**: N/A
**Reported**: 2026-06-30
**Fixed**:

## Description

No <main> element or role=main exists in the rendered DOM, so screen-reader users cannot skip to primary content (WCAG 2.1 AA SC 2.4.1, Level A). Pre-existing app-shell gap; surfaced by design-auditor during review of feature 011-tab-width-cap, not introduced by it.

## Expected Behavior

_Expected behavior not specified — see spec AC._

## Actual Behavior

_Actual behavior not specified — see verification evidence._

## File(s)

| File                                        | Detail |
| ------------------------------------------- | ------ |
| src/renderer/src/components/organisms/shell |        |

## Evidence

Reported by user.

## Related Issues

_None — standalone bug._

## Fix Notes

_Filled in after resolution._
