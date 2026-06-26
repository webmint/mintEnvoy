# Research: Bring tab bar to full visual fidelity with design/reference.html (feature 005-tab-bar-visual-fidelity)


**Date**: 2026-06-25
**Topic**: Bring tab bar to full visual fidelity with design/reference.html (feature 005-tab-bar-visual-fidelity)
**Mode**: Enhancement
**Verdict**: Feasible with caveats

## Summary

Feature 004 shipped the tab strip 'look-only' with zero visual-fidelity ACs, so 8 reference items in design/reference.html drifted. Investigation (CBM + source) confirms all 8 sites and the note's reuse assets: Icon atom (x/plus/chevronDown in atoms/icons.ts) and tokens.css .method.{METHOD} classes are present. Full fidelity is feasible via an additive opt-in TabDescriptor extension (optional method?/dirty?) keeping the non-closable path byte-identical, plus chip/SVG/active-CSS/border-dedup changes. One non-obvious risk surfaced: the method chip's color rules are gated entirely on a runtime [data-mstyle] attribute and set no font-family/no HEAD token — but Shell.tsx:237 already writes data-mstyle (default 'soft'), so runtime color resolves; the residual gaps are HEAD color, mono font, and Shell-less test/story fixtures, all closeable in tokens.css (Task C) plus a fixture guard. Remaining uncertainty: active ::before/::after rewrite + overflow:hidden removal must be proven non-regressing on other Tabs consumers via the live design-auditor probe.

## Symptom

| Dimension | Value |
|---|---|
| Symptom | Tab bar UI does not match design/reference.html across 8 structural/visual points (method chip, active-tab accent, dirty-XOR-close, tabbar geometry/separators, SVG close icon, +/spacer/chevron actions, tab padding/gap, double bottom border). Feature 004 shipped 'look only' with zero visual-fidelity ACs; close all drift as new feature 005. |
| Affected area | 002 Tabs primitive (src/renderer/src/components/molecules/Tabs.tsx + Tabs.css) + global tokens.css + Shell.css. Authoritative consumer set = inbound-call trace on the primitive. Only BUILT PRODUCT consumer = app-shell TabBar (src/renderer/src/components/organisms/TabBar.tsx + TabBar.css). PrimitivesDemo/TabsSection (src/renderer/src/components/PrimitivesDemo.tsx) is a dev-only gallery, NOT a feature consumer — its sole relevance is as the surface proving the opt-in contract stays backward-compatible (default-off non-closable path byte-identical, test-proven). Designed-but-unbuilt section-tab request/response consumers = forward-compat duty under the default-off contract, not a present regression surface. |
| Repro / Current | Visual current-state per the note's table. Behavior: (a) dirty mechanics = locked 004 lifecycle (flips on RequestSpec mutation; new tab dirty=false; markClean exposed-not-triggered) — feature 005 changes the dirty INDICATOR only, not the lifecycle. (b) Keyboard from 002 = roving-tabindex single-stop + Arrow select; close is pointer-only via opacity:0 hover-reveal ✕; no Delete/Backspace close path exists yet. (c) Hover-reveal close is likely keyboard-unreachable today — pre-existing close a11y gap; the new Delete path is an improvement, not a regression, provided the new closable model passes axe. |
| Desired | Target = reference's 8-item spec with TIERED fidelity (not flat pixel-perfect): (1) Verification = computed-style EXACT equality on enumerated props (font-size, padding, gap, border, color-tokens) PLUS screenshot diff with explicit anti-aliasing pixel-threshold; 'verified' = computed-style assertions pass, not eyeballed. (2) Semantic/interaction items EXACT + non-negotiable: active ::before/::after, dirty-dot-XOR-close, method chip. (3) 'More tabs' chevron = VISUAL fidelity only; overflow behavior OUT — no working overflow required to pass. (4) HEAD method color is closed: add --m-head/.method.HEAD token (colored HEAD); uncolored HEAD NOT accepted. (5) Geometry items exact-by-computed-style. Hard constraint: opt-in contract stays backward-compatible — non-closable render path byte-identical, proven by test. |
| Scope | feature-wide |

## Codebase Findings (WHERE)

