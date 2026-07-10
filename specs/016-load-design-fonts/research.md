# Research: load-design-fonts

**Date**: 2026-07-09
**Signals detected**: external library not in project deps (@fontsource); first-ever @font-face / self-hosted-webfont pattern in the codebase.

## Questions Investigated

1. How does the app currently load the design fonts? → It does NOT. `tokens.css:62-63` declares `--font-sans` (Inter 3rd) / `--font-mono` (JetBrains Mono 1st) but there is zero `@font-face`, zero bundled woff2, and CSP (`index.html:8`, `default-src 'self'`, no `font-src`) blocks remote Google Fonts. Confirmed statically in `research/2026-07-09-design-fonts-inter-and.md`.
2. Where should `@font-face` live, given `tokens.css` is generated? → In a NEW hand-authored `src/renderer/src/assets/fonts.css`. `docs/renderer/styles/index.md` states `tokens.css` is generated from `design/tokens.json` (DTCG) and never hand-edited; `design/tokens.json` is not even present in the repo. So `@font-face` must NOT go in `tokens.css`.
3. How to self-host Inter + JetBrains Mono with exact weights? → Install `@fontsource/inter` + `@fontsource/jetbrains-mono` (Context7 `/fontsource/fontsource`). Each package ships per-weight woff2 under `@fontsource/<pkg>/files/*.woff2` plus per-weight CSS (`@fontsource/inter/400.css`) whose `@font-face` defaults to `font-display: swap`. To satisfy spec AC-1 (a hand-authored `fonts.css` that declares `@font-face`), we do NOT import the @fontsource per-weight CSS directly; instead we hand-author `fonts.css` `@font-face` rules that source the @fontsource-provided woff2 via `src: url(...)`, keeping `font-display: swap` and control over family names/unicode-range.
4. Does the app apply the sans token to body? → No. `base.css:49-71` (electron-vite starter cruft) hardcodes `body { font-family: Inter, -apple-system, ... }` (Inter FIRST) that does NOT reference `var(--font-sans)`. Design uses `body { font-family: var(--font-sans) }`. So the body sans stack diverges from the token and is already Inter-first. Mono surfaces use `var(--font-mono)` explicitly.

## Alternatives Compared

### Webfont delivery (the big approach-level choice was settled upstream in research; recorded here for provenance)
| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| Self-hosted bundled woff2 + hand-authored @font-face (@fontsource as woff2 source) | Offline-safe; no CSP change; exact-weight control; satisfies AC-1 hand-authored fonts.css | Adds woff2 binaries + 2 npm deps | Chosen |
| Remote Google Fonts + CSP relaxation | Mirrors reference.html exactly; no binaries | Breaks offline launch; loosens CSP — both violate §7 unchanged_behavior | Rejected (settled in upstream research handoff) |

### @fontsource static per-weight vs variable font (sub-decision)
| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| Static per-weight woff2 (Inter 400/500/600/700, JetBrains Mono 400/700) | Matches the spec's discrete weight list exactly; predictable @font-face per weight | 6 woff2 files | Chosen |
| `@fontsource-variable/*` single file | Smaller total; all weights | Spec pins discrete weights; extra variable-axis handling; AC-2 names `@fontsource/*` (static) deps | Rejected |

**Decision**: Self-hosted, `@fontsource/inter` + `@fontsource/jetbrains-mono` as the woff2 source, hand-authored `fonts.css` with `@font-face` (`font-display: swap`) referencing the bundled woff2 — one CSS import added to `main.tsx` before `tokens.css`.

## References
- Context7 `/fontsource/fontsource` — per-weight CSS import (`@fontsource/inter/400.css`), files layout, `font-display: swap` default, variable-vs-static guidance.
- `research/2026-07-09-design-fonts-inter-and.md` — confirmed root cause + self-hosted recommendation (upstream handoff).
- `docs/renderer/styles/index.md` — tokens.css is generated, never hand-edited.
- `design/reference.html` (@font-face + :root) / `design/styles.css` — design intent: Inter + JetBrains Mono, `body { font-family: var(--font-sans) }`.
