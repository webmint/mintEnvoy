# Feature Verification — 018-code-editor-extract — 2026-07-19

**Feature**: specs/018-code-editor-extract
**Date**: 2026-07-19
**AC Verification Mode**: tests

## Acceptance Criteria

| AC | Status | Evidence |
|---|---|---|
| AC-1 | PASS (code) | BodyEditor.tsx (219 lines) contains no `.code-editor-content` markup; raw slot at lines 185–193 delegates entirely to `<CodeEditor>`. BodyEditor.css (26 lines) has no `.code-editor*` rules. |
| AC-9 | PASS (code) | File exists and is valid: `/Users/mykolakudlyk/Projects/private/mintEnvoy/src/renderer/src/components/molecules/CodeEditor.tsx` (191 lines, exported `CodeEditor` memo component). |
| AC-10 | PASS (code) | File exists: `/Users/mykolakudlyk/Projects/private/mintEnvoy/src/renderer/src/components/molecules/CodeEditor.css` (117 lines, imported via `import './CodeEditor.css'` at CodeEditor.tsx:19). |
| AC-2 | PASS (code) | jsonTokens.ts:364–372 — catch block returns `[{ kind: 'plain', text }]`, no throw. CodeEditor.tsx:174–175 — pre renders `<span>{value}</span>` (pre-debounce) or `<span>{t.text}</span>` (plain token post-debounce). CodeEditor.ct.tsx:408–423 test asserts no `.tk-*` spans appear. |
| AC-3 | PASS (code) | jsonTokens.ts:262–291 `overlayVarsInJsonString()` splits `tk-str`/`tk-key` token content on `{{var}}` and emits `tk-var` (var-pass-wins). compose() at lines 376–384 applies overlay for every string/key token. |
| AC-4 | PASS (code) | BodyEditor.tsx:182–216 — all 6 panels always mounted (mount-all), hidden attribute toggled. resetKey={activeTabId} (line 187) is unchanged on same-tab mode switch so CodeEditor.tsx:77–87 `useEffect([resetKey])` does NOT fire. LIVE-CONFIRMED: scroll 60/40 preserved; caret 25/40 preserved. BodyEditor.ct.tsx:883–970 covers this. |
| AC-5 | PASS (code) | CodeEditor.tsx:136–155 `tokenSpans` — every span uses JSX `{t.text}` children. Line 174: pre renders `{showColored ? tokenSpans : <span>{value}</span>}`. No `dangerouslySetInnerHTML` or `.innerHTML` anywhere in CodeEditor.tsx. |
| AC-6 | PASS (code) | CodeEditor.tsx:77–87 `useEffect([resetKey])` sets `setColored(null)` and resets `scrollTop`/`scrollLeft` to 0 on both `textareaRef` and `preRef`. BodyEditor.tsx:187 passes `resetKey={activeTabId}`. LIVE-CONFIRMED. CodeEditor.ct.tsx:232–331 tests both clear+re-arm and scroll-reset. |
| AC-7 | PASS (code) | BodyEditor.tsx:182 (`none` → `<div hidden=.../>`) and lines 195–200 (`urlencoded` render-prop) are structurally unchanged from the pre-extraction pattern. BodyEditor.ct.tsx:60–72 and 500–509 verify these slots independently. |
| AC-8 | PASS (code) | CodeEditor.tsx:160 `data-testid="body-code-editor"`, line 162 `data-testid="body-gutter"`, line 174 `data-testid="body-pre"` — all three testids present on the extracted molecule. |
| AC-11 | PASS (code) | CodeEditor.tsx:22 `import { compose } from '@renderer/lib/jsonTokens'`. Line 96: `const tokens = compose(value, lang, validVars)` in debounce effect. jsonTokens.ts compose() is the same unchanged lib function. LIVE-CONFIRMED: typing updates store and pre re-renders with token spans. |
| AC-12 | PASS (code) | CodeEditor.css:9 `--code-line-h: calc(12.5px * 1.65);` declared on `.code-editor`. Line 27: `.code-editor .gutter > div { height: var(--code-line-h); }`. Line 78: `pre { line-height: var(--code-line-h); }`. Line 107: `textarea { line-height: var(--code-line-h); }`. All three layers use the single var. |
| AC-13 | PASS (code) | CodeEditor.css:9 `--code-line-h: calc(12.5px * 1.65)` uses absolute `px` values, not relative units — independent of inherited `font-size` or `line-height`. CodeEditor.ct.tsx:356–385 test mounts with ancestor `font-size:20px / line-height:3` and asserts all three = 20.625px. |
| AC-14 | PASS (code) | CodeEditor.tsx:27 `const BODY_HIGHLIGHT_DEBOUNCE_MS = 100`. Lines 63–66: internal `colored` state. Lines 94–101: internal debounce `useEffect`. Props interface lines 31–45: `value`, `lang`, `onChange`, `validVars`, optional `resetKey`. No store imports. |
| AC-15 | PASS (code) | CodeEditor.tsx resides at `src/renderer/src/components/molecules/CodeEditor.tsx`. BodyEditor.tsx:31: `import { CodeEditor } from '@renderer/components/molecules/CodeEditor'` — organism-to-molecule import, satisfying §2.2 (no sibling-organism import). |
| AC-16 | PASS (code) | fidelityAssert.ts:86–89 `skipIfChannelUnavailable()` calls `test.skip(!available, 'UNVERIFIED...')`. Layer-2 guards (lines 130–147, 200–245) skip on `""` response. CodeEditor.ct.tsx: all six computed-style tests call `await skipIfChannelUnavailable(page)` (lines 63, 109, 130, 153, 362, 497). |
| AC-17 | PASS (code) | CodeEditor.css:29–35: all seven tk-* classes (`tk-key`, `tk-str`, `tk-num`, `tk-bool`, `tk-null`, `tk-punc`, `tk-var`) using design tokens. Lines 8–17: `.code-editor { display:grid; grid-template-columns:36px 1fr; }`. Line 27: gutter geometry. CodeEditor.ct.tsx:105–159 fidelity tests verify light/dark literals and token bindings. |
| AC-21 | PASS (code) | CodeEditor.css:9 `--code-line-h: calc(12.5px * 1.65) /* = 20.625px */`. Gutter: `height: var(--code-line-h)` (line 27). Pre: `line-height: var(--code-line-h)` (line 78). Textarea: `line-height: var(--code-line-h)` (line 107). `12.5 × 1.65 = 20.625`. CodeEditor.ct.tsx:57–92 asserts all three equal `'20.625px'` at runtime. |
| AC-18 | PASS (code) | docs/architecture.md:30 — molecules row documents "CodeEditor — domain-agnostic self-contained three-layer overlay code editor... consumed by BodyEditor (resetKey={activeTabId})". docs/renderer/src/index.md:61 — "CodeEditor.tsx — Self-contained three-layer overlay editor... reuses jsonTokens.compose; consumed by BodyEditor". Module/Package Structure at architecture.md:97 lists CodeEditor in molecules. |
| AC-19 | PASS (code) | All imports use `@renderer` alias; types are explicit (no `any`); eslint-disable at CodeEditor.tsx:100 is legitimate (validVars stable singleton rationale documented). Supplementary mechanical evidence: "PASSED this run" (typecheck + eslint). |
| AC-20 | PASS (code) | CodeEditor.css:9 `--code-line-h: calc(12.5px * 1.65)` — absolute px, no `em`. Line 27 `.code-editor .gutter > div { height: var(--code-line-h); }`. The string `1.65em` does not appear anywhere in CodeEditor.css (117 lines verified in full). |

## Code Quality

**Mechanical checks**: PASS
**Cross-task consistency**: see /review report at specs/018-code-editor-extract/review.md
**Scope creep** _(advisory — does not block the verdict)_: 1 changed file(s) outside the planned scope: src/renderer/src/components/molecules/__tests__/CodeEditor.stories.tsx
**Leftover artifacts** _(advisory — does not block the verdict)_: 34 flagged (debug prints / bare TODOs / commented-out code)

## Review Findings

0 confirmed | 0 contested | 1 dismissed | 0 uncertain
Severity breakdown: 0 Critical, 0 High, 0 Medium, 0 Info

## Issues Found

_No confirmed or contested findings in the review report._
## Verdict

**APPROVED**

**Reasons**:

- Hygiene (advisory, non-blocking): 1 scope-creep file(s), 34 leftover artifact(s) — review but does not block the verdict.

**Next step**: run `/summarize` then `/finalize`.
