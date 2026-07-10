# Research: tokens.css declares font-family stacks naming 'Inter' (sans) and 'JetBrains Mono' (mono), but no @font-face rule, @import, <link>, or bundled font file exists anywhere in the app, so all UI text renders in system fallbacks (-apple-system/SF, SF Mono) instead of the design typefaces, producing a pervasive visual mismatch vs design/reference.html


**Date**: 2026-07-09
**Topic**: tokens.css declares font-family stacks naming 'Inter' (sans) and 'JetBrains Mono' (mono), but no @font-face rule, @import, <link>, or bundled font file exists anywhere in the app, so all UI text renders in system fallbacks (-apple-system/SF, SF Mono) instead of the design typefaces, producing a pervasive visual mismatch vs design/reference.html
**Mode**: Bug
**Verdict**: Root cause confirmed

## Summary

The renderer declares font-family stacks naming Inter (--font-sans) and JetBrains Mono (--font-mono) in src/renderer/styles/tokens.css, but the @font-face declarations design/reference.html uses to load those faces (from Google Fonts) were never ported to the app and no font files were bundled -- so both named faces have no source and every surface falls back to system fonts (San Francisco / SF Mono). CSP (default-src 'self', no font-src) additionally blocks the design's remote gstatic @font-face, so the fix must be self-hosted. Root cause is confirmed statically: zero @font-face and zero font files exist under src/renderer (a probe script reproduces this deterministically). Recommended fix: bundle Inter (400/500/600/700) + JetBrains Mono woff2 under a vite-served assets path and add self-hosted @font-face rules -- no CSP change, offline-safe. One nuance is held as an open question: --font-sans lists -apple-system before Inter, so on macOS sans stays San Francisco even after loading; the dominant visible gap is the mono surfaces, and a sans reorder is outside the confirmed minimal scope.

## Symptom

| Dimension | Value |
|---|---|
| Symptom | tokens.css declares font-family stacks naming 'Inter' (sans) and 'JetBrains Mono' (mono), but no @font-face rule, @import, <link>, or bundled font file exists anywhere in the app, so all UI text renders in system fallbacks (-apple-system/SF, SF Mono) instead of the design typefaces, producing a pervasive visual mismatch vs design/reference.html |
| Affected area | src/renderer/styles/tokens.css (--font-sans/--font-mono design tokens; app-wide text rendering). The renderer Content-Security-Policy (no font-src directive) is a constraint on the fix and is captured in Codebase Findings. |
| Repro / Current | Launch the app in dev or built mode with no font assets present; all text renders in system fallback faces (-apple-system sans, SF Mono/Menlo mono) rather than Inter and JetBrains Mono; comparing side-by-side with design/reference.html (which loads Inter+JetBrains Mono via Google Fonts @font-face) shows a typeface mismatch across every surface |
| Desired | Inter and JetBrains Mono actually load and render, matching design/reference.html, via self-hosted bundled woff2 files declared with local @font-face rules — no network dependency, no CSP change |
| Scope | one place (evidence: src/renderer/styles/tokens.css:62) |

## Codebase Findings (WHERE)

