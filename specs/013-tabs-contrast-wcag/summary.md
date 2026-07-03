# Summary: 013-tabs-contrast-wcag

**Status**: Complete · **Verdict**: APPROVED (`/verify`) · **Date**: 2026-07-03

## What was built

The working-tabs strip now meets WCAG 2.1 AA contrast in both light and dark themes. Every muted and faint text role across the app (inactive tab labels, close-button icons, dirty-state dots — and the same tokens wherever else they're used) was brought to AA by syncing the design tokens to their already-darkened design source, and the two accent-colored text sites on the active tab (its label and badge) were switched to the primary text color so they read clearly instead of failing as low-contrast green.

## Changes

- **Sync drifted text tokens** — updated three stale muted/faint token values in the app's design tokens to match the design source (light muted `#6c6c75`, light faint `#6e6e77`, dark faint `#787881`), fixing every consumer of those tokens app-wide in one edit. No new token introduced.
- **Fix active-tab accent-on-light text** — swapped the active-tab label and active-tab badge text from the accent color to the primary text color (`var(--text)`), clearing AA; the `.tabbar` variant inherits the same fix. The accent's legitimate non-text roles (underline, tinted backgrounds) are untouched.
- **Lock the fix with tests + baselines** — added component-test contrast assertions pinning the five fixed text sites across light and dark, in both the bare-tabs and `.tabbar` scopes, and regenerated the three affected screenshot baselines.

## Files changed

- `src/renderer/styles/tokens.css` — 3 text-token value syncs (light `--text-muted`/`--text-faint`, dark `--text-faint`).
- `src/renderer/src/components/molecules/Tabs.css` — 2 active-tab color swaps to `var(--text)`; 6 stale fallback literals dropped (remediation).
- `src/renderer/src/components/molecules/__tests__/` — `Tabs.ct.tsx` (contrast assertions, light + dark, tabbar + bare scopes) and `Tabs.stories.tsx` (two badge fixtures).
- `design/tokens.json` — dark `textFaint` synced to the source value.
- `__snapshots__/…` — 3 regenerated fidelity baselines (Tabs, Dropdown, RequestBar).
- `specs/013-tabs-contrast-wcag/…`, `research/…` — planning/record artifacts.
- Totals: 24 files, +1605 / −13 (the bulk is planning markdown + regenerated binary baselines; the code surface is small).

## Key decisions

- **Fix mechanism** — sync `tokens.css` to the design source (3 values) rather than adding a new token; the source already carried AA-safe values, so one edit fixes every muted/faint consumer app-wide.
- **Active-tab label + badge** — `var(--accent)` → `var(--text)`; accent-as-text was sub-AA regardless of the token sync, and `var(--text)` clears AA with margin. `.tabbar` inherits the label color, so one edit covers both variants.
- **Inactive label / close icon / dirty-dot** — no per-site change; the token sync alone brings them to AA.
- **No new `--text-secondary` token and no design-fidelity-contract §5 hand-edit** — the ramp gap that would have motivated a new token doesn't exist once the tokens are synced, and §5 derives from the design source (editing it would desync it).

## Deviations from plan

- **Task 001** — also deleted a pre-existing lint-failing throwaway research probe (`research/2026-07-01-bug-005-active-tab/probe-script.mjs`) to clear the repo-wide ESLint gate (user-approved), and synced the one stale value in `design/tokens.json` to keep the two design artifacts consistent (architect Finding A). Both out of the original token-scope but folded in.
- **Task 003** — added `TabbarBadgeFidelityFixture` (and, via the later remediation, `TabsBadgeFidelityFixture`) because no existing fixture rendered a badge; kept computed-color equality assertions rather than an in-test WCAG ratio calc (fragile against the semi-transparent accent-soft badge background — ratios are proven analytically in the spec). The `/review` findings that followed (stale fallback literals + bare-scope coverage) were remediated via `/fix` and re-confirmed clean.

## Acceptance criteria

All 10 ACs **PASS** (per `verification.md`, `tests` mode / code-read):

- [x] AC-1 — tokens defined at the darkened design-source values
- [x] AC-2 — existing token names/semantics preserved, no new token
- [x] AC-3 — active vs inactive labels stay visually distinct (both themes)
- [x] AC-4 — every muted/faint text role brought to WCAG AA via the token sync
- [x] AC-5 — active-tab label meets AA via `var(--text)` (tabbar inherits)
- [x] AC-6 — active-tab badge text meets AA via `var(--text)`
- [x] AC-7 — inactive-tab label meets AA via synced `--text-muted`
- [x] AC-8 — close-button icon meets AA (non-text) via synced `--text-faint`
- [x] AC-9 — dirty-state indicator meets AA (non-text) via synced `--text-faint`
- [x] AC-10 — lint + type-check pass on all changed files
