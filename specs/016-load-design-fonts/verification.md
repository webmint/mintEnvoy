# Feature Verification — 016-load-design-fonts — 2026-07-10

**Feature**: specs/016-load-design-fonts
**Date**: 2026-07-10
**AC Verification Mode**: tests

## Acceptance Criteria

| AC | Status | Evidence |
|---|---|---|
| AC-1 | PASS (code) | `src/renderer/src/assets/fonts.css` exists; header comment reads "Hand-authored @font-face rules"; contains 4 Inter rules (400/500/600/700, lines 16-43) and 3 JetBrains Mono rules (400/600/700, lines 46-66). |
| AC-2 | PASS (code) | `package.json` dependencies include `"@fontsource/inter": "^5.2.8"` and `"@fontsource/jetbrains-mono": "^5.2.8"` (lines 29-30). Both woff2 files confirmed present: `node_modules/@fontsource/inter/files/inter-latin-400-normal.woff2` (23.1K), `node_modules/@fontsource/jetbrains-mono/files/jetbrains-mono-latin-400-normal.woff2` (20.7K). |
| AC-3 | PASS (code) | `src/renderer/src/main.tsx` line 1: `import './assets/fonts.css'` — imported before `../styles/tokens.css` (line 2), matching the required order documented in the file header. |
| AC-4 | PASS (code) | All 7 `url()` values in `fonts.css` are relative paths into `node_modules/@fontsource/*/files/*.woff2` — Vite bundles them locally; no remote fetch. CT at `src/renderer/src/__tests__/font-load.ct.tsx` (lines 31-58) calls `document.fonts.load()` + `document.fonts.check()` for all 7 faces and asserts `toBe(true)`. |
| AC-5 | PASS (code) | `src/renderer/styles/tokens.css` retains all color (`--accent`, `--bg*`, `--border*`, `--text*`, `--m-*`, `--status-*`), shadow (`--shadow-sm/md/lg`), and radius (`--radius-sm/md/lg`) tokens unchanged. Only the font stack tokens (`--font-sans`, `--font-mono`, lines 64-65) and `--fs-*` scale were added/updated; no token removed. |
| AC-6 | PASS (code) | `src/renderer/index.html` CSP (line 9): `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:` — no `font-src`, no remote origins. `src/main/index.ts` adds no `webSecurity: false` or CSP override. Negative grep across all CSS/TS/HTML in `src/` found no `fonts.googleapis`, `fonts.gstatic`, `typekit`, `fontawesome`, `data:font`, or `http.*\.woff` matches. |
| AC-7 | PASS (code) | `tokens.css` line 64: `--font-sans: 'Inter', system-ui, -apple-system, sans-serif` — Inter is primary. `src/renderer/src/assets/base.css` line 57: `body { font-family: var(--font-sans); }`. Lines 45-50: `button, input, select, textarea { font-family: inherit }`. CT (font-load.ct.tsx lines 63-70) asserts `sansFamily` matches `/^["']?Inter["']?/`. |
| AC-8 | PASS (code) | All 7 @font-face rules in `fonts.css` include `font-display: swap` (lines 20, 27, 33, 40, 48, 55, 62). No rule is missing this declaration. |
| AC-12 | PASS (code) | `tokens.css` line 65: `--font-mono: 'JetBrains Mono', 'SF Mono', ui-monospace, Menlo, Consolas, monospace` — JBM is primary. `KVTable.css` line 10: `.kv-cell { ... font-family: var(--font-mono); }` and line 11: `.kv-cell input { ... font-family: var(--font-mono); }`. |
| AC-9 | PASS (code) | `docs/renderer/styles/index.md` lines 17-19 contain a "Fonts (self-hosted)" subsection explicitly stating that `@fontsource/inter` and `@fontsource/jetbrains-mono` are bundled in `src/renderer/src/assets/fonts.css` with Inter 400/500/600/700, JetBrains Mono 400/600/700, latin, `font-display: swap`, imported before tokens.css. |
| AC-10 | PASS (code) | Negative grep for remote font URL patterns (`fonts.googleapis`, `fonts.gstatic`, `typekit`, `use.fontawesome`, `data:font`, `http.*\.woff`) across all `.css`, `.ts`, `.tsx`, `.html` under `src/` returned no matches. Only relative `url()` paths appear in `fonts.css`. |
| AC-11 | PASS (code) | `fonts.css` is a plain CSS file — no TypeScript errors possible. `main.tsx` import syntax is valid Vite/TS. `font-load.ct.tsx` is well-typed (uses `@playwright/experimental-ct-react`, no unresolved imports). No `console.log`, bare `any`, or unused imports in changed files. No obvious lint violations. |
| AC-13 | PASS (code) | Full read of `src/renderer/styles/tokens.css` (330 lines) confirms zero `@font-face` occurrences. The file header explicitly states: "the `@font-face` rules and the woff2 do NOT live here" (line 19 of docs index mirrors this). |

## Code Quality

**Mechanical checks**: PASS
**Cross-task consistency**: see /review report at specs/016-load-design-fonts/review.md
**Scope creep** _(advisory — does not block the verdict)_: 4 changed file(s) outside the planned scope: __snapshots__/components/molecules/__tests__/Tabs.ct.tsx-snapshots/tabbar-fidelity-chromium-darwin.png, __snapshots__/components/organisms/__tests__/RequestBar.ct.tsx-snapshots/request-bar-fidelity-chromium-darwin.png, playwright/index.tsx, src/renderer/src/__tests__/font-load.ct.tsx
**Leftover artifacts**: none detected

## Review Findings

0 confirmed | 0 contested | 2 dismissed | 0 uncertain
Severity breakdown: 0 Critical, 0 High, 0 Medium, 0 Info

## Issues Found

_No confirmed or contested findings in the review report._
## Verdict

**APPROVED**

**Reasons**:

- Hygiene (advisory, non-blocking): 4 scope-creep file(s) — review but does not block the verdict.

**Next step**: run `/summarize` then `/finalize`.
