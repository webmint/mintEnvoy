# Task 004: CT fidelity util — assertComputedStyle / assertResolvesToToken (fail-closed)

**Feature**: 017-body-editor-shell
**Agent**: qa-engineer
**Status**: Complete
**Depends on**: None
**Blocks**: 010
**Spec criteria**: AC-2, AC-19
**Review checkpoint**: No
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/test-utils/fidelityAssert.ts | Create | Live-renderer computed-style assertion helpers + fail-closed UNVERIFIED channel |

## Description

Build the shared CT fidelity assertion helpers that §8 computed-style assertions depend on, with a **two-layer fail-closed** gate so a missing/broken live-renderer computed-style channel reports UNVERIFIED and never PASS (AC-19). Place them in the existing `src/renderer/src/test-utils/` directory (established convention — it already holds `simulateDrag.ts`). This task builds only the reusable util; BodyEditor.ct.tsx (task 010) consumes it.

## Change Details

- In `src/renderer/src/test-utils/fidelityAssert.ts` (new):
  - `assertComputedStyle(selector, prop, expectedHex)` — reads the live-renderer `getComputedStyle(el).getPropertyValue(prop)` for the element matched by `selector` and asserts it equals `expectedHex` (used for the literal per-theme token hex, AC-20/21).
  - `assertResolvesToToken(selector, prop, tokenVar)` — asserts the computed value of `prop` resolves to the same value the CSS variable `tokenVar` resolves to (used for `.tk-null/.tk-punc/.tk-var` → `var(--text-faint/--text-muted/--accent)`, AC-22).
  - **Layer 1 — setup probe**: a helper that probes whether `getComputedStyle` is available and non-empty; when empty or throwing, the fidelity suite marks itself `test.skip('UNVERIFIED — live-renderer computed-style channel unavailable')` (never PASS, never a plain failure).
  - **Layer 2 — per-assertion guard**: each assertion wraps the channel read in try/catch AND intercepts the critical `getPropertyValue('--x') === ''` (undefined-token returns `""`, not a throw) as UNVERIFIED **before any `expect`** — else a false-green (resolves-to-token) or an unrelated hard-fail (computed-style) leaks through.
  - Carry doc comments describing the fail-closed contract.

## Contracts

### Expects (checked before execution)
- The Playwright experimental-ct-react harness is present (existing `*.ct.tsx` suites run).
- `src/renderer/src/test-utils/` exists (holds `simulateDrag.ts`).

### Produces (checked after execution)
- `src/renderer/src/test-utils/fidelityAssert.ts` exports `assertComputedStyle` and `assertResolvesToToken`.
- A setup-probe path marks the fidelity suite UNVERIFIED (skip) when the computed-style channel is empty/throws.
- Each assertion intercepts `""` from `getPropertyValue` as UNVERIFIED before any `expect`.

## Done When

- [x] `assertComputedStyle` and `assertResolvesToToken` are exported from `test-utils/fidelityAssert.ts` (AC-2).
- [x] The setup probe yields a `test.skip('UNVERIFIED …')` (not PASS, not hard-fail) when `getComputedStyle` is empty/throws (AC-19).
- [x] A `getPropertyValue` returning `""` is intercepted as UNVERIFIED before any `expect` in both helpers (AC-19).
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-11T06:54:46Z
**Files changed**: src/renderer/src/test-utils/fidelityAssert.ts
**Contract**: Expects 2/2 | Produces 3/3
**Notes**: New CT fidelity util: assertComputedStyle + assertResolvesToToken + probeComputedStyleChannel/skipIfChannelUnavailable. Two-layer fail-closed: Layer1 setup probe -> test.skip UNVERIFIED; Layer2 per-assertion try/catch + '' -intercept before expect (blocks the ''===''  false-green). typecheck/lint/build clean. Advisory (accepted as-is): probe cleanup not in try/finally (low-risk test-only node leak). Consumer suite = task 010.
