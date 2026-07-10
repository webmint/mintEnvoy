# Plan: load-design-fonts

**Date**: 2026-07-09
**Spec**: specs/016-load-design-fonts/spec.md
**Status**: Approved

## Specialist Consultation

**Invocations**:
- Phase 0 alternatives: no — the approach-level alternative (self-hosted vs remote Google Fonts + CSP relaxation) was settled in the upstream research handoff (`research/2026-07-09-design-fonts-inter-and/handoff.json`); the remaining sub-choice (static per-weight vs variable font) is mechanical (spec pins discrete weights). See research.md §Alternatives Compared.
- Phase 1.3 architecture decisions: yes (mandatory). First dispatch stalled on the 600s stream watchdog (known subagent-tool-use stall); re-dispatched self-contained with facts embedded + no-tools, which completed.
- Specialists consulted: none (see table).

**Architect-authored sections** (transcribed verbatim from architect return):
- Layer Map: rows 1-6
- Key Design Decisions: rows D1-D5
- Risk Assessment seeds: 3 seeds (folded with spec §9 risks)
- Constitution Compliance flags: §2.1, §4, Design Fidelity, generated-tokens.css tension

| Specialist | Sub-question | Input summary | Verdict | Cites |
| --- | --- | --- | --- | --- |
| architect | Layer map + key design decisions + constitution/OOS trace for self-hosted font loading | Authored D1-D5, layer map, risk seeds; flagged D2/D3 as DEPARTUREs; no specialist consult needed | accepted | specs/016-load-design-fonts/spec.md; own-reasoning |
| (none) | — | — | — | — |

## Summary

Self-host the design fonts the app declares but never loads. Add `@fontsource/inter` + `@fontsource/jetbrains-mono` as the woff2 source, hand-author `src/renderer/src/assets/fonts.css` with `@font-face` (Inter 400/500/600/700, JetBrains Mono 400/700, `font-display: swap`) sourcing the bundled woff2 via `url()`, and import it in `main.tsx` before `tokens.css`. Reorder `--font-sans` (Inter first) in `tokens.css` and repoint `base.css`'s hardcoded starter body rule at `var(--font-sans)` so sans renders Inter. Offline-safe, no CSP change, no `@font-face` in the generated `tokens.css`.

**Why no new research beyond research.md**: the approach was settled upstream; research.md adds only the `@fontsource` integration detail (Context7 `/fontsource/fontsource`): per-weight woff2 under `@fontsource/<pkg>/files/*.woff2`, `font-display: swap` default, and that AC-1's hand-authored requirement rules out importing the vendor per-weight CSS directly.

## Technical Context

**Architecture**: Renderer-only (React 19 / renderer-pure). Touches the renderer style layer (`fonts.css` new, `tokens.css`, `base.css`) + the renderer entry (`main.tsx`) + `package.json`. `src/main` (createWindow) and the CSP (`index.html`) are context only — no change (same-origin `url()` fonts need no `font-src`).
**Error Handling**: N/A — declarative CSS + asset bundling; graceful degradation to the existing fallback stack is inherent to CSS if a face fails to load.
**State Management**: N/A — no runtime state; fonts load via CSS `@font-face` at renderer boot.

## Constitution Compliance

- §2.1 Process Boundaries (no Node/Electron in renderer): compliant — all changes are CSS + a CSS import; `@fontsource` is a build-time CSS/asset dependency (`url()`), never a JS `require` of node/electron.
- §4 Prefer design tokens / no literal font-family: compliant — D3 removes the last hardcoded `font-family` literal (base.css body) in favor of `var(--font-sans)`; `fonts.css` declares faces (allowed) but applies no family literals to elements.
- Design Fidelity (design_token_provenance): compliant — app now loads Inter + JetBrains Mono; verified via loaded-typeface assertion (D4), not a platform-confounded pixel-diff.
- "Do not hand-edit generated tokens.css" (§7): compliant-with-note — acknowledged DEPARTURE (D2). No `design/tokens.json` or generator exists in the repo, so `tokens.css` is the de-facto source; the edit is value-only (reorder), adds no `@font-face` (AC-13 holds), and carries a restore-to-pipeline comment.

