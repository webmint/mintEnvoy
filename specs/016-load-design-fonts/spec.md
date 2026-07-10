# Spec: load-design-fonts

**Date**: 2026-07-09
**Status**: Complete
**Design source**: html:design/reference.html
**Author**: Claude + User

## 1. Overview

The renderer declares Inter (--font-sans) and JetBrains Mono (--font-mono) in its design-token font stacks but never loads the faces — there is no @font-face, no bundled font file, and the CSP blocks remote Google Fonts — so every surface renders in system fallbacks (San Francisco / SF Mono), a pervasive visual mismatch vs design/reference.html. This feature self-hosts the faces: it bundles Inter (400/500/600/700) and JetBrains Mono (400/700) as woff2 via @fontsource, declares them with local @font-face (font-display: swap) in a new hand-authored fonts.css imported before tokens.css, and reorders the sans stack so Inter actually renders. It is offline-safe, requires no CSP change, and does not hand-edit the generated tokens.css.

## 2. Current State

tokens.css (src/renderer/styles/tokens.css:62-63) declares --font-sans (naming 'Inter' third, after -apple-system/BlinkMacSystemFont) and --font-mono (naming 'JetBrains Mono' first), but NO @font-face, @import, <link>, or bundled .woff2/.woff/.ttf exists anywhere in src/renderer (research/2026-07-09-design-fonts-inter-and.md confirms this statically). The renderer CSP (src/renderer/index.html:8, default-src 'self', no font-src) blocks remote Google Fonts, so design/reference.html's gstatic @font-face cannot be reused. main.tsx (src/renderer/src/main.tsx:1-2) imports tokens.css then assets/main.css. base.css (src/renderer/src/assets/base.css:49-71) sets body to a HARDCODED font-family 'Inter, -apple-system, BlinkMacSystemFont, ...' (electron-vite starter cruft, Inter first) that does NOT reference var(--font-sans) — so the app's body sans stack both diverges from the token and is already Inter-first; base.css also sets -webkit-font-smoothing: antialiased + text-rendering: optimizeLegibility. Mono surfaces (KVTable cells, code, method chips) use var(--font-mono) explicitly. Live: document.fonts has zero loaded faces; sans computes to -apple-system (SF), mono to SF Mono/Menlo. tokens.css is GENERATED from design/tokens.json (DTCG) per docs/renderer/styles/index.md and is never hand-edited (tokens.json is not present in the repo). No @fontsource dependency is installed.

## 3. Desired Behavior

Inter (weights 400/500/600/700) and JetBrains Mono (weights 400/700) shall load as self-hosted woff2 and render across the UI, matching the design's intended typefaces. A new hand-authored stylesheet src/renderer/src/assets/fonts.css shall declare the faces via local @font-face with font-display: swap, and shall be imported in main.tsx before tokens.css; the generated tokens.css shall NOT be hand-edited. The sans font stack shall be reordered so 'Inter' precedes -apple-system, and the base.css hardcoded body font-family shall be reconciled to align with the --font-sans token, so body/sans text renders Inter (including on macOS). Mono surfaces shall render JetBrains Mono. Loading shall require no network access and no CSP change (self-hosted, same-origin). Existing design-token colors, spacing, radius, geometry, and theme behavior shall be unchanged — only the rendered typeface changes. Success is verified by document.fonts reporting the faces loaded and getComputedStyle resolving to Inter / JetBrains Mono in the running app; affected Playwright CT screenshot baselines are regenerated to reflect the new typefaces.

## 4. Affected Areas

| Area | Files | Impact |
|------|-------|--------|
| src/main | src/main/index.ts:6 | see findings |
| Font assets + @font-face stylesheet | src/renderer/src/assets/fonts.css, src/renderer/src/assets/fonts/ | Create new — new hand-authored fonts.css with local @font-face rules (font-display: swap) for Inter 400/500/600/700 + JetBrains Mono 400/700, sourcing self-hosted woff2 (via @fontsource) |
| Renderer entry import chain | src/renderer/src/main.tsx | Modify — import the new fonts.css before tokens.css so @font-face is registered; no logic change |
| Sans font stack (token + starter cruft) | src/renderer/styles/tokens.css, src/renderer/src/assets/base.css | Modify — reorder --font-sans so Inter precedes -apple-system, and reconcile base.css hardcoded body font-family to use var(--font-sans); tokens.css must not be hand-edited (generated) so the token reorder is resolved in /plan (token source vs override) |
| Build dependencies | package.json | Modify — add @fontsource/inter + @fontsource/jetbrains-mono as dependencies (self-hosted woff2, bundled by vite) |
| Font-fidelity tests + baselines | src/renderer/src/components/**/__tests__/, playwright.config.ts | Create/extend — add a font-load verification (document.fonts / computed fontFamily) and regenerate affected CT screenshot baselines to reflect the real typefaces (delete stale PNGs then regenerate) |

