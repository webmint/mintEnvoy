# Task 002: Create fonts.css @font-face and import it in main.tsx

**Feature**: 016-load-design-fonts
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 001
**Blocks**: 003, 004, 005
**Spec criteria**: AC-1, AC-3, AC-4, AC-6, AC-8, AC-10, AC-12
**Review checkpoint**: No
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/assets/fonts.css | Create | Hand-authored `@font-face` × 6 sourcing bundled woff2 |
| src/renderer/src/main.tsx | Modify | Import `fonts.css` before `tokens.css` |

## Description

Create the hand-authored fonts stylesheet that self-hosts Inter and JetBrains Mono, and wire it into the renderer entry so the faces load at boot. This is the core of the fix: it gives the `--font-sans` / `--font-mono` families a real source so text stops falling back to system fonts. No CSP change and no remote URLs — the woff2 are same-origin, bundled by vite.

## Change Details

- Create `src/renderer/src/assets/fonts.css` with exactly 6 hand-authored `@font-face` rules:
  - `Inter` weights 400, 500, 600, 700 (`font-style: normal`).
  - `JetBrains Mono` weights 400, 700 (`font-style: normal`).
  - Each rule: `font-display: swap;` and `src: url(...) format('woff2');` pointing at the corresponding `@fontsource` latin woff2.
  - **Enumerate the actual filenames** under `node_modules/@fontsource/inter/files/` and `node_modules/@fontsource/jetbrains-mono/files/` (the pattern is `inter-latin-<weight>-normal.woff2` / `jetbrains-mono-latin-<weight>-normal.woff2`, but confirm the real names — do NOT hardcode from memory).
  - **The `url()` MUST be a vite-resolvable relative path** from `src/renderer/src/assets/fonts.css` to `node_modules/@fontsource/...` (i.e. a `../../../../node_modules/@fontsource/...` style relative path, or a configured `@renderer`/alias form vite rebases). Do NOT use a bare `@fontsource/...` package specifier and do NOT use webpack's `~` prefix — vite silently fails to bundle those, producing a broken (unbundled) font reference.
- In `src/renderer/src/main.tsx`:
  - Add `import './assets/fonts.css'` as the FIRST import, BEFORE `import '../styles/tokens.css'`.

## Contracts

### Expects (checked before execution)
- `@fontsource/inter` and `@fontsource/jetbrains-mono` woff2 files are present under `node_modules/@fontsource/*/files/` (Task 001 Produces).

### Produces (checked after execution)
- `src/renderer/src/assets/fonts.css` exists and declares 6 `@font-face` rules: `Inter` (400/500/600/700) and `JetBrains Mono` (400/700).
- Every `@font-face` in `fonts.css` sets `font-display: swap` and a `src: url(...) format('woff2')` that resolves to a bundled `@fontsource` woff2 (no remote URL).
- `src/renderer/src/main.tsx` contains `import './assets/fonts.css'` before `import '../styles/tokens.css'`.

## Done When

- [x] `fonts.css` declares 6 `@font-face` (Inter 400/500/600/700, JetBrains Mono 400/700), each with `font-display: swap`
- [x] Each `src: url()` is a vite-resolvable relative path to an actual `@fontsource` woff2 filename (enumerated from node_modules, not guessed)
- [x] `fonts.css` contains no `fonts.googleapis.com` / `fonts.gstatic.com` / other remote URL
- [x] `main.tsx` imports `./assets/fonts.css` before `../styles/tokens.css`
- [x] `electron-vite build` emits the woff2 (the fonts resolve at the renderer origin, not a dangling reference)
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-09T18:38:18Z
**Files changed**: src/renderer/src/assets/fonts.css, src/renderer/src/main.tsx
**Contract**: Expects 1/1 | Produces 3/3
**Notes**: fonts.css: 6 @font-face (Inter 400/500/600/700, JetBrains Mono 400/700), font-display:swap, relative url() to @fontsource woff2. main.tsx imports it before tokens.css. Build emits all 6 woff2 to out/renderer/assets/ (url() bundles). Impl in main thread.
