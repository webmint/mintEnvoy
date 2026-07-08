# Bug 009: KVTable checkbox not dark-gray custom style

**Status**: Open
**Severity**: Warning
**Source**: manual
**Feature**: N/A
**AC**: N/A
**Reported**: 2026-07-06
**Fixed**: 

## Description

KVTable row checkboxes render as native Chromium checkboxes (appearance:auto); accent-color:var(--accent) only tints the checked fill green, so the unchecked box is the browser default (light), not the dark-gray custom checkbox the design intends. Neither design/styles.css §.kv nor KVTable.css implements a custom unchecked appearance — this is an unimplemented design detail, newly visible since 015 mounted KVTable live. Needs the exact design target (dark-gray border? filled box? which token) before fixing.

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
