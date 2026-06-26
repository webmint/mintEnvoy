# Spec: tab-bar-visual-fidelity

**Date**: 2026-06-25
**Status**: Complete
**Design source**: html:design/reference.html
**Author**: Claude + User

## 1. Overview

Close the visual-fidelity gap between the working-tabs TabBar (feature 004) and design/reference.html across the reference's 8 structural/visual points — method chip, active-tab accent (top ::before + bottom ::after mask), dirty-dot-XOR-close, tabbar geometry + per-tab separators, 16px SVG close icon, +/spacer/'More tabs'-chevron actions row, tab padding/gap, and single bottom border. Feature 004 shipped 'look only' with zero visual-fidelity acceptance criteria; 005 adds those criteria with TIERED fidelity (computed-style EXACT equality on enumerated props plus a thresholded screenshot diff — not eyeballed), extends the 002 Tabs primitive additively (optional method/dirty descriptor fields) under a backward-compatible byte-identical guarantee, and completes the method-token set (colored HEAD via a new --m-head/.method.HEAD).

## 2. Current State

Feature 004 wired the working-tabs strip but declared design/reference.html 'look only' with no fidelity ACs, so the rendered TabBar drifts from the reference on 8 points. Current implementation: TabBar.toDescriptor (src/renderer/src/components/organisms/TabBar.tsx:73-79) maps each store Tab to a TabDescriptor with label only and badge: tab.dirty ? '●' : undefined — no method is passed. The Tabs primitive (src/renderer/src/components/molecules/Tabs.tsx) renders, in its closable=true branch, an always-mounted sibling close button using the unicode glyph '✕' (Tabs.tsx:577-590, opacity hover-reveal in CSS) and TabDescriptor = { id; label; badge?: string|number; disabled? } (Tabs.tsx:116-138) with no method/dirty fields. Tabs.css: active state is a box-shadow inset bottom underline in --accent plus an --accent-soft wash (no top ::before accent, no bottom ::after mask); .tabs__tab uses padding 0 0.75rem and gap 0.375rem (6px); .tabs has border-bottom 1px (Tabs.css:38) AND overflow:hidden (Tabs.css:40); .tabbar (TabBar.css) only sets background --bg. The strip also carries a SECOND bottom border on .shell__tabs (Shell.css:130) → a double border. tokens.css already defines .method + per-[data-mstyle] variants and --m-get/post/put/patch/delete/options (light + dark) but NO --m-head and no base .method{font-family:var(--font-mono)} rule. Reuse assets confirmed present: the Icon atom exposes x, plus, and chevronDown glyphs (src/renderer/src/components/atoms/icons.ts:19/25/28); the reference's exact target values live in design/styles.css (.tabbar 680-687, .tab 689-727, .tab-label/.tab-dirty/.tab-close 729-756, .tab-new 758-767, .method base 490-499). Shell sets data-mstyle on <html> (default 'soft'), recoloring .method at runtime.

## 3. Desired Behavior

The working-tabs TabBar shall match design/reference.html on the 8 enumerated points, verified by tier. (A) Method chip: each tab renders a leading .method chip carrying the tab's HTTP method (from tab.spec.method via a new optional TabDescriptor.method), colored per method using the global .method/.{METHOD} classes (a documented departure from 002's BEM-only convention); a method outside the colored set renders an uncolored chip that inherits text color; HEAD shall be colored via a new --m-head token + .method.HEAD class (uncolored HEAD is not accepted). (B) Active tab: a top accent bar via ::before (height 1.5px, --accent, left/right 0, top 0) plus a bottom mask via ::after (height 1px, --bg, bottom -1px) over an --bg background, replacing the current box-shadow underline + --accent-soft wash. (C) Dirty-dot-XOR-close: a dirty tab renders a 7px --text-faint dot in place of (mutually exclusive with) the close button, and the dot is itself clickable-to-close; a clean tab renders the always-visible close control; the dirty marker never replaces the LABEL (004 AC-26 preserved). (D) Tabbar geometry: .tabbar uses --bg-sunken, height 36px, border-bottom 1px --border, padding-right 8px, with a per-tab border-right 1px --border separator. (E) Close control: a 16px×16px grid-centered SVG x (Icon, size 11) at color --text-faint, always visible (not opacity-hover-revealed), border-radius 3px, hover bg --bg-active. (F) Actions row: a + new-tab button (Icon plus), a flex:1 spacer, and a static 'More tabs' chevron button (Icon chevronDown) — the chevron is a VISUAL affordance only; no working overflow behavior is in scope. (G) Tab geometry: padding 0 10px 0 12px, gap 8px, label flex:1 with ellipsis. (H) Single bottom border: remove the duplicate border-bottom from .shell__tabs (Shell.css:130), keep one. The new active/geometry CSS shall be scoped to .tabbar so the request-pane section-tabs Tabs consumer is not regressed. The non-closable Tabs render path shall remain byte-identical to the 002 contract, proven by a regression test (002 AC-11). Verification is tiered: geometry/typography/color props are asserted by computed-style EXACT equality in a real browser (Playwright CT, which resolves ::before/::after), backed by a thresholded screenshot diff with an explicit anti-aliasing pixel-threshold; the semantic/interaction items (active ::before/::after, dirty-XOR-close, method chip) are EXACT and non-negotiable; a runtime design-auditor pass (Chrome DevTools MCP) is the supplementary /verify confirmation. All changes are renderer-only, styled via tokens-bound semantic classes (no inline styles), animations gated behind prefers-reduced-motion.

