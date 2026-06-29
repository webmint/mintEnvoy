# Task 003: add-ct-fidelity-suite

**Feature**: 010-request-bar-fidelity
**Agent**: qa-engineer
**Status**: Complete
**Depends on**: 001, 002
**Blocks**: None
**Spec criteria**: AC-13, AC-15, AC-16, AC-17, AC-19
**Review checkpoint**: Yes
**Context docs**: docs/architecture.md

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/organisms/__tests__/RequestBar.ct.tsx | Modify | Add Playwright CT computed-style EXACT-equality fidelity assertions on enumerated `.request-bar` props + a thresholded screenshot diff |
| src/renderer/src/components/organisms/__tests__/RequestBar.stories.tsx | Modify | Add a filled-state fixture (non-empty URL → enabled Send + keycap) if existing fixtures don't cover it |

## Description

Add the tiered fidelity verification for the restyled RequestBar (per the 005 precedent): Playwright CT computed-style EXACT-equality assertions on the enumerated `.request-bar` properties, backed by a thresholded screenshot diff. Run in a real Chromium browser (jsdom cannot resolve computed/pseudo styles). Reuse the existing CT fixture scaffolding — `tokens.css` is imported globally via `playwright/index.tsx` and `data-mstyle='soft'` is set on `document.documentElement` in `beforeEach` — and the two-step Radix dismiss gate already present in the file. Add a filled-state fixture (non-empty URL → `canSend` true → enabled Send + visible keycap) in `RequestBar.stories.tsx` if the existing fixtures don't already exercise the enabled state. Existing behaviour/layout CT and unit suites must stay green.

## Change Details

- In `src/renderer/src/components/organisms/__tests__/RequestBar.ct.tsx`:
  - Add a `describe('RequestBar — fidelity')` block asserting computed-style EXACT equality on: control height (~`32px`); `border-radius` = the resolved `--radius` value on URL input / method-select / Send / ghost actions; URL `:focus` border-color = `--accent` and a non-empty `box-shadow` ring; method-select computed `background` (elevated) + `border` AND the per-method text `color` (GET resolves to `--m-get` via the soft cascade); Send computed `font-weight` 600 + non-empty `box-shadow`; the `request-bar__kbd` present when the URL is non-empty and absent when empty; Save/Share rendered as bordered actions with visible labels.
  - Add a thresholded screenshot assertion: `toHaveScreenshot` with `maxDiffPixelRatio: 0.01` (and a per-pixel `threshold` for anti-aliasing) on the rendered `.request-bar`.
  - Reuse the `beforeEach` store-reset + `data-mstyle='soft'` setup and the two-step dismiss gate; do not duplicate them.
- In `src/renderer/src/components/organisms/__tests__/RequestBar.stories.tsx`:
  - Add a filled-state fixture (seed a tab with a non-empty URL) if no existing fixture renders the enabled Send + keycap; otherwise reuse `RequestBarSendSpyFixture` / `RequestBarTwoTabFixture`.

## Contracts

### Expects (checked before execution)
- Task 001 landed: `RequestBar.tsx` renders the `request-bar__kbd` (aria-hidden, canSend-gated) and visible Save/Share labels.
- Task 002 landed: `.request-bar` carries the reference geometry, `--radius` binding, URL focus ring, Send weight-600 + shadow, and the `.request-bar .request-bar__method.method` background/border override (no color).
- The existing CT fixtures import `tokens.css` and set `data-mstyle='soft'` on the host; the two-step Radix dismiss gate is present in `RequestBar.ct.tsx`.

### Produces (checked after execution)
- `RequestBar.ct.tsx` contains computed-style EXACT-equality assertions on the enumerated `.request-bar` props (height, radius, focus ring, method-select background/border + per-method colour, Send weight/shadow, keycap presence/absence, labelled actions).
- `RequestBar.ct.tsx` contains a `toHaveScreenshot` assertion with `maxDiffPixelRatio` set.
- `RequestBar.stories.tsx` provides a fixture that renders the filled/enabled state (non-empty URL).
- The existing behaviour/layout CT tests and the unit suite still pass.

## Done When

- [x] CT asserts computed-style EXACT equality on the enumerated `.request-bar` props (incl. method-select bg/border + per-method colour, keycap presence/absence)
- [x] Thresholded `toHaveScreenshot` (maxDiffPixelRatio 0.01) added on `.request-bar`
- [x] Filled-state fixture exercises enabled Send + keycap
- [ ] Existing RequestBar behaviour/layout CT + unit suites stay green _(unverified — see Completion Notes)_
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (npm run typecheck:web)
- [x] Linter passes on changed files (npm run lint)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-29T08:47:35Z
**Files changed**: src/renderer/src/components/organisms/__tests__/RequestBar.ct.tsx, src/renderer/src/components/organisms/__tests__/RequestBar.stories.tsx, __snapshots__/components/organisms/__tests__/RequestBar.ct.tsx-snapshots/request-bar-fidelity-chromium-darwin.png
**Contract**: Expects 3/3 | Produces 4/4
**Notes**: Added describe('RequestBar — fidelity'): 10 CT tests (heights, --radius binding, exact box-shadow via probe-elements, method bg/border + GET->--m-get AND POST->--m-post proving (0,3,0) no-color fall-through, Send weight-600+inset shadow, keycap present/absent, Save/Share bordered+labelled+Share disabled) + thresholded toHaveScreenshot baseline. Panel clean R1; repair leg closed 5 qa assertion-strength gaps. 10/10 fidelity tests pass. KNOWN REGRESSION (NOT this task): pre-existing AC-20 CT (long URL must not reflow Send button) FAILS — Tasks 001/002 RequestBar.css/.tsx introduced a ~30px reflow (confirmed via git stash). Task 003 cannot touch those files; the new CT correctly catches it. 'Existing CT stay green' Done-When left unticked accordingly — remediate via /fix on RequestBar.css (flex-shrink/min-width) before /verify.
