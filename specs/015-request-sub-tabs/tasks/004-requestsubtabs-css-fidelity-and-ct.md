# Task 004: RequestSubTabs §6 fidelity CSS and CT

**Feature**: 015-request-sub-tabs
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: 003
**Blocks**: 005
**Spec criteria**: AC-2, AC-8, AC-9, AC-20, AC-21, AC-27
**Review checkpoint**: Yes
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/organisms/RequestSubTabs.css | Create | `.pane-tabs`-scoped override of the Tabs DOM to hit design/styles.css §6 + panel/empty-state layout |
| src/renderer/src/components/organisms/__tests__/RequestSubTabs.ct.tsx | Create | Playwright CT: keyboard, focus-survives-switch (R1 gate), A→B→A per-tab state, per-theme computed-style fidelity, a11y |

## Description

Author the `.pane-tabs`-scoped fidelity stylesheet (D4) that reshapes the composed `Tabs` DOM to match design/styles.css §6 (`.pane-tabs` / `.pane-tab` / `.pane-tab.active::after` underline / `.pane-tab .badge`) in BOTH themes, mirroring the existing `.tabbar` scope precedent in `Tabs.css`. Co-author the CT that asserts resolved computed styles (not screenshots, R3/R7) reading the §6 numbers from `design/styles.css` at test-writing time, plus the behavioral go/no-go CTs (focus-survives-switch is the R1 gate before App wiring).

## Change Details

- Verify §6 tokens exist at `src/renderer/styles/tokens.css` (real path — NOT `src/renderer/src/styles/`): `--text-muted`, `--text`, `--accent`, `--accent-soft`, `--bg-active`, `--border-faint` (present in both `:root` light and dark blocks). No new token.
- Create `src/renderer/src/components/organisms/RequestSubTabs.css` — `.pane-tabs`-scoped rules only (compound selectors so no bare `.tabs` consumer is touched, mirror `Tabs.css` §.tabbar block):
  - `.tabs.pane-tabs`: `overflow: visible`, `height: 36px`, `border-bottom: 1px solid var(--border-faint)`, `padding: 0 16px`.
  - `.pane-tabs .tabs__list`: `gap: 2px`.
  - `.pane-tabs .tabs__tab`: `height: 36px`, `padding: 0 4px`, `gap: 6px`, `font-size: 12.5px`, `font-weight: 500`, `margin-right: 14px`, `color: var(--text-muted)`; `:hover` → `var(--text)`.
  - Neutralize the molecule's active treatment (`box-shadow: none`) and add `.pane-tabs .tabs__tab--active { color: var(--text) }` + `.pane-tabs .tabs__tab--active::after { content:''; position:absolute; left:0; right:0; bottom:-1px; height:1.5px; background: var(--accent) }`.
  - Rebind badge: `.pane-tabs .tabs__badge { font-size:10px; background: var(--bg-active); color: var(--text-muted); border-radius:999px; padding:1px 6px; font-weight:600 }` and `.pane-tabs .tabs__tab--active .tabs__badge { background: var(--accent-soft); color: var(--accent) }`.
  - Panel/empty-state layout: the strip container `flex:1; min-height:0`; the panel body `flex:1; overflow:auto`; the shared empty-state text `color: var(--text-muted)`.
- Create `src/renderer/src/components/organisms/__tests__/RequestSubTabs.ct.tsx` (Playwright CT):
  - Keyboard: Arrow/Home/End move the active sub-tab (delegated to Tabs) (AC-6).
  - Focus-survives-switch (R1 GO/NO-GO): focus an input in the Params panel, switch to Headers and back, assert the SAME DOM node retains focus + value + scroll (AC-9).
  - A→B→A per-tab state: tab A on Headers, tab B on Body, switch A→B→A, assert A's active sub-tab is still Headers (AC-8, R2).
  - Per-theme fidelity: under both light and dark `data-theme`, assert resolved computed styles of `.pane-tab`/active-underline/badge against the §6 values read from `design/styles.css` (AC-27, R3/R7). Reproduce the full styling context (tokens.css import + production `.pane-tabs` scope) per the CT fidelity-fixture-scoping constraint.
  - a11y: each tabpanel exposes `role='tabpanel'` + `aria-labelledby` resolving to its tab's `id` (AC-14).

## Change Details Notes

Enumerate EVERY §6 property in the fidelity CT (badge bg + geometry, active underline, active-badge accent wash, `overflow:visible`, border-faint separator) — missing any one leaves a stale computed-style drift (R7). CT baselines within tolerance can stay stale (memory: ct-baseline-within-tolerance); assert numeric computed values, not screenshot pixels.

## Contracts

### Expects (checked before execution)
- `RequestSubTabs` renders a `.pane-tabs`-classed `Tabs` plus 6 `role='tabpanel'` nodes with `aria-labelledby` (task 003).
- §6 tokens `--text-muted/--text/--accent/--accent-soft/--bg-active/--border-faint` are defined in `src/renderer/styles/tokens.css`.

### Produces (checked after execution)
- `RequestSubTabs.css` exists with `.pane-tabs`-scoped rules including the `.pane-tabs .tabs__tab--active::after` underline and the `.pane-tabs .tabs__badge` rebind.
- `RequestSubTabs.ct.tsx` asserts focus-survives-switch, A→B→A per-tab state, and per-theme computed-style fidelity against §6.

## Done When

- [x] `RequestSubTabs.css` matches design/styles.css §6 computed targets in both themes (AC-27).
- [x] Focus-survives-switch CT passes (R1 gate green) — same DOM node keeps focus + value + scroll (AC-9).
- [x] A→B→A per-tab-state CT passes (AC-8).
- [x] Per-theme fidelity CT asserts resolved computed styles read from design/styles.css §6.
- [x] §6 tokens confirmed present at `src/renderer/styles/tokens.css` (no new token).
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-06T17:10:26Z
**Files changed**: src/renderer/src/components/organisms/RequestSubTabs.tsx, src/renderer/src/components/organisms/RequestSubTabs.css, src/renderer/src/components/organisms/__tests__/RequestSubTabs.ct.tsx, src/renderer/src/components/organisms/__tests__/RequestSubTabs.stories.tsx
**Contract**: Expects 2/2 | Produces 2/2
**Notes**: Reopened RequestSubTabs.tsx (production) to fix an AC-9 scroll-preservation defect the CT surfaced: mount-all+hidden zeroes scrollTop; fix = synchronous capture in handleSubTabChange + layout-effect restore + focus({preventScroll:true}) so focus doesn't clobber scroll. Also fixed a build-breaking wrong tokens.css import (@renderer/styles → nonexistent; tokens load globally via playwright/index.tsx). CT 23 pass, Vitest 36 pass, both themes fidelity asserted via getComputedStyle.