## 4. Affected Areas

| Area | Files | Impact |
|------|-------|--------|
| Tabs primitive (contract + render) | src/renderer/src/components/molecules/Tabs.tsx | Modify — add optional method?:string + dirty?:boolean to TabDescriptor (additive, backward-compatible); render a leading .method chip before the label when method is set; in the closable branch render dirty-dot-XOR-close (dirty → clickable 7px dot replacing the close button; clean → always-visible SVG x via Icon); keep non-closable path byte-identical (002 AC-11); keep hand-rolled roving a11y intact |
| Tabs primitive styles | src/renderer/src/components/molecules/Tabs.css | Modify — replace box-shadow active underline with top ::before accent (1.5px --accent) + bottom ::after mask (1px --bg) over --bg bg; add .tabs__tab-dirty (7px --text-faint circle); rewrite .tabs__tab-close to always-visible 16px grid-centered (border-radius 3px, --text-faint, hover --bg-active); geometry gap 8px, padding 0 10px 0 12px, label flex:1 ellipsis; new active/geometry rules scoped under .tabbar; remove/guard overflow:hidden only if it clips ::before/chevron |
| TabBar organism | src/renderer/src/components/organisms/TabBar.tsx | Modify — toDescriptor adds method: tab.spec.method + dirty: tab.dirty and REMOVES badge: tab.dirty ? '●'; deriveLabel unchanged (004 AC-25); actions slot becomes + new-tab button (Icon plus) + flex:1 spacer + static 'More tabs' chevron button (Icon chevronDown) with a TODO(overflow) marker |
| TabBar styles | src/renderer/src/components/organisms/TabBar.css | Modify — .tabbar gets --bg-sunken, height 36px, border-bottom 1px --border, padding-right 8px; per-tab .tabbar .tabs__tab border-right 1px --border; .tabbar__new + .tabbar chevron as grid-centered icon buttons; delete the .tabbar .tabs__badge dirty block |
| Design tokens + global method CSS | src/renderer/styles/tokens.css | Modify — add base .method { font-family: var(--font-mono); ... }; add --m-head token (light + dark) and a .method.HEAD color rule (colored HEAD); confirm --font-mono present |
| Shell tabs-slot border de-dup | src/renderer/src/components/organisms/Shell.css | Modify — remove the duplicate border-bottom from .shell__tabs (Shell.css:130) so the strip shows a single bottom border (the .tabbar border-bottom owns it) |
| 002 Tabs contract lineage | specs/002-tabs-primitive/spec.md | Modify — append a '### Extension: feature 005-tab-bar-visual-fidelity' block under §10 documenting the new method/dirty descriptor fields, dirty-XOR-close render model, AC-26-preserved note, byte-identical non-closable path, and the global-.method-class departure (the AC-29 lineage pattern) |
| Fidelity + behavior tests | src/renderer/src/components/molecules/__tests__/Tabs.test.tsx, src/renderer/src/components/molecules/__tests__/Tabs.ct.tsx, src/renderer/src/components/molecules/__tests__/Tabs.stories.tsx, src/renderer/src/components/organisms/__tests__/TabBar.test.tsx | Create/extend — Tabs.test: byte-identical non-closable regression, dirty-XOR-close, method chip, keyboard-Delete still closes a dirty tab; TabBar.test: migrate the AC-26 '●' badge assertions to .tabs__tab-dirty/.tabs__tab-close, dirty-dot-click → close, method chip, static chevron; Tabs.ct: real-browser computed-style EXACT assertions on .tabbar geometry/typography/colors + active ::before/::after + thresholded screenshot diff (anti-aliasing pixel-threshold); add a dirty fixture (dot click → onClose, dot not a tab stop) |

