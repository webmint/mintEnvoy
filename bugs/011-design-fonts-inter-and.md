# Bug 011: Design fonts Inter and JetBrains Mono never loaded

**Status**: Fixed
**Severity**: Warning
**Source**: manual
**Feature**: 016-load-design-fonts
**AC**: N/A
**Reported**: 2026-07-06
**Fixed**: 2026-07-10

## Description

App-wide design-fidelity root cause. The renderer's font stacks reference 'Inter' (UI/--font-sans, used by body/headers) and 'JetBrains Mono' (--font-mono, used by KVTable cells, code, mono UI), but the app NEVER LOADS those fonts: no @font-face declaration anywhere in src/renderer, no bundled .woff2/.woff/.ttf files, and index.html CSP is default-src 'self' with no font-src (so a Google Fonts link would be blocked). Live: document.fonts has zero loaded faces; header/body compute to -apple-system (San Francisco) fallback, KV cells to SF Mono/Menlo fallback. design/reference.html loads Inter + JetBrains Mono from Google Fonts, so it renders in the intended typefaces while the Electron app renders in system fallbacks — a pervasive visual mismatch (perceived weight/color/letterform differences across the whole UI, incl. the KVTable header vs rows). FIX: bundle Inter + JetBrains Mono locally (woff2 in resources/), add @font-face (src: local 'self' so CSP default-src 'self' permits them), verify document.fonts loads them. This supersedes/explains bug 010 (KVTable header/row font). Not a 014/015 regression — a missing app-wide font-loading setup.

## Expected Behavior

_Expected behavior not specified — see spec AC._

## Actual Behavior

_Actual behavior not specified — see verification evidence._

## File(s)

| File | Detail |
|------|--------|
| src/renderer/index.html |  |

## Evidence

Reported by user.

## Related Issues

_None — standalone bug._

## Fix Notes

Fixed by feature 016-load-design-fonts. Inter + JetBrains Mono are now self-hosted via @fontsource: a hand-authored src/renderer/src/assets/fonts.css declares @font-face for every weight (Inter 400/500/600/700, JetBrains Mono 400/600/700) with font-display:swap, referencing bundled woff2 by relative url() into node_modules/@fontsource so Vite emits them into the renderer bundle (same-origin, no CSP change — default-src 'self' permits them). main.tsx imports fonts.css before tokens.css; --font-sans leads with Inter. Verified: /review design-fidelity audit CLEAN — document.fonts loads all faces, body/titlebar/buttons compute Inter-first, .method computes JetBrains Mono 700. /verify APPROVED, 13/13 ACs PASS. A follow-on fix also added `button,input,select,textarea{font-family:inherit}` to base.css so form controls (which don't inherit body font per the UA stylesheet) render Inter instead of Arial.
