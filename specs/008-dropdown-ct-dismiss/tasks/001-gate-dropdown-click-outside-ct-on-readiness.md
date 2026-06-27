# Task 001: Gate Dropdown click-outside CT tests on overlay readiness

**Feature**: 008-dropdown-ct-dismiss
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: None
**Blocks**: None
**Spec criteria**: AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8
**Review checkpoint**: No
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/molecules/__tests__/Dropdown.ct.tsx | Modify | Insert an overlay-readiness gate immediately before the corner `page.mouse.click(...)` in the two click-outside tests; strict assertions unchanged. |

## Description

Two Playwright CT tests fire their outside corner click in the same tick the menu becomes visible, before Radix `DismissableLayer` arms its document `pointerdown` listener (attached via `setTimeout(0)` while the 140ms entry animation runs), so the click is not classified as outside and the menu never dismisses. Fix both tests by gating each corner click on a concrete overlay-readiness signal: await the menu's running animations to finish, then yield one in-page `setTimeout(0)` macrotask boundary (a motion-independent floor that guarantees Radix's earlier-queued `setTimeout(0)` listener has fired). Keep a SINGLE corner click per test and leave the strict assertions verbatim — do NOT wrap the click+assert in a `toPass()` retry loop. No production code changes.

## Change Details

- In `src/renderer/src/components/molecules/__tests__/Dropdown.ct.tsx`:
  - In the test `'clicking outside the menu closes it'` (AC-3), immediately before `await page.mouse.click(vp.width - 10, vp.height - 10)`, insert:
    - `await menu.evaluate((el) => Promise.all(el.getAnimations().map((a) => a.finished)))` — wait for the entry animation to complete (overlay-readiness signal).
    - `await page.evaluate(() => new Promise((r) => setTimeout(r, 0)))` — macrotask-boundary readiness floor (a distinct yield, NOT folded into the `menu.evaluate` above): guarantees Radix DismissableLayer's `setTimeout(0)`-deferred `pointerdown` listener has fired even when no animation runs. Carry a one-line comment saying exactly this so it is not read as a banned fixed-delay sleep.
  - In the test `'focus returns to the trigger button after the menu closes via click-outside'` (AC-4), apply the identical two-await readiness gate immediately before `await page.mouse.click(640, 600)`.
  - Leave the single `page.mouse.click(...)` per test and the assertions (`expect(menu).not.toBeVisible()`, `expect(trigger).toBeFocused()`) unchanged.

## Contracts

### Expects (checked before execution)
- `Dropdown.ct.tsx` contains the test `'clicking outside the menu closes it'` whose body has a `page.mouse.click(...)` followed by `expect(menu).not.toBeVisible()` (AC-3).
- `Dropdown.ct.tsx` contains the test `'focus returns to the trigger button after the menu closes via click-outside'` whose body has a `page.mouse.click(...)` followed by `expect(menu).not.toBeVisible()` and `expect(trigger).toBeFocused()` (AC-4).
- `menu` is a `page.getByRole('menu')` locator in scope in both tests; `trigger` is in scope in the focus-return test.

### Produces (checked after execution)
- In both tests, immediately before the corner `page.mouse.click(...)`, a `menu.evaluate(...)` call referencing `getAnimations` and `finished` is present, followed by a SEPARATE in-page `setTimeout` macrotask yield.
- The `setTimeout` yield line carries an explanatory comment naming it a macrotask-boundary readiness floor (not a fixed delay).
- `expect(menu).not.toBeVisible()` and `expect(trigger).toBeFocused()` are unchanged; exactly one `page.mouse.click(...)` per test (no `toPass` retry wrapper).
- Both tests pass deterministically; the rest of the CT suite is unaffected.

## Done When

- [x] The test `'clicking outside the menu closes it'` passes (AC-3).
- [x] The test `'focus returns to the trigger button after the menu closes via click-outside'` passes (AC-4).
- [x] Each test has the readiness await + a separate commented `setTimeout(0)` floor before its single corner click; strict assertions unchanged (AC-5, AC-7).
- [x] The full CT suite is green (`playwright test -c playwright.config.ts` → 127/127), confirming no regression (AC-2).
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-27T19:39:59Z
**Files changed**: src/renderer/src/components/molecules/__tests__/Dropdown.ct.tsx
**Contract**: Expects 3/3 | Produces 4/4
**Notes**: Added readiness gate (getAnimations().finished await + separate commented setTimeout(0) macrotask floor) before the corner click in both click-outside tests; added a reduced-motion click-outside test (qa Gap-1) proving the floor alone dismisses. Full CT suite 128/128 green. No production code touched.
