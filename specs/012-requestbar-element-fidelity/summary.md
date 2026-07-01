# Summary: 012-requestbar-element-fidelity

**Verdict** (from `/verify`): **APPROVED** — 19/19 acceptance criteria passed.

## What was built

The RequestBar (the method + URL + Send/Save/Share row) and the shared Dropdown menu panel were brought into pixel-level agreement with the design reference. Users now see the URL field as a single bordered box with a leading link icon inside it and a focus ring around the whole field, an icon-only Share button, a right-aligned method-dropdown chevron in a correctly-sized pill, and a crisper dropdown panel — all matching the reference in every method-style theme (soft and chip). Behaviour is unchanged: Send/Save/Share, keyboard shortcuts, per-tab state, and the method dropdown all work exactly as before.

## Changes

- **Markup restructure** — wrapped the URL input in a `.url-bar` container with a leading decorative link icon, corrected the placeholder to `Enter URL or paste cURL command…`, and made Share icon-only with a restored `aria-label` (no behaviour change).
- **RequestBar styling** — bound the `.url-bar` box (border, background, height, `:focus-within` accent ring) and the method trigger to reference tokens; the container owns the box while the input stays borderless and full-height (fixing dead click-zones); Save rest/hover treatments matched to the reference.
- **Shared Dropdown panel** — upgraded the panel to `--shadow-lg`, a 1px inter-item gap, and `6px 8px` item padding, bound to existing tokens.
- **Fidelity test suite** — added computed-style exact-equality Playwright component tests + thresholded screenshot diffs across both mstyle variants, locking every corrected value so drift can't silently return.

## Files changed

`src/` (6 files) — RequestBar.tsx, RequestBar.css, Dropdown.css + the RequestBar/Dropdown unit & component tests. `__snapshots__/` (2) — rebaselined RequestBar + Dropdown fidelity screenshots. Plus `specs/` (15) and `research/` (2) planning artifacts.

**25 files changed, 2504 insertions(+), 95 deletions(-).**

## Key decisions

- **URL field = `.url-bar` flex container** (aria-hidden link icon + the existing input); the container owns the bordered box, the input is transparent/borderless.
- **Method trigger keeps `color` UNSET** so the per-method chip colour falls through the `[data-mstyle]` cascade; only the redundant `justify-content` was removed.
- **Seven `[data-mstyle='chip']` per-method counter-rules kept in lockstep** with the `METHODS` list — the guard against the white-on-white chip regression.
- **Shared `Dropdown.css` edited in place** (shadow-lg / 1px gap / 6px 8px padding) rather than forked — one panel, one source of truth.
- **All values bound to EXISTING design tokens** (`--shadow-lg`, `--radius-md`, colour/padding tokens) — no new tokens, no hardcoded literals.
- **Fidelity verified by computed-style EXACT-equality Playwright CT + screenshot diff** at `maxDiffPixelRatio: 0.01, threshold: 0.1`.

## Deviations from plan

- **Post-implement fidelity refinements (review→fix loop).** The 4 planned tasks landed as specced, but the runtime design-auditor (live-app computed-style diff vs the rendered reference) caught several default-mode-invisible fidelity gaps that static review + CT could not, remediated across four gated `/fix` rounds: the method chevron was inheriting the per-method colour (corrected to a dark `--text` caret in all mstyles), the method button rendered 29px vs the reference 33px (fixed via `line-height:17px`) and 31px in chip mode (fixed by `border:1px solid transparent` on the chip counter-rules), plus completeness CT locks (Dropdown styles from the consumer path, `.url-bar` height, chip justify-content/height/border). Each fix was panel-gated and CT-locked; the design-manifest was left intentionally empty (the reference carries no `data-ref` anchors).
- Minor in-task notes: task 002 added `height:100%` to the input (eliminating dead click-zones); task 003's 1px item gap also adds 2px around dropdown separators (no method-dropdown impact).

## Acceptance criteria

All 19 verified PASS by `/verify` (mode: tests / code-read + assembled mechanical checks):

- [x] AC-1 – AC-19 — no design-export cruft, link icon in the icon set, behaviour preservation, per-tab isolation, Shell sole `data-mstyle` writer, Share disabled/icon-only + aria-label, exact placeholder, Save hover treatment, Dropdown panel treatment, computed-style fidelity suite, url-bar structure, method-select treatment, source documentation, type-check / lint / build clean, no inline styles, unit + component suites green.