## Implementation Approach

### Layer Map

| Layer | What | Files (existing or new) |
|-------|------|------------------------|
| Renderer styles (primary) | New hand-authored `@font-face` block referencing bundled woff2 | `src/renderer/src/assets/fonts.css` (new) |
| Renderer styles | Reorder `--font-sans` so Inter precedes `-apple-system` (value-only) | `src/renderer/styles/tokens.css:62` |
| Renderer styles | Replace hardcoded `body{font-family: Inter, …}` cruft with `var(--font-sans)` | `src/renderer/src/assets/base.css:49-71` |
| Renderer entry | Import `fonts.css` BEFORE `tokens.css` | `src/renderer/src/main.tsx` |
| Build/deps | `@fontsource/inter` + `@fontsource/jetbrains-mono` as woff2 source | `package.json` |
| Main (context only — NO change) | `createWindow`/CSP owner; confirms `font-src` not needed (same-origin) | `src/main/index.ts`, `src/renderer/index.html:8` |

### Key Design Decisions

| Decision | Chosen Approach | Why | Alternatives Rejected |
|----------|----------------|-----|----------------------|
| D1 — `@font-face` delivery | Single hand-authored `fonts.css` with explicit `@font-face` per weight (Inter 400/500/600/700, JetBrains Mono 400/700), `font-display:swap`, `url()` → `@fontsource` woff2 | AC-1 forces hand-authored `@font-face`; AC-8 swap; one file = one reviewable provenance surface, decoupled from `@fontsource` CSS internals | Importing each `@fontsource/*/400.css`: violates AC-1 (not hand-authored), pulls in vendor `@font-face` we don't control, harder to pin latin-only/weights (§6 OOS creep) |
| D2 — `--font-sans` reorder location | Edit value in `tokens.css:62` (Inter first); value-only, NO `@font-face` added; leave a comment: "move to design/tokens.json if generation pipeline is restored" | tokens.css is the de-facto in-repo source (tokens.json + script absent); AC-7 needs Inter to win on macOS; AC-13 holds (value edit, no `@font-face`). **DEPARTURE**: editing a file documented "GENERATED, never hand-edit" — justified: no generator/source exists, so the doc-invariant is unenforceable and tokens.css IS the source | Adding `@font-face` here: breaks AC-13. Overriding order in fonts.css/base.css: splits the sans stack across two files, harder to trace |
| D3 — base.css body rule | Replace `body{font-family: Inter, -apple-system, …}` with `body{font-family: var(--font-sans)}`; keep antialiasing/optimizeLegibility | Design parity (design body uses `var(--font-sans)`); §4 no hardcoded font-family literal; makes the D2 reorder actually take effect. **DEPARTURE**: replacing electron-vite starter body rule — justified as removing starter cruft, in feature intent | Leaving cruft: hardcoded `Inter` first would mask the token, silently diverge from design, violate §4 |
| D4 — fidelity assertion | Assert LOADED typeface at runtime: `document.fonts.check`/`.load` for Inter + JetBrains Mono AND `getComputedStyle().fontFamily` resolves to them; NOT a pixel-diff vs `reference.html` | `reference.html` on macOS renders `-apple-system`/SF for sans, so a pixel-diff would assert the wrong (fallback) glyphs; AC-7/AC-12 are about the loaded face, not pixel match; AC-5 (colors/geometry) stays a separate token assertion | Screenshot pixel-diff vs reference: false pass/fail from platform font substitution (per memory: CT fidelity misses typeface) |
| D5 — woff2 reference for bundling | `url()` points into `@fontsource/*/files/*.woff2` inside `node_modules`; let electron-vite/vite fingerprint + emit them; NO manual copy to `assets/fonts/` | Single source of truth (the dep), no duplicated binaries in-repo, vite already fingerprints CSS `url()` assets; AC-4 offline satisfied (bundled at build), AC-10 no remote URLs | Copying woff2 into `src/renderer/src/assets/fonts/`: duplicates binaries, manual sync burden, drifts from `@fontsource` version |

### Established-Convention Departures

