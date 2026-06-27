# Spec: dropdown-ct-dismiss

**Date**: 2026-06-27
**Status**: Complete
**Design source**: none
**Author**: Claude + User

## 1. Overview

Two Playwright component tests for the Dropdown primitive's click-outside dismissal are flaky-to-failing because each fires its outside click before Radix's DismissableLayer has armed its outside-click detection. This spec makes both tests deterministic by gating the outside click on a concrete overlay-readiness signal — a test-only change that touches no production code and keeps the existing strict assertions verbatim.

## 2. Current State

Dropdown (src/renderer/src/components/molecules/Dropdown.tsx:204) wraps Radix DropdownMenu (modal by default); click-outside dismissal is owned by Radix's DismissableLayer. Two CT tests exercise it: 'AC-4 — clicking outside the menu closes it' (src/renderer/src/components/molecules/__tests__/Dropdown.ct.tsx:185) and 'AC-3 — focus return after click-outside' (Dropdown.ct.tsx:236). Both open the menu via trigger.click(), assert the menu visible, then immediately fire page.mouse.click at a viewport coordinate (Dropdown.ct.tsx:198 and :253) and assert expect(menu).not.toBeVisible(). They fail: research (research/2026-06-27-003-dropdown-ct-click.md) proved a setup-timing race — Radix DismissableLayer attaches its document pointerdown listener via setTimeout(0) (node_modules/@radix-ui/react-dismissable-layer/dist/index.mjs:265) while the 140ms entry animation runs, so a click in the same tick the menu becomes visible is never classified as outside and onDismiss never fires (measured: zero of five runs dismissed with no settle, all five with a 100ms settle). The sibling Modal CT (src/renderer/src/components/molecules/__tests__/Modal.ct.tsx:127) passes the identical page.mouse.click outside dispatch because it mounts the overlay open, arming the layer long before its click — confirming this is a test-timing defect, not a production defect. Per docs/architecture.md the CT suite runs via 'playwright test -c playwright.config.ts'; these two are the sole failures (125 of 127 passing). The CT spec has been unchanged since it was added in 001-ui-primitives, so it has been racy since inception.

## 3. Desired Behavior

