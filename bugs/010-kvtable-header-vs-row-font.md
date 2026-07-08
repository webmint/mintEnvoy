# Bug 010: KVTable header vs row font color perceived mismatch

**Status**: Open
**Severity**: Info
**Source**: manual
**Feature**: N/A
**AC**: N/A
**Reported**: 2026-07-06
**Fixed**: 

## Description

User reports the header vs row font-color relationship in KVTable does not match the intended design. Live inspection: header text is --text-faint (gray), key cells --text (near-black), value cells --text-muted (medium gray), header font-weight 600 — all of which MATCH the checked-in design spec design/styles.css §.kv (lines 951-1035). Not a code-vs-spec defect; the checked-in design/styles.css may differ from the intended mockup. Needs confirmed target header/row colors (and weight) to act on.

## Expected Behavior

_Expected behavior not specified — see spec AC._

## Actual Behavior

_Actual behavior not specified — see verification evidence._

## File(s)

| File | Detail |
|------|--------|
| src/renderer/src/components/organisms/KVTable.css |  |

## Evidence

Reported by user.

## Related Issues

_None — standalone bug._

## Fix Notes

_Filled in after resolution._
