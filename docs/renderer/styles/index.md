---
concern: styles
files: 1
last_indexed: 2026-07-09
package: .
parent_concern: renderer
source_stamp: b9138cb1297b8996
---


# styles

## Purpose

Holds tokens.css, the compiled design-token layer for the renderer: accent, surface, border, and text color variables plus theme scaffolding, generated from design/tokens.json (DTCG) as the single source of truth. Themed at runtime via data-theme and data-mstyle attributes on <html>; values are regenerated from tokens.json, never hand-edited here.

### Fonts (self-hosted)

The font-family tokens `--font-sans` (Inter) and `--font-mono` (JetBrains Mono) are backed by **self-hosted** `@font-face` declarations. The faces are bundled from the `@fontsource/inter` and `@fontsource/jetbrains-mono` packages and declared in a hand-authored stylesheet `src/renderer/src/assets/fonts.css` (Inter 400/500/600/700, JetBrains Mono 400/600/700, latin, `font-display: swap`), imported in `main.tsx` **before** tokens.css. There are no remote font URLs and no CSP change — the woff2 load same-origin from the vite bundle. `tokens.css` stays generated (it holds token *values*, e.g. the `--font-sans` stack ordering); the `@font-face` rules and the woff2 do NOT live here.

## Structure

```text
src/renderer/styles/
└── tokens.css  # Compiled design tokens (color/theme CSS vars) from tokens.json

# related (different concern): src/renderer/src/assets/fonts.css — hand-authored
# @font-face for the self-hosted Inter / JetBrains Mono faces the tokens name.
```
