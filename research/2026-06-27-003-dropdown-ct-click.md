# Research: 003-dropdown-ct-click-outside-dismiss bug


**Date**: 2026-06-27
**Topic**: 003-dropdown-ct-click-outside-dismiss bug
**Mode**: Bug
**Verdict**: Root cause confirmed

## Summary

Two Playwright CT tests (Dropdown.ct.tsx:185 dismiss-on-outside-click and :236 focus-return-after-click-outside) fail because the spec dispatches page.mouse.click at a viewport corner in the same tick the menu becomes visible, before Radix DismissableLayer has armed its document pointerdown listener (attached via setTimeout(0) at index.mjs:265, while the 140ms entry animation is still running). Proven empirically: with no settle the corner click is never classified as outside (0/5 dismiss); with a 100ms settle it is deterministic (5/5). The same Radix mechanism dismisses reliably in the Modal CT suite (Modal.ct.tsx:139), which opens its overlay at mount and is therefore armed long before its corner click — confirming this is a test-timing race, not a production defect. Recommended fix is test-only: gate the two specs on a concrete overlay-readiness signal before the corner click, keeping the strict assertions; confidence is high, residual uncertainty is only the choice of readiness signal (entry-animation completion vs a fixed delay).

## Symptom

| Dimension | Value |
|---|---|
| Symptom | Playwright CT test 'Dropdown — AC-4 dismiss › clicking outside the menu closes it' (Dropdown.ct.tsx:185) fails: after opening the menu and clicking the viewport corner, the menu stays visible; expect(menu).not.toBeVisible() times out (line 200). Downstream, :236 (AC-3 focus-return after click-outside) also fails because the dismissal never fires. CT suite 125/127, these 2 the sole failures. |
| Affected area | Dropdown component test harness: src/renderer/src/components/molecules/__tests__/Dropdown.ct.tsx (failing CT spec), Radix-based Dropdown.tsx (Radix DropdownMenu -> DismissableLayer), CT fixtures Dropdown.stories.tsx, and the shared Playwright CT mount (playwright/index.tsx). Cross-cutting candidate: any Radix overlay in CT (Modal). |
| Repro / Current | Run the CT suite (playwright test over CT specs). In Dropdown.ct.tsx:185: render the Dropdown fixture, open the menu (click trigger), assert menu visible, then page.mouse.click(vp.width - 10, vp.height - 10) to click the viewport corner, then expect(menu).not.toBeVisible() — times out at line 200. Fails identically with/without the tokens.css import; reproduces on a clean baseline (006 changes stashed). |
| Desired | Both CT tests pass (Dropdown.ct.tsx:185 dismiss + :236 focus-return) via a correct fix at whatever layer the root cause lives; production click-outside dismissal behavior confirmed intact (not a loosened/weakened test). |
| Scope | cross-cutting |

## Codebase Findings (WHERE)

| Surface | File:line | Relevance | Framing |
|---|---|---|---|
| Test outside-click site (race trigger): page.mouse.click at viewport corner fired in the same tick the menu became visible, before Radix's dismiss layer is armed | src/renderer/src/components/molecules/__tests__/Dropdown.ct.tsx:198 | Primary symptom site for AC-4 dismiss; clicking here immediately after toBeVisible races Radix DismissableLayer setTimeout(0) arm | primary |
| Failing assertion: expect(menu).not.toBeVisible() times out at 5s | src/renderer/src/components/molecules/__tests__/Dropdown.ct.tsx:200 | The assertion that times out because the outside click was not classified as outside (dismiss never fired) | primary |
| Second affected test (AC-3 focus-return after click-outside): same immediate outside click | src/renderer/src/components/molecules/__tests__/Dropdown.ct.tsx:253 | Downstream symptom :236 — same race; focus-return cannot fire because dismissal never happens | primary |
| Radix DismissableLayer defers the document pointerdown listener attach via setTimeout(0) | node_modules/@radix-ui/react-dismissable-layer/dist/index.mjs:265 | Root mechanism: the outside-click detection listener is attached on a macrotask AFTER content mount; an outside click before this fires is not classified as outside | primary |
| Radix onPointerDownCapture sets isPointerInsideReactTreeRef; reset only inside the document handler | node_modules/@radix-ui/react-dismissable-layer/dist/index.mjs:286 | Secondary mechanism in the same arm/reset cycle that gates whether a pointerdown is treated as outside | primary |
| Canonical reuse: Modal CT opens the overlay at mount (initialOpen=true), so DismissableLayer is armed well before the outside click | src/renderer/src/components/molecules/__tests__/Modal.ct.tsx:127 | canonical pattern — reusable: same Radix DismissableLayer dismisses reliably in CT when the layer is armed before page.mouse.click; disproves the production-defect framing | runner-up |
| Modal CT outside-click via page.mouse.click(5,5) passes | src/renderer/src/components/molecules/__tests__/Modal.ct.tsx:139 | Same dispatch mechanism as the failing Dropdown test, but passes — the only difference is open timing (armed vs racing), confirming primary framing | runner-up |

