# Feature Verification — 013-tabs-contrast-wcag — 2026-07-03

**Feature**: specs/013-tabs-contrast-wcag
**Date**: 2026-07-03
**AC Verification Mode**: tests

## Acceptance Criteria

| AC | Status | Evidence |
|---|---|---|
| AC-1 | PASS (code) | tokens.css:28 `--text-muted: #6c6c75;` (light), tokens.css:29 `--text-faint: #6e6e77;` (light), tokens.css:88 `--text-faint: #787881;` (dark) — all three required values present. design/tokens.json:26 `"textMuted":"#6c6c75"`, :27 `"textFaint":"#6e6e77"`, :40 `"textFaint":"#787881"` match. |
| AC-2 | PASS (code) | tokens.css `:root` text group contains only the four pre-existing names (`--text`, `--text-muted`, `--text-faint`, `--text-inverse`); `[data-theme='dark']` block mirrors them. design/tokens.json `color.light` and `color.dark` objects are structurally identical to the pre-013 schema — no new key added. |
| AC-3 | PASS (code) | Active tab: Tabs.css:149 `color: var(--text)`. Inactive tab: Tabs.css:97 `color: var(--text-muted)`. CT test Tabs.ct.tsx:1504 asserts `expect(v.active).not.toBe(v.inactive)` (light); Tabs.ct.tsx:1533 asserts same for dark. Different tokens guarantee inequality in both themes. |
| AC-4 | PASS (code) | Light `--text-muted: #6c6c75` (4.69:1 on `--bg: #fbfaf9`), light `--text-faint: #6e6e77` (4.55:1), dark `--text-faint: #787881` (4.58:1) — all above the WCAG AA 4.5:1 normal-text / 3:1 non-text threshold as stated in spec. Active-label token `--text` (#18181b) gives 15.98:1. All three synced sites verified present in tokens.css:28-29 and tokens.css:87-88. |
| AC-5 | PASS (code) | Tabs.css:147-153 `.tabs__tab--active, .tabs__tab[aria-selected='true'] { color: var(--text); }`. The `.tabbar` override (Tabs.css:481-484) sets only `box-shadow: none; background: transparent` — color is not overridden, so the tabbar variant inherits `var(--text)`. CT tests Tabs.ct.tsx:1500 (`rgb(24,24,27)` light) and Tabs.ct.tsx:1529 (`rgb(244,244,245)` dark) assert the resolved value. |
| AC-6 | PASS (code) | Tabs.css:230-234 `.tabs__tab--active .tabs__badge { background-color: var(--accent-soft,...); color: var(--text); }`. CT test Tabs.ct.tsx:1545 asserts `v.color === TEXT_LIGHT` (rgb(24,24,27)) and `v.color !== v.background` for light; Tabs.ct.tsx:1564 asserts `v.color === TEXT_DARK` (rgb(244,244,245)) and `v.color !== v.background` for dark. TabbarBadgeFidelityFixture exported at Tabs.stories.tsx:657. |
| AC-7 | PASS (code) | Tabs.css:97 `.tabs__tab { color: var(--text-muted); }`. tokens.css:28 `--text-muted: #6c6c75` (light, 4.69:1); tokens.css:87 `--text-muted: #a1a1aa` (dark, unchanged). CT test Tabs.ct.tsx:1501 asserts `v.inactive === MUTED_LIGHT` (`rgb(108,108,117)`); Tabs.ct.tsx:1530 asserts `v.inactive === MUTED_DARK` (`rgb(161,161,170)`). |
| AC-8 | PASS (code) | Tabs.css:326 `.tabs__tab-close { color: var(--text-faint); }`. tokens.css:29 `--text-faint: #6e6e77` (light, 4.55:1); tokens.css:88 `--text-faint: #787881` (dark, 4.58:1). CT test Tabs.ct.tsx:1502 asserts `v.close === FAINT_LIGHT` (`rgb(110,110,119)`); Tabs.ct.tsx:1531 asserts `v.close === FAINT_DARK` (`rgb(120,120,129)`). |
| AC-9 | PASS (code) | Tabs.css:384-393 `.tabs__tab-dirty { background: var(--text-faint); }`. Same token values as AC-8. CT test Tabs.ct.tsx:1503 asserts `v.dirty === FAINT_LIGHT` (backgroundColor); Tabs.ct.tsx:1532 asserts `v.dirty === FAINT_DARK`. |
| AC-10 | PASS (code) | tokens.css: syntactically valid CSS, all declarations properly terminated. Tabs.css: no unterminated rules or invalid properties observed. Tabs.ct.tsx: all named imports (`TabbarBadgeFidelityFixture`, `TabsBadgeFidelityFixture`, etc.) verified present as exports in Tabs.stories.tsx:657 and Tabs.stories.tsx:694 respectively. tokens.json: valid DTCG JSON. No type-unsafe constructs introduced in the TypeScript changes. Mechanical suite runs separately. |

## Code Quality

**Mechanical checks**: PASS
**Cross-task consistency**: see /review report at specs/013-tabs-contrast-wcag/review.md
**Scope creep** _(advisory — does not block the verdict)_: 1 changed file(s) outside the planned scope: src/renderer/src/components/molecules/__tests__/Tabs.stories.tsx
**Leftover artifacts** _(advisory — does not block the verdict)_: 38 flagged (debug prints / bare TODOs / commented-out code)

## Review Findings

1 confirmed | 0 contested | 0 dismissed | 0 uncertain
Severity breakdown: 0 Critical, 0 High, 0 Medium, 1 Info

## Issues Found

### Info

- [Info] src/renderer/src/components/molecules/Tabs.css:149 — Cross-task divergence: Task 002 inline "departure from convention" comment overstates uniqueness after the F1-fix commit drops 6 more fallbacks from the same file without any comment

## Verdict

**APPROVED**

**Reasons**:

- Hygiene (advisory, non-blocking): 1 scope-creep file(s), 38 leftover artifact(s) — review but does not block the verdict.

**Next step**: run `/summarize` then `/finalize`.