## 5. Acceptance Criteria

Each AC must be testable and unambiguous. **Cover each category that applies. Mark non-applicable categories with "N/A — [reason]".**

### 5.1 Tooling / artifact presence and absence

- [x] **AC-1**: The renderer shall provide a hand-authored fonts stylesheet that declares @font-face rules for Inter and JetBrains Mono.
  > Verification: test -f src/renderer/src/assets/fonts.css && grep -q '@font-face' src/renderer/src/assets/fonts.css
- [x] **AC-2**: The renderer shall bundle self-hosted Inter and JetBrains Mono webfonts via @fontsource dependencies.
  > Verification: grep -q '@fontsource/inter' package.json && grep -q '@fontsource/jetbrains-mono' package.json
- [x] **AC-3**: The renderer entry shall import the fonts stylesheet.
  > Verification: grep -q "assets/fonts.css" src/renderer/src/main.tsx

### 5.2 Behavior preservation

- [x] **AC-4**: WHILE the app runs with no network access, the renderer shall load and render Inter and JetBrains Mono from self-hosted assets.
- [x] **AC-5**: The renderer shall preserve existing design-token colors, spacing, radius, and theme behavior, changing only the rendered typeface.
- [x] **AC-6**: The renderer Content-Security-Policy shall remain unchanged, adding no remote font or style origins.
  > Verification: ! grep -Eq 'fonts\.(googleapis|gstatic)\.com' src/renderer/index.html

### 5.3 Behavior change

- [x] **AC-7**: WHEN the app renders sans or body text, the renderer shall display Inter (including on macOS), matching the design mockup.
  > Q-3 resolution (user-directed): match the DESIGN MOCKUP, which renders Inter. The design's own --font-sans CSS is -apple-system-first (so it renders San Francisco on a native Mac, like reference.html), but the mockup is rendered off-Mac where -apple-system is absent, so it shows Inter — the intended brand face. The app therefore leads --font-sans with 'Inter' so macOS renders Inter to match the mockup. Mono renders JetBrains Mono (AC-12).
- [x] **AC-8**: The renderer shall declare every bundled @font-face with font-display set to swap.
  > Verification: grep -q 'font-display: *swap' src/renderer/src/assets/fonts.css
- [x] **AC-12**: WHEN the app renders a mono surface such as a KVTable cell or a code block, the renderer shall display JetBrains Mono.

### 5.4 CI / pipeline

N/A — No CI/pipeline configuration changes — this is a renderer asset + stylesheet change; existing build/test commands are unchanged

### 5.5 Hooks / gates

N/A — No new hooks or gates — no pre-commit/CI gate is added or modified by bundling fonts

### 5.6 Documentation

- [x] **AC-9**: The project documentation shall record that Inter and JetBrains Mono are self-hosted via the fonts stylesheet.

### 5.7 Hygiene

- [x] **AC-10**: The renderer source shall contain no remote font URLs.
  > Verification: ! grep -rEq 'fonts\.(googleapis|gstatic)\.com' src/renderer
- [x] **AC-11**: The project shall pass type-check, lint, and build with the font changes in place.
  > Verification: npm run typecheck && npm run lint && npm run build
- [x] **AC-13**: The generated design-token stylesheet shall contain no @font-face rule.
  > Verification: ! grep -q '@font-face' src/renderer/styles/tokens.css

## 6. Out of Scope

**Coverage rule (v3)**: For each Phase 1.5 finding, the finding either (a) becomes an AC in §5, (b) becomes a Constraint in §7, (c) is explicitly listed here as out of scope, OR (d) is in §9 Risks with documented mitigation. Unlanded finding = hard error — re-verify Phase 1.5 enumeration is complete before saving.