## Root Cause Hypothesis (WHY)

**Primary hypothesis**: Test-timing race between Playwright's immediate page.mouse.click(outside) and Radix DismissableLayer's asynchronously-armed (setTimeout(0)) outside-pointerdown detection. 'Menu visible' (toBeVisible) does not imply 'menu dismissable' — there is a window after open where the menu is rendered but the dismiss layer is not yet listening. Not a production defect.

**Confidence**: Confirmed

### Structured root cause

| Field | Value |
|---|---|
| trigger | page.mouse.click(vp.width-10, vp.height-10) at Dropdown.ct.tsx:198 fired immediately after expect(menu).toBeVisible() resolved, before Radix's setTimeout(0)-deferred document pointerdown listener was attached. |
| root_cause | The CT tests equate 'menu visible' (toBeVisible) with 'menu interactive/dismissable', but Radix DismissableLayer arms outside-click detection asynchronously (setTimeout(0) listener attach at index.mjs:265) after content mount and during the 140ms entry animation. This leaves a race window where an immediate outside click is not classified as outside, so onDismiss never runs. |
| contributing_factors | 1. Radix defers the document pointerdown listener attach via setTimeout(0) (index.mjs:265-266), so detection is not live the instant the menu renders. 2. The Dropdown CT tests open via trigger.click() immediately before the outside click, with no settle — unlike Modal CT which opens at mount (initialOpen=true) and is armed well before its outside click. 3. The entry animation (dropdown-content-in, 140ms) is still in flight when toBeVisible resolves (Playwright ignores opacity), reinforcing the false 'ready' signal. |

## Runner-up framing

| Field | Value |
|---|---|
| Frame | Genuine production defect: Radix DismissableLayer in modal mode (body pointer-events:none, outside pointerdown lands on the HTML element) fails to reliably detect/dispatch click-outside dismissal, so real users would also see the menu stay open. |
| Falsifier | If a settle delay before the outside click makes dismissal deterministic, the detection works once armed — so the failure is a test-timing race, not a production detection defect. (Observed: SETTLE=0 -> 0/5 dismiss; SETTLE=100ms -> 5/5 dismiss, refuting the production-defect frame.) |
| Confidence vs primary | lower |

## Hypothesis Enumeration

| Hypothesis | Falsifier (what would disprove it) | Runtime probe needed? |
|---|---|---|
| CT test-timing race: page.mouse.click(outside) is dispatched in the same tick the menu became visible (toBeVisible resolves while the entry animation is still in flight), BEFORE Radix DismissableLayer arms its document pointerdown listener (attached via setTimeout(0) at index.mjs:265). The outside pointerdown is therefore not classified as 'outside', so onDismiss never fires. | If true, inserting a settle delay between open and the outside click should make dismissal deterministic. Observed: SETTLE=0 -> 0/5 dismiss; SETTLE=100ms -> 5/5 dismiss. Confirmed. | no |
| Genuine production defect: Radix modal DismissableLayer (body pointer-events:none, outside pointerdown lands on HTML element) cannot reliably dispatch click-outside dismissal, so real users also see the menu stay open. | If true, the same mechanism would also fail when armed, and a settle delay would not help. Observed: Modal CT uses the identical page.mouse.click outside dispatch and passes (Modal.ct.tsx:139, opened at mount so armed early); and a settle delay makes Dropdown deterministic. Refuted. | no |

## Approaches (HOW to change)

### Gate the two outside-dismissal specs on overlay readiness (test-only)
- **Description**: In Dropdown.ct.tsx:185 and :236, after the overlay is asserted visible, await its entry-animation completion as a concrete readiness signal prior to the corner click (e.g. await menu.evaluate(el => Promise.all(el.getAnimations().map(a => a.finished)))). Mirrors the overlay-readiness convention already proven by the Modal suite at Modal.ct.tsx:127, which mounts the overlay open so its dismiss layer is armed well ahead of its corner click. Zero shipped-code changes; both strict not.toBeVisible assertions kept verbatim.
- **Addresses hypothesis**: A
- **Does NOT cover**: B
- **Pros**: Deterministic — keys on a real readiness signal, not a fixed delay; Zero shipped-code change; both strict assertions kept verbatim; Smallest blast radius: only the two failing specs; Reuses the existing Modal-suite overlay-readiness convention (Modal.ct.tsx:127), honoring the reuse-first rule
- **Cons**: Relies on the entry animation existing as the readiness proxy; a future zero-animation config would need a different ready signal; Slightly more verbose than a bare wait
- **Complexity**: Low