| Surface | File:line | Relevance | Framing |
|---|---|---|---|
| sans font token declaration | src/renderer/styles/tokens.css:62 | --font-sans names 'Inter' (3rd, after -apple-system/BlinkMacSystemFont) but no @font-face/@import/font file exists -> Inter never loads; primary symptom site | primary |
| mono font token declaration | src/renderer/styles/tokens.css:63 | --font-mono names 'JetBrains Mono' (1st in stack) but no @font-face exists -> clearest visible fallback to SF Mono on all mono surfaces (KVTable cells, code, method chips) | primary |
| renderer CSP meta | src/renderer/index.html:8 | CSP default-src 'self' with no font-src -> remote Google Fonts (fonts.gstatic.com) are blocked; only self-hosted same-origin fonts are permitted, forcing a bundled solution | primary |
| renderer CSS entry import | src/renderer/src/main.tsx:1 | renderer entry imports '../styles/tokens.css'; this is the CSS load chain where @font-face rules (in tokens.css or a new fonts.css imported here) take effect | primary |
| main-process window load origin | src/main/index.ts:6 | createWindow loads the renderer via loadURL(dev http)/loadFile(prod file://); establishes the origin under which self-hosted @font-face url() font assets must resolve | primary |
| canonical-pattern search (primary) | (none) | canonical pattern -- reusable: no canonical pattern found project-wide for @font-face / self-hosted webfont loading (only design/reference.html and a devforge parser contain @font-face); new @font-face setup is justified | primary |
| sans stack ordering (runner-up) | src/renderer/styles/tokens.css:62 | --font-sans lists -apple-system before 'Inter'; on macOS San Francisco wins even when Inter is loaded, so the sans mismatch is order-masked and platform-conditional -- supports runner-up framing that the mono stack is the real gap | runner-up |
| canonical-pattern search (runner-up) | (none) | no canonical pattern found project-wide for font-stack reordering / Inter-first sans; if the runner-up is pursued the reorder is a fresh token change | runner-up |

## Root Cause Hypothesis (WHY)

**Primary hypothesis**: The renderer never loads Inter or JetBrains Mono: tokens.css declares the font-family stacks that name them, but the @font-face declarations present in design/reference.html were never ported to the app and no font files were bundled, so both named faces have no source and every surface falls back to system fonts.

**Confidence**: Confirmed

### Structured root cause

| Field | Value |
|---|---|
| trigger | The renderer paints any text; the --font-sans/--font-mono tokens name Inter and JetBrains Mono but the faces are unavailable |
| root_cause | The design->app port copied font-family token values from design/styles.css but omitted design/reference.html's @font-face rules and never bundled the font files, leaving the named web fonts sourceless |
| contributing_factors | 1. CSP default-src 'self' with no font-src blocks a simple re-add of the design's gstatic @font-face, so remote loading is not an option 2. --font-sans lists -apple-system before 'Inter', masking sans on macOS even once Inter loads 3. resources/ holds only icon.png (electron-builder assets, not renderer-served), so the bug file's 'bundle in resources/' suggestion would not resolve at the renderer origin |

## Runner-up framing

| Field | Value |
|---|---|
| Frame | The dominant user-visible gap is the --font-mono surfaces (JetBrains Mono is first in the mono stack and unloaded -> clear SF Mono fallback), while --font-sans is largely masked on macOS because -apple-system precedes 'Inter' in the stack; bundling Inter alone will not change sans rendering on macOS |
| Falsifier | getComputedStyle on a sans/body element in design/reference.html (Inter loaded) on macOS resolves to 'Inter' rather than San Francisco, i.e. -apple-system does NOT mask Inter |
| Confidence vs primary | lower |

## Hypothesis Enumeration

| Hypothesis | Falsifier (what would disprove it) | Runtime probe needed? |
|---|---|---|
| The app's stylesheet ported the design's font-family token VALUES but never ported design/reference.html's @font-face declarations, and no woff2/woff/ttf files were bundled -> 'Inter' and 'JetBrains Mono' have no font source -> the browser falls back to system fonts | an @font-face for Inter/JetBrains Mono exists anywhere in src/renderer, OR document.fonts reports them loaded at runtime | no |
| CSP (default-src 'self', no font-src) at src/renderer/index.html:8 blocks remote font sourcing, so the design's fonts.gstatic.com @font-face cannot simply be re-added; self-hosted same-origin fonts are required | adding a fonts.gstatic.com @font-face loads successfully with the current CSP left unchanged | no |

## Approaches (HOW to change)

### Self-hosted bundled woff2 + @font-face
- **Description**: Add Inter (400/500/600/700) + JetBrains Mono woff2 files under a vite-served assets path (src/renderer/src/assets/fonts/) and add same-origin @font-face rules (font-display: swap) in a fonts stylesheet imported before tokens.css. No CSP change; resolves under 'self'.
- **Addresses hypothesis**: A, B
- **Does NOT cover**: (none)
- **Pros**: Works offline (no network dependency); Needs no CSP change (same-origin url() permitted by default-src self); Restores mono-surface fidelity immediately (JetBrains Mono is first in the mono stack); Deterministic, versioned font files
- **Cons**: Adds ~5 woff2 binaries to the repo/bundle; Does not by itself change sans on macOS (open question: -apple-system precedes Inter); May shift CT screenshot baselines -> regenerate
- **Complexity**: Low

### Remote Google Fonts + CSP relaxation
- **Description**: Port design/reference.html's gstatic @font-face + preconnect links and relax CSP to allow font-src fonts.gstatic.com and style-src fonts.googleapis.com.
- **Addresses hypothesis**: A
- **Does NOT cover**: B
- **Pros**: Mirrors the design reference exactly; No font binaries in the repo
- **Cons**: Breaks offline launch (network dependency) -- violates unchanged_behavior; Requires loosening CSP -- violates unchanged_behavior; Adds a runtime dependency on Google Fonts availability
- **Complexity**: Med

**Recommended approach**: Self-hosted bundled woff2 + @font-face — User selected self-hosted bundling; it is the only approach that satisfies unchanged_behavior (offline launch plus no CSP loosening). No canonical @font-face/self-hosted-font pattern exists project-wide (Phase 2.4b recorded file_line (none)), so a fresh @font-face setup is justified rather than reuse. Fidelity is anchored to the existing design tokens: the fix adds sources for --font-mono / --font-sans (value-semantics row for --font-mono) without hardcoding families. Scope-confined to the renderer style layer; createWindow's loadURL/loadFile origin is the only main-process surface that bears on whether the same-origin url() assets resolve.

**Single-layer justification:**
The fix is declarative (bundle woff2 + @font-face in the renderer stylesheet + one CSS import); it has no data-flow call chain. The sole code-layer surface that affects whether self-hosted url() fonts resolve at runtime is createWindow's renderer-load origin (src/main), so the code footprint is genuinely single-layer.

**Cites:**
- --font-mono

**Proposed call shape:**
```
createWindow()
```

## Constitution Constraints

| Rule | Impact on this change |
|---|---|
| Sec4 Prefer design tokens (CSS custom properties in tokens.css) over literal style values | The @font-face fix keeps --font-sans/--font-mono as the single source of typeface truth; add url() sources for the named families, never hardcode font-family at call sites |
| Sec2.1 Process Boundaries -- Never import Node/Electron in the renderer | Font loading stays a renderer-side declarative concern (CSS @font-face + vite-served assets); not routed through the main process. createWindow origin is context only, not a code change |
| Design Fidelity (design_token_provenance) | This bug is a fidelity gap vs design/reference.html; bundling the same faces the reference loads (Inter 400/500/600/700 + JetBrains Mono) restores fidelity without altering token geometry or colors |

## Complexity Assessment

| Dimension | Rating | Notes |
|---|---|---|
| Codebase changes | Low | Add ~5 woff2 assets + one @font-face block (fonts.css) + one import in main.tsx; no component changes |
| Risk | Med | Typeface change on mono surfaces is intended but alters rendering; FOUT/layout-shift risk mitigated by font-display: swap and metric-compatible fallbacks; existing CT screenshot baselines will likely need regeneration (sub-threshold diffs leave stale baselines) |
| Verify cost | Med | Static probe script confirms root cause; runtime corroboration via document.fonts + getComputedStyle in the running app; regenerate affected CT PNG baselines |

## Value Semantics

| Value | Classification | Evidence | Stability |
|---|---|---|---|
| --font-mono | unclassified | CSS custom property design token declared at src/renderer/styles/tokens.css:63; a declarative styling constant, not a runtime-carried data value | — |

## Open Uncertainties

- [NEEDS CLARIFICATION: desired — confirm whether --font-sans should be reordered so 'Inter' precedes -apple-system (sans is order-masked on macOS) before designing that change -- a separate token reorder outside the confirmed minimal font-loading fix]

## Next step

Copy the block below into a new `/specify` session manually. No automation — user controls when (or if) `/specify` runs.

~~~
/specify "tokens.css declares font-family stacks naming 'Inter' (sans) and 'JetBrains Mono' (mono), but no @font-face rule, @import, <link>, or bundled font file exists anywhere in the app, so all UI text renders in system fallbacks (-apple-system/SF, SF Mono) instead of the design typefaces, producing a pervasive visual mismatch vs design/reference.html — Inter and JetBrains Mono actually load and render, matching design/reference.html, via self-hosted bundled woff2 files declared with local @font-face rules — no network dependency, no CSP change"

Research reference: research/2026-07-09-design-fonts-inter-and.md
Key facts:
- Mode: Bug
- Symptom: tokens.css declares font-family stacks naming 'Inter' (sans) and 'JetBrains Mono' (mono), but no @font-face rule, @import, <link>, or bundled font file exists anywhere in the app, so all UI text renders in system fallbacks (-apple-system/SF, SF Mono) instead of the design typefaces, producing a pervasive visual mismatch vs design/reference.html
- Desired: Inter and JetBrains Mono actually load and render, matching design/reference.html, via self-hosted bundled woff2 files declared with local @font-face rules — no network dependency, no CSP change
- Recommended approach: Self-hosted bundled woff2 + @font-face
- Hypothesis addressed: A, B
- Hypotheses NOT covered: (none)
- Open uncertainties: 1 (see research doc §Open Uncertainties)
~~~