| Surface | File:line | Relevance | Framing |
|---|---|---|---|
| Tabs primitive closable render branch (always-in-DOM unicode ✕ + badge span) | src/renderer/src/components/molecules/Tabs.tsx:333 | Current close = unicode ✕ button (tabs__tab-close), badge rendered when defined; target swaps to 16px SVG x and dirty-dot-XOR-close. Label span untouched (AC-26). | primary |
| TabBar toDescriptor maps dirty→badge '●', no method/dirty fields | src/renderer/src/components/organisms/TabBar.tsx:73 | toDescriptor sets badge: tab.dirty?'●':undefined; needs method+dirty fields, remove badge mapping. deriveLabel unchanged (AC-25). | primary |
| TabDescriptor interface — id/label/badge?/disabled? only | src/renderer/src/components/molecules/Tabs.tsx:116 | Contract change site: add optional method?/dirty? (backward-compatible, keep badge). | primary |
| Tabs.css active-state block (box-shadow underline + accent-soft) | src/renderer/src/components/molecules/Tabs.css:142 | Current active = inset box-shadow underline + --accent-soft wash; target = top ::before accent + bottom ::after mask + --bg bg. | primary |
| Tabs.css tab geometry (gap 6px, symmetric 12px padding, 32px) | src/renderer/src/components/molecules/Tabs.css:83 | Target geometry: padding 0 10px 0 12px, gap 8px, label flex:1 ellipsis, 36px in tabbar context. | primary |
| Tabs.css close button opacity:0 hover-reveal, width 20px unicode | src/renderer/src/components/molecules/Tabs.css:295 | Target: always-visible 16px grid-centered SVG x; rewrite .tabs__tab-close, add .tabs__tab-dirty 7px --text-faint circle. | primary |
| Tabs.css .tabs border-bottom + overflow:hidden (double-border + clip risk) | src/renderer/src/components/molecules/Tabs.css:38 | Keep .tabs border for section-tab consumers; overflow:hidden (:40) may clip new ::before accent/chevron — verify/remove. | primary |
| Shell.css .shell__tabs duplicate border-bottom | src/renderer/src/components/organisms/Shell.css:130 | Double bottom border source #2; de-dup here (remove), keep .tabs border. | primary |
| tokens.css .method rules gated on [data-mstyle], no font-family, no HEAD variant | src/renderer/styles/tokens.css:108 | RUNNER-UP: chip color requires [data-mstyle='chip'\|'soft'] ancestor; neither mode sets font-family (mono gap); only GET/POST/PUT/PATCH/DELETE/OPTIONS — HEAD has no color token. Task C must add base .method{font-family} + --m-head/.method.HEAD. | runner-up |
| Shell.tsx writes documentElement.dataset.mstyle (refutes data-mstyle-missing) | src/renderer/src/components/organisms/Shell.tsx:237 | RUNNER-UP REFUTED for runtime: Shell sets data-mstyle (default 'soft' from settingsStore) on <html>, so .method colors DO resolve in the running app. Residual risk: Shell-less test/story fixtures lack this writer → uncolored chips unless fixture sets the attr. | runner-up |
| tokens.css comment: default-no-attribute should match soft, but no base .method rule | src/renderer/styles/tokens.css:105 | RUNNER-UP: documented intent ('Default (no attribute) should match soft') not implemented — no unprefixed .method rule; only bites Shell-less isolated rendering (Task D fixtures). | runner-up |
| Icon atom canonical usage (reuse SVG icons, not unicode/new SVG) | src/renderer/src/components/PrimitivesDemo.tsx:45 | canonical pattern — reusable: <Icon name=... size=.../> is the project SVG-render idiom; reuse for x/plus/chevronDown instead of unicode ✕ or hand-rolled SVG. | primary |
| ICONS atom set has x/plus/chevronDown | src/renderer/src/components/atoms/icons.ts:14 | canonical pattern — reusable: x/plus/chevronDown SVG paths already present; no new icon dependency needed (unchanged-behavior #11). | primary |

## Root Cause Hypothesis (WHY)

**Primary hypothesis**: Feature 004 shipped tab UI as 'look-only' with zero visual-fidelity ACs, so 8 reference items drifted. Full fidelity is achievable via an additive opt-in TabDescriptor extension (method?/dirty?) plus chip/SVG/active-CSS/border-dedup changes, with method-chip color/font requiring three tokens.css additions (base .method font-mono, --m-head, .method.HEAD) since the existing .method rules are [data-mstyle]-gated, set no font-family, and lack HEAD.

**Confidence**: Hypothesis

## Runner-up framing

| Field | Value |
|---|---|
| Frame | Method-chip fidelity is not a pure markup-add: chip color/font/HEAD are gated on tokens.css [data-mstyle] rules + the runtime data-mstyle attribute, so closing item #1 needs tokens work + a Shell-attribute dependency, not just a <span> in Tabs/TabBar; isolated test/story fixtures lack the Shell writer entirely. |
| Falsifier | No writer of document.documentElement.dataset.mstyle exists, so .method color rules stay dormant and chips render uncolored even in the running app. |
| Confidence vs primary | comparable |

## Hypothesis Enumeration

| Hypothesis | Falsifier (what would disprove it) | Runtime probe needed? |
|---|---|---|
| Full fidelity achievable by additive opt-in contract: extend TabDescriptor with optional method?/dirty?, add chip+SVG+active-CSS, de-dup border — non-closable path stays byte-identical, all 8 items close in Tabs/TabBar/tokens/Shell. | A reference item cannot be reproduced without breaking the byte-identical non-closable path or the roving single-stop model (e.g. dirty-dot must be focusable). | no |
| Method-chip color/font fidelity requires tokens.css work beyond markup (base .method{font-family:mono} + --m-head/.method.HEAD), because chip rules are gated on [data-mstyle] and set no font-family / no HEAD; runtime is fine (Shell sets data-mstyle) but isolated fixtures and HEAD tabs miss color/font without the token additions. | Adding only the <span class='method'> markup (no tokens.css change) already renders chips at full reference fidelity incl. mono font + colored HEAD in the running app. | yes |
| Active-state ::before/::after rewrite + overflow:hidden removal regresses other Tabs consumers (PrimitivesDemo gallery, future section-tabs) or clips the accent/chevron. | Active styles are scoped to .tabbar (not bare .tabs__tab) and removing overflow:hidden introduces no clipping in any consumer. | yes |

## Recommended Verify Step

| Sub-field | Value |
|---|---|
| probe | npm run dev; design-auditor via Chrome DevTools MCP — computed-style assertions on .method (font-family, background, color per method incl. HEAD), .tabs__tab (padding 0 10px 0 12px, gap 8px), .tabbar (36px, --bg-sunken, border-bottom), active ::before/::after; screenshot diff vs design/reference.html with AA pixel-threshold. |
| reproduction | Open the app shell with >=2 tabs incl. a dirty tab and a HEAD-method tab; observe the running tab strip. |
| discriminator | If computed .method background/color is empty on a chip → tokens/data-mstyle gap confirmed (H-B); if HEAD chip uncolored while others colored → HEAD-token gap; if active ::before/::after or chevron clipped → overflow:hidden regression (H-C); all assertions pass → H-A confirmed. |

## Approaches (HOW to change)

### Additive opt-in + tokens completion (note's 4-task plan, gaps closed)
- **Description**: Extend TabDescriptor with optional method?/dirty? (backward-compatible, keep badge); add method chip + 16px SVG close (reuse Icon atom) + dirty-XOR-close + active ::before/::after + tabbar 36px/--bg-sunken/separators + +/spacer/static chevron; de-dup the Shell.css border. Close the runner-up's token gaps in Task C: add base .method{font-family:var(--font-mono)} + --m-head + .method.HEAD, and set data-mstyle on Shell-less Task-D story/CT fixtures so chip color renders there.
- **Addresses hypothesis**: A, B
- **Does NOT cover**: C
- **Pros**: Reference-faithful on all 8 incl. colored HEAD + mono chip; Non-closable path byte-identical (AC-11) — proven by test; Reuses Icon atom + existing .method classes (no new deps); Closes the data-mstyle/HEAD/font gaps the static audit missed
- **Cons**: Largest diff (4 tasks across 6 files); Active ::before/::after + overflow removal needs runtime regression proof (H-C); Contract change touches shared 002 primitive — lineage note required
- **Complexity**: Med

### Markup-first, defer token gaps
- **Description**: Add chip span + SVG close + active-CSS + border-dedup now; rely on Shell's existing data-mstyle='soft' for chip color and DEFER the base .method{font-mono} rule, --m-head and .method.HEAD token to a follow-up.
- **Addresses hypothesis**: A
- **Does NOT cover**: B, C
- **Pros**: Smaller, faster diff; Chip colors still render in the running app (Shell writes data-mstyle)
- **Cons**: Fails desired tier-4: HEAD stays uncolored (explicitly NOT accepted); Chip font is ambient, not mono — fails computed-style fidelity; Shell-less story/CT fixtures show uncolored chips — misleading visual baseline
- **Complexity**: Low

**Recommended approach**: Additive opt-in + tokens completion (note's 4-task plan, gaps closed) — Recommended as the only candidate that completely meets the tiered acceptance bar the user defined; the cheaper alternative deliberately leaves required visuals unmet and is non-compliant by construction. It preserves every stated guarantee and REUSES the project's canonical Icon-atom idiom (glyph definitions already present in atoms/icons.ts:14) instead of reinventing it, honoring the search-first reuse rule. Residual unknowns are tracked as open questions Q1 and Q2 and settled by the live design-auditor pass rather than asserted here.

## Constitution Constraints

| Rule | Impact on this change |
|---|---|
| Search before building | Reuse the Icon atom (atoms/icons.ts:14 has x/plus/chevronDown; canonical usage PrimitivesDemo.tsx:45) and the existing tokens.css .method.{METHOD} classes — no new icon/style dependency; reuse beats reinvention. |
| Minimal changes / backward-compatible contract | TabDescriptor gains only OPTIONAL method?/dirty?; non-closable render path must stay byte-identical (test-proven on TabBar + PrimitivesDemo gallery). |
| Accessibility — roving single-stop (002 AC-12) | Dirty dot = non-focusable span, ✕ tabIndex=-1, +/chevron outside role=tablist; exactly one tab stop per tab; axe stays clean. |
| Design Fidelity principle | Verification = computed-style exact equality on enumerated props + screenshot diff (AA threshold) via live design-auditor; 'verified' is asserted, not eyeballed. |

## Complexity Assessment

| Dimension | Rating | Notes |
|---|---|---|
| Codebase changes | Med | 6 files: Tabs.tsx/Tabs.css, TabBar.tsx/TabBar.css, tokens.css, Shell.css + tests/stories; 4 ordered tasks (A→B, C/D alongside). |
| Risk | Med | Shared 002 contract change; active-CSS rewrite + overflow:hidden removal could regress other Tabs consumers / clip accent; mitigated by .tabbar-scoping + byte-identical-path test + runtime probe. |
| Verify cost | Med | Runtime design-auditor via Chrome DevTools MCP (computed-style + screenshot diff) + touched unit/CT suites; app must be running (npm run dev). |

## Open Uncertainties

- [NEEDS CLARIFICATION: desired — Q1: confirm the selected-tab indicator rewrite (::before/::after) + overflow:hidden removal do not regress or clip other Tabs consumers — prove via runtime design-auditor before/after.]
- [NEEDS CLARIFICATION: desired — Q2: confirm method-chip renders at full reference fidelity (mono font + per-method color incl. HEAD) in the running app and in Shell-less story/CT fixtures, after the tokens.css additions.]

## Next step

Copy the block below into a new `/specify` session manually. No automation — user controls when (or if) `/specify` runs.

~~~
/specify "Tab bar UI does not match design/reference.html across 8 structural/visual points (method chip, active-tab accent, dirty-XOR-close, tabbar geometry/separators, SVG close icon, +/spacer/chevron actions, tab padding/gap, double bottom border). Feature 004 shipped 'look only' with zero visual-fidelity ACs; close all drift as new feature 005. — Target = reference's 8-item spec with TIERED fidelity (not flat pixel-perfect): (1) Verification = computed-style EXACT equality on enumerated props (font-size, padding, gap, border, color-tokens) PLUS screenshot diff with explicit anti-aliasing pixel-threshold; 'verified' = computed-style assertions pass, not eyeballed. (2) Semantic/interaction items EXACT + non-negotiable: active ::before/::after, dirty-dot-XOR-close, method chip. (3) 'More tabs' chevron = VISUAL fidelity only; overflow behavior OUT — no working overflow required to pass. (4) HEAD method color is closed: add --m-head/.method.HEAD token (colored HEAD); uncolored HEAD NOT accepted. (5) Geometry items exact-by-computed-style. Hard constraint: opt-in contract stays backward-compatible — non-closable render path byte-identical, proven by test."

Research reference: research/2026-06-25-bring-tab-bar-to.md
Key facts:
- Mode: Enhancement
- Symptom: Tab bar UI does not match design/reference.html across 8 structural/visual points (method chip, active-tab accent, dirty-XOR-close, tabbar geometry/separators, SVG close icon, +/spacer/chevron actions, tab padding/gap, double bottom border). Feature 004 shipped 'look only' with zero visual-fidelity ACs; close all drift as new feature 005.
- Desired: Target = reference's 8-item spec with TIERED fidelity (not flat pixel-perfect): (1) Verification = computed-style EXACT equality on enumerated props (font-size, padding, gap, border, color-tokens) PLUS screenshot diff with explicit anti-aliasing pixel-threshold; 'verified' = computed-style assertions pass, not eyeballed. (2) Semantic/interaction items EXACT + non-negotiable: active ::before/::after, dirty-dot-XOR-close, method chip. (3) 'More tabs' chevron = VISUAL fidelity only; overflow behavior OUT — no working overflow required to pass. (4) HEAD method color is closed: add --m-head/.method.HEAD token (colored HEAD); uncolored HEAD NOT accepted. (5) Geometry items exact-by-computed-style. Hard constraint: opt-in contract stays backward-compatible — non-closable render path byte-identical, proven by test.
- Recommended approach: Additive opt-in + tokens completion (note's 4-task plan, gaps closed)
- Hypothesis addressed: A, B
- Hypotheses NOT covered: C
- Open uncertainties: 0 (see research doc §Open Uncertainties)
~~~
