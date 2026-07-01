# Task 001: complete method tokens and HEAD color

**Feature**: 005-tab-bar-visual-fidelity
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: None
**Blocks**: 002, 006
**Spec criteria**: AC-1, AC-7, AC-8, AC-19
**Review checkpoint**: No
**Context docs**: None

## Files

| File                           | Action | Description                                                                             |
| ------------------------------ | ------ | --------------------------------------------------------------------------------------- |
| src/renderer/styles/tokens.css | Modify | Add base `.method` font rule, `--m-head` token (light+dark), `.method.HEAD` color rules |

## Description

Complete the method-token set so a HEAD chip renders colored and the chip uses the mono font under every method-style variant. Three additions, all token/CSS-rule level (Decision (d)):

1. A base `.method` rule carrying ONLY the mstyle-invariant font (`font-family: var(--font-mono)`). Do NOT add box geometry (display/min-width/padding/height) to the base rule — that geometry is deliberately gated per `[data-mstyle='X'] .method` variant and must stay there.
2. A `--m-head` custom property — light `#ec4899`, dark `#f472b6` (Tailwind pink-500/400) — placed alongside the existing `--m-get`…`--m-options` tokens in both the light block and the dark (`[data-theme='dark']` or equivalent) block, matching the existing light/dark token-pair convention.
3. A base `.method.HEAD { color: var(--m-head); }` rule (colored fallback under any mstyle) PLUS a `[data-mstyle='soft'] .method.HEAD { background: color-mix(in oklab, var(--m-head) 16%, transparent); color: var(--m-head); }` rule matching the six existing soft sibling rules.

## Change Details

- In `src/renderer/styles/tokens.css`:
  - Add `--m-head: #ec4899;` to the light token block (next to `--m-get`…`--m-options`) and `--m-head: #f472b6;` to the dark override block.
  - Add a bare `.method { font-family: var(--font-mono); }` rule (font only — no box props).
  - Add `.method.HEAD { color: var(--m-head); }` next to the other base per-method color rules (`.method.GET`…`.method.OPTIONS`).
  - Add `[data-mstyle='soft'] .method.HEAD { background: color-mix(in oklab, var(--m-head) 16%, transparent); color: var(--m-head); }` next to the soft sibling rules.

## Contracts

### Expects (checked before execution)

- `src/renderer/styles/tokens.css` defines `--m-get`/`--m-post`/…/`--m-options` and per-`[data-mstyle]` `.method` variants, with NO existing `--m-head` and no bare `.method { font-family }` rule.
- `--font-mono` is defined in `tokens.css`.

### Produces (checked after execution)

- `--m-head` is defined in both the light and dark token blocks of `tokens.css`.
- A `.method.HEAD` color rule exists (base) and a `[data-mstyle='soft'] .method.HEAD` rule exists.
- A bare `.method { font-family: var(--font-mono) }` rule exists carrying no box geometry.

## Done When

- [x] `grep -qE '\-\-m-head\s*:' src/renderer/styles/tokens.css` passes (AC-1)
- [x] `grep -qE '\.method\.HEAD' src/renderer/styles/tokens.css` passes (AC-7)
- [x] `grep -qE '^\.method[[:space:]]*\{' src/renderer/styles/tokens.css` passes and that block contains `font-family: var(--font-mono)` only (AC-8)
- [x] The base `.method` rule adds no display/min-width/padding/height (geometry stays under `[data-mstyle]`)
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-26T07:21:40Z
**Files changed**: src/renderer/styles/tokens.css
**Contract**: Expects 2/2 | Produces 3/3
**Notes**: (none)
