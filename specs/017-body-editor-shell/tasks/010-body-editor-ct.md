# Task 010: BodyEditor CT — fidelity + behavior

**Feature**: 017-body-editor-shell
**Agent**: qa-engineer
**Status**: Complete
**Depends on**: 004, 006, 009
**Blocks**: None
**Spec criteria**: AC-6, AC-7, AC-8, AC-9, AC-10, AC-14, AC-16, AC-17, AC-18, AC-19, AC-20, AC-21, AC-22, AC-23, AC-24
**Review checkpoint**: Yes
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/organisms/__tests__/BodyEditor.stories.tsx | Create | Mounted fixtures (theme wrappers + seeded body states) |
| src/renderer/src/components/organisms/__tests__/BodyEditor.ct.tsx | Create | Fidelity (computed-style) + behavior CT over the fixtures |

## Description

Author the BodyEditor component tests. Per the codebase CT convention (Playwright experimental-ct-react requires mounted components in a separate file), create both a `.stories.tsx` fixture file and the `.ct.tsx` suite. The fidelity half uses the `test-utils/fidelityAssert.ts` helpers (task 004) so §8 computed-style assertions run fail-closed (UNVERIFIED, never PASS, when the channel is unavailable — AC-19). The behavior half exercises the radiogroup, mode switch, lang-pill, cross-mode round-trip, and degrade paths.

## Change Details

- In `src/renderer/src/components/organisms/__tests__/BodyEditor.stories.tsx` (new):
  - Export mounted fixtures wrapping `BodyEditor` (with a stub `renderUrlencoded`) in a container that sets `data-theme` — a **light** wrapper and a **dark** wrapper (so AC-20 light + AC-21 dark can BOTH be exercised).
  - Export store-seeded mounts for the body states needed: none, raw+json, raw+xml (non-JSON), urlencoded, empty raw text, malformed JSON.
  - Reproduce the full styling context (tokens.css import, production className scope, box-sizing scoped to the fixture) per the CT fidelity-fixture-scoping lesson.
- In `src/renderer/src/components/organisms/__tests__/BodyEditor.ct.tsx` (new):
  - **Fidelity** (via task 004 utils): `assertComputedStyle` for `.tk-key/str/num/bool` literal hex in the light fixture (AC-20) and dark fixture (AC-21) — assert ALL FOUR tokens in BOTH theme contexts (toggle `data-theme='dark'` on the dark fixture root); a light-only or subset assertion leaves the dark hex unverified (carried from task 009 review); `assertResolvesToToken` for `.tk-null → var(--text-faint)`, `.tk-punc → var(--text-muted)`, `.tk-var → var(--accent)` (AC-22); `.code-editor` grid `36px 1fr` (AC-24); gutter row height == computed pre line-height + gutter node count == rendered line count + single shared scrollTop (AC-23); exercise the fail-closed probe so an unavailable channel reports UNVERIFIED (AC-19).
  - **Behavior**: six radio options present + default none (AC-7); `role=radiogroup`/`role=radio`/`aria-checked`/arrow-key roving focus (AC-18) — MUST also assert (carried from task 006 review): **Space/Enter selects** the focused radio, **ArrowLeft/Up wraps** from the first option to the last, and the **lang-pill CYCLE order** json→xml→html→text→json with a 4th click wrapping back to json (a transposed cycle array would else pass); also assert the **textarea→pre scroll sync** (force overflow, scroll the textarea, assert the `<pre>` overlay scrollTop/Left matches) and the **BLANK_BODY fallback** (component mounts cleanly with `active:'none'` + empty text when the store body is absent); selecting a type switches the visible panel with all panels still mounted (AC-6); lang-pill defaults JSON + XML/HTML/Text selectable (AC-8); rendered two-pass highlight in `<pre>` — var-pass-wins for JSON (AC-9), var-only for non-JSON (AC-10); empty raw text → zero highlight tokens, no throw (AC-16); malformed JSON → plain `var(--text)`, no throw, no error UI (AC-17); switch body-type away and back restores each mode's value (AC-14).

## Contracts

### Expects (checked before execution)
- `assertComputedStyle`/`assertResolvesToToken` + the fail-closed probe are exported from `test-utils/fidelityAssert.ts` (task 004).
- `BodyEditor` is mountable with a `renderUrlencoded` render-prop and carries the `data-testid`s from `design-manifest.json` (task 006).
- `--tk-key/str/num/bool` tokens exist in tokens.css (task 009).

### Produces (checked after execution)
- `BodyEditor.stories.tsx` exports light + dark theme wrappers and the seeded body-state mounts.
- `BodyEditor.ct.tsx` asserts the §8 fidelity set (fail-closed) and the behavior set above.

## Done When

- [x] `BodyEditor.stories.tsx` + `BodyEditor.ct.tsx` exist; the suite mounts via the stories fixtures.
- [x] Light-theme tk-* hex (AC-20), dark-theme tk-* hex (AC-21), resolves-to-token (AC-22), grid (AC-24), and gutter/pre alignment (AC-23) assertions run via the fail-closed util.
- [x] The channel-unavailable path reports UNVERIFIED, never PASS (AC-19).
- [x] Behavior assertions cover AC-6, AC-7, AC-8, AC-9, AC-10, AC-14, AC-16, AC-17, AC-18.
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-14T11:31:45Z
**Files changed**: src/renderer/src/components/organisms/__tests__/BodyEditor.stories.tsx, src/renderer/src/components/organisms/__tests__/BodyEditor.ct.tsx
**Contract**: Expects 3/3 | Produces 2/2
**Notes**: New BodyEditor CT: 9 stories fixtures + 18 tests, ALL PASS. Fidelity (per-theme tk-* hex light+dark AC-20/21, resolves-to-token AC-22, grid AC-24, gutter/line AC-23, fail-closed AC-19) + behavior (AC-6/7/8/9/10/14/16/17/18). Authored+run in main thread after qa-engineer subagent stalled on 600s watchdog (~16min no output). 1 review-panel repair round strengthened AC-6 (not.toBeVisible), AC-7 (aria-checked flip), AC-17 (role=alert count 0). Fixes found by running suite: (1) [[ct-tokens-import-alias-trap]] recurred - removed broken @renderer/styles/tokens.css local import (relies on global playwright/index.tsx); (2) getByLabel exact-match for Request-body/Request-body-type collision; (3) cleared stale playwright/.cache. FOLLOW-UP: KVTable.stories.tsx still has the same broken tokens import (latent bug, worth /report-bug).
