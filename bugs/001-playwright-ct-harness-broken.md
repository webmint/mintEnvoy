# Bug 001: Playwright CT harness broken

**Status**: Fixed
**Severity**: Warning
**Source**: manual
**Feature**: N/A
**AC**: N/A
**Reported**: 2026-06-24
**Fixed**: 2026-06-24

## Description

`npm run test:ct` failed with `RollupError: Could not resolve "./components/Versions" from "playwright/index.tsx"` and "92 did not run". CORRECTION: the root cause was NOT a source import — `playwright/index.tsx` is a comment-only file with no such import. The error came from a STALE Vite CT build cache (`playwright/.cache/`, gitignored) that retained a build graph from when an entry once referenced `./components/Versions` (the component was removed in feature 001 but the cache was never invalidated). Surfaced during feature 003 /implement and confirmed during /review.

## Expected Behavior

_Expected behavior not specified — see spec AC._

## Actual Behavior

_Actual behavior not specified — see verification evidence._

## File(s)

| File                 | Detail |
| -------------------- | ------ |
| playwright/index.tsx |        |

## Evidence

Reported by user.

## Related Issues

_None — standalone bug._

## Fix Notes

Resolved by clearing the stale CT cache: `rm -rf playwright/.cache`. After clearing, `npm run test:ct` rebuilds clean (166 modules transformed) and **92 CT tests pass (11.4s)**, including all 33 `Shell.ct.tsx` tests (real-browser pointer drag/capture, release-outside-window, focus-return, Sidebar→Divider→store + PaneSplit→Divider→store integration drags). No source change was needed. Follow-up (optional): ensure `playwright/.cache/` is gitignored (it is a build artifact) so a stale cache can't re-trigger this; consider a `pretest:ct` clean step if it recurs.
