# Bug 012: Titlebar + KVTable controls lack focus-visible

**Status**: Open
**Severity**: Critical
**Source**: manual
**Feature**: N/A
**AC**: N/A
**Reported**: 2026-07-10
**Fixed**: 

## Description

Titlebar interactive buttons (.titlebar__workspace-pill, .titlebar__icon-btn, .titlebar__cmdk, .titlebar__env-selector, .titlebar__account-pill) and the KVTable delete button (.kv-actions button) have no :focus-visible indicator — they set outline:none (or rely on the UA default) with no override, so keyboard focus is invisible. WCAG 2.1 SC 2.4.7 (Focus Visible). Pre-existing (not introduced by feature 016; surfaced by the 016 /review accessibility audit). Suggested fix: add ':focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }' to each control (matches the pattern used elsewhere in the codebase). Also affects KVTable delete button in src/renderer/src/components/organisms/KVTable.css.

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
