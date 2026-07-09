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

## Structure

```text
src/renderer/styles/
└── tokens.css  # Compiled design tokens (color/theme CSS vars) from tokens.json
```
