# Bug 015: Titlebar left section overflows at 720px min width

**Status**: Open
**Severity**: Warning
**Source**: manual
**Feature**: N/A
**AC**: N/A
**Reported**: 2026-07-10
**Fixed**: 

## Description

At the Electron-enforced 720px minimum window width, the titlebar left section (measured ~258px) overflows its 180px '1fr' grid column — the workspace name has no truncation rule (no text-overflow:ellipsis / min-width:0 / overflow:hidden), so it pushes the layout instead of clipping. Pre-existing (not introduced by feature 016; surfaced by the 016 /review responsive audit). Suggested fix: add min-width:0 to the grid column/flex item and text-overflow:ellipsis + overflow:hidden + white-space:nowrap on the workspace-name element so it truncates at narrow widths.

## Expected Behavior

_Expected behavior not specified — see spec AC._

## Actual Behavior

_Actual behavior not specified — see verification evidence._

## File(s)

| File | Detail |
|------|--------|
| src/renderer/src/components/organisms/shell/Titlebar.css |  |

## Evidence

Reported by user.

## Related Issues

_None — standalone bug._

## Fix Notes

_Filled in after resolution._
