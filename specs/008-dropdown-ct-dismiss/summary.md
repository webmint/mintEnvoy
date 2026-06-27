# Summary: dropdown-ct-dismiss

**Feature**: 008-dropdown-ct-dismiss
**Verdict** (from `/verify`): APPROVED

## What was built

The Dropdown primitive's two click-outside component tests were flaky-to-failing and are now deterministic. Clicking outside an open dropdown menu reliably closes it (and returns focus to the trigger) in the Playwright component-test suite, with no change to the shipped app — the fix corrected the test's timing, not the production component. The full component-test suite is green again.

## Changes

- Gated both click-outside CT tests on a real overlay-readiness signal before the outside click, so Radix's dismissal is armed before the click fires — removing the race that left the menu open. Added a third test covering the reduced-motion case to prove the fix holds when entry animations are disabled.

## Files changed

15 files, +1020 / -0.

- `src/` (the only source change): `src/renderer/src/components/molecules/__tests__/Dropdown.ct.tsx` — the readiness gate added before each corner click in the two click-outside tests, plus the new reduced-motion test.
- `specs/008-dropdown-ct-dismiss/` (planning + pipeline record): spec, plan, tasks, design-manifest, review, verification, and the per-stage handoffs.
- `research/`: the root-cause investigation report + handoff for bug 003.

(No production/runtime code changed — the single source edit is a test file.)

## Key decisions

- **Readiness-signal API**: await the menu's entry-animation completion (`getAnimations().finished`), then a separate `setTimeout(0)` macrotask-boundary yield — deterministic and motion-independent, and explicitly not a fixed-delay magic-number (which the spec excluded).
- **Action fidelity**: keep a single outside click per test (no `toPass()` retry loop), so the test still models a real one-shot user click.
- **Scope confinement**: edit only the failing CT tests; the production `Dropdown.tsx`/Radix and the sibling overlay CTs (Modal, nested-overlays) were left untouched.
- **Reuse**: mirror the Modal suite's "armed-before-dismissal" convention rather than introduce a new shared test helper.

## Deviations from plan

- The plan scoped the change to editing the two failing tests; during the `/implement` review panel, QA flagged the missing reduced-motion coverage of the spec's §9 Risk-1, so a third CT test (reduced-motion click-outside) was added in the same file to validate the macrotask-floor mitigation. Approved at the per-task hard gate; stays within the single planned file.

## Acceptance criteria

All 8 PASS (per `/verify`, code-read in `tests` mode):

- [x] AC-1 — clicking outside an open menu closes it
- [x] AC-2 — the CT suite keeps its currently-passing tests passing
- [x] AC-7 — strict dismissal/focus-return assertions kept unchanged and unweakened
- [x] AC-3 — `clicking outside the menu closes it` passes
- [x] AC-4 — `focus return after click-outside` passes (menu closes + focus returns to trigger)
- [x] AC-5 — both click-outside tests pass deterministically across repeated runs
- [x] AC-6 — changed test file passes type-check and lint
- [x] AC-8 — no leftover debug artifacts in the changed file