## 5. Acceptance Criteria

Each AC must be testable and unambiguous. **Cover each category that applies. Mark non-applicable categories with "N/A — [reason]".**

### 5.1 Tooling / artifact presence and absence

- [x] **AC-1**: The tokens stylesheet shall define a --m-head custom property so the HEAD method has a dedicated color token.
  > Verification: grep -qE '\-\-m-head\s*:' src/renderer/styles/tokens.css
- [x] **AC-7**: The tokens stylesheet shall define a HEAD-method color rule so a HEAD chip renders colored rather than uncolored.
  > Verification: grep -qE '\.method\.HEAD' src/renderer/styles/tokens.css
- [x] **AC-8**: The tokens stylesheet shall define a base method rule that binds the chip font to the monospace token.
  > Verification: grep -qE '^\.method[[:space:]]*\{' src/renderer/styles/tokens.css

### 5.2 Behavior preservation

- [x] **AC-2**: WHILE the Tabs primitive is rendered without the closable option, the primitive shall remain byte-identical to its 002 selection-only contract — no method chip, no dirty or close DOM node, and no extra roving tab stop.
- [x] **AC-3**: The Tabs primitive shall maintain exactly one roving tab stop per tab regardless of the closable option or the new method and dirty descriptor fields.
- [x] **AC-4**: WHILE a tab is dirty, the TabBar shall leave the tab's derived label text unchanged, replacing only the close control with the dirty dot and never the label (feature 004 AC-26 preserved).
- [x] **AC-5**: WHEN the TabBar derives a tab label, the TabBar shall apply the unchanged feature 004 AC-25 precedence of name then method-plus-url then the literal Untitled, rendered verbatim.
- [x] **AC-6**: WHILE a tab is dirty, the Tabs primitive shall keep the dirty dot a non-focusable element and shall keep Delete or Backspace closing the focused tab so a dirty tab stays keyboard-closable.

### 5.3 Behavior change

- [x] **AC-9**: WHERE a tab descriptor carries a method, the Tabs primitive shall render a leading method chip before the tab label, colored per the method via the global method classes.
- [x] **AC-10**: IF a tab's method is outside the colored method set, THEN the Tabs primitive shall render the chip uncolored so it inherits the tab text color.
- [x] **AC-11**: WHILE a tab is active, the Tabs primitive shall render a top accent bar in the accent color via a ::before pseudo-element and a bottom mask in the surface color via a ::after pseudo-element over a surface-colored background.
- [x] **AC-12**: WHILE a closable tab is dirty, the Tabs primitive shall render a faint dirty dot in place of the close control and shall emit onClose when the dot is clicked.
- [x] **AC-13**: WHILE a closable tab is clean, the Tabs primitive shall render an always-visible grid-centered SVG close control sized 16px square rather than an opacity-hover-revealed glyph.
- [x] **AC-14**: WHILE the TabBar is rendered, the tabbar element shall have a computed sunken background, a height of 36px, a 1px bottom border in the border color, and a right padding of 8px.
- [x] **AC-15**: WHILE a tab is rendered in the TabBar, each tab shall have a computed gap of 8px, a padding of 0 10px 0 12px, a 1px right-border separator in the border color, and a font size equal to the --fs-base token.
- [x] **AC-16**: WHILE a tab label overflows its width, the label shall be a flex-filling element truncated with an ellipsis.
- [x] **AC-17**: WHILE the shell renders the tabs strip, exactly one bottom border shall be present after the duplicate shell-tabs border is removed.
- [x] **AC-18**: WHEN the fidelity suite runs, the enumerated computed-style properties of font size, padding, gap, border, color tokens, and active pseudo-element geometry shall be asserted by exact equality in a real browser via Playwright component tests.
- [x] **AC-19**: WHILE the method style is at its default, the Tabs primitive shall render a HEAD-method chip colored via the --m-head token rather than uncolored.
- [x] **AC-20**: WHEN the TabBar renders its actions slot, the TabBar shall render a plus new-tab button, a flex-filling spacer, and a static More-tabs chevron button.
- [x] **AC-21**: WHEN the fidelity suite runs, the fidelity suite shall pass the screenshot diff against the design reference only within an explicit anti-aliasing pixel-threshold, resting verification on the computed-style assertions and the thresholded diff rather than on visual eyeballing.
- [x] **AC-22**: WHILE the new active and geometry styles are applied, the Tabs styling shall scope them to the tabbar so the request-pane section-tabs consumer of the Tabs primitive renders unchanged.

