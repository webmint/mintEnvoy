# Bug 014: Method chip soft-mode contrast fails WCAG AA

**Status**: Open
**Severity**: Warning
**Source**: manual
**Feature**: N/A
**AC**: N/A
**Reported**: 2026-07-10
**Fixed**: 

## Description

The HTTP method chip in soft mstyle (data-mstyle='soft') renders text at ~2.36:1 contrast against its background for all method colors at 9.5px — fails WCAG 2.1 SC 1.4.3 Contrast (Minimum) which requires 4.5:1 for text this size. Pre-existing (not introduced by feature 016; surfaced by the 016 /review accessibility audit). Suggested fix: darken the soft-mode method text color or the chip background so the pair reaches >=4.5:1; verify across all method color variants (GET/POST/PUT/DELETE/PATCH). Colors originate in the design tokens (design/tokens.json -> tokens.css).

## Expected Behavior

_Expected behavior not specified — see spec AC._

## Actual Behavior

_Actual behavior not specified — see verification evidence._

## File(s)

| File | Detail |
|------|--------|
| src/renderer/src/components/organisms/RequestBar.css |  |

## Evidence

Reported by user.

## Related Issues

_None — standalone bug._

## Fix Notes

_Filled in after resolution._
