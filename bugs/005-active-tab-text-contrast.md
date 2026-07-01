# Bug 005: active-tab text contrast

**Status**: Open
**Severity**: Warning
**Source**: manual
**Feature**: N/A
**AC**: N/A
**Reported**: 2026-06-30
**Fixed**:

## Description

Active-tab label color renders var(--accent) #10b981 — contrast 2.29:1 on --bg-sunken #f4f3f1 and 2.54:1 on the active-tab #ffffff wrapper, both failing WCAG 2.1 AA SC 1.4.3 (4.5:1 for 12.5px text). Also diverges from design-fidelity-contract §5, which prescribes .tab.active { color: var(--text) } = #18181b. Pre-existing; surfaced by design-auditor during review of feature 011-tab-width-cap but not introduced by it.

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