### Fixed settle delay before the corner click
- **Description**: Insert a fixed wait (~150ms) before the corner click in both specs. Matches the validated experiment (0ms gives 0/5 dismiss, 100ms gives 5/5).
- **Addresses hypothesis**: A
- **Does NOT cover**: B
- **Pros**: Trivial one-line change; Directly matches the validated settle experiment
- **Cons**: Magic-number — brittle under slower CI/hardware, a classic flake-bandage; No principled link to an actual readiness signal
- **Complexity**: Low

**Recommended approach**: Gate the two outside-dismissal specs on overlay readiness (test-only) — This option has the smallest blast radius: it edits only the two failing specs, ships no change to any shipped component, and keeps both strict negative assertions exactly as written, so coverage strength is preserved. It reuses an existing convention already established elsewhere in the suite (cited in the approach description) instead of adding new helpers, honoring the reuse-first constitution principle. The alternative — a fixed numeric delay — is rejected as a brittle magic-number that degrades under slower hardware and reads as a flake-bandage; the chosen option keys on a concrete readiness signal and is deterministic.

**Single-layer justification:**
The fix is genuinely spec-layer-local: the production dismissal path works correctly once armed (proven by the Modal CT suite using the identical Radix mechanism, and by the settle experiment making the Dropdown specs deterministic). No shipped/helper-layer change is warranted — the defect is the spec exercising the outside click before the overlay is ready, which is fixed in the spec.

**Cites:**
- DropdownFixture.setOpen

**Proposed call shape:**
```
page.mouse.click(1270, 710)
```

## Constitution Constraints

| Rule | Impact on this change |
|---|---|
| Search before building | A canonical overlay-readiness pattern already exists at Modal.ct.tsx:127 (open-at-mount so the dismiss layer is armed before the corner click); reuse it rather than inventing new test machinery. |
| Minimal changes (Key Rules #3) | Fix is confined to the two failing specs; no shipped/runtime code is touched, so impact is as small as possible. |
| Specs are contracts / strict assertions | The fix must keep expect(menu).not.toBeVisible() strict — it removes a race, it does not weaken the AC-4/AC-3 assertions. |

## Complexity Assessment

| Dimension | Rating | Notes |
|---|---|---|
| Codebase changes | Low | Two test files edited (Dropdown.ct.tsx:185 and :236); a few lines each. |
| Risk | Low | Test-only; no shipped code changes. Risk limited to the readiness-signal choice. |
| Verify cost | Low | Re-run the CT suite; already empirically validated (settle 0 -> 0/5, 100ms -> 5/5). |

## Next step

Copy the block below into a new `/specify` session manually. No automation — user controls when (or if) `/specify` runs.

~~~
/specify "Playwright CT test 'Dropdown — AC-4 dismiss › clicking outside the menu closes it' (Dropdown.ct.tsx:185) fails: after opening the menu and clicking the viewport corner, the menu stays visible; expect(menu).not.toBeVisible() times out (line 200). Downstream, :236 (AC-3 focus-return after click-outside) also fails because the dismissal never fires. CT suite 125/127, these 2 the sole failures. — Both CT tests pass (Dropdown.ct.tsx:185 dismiss + :236 focus-return) via a correct fix at whatever layer the root cause lives; production click-outside dismissal behavior confirmed intact (not a loosened/weakened test)."

Research reference: research/2026-06-27-003-dropdown-ct-click.md
Key facts:
- Mode: Bug
- Symptom: Playwright CT test 'Dropdown — AC-4 dismiss › clicking outside the menu closes it' (Dropdown.ct.tsx:185) fails: after opening the menu and clicking the viewport corner, the menu stays visible; expect(menu).not.toBeVisible() times out (line 200). Downstream, :236 (AC-3 focus-return after click-outside) also fails because the dismissal never fires. CT suite 125/127, these 2 the sole failures.
- Desired: Both CT tests pass (Dropdown.ct.tsx:185 dismiss + :236 focus-return) via a correct fix at whatever layer the root cause lives; production click-outside dismissal behavior confirmed intact (not a loosened/weakened test).
- Recommended approach: Gate the two outside-dismissal specs on overlay readiness (test-only)
- Hypothesis addressed: A
- Hypotheses NOT covered: B
- Open uncertainties: 0 (see research doc §Open Uncertainties)
~~~