Both CT tests pass deterministically. Each test, after asserting the menu is visible and before firing the outside corner click, waits for a concrete overlay-readiness signal (the menu's entry animation having completed) so Radix's DismissableLayer is guaranteed armed. The existing strict assertions are preserved exactly — expect(menu).not.toBeVisible() for dismissal (Dropdown.ct.tsx:200) and the dismissal + expect(trigger).toBeFocused() for focus-return (Dropdown.ct.tsx:256, :259). No production code changes: only the two test cases (and, if needed, their fixture in Dropdown.stories.tsx) are edited. No bare fixed-delay timeout is introduced. The rest of the CT suite stays green.

## 4. Affected Areas

| Area | Files | Impact |
|------|-------|--------|
| node_modules/@radix-ui | node_modules/@radix-ui/react-dismissable-layer/dist/index.mjs:265 | see findings |
| Dropdown click-outside CT tests | src/renderer/src/components/molecules/__tests__/Dropdown.ct.tsx | Edit the two failing test cases (the outside clicks at :198 and :253): insert an overlay-readiness wait before each corner click. Strict assertions unchanged. |
| Dropdown CT fixture (conditional) | src/renderer/src/components/molecules/__tests__/Dropdown.stories.tsx | Only if the readiness wait needs a fixture affordance (e.g. a stable test hook). Preferred approach needs no fixture change; listed so /plan can confirm. |

## 5. Acceptance Criteria

Each AC must be testable and unambiguous. **Cover each category that applies. Mark non-applicable categories with "N/A — [reason]".**

### 5.1 Tooling / artifact presence and absence

N/A — No tooling artifact is added or removed; this is a behavior fix to two existing test cases.

### 5.2 Behavior preservation

- [x] **AC-1**: WHEN a user clicks outside an open Dropdown menu, the Dropdown shall close the menu.
- [x] **AC-2**: The Dropdown component-test suite shall keep all of its currently-passing tests passing.
- [x] **AC-7**: WHILE applying the fix, the system shall keep the existing strict dismissal and focus-return assertions unchanged and unweakened.

### 5.3 Behavior change

- [x] **AC-3**: WHEN the CT test 'clicking outside the menu closes it' (Dropdown.ct.tsx:185) runs, the Dropdown menu shall become not visible so the dismissal assertion passes.
  > Verification: npx playwright test -c playwright.config.ts --grep 'clicking outside the menu closes it'
- [x] **AC-4**: WHEN the CT test 'focus return after click-outside' (Dropdown.ct.tsx:236) runs, the Dropdown menu shall close and focus shall return to the trigger button.
- [x] **AC-5**: The two click-outside Dropdown component tests shall pass deterministically across repeated runs.

### 5.4 CI / pipeline

N/A — No CI/pipeline config change; deterministic passing is asserted by the CT acceptance criteria in §5.3.

### 5.5 Hooks / gates

N/A — No hook or commit-gate change.

### 5.6 Documentation

N/A — No docs/ change required; the bugs/003 record lifecycle is handled by /verify, not this spec.

### 5.7 Hygiene

- [x] **AC-6**: The changed test files shall pass type-check and lint.
  > Verification: npm run typecheck:web && eslint --cache src/renderer/src/components/molecules/__tests__/Dropdown.ct.tsx
- [x] **AC-8**: The changed test files shall contain no leftover debug artifacts such as console statements, debugger statements, or focused or skipped tests.
  > Verification: ! grep -nE 'console\.log|debugger|\.only\(|\.skip\(' src/renderer/src/components/molecules/__tests__/Dropdown.ct.tsx

## 6. Out of Scope

**Coverage rule (v3)**: For each Phase 1.5 finding, the finding either (a) becomes an AC in §5, (b) becomes a Constraint in §7, (c) is explicitly listed here as out of scope, OR (d) is in §9 Risks with documented mitigation. Unlanded finding = hard error — re-verify Phase 1.5 enumeration is complete before saving.

- NOT included: Modifying Radix or the production Dropdown component (src/renderer/src/components/molecules/Dropdown.tsx) — click-outside dismissal is Radix-owned and works correctly in production. — F-index-2
- NOT included: Introducing a bare fixed-delay waitForTimeout as the fix mechanism (brittle magic-number; rejected by the research). — F-2026-06-27-003-dropdown-ct-click-6
- NOT included: Hardening the sibling overlay CT specs (Modal.ct.tsx, nested-overlays.ct.tsx) that share the same arm-race risk — they pass today and are excluded per the scope decision.

## 7. Technical Constraints

- Must follow: Search before building
- Must follow: Minimal changes (Key Rules #3)
- Must follow: Specs are contracts / strict assertions
- Must not break: Production Dropdown click-outside dismissal behavior must not change — it works for real users; only the test's timing is corrected.
- Must follow constitution §6.3: Search the codebase for an existing utility/helper/component before writing anything generic or reusable — reuse the Modal CT overlay-readiness pattern (Modal.ct.tsx:127) rather than inventing new test machinery.
- Must follow constitution §3.4: Co-located tests under __tests__/ next to the code, split .test.tsx (Vitest) and .ct.tsx (Playwright CT); the click-outside behavior is CT-only and the fix stays in the .ct.tsx spec (and fixture, if needed).

## 8. Open Questions

- **Q-1**: Exact readiness API for the pre-click wait (e.g. awaiting element.getAnimations() completion vs a waitForFunction on the menu's computed opacity) — deferred to /plan; spec mandates a concrete readiness signal, not a fixed delay.
- **DP-existing_behavior-1** [no DP in category existing_behavior]: no relevant decision point for existing_behavior
- **DP-data_flow_state-1** [no DP in category data_flow_state]: no relevant decision point for data_flow_state
- **DP-edge_cases-1** [no DP in category edge_cases]: no relevant decision point for edge_cases
- **DP-ui_ux_details-1** [no DP in category ui_ux_details]: no relevant decision point for ui_ux_details
- **DP-breaking_changes-1** [no DP in category breaking_changes]: no relevant decision point for breaking_changes

## 9. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Under prefers-reduced-motion (or any zero-animation config), the entry animation is disabled, so an animation-completion readiness signal could resolve immediately and let the arm-race resurface. | Low | Med | Readiness signal must not rely solely on animation presence; /plan picks a signal that holds when animations are off (e.g. a microtask/rAF settle or polling the armed state), or the test enables motion. |
| The readiness wait could mask a genuine future production dismissal regression (test waits, then still asserts). | Low | Low | Assertions stay strict (not.toBeVisible / toBeFocused), so a real dismissal break still fails the test after the wait. |
