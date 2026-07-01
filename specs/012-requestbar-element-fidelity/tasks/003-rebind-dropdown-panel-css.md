# Task 003: rebind shared dropdown open-panel css

**Feature**: 012-requestbar-element-fidelity
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: None
**Blocks**: 004
**Spec criteria**: AC-1, AC-10, AC-14, AC-15, AC-16, AC-17
**Review checkpoint**: No
**Context docs**: None

## Files

| File                                               | Action | Description                                                                                                                                                                                                                                                        |
| -------------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| src/renderer/src/components/molecules/Dropdown.css | Modify | Rebind the open panel to reference values: `.dropdown-content` `box-shadow var(--shadow-lg)` + 1px inter-item gap; `.dropdown-item` padding `6px 8px`. Bounded cross-component change (ripples to dev-only PrimitivesDemo + visual snapshots — accepted in scope). |

## Description

Rebind the shared Dropdown molecule's OPEN PANEL to the `design/styles.css` `.dropdown` reference values (:1536-1566) using existing tokens. Three property edits only: (1) `.dropdown-content` box-shadow `var(--shadow-md)` → `var(--shadow-lg)`; (2) add a 1px inter-item gap on the panel (the reference `.dropdown` panel gap); (3) `.dropdown-item` padding `0.375rem 0.625rem` (6px 10px) → `6px 8px`. Keep the already-matching `border-radius:var(--radius-md)`, `background-color:var(--bg-elev)`, and the `[data-highlighted]` hover `background-color:var(--bg-hover)`. This is the ONE intentional cross-component change (the other prod consumer, PrimitivesDemo, is dev-only and tree-shaken); the fidelity CT + visual-snapshot rebaseline live in task 004. No behaviour change, no Radix positioning change.

## Change Details

- In `src/renderer/src/components/molecules/Dropdown.css`:
  - `.dropdown-content`: change `box-shadow` from `var(--shadow-md, …)` to `var(--shadow-lg)`; add a 1px inter-item gap between panel items — either `display:flex; flex-direction:column; gap:1px;` on `.dropdown-content`, or a `gap:1px` consistent with the reference panel (match the reference `.dropdown` mechanism at design/styles.css:1536-1566). Keep `border-radius:var(--radius-md)`, `background-color:var(--bg-elev)`, `border`, `z-index`, and the animation rules unchanged.
  - `.dropdown-item`: change `padding` from `0.375rem 0.625rem` to `6px 8px`. Keep every other declaration, including the `[data-highlighted]` `background-color:var(--bg-hover)` hover.
  - Update the file header comment token list + inline comments to document the open-panel rebind (shadow-lg / 1px gap / `6px 8px` item padding) and note the bounded ripple to PrimitivesDemo (AC-14). Do not introduce new hardcoded colour literals; the `1px` gap and `6px 8px` padding are raw-px where no token exists (allowed per spec §7).

## Contracts

### Expects (checked before execution)

- `Dropdown.css` `.dropdown-content` currently declares `box-shadow: var(--shadow-md, …)` and has no inter-item gap.
- `Dropdown.css` `.dropdown-item` currently declares `padding: 0.375rem 0.625rem`.
- `tokens.css` defines `--shadow-lg`, `--radius-md`, `--bg-elev`, `--bg-hover`.
- `Dropdown.tsx` is not modified by this feature (AC-1 Dropdown side satisfied by non-modification).

### Produces (checked after execution)

- `.dropdown-content` declares `box-shadow: var(--shadow-lg)` and a `1px` inter-item panel gap.
- `.dropdown-item` declares `padding: 6px 8px`.
- `.dropdown-content` retains `border-radius: var(--radius-md)` + `background-color: var(--bg-elev)`; `.dropdown-item[data-highlighted]` retains `background-color: var(--bg-hover)`.
- `Dropdown.css` and `Dropdown.tsx` contain no `data-om-`, `__OmT`, or `tweaks-panel` markers.

## Done When

- [x] `.dropdown-content` box-shadow rebound to `var(--shadow-lg)` with a 1px inter-item gap (AC-10)
- [x] `.dropdown-item` padding set to `6px 8px` (AC-10)
- [x] `border-radius:var(--radius-md)`, `background-color:var(--bg-elev)`, highlighted hover `var(--bg-hover)` all retained
- [x] `! grep -REn 'data-om-|__OmT|tweaks-panel' src/renderer/src/components/molecules/Dropdown.tsx` passes (AC-1)
- [x] Comments document the open-panel rebind + PrimitivesDemo ripple (AC-14)
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (`npm run typecheck:web`)
- [x] Linter passes on changed files (`npm run lint`)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-01T08:58:57Z
**Files changed**: src/renderer/src/components/molecules/Dropdown.css
**Contract**: Expects 4/4 | Produces 4/4
**Notes**: CSS-only rebind: box-shadow→var(--shadow-lg), added 1px inter-item panel gap (flex column), item padding→6px 8px. Kept file's existing var(--x,fallback) convention. Panel warning: 1px gap also spaces separators (+2px) — no method-dropdown impact; task 004 screenshot rebaseline verifies. typecheck+lint+build pass.
