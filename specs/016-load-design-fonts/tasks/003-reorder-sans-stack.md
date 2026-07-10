# Task 003: Reorder --font-sans and point base.css body at the token

**Feature**: 016-load-design-fonts
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 002
**Blocks**: 005
**Spec criteria**: AC-5, AC-7, AC-13
**Review checkpoint**: No
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/styles/tokens.css | Modify | Reorder `--font-sans` so `'Inter'` precedes `-apple-system` |
| src/renderer/src/assets/base.css | Modify | Replace hardcoded body `font-family` stack with `var(--font-sans)` |

## Description

Make the sans cascade actually render Inter. Two coordinated edits: reorder the `--font-sans` token so `'Inter'` wins over `-apple-system` (otherwise macOS renders San Francisco even with Inter loaded), and repoint `base.css`'s hardcoded electron-vite starter body stack at `var(--font-sans)` so body/sans text is driven by the token instead of a divergent literal. Only the `--font-sans` value order changes in `tokens.css` — no other token, no `@font-face`.

## Change Details

- In `src/renderer/styles/tokens.css`:
  - Reorder `--font-sans` so `'Inter'` comes first: `--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Text', system-ui, sans-serif;` (keep the existing fallbacks, only move `'Inter'` to the front).
  - Add a comment noting the file is otherwise generated: e.g. `/* --font-sans reordered by hand (016): Inter first. If the design/tokens.json generation pipeline is restored, move this change to tokens.json. */`.
  - Do NOT add any `@font-face` rule here (those live in `fonts.css`; AC-13).
  - Leave `--font-mono` unchanged (`'JetBrains Mono'` is already first).
- In `src/renderer/src/assets/base.css`:
  - Replace the hardcoded `body { font-family: Inter, -apple-system, ... }` stack with `body { font-family: var(--font-sans); }`.
  - Keep the other body properties (`-webkit-font-smoothing: antialiased`, `-moz-osx-font-smoothing: grayscale`, `text-rendering: optimizeLegibility`, `min-height`, `color`, `background`, `line-height`).

## Contracts

### Expects (checked before execution)
- `fonts.css` loads Inter and JetBrains Mono (Task 002 Produces) so the reordered token resolves to a real face.

### Produces (checked after execution)
- In `tokens.css`, `--font-sans` lists `'Inter'` before `-apple-system`, and carries the restore-to-`tokens.json` comment.
- `tokens.css` contains no `@font-face` rule.
- In `base.css`, the `body` rule's `font-family` is `var(--font-sans)` (the hardcoded literal stack is removed); the antialiasing / `optimizeLegibility` declarations are retained.

## Done When

- [x] `tokens.css` `--font-sans` has `'Inter'` first, other fallbacks retained, plus the restore-to-pipeline comment
- [x] `tokens.css` contains no `@font-face`
- [x] `base.css` `body` uses `font-family: var(--font-sans)` and retains antialiasing/optimizeLegibility
- [x] No other design-token value changed
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-09T18:42:43Z
**Files changed**: src/renderer/styles/tokens.css, src/renderer/src/assets/base.css
**Contract**: Expects 1/1 | Produces 3/3
**Notes**: tokens.css --font-sans reordered 'Inter' first (+restore comment); no @font-face (AC-13). base.css body font-family -> var(--font-sans), antialiasing retained. Impl in main thread.