### 5.4 CI / pipeline

N/A — No CI pipeline changes in scope; tests run via the existing npm scripts (vitest/playwright), not a new pipeline stage.

### 5.5 Hooks / gates

N/A — No new git hooks or commit gates introduced; the project's existing forge gates apply unchanged.

### 5.6 Documentation

- [x] **AC-23**: The feature 002 Tabs spec lineage shall record the 005 contract extension covering the new method and dirty descriptor fields, the dirty-XOR-close render model, the byte-identical non-closable path, and the global method-class departure, rather than a silent prop addition.
- [x] **AC-24**: The new TabDescriptor method and dirty fields and the dirty-XOR-close behavior shall carry documentation comments on the exported symbols.

### 5.7 Hygiene

- [x] **AC-25**: The renderer source shall pass strict type-checking.
  > Verification: npm run typecheck:web
- [x] **AC-26**: The codebase shall pass ESLint without new errors.
  > Verification: npm run lint
- [x] **AC-27**: The project shall build cleanly.
  > Verification: npm run build
- [x] **AC-28**: The touched renderer source shall contain no inline style attributes outside comments.
  > Verification: ! grep -REn 'style=[{][{]' src/renderer/src/components/molecules/Tabs.tsx src/renderer/src/components/organisms/TabBar.tsx | grep -vqE ':[[:space:]]*(\*|//|/[*])'
- [x] **AC-29**: The touched renderer modules shall not import the electron or node built-in modules directly.
  > Verification: ! grep -REn "from '(electron|node:)" src/renderer/src/components/molecules/Tabs.tsx src/renderer/src/components/organisms/TabBar.tsx

## 6. Out of Scope

**Coverage rule (v3)**: For each Phase 1.5 finding, the finding either (a) becomes an AC in §5, (b) becomes a Constraint in §7, (c) is explicitly listed here as out of scope, OR (d) is in §9 Risks with documented mitigation. Unlanded finding = hard error — re-verify Phase 1.5 enumeration is complete before saving.

- NOT included: Functional tab overflow — the 'More tabs' chevron is a static visual affordance only; real overflow behavior (tab measurement, hidden-tab dropdown, scroll-into-view, keyboard) is a separate follow-on feature and is not required to pass.
- NOT included: Reproducing design/reference.html markup or its generated cruft (data-om-*, __OmT wrappers, inline styles, tweaks panel) — fidelity is matched via tokens-bound semantic classes, not by copying the reference DOM.
- NOT included: Changing the tab label derivation — deriveLabel and the 004 AC-25 precedence (name then method-plus-url then Untitled) stay byte-for-byte unchanged; the method chip is additive and the label keeps the method on unnamed-URL tabs (reference-faithful).
- NOT included: tabsStore lifecycle behavior (open, dedupe, close never-zero, dirty, markClean) — 005 touches only the TabBar/Tabs presentation and the descriptor mapping, not the store state machine.
- NOT included: Visual changes to the request-pane section-tabs Tabs consumer — the new active/geometry CSS is scoped to the working-tabs .tabbar so the other Tabs consumer renders unchanged.
- NOT included: Separate dark-theme fidelity work — dark rendering is driven by the existing light/dark token pairs (including the new --m-head pair); no theme-specific layout or geometry work is in scope.
- NOT included: Repo-wide reformatting or unrelated housekeeping commits on this feature branch — they pollute the /verify hygiene scope vs the breakdown baseline (memory lesson from features 001/002).

## 7. Technical Constraints

