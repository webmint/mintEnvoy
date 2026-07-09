---
concern: renderer
last_indexed: 2026-07-09
package: .
source_stamp: 39cbc7488a62b93b
split: True
---


# renderer

## Purpose

The Electron renderer process — the entire React 19 user interface plus its compiled design-token layer. Splits into the src application (atomic-design components, zustand stores, renderer-only domain model and utilities) and styles (the generated tokens.css that binds every component's color and theme to design/tokens.json). Everything here is renderer-pure: no node or electron imports cross into this process.

## Sub-concerns

- src — React 19 app: atomic-design components (atoms/molecules/organisms + shell), zustand stores, renderer-only request domain model and pure utilities. ([→](src/index.md))
- styles — Compiled design-token CSS (tokens.css) generated from design/tokens.json — color, surface, border, text vars themed via data-theme/data-mstyle. ([→](styles/index.md))
