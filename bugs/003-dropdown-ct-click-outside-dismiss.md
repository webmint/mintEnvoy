# Bug 003: Dropdown CT — clicking outside the menu does not close it

**Status**: Open
**Source**: manual
**Severity**: Warning
**Filed**: 2026-06-26
**File**: src/renderer/src/components/molecules/__tests__/Dropdown.ct.tsx:185

## Description

The Playwright component test `Dropdown — AC-4 dismiss › clicking outside the menu closes it` (`Dropdown.ct.tsx:185`) fails: after opening the menu and clicking the viewport corner (`page.mouse.click(vp.width - 10, vp.height - 10)`), the menu remains visible — `expect(menu).not.toBeVisible()` times out at line 200.

This is a Radix `DismissableLayer` click-outside interaction failing in the CT environment (the click at the viewport boundary does not trigger Radix's outside-click dismissal).

## Provenance — pre-existing, NOT feature 005

Discovered during feature `005-tab-bar-visual-fidelity` task 006 (the CT token-harness F2 blast-radius check). Verified pre-existing and unrelated to 005: the test fails **identically with and without** the task-006 `tokens.css` import into `playwright/index.tsx` (the orchestrator ran the single test both ways — the global token import caused zero existing-suite shift). CSS custom properties cannot affect Radix's JS click-outside detection. No feature-005-touched file is involved.

## Impact

The CT suite is 100/101 (this is the sole failure). It does not block feature 005 (a different component's behavioral test). It should be investigated separately — likely a CT-environment viewport/pointer-coordinate or Radix `DismissableLayer` interaction issue in the Playwright CT harness, not necessarily a production defect.

## Next step

`/research "Dropdown CT click-outside dismissal fails at viewport boundary in Playwright CT"` to investigate, then `/specify` or `/fix` as appropriate. Out of scope for feature 005.

## Re-confirmed — feature 006 (2026-06-27)

Re-observed during feature `006-reorganize-flat-components` verification. Still Open, still pre-existing + unrelated (confirmed failing on the clean 006 baseline with the feature's changes stashed — 006 touched no Dropdown/CT/component code). Two CT tests now fail from this one root cause:
- `Dropdown.ct.tsx:185` — `AC-4 dismiss › clicking outside the menu closes it` (the original).
- `Dropdown.ct.tsx:236` — `AC-3 focus return after click-outside › focus returns to the trigger button after the menu closes via click-outside` — a downstream symptom (focus return cannot fire because the click-outside dismissal never happens).

CT suite is 125/127 (these 2 are the sole failures). Investigate the root dismissal failure once; both tests should recover together.