| Departure | Established Pattern Left | Why Necessary |
|-----------|--------------------------|---------------|
| D2 — edit `--font-sans` value directly in `tokens.css` | `tokens.css` is documented (docs/renderer/styles/index.md) as generated from `design/tokens.json`, never hand-edited | No `design/tokens.json` and no generation script exist in the repo, so the "generated" invariant is unenforceable and `tokens.css` is the de-facto source. Edit is value-only (no `@font-face`, AC-13 holds) with an inline restore-to-pipeline comment |
| D3 — replace `base.css` body `font-family` with `var(--font-sans)` | electron-vite starter `base.css` hardcodes a body font stack (Inter-first literal) not tied to the token | Design parity requires `body{font-family:var(--font-sans)}`; the hardcoded literal masks the token and violates §4 (prefer tokens over literals). Removing starter cruft is in the feature's intent |

### File Impact

| File | Action | What Changes |
|------|--------|-------------|
| src/renderer/src/assets/fonts.css | Create | Hand-authored `@font-face` × 6 (Inter 400/500/600/700, JetBrains Mono 400/700), `font-display: swap`, `src: url()` → `@fontsource` woff2 (latin) |
| src/renderer/src/main.tsx | Modify | Add `import './assets/fonts.css'` BEFORE `import '../styles/tokens.css'` |
| src/renderer/styles/tokens.css | Modify | Reorder `--font-sans:62` so `'Inter'` precedes `-apple-system`; add restore-to-pipeline comment. No `@font-face`. No other token change |
| src/renderer/src/assets/base.css | Modify | Replace body `font-family` literal stack with `var(--font-sans)`; keep antialiasing/optimizeLegibility/other body props |
| package.json | Modify | Add `@fontsource/inter` + `@fontsource/jetbrains-mono` (dependencies) |
| src/renderer/src/components/**/__tests__/ (font-load CT) | Create/Modify | Add a loaded-typeface assertion (document.fonts + getComputedStyle == Inter/JetBrains Mono) per D4; regenerate affected CT screenshot baselines (rm + re-generate stale PNGs) |

### Documentation Impact

| Doc File | Action | What Changes |
|----------|--------|-------------|
| docs/renderer/styles/index.md | Update | Record `fonts.css` as the second file in the styles concern; note self-hosted Inter/JetBrains Mono via `@font-face` (AC-9) |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `@fontsource` `url()` path fails to resolve/bundle in electron-vite renderer build | Med | Med | Reference the exact `@fontsource/*/files/*-latin-<w>-normal.woff2` paths; verify the built bundle emits the woff2 + resolves at the renderer origin (dev + `electron-vite build`) as part of AC-4/AC-11 |
| Editing GENERATED `tokens.css` is normalized away if a token pipeline is later restored | Med | Med | Value-only reorder + inline "restore via design/tokens.json" comment; AC-13 gate asserts no `@font-face` lands there; scope stays §6-bounded |
| Sans reorder → app renders Inter on macOS while reference.html renders SF; strict pixel-diff CT vs reference would flag it | Med | Med | Assert the intended LOADED typeface (D4), not a pixel-diff vs reference's mac-resolved face; document intent-over-reference |
| FOUT / layout shift from `font-display: swap` alters existing CT screenshot baselines | High | Low | `swap` is intended (AC-8) + metric-compatible fallbacks; rm + regenerate affected CT PNG baselines (sub-threshold diffs otherwise stay stale) |
| Renderer-purity regression via `@fontsource` | Low | High | CSS `url()`/asset-only path (D5), never a JS `require` of node/electron; typecheck confirms no node imports (AC-11) |
| `@fontsource` adds woff2 binaries to the bundle | Low | Low | Latin subset only, static weights (Inter 400/500/600/700 + JetBrains Mono 400/700) |

## Dependencies

- `@fontsource/inter` — npm dependency (woff2 source for Inter 400/500/600/700, latin).
- `@fontsource/jetbrains-mono` — npm dependency (woff2 source for JetBrains Mono 400/700, latin).
- No services, no environment variables, no CSP change.

## Supporting Documents

- [Research](research.md) — webfont delivery + `@fontsource` integration (Context7).