- NOT included: Remote / Google Fonts loading (fonts.gstatic.com @font-face + preconnect) — explicitly rejected; fonts are self-hosted — F-2026-07-09-design-fonts-inter-and-2
- NOT included: Non-latin font subsets (Cyrillic, Greek, Vietnamese) — latin woff2 only
- NOT included: Font weights beyond Inter 400/500/600/700 and JetBrains Mono 400/700; variable-font single-file approach
- NOT included: Broader design-token pipeline / tokens.json regeneration work, and removing electron-vite starter cruft in base.css beyond reconciling the body font-family — F-index-5
- NOT included: Never importing design-export markup/cruft (data-om-*, __OmT, tweaks-panel) from reference.html; class-based styling only, no inline styles — F-constitution-3

## 7. Technical Constraints

- Must follow: Sec4 Prefer design tokens (CSS custom properties in tokens.css) over literal style values
- Must follow: Sec2.1 Process Boundaries -- Never import Node/Electron in the renderer
- Must follow: Design Fidelity (design_token_provenance)
- Must follow: Do NOT hand-edit the generated tokens.css (generated from design/tokens.json per docs/renderer/styles/index.md); the @font-face rules live in a separate hand-authored fonts.css and any --font-sans reorder is resolved at the token source in /plan
- Must follow: Reuse the established fidelity-test precedent (Playwright CT computed-style + thresholded screenshot diff over a tokens.css fixture) and reconcile stale baselines by deleting then regenerating the PNGs
- Must not break: Offline launch must keep working: fonts load from self-hosted same-origin assets with no network dependency
- Must not break: Existing design-token colors, spacing, radius, geometry, and theme (data-theme/data-mstyle) behavior must not regress; base.css antialiasing/text-rendering settings preserved
- Must follow constitution §2.1: Process Boundaries: the renderer must not import Node/Electron; font loading stays a renderer-side declarative concern (CSS @font-face + vite-served assets), never routed through the main process

## 8. Open Questions

- **Q-1**: tokens.css is documented as generated from design/tokens.json, but tokens.json is not present in the repo. /plan must resolve where the --font-sans reorder lands: edit the (absent/external) token source, treat tokens.css as the de-facto source, or override --font-sans in the hand-authored fonts.css
- **Q-2**: Should base.css's hardcoded body font-family (Inter-first starter cruft) be replaced with var(--font-sans) for design parity (design uses body font-family var(--font-sans)), or reordered in place? /plan decides the reconciliation
- **Q-3**: design/reference.html's --font-sans is also -apple-system-first, so the reference renders San Francisco for sans on macOS. Reordering to Inter-first makes the app render Inter on macOS: matching design INTENT but diverging from what reference.html actually renders. Confirm the fidelity check asserts the intended typeface (Inter) not the reference mac-resolved face
- **DP-existing_behavior-1** [no DP in category existing_behavior]: no relevant decision point for existing_behavior
- **DP-edge_cases-1** [no DP in category edge_cases]: no relevant decision point for edge_cases
- **DP-breaking_changes-1** [no DP in category breaking_changes]: no relevant decision point for breaking_changes

## 9. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Typeface change on mono surfaces is intended but alters rendering; FOUT/layout-shift risk mitigated by font-display: swap and metric-compatible fallbacks; existing CT screenshot baselines will likely need regeneration (sub-threshold diffs leave stale baselines) | Med | Med | tbd via /plan |
| Sans reorder makes the app render Inter on macOS while reference.html renders SF; a strict computed-style CT fidelity check vs the reference could flag a mismatch | Med | Med | Assert the fidelity check against the intended typeface (Inter/JetBrains Mono) not reference.html's mac-resolved face; document the intent-over-reference decision |
| FOUT / layout shift from font swap alters existing CT screenshot baselines | High | Low | font-display: swap + metric-compatible fallbacks; delete then regenerate affected CT PNG baselines (sub-threshold diffs otherwise leave them stale) |
| A future tokens.css regeneration overwrites any @font-face or reorder placed directly in tokens.css | Med | Med | Keep @font-face in the separate fonts.css; resolve the --font-sans reorder at the token source, never by hand-editing generated tokens.css |
| @fontsource adds woff2 binaries to the bundle | Low | Low | Latin subset only, static weights (Inter 400/500/600/700 + JetBrains Mono 400/700) |
