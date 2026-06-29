# Feature Summary — 010-request-bar-fidelity

**Verdict**: APPROVED (`/verify`) · **Status**: Complete

## What was built

The RequestBar — the top-of-request control row holding the HTTP-method pill, URL input, and Send/Save/Share actions — was brought into pixel-fidelity with the design reference. Visually it now matches the mockup's spacing, typography, borders, per-method colors, the green Send button with its ⌘↵ keycap, and the focus ring on the URL field. The work is presentation-only: no request/response behavior, store wiring, or keyboard shortcuts changed — only how the bar looks and a comprehensive computed-style test suite that locks that appearance against future drift.

## Changes

- **Markup (task 001)** — gave Save/Share visible text labels (dropping the redundant `aria-label`) and made the Send ⌘↵ keycap an `aria-hidden` element that renders only when Send is enabled. No logic touched.
- **Styling (task 002)** — rewrote RequestBar CSS to the design reference using existing design tokens: a single `.request-bar`-scoped ancestor rule supplies the flat elevated method-pill treatment while per-method text color falls through from the `data-mstyle` token rules; added the keycap, ghost-bordered Save/Share, and the weight-600 Send with inset shadow.
- **Tests (task 003)** — added a `RequestBar — fidelity` component-test suite: exact computed-style assertions (heights, radius-token binding, box-shadow, per-method background/color, Send weight + shadow, keycap presence/absence, Save/Share bordered + labelled) plus a thresholded screenshot baseline.
- **Post-review fidelity fixes** — runtime design-audit (live `getComputedStyle` against the rendered app) plus cross-task review surfaced and closed: the HEAD method's missing chip-mode color rule, the action-button gap (4px → reference 8px), Save/Share `font-weight: 500`, and keycap `letter-spacing: 0.02em` — each now locked by a computed-style test, with chip-mode coverage extended to all 7 methods and the outline/dot/bar/text mstyle variants.

## Files changed

22 files changed, +2830 / −111. Feature code + tests:
- `src/renderer/src/components/organisms/RequestBar.tsx`, `RequestBar.css` — the markup + styling.
- `src/renderer/src/components/organisms/__tests__/` — `RequestBar.ct.tsx`, `RequestBar.stories.tsx`, `RequestBar.test.tsx` (fidelity CT suite + fixtures).
- `__snapshots__/.../request-bar-fidelity-chromium-darwin.png` — the visual-regression baseline.

The remaining changes are pipeline artifacts under `specs/010-request-bar-fidelity/` and `research/` (spec, plan, tasks, review/verification reports).

## Key decisions

- **Method-pill color via cascade fall-through** — one `.request-bar`-scoped ancestor rule (0,3,0) sets the elevated background/border/radius and declares **no `color`**, so each method's text color falls through from its `[data-mstyle] .method.{METHOD}` token rule. Keeps per-method coloring token-driven without per-method overrides in RequestBar.
- **Keycap is a DOM-presence contract** — the ⌘↵ `<kbd>` renders only when `canSend`, satisfying AC-10's "not rendered when disabled" as presence (not mere visibility).
- **Visible text as the accessible name** — Save/Share visible labels supply the accessible name (redundant `aria-label` dropped); the keycap stays `aria-hidden` so Send's accessible name stays "Send".
- **URL focus** — accent border + 3px `var(--accent-soft)` ring, reusing the token that already equals the reference's accent-14% mix.

## Deviations from plan

- **Task 002** — removed `var(--token, <literal>)` fallback literals in favor of token-only binding (the CT harness imports `tokens.css` globally, so fallbacks were redundant and would have masked a missing-token regression).
- **Task 003 (resolved later)** — the task-time notes flagged a pre-existing AC-20 reflow (long URL pushing the Send button) introduced by the tasks 001/002 markup/CSS; subsequent post-review `/fix` rounds remediated it, and the feature now verifies APPROVED with all 19 ACs passing.

## Acceptance criteria

All 19 ACs **PASS** (per `verification.md`, code-verified; assembled type-check / lint / build / test passed):

- [x] AC-1 — AC-19 (module structure, no design-export cruft, Shell sole `data-mstyle` writer, active-tab render, control/shortcut behavior preserved, URL radius + focus ring, method-pill reference treatment, bar geometry, Send enabled/disabled states, Save/Share layout, `.request-bar`-scoped styling, computed-style fidelity suite, documented fidelity rationale, strict type-check, lint, build, no stray inline styles, unit + component suites pass).
