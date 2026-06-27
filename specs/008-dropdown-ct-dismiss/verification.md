# Feature Verification — 008-dropdown-ct-dismiss — 2026-06-27

**Feature**: specs/008-dropdown-ct-dismiss
**Date**: 2026-06-27
**AC Verification Mode**: tests

## Acceptance Criteria

| AC | Status | Evidence |
|---|---|---|
| AC-1 | PASS (code) | Test `clicking outside the menu closes it` at Dropdown.ct.tsx:185-205 opens the dropdown, fires the animation-completion gate (`menu.evaluate((el) => Promise.all(el.getAnimations().map((a) => a.finished)))`, line 198), the macrotask-floor (`page.evaluate(() => new Promise((resolve) => setTimeout(resolve, 0)))`, line 201), then `page.mouse.click(vp.width - 10, vp.height - 10)`. Strict assertion at line 204: `await expect(menu).not.toBeVisible()` directly proves the AC. |
| AC-2 | PASS (code) | No existing tests were removed, reordered, or restructured. All prior describe-blocks (AC-2 keyboard nav lines 33-161, AC-4 dismiss lines 167-229, AC-3 focus-return lines 235-292, AC-2 activation lines 298-357, AC-5 edge lines 363-435, AC-14 reduced-motion lines 441-478) are intact. The single addition is the new third test in AC-4 dismiss (lines 207-228). Suite-green confirmation is the mechanical signal run separately. |
| AC-7 | PASS (code) | `clicking outside the menu closes it` (line 204): `await expect(menu).not.toBeVisible()` — strict, no `.toPass()`, no `.not.toBeVisible({ timeout: N })` softening. `focus returns after click-outside` (line 287): `await expect(menu).not.toBeVisible()` — strict. Line 290: `await expect(trigger).toBeFocused()` — strict. All three assertions are unweakened verbatim strings; no wrapping or tolerance adjustments present. |
| AC-3 | PASS (code) | Test at line 185 (`clicking outside the menu closes it`): readiness gate at line 198 (animation completion) + macrotask floor at line 201 (setTimeout 0) precede the single `page.mouse.click` at line 202. Assertion at line 204: `await expect(menu).not.toBeVisible()`. The gate sequence ensures Radix DismissableLayer's deferred pointerdown listener is armed before the click, making the dismissal reliable. Note: the spec references "line 185" which matches the `test(` declaration exactly. |
| AC-4 | PASS (code) | The focus-return-after-click-outside test is in the describe block starting at line 262; the `test(...)` declaration is at line 265. (The spec's ":236" references the comment section heading at line 236, not the test declaration — a line-number drift from insertions above.) The test: focuses trigger (line 270), clicks trigger (line 271), waits for animation completion (line 280), waits for macrotask floor (line 283), clicks at (640, 600) (line 284), asserts `expect(menu).not.toBeVisible()` (line 287), asserts `expect(trigger).toBeFocused()` (line 290). Both close-menu and focus-return conditions are verified with strict assertions. |
| AC-5 | PASS (code) | Both click-outside tests apply identical readiness-gate sequences: (1) `menu.evaluate((el) => Promise.all(el.getAnimations().map((a) => a.finished)))` waits for all CSS animations on the menu element to settle; (2) `page.evaluate(() => new Promise((resolve) => setTimeout(resolve, 0)))` advances to the next macrotask boundary, guaranteeing Radix's setTimeout(0)-deferred pointerdown listener is registered before the click. The reduced-motion test (lines 207-228) confirms the macrotask floor alone suffices when no animations run, covering that variant. The structure eliminates the timing race described in spec §9 Risk-1. Determinism across repeated runs is a runtime claim; code-reading confirms the fix mechanism is in place. |
| AC-6 | PASS (code) | New code uses `@playwright/experimental-ct-react` types consistently; `page.viewportSize()` returns `{ width: number; height: number } \\| null` and is null-coalesced correctly (line 220). `el.getAnimations()` returns `Animation[]`; `a.finished` is `Promise<Animation>`; `Promise.all(...)` is valid. `page.evaluate()` accepts `() => Promise<unknown>`. No suppressed TypeScript (`@ts-ignore`/`@ts-expect-error`) or ESLint-disable directives. Lint/type-check mechanical confirmation deferred to suite run. |
| AC-8 | PASS (code) | Full file scan: zero `console.*` calls, zero `debugger` statements, zero `test.only` / `describe.only` / `test.skip` / `describe.skip` / `.only` / `.skip` occurrences in executable code. The file contains only `test(...)` and `test.describe(...)` declarations — no focused or excluded tests. |

## Code Quality

**Mechanical checks**: PASS
**Cross-task consistency**: see /review report at specs/008-dropdown-ct-dismiss/review.md
**Scope creep**: none detected
**Leftover artifacts** _(advisory — does not block the verdict)_: 17 flagged (debug prints / bare TODOs / commented-out code)

## Review Findings

0 confirmed | 0 contested | 0 dismissed | 0 uncertain
Severity breakdown: 0 Critical, 0 High, 0 Medium, 0 Info

## Issues Found

_No confirmed or contested findings in the review report._
## Verdict

**APPROVED**

**Reasons**:

- Hygiene (advisory, non-blocking): 17 leftover artifact(s) — review but does not block the verdict.

**Next step**: run `/summarize` then `/finalize`.