- Must follow: Search before building
- Must follow: Minimal changes / backward-compatible contract
- Must follow: Accessibility — roving single-stop (002 AC-12)
- Must follow: Design Fidelity principle
- Must follow: Scope the new active (::before/::after) and geometry CSS to the working-tabs .tabbar so the request-pane section-tabs Tabs consumer is not regressed; reuse the existing .tabbar-scoping precedent in TabBar.css.
- Must follow: Style exclusively via tokens-bound semantic class names (no inline styles); gate any animation behind prefers-reduced-motion; never reproduce the design reference markup.
- Must follow: Search before building: reuse the Icon atom glyphs (x, plus, chevronDown — already present in atoms/icons.ts) and the existing tokens.css .method color classes; introduce no new runtime dependency.
- Must follow: Author hygiene/AC verification commands behaviorally or with comment-line stripping so a grep does not self-match JSDoc/comments that quote the forbidden pattern (lesson from feature 002 AC-14).
- Must not break: The opt-in Tabs contract must stay backward-compatible: the non-closable render path stays byte-identical to the 002 selection-only contract (no method chip, no dirty/close node, no extra roving stop), proven by a regression test (002 AC-11).
- Must not break: The deriveLabel/AC-25 label precedence and the tabsStore lifecycle must not regress — 005 changes presentation and descriptor mapping only.
- Must follow constitution §2.1: Renderer-only: Tabs, TabBar, tokens.css carry no Node or electron imports; the renderer reaches the platform only through preload-exposed globals.
- Must follow constitution §2.3: Resolve renderer cross-module imports via the @renderer alias; lib stays leaf. The global .method/.{METHOD} class usage inside Tabs is a documented departure from the BEM-only convention and must be recorded in the 002 lineage.
- Must follow constitution §3.1: Strict mode, no any: the new optional TabDescriptor.method and .dirty fields are fully typed; method is narrowed against the known set before applying a color class.
- Must follow constitution §3.4: Gate behavior and fidelity with Vitest + Testing Library and Playwright CT, co-located under __tests__/ split .test.tsx/.ct.tsx; the real-browser computed-style assertions require Playwright CT because jsdom cannot resolve pseudo-element computed styles.

## 8. Open Questions

- **Q-1**: Exact --m-head color value (light + dark) is deferred to /plan; spec mandates HEAD IS colored via a new --m-head token + .method.HEAD class (uncolored HEAD rejected), /plan picks a hue distinct from the existing six methods.
- **Q-2**: Exact screenshot-diff anti-aliasing pixel-threshold value is deferred to /plan; spec mandates an explicit threshold MUST be set (verification is computed-style assertions + thresholded diff, not eyeballing), /plan fixes the concrete number (e.g. Playwright toHaveScreenshot threshold + maxDiffPixelRatio).
- **Q-3**: Accessibility tradeoff: the dirty dot has no accessible name (matching the reference's span-title pattern); assistive-tech close routes via the retained Delete/Backspace keyboard path, not a pointer label. Accepted for v1 and to be documented in the 002 lineage; revisit if an explicit aria-label on the dirty dot is later wanted.
- **Q-4**: The .tabs overflow:hidden (Tabs.css:40) must be removed or guarded only if it clips the new active ::before accent or the chevron; whether removal is needed is settled by the runtime design-auditor probe during /plan or /implement (no blind removal).
- **DP-breaking_changes-1** [no DP in category breaking_changes]: no relevant decision point for breaking_changes
- **DP-tooling_configuration-1** [no DP in category tooling_configuration]: no relevant decision point for tooling_configuration

## 9. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Shared 002 contract change; active-CSS rewrite + overflow:hidden removal could regress other Tabs consumers / clip accent; mitigated by .tabbar-scoping + byte-identical-path test + runtime probe. | Med | Med | tbd via /plan |
| Shared 002 contract change: the active-CSS rewrite + possible overflow:hidden removal could regress other Tabs consumers or clip the new ::before accent/chevron. | Med | Med | Scope new active/geometry CSS to .tabbar; keep a closable=false byte-identical regression test; confirm via a runtime design-auditor (Chrome DevTools MCP) probe that ::before/::after/chevron are not clipped. |
| jsdom cannot resolve ::before/::after computed styles, so the EXACT computed-style fidelity assertions must run in Playwright CT (real browser); a flaky or stale CT build cache could mask a clean source as broken. | Med | Med | Author fidelity assertions in Playwright CT (established by feature 001); when a build/test error names a clean file, clear the CT cache (playwright/.cache, node_modules/.vite, dist) and re-run before editing source (memory lesson 2026-06-24). |
| Removing the badge:'●' mapping + deleting the .tabbar .tabs__badge block leaves the existing TabBar.test AC-26 '●' assertions failing. | Med | Low | Migrate the TabBar.test AC-26 dirty-marker assertions to .tabs__tab-dirty/.tabs__tab-close and dirty-dot-click-to-close in the same change; verify the label text is still asserted present. |
| The dirty dot lacking an accessible name reduces screen-reader clarity for the unsaved + close affordance. | Low | Med | Retain and test the keyboard Delete/Backspace close path on dirty tabs; document the accepted tradeoff in the 002 lineage; leave an explicit aria-label as a flagged future option (Q-3). |
