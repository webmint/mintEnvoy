# Feature Verification — 010-request-bar-fidelity — 2026-06-29

**Feature**: specs/010-request-bar-fidelity
**Date**: 2026-06-29
**AC Verification Mode**: tests

## Acceptance Criteria

| AC    | Status      | Evidence                                                                                                                                                                                                                                                                                                                                                               |
| ----- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AC-1  | PASS (code) | `src/renderer/src/components/organisms/RequestBar.tsx` + `RequestBar.css` both present in scope.json files array                                                                                                                                                                                                                                                       |
| AC-2  | PASS (code) | Grep of RequestBar.tsx returns zero matches for `data-om`, `__OmT`, `tweaks-panel`; file is hand-written production code                                                                                                                                                                                                                                               |
| AC-3  | PASS (code) | The single `data-mstyle` hit in RequestBar.tsx:261 is inside a JSX comment ("resolved by [data-mstyle] written by Shell"); no `setAttribute('data-mstyle', ...)` call anywhere in the component                                                                                                                                                                        |
| AC-4  | PASS (code) | Per-field zustand selectors at RequestBar.tsx:118-126 re-derive from `activeTabId` on every store change; CT test 5 (per-tab isolation) and unit tests (f) assert no bleed                                                                                                                                                                                             |
| AC-7  | PASS (code) | RequestBar.tsx:289 `updateActiveSpec` on URL change; tsx:180-183 `handleSend` calls `onSend`; tsx:186-190 `handleSave` calls `markClean`; tsx:172 `canSend = url.trim() !== ''`; all four paths covered by unit tests (b), (c), (d), (g), (h)                                                                                                                          |
| AC-5  | PASS (code) | RequestBar.css:139 `border-radius: var(--radius)`; css:167-170 `.request-bar__url:focus { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft) }`; CT test "URL input focus: border-color resolves to --accent" at ct.tsx:557                                                                                                                         |
| AC-6  | PASS (code) | RequestBar.css:73-105: `.request-bar .request-bar__method.method` sets `border: 1px solid var(--border)`, `background: var(--bg-elev)`, `border-radius: var(--radius)`, `font-weight: 700`; no `color` declaration → per-method token falls through; CT tests at ct.tsx:616, ct.tsx:653 prove GET/POST colour fall-through                                             |
| AC-8  | PASS (code) | RequestBar.css:50-51 `gap: 8px; padding: 12px 16px`; css:147 `height: 32px` on URL input; css:215 `height: 32px` on Send/Save/Share; CT tests at ct.tsx:471 and ct.tsx:426 assert exact padding/gap and ≥32px heights                                                                                                                                                  |
| AC-9  | PASS (code) | RequestBar.css:233 `background: var(--accent)`, css:235 `font-weight: 600`, css:237-239 `box-shadow: 0 1px 0 rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,0.15)`; tsx:312-315 `{canSend && <kbd aria-hidden="true" className="request-bar__kbd">⌘↵</kbd>}`; CT test at ct.tsx:683 asserts font-weight 600 + non-empty box-shadow                                   |
| AC-10 | PASS (code) | tsx:312 conditional `{canSend && (...kbd...)}` — keycap only mounts when `canSend` is true; unit tests (j) at test.tsx:631, 633 assert kbd absent for empty/whitespace URL; CT test at ct.tsx:727 asserts kbd not attached                                                                                                                                             |
| AC-11 | PASS (code) | tsx:329 `Save` text node, tsx:341 `Share` text node; RequestBar.css:291 Save `border: 1px solid var(--border)`, css:328 Share `border: 1px solid var(--border)`; tsx:339 Share has `disabled aria-disabled="true"`; unit test (i) at test.tsx:609 asserts Share disabled; CT test at ct.tsx:849 asserts visible text + solid borders + Share disabled                  |
| AC-12 | PASS (code) | Every rule in RequestBar.css is either `.request-bar{…}` (root), `.request-bar .request-bar__method.method{…}` (scoped), `.request-bar__*{…}` (prefixed), or `[data-mstyle='chip'] .request-bar .request-bar__method.method.*{…}` (chip counter-rules, still scoped under .request-bar); no bare element or unscoped class selectors that could reach other components |
| AC-13 | PASS (code) | CT suite (ct.tsx:416-1107) has 14 `getComputedStyle` exact-equality assertions; screenshot at ct.tsx:1101 uses `toHaveScreenshot('request-bar-fidelity.png', { maxDiffPixelRatio: 0.01, threshold: 0.1, animations: 'disabled' })`; baseline PNG present in scope.json                                                                                                 |
| AC-14 | PASS (code) | RequestBar.css:1-33 file header documents fidelity scope and token bindings; css:17-22 documents the (0,3,0) ancestor-scoped method-select override; css:26-30 and tsx:297-301 document `aria-hidden` keycap rationale ("purely decorative — the Send button's accessible name remains exactly 'Send'")                                                                |
| AC-15 | PASS (code) | RequestBar.tsx:28 module constraint "Strictly typed, no `any` (§3.1)"; no `any` annotation found in tsx or test files; all function return types declared (e.g., `handleSend(): void`, `handleSave(): void`)                                                                                                                                                           |
| AC-16 | PASS (code) | No ESLint-triggering patterns found: no console.log, no unused imports, no `any`, proper React hooks usage; RequestBar.css uses `/* stylelint-disable no-descending-specificity */` for intentional chip counter-rules (legitimate suppression)                                                                                                                        |
| AC-17 | PASS (code) | Imports are all aliased (`@renderer/...`) and resolve to existing modules visible in the codebase; CSS imported via relative path tsx:33; no circular imports or missing exports                                                                                                                                                                                       |
| AC-18 | PASS (code) | RequestBar.tsx contains no `style={{` JSX attribute in executable code; the module comment at tsx:27 mentions the prohibition ("No inline `style={{...}}`") but does not use one; grep of tsx shows zero `style={{` occurrences                                                                                                                                        |
| AC-19 | PASS (code) | RequestBar.test.tsx has 27 `it(...)` cases across 9 describe blocks covering trim guard, send, method dropdown, save, tab isolation, ⌘↵, ⌘S, Share stub, keycap markup; RequestBar.ct.tsx has 29 test cases across 7 describe blocks with real-Chromium computed-style proofs; feature description states 29/29 CT passing                                             |

## Code Quality

**Mechanical checks**: PASS
**Cross-task consistency**: see /review report at specs/010-request-bar-fidelity/review.md
**Scope creep** _(advisory — does not block the verdict)_: 1 changed file(s) outside the planned scope: **snapshots**/components/organisms/**tests**/RequestBar.ct.tsx-snapshots/request-bar-fidelity-chromium-darwin.png
**Leftover artifacts** _(advisory — does not block the verdict)_: 31 flagged (debug prints / bare TODOs / commented-out code)

## Review Findings

1 confirmed | 0 contested | 0 dismissed | 0 uncertain
Severity breakdown: 0 Critical, 0 High, 0 Medium, 1 Info

## Issues Found

### Info

- [Info] src/renderer/src/components/organisms/**tests**/RequestBar.ct.tsx:1029 — Cross-task blind-spot — Task 002 adds method-button hover CSS, Task 003 adds Save hover CT but omits method-button hover CT

## Verdict

**APPROVED**

**Reasons**:

- Hygiene (advisory, non-blocking): 1 scope-creep file(s), 31 leftover artifact(s) — review but does not block the verdict.

**Next step**: run `/summarize` then `/finalize`.
