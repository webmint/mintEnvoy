# Task 003: Tabs fidelity CSS (active accent, dirty dot, close, geometry)

**Feature**: 005-tab-bar-visual-fidelity
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 002
**Blocks**: 005, 009
**Spec criteria**: AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-22, AC-28
**Review checkpoint**: Yes
**Context docs**: None

## Files

| File                                           | Action | Description                                                                                         |
| ---------------------------------------------- | ------ | --------------------------------------------------------------------------------------------------- |
| src/renderer/src/components/molecules/Tabs.css | Modify | Active ::before/::after accent, dirty dot, close button, .tabbar-scoped geometry, overflow override |

## Description

Rewrite the active-tab treatment and tab geometry to match `design/reference.html` (Decisions (a), (b)). ALL new active/geometry rules are scoped under `.tabbar` so the global `.tabs` consumer is untouched (AC-22). Reference target values: `design/styles.css` `.tab*` rules (`.tab` 689-727, `.tab-dirty` 736, `.tab-close` 744, `.tabbar` geometry).

1. **Active accent** (replaces the box-shadow underline + `--accent-soft` wash) — on `.tabbar .tabs__tab-wrapper--active`: a top `::before` (position absolute, left/right 0, top 0, height `1.5px`, background `var(--accent)`), a bottom `::after` mask (left/right 0, bottom `-1px`, height `1px`, background `var(--bg)`), and `background: var(--bg)` on the active tab. Neutralize the inherited box-shadow active underline + accent-soft inside `.tabbar`.
2. **Dirty dot** — `.tabs__tab-dirty` 7px×7px, `border-radius: 50%`, `background: var(--text-faint)`, `flex-shrink: 0`.
3. **Close button** — rewrite `.tabs__tab-close` to always-visible (NOT `opacity:0` hover-reveal): `16px×16px`, `display: grid; place-items: center`, `border-radius: 3px`, `color: var(--text-faint)`, `flex-shrink: 0`; hover `background: var(--bg-active); color: var(--text)`.
4. **Geometry** (`.tabbar`-scoped) — gap `8px`, padding `0 10px 0 12px`, a per-tab right border `1px solid var(--border)` on the wrapper; `.tabs__tab-label` `flex: 1` with ellipsis.
5. **Overflow** — override `.tabs.tabbar { overflow: visible }` (leave global `.tabs { overflow: hidden }` intact) so the `::after` bottom mask at `bottom:-1px` is not clipped.

## Change Details

- In `src/renderer/src/components/molecules/Tabs.css`:
  - Add the `.tabbar .tabs__tab-wrapper--active` block (`::before`, `::after`, `background: var(--bg)`); scope the old box-shadow/accent-soft active rules so they no longer apply inside `.tabbar`.
  - Add `.tabs__tab-dirty`.
  - Rewrite `.tabs__tab-close` (always-visible 16px) + its hover.
  - Add `.tabbar`-scoped gap/padding/wrapper-border-right and the `.tabs__tab-label { flex: 1 }` ellipsis cap.
  - Add `.tabs.tabbar { overflow: visible }`.

## Contracts

### Expects (checked before execution)

- Task 002 emits `tabs__tab-wrapper--active` on the active wrapper, `tabs__tab-dirty` (dirty), and `tabs__tab-close` (clean) nodes.
- `.tabs` currently has `border-bottom` + `overflow: hidden` and an active box-shadow underline + `--accent-soft` wash.
- Tokens `--accent`, `--bg`, `--text-faint`, `--bg-active`, `--text`, `--border` are defined.

### Produces (checked after execution)

- `.tabbar .tabs__tab-wrapper--active::before` (accent top bar) and `::after` (bg bottom mask) rules exist; the active tab background is `var(--bg)`.
- `.tabs__tab-dirty` (7px circle) and an always-visible 16px `.tabs__tab-close` rule exist.
- `.tabbar`-scoped gap/padding/wrapper-border-right rules and `.tabs.tabbar { overflow: visible }` exist; `.tabs__tab-label` is `flex: 1` with ellipsis.
- No new active/geometry rule applies to a bare `.tabs` (non-`.tabbar`) consumer (AC-22).

## Done When

- [x] Active accent renders as a top `::before` 1.5px `--accent` + bottom `::after` 1px `--bg` mask over a `--bg` background, scoped to `.tabbar` (AC-11, AC-22)
- [x] `.tabs__tab-dirty` is a 7px `--text-faint` dot; `.tabs__tab-close` is an always-visible 16px grid-centered control (AC-12, AC-13)
- [x] `.tabbar`-scoped gap 8px / padding `0 10px 0 12px` / wrapper right-border; label `flex:1` ellipsis (AC-14, AC-15, AC-16)
- [x] `.tabs.tabbar { overflow: visible }` present; global `.tabs { overflow: hidden }` unchanged
- [x] No inline styles (CSS file) — token-bound values only (AC-28); animations gated behind `prefers-reduced-motion`
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-06-26T08:08:01Z
**Files changed**: src/renderer/src/components/molecules/Tabs.css
**Contract**: Expects 3/3 | Produces 4/4
**Notes**: Repair round: added align-self:center to close+dirty (AC-22-safe non-tabbar fix). Added AC-16/AC-22 + bare-consumer assertion to task 009 spec (qa panel).
