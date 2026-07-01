# Feature Verification — 005-tab-bar-visual-fidelity — 2026-06-26

**Feature**: specs/005-tab-bar-visual-fidelity
**Date**: 2026-06-26
**AC Verification Mode**: tests

## Acceptance Criteria

| AC    | Status      | Evidence                                                                                                                                |
| ----- | ----------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| AC-1  | PASS (code) | tokens.css `--m-head: #ec4899` (light) / `#f472b6` (dark)                                                                               |
| AC-7  | PASS (code) | tokens.css `.method.HEAD { color: var(--m-head) }`                                                                                      |
| AC-8  | PASS (code) | tokens.css `.method { font-family: var(--font-mono) }`                                                                                  |
| AC-2  | PASS (code) | Tabs.tsx non-closable branch: no dirty/close node when method+dirty absent; Tabs.test.tsx byte-identical cases                          |
| AC-3  | PASS (code) | Tabs.tsx one rovingTabStopIndex; dirty span no tabIndex; close button tabIndex=-1; Tabs.test.tsx count=1                                |
| AC-4  | PASS (code) | TabBar.tsx toDescriptor label unchanged + dirty; Tabs.tsx dirty dot is sibling of button, not label; TabBar.test.tsx                    |
| AC-5  | PASS (code) | TabBar.tsx deriveLabel unchanged (name / method+url / Untitled); TabBar.test.tsx label precedence                                       |
| AC-6  | PASS (code) | Tabs.tsx Delete/Backspace gated on closable (not dirty); dirty span non-focusable; Tabs.test.tsx matrix                                 |
| AC-9  | PASS (code) | Tabs.tsx KNOWN_METHODS+methodChipClassName; chip rendered both branches; Tabs.test/TabBar.test                                          |
| AC-10 | PASS (code) | Tabs.tsx unknown method → cx('method') base only; Tabs.test.tsx uncolored case                                                          |
| AC-11 | PASS (code) | Tabs.css `.tabbar .tabs__tab-wrapper--active::before` 1.5px --accent / `::after` 1px --bg; Tabs.ct.tsx exact assertions                 |
| AC-12 | PASS (code) | Tabs.tsx dirty-XOR-close ternary; dot onClick→onClose+stopProp; Tabs.test.tsx all 4 cases                                               |
| AC-13 | PASS (code) | Tabs.tsx always-visible `<Icon name=x>` close 16px grid; Tabs.css .tabs\_\_tab-close                                                    |
| AC-14 | PASS (code) | TabBar.css .tabbar bg-sunken/36px/padding-right 8px; Tabs.css border-bottom; Tabs.ct.tsx exact assertions                               |
| AC-15 | PASS (code) | Tabs.css .tabbar .tabs\_\_tab-wrapper gap 8px/padding 0 10px 0 12px/border-right; Tabs.ct.tsx wrapper assertions                        |
| AC-16 | PASS (code) | Tabs.css .tabs\_\_tab-label flex:1 + ellipsis; Tabs.ct.tsx flex-grow/text-overflow assertions                                           |
| AC-17 | PASS (code) | Shell.css no .shell**tabs border; Tabs.css .tabs single border; Tabs.ct.tsx .tabbar=1px / .shell**tabs=0px                              |
| AC-18 | PASS (code) | Tabs.ct.tsx Feature-005 fidelity describe — exact computed-style in real Chromium; playwright/index.tsx tokens import                   |
| AC-19 | PASS (code) | tokens.css .method.HEAD + soft variant; Tabs.ct.tsx HEAD chip color rgb(236,72,153) under data-mstyle=soft                              |
| AC-20 | PASS (code) | TabBar.tsx actions slot +/spacer/chevron; TabBar.test.tsx actions row + no-op chevron                                                   |
| AC-21 | PASS (code) | Tabs.ct.tsx toHaveScreenshot threshold 0.2 / maxDiffPixelRatio 0.01 / animations disabled                                               |
| AC-22 | PASS (code) | Tabs.css all new rules .tabbar-compound-scoped; global .tabs unchanged; Tabs.ct.tsx bare-consumer non-regression                        |
| AC-23 | PASS (code) | specs/002-tabs-primitive/spec.md §10 Extension: feature 005 block (fields, XOR-close, byte-identical, .method departure, a11y tradeoff) |
| AC-24 | PASS (code) | Tabs.tsx JSDoc on method? (incl. aria-hidden tradeoff) + dirty? fields                                                                  |
| AC-25 | PASS (code) | Tabs.tsx/TabBar.tsx strict types, no any, method?:string/dirty?:boolean, KNOWN_METHODS as const; typecheck passes                       |
| AC-26 | PASS (code) | ESLint-clean patterns, @renderer alias imports; lint passes                                                                             |
| AC-27 | PASS (code) | Valid import chains, no circular deps; build passes                                                                                     |
| AC-28 | PASS (code) | grep style={{ in Tabs.tsx/TabBar.tsx — only JSDoc/comment text, zero inline style attrs                                                 |
| AC-29 | PASS (code) | grep electron/node: imports in Tabs.tsx/TabBar.tsx — zero matches                                                                       |

## Code Quality

**Mechanical checks**: PASS
**Cross-task consistency**: see /review report at specs/005-tab-bar-visual-fidelity/review.md
**Scope creep** _(advisory — does not block the verdict)_: 1 changed file(s) outside the planned scope: **snapshots**/components/molecules/**tests**/Tabs.ct.tsx-snapshots/tabbar-fidelity-chromium-darwin.png
**Leftover artifacts** _(advisory — does not block the verdict)_: 53 flagged (debug prints / bare TODOs / commented-out code)

## Review Findings

1 confirmed | 0 contested | 2 dismissed | 0 uncertain
Severity breakdown: 0 Critical, 0 High, 0 Medium, 1 Info

## Issues Found

### Info

- [Info] src/renderer/src/components/molecules/**tests**/Tabs.stories.tsx:383 — Incorrect comment — `addTab` is not stable across renders; the empty `useEffect` deps are safe for a different reason

## Verdict

**APPROVED**

**Reasons**:

- Hygiene (advisory, non-blocking): 1 scope-creep file(s), 53 leftover artifact(s) — review but does not block the verdict.

**Next step**: run `/summarize` then `/finalize`.
