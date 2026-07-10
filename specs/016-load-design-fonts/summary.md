# Feature Summary — 016-load-design-fonts

**Verdict**: APPROVED (see `verification.md`) · **Status**: Complete · 13/13 acceptance criteria PASS

## What was built

mintEnvoy now renders its UI in the intended design typefaces — **Inter** for sans/body text and **JetBrains Mono** for code and mono surfaces — self-hosted from the app bundle instead of relying on system-fallback fonts. The typefaces load with no network access (no Google Fonts, no CSP change), so the running app matches the design mockup on every platform, including macOS where it previously fell back to San Francisco.

## Changes

- **Self-hosted webfonts** — bundled Inter and JetBrains Mono via `@fontsource` packages; no remote font URLs.
- **Hand-authored `@font-face` layer** — a new `fonts.css` declares every face (Inter 400/500/600/700, JetBrains Mono 400/600/700) with `font-display: swap`, referencing the bundled woff2 by relative path so Vite fingerprints and emits them.
- **Inter-first token stack** — reordered `--font-sans` so Inter leads; `body` now resolves to the design font.
- **Form controls inherit the app font** — added a `button, input, select, textarea { font-family: inherit }` reset so Titlebar buttons and the KVTable delete button render Inter (they previously showed the browser default, Arial).
- **Documentation** — recorded the self-hosted-fonts setup in the renderer styles docs.
- **Fidelity test** — a Playwright CT asserts the faces actually load and the tokens resolve to them (and that the form-control reset propagates Inter), rather than a brittle pixel-diff.

## Files changed

32 files changed, +2019 / −16.

- `src/renderer/src/assets/fonts.css` — new `@font-face` layer (self-hosted Inter + JetBrains Mono)
- `src/renderer/src/assets/base.css` — `body` → `var(--font-sans)`; form-control `font-family: inherit` reset
- `src/renderer/styles/tokens.css` — Inter-first `--font-sans`
- `src/renderer/src/main.tsx` — imports `fonts.css` before `tokens.css`
- `src/renderer/src/__tests__/font-load.ct.tsx` + `playwright/index.tsx` — font-load fidelity CT + harness import
- `package.json` / `package-lock.json` — `@fontsource/inter`, `@fontsource/jetbrains-mono`
- `docs/renderer/styles/index.md` — self-hosted-fonts documentation
- `__snapshots__/…` — regenerated Tabs + RequestBar fidelity baselines
- `specs/016-load-design-fonts/…`, `research/…` — planning + research artifacts

## Key decisions

- **`@font-face` delivery** — a single hand-authored `fonts.css` with explicit `@font-face` rules (not a `@fontsource` bare-import), because Vite does not resolve bare-specifier font URLs in CSS `url()`.
- **`url()` for bundling** — point `url()` into `@fontsource/*/files/*.woff2` by relative path so Vite fingerprints and emits the woff2 into the renderer bundle.
- **`--font-sans` reorder** — edit the token value in `tokens.css` (Inter first) rather than restructure the stack elsewhere.
- **`base.css` body rule** — resolve `body` font through `var(--font-sans)` so the token stays the single source of truth.
- **Fidelity assertion** — assert the LOADED typeface at runtime via `document.fonts`, not a pixel-diff (which would only confirm platform-fallback glyphs; the reference renders SF on macOS).

## Deviations from plan

- **JetBrains Mono 600 added** beyond the plan's 400/700 — weight 600 is the design contract for the `dot`-mstyle method chip; `fonts.css`, docs, and the CT were aligned to 400/600/700.
- **Form-control `font-family: inherit` reset added** to `base.css` — not in the original plan; surfaced by the review accessibility audit (buttons rendered Arial because form elements don't inherit `body`'s font per the UA stylesheet) and remediated via `/fix`, with a dedicated regression CT.
- **Font-load CT coverage expanded** — the test now verifies every declared weight (Inter 400/500/600/700, JBM 400/600/700) plus button font inheritance, not just 400/700.

## Acceptance criteria

All 13 PASS (verbatim from `verification.md`):

- [x] AC-1 — hand-authored fonts stylesheet with `@font-face` for Inter + JetBrains Mono
- [x] AC-2 — self-hosted Inter + JetBrains Mono bundled via `@fontsource`
- [x] AC-3 — renderer entry imports the fonts stylesheet
- [x] AC-4 — loads + renders both faces from self-hosted assets with no network
- [x] AC-5 — existing design-token colors/spacing/radius/theme preserved
- [x] AC-6 — CSP unchanged, no remote font/style origins added
- [x] AC-7 — sans/body text renders Inter (including macOS)
- [x] AC-8 — every `@font-face` declares `font-display: swap`
- [x] AC-9 — docs record the self-hosted fonts
- [x] AC-10 — no remote font URLs in renderer source
- [x] AC-11 — type-check, lint, and build pass
- [x] AC-12 — mono surfaces render JetBrains Mono
- [x] AC-13 — generated token stylesheet contains no `@font-face`
