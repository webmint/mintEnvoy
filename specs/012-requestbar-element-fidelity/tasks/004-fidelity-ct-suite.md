# Task 004: computed-style fidelity ct suite

**Feature**: 012-requestbar-element-fidelity
**Agent**: qa-engineer
**Status**: Complete
**Depends on**: 001, 002, 003
**Blocks**: None
**Spec criteria**: AC-10, AC-11, AC-15, AC-16, AC-17, AC-19
**Review checkpoint**: Yes
**Context docs**: None

## Files

| File                                                              | Action | Description                                                                                                                                                                                                |
| ----------------------------------------------------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| src/renderer/src/components/organisms/**tests**/RequestBar.ct.tsx | Modify | Add computed-style EXACT-equality asserts for url-bar / method-select / Save hover / icon-only Share + a thresholded screenshot diff; cover mstyle variants beyond soft; non-empty-URL no-reflow baseline. |
| src/renderer/src/components/molecules/**tests**/Dropdown.ct.tsx   | Modify | Add open-panel computed-style asserts (shadow / 1px gap / item padding `6px 8px`) + rebaseline the panel screenshot snapshot; keep the Radix two-step dismiss gate.                                        |

## Description

Author the AC-11 fidelity suite — the single owner of ALL computed-style EXACT-equality CT + screenshot rebaselines for this feature (RequestBar props + shared Dropdown panel). Runs in a real browser via Playwright component tests (jsdom cannot resolve computed/pseudo styles). Assert the resolved computed values equal the `design/styles.css` reference for: the `.url-bar` container (border, bg, radius, height, padding, gap, mono font, `:focus-within` ring), the method-select trigger (mono/700/11.5px/0.04em/min-width 88px/padding/border/bg/radius, and per-method colour falling through across mstyle variants — not just `soft`), the Save hover treatment (color `--text` / border-color `--border-strong`), the icon-only Share (accessible name = "Share", no visible text), and the Dropdown open panel (box-shadow `--shadow-lg`, 1px inter-item gap, item padding `6px 8px`). Back each element with a thresholded screenshot diff `toHaveScreenshot(…, { maxDiffPixelRatio: 0.01, threshold: 0.1 })` and deliberately rebaseline the Dropdown panel snapshot. Reuse the established fixture scoping: import `tokens.css`, set `data-mstyle` on the host, apply the Radix two-step dismiss gate, and baseline the no-reflow check with a NON-EMPTY URL (empty→filled conflates the canSend-gated keycap mount with URL-length reflow — see MEMORY `ct-layout-baseline-keycap-confound`).

## Change Details

- In `src/renderer/src/components/organisms/__tests__/RequestBar.ct.tsx`:
  - Add computed-style EXACT-equality asserts (via `getComputedStyle` in-browser) for the `.url-bar` container box (border `1px … var(--border)` resolved, background `--bg-elev` resolved, border-radius `--radius` resolved, height 32px, padding `0 12px`, gap 6px, font-family mono) and its `:focus-within` accent border + `0 0 0 3px` accent-soft ring.
  - Add asserts for the method-select trigger: font-family mono, weight 700, font-size 11.5px, letter-spacing 0.04em, min-width 88px, padding `7px 10px 7px 12px`, border/bg/radius resolved to tokens, and per-method computed `color` correct across MULTIPLE `data-mstyle` variants (e.g. soft + chip + one more), guarding the counter-rule lockstep.
  - Add a Save `:hover` computed-style assert (color `--text`, border-color `--border-strong`) and an icon-only Share assert (accessible name "Share", no visible text child).
  - Add `toHaveScreenshot` diffs with `{ maxDiffPixelRatio: 0.01, threshold: 0.1 }`; baseline the no-reflow check with a non-empty URL.
