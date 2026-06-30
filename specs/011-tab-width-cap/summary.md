# Feature Summary: 011-tab-width-cap

**Status**: Complete · **Verdict**: APPROVED (see `verification.md`)

## What was built

Working tabs in the tab bar no longer grow without bound as their titles get longer. Each tab cell is now capped at a fixed width and overlong request titles truncate with an ellipsis, so the tab strip stays tidy and the new-tab button and overflow controls stay anchored instead of being pushed off to the side. The cap was moved onto the tab cell itself (matching the design contract), so it behaves consistently regardless of method-chip width — and bare `<Tabs>` consumers outside the tab bar are unaffected.

## Changes

- **Relocated the width cap onto the tab cell** — the 220px cap now sits on the `.tabbar` tab-cell wrapper (where the design contract §5 puts it) instead of on the label; the old divergent 200px label cap was removed. Long titles truncate via the existing label ellipsis rule.
- **Proved the cap in a real browser** — added a long-title test fixture and Playwright component tests that assert the cell's computed 220px cap, that an overflowing title is held at the cap and shows an ellipsis, that multiple long tabs keep the action buttons anchored, and that bare (non-tabbar) tabs stay uncapped.

## Files changed

`19 files changed, 1421 insertions(+), 30 deletions(-)` (most of which is the feature's spec/plan/task/review records).

Code (`src/renderer/src/components/`):
- `molecules/Tabs.css` — added the `max-width: 220px` cap to the `.tabbar` tab-cell wrapper with a design-fidelity-contract §5 comment.
- `organisms/TabBar.css` — removed the now-redundant `.tabbar` label rule; rewrote the file-block header from "Label truncation" to "Tab width cap".
- `molecules/__tests__/Tabs.stories.tsx` — added `TabbarLongTitleFidelityFixture` (two long + one short tab, with a fixture-scoped border-box reset).
- `molecules/__tests__/Tabs.ct.tsx` — added four component tests (computed 220px cap, long-title no-growth + ellipsis, tablist anchoring bound, bare-consumer uncapped).

Records: `specs/011-tab-width-cap/` (spec, plan, tasks, review, verification), `research/`.

## Key decisions

- **Cap the cell, not the label** — capping `.tabbar .tabs__tab-wrapper` makes tab width independent of the method-chip and fires the existing label ellipsis, matching contract §5.
- **Cap rule lives in `Tabs.css`** alongside the other `.tabbar` cell-geometry overrides, and is `.tabbar`-scoped so bare `<Tabs>` consumers stay uncapped (AC-3).
- **Reuse the base `.tabs__tab-label` ellipsis rule** rather than writing new truncation CSS (search-before-building) — removing the label cap drops only its `max-width`, not the ellipsis triple.
- **Literal `220px` with a §5-citing comment** — consistent with the prior literal cap; tokens.css has no per-component width token.
- **Prove the cap with Playwright computed-style tests** — jsdom cannot resolve computed layout, so a real-browser fixture reproduces the production cascade.

## Deviations from plan

- **Task 001**: removed the entire redundant `.tabbar .tabs__tab-label` rule (its post-cap declarations duplicated the base rule) rather than only deleting the `max-width` line — a review-panel cleanup; also rewrote the TabBar.css file-block header to match.
- **Task 002**: reproduced production `box-sizing: border-box` via a fixture-scoped `<style>` after a global `base.css` import into the CT harness broke two unrelated screenshot baselines (reverted); `playwright/index.tsx` left net-unchanged. Full CT suite: 161/161 passing.

## Acceptance criteria

All 13 verified PASS (code) — verdict APPROVED (`verification.md`):

- [x] AC-1 — Tabs stylesheet caps the tab-cell wrapper at 220px
- [x] AC-2 — TabBar stylesheet no longer sets the 200px label cap
- [x] AC-3 — bare Tabs consumers stay uncapped
- [x] AC-4 — tab select/close/reorder/dirty-dot/chip/active styling unchanged
- [x] AC-5 — deriveLabel and its text output unchanged
- [x] AC-6 — tab-cell wrapper computed max-width is 220px
- [x] AC-7 — long title held ≤220px and truncated with an ellipsis
- [x] AC-8 — new-tab button, spacer, and overflow chevron stay anchored
- [x] AC-9 — fidelity suite asserts the 220px cap by exact computed-style equality (Playwright CT)
- [x] AC-10 — the cap rule carries a design-fidelity-contract §5 comment
- [x] AC-11 — renderer passes strict type-checking
- [x] AC-12 — codebase passes ESLint with no new errors
- [x] AC-13 — project builds cleanly
