# Plan: dropdown-ct-dismiss

**Date**: 2026-06-27
**Spec**: specs/008-dropdown-ct-dismiss/spec.md
**Status**: Approved

## Specialist Consultation

**Invocations**:

- Phase 0 alternatives: no — N/A. No external-library / new-integration / out-of-stack signal; everything is within the existing Playwright CT + DOM stack, and the upstream research handoff supplies prior art (recommended approach + cited canonical pattern). The one open decision (readiness API) was resolved by the mandatory Phase 1.3 architect consultation, not by alternative-comparison research.
- Phase 1.3 architecture decisions: yes (mandatory).
- Specialists consulted (orchestrator-relayed on the architect's request, or directly): none — see table below.

**Architect-authored sections** (transcribed verbatim from architect return):

- Layer Map: rows 1-2
- Key Design Decisions: rows 1-4
- Risk Assessment seeds: rows 1-4
- Constitution Compliance flags: none

| Specialist | Sub-question | Input summary | Verdict | Cites |
| ---------- | ------------ | ------------- | ------- | ----- |
| (none)     | —            | —             | —       | —     |

The architect emitted zero consultation requests: a fully-diagnosed test-timing fix within renderer test-infrastructure is generalist scope; a domain specialist would be disproportionate.

## Summary

Two Playwright component tests for Dropdown click-outside dismissal fail because each fires its outside click before Radix's `DismissableLayer` arms its `pointerdown` listener (deferred via `setTimeout(0)` during the entry animation). The fix is test-only: before each corner click, gate on a concrete overlay-readiness signal — await the menu's running animations to finish, then yield one `setTimeout(0)` macrotask boundary as a motion-independent floor that guarantees Radix's own earlier-queued `setTimeout(0)` listener has fired. The single click and the strict assertions stay verbatim; no production code changes.

## Technical Context

**Architecture**: Renderer test layer only (`src/renderer/src/components/molecules/__tests__/`). No process-boundary (main/preload/renderer) or production-component surface is touched — constitution §2.1/§2.2 are not in play.
**Error Handling**: N/A — test-only change; no fallible runtime path added.
**State Management**: N/A — no store or component state changed. The production controlled-dropdown path (`DropdownFixture.setOpen` ← Radix `onOpenChange`) is unchanged.

## Constitution Compliance

- §3.4 Testing (co-located `.ct.tsx`): compliant — the fix stays inside `Dropdown.ct.tsx`; no fixture change needed.
- §6.3 Search before building: compliant — reuses the Modal-suite "armed before outside-click" _intent_ (Modal.ct.tsx:127). Modal's literal open-at-mount can't transfer (Dropdown opens via trigger), and there is no third caller, so no new shared test helper is extracted (DRY rule-of-three unmet).
- §6.1 Minimal changes: compliant — only the two failing test cases are edited.
- §2.1/§2.2 Process & tier boundaries: compliant — no production/process surface touched.

## Implementation Approach

### Layer Map

| Layer                                     | What                                                                                                                                                               | Files (existing or new)                                                                                                                                                     |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Renderer · component-test (Playwright CT) | Before each corner click, gate the single outside click on an animation-completion await + a `setTimeout(0)` macrotask-boundary floor; strict assertions unchanged | `src/renderer/src/components/molecules/__tests__/Dropdown.ct.tsx` (two cases — dismiss at `:185`, outside click at `:198`; focus-return at `:236`, outside click at `:253`) |
| Renderer · CT fixture                     | No change — preferred design needs no fixture affordance                                                                                                           | `src/renderer/src/components/molecules/__tests__/Dropdown.stories.tsx` (untouched)                                                                                          |

### Key Design Decisions

| Decision             | Chosen Approach                                                                                                                                                           | Why                                                                                                                                                                                                                                                                                                                                                                                                        | Alternatives Rejected                                                                                                                                                                                                                                                                                                                                           |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Readiness-signal API | `await menu.evaluate(el => Promise.all(el.getAnimations().map(a => a.finished)))` **then** one in-page `setTimeout(0)` macrotask-boundary yield, before each corner click | Deterministic in CT (140ms entry animation ≫ Radix's `setTimeout(0)`, so the listener is armed) AND motion-independent (the 0-delay floor crosses the macrotask boundary after Radix's earlier-queued `setTimeout(0)` even when no animation exists). The `0` is an event-loop ordering primitive, not a hardware-racing duration → outside §6's magic-number rationale. Satisfies AC-3/4/5 and §9 Risk-1. | (A) animation-await alone — `Promise.all([])` resolves immediately under zero-animation → §9 Risk-1 resurfaces. (B) `waitForFunction` opacity-poll — same animation dependency, brittle computed-style read. (C) single rAF/microtask — does not order after a `setTimeout(0)` macrotask → false determinism. `waitForTimeout(150)` — §6 OOS bare magic-number. |
| Action fidelity      | Keep a **single** outside corner click per test                                                                                                                           | AC-1/AC-3/AC-4 model "a user clicks outside" once; gate the click, do not repeat it                                                                                                                                                                                                                                                                                                                        | `expect(async () => { click; assert }).toPass()` — re-dispatches the click, diverging from the single-click interaction the ACs model                                                                                                                                                                                                                           |
| Scope confinement    | Edit only the two failing cases; fixture + production Dropdown untouched                                                                                                  | §6 exclusions + constitution §6.1; production path proven correct by Modal CT                                                                                                                                                                                                                                                                                                                              | Touching `Dropdown.tsx`/Radix (§6); hardening Modal/nested-overlays CT (§6)                                                                                                                                                                                                                                                                                     |
| Reuse                | Conceptual reuse of Modal's "armed-before-dismissal" convention via the readiness wait                                                                                    | Constitution §6.3 — Modal's literal open-at-mount can't transfer (Dropdown opens via trigger), so reuse the intent                                                                                                                                                                                                                                                                                         | A new shared test helper — no third caller (DRY rule-of-three unmet)                                                                                                                                                                                                                                                                                            |

### File Impact

| File                                                            | Action | What Changes                                                                                                                                                                                                                                                                                                                                                                                                           |
| --------------------------------------------------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| src/renderer/src/components/molecules/**tests**/Dropdown.ct.tsx | Modify | In the two failing cases, insert the readiness gate (animation-completion await + `setTimeout(0)` floor) immediately before the corner clicks at `:198` and `:253`. Add a one-line comment on the `setTimeout(0)` line explaining it is a macrotask-boundary readiness floor (so the `/implement` review panel does not read it as a banned fixed-delay sleep). Strict assertions at `:200`, `:256`, `:259` unchanged. |

### Documentation Impact

No documentation changes expected — internal test-only fix; no package role, concern Purpose/Structure, or cross-package architecture changes.

## Risk Assessment

| Risk                                                                                     | Likelihood | Impact | Mitigation                                                                                                                                                                               |
| ---------------------------------------------------------------------------------------- | ---------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Reviewer mistakes the `setTimeout(0)` floor for a banned fixed-delay sleep (§6)          | Low        | Low    | Breakdown mandates an explanatory comment on that line and pairs it with the named animation-completion await so intent reads as readiness, not duration.                                |
| One macrotask turn assumed sufficient but the arm needs more                             | Low        | Med    | The animation-completion await already crosses far past one turn in CT; the `setTimeout(0)` floor is only the zero-animation backstop; AC-5's repeated-run check catches residual flake. |
| Focus-return case: corner click blurs the trigger before arm                             | Low        | Low    | Assert `toBeFocused()` once, after the readiness-gated single click; Radix `FocusScope` restores focus to the trigger on dismiss.                                                        |
| Breakdown drifts to a `toPass` retry loop                                                | Low        | Low    | Decision 2 fixes a single click; the breakdown task flags this explicitly.                                                                                                               |
| Production Dropdown dismissal regresses in the future, masked by the wait (§7 not-break) | Low        | Low    | Assertions stay strict (`not.toBeVisible` / `toBeFocused`), so a real dismissal break still fails after the wait.                                                                        |

## Dependencies

None — no packages to install, no services to configure, no environment variables. Uses the existing `@playwright/experimental-ct-react` stack and the DOM `Element.getAnimations()` API.

## Supporting Documents

- [Research](../../research/2026-06-27-003-dropdown-ct-click.md) — root-cause investigation + recommended approach (no new research.md: no deep-research signals; in-stack, prior art from the upstream handoff).
