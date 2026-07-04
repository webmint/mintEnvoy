# Bug 008: missing main landmark

**Status**: Fixed
**Severity**: Warning
**Source**: manual
**Feature**: N/A
**AC**: N/A
**Reported**: 2026-06-30
**Fixed**: 2026-07-04

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

Resolved by manual change in `src/renderer/src/components/organisms/shell/Shell.tsx:359`: the
workspace wrapper was changed from `<div className="shell__workspace">` to
`<main className="shell__workspace">`. The `<main>` renders unconditionally on the live path
(`App.tsx:23` → `<Shell>` → workspace `<main>`), wrapping the primary content (tabs strip +
request/response PaneSplit) and excluding Titlebar / Sidebar / Statusbar. One `<main>` landmark
now ships (the only other `<main>`, `PrimitivesDemo.tsx:656`, has no callers and is not in the
App tree), closing the WCAG 2.1 SC 2.4.1 (Level A) skip-to-content gap. Regression guard added:
`Shell.ct.tsx` asserts exactly one `<main>` landmark wraps the workspace content.
