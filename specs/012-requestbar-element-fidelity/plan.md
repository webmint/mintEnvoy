# Plan: requestbar-element-fidelity

**Date**: 2026-07-01
**Spec**: specs/012-requestbar-element-fidelity/spec.md
**Status**: Approved

## Specialist Consultation

**Invocations**:

- Phase 0 alternatives: no — N/A (no 2+ alternatives compared fresh; the sole alternative — defer the shared Dropdown panel — was already settled-rejected in the upstream research handoff and confirmed by the user at /specify).
- Phase 1.3 architecture decisions: yes (mandatory) — architect authored the Layer Map, Key Design Decisions, Risk seeds, and Constitution flags below.
- Specialists consulted (orchestrator-relayed on the architect's request, or directly): none — the architect returned zero consultation requests (presentational token-rebind; the two non-trivial axes are already documented in docs/architecture.md + spec §7/§9).

**Architect-authored sections** (transcribed verbatim from architect return):

- Layer Map: rows 1-5
- Key Design Decisions: rows 1-9
- Risk Assessment seeds: rows 1-5
- Constitution Compliance flags: Design Fidelity — /breakdown must emit the design-manifest (Phase 3.5 integrity gate); no rule violations.

| Specialist | Sub-question                                                              | Input summary                                                                                                                                                        | Verdict  | Cites                                                                      |
| ---------- | ------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------- |
| architect  | Layer map, key decisions, risks, constitution flags for the fidelity pass | Single Presentation layer; keep method-trigger `color` unset; keep chip counter-rules in lockstep; restore Share aria-label; reuse 010 screenshot threshold 0.01/0.1 | accepted | docs/architecture.md:240-275 (method-select cascade hazard); own-reasoning |
| (none)     | —                                                                         | —                                                                                                                                                                    | —        | —                                                                          |

## Summary

Rebind five drifted presentational props of the RequestBar organism (`RequestBar.tsx` + `RequestBar.css`) and the shared Dropdown molecule's open panel (`Dropdown.css`) to the resolved values in `design/styles.css`, using existing `tokens.css` custom-properties — no new tokens, no logic change. Verification is computed-style EXACT-equality Playwright CT plus a thresholded screenshot diff, reusing the 005/010 fidelity-CT scoping. No research.md was generated: no research signals (link icon + Radix already in-stack, approach settled by the upstream HOW-seed); codebase patterns were read during /specify.

## Technical Context

**Architecture**: Renderer atomic-design tiers — the change is confined to the Presentation layer (organisms `RequestBar` + the shared molecule `Dropdown`), reusing the existing `link` Icon atom. No lib/store/main/preload surface touched; dependency direction (organisms→molecules→atoms→lib) preserved.
**Error Handling**: N/A — presentational CSS/markup only; no fallible operations added.
**State Management**: Unchanged — the URL input stays bound to `RequestSpec.url` via `tabsStore.updateActiveSpec`; the `canSend` trim guard reads the same value; Shell remains the sole writer of `data-mstyle`.

## Constitution Compliance

- §2 Architecture Rules (dependency direction) — organisms→molecules→atoms→lib preserved; the only intentional cross-component change is the shared Dropdown panel (IN scope). **Compliant.**
- §4 Patterns / Styling (semantic classes bound to tokens.css, no inline styles, no new tokens, cx() composition) — **Compliant.**
- §4 Never (only Shell writes `data-mstyle`) — the method-trigger colour stays on the `.method/.{METHOD}` class path; RequestBar never writes `data-mstyle`. **Compliant.**
- Design Fidelity principle — feature has `design/reference.html`, so `/breakdown` MUST emit the design-manifest + static token-provenance check (Phase 3.5 integrity gate); every binding traces to a `design/styles.css` resolved value. **Requires attention at /breakdown.**

## Implementation Approach

### Layer Map

| Layer                             | What                                                                                                                                                                                                                                                                                               | Files (existing or new)                                                                                                                                               |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Presentation — organisms          | RequestBar markup restructure: wrap URL input in `.url-bar` flex container with leading aria-hidden `<Icon name="link">`, exact placeholder, icon-only Share + `aria-label="Share"`, keep Save label — presentational only, no logic                                                               | src/renderer/src/components/organisms/RequestBar.tsx                                                                                                                  |
| Presentation — organisms (styles) | `.url-bar` container + focus-within ring; `.method-select` treatment with `justify-content:center` removed and `color` still unset; `.btn-ghost` Save rest+hover; seven `[data-mstyle='chip']` counter-rules kept in lockstep with `METHODS`; all scoped under `.request-bar`                      | src/renderer/src/components/organisms/RequestBar.css                                                                                                                  |
| Presentation — molecules (shared) | Open-panel rebind: `.dropdown-content` `box-shadow var(--shadow-lg)` + 1px inter-item gap; `.dropdown-item` padding `6px 8px` — bounded cross-component change, ripples to dev-only PrimitivesDemo                                                                                                 | src/renderer/src/components/molecules/Dropdown.css                                                                                                                    |
| Support — atoms (reuse only)      | Existing `link` Icon consumed as URL leading icon — no change                                                                                                                                                                                                                                      | src/renderer/src/components/atoms/icons.ts                                                                                                                            |
| Test — CT/unit                    | Computed-style EXACT-equality Playwright CT on the five props + thresholded screenshot diff; tokens.css + `data-mstyle='soft'` fixture, Radix two-step dismiss gate, non-empty-URL no-reflow baseline, mstyle variants beyond soft; rebaseline Dropdown panel snapshot; existing suites stay green | src/renderer/src/components/organisms/**tests**/RequestBar.ct.tsx, .../**tests**/RequestBar.test.tsx, src/renderer/src/components/molecules/**tests**/Dropdown.ct.tsx |

### Key Design Decisions

| Decision                        | Chosen Approach                                                                                                                                                                                                                                              | Why                                                                                                                                                                                                | Alternatives Rejected                                                                                           |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| URL field structure             | `.url-bar` flex container [aria-hidden link Icon + existing input, gap 6px]; input stays bound to `RequestSpec.url` via `updateActiveSpec`; `canSend` trim guard reads same value                                                                            | Matches reference `.url-bar`; icon is decorative so aria-hidden; zero behaviour change preserves 009/010 (AC-3/AC-12); Icon reused from atoms                                                      | Bare input with `::before` pseudo-icon — can't host the SVG atom, duplicates icon markup                        |
| Method-trigger color            | Keep `color` UNSET on `.request-bar .request-bar__method.method`; remove only the extra `justify-content:center`                                                                                                                                             | Documented cascade hazard: per-method colour falls through `[data-mstyle]` at the (0,3,0) tie won by source-order; adding `color` kills all seven per-method colours with no compile error (AC-13) | Setting explicit per-method `color` on the trigger — reintroduces the hazard docs/architecture.md warns against |
| Chip counter-rules              | Keep the seven `(0,5,0)` `[data-mstyle='chip']` per-method counter-rules in lockstep with `METHODS` in httpMethods.ts                                                                                                                                        | Removing/drifting any reintroduces the white-on-white chip regression; CT asserts per-method computed colour across mstyle variants, not just soft                                                 | Dropping counter-rules assuming soft-only usage — Shell can set any mstyle                                      |
| Share accessible name           | Drop visible text node (icon-only), restore `aria-label="Share"`; stays disabled no-op in final slot                                                                                                                                                         | Visible text previously supplied the accessible name; icon-only without aria-label breaks `getByRole` name queries (AC-8, AC-6)                                                                    | Icon-only with no aria-label — silently breaks accessible-name regression queries                               |
| Save button                     | Keep visible label; bind reference `.btn-ghost` rest (color `--text-muted`, border `--border`, bg `--bg-elev`) + hover (color `--text`, border-color `--border-strong`)                                                                                      | Reference keeps Save labelled; hover is pure treatment via existing tokens (AC-9)                                                                                                                  | Icon-only Save — reference shows labelled; out of scope                                                         |
| Shared Dropdown panel rebind    | Edit shared `Dropdown.css` in place: `box-shadow var(--shadow-lg)`, 1px inter-item gap, `.dropdown-item` padding `6px 8px`; accept ripple to PrimitivesDemo + rebaseline snapshot                                                                            | Panel is IN scope (defer-alternative rejected at /specify); only consumers are RequestBar + dev-only tree-shaken PrimitivesDemo, so blast radius is bounded and deliberate (AC-10)                 | Fork a RequestBar-local dropdown panel class — duplicates the molecule, violates DRY                            |
| Token binding                   | Bind all shadow/radius/colour/padding to EXISTING tokens (`--shadow-lg`, `--radius-md`, `--radius`, `--bg-elev`, `--bg-hover`, `--border`, `--border-strong`, `--font-mono`, `--text-muted`); raw px only for item padding + panel gap where no token exists | Every target value already exists as a token; "prefer design tokens over literal values" (§7); no token additions (AC-1, OOS F-spec-2)                                                             | Adding new tokens or restoring un-gated `.method` colour defaults — explicitly out of scope                     |
| Fidelity verification           | Computed-style EXACT-equality Playwright CT + thresholded screenshot diff; tokens.css + `data-mstyle='soft'` fixture, Radix two-step dismiss gate, non-empty-URL no-reflow baseline                                                                          | jsdom can't resolve computed/pseudo styles — real-browser CT required (AC-11); reuses 005/010 fixture-scoping lessons                                                                              | Vitest/jsdom-only assertions — cannot read resolved computed styles or pseudo-elements                          |
| Screenshot-diff threshold (Q-1) | `toHaveScreenshot(..., { maxDiffPixelRatio: 0.01, threshold: 0.1 })` on the RequestBar/panel fidelity snapshots                                                                                                                                              | Reuses the 010 precedent verbatim for consistency with the established fidelity suite; settles Q-1 with an explicit (non-eyeballed) threshold (AC-11)                                              | A fresh/tighter threshold — inconsistent with the sibling 010 CT, no basis to diverge                           |

### File Impact

| File                                                                | Action | What Changes                                                                                                                                                                                                                                           |
| ------------------------------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| src/renderer/src/components/organisms/RequestBar.tsx                | Modify | Wrap URL input in a `.url-bar` container + leading aria-hidden `<Icon name="link">`; set placeholder to `Enter URL or paste cURL command…`; drop the Share text node (icon-only) + add `aria-label="Share"`; keep Save label. No logic change.         |
| src/renderer/src/components/organisms/RequestBar.css                | Modify | Add `.url-bar` container treatment + `:focus-within` accent ring; method-select treatment with `justify-content:center` removed, `color` unset; Save `.btn-ghost` rest+hover; keep the seven chip counter-rules in lockstep; all under `.request-bar`. |
| src/renderer/src/components/molecules/Dropdown.css                  | Modify | `.dropdown-content` → `box-shadow var(--shadow-lg)` + 1px inter-item gap; `.dropdown-item` padding → `6px 8px`.                                                                                                                                        |
| src/renderer/src/components/organisms/**tests**/RequestBar.ct.tsx   | Modify | Add computed-style EXACT-equality asserts for url-bar / method-select / Save hover / icon-only Share + a thresholded screenshot diff (`maxDiffPixelRatio: 0.01, threshold: 0.1`); cover mstyle variants beyond soft; non-empty-URL baseline.           |
| src/renderer/src/components/organisms/**tests**/RequestBar.test.tsx | Modify | Extend unit asserts: exact placeholder string, Share icon-only accessible name (`getByRole` name = Share), Save label retained.                                                                                                                        |
| src/renderer/src/components/molecules/**tests**/Dropdown.ct.tsx     | Modify | Add panel computed-style asserts (shadow/gap/item-padding) + rebaseline the panel screenshot snapshot; keep the Radix two-step dismiss gate.                                                                                                           |

### Documentation Impact

| Doc File               | Action | What Changes                                                                                                                                                                                                                    |
| ---------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| docs/architecture.md   | Update | Extend the `RequestBar — method-select CSS cascade` section to note the new `.url-bar` container structure + the icon-only Share, and the shared Dropdown open-panel reference values (shadow-lg / 6px 8px item pad / 1px gap). |
| docs/renderer/index.md | Update | Refresh the RequestBar/Dropdown one-liners if the URL-input structure or Share affordance description drifts.                                                                                                                   |

### Established-Convention Departures

_None — every decision reuses an established pattern (token binding, `.request-bar` scoping, the `.method/.{METHOD}` cascade, the 005/010 CT fixture-scoping and screenshot-threshold precedent)._

## Risk Assessment

| Risk                                                                                                                                                               | Likelihood | Impact | Mitigation                                                                                                                                                                                              |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Shared Dropdown panel rebind ripples to dev-only PrimitivesDemo + visual-snapshot baselines (unrelated dropdown regression / snapshot failure)                     | Med        | Low    | Limit the edit to box-shadow + item padding + panel gap; deliberately rebaseline the Dropdown snapshot; the other consumer is dev-only, tree-shaken from production.                                    |
| Method-trigger CSS edit reintroduces white-on-white chip regression (counter-rules drift from `METHODS`) or kills all per-method colours (accidental `color` decl) | Med        | Med    | Keep `color` unset on `.request-bar__method.method`; keep the seven `(0,5,0)` counter-rules in lockstep with `METHODS`; assert per-method computed colour across mstyle variants (not just soft) in CT. |
| Method-trigger + Save-hover may already match the reference from 010 — locking ACs without a runtime check could enshrine wrong values (spec Q-2)                  | Low        | Med    | Carry a design-auditor runtime computed-style + screenshot diff vs design/reference.html to /breakdown as a verification task before locking those ACs; residual drift, if any, is context-only.        |
| Dropping Share's visible label without an accessible name breaks existing `getByRole` name queries                                                                 | Low        | Med    | Add `aria-label="Share"` when going icon-only; run existing RequestBar CT + unit accessible-name queries as a regression gate.                                                                          |
| CT flakiness — Radix dismiss arm-race, keycap-mount no-reflow baseline confound, jsdom cannot resolve computed/pseudo styles                                       | Med        | Med    | Real-browser Playwright CT only; two-step dismiss gate; non-empty-URL no-reflow baseline; clear playwright/.cache + node_modules/.vite + dist on clean-file build errors.                               |

## Dependencies

None — no packages to install, no services to configure, no environment variables. Reuses the existing `link` Icon atom, `tokens.css` custom-properties, Radix (already in deps), and the Playwright CT harness.

## Supporting Documents

- No research.md — no research signals (link icon + Radix already in-stack; approach settled by the upstream research HOW-seed).
- No data-model.md — no entities.
- No contracts.md — no API changes.
