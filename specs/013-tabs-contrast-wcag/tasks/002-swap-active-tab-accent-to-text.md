# Task 002: Swap active-tab accent-on-light sites to text token

**Feature**: 013-tabs-contrast-wcag
**Agent**: frontend-engineer
**Status**: Complete
**Depends on**: None
**Blocks**: 003
**Spec criteria**: AC-3, AC-5, AC-6
**Review checkpoint**: Yes
**Context docs**: None

## Files

| File | Action | Description |
|------|--------|-------------|
| src/renderer/src/components/molecules/Tabs.css | Modify | Swap two accent-on-light `color` sites (active-tab label, active-tab badge text) to the primary text token |

## Description

Two active-tab sites color TEXT with `var(--accent)` (#10b981), which fails WCAG AA as text regardless of the token sync: active-tab label measures 2.29:1 (light) / 2.54:1 (dark), and active-tab badge text fails on the `--accent-soft` background. Swap both to `var(--text)` (15.98:1 light / 17.72:1 dark) — the same promote-to-`var(--text)` idiom the hover rules already use (Tabs.css:120, :339). This is a color-only change: the accent underline (box-shadow, line 151) and the `--accent-soft` backgrounds (lines 152, 232) are the accent's legitimate non-text roles and stay untouched.

The `.tabbar` active variant (Tabs.css:480-481) overrides only `box-shadow` and `background` — it does NOT set `color`, so it inherits the swapped label color from line 149. One edit therefore covers both the bare `.tabs` and `.tabbar` scopes (spec Risk R3, confirmed).

Lines 97 (inactive label), 326 (close icon), and 388 (dirty dot) are NOT changed here — they are fixed by the Task 001 token sync.

**Fallback convention departure (architect Finding B):** every `var()` in Tabs.css carries a defensive fallback literal (documented file convention). These two swapped sites must use `var(--text)` WITHOUT a fallback literal, because the `/implement` design-token provenance gate (`verify-design-tokens`) forbids `var(--x, <literal>)` fallbacks on token-bound sites. This is a deliberate, gate-required departure from the per-file convention — do NOT restore a fallback on pattern-following instinct. Add a brief inline comment noting the departure so reviewers see the intent.

## Change Details

- In `src/renderer/src/components/molecules/Tabs.css`:
  - Line 149 — `.tabs__tab--active, .tabs__tab[aria-selected='true']`: change `color: var(--accent, #10b981);` → `color: var(--text);` (no fallback literal). Leave the `box-shadow: inset 0 -2px 0 var(--accent, #10b981)` and `background-color: var(--accent-soft, …)` on the same rule UNCHANGED.
  - Line 233 — active `.tabs__badge` (`.tabs__tab--active .tabs__badge, .tabs__tab[aria-selected='true'] .tabs__badge`): change `color: var(--accent, #10b981);` → `color: var(--text);` (no fallback literal). Leave the sibling `background-color: var(--accent-soft, …)` UNCHANGED.
  - Add a short inline comment at each swapped site noting the no-fallback provenance-gate departure.

## Contracts

### Expects (checked before execution)
- `Tabs.css` rule `.tabs__tab--active, .tabs__tab[aria-selected='true']` sets `color: var(--accent, …)`.
- `Tabs.css` active-badge rule (`.tabs__tab--active .tabs__badge, .tabs__tab[aria-selected='true'] .tabs__badge`) sets `color: var(--accent, …)`.
- `Tabs.css` `.tabbar .tabs__tab--active` rule sets only `box-shadow` and `background` (no `color`) — so the swapped label color inherits into `.tabbar`.

### Produces (checked after execution)
- `Tabs.css` rule `.tabs__tab--active, .tabs__tab[aria-selected='true']` sets `color: var(--text)` with NO fallback literal.
- `Tabs.css` active-badge rule sets `color: var(--text)` with NO fallback literal.
- The active-tab `box-shadow: inset 0 -2px 0 var(--accent, …)` and both `background-color: var(--accent-soft, …)` declarations remain present and unchanged.
- No `.tabbar`-scoped `color` override is added (the `.tabbar` active variant still inherits line 149's color).

## Done When

- [x] Active-tab label rule computes `color: var(--text)` (no fallback) in bare `.tabs` and `.tabbar` scopes
- [x] Active-tab badge text rule computes `color: var(--text)` (no fallback)
- [x] Accent underline (box-shadow) and `--accent-soft` backgrounds are unchanged
- [x] No fallback literal on the two swapped `color` declarations (provenance-gate compliant); inline departure comment present
- [x] No debug artifacts left in changed files
- [x] Type checker passes on changed files (see Development Commands section)
- [x] Linter passes on changed files (see Development Commands section)
- [x] No new secrets or credentials in code

## Completion Notes

**Completed**: 2026-07-02T21:36:18Z
**Files changed**: src/renderer/src/components/molecules/Tabs.css
**Contract**: Expects 3/3 | Produces 4/4
**Notes**: (none)
