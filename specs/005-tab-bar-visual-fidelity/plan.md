# Plan: tab-bar-visual-fidelity

**Date**: 2026-06-26
**Spec**: specs/005-tab-bar-visual-fidelity/spec.md
**Status**: Approved

> **Revision note (grill-revision, cycle 1)**: This plan was revised after `/grill` returned REVISE-PLAN with 3 confirmed findings, all in the verification design (`specs/005-tab-bar-visual-fidelity/grill.md`). The CSS/React decisions (a)–(f) were confirmed sound and are unchanged. This revision adds **Decision (g) — CT fidelity-harness setup** (the missing wiring that makes the AC-18/AC-19/AC-21 computed-style proofs actually runnable in Playwright CT), lists `playwright/index.tsx` in File Impact, corrects the "computed-style pattern already established" claim, and regrounds the `.tabbar`-scoping rationale on the AC-2 byte-identical test rather than a non-shipping consumer.

## Specialist Consultation

**Invocations**:
- Phase 0 alternatives: no — alternatives were settled upstream in the research handoff (additive opt-in + tokens completion chosen; markup-first-defer-token-gaps rejected as non-compliant by construction). Seeded from the upstream plan-seeds; no fresh alternative discovery run.
- Phase 1.3 architecture decisions: yes (mandatory; consulted twice — initial design + this grill-revision pass for Decision (g) + the two grounding corrections).
- Specialists consulted (orchestrator-relayed on the architect's request, or directly): none — the architect decided directly both passes; CT-harness wiring is within its generalist scope.

**Architect-authored sections** (transcribed verbatim from architect return):
- Layer Map: rows 1-8 (+ CT-harness row added this revision)
- Key Design Decisions: rows (a)-(g)
- Risk Assessment seeds: rows 1-6
- Constitution Compliance flags: §2.1, §2.2/§2.3, §3.1, §3.4, §3.6, §4 (incl. the Shell-sole-data-mstyle-writer invariant, flagged-not-violated)

| Specialist | Sub-question | Input summary | Verdict | Cites |
| --- | --- | --- | --- | --- |
| (none) | — | — | — | — |

## Summary

Close the 8-point visual-fidelity gap between the working-tabs TabBar and `design/reference.html` via the upstream-settled **additive opt-in + tokens completion** approach: add optional `method`/`dirty` fields to the 002 `TabDescriptor`, render a leading method chip and a dirty-dot-XOR-close marker in the Tabs closable branch, complete the method-token set (`--m-head` + base/`HEAD` `.method` rules), rewrite the active-tab accent to the reference's top-`::before`/bottom-`::after` model scoped to `.tabbar`, and remove the one duplicate Shell border. The non-closable Tabs path stays byte-identical (proven by the AC-2 regression test); fidelity is proven by EXACT computed-style assertions in Playwright CT plus a thresholded screenshot diff — both gated on the new CT fidelity-harness setup (Decision (g)) that loads `tokens.css` and the `data-mstyle='soft'` context into the CT mount.

**Why no new research**: all libraries are in-stack (Icon atom, tokens.css `.method` palette, Playwright CT with `snapshotDir` configured, zustand). The `getComputedStyle` mechanic is established (Dropdown.ct.tsx:425 reads `animation-name`, a component-local property), but token-color/geometry resolution in CT is NOT established by that precedent — it needs the CT-harness styling-context setup in Decision (g). The upstream research handoff settled the approach and its rejected alternative. No deep-research signals.

## Technical Context

**Architecture**: Renderer atomic-design tiers — organisms (TabBar) → molecules (Tabs) → atoms (Icon); leaf `lib` (tabsStore, untouched) and `styles/tokens.css`. Downward imports only; `@renderer` alias. Test layer: Playwright CT (real browser) + Vitest.
**Error Handling**: N/A at the design boundary — `method` is narrowed against a `KNOWN_METHODS` const before a color class is applied; an unknown method renders an uncolored chip (total, never throws), consistent with the resolveIcon fallback idiom.
**State Management**: No store change — `tabsStore` lifecycle is untouched; TabBar's `toDescriptor` maps `tab.spec.method`/`tab.dirty` into the new optional descriptor fields.

## Constitution Compliance

- **§2.1 Process boundaries** — Tabs.tsx/TabBar.tsx/tokens.css carry no `electron`/`node:` imports; renderer reaches the platform only via preload globals (AC-29). Compliant.
- **§2.2 / §2.3 Tier + import rules** — the new `Icon` import in Tabs is molecule→atom (downward, allowed) via the `@renderer` alias; no sibling/upward imports. The global `.method` class inside the BEM Tabs primitive is a **documented departure** from BEM-only, recorded in the 002 lineage. Compliant with departure noted.
- **§3.1 Type safety** — `method?`/`dirty?` fully typed; `method` narrowed against a `KNOWN_METHODS` const before applying a color class — no `any`, no cast (AC-25). Compliant.
- **§3.4 Testing** — pseudo-element + token-resolved computed-style fidelity asserted in Playwright CT (jsdom cannot resolve `::before`/`::after` or `var()`); the harness setup (global `tokens.css` + per-test `data-mstyle='soft'`, Decision (g)) is the prerequisite that makes the CT computed-style proof real rather than measuring an unstyled span (AC-18/AC-19/AC-21). Compliant.
- **§3.6 Simplicity & reuse** — reuse the Icon atom glyphs (`x`/`plus`/`chevronDown`) and the existing tokens.css `.method` palette; no new runtime dependency. Compliant.
- **§4 Patterns — no inline style** — no inline `style={{…}}` in production source; all styling via token-bound semantic classes (AC-28); animations stay behind `prefers-reduced-motion`. The harness sets a DATA ATTRIBUTE (`document.documentElement.dataset.mstyle='soft'`) via the DOM API in test infrastructure, NOT an inline style — AC-28 greps `style={{` in Tabs.tsx/TabBar.tsx only. Compliant.
- **§4 "Shell is the sole `data-mstyle` writer" invariant — FLAGGED, not violated** — the rule "Never write Shell document.documentElement vars/attrs from anywhere but Shell.tsx" governs RENDERER PRODUCTION code (the mounted component tree). The CT harness/test is infrastructure that deliberately stands in for the un-mounted Shell — reproducing the `data-mstyle` context Shell establishes at runtime is the only way to make CT faithful to the app, and no production module is changed. Decision (g) honors the invariant by confining the substitute write to test infrastructure. Recorded so `/breakdown` does not mistake the test-side attribute write for a production violation.

## Implementation Approach

### Layer Map

| Layer | What | Files |
|-------|------|-------|
| Renderer · molecules (Tabs contract + render) | Add optional `method?: string` + `dirty?: boolean` to `TabDescriptor`; render a leading `.method` chip before the label in BOTH branches gated on `method !== undefined`; in the closable branch render dirty-dot-XOR-close; add `tabs__tab-wrapper--active` modifier to the wrapper; import the Icon atom (`x`) | src/renderer/src/components/molecules/Tabs.tsx |
| Renderer · molecules (Tabs styles) | New active `::before`(1.5px --accent)/`::after`(1px --bg mask) + `--bg` surface on `.tabbar .tabs__tab-wrapper--active`; `.tabs__tab-dirty` 7px --text-faint dot; rewrite `.tabs__tab-close` to always-visible 16px grid-centered (radius 3px, --text-faint, hover --bg-active); `.tabbar`-scoped geometry (gap 8px, padding 0 10px 0 12px, border-right 1px --border on the wrapper, label `flex:1` ellipsis); override `.tabs.tabbar { overflow: visible }` | src/renderer/src/components/molecules/Tabs.css |
| Renderer · organisms (TabBar) | `toDescriptor` adds `method: tab.spec.method` + `dirty: tab.dirty` and REMOVES `badge: tab.dirty ? '●'`; `deriveLabel` unchanged (AC-5); actions slot → `+` button (Icon `plus`) + `flex:1` spacer + static "More tabs" chevron (Icon `chevronDown`, `TODO(overflow)` marker) | src/renderer/src/components/organisms/TabBar.tsx |
| Renderer · organisms (TabBar styles) | `.tabbar` → --bg-sunken, height 36px, border-bottom 1px --border, padding-right 8px; `.tabbar__new` + chevron as grid-centered icon buttons; DELETE the `.tabbar .tabs__badge` dirty-dot block | src/renderer/src/components/organisms/TabBar.css |
| Renderer · styles (tokens + global method) | Add base `.method { font-family: var(--font-mono); … }` (AC-8 — mstyle-invariant only); add `--m-head` light+dark token (AC-1); add base `.method.HEAD` + `[data-mstyle='soft'] .method.HEAD` color rules (AC-7/AC-19) | src/renderer/styles/tokens.css |
| Renderer · organisms (Shell border de-dup) | Remove `border-bottom` from `.shell__tabs` (Shell.css:130) so the single remaining border is `.tabbar`'s — required for the active `::after` mask to read (AC-17) | src/renderer/src/components/organisms/Shell.css |
| Test harness (CT styling context — Decision (g)) | Import `tokens.css` globally into the CT mount root so every CT page resolves real token values + `.method` rules; the fidelity suite sets `data-mstyle='soft'` per-test on the document root (the prerequisite for AC-18/AC-19/AC-21 computed-style resolution) | playwright/index.tsx |
| Docs · 002 lineage | Append `### Extension: feature 005-tab-bar-visual-fidelity` under §10 (new method/dirty fields, dirty-XOR-close model, byte-identical non-closable path, global-`.method` departure, Q-3 a11y tradeoff) (AC-23) | specs/002-tabs-primitive/spec.md |
| Tests | Tabs.test (byte-identical non-closable, dirty-XOR-close, method chip, keyboard Delete closes dirty); TabBar.test (migrate AC-26 `'●'` → `.tabs__tab-dirty`/`.tabs__tab-close`, dot-click→onClose, method chip, static chevron); Tabs.ct (real-browser computed-style EXACT on geometry/typography/color + active `::before`/`::after` + thresholded screenshot diff, under per-test `data-mstyle='soft'`); Tabs.stories dirty fixture | src/renderer/src/components/molecules/__tests__/{Tabs.test.tsx,Tabs.ct.tsx,Tabs.stories.tsx}, src/renderer/src/components/organisms/__tests__/TabBar.test.tsx |

### Key Design Decisions

| Decision | Chosen Approach | Why | Alternatives Rejected |
|----------|----------------|-----|----------------------|
| (a) Active-tab accent treatment | Top `::before` 1.5px --accent + bottom `::after` 1px --bg mask over a --bg surface, placed on a new `tabs__tab-wrapper--active` modifier; neutralize the inherited box-shadow underline + --accent-soft inside `.tabbar` | DEPARTURE: replaces the codebase's established box-shadow-underline + accent-soft active treatment (Tabs.css:142) — needed because the reference (design/styles.css:710-727) connects the active tab to the pane via a top accent + bottom mask, which box-shadow can't reproduce. Scoped to `.tabbar` as CSS-isolation hygiene so the rules never leak to any other global `.tabs` consumer (AC-22). Wrapper modifier (not `:has()`) so the accent spans the full tab cell incl. the close, and stays testable. Selector `.tabbar .tabs__tab-wrapper--active` (0,2,0) beats global `.tabs__tab--active` (0,1,0) — no source-order dependence | `:has(.tabs__tab--active)` on the wrapper: avoidable Chromium-version coupling when we already edit Tabs.tsx; `::before` on the button: spans only the button, not the close cell |
| (b) `.tabs overflow:hidden` vs the `bottom:-1px` mask | Override `.tabs.tabbar { overflow: visible }` (specificity 0,2,0, leave global `.tabs{overflow:hidden}` intact); remove the duplicate Shell.css:130 border | The `::after` mask sits 1px below the tab to paint over the strip's bottom border — `overflow:hidden` would clip it. Scoping `overflow:visible` to `.tabbar` keeps the global `.tabs` clip behavior intact for any other consumer. The Shell border de-dup is LOAD-BEARING, not cosmetic: with two borders the mask covers only `.tabbar`'s, leaving Shell's visible and breaking the connect (AC-17). Q-4 runtime probe confirms no `::before`/chevron clipping at `/verify` | Global `overflow:visible` removal: changes the global `.tabs` clip behavior unnecessarily; keep-and-re-approach the mask: diverges from the enumerated reference geometry AC-11 asserts |
| (c) Method chip via GLOBAL `.method`/`.{METHOD}` classes inside the BEM Tabs primitive | `<span className={cx('method', knownMethodClass)}>` — reuse tokens.css's existing `.method` color system; narrow via a `KNOWN_METHODS` const | DEPARTURE: Tabs is BEM-only (`tabs__*`); this injects the global `.method` namespace — needed by "search before building" (§3.6): tokens.css already ships `.method.GET…OPTIONS` × 6 mstyle variants and Shell drives `data-mstyle` at app runtime; a BEM-local re-implementation would duplicate ~40 color rules and visually diverge from the sidebar/request-bar method rendering. Recorded in the 002 lineage (AC-23, §2.3). States: known-method→AC-9/AC-19 (colored), unknown-method→AC-10 (uncolored, inherits), method `undefined`→AC-2 (no chip, byte-identical) | BEM-local `tabs__tab-method--get…`: DRY violation + divergence from the app-wide method palette |
| (d) `--m-head` color value | Light `#ec4899`, dark `#f472b6` (Tailwind pink-500/400); base `.method.HEAD{color:var(--m-head)}` + `[data-mstyle='soft'] .method.HEAD{background:color-mix(…16%); color:var(--m-head)}` | Q-1 resolved. Pink is the cleanest open hue — distinct from GET sky/POST green/PUT amber/PATCH purple/DELETE red/OPTIONS slate and from the emerald accent — and stays palette-consistent (every existing token is a Tailwind-500 light / -400 dark pair). Base rule satisfies AC-7 grep + gives a colored fallback under any mstyle; soft rule matches the six siblings at the default mstyle (AC-19). Non-soft variants for HEAD are out (gold-plating; AC-19 is "at default") | Indigo `#6366f1`: sits between GET sky and PATCH purple (≤40° hue gap) — confusable; teal `#14b8a6`: collides with the emerald accent |
| (e) Screenshot-diff threshold | Playwright `toHaveScreenshot({ threshold: 0.2, maxDiffPixelRatio: 0.01, animations: 'disabled' })`, pinned device scale | Q-2 resolved. `threshold:0.2` (per-pixel YIQ, the Playwright default) absorbs sub-pixel anti-aliasing without masking a token/geometry regression; `maxDiffPixelRatio:0.01` (≤1% of pixels) bounds the total drift; `animations:'disabled'` removes transition flake. Verification rests on the EXACT computed-style assertions (AC-18) with the diff as the supplementary gate (AC-21) — not eyeballing | `threshold:0` / `maxDiffPixels:0`: anti-aliasing flake → false failures; high `maxDiffPixelRatio` (>0.05): masks real geometry drift |
| (f) Dirty-dot-XOR-close render structure | In the closable wrapper, after the `role="tab"` button render XOR: `dirty` → `<span className="tabs__tab-dirty" onClick={stopProp→onClose}>` (7px --text-faint, no role, not focusable, not in `buttonRefs`); clean → `<button type="button" tabIndex={-1} aria-label={`Close ${label}`} className="tabs__tab-close"><Icon name="x" size={11}/></button>`. Tab button keeps the sole roving stop; Delete/Backspace path unchanged | Span (not button) for the dirty marker matches the reference's non-interactive `.tab-dirty` span (Q-3) and sidesteps the "button without discernible text" axe error while staying pointer-clickable; neither marker enters `buttonRefs` or carries `tabIndex≥0`, so exactly one roving stop survives (AC-3); the existing `handleKeyDown` Delete/Backspace branch already fires `onClose` independent of which marker renders, so dirty tabs stay keyboard-closable (AC-6); the marker is a sibling of the label span, never replacing it (AC-4). States: dirty→AC-12, clean→AC-13, non-closable→AC-2 (no marker node). Q-3 no-aria-label tradeoff documented in the 002 lineage | Dirty marker as `<button tabIndex={-1}>` with no name: axe 4.1.2 failure; adding it to `buttonRefs`: breaks the single-roving-stop invariant (AC-3) |
| (g) CT fidelity-harness styling context | Import `tokens.css` GLOBALLY into the CT mount root `playwright/index.tsx` (`import '../src/renderer/styles/tokens.css'`); establish `data-mstyle='soft'` on `document.documentElement` PER-TEST, scoped to the fidelity suite in `Tabs.ct.tsx` (a fidelity-`describe` `beforeEach`/`page.evaluate`, or a `hooksConfig`-gated `beforeMount`) — NOT a global unconditional `data-mstyle` | `tokens.css` is the CT analog of `main.tsx`'s global token sheet — it belongs at the mount root so every `var(--accent/--bg/--m-head)` and the `.method` rules resolve to real values (fixes grill F-001); index.tsx self-documents as the place for "global providers." `data-mstyle` is Shell's per-render app state, not a static foundation: only the `.method` chip (Tabs alone) consumes it and only the fidelity suite asserts the soft variant, so scoping it per-test confines blast radius and keeps every other CT suite's styling context unchanged (fixes grill F-002 minimally). The harness reproduces the attribute Shell would set at runtime — in-scope for AC-18/AC-19/AC-21 | (i) `data-mstyle` set globally in index.tsx: changes the styling context for EVERY CT suite (Dropdown/Modal/Toast/…), needlessly risking their baselines for a Tabs-only need; (ii) add a bare `.method{display;min-width;padding;height}` box rule to tokens.css: WORSE — mutates the REAL app's CSS to satisfy a test; the app deliberately gates `.method` box geometry on `data-mstyle` (the base `.method{font-family}` rule is fine only because font-family is mstyle-invariant; box geometry is not); (iii) import tokens.css per-test only: a CSS import is page-global once loaded, and the token sheet is a genuine runtime foundation — the mount root is its correct home |

### Established-Convention Departures

| Departure | Established Pattern Left | Why Necessary |
|-----------|--------------------------|---------------|
| Active-tab accent via top `::before` + bottom `::after` mask on a `tabs__tab-wrapper--active` modifier, scoped to `.tabbar` | The codebase's box-shadow inset bottom-underline + `--accent-soft` wash active treatment (Tabs.css:142) | The reference (design/styles.css:710-727) connects the active tab to the pane below via a top accent bar + a bottom mask over the strip border — a box-shadow underline cannot reproduce the bottom-mask connect. Scoped to `.tabbar` so any other global `.tabs` consumer keeps the established box-shadow treatment unchanged (AC-22) |
| Global `.method`/`.{METHOD}` class used inside the BEM-only Tabs primitive | Tabs is styled exclusively with `tabs__*` BEM classes | tokens.css already ships the full `.method` color system (6 methods × 6 `data-mstyle` variants) driven by Shell's `data-mstyle`; reusing it (search-before-building, §3.6) avoids duplicating ~40 color rules and keeps the chip visually identical to the sidebar/request-bar method rendering. Recorded in the 002 lineage (AC-23) |

(Decision (g) is NOT a flagged departure — the CT harness ships empty with no established global-styling-context pattern; (g) ESTABLISHES that convention rather than leaving one. Its interaction with the §4 "Shell sole data-mstyle writer" invariant is addressed in Constitution Compliance, flagged-not-violated.)

### File Impact

| File | Action | What Changes |
|------|--------|-------------|
| src/renderer/src/components/molecules/Tabs.tsx | Modify | Add optional `method?`/`dirty?` to `TabDescriptor`; leading `.method` chip (narrowed via `KNOWN_METHODS`) before the label in both branches; dirty-dot-XOR-close in the closable branch; `tabs__tab-wrapper--active` modifier; import Icon `x`; JSDoc on the new fields (AC-24) |
| src/renderer/src/components/molecules/Tabs.css | Modify | Active `::before`/`::after`+`--bg` on `.tabbar .tabs__tab-wrapper--active`; `.tabs__tab-dirty`; rewrite `.tabs__tab-close` always-visible 16px; `.tabbar`-scoped geometry (gap 8px, padding 0 10px 0 12px, wrapper border-right, label flex:1 ellipsis); `.tabs.tabbar{overflow:visible}` |
| src/renderer/src/components/organisms/TabBar.tsx | Modify | `toDescriptor` adds `method`/`dirty`, removes `badge:'●'`; actions slot → + / spacer / static chevron with `TODO(overflow)` |
| src/renderer/src/components/organisms/TabBar.css | Modify | `.tabbar` --bg-sunken/36px/border-bottom/padding-right 8px; `.tabbar__new` + chevron icon buttons; delete `.tabbar .tabs__badge` |
| src/renderer/styles/tokens.css | Modify | base `.method{font-family:var(--font-mono)}` (mstyle-invariant only — NO box geometry); `--m-head` light+dark; `.method.HEAD` + soft-mstyle `.method.HEAD` |
| src/renderer/src/components/organisms/Shell.css | Modify | Remove `.shell__tabs` `border-bottom` (line 130) |
| **playwright/index.tsx** | **Modify (grill-revision)** | Add `import '../src/renderer/styles/tokens.css'` so the CT mount root reproduces the app's global design-token context (token values + `.method`/`[data-mstyle]` rules) for every CT page — the harness prerequisite for AC-18/AC-19/AC-21 computed-style resolution |
| specs/002-tabs-primitive/spec.md | Modify | Append `### Extension: feature 005-tab-bar-visual-fidelity` under §10 (AC-23) |
| src/renderer/src/components/molecules/__tests__/Tabs.test.tsx | Modify | byte-identical non-closable regression, dirty-XOR-close, method chip, keyboard-Delete closes dirty |
| src/renderer/src/components/molecules/__tests__/Tabs.ct.tsx | Modify | real-browser computed-style EXACT (geometry/typography/color + active ::before/::after) + thresholded screenshot diff; **PLUS (grill-revision): before the fidelity assertions, set `data-mstyle='soft'` on `document.documentElement` scoped to the fidelity suite (fidelity-`describe` `beforeEach`/`page.evaluate` or `hooksConfig`-gated `beforeMount`), and assert token-RESOLVED values — do NOT set `data-mstyle` globally in index.tsx** |
| src/renderer/src/components/molecules/__tests__/Tabs.stories.tsx | Modify | dirty fixture (dot click → onClose; dot not a tab stop; active ::before; method chip) |
| src/renderer/src/components/organisms/__tests__/TabBar.test.tsx | Modify | migrate AC-26 `'●'` assertions → `.tabs__tab-dirty`/`.tabs__tab-close`; dot-click → close; method chip; static chevron |

(12 files modified, 0 new — `playwright/index.tsx` added this revision, an addition discovered during grill, not in the spec's §4 Affected Areas because §4 scoped the fidelity work to the test files; the harness is the wiring those tests require.)

### Documentation Impact

| Doc File | Action | What Changes |
|----------|--------|-------------|
| specs/002-tabs-primitive/spec.md §10 | Update | Contract-lineage block for the 005 extension (covered as AC-23 — the canonical lineage record; counted in File Impact above) |
| docs/renderer/*/index.md (Tabs/TabBar concern) | Update (at `/finalize`) | Note the method chip + dirty-XOR-close + active-accent fidelity additions if the concern doc enumerates Tabs behavior — tech-writer surgical update, deferred to `/finalize` |

No cross-package architecture change — `docs/architecture.md` already documents the Tabs hand-rolled departure + opt-in closable extension; the 005 additive fields stay within that pattern.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Active-CSS rewrite + `overflow:visible` override regresses any global `.tabs` consumer or clips the new accent/chevron | Med | Med | Scope every new active/geometry/overflow rule to `.tabbar` (compound `.tabs.tabbar`, `.tabbar .tabs__tab-wrapper--active`); keep a closable=false byte-identical regression test (AC-2) — this test, NOT any mounted consumer, is the proof the non-closable path is unchanged; confirm via the `/verify` runtime design-auditor probe that `::before`/`::after`/chevron are not clipped (Q-4) |
| jsdom cannot resolve `::before`/`::after`; a stale CT build cache masks clean source as broken | Med | Med | Author the EXACT computed-style + pseudo-element assertions in Playwright CT (AC-18); on a build/test error naming a clean file, clear `playwright/.cache`, `node_modules/.vite`, `dist` and re-run before editing source (2026-06-24 memory lesson) |
| Dropping `badge:'●'` + deleting `.tabbar .tabs__badge` leaves the existing TabBar.test AC-26 `'●'` assertions failing | Med | Low | Migrate the AC-26 dirty-marker assertions to `.tabs__tab-dirty`/`.tabs__tab-close` + dot-click→onClose in the same change; re-assert the label text is still present (AC-4) |
| New `Icon` import in Tabs adds a molecule→atom edge; method chip could leak the global `.method` namespace into non-tabbar consumers | Low | Low | Molecule→atom is the allowed downward direction (§2.2); the chip renders only when `tab.method` is set and a non-method consumer passes none, so byte-identity holds (AC-2); record the global-`.method` departure in the 002 lineage |
| Importing `tokens.css` globally into `playwright/index.tsx` shifts the styling context of existing CT suites (Dropdown/Modal/Toast) — currently rendering in CT against `var()` defensive fallbacks, not real tokens — perturbing layout-sensitive assertions or any screenshot baseline | Med | Low | Existing CT assertions read component-local `animation-name` + boundingBox with ±1px tolerance (token-robust); after the import, run the full CT suite and regenerate/verify any affected baseline as a one-time isolated step BEFORE adding the Tabs fidelity assertions — do not co-mingle baseline regen with source edits |
| First-run CT fidelity baselines (computed-style + screenshot) are authored against the new harness, so there is no prior baseline to diff — a wrong harness setup could bake an off-palette baseline | Med | Med | Author the EXACT computed-style assertions (AC-18) as the primary gate (they fail loudly on unresolved tokens — a `var()`-unresolved color is not the target literal); treat `toHaveScreenshot` as the supplementary gate only (decision (e)); manually confirm the first screenshot baseline renders the soft-mstyle palette before committing it |

## Dependencies

None — no packages to install, no services to configure, no environment variables. All assets are in-stack: the Icon atom glyphs (`x`/`plus`/`chevronDown`, atoms/icons.ts), the tokens.css `.method` palette, and Playwright CT (`snapshotDir: ./__snapshots__` already configured; the mount root `playwright/index.tsx` is modified, not added).

## Supporting Documents

- Research: none — no deep-research signals (approach settled upstream; all libraries in-stack; see Summary "Why no new research").
- Data Model: none — no new or changed data entities (`tabsStore`/`RequestSpec` untouched).
- Contracts: none — no API surface; pure renderer UI.
- Grill: specs/005-tab-bar-visual-fidelity/grill.md (REVISE-PLAN — drove this revision: Decision (g) + the two grounding corrections).
- Upstream: research/2026-06-25-bring-tab-bar-to/handoff.json (settled the approach + rejected alternative).