- In `src/renderer/src/components/molecules/__tests__/Dropdown.ct.tsx`:
  - Add open-panel computed-style asserts: `.dropdown-content` box-shadow resolves to `--shadow-lg`, 1px inter-item gap, `.dropdown-item` padding `6px 8px`, retained `--radius-md` / `--bg-elev` / highlighted `--bg-hover`.
  - Rebaseline the panel screenshot snapshot deliberately (the accepted shared-panel rebind); keep the Radix two-step dismiss gate (wait for overlay readiness before outside click — see MEMORY `ct-radix-dismiss-arm-race`).
  - Reproduce the full styling context in the fixture (tokens.css import + `data-mstyle` host + production className scope — see MEMORY `ct-fidelity-fixture-scoping`); scope `box-sizing:border-box` to the fixture inline, not via global base.css import (see MEMORY `ct-borderbox-harness-import-breaks-screenshots`).

## Contracts

### Expects (checked before execution)

- `RequestBar.tsx` renders the `.url-bar` container + icon-only Share with `aria-label="Share"` (task 001).
- `RequestBar.css` has the `.url-bar` treatment, the method-trigger rule without `justify-content` and without `color`, and the Save rest+hover tokens (task 002).
- `Dropdown.css` `.dropdown-content` uses `var(--shadow-lg)` + 1px gap and `.dropdown-item` padding `6px 8px` (task 003).
- The Playwright CT harness + existing `RequestBar.ct.tsx` / `Dropdown.ct.tsx` fixture patterns (tokens.css import, `data-mstyle` host, Radix dismiss gate) are present.

### Produces (checked after execution)

- `RequestBar.ct.tsx` contains computed-style EXACT-equality asserts for the url-bar, method-select (across ≥2 mstyle variants), Save hover, and icon-only Share, plus `toHaveScreenshot(…, { maxDiffPixelRatio: 0.01, threshold: 0.1 })` diffs and a non-empty-URL no-reflow baseline.
- `Dropdown.ct.tsx` contains computed-style asserts for the panel box-shadow (`--shadow-lg`), 1px gap, and item padding `6px 8px`, plus a rebaselined panel screenshot snapshot and the retained Radix two-step dismiss gate.
- Both CT files run green in the real-browser Playwright runner; the existing behaviour/unit suites stay green.

## Done When

- [x] RequestBar computed-style EXACT-equality asserts for url-bar / method-select / Save hover / icon-only Share present and passing (AC-11)
- [x] Method per-method colour asserted across ≥2 `data-mstyle` variants (not just soft)
- [x] Dropdown panel computed-style asserts (shadow-lg / 1px gap / `6px 8px` item padding) present and passing (AC-10, AC-11)
- [x] `toHaveScreenshot(…, { maxDiffPixelRatio: 0.01, threshold: 0.1 })` diffs added; Dropdown panel snapshot rebaselined
- [x] No-reflow check baselined with a non-empty URL; Radix two-step dismiss gate applied
- [x] Full CT + unit suites pass (AC-19): RequestBar.ct.tsx, Dropdown.ct.tsx, RequestBar.test.tsx
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (`npm run typecheck:web`)
- [x] Linter passes on changed files (`npm run lint`)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-01T09:20:37Z
**Files changed**: src/renderer/src/components/organisms/**tests**/RequestBar.ct.tsx, src/renderer/src/components/molecules/**tests**/Dropdown.ct.tsx, **snapshots**/components/organisms/**tests**/RequestBar.ct.tsx-snapshots/request-bar-fidelity-chromium-darwin.png, **snapshots**/components/molecules/**tests**/Dropdown.ct.tsx-snapshots/dropdown-panel-fidelity-chromium-darwin.png
**Contract**: Expects 4/4 | Produces 3/3
**Notes**: Fidelity CT suite. CT 50/50 green on the two files (whole suite 167/167); unit 34/34; typecheck+lint clean. Retargeted 4 tests to .url-bar; added url-bar/method-select geometry + Save-hover-color asserts; Dropdown panel shadow-lg/1px row-gap/6px8px asserts. 2 screenshots rebaselined (Share icon-only markup + new Dropdown panel). Chip 7-method computed-color block confirmed as the >=2-mstyle-variant guard.
