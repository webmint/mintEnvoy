# Task 004: Document self-hosted fonts in the styles concern doc

**Feature**: 016-load-design-fonts
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 002
**Blocks**: None
**Spec criteria**: AC-9
**Review checkpoint**: No
**Context docs**: docs/renderer/styles/index.md

## Files

| File | Action | Description |
|------|--------|-------------|
| docs/renderer/styles/index.md | Modify | Record fonts.css + self-hosted Inter/JetBrains Mono |

## Description

Record that the renderer now self-hosts its design fonts. The styles-concern doc currently states `styles/` contains only `tokens.css`; update it to note the new hand-authored `fonts.css` (the second file in the concern) that declares `@font-face` for self-hosted Inter and JetBrains Mono via `@fontsource`. This satisfies AC-9's requirement that the docs record the self-hosted fonts within the feature diff (rather than deferring to `/finalize`).

## Change Details

- In `docs/renderer/styles/index.md`:
  - Update the Purpose and/or Structure section to name `fonts.css` alongside `tokens.css`.
  - State that Inter (400/500/600/700) and JetBrains Mono (400/700) are self-hosted via `@font-face` (`font-display: swap`), sourced from the `@fontsource` woff2 packages, and imported in `main.tsx` before `tokens.css`.
  - Keep the note that `tokens.css` remains generated from `design/tokens.json`.

## Contracts

### Expects (checked before execution)
- `src/renderer/src/assets/fonts.css` exists (Task 002 Produces).

### Produces (checked after execution)
- `docs/renderer/styles/index.md` names `fonts.css` and records that Inter and JetBrains Mono are self-hosted via `@font-face` / `@fontsource`.

## Done When

- [x] `docs/renderer/styles/index.md` mentions `fonts.css` and the self-hosted Inter + JetBrains Mono setup
- [x] The existing tokens.css-is-generated note is preserved
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-09T18:46:23Z
**Files changed**: docs/renderer/styles/index.md
**Contract**: Expects 1/1 | Produces 1/1
**Notes**: Added 'Fonts (self-hosted)' note + Structure cross-ref to docs/renderer/styles/index.md; accurately notes fonts.css lives in src/renderer/src/assets (different concern), not styles/. Impl in main thread.
