# Bug 007: close-button icon contrast

**Status**: Open
**Severity**: Warning
**Source**: manual
**Feature**: N/A
**AC**: N/A
**Reported**: 2026-06-30
**Fixed**:

## Description

Tab close-button icon color var(--text-faint) #a1a1aa measures 2.31:1 on --bg-sunken #f4f3f1 and 2.56:1 on #ffffff — both fail WCAG 2.1 AA SC 1.4.11 (3:1 for non-text UI components). Pre-existing; surfaced by design-auditor during review of feature 011-tab-width-cap, not introduced by it.

## Expected Behavior

_Expected behavior not specified — see spec AC._

## Actual Behavior

_Actual behavior not specified — see verification evidence._

## File(s)

| File                                           | Detail |
| ---------------------------------------------- | ------ |
| src/renderer/src/components/molecules/Tabs.css |        |

## Evidence

Reported by user.

## Related Issues

_None — standalone bug._

## Fix Notes

_Filled in after resolution._
