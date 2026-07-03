# Task 001: Sync drifted muted and faint token values

**Feature**: 013-tabs-contrast-wcag
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: None
**Blocks**: 003
**Spec criteria**: AC-1, AC-2, AC-4, AC-7, AC-8, AC-9
**Review checkpoint**: No
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/styles/tokens.css | Modify | Sync 3 drifted text-token values to the design source (design/styles.css) |
| design/tokens.json | Modify | Sync the one stale DTCG value (dark `textFaint`) to match design/styles.css — keeps the two design artifacts consistent (Addition to Spec, architect Finding A) |

## Description

The app's design tokens in `src/renderer/styles/tokens.css` have drifted from `design/styles.css` (the spec's declared design source of truth). Three text tokens still hold pre-AA values; sync all three to the darkened source values. This one edit brings every `--text-muted` / `--text-faint` text consumer app-wide to WCAG AA — including the Tabs inactive label (4.36→4.69:1), close-button icon (2.31→4.55:1 light / 4.58:1 dark), and dirty-dot (→4.55:1).

No new token is introduced and no existing token is renamed — only three existing values change (AC-2). `design-fidelity-contract §5` is NOT hand-edited (it derives from `design/styles.css` and is already correct once the tokens sync).

**Addition to Spec (architect Finding A):** `design/tokens.json` (the DTCG artifact named in the tokens.css header) declares dark `textFaint: #71717a` — the stale value — disagreeing with `design/styles.css` (#787881). No generator wires tokens.json → tokens.css (the "regenerate" header note is stale), but dark faint IS one of the three in-scope values, so this task also fixes the single stale JSON value to keep the two design artifacts internally consistent. The light `textMuted`/`textFaint` JSON values already match the source — only dark `textFaint` needs the edit. AC-1 greps `tokens.css` only, so this addition changes no acceptance check.

## Change Details

- In `src/renderer/styles/tokens.css`:
  - `:root` block: `--text-muted: #71717a` → `--text-muted: #6c6c75`
  - `:root` block: `--text-faint: #a1a1aa` → `--text-faint: #6e6e77`
  - `[data-theme='dark']` block: `--text-faint: #71717a` → `--text-faint: #787881`
  - Leave the dark `--text-muted: #a1a1aa` UNCHANGED (already matches the source)
- In `design/tokens.json`:
  - The dark theme group's `textFaint` `$value`: `#71717a` → `#787881` (the light `textMuted`/`textFaint` and dark `textMuted` already match `design/styles.css` — do NOT touch them)

## Contracts

### Expects (checked before execution)
- `src/renderer/styles/tokens.css` `:root` declares `--text-muted: #71717a` and `--text-faint: #a1a1aa`.
- `src/renderer/styles/tokens.css` `[data-theme='dark']` declares `--text-faint: #71717a`.
- `design/styles.css` declares light `--text-muted: #6c6c75`, light `--text-faint: #6e6e77`, dark `--text-faint: #787881` (the sync targets).
- `design/tokens.json` dark theme group declares `textFaint` `$value: #71717a`.

### Produces (checked after execution)
- `src/renderer/styles/tokens.css` `:root` declares `--text-muted: #6c6c75` and `--text-faint: #6e6e77`.
- `src/renderer/styles/tokens.css` `[data-theme='dark']` declares `--text-faint: #787881`; its `--text-muted` remains `#a1a1aa`.
- No new custom-property name is added to `tokens.css` (no `--text-secondary` or other new token).
- `design/tokens.json` dark theme group declares `textFaint` `$value: #787881`, matching `design/styles.css`.

## Done When

- [x] `tokens.css` `:root` reads `--text-muted: #6c6c75` and `--text-faint: #6e6e77`
- [x] `tokens.css` `[data-theme='dark']` reads `--text-faint: #787881` and still `--text-muted: #a1a1aa`
- [x] No new token name introduced in `tokens.css` (AC-2)
- [x] `design/tokens.json` dark `textFaint` reads `#787881`
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-02T20:31:32Z
**Files changed**: src/renderer/styles/tokens.css, design/tokens.json
**Contract**: Expects 4/4 | Produces 4/4
**Notes**: Also deleted pre-existing lint-failing throwaway research probe (research/2026-07-01-bug-005-active-tab/probe-script.mjs) to clear repo-wide eslint gate (user-approved); out of task scope but folded in. tokens.css/tokens.json are not eslint targets (0 lint errors).
