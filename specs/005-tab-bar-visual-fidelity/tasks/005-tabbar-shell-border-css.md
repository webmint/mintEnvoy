# Task 005: TabBar strip CSS + Shell border de-dup

**Feature**: 005-tab-bar-visual-fidelity
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 003, 004
**Blocks**: 009
**Spec criteria**: AC-14, AC-17, AC-20
**Review checkpoint**: Yes
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/organisms/TabBar.css | Modify | .tabbar strip geometry; +/chevron icon buttons; delete dirty-badge block |
| src/renderer/src/components/organisms/Shell.css | Modify | Remove the duplicate .shell__tabs bottom border |

## Description

Style the strip to the reference and remove the duplicate border in ONE atomic change (Decision (b) — the de-dup is load-bearing: it must converge with the `.tabbar` border so the strip never shows two borders or zero borders).

1. **TabBar.css** — `.tabbar`: `background: var(--bg-sunken)`, `height: 36px`, `border-bottom: 1px solid var(--border)`, `padding-right: 8px`. Style `.tabbar__new` and the chevron button as grid-centered icon buttons (`display: grid; place-items: center`, padding `0 10px`, `color: var(--text-muted)`, hover `--bg-hover`/`--text`); `.tabbar__spacer { flex: 1 }`. DELETE the `.tabbar .tabs__badge` dirty-dot block (the badge mapping is gone as of task 004).
2. **Shell.css** — remove the `border-bottom` declaration from `.shell__tabs` (the `.tabbar` border now owns the single bottom border; the active `::after` mask from task 003 paints over exactly one border — AC-17).

## Change Details

- In `src/renderer/src/components/organisms/TabBar.css`:
  - Set `.tabbar` to `--bg-sunken` / 36px / `border-bottom: 1px solid var(--border)` / `padding-right: 8px` (replacing the current `background-color: var(--bg)` only rule).
  - Add `.tabbar__new` + chevron grid-centered icon-button rules + `.tabbar__spacer { flex: 1 }`.
  - Delete the `.tabbar .tabs__badge` rule block.
- In `src/renderer/src/components/organisms/Shell.css`:
  - Remove the `border-bottom: 1px solid var(--border…)` line from `.shell__tabs`.

## Contracts

### Expects (checked before execution)
- `.tabbar` currently sets only `background-color: var(--bg)`; a `.tabbar .tabs__badge` dirty block exists.
- `.shell__tabs` carries a `border-bottom` (the duplicate alongside the Tabs `.tabs` border).
- Task 004 emits `.tabbar__new`, `.tabbar__spacer`, and the chevron button markup; task 003 added the active `::after` bottom mask.

### Produces (checked after execution)
- `.tabbar` computes `--bg-sunken` background, 36px height, a 1px `--border` bottom border, and 8px right padding.
- `.tabbar__new` and the chevron are grid-centered icon buttons; `.tabbar__spacer` is `flex: 1`.
- The `.tabbar .tabs__badge` block is removed.
- `.shell__tabs` no longer declares a `border-bottom` (exactly one strip bottom border remains).

## Done When

- [x] `.tabbar` = `--bg-sunken` / 36px / `border-bottom 1px --border` / `padding-right 8px` (AC-14)
- [x] `.tabbar__new` + chevron are grid-centered icon buttons; `.tabbar .tabs__badge` deleted (AC-20)
- [x] `.shell__tabs` `border-bottom` removed → a single strip bottom border (AC-17 — runtime-verified by the task-009 fidelity suite + the `/verify` design-auditor probe, not a code-only grep)
- [x] No inline styles; token-bound values only
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-26T09:13:53Z
**Files changed**: src/renderer/src/components/organisms/TabBar.css, src/renderer/src/components/organisms/Shell.css
**Contract**: Expects 3/3 | Produces 4/4
**Notes**: Repair: updated stale badge/border comments. Added AC-17 + a .shell__tabs(0px)/.tabbar(1px) border assertion to task 009 (qa panel).
