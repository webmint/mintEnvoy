# Feature Summary: 005 — Tab Bar Visual Fidelity

**Status**: Complete · **Verdict**: APPROVED (`/verify`) · **Design source**: `design/reference.html`

## What was built

The working-tabs TabBar now matches the design reference. Each tab shows a colored HTTP-method chip (incl. a new pink HEAD color), a dirty tab shows a small dot in place of its close button (clean tabs show an always-visible SVG close), the active tab gets the accent underline + lifted-strip treatment, and the strip carries the correct geometry — padded cells, separators, a single bottom border, and a `+` / overflow-chevron actions row. Visual correctness is locked by a Playwright computed-style fidelity suite that asserts every value in a real browser. The opt-in `method`/`dirty` fields were added to the shared Tabs primitive without changing any existing consumer.

## Changes

- **Method tokens + HEAD color** — added `--m-head` (light/dark) and the `.method` font + HEAD color rules to `tokens.css`.
- **Tabs render contract** — `TabDescriptor` gained optional `method` / `dirty`; renders the method chip + the dirty-dot-XOR-close control; non-closable path stays byte-identical to the 002 contract.
- **Tabs fidelity CSS** — `.tabbar`-scoped active `::before`/`::after` accent, tab-cell geometry, the dirty dot, and the close control.
- **TabBar descriptor + actions row** — maps `method`/`dirty` into descriptors; adds the `+` / spacer / overflow-chevron actions row.
- **Strip geometry + border de-dup** — `.tabbar` strip background/height/border/padding; removed the duplicate Shell border so the strip has exactly one bottom border.
- **CT token harness** — `tokens.css` imported into the Playwright mount root (verified zero blast radius).
- **Tests** — Tabs behavior suite (byte-identical, dirty-XOR-close, method chip, keyboard close), TabBar suite (descriptor mapping, dirty-dot→store close, actions row), and the real-browser computed-style + screenshot fidelity suite.
- **002 lineage** — recorded the 005 contract extension in the Tabs-primitive spec lineage.
- **Post-implement fidelity fix** — a gated remediation closed 4 visual drifts caught on the running app (cell padding moved to the wrapper, `+` re-anchored to the last tab, flush action buttons, whole-cell hover) plus 4 `/review` findings (method-chip `aria-hidden` to stop a double screen-reader announce, redundant-border removal, comment corrections); +6 CT assertions added.

## Files changed

`+4111 / −148` across 37 files.

- **`src/renderer`** (10) — `styles/tokens.css`; `components/molecules/Tabs.tsx` + `Tabs.css`; `components/organisms/TabBar.tsx` + `TabBar.css` + `Shell.css`; the molecule + organism test suites (`Tabs.test`, `Tabs.ct`, `Tabs.stories`, `TabBar.test`).
- **`playwright`** (1) — `index.tsx` token-harness import.
- **`__snapshots__`** (1) — the fidelity screenshot baseline.
- **`specs`** (25) — feature planning artifacts (spec, plan, grill, breakdown, 10 task files, review/verify/summary records) + the 002 lineage edit.

## Key decisions

- **(a) Active accent** — `::before` accent stripe + `::after` mask for the lifted-tab effect (no layout shift).
- **(b) Overflow** — `.tabbar` uses `overflow:visible` so the `bottom:-1px` mask renders; the bare `.tabs` consumer keeps `overflow:hidden` (AC-22).
- **(c) Method chip** — reuses the existing global `.method`/`.{METHOD}` palette inside the BEM Tabs primitive (documented constitution §2.3 departure) rather than duplicating colors.
- **(d) `--m-head`** — `#ec4899` (light) / `#f472b6` (dark); HEAD coloring scoped to the default `soft` mstyle.
- **(e) Screenshot threshold** — `toHaveScreenshot({ threshold: 0.2, maxDiffPixelRatio: 0.01, animations: 'disabled' })`, supplementary to the computed-style primary gate.
- **(f) Dirty-dot-XOR-close** — dirty → non-focusable clickable dot; clean → always-visible SVG close; mutually exclusive, close routed via the retained Delete/Backspace keyboard path.
- **(g) CT harness** — fidelity fixture reproduces the full styling context (tokens.css + `data-mstyle='soft'` + the production `.tabbar` className scope).

## Deviations from plan

- **Tiered verification, grill-hardened** — two `/grill` cycles tightened the CT harness contract before implementation; the fidelity CT then caught a real strip-geometry gap (harness wasn't loading `TabBar.css`), fixed by composing the organism CSS into the test, not duplicating into the molecule.
- **Post-`/implement` remediation** — 4 visual drifts visible only on the running app (not caught by the molecule-fixture CT) were fixed via a gated `/fix` after implementation; `review.md` was refreshed via a second `/review` before `/verify` approved.
- **Pre-existing bug filed** — `bugs/003` (Dropdown CT click-outside) surfaced during the CT-harness blast-radius check; confirmed unrelated to 005 and deferred.

## Acceptance criteria

29/29 PASS (per `verification.md`, `tests` mode — code-read, fidelity ACs cross-checked against the real-browser CT computed-style assertions).

- [x] AC-1 … AC-29 — all PASS.
