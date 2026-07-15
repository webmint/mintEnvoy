# Feature Review — specs/017-body-editor-shell — 2026-07-15

**Feature**: specs/017-body-editor-shell
**Scope**: assembled feature diff (all tasks together) — 52 files
**Finders invoked**: code-reviewer, architect, qa-reviewer, security-reviewer, performance-analyst
**Refuters invoked**: code-reviewer, architect
**Source Root**: .
**Framework / Language**: Electron, React

## Confirmed — Top Priorities
Force-ranked across the confirmed findings. Fix these first.
(no confirmed findings)

## Confirmed Findings
(none)

## Summary
- Critical: 0 | High: 0 | Medium: 0 | Info: 0
- Confirmed: 0 | Contested: 0 | Dismissed: 4 | Uncertain: 0
- Finders skipped (not installed): none

## Dismissed / Worth a Glance
These findings were reviewed but not confirmed. Dismissed findings had no demonstrable emergent defect at feature scope; uncertain findings could not be resolved from the code alone. A reviewer may want to glance at them before closing the review.

### Dismissed
- [D-001] [Medium] src/renderer/src/components/organisms/BodyEditor.tsx:104 — Cross-task architectural drift — one task's scroll-preservation contract (RequestSubTabs panel, AC-9) does not reach a nested scroll container a second task introduces (BodyEditor's raw-body textarea)
- [D-002] [Medium] src/renderer/src/components/organisms/__tests__/BodyEditor.stories.tsx:60 — Cross-task duplication — Task 010 open-codes body defaults that Task 001 already canonicalized as BLANK_BODY
- [D-003] [Medium] src/renderer/src/components/organisms/__tests__/RequestSubTabs.ct.tsx:1095 — Cross-task test coverage gap — assembled write-isolation triangle is missing the headers-edit → body-raw-text direction
- [D-004] [Medium] src/renderer/src/components/organisms/__tests__/BodyEditor.ct.tsx:437 — Cross-task test coverage gap — no CT verifies per-request-tab urlencoded row isolation when BOTH request tabs are in urlencoded mode

## Methodology
Findings are grounded — every finding carries a verbatim quote from the actual
cross-task code, and validation discards ungrounded ones. A refutation stage
then cross-examines each grounded finding before it reaches the report: a
finding earns the headline only by surviving an adversary who default-dismisses
anything not demonstrable as emergent at feature scope. Confirmed findings reach
the headline; dismissed findings and low-stakes uncertain findings drop to the
Dismissed / Worth a Glance appendix; contested findings (a high-stakes `security`
/ `[CONSTITUTION-VIOLATION]` finding the refuter could not confirm, or a
`[CONSTITUTION-VIOLATION]` finding the refuter dismissed) are surfaced in the
headline, flagged `[CONTESTED]`, never buried. This report is findings only —
the verdict is `/verify`'s.

## Design Fidelity

Coverage: DEFECT — 2 value-axis mismatches detected via computed-style diff; all color, border, radius, and typography axes otherwise CLEAN.

### Computed-Style Diff

| Element (`data-ref`) | Disposition | Axis | Design (reference.html) | Implementation | Severity | Status |
|---|---|---|---|---|---|---|
| `.body-toolbar` | MATCH | height | 45px | 40px | Medium | Mismatch |
| `.body-toolbar` | MATCH | border-bottom | 1px solid rgb(240,239,237) | 1px solid rgb(240,239,237) | — | Match |
| `.body-toolbar` | MATCH | padding | 8px 16px | 8px 16px | — | Match |
| `.body-toolbar` | MATCH | gap / align-items | 4px / center | 4px / center | — | Match |
| `.body-radio` (inactive) | MATCH | color / bg / padding / radius | rgb(108,108,117) / transparent / 4px 10px / 5px | same | — | Match |
| `.body-radio` (active) | MATCH | bg / color / font-weight | rgb(232,230,227) / rgb(24,24,27) / 500 | same | — | Match |
| `.body-radio` active `.dot` | MATCH | bg / size / radius / border | rgb(16,185,129) / 8×8px / 50% / 1.5px | same | — | Match |
| `.lang-pill` | MATCH | bg / color / border / radius / padding | rgb(244,243,241) / rgb(108,108,117) / 1px rgb(232,230,227) / 5px / 3px 8px | same | — | Match |
| `.code-editor` | MATCH | padding / font / line-height / display | 12px 0px / JetBrains Mono 12.5px / 20.625px / grid | same | — | Match |
| `.code-editor .gutter` | MATCH | color / font-size / padding-right | rgb(110,110,119) / 11.5px / 12px | same | — | Match |
| `.code-editor pre` | MATCH | padding | 0px | 0px 12px | Medium | Mismatch |
| `.code-editor pre` | MATCH | font-family | monospace (fonts not loaded in reference.html) | JetBrains Mono loaded | Info | See advisory |
| `.tk-key` | MATCH | color | rgb(3,105,161) | #0369a1 → rgb(3,105,161) via token | — | Match |
| `.tk-str` | MATCH | color | rgb(21,128,61) | #15803d → rgb(21,128,61) via token | — | Match |
| `.tk-num` | MATCH | color | rgb(180,83,9) | #b45309 → rgb(180,83,9) via token | — | Match |
| `.tk-bool` | MATCH | color | rgb(190,24,93) | #be185d → rgb(190,24,93) via token | — | Match |
| `.tk-punc` | MATCH | color | rgb(108,108,117) | #6c6c75 → rgb(108,108,117) via token | — | Match |

### Sanity Floor

| Check | Status | Notes |
|---|---|---|
| Font loaded (Inter) | PASS | `document.fonts` reports all Inter variants loaded |
| Font loaded (JetBrains Mono) | PASS | JetBrains Mono loaded; reference.html does not load the font file so its `pre` resolves to browser-default `monospace` — this is a reference artifact, not an implementation defect |
| Overflow / clipping | PASS | No overflow detected on `.code-editor`, `.body-toolbar`, or `.code-editor pre` |

### Defect Details

**D1 — `.body-toolbar` height 5px short (Medium)**
Reference renders at 45px; implementation renders at 40px. Root cause: the reference's `.right` section is 28px tall because it contains action buttons (visible in the reference screenshot as a lightning-bolt, copy, and code-view icon) alongside the lang-pill, pushing the flex-container to 28px. The implementation's `.right` contains only the `body-lang-pill` (21px), making the flex container settle at 40px. Fix options: add a `min-height: 45px` rule to `.body-toolbar` so the toolbar height is anchor-independent, OR add the missing right-section action buttons (if in scope).

**D2 — `.code-editor pre` has unexpected 12px horizontal padding (Medium)**
Reference `pre` uses `padding: 0px`; implementation uses `padding: 0px 12px`. The 12px left padding shifts code content 12px further right than the design intends, and the 12px right padding narrows the scrollable code area. The gutter already provides visual separation via its own `padding-right: 12px`. Fix: remove the `padding: 0px 12px` from the `pre` element rule, or if a left-padding gap is desired, confirm it against the design token for code indentation.

### Non-Gating Advisory

- The reference's `.body-toolbar .right` section contains additional action icons (flash/send, copy, `</>` code view) beyond the lang-pill that are absent from the implementation. This is likely a later-scope concern (the current spec is the shell); however, it is the direct cause of the toolbar height delta (D1) and is noted here as context.
- Token syntax colors all resolve correctly through CSS custom properties; the static-fidelity (token-provenance) gate already verified no hardcoded literals are used.

## Accessibility

### Accessibility

Runtime conformance: Chrome MCP available and connected to Electron renderer at http://localhost:5173/. Accessibility audit performed with live DOM inspection, computed-style queries, and programmatic keyboard-event simulation against the BodyEditor in Raw mode and x-www-form-urlencoded mode.

| Check | Severity | Status | Details |
|-------|----------|--------|---------|
| Semantic HTML — heading hierarchy | High | Fail | Zero `<h1>`–`<h6>` elements exist anywhere in the app. Screen reader "jump by heading" navigation finds nothing. The tabs (`Params`, `Body`, etc.) serve as in-page navigation landmarks but no heading identifies the request editor area. Fix: add a visually-hidden `<h1>` or `<h2>` as the app root heading and a `<h2>` scoping the request panel. |
| Semantic HTML — landmark labels | Info | Pass | Single `<header>`, single `<aside>` (complementary), single `<main>`, single `<footer role="status">`. No duplicate landmark types, so unlabelled landmarks do not create ambiguity. No finding required. |
| Semantic HTML — tabpanel association | Pass | Pass | `panel-body` carries `aria-labelledby="tab-body"`; `id="tab-body"` is present and resolves to the "Body" tab element. All six sub-tab panels follow the same pattern. |
| Semantic HTML — KVTable grid semantics | Medium | Fail | The x-www-form-urlencoded KVTable uses all `<div>` elements with no `role="grid"`, `role="row"`, `role="columnheader"`, or `role="gridcell"`. Column headers (KEY, VALUE, DESCRIPTION) carry IDs that inputs reference via `aria-describedby`, so column context is present, but screen reader users cannot use grid navigation commands (Ctrl+Alt+Arrow on NVDA; VO+Arrow on VoiceOver) to traverse rows and cells. Fix: add `role="grid"` to `.kv`, `role="row"` to `.kv-header` and each `.kv-row`, `role="columnheader"` to the three header `<div>` cells, and `role="gridcell"` to `.kv-cell` elements. |
| ARIA — radiogroup | Pass | Pass | `role="radiogroup"` on `.body-radiogroup` with `aria-label="Request body type"`. Each child `[role="radio"]` carries `aria-checked` (`"true"` / `"false"`) and correct roving tabindex (`0` on checked, `-1` on all others). Arrow-key auto-selection confirmed: ArrowRight from "Raw" moves focus to and selects "x-www-form-urlencoded", updating `aria-checked` and `tabindex` on both elements. |
| ARIA — decorative gutter | High | Fail | The `.gutter` element (`<div class="gutter" data-testid="body-gutter">`) renders line numbers ("1", "2", …) for visual orientation only but is **not** marked `aria-hidden="true"`. Screen readers announce the number(s) as content. The `<pre aria-hidden="true">` syntax-highlight overlay is correctly suppressed. Fix: add `aria-hidden="true"` to the `.gutter` div. |
| ARIA — lang-pill button | Medium | Fail (partial) | `<button class="lang-pill" aria-label="Raw body language: json">` is a cycle button — each click advances the language (json → xml → html → text → json). The button has no `aria-haspopup` or `aria-expanded` (correct — it does not open a popup). However, when clicked and the `aria-label` updates in place, VoiceOver and NVDA do not re-announce the button's new label because focus remains on the button after activation. There is no `aria-live` region to announce the language change. Screen reader users receive no feedback after clicking. Fix: add a visually-hidden `role="status"` live region and emit "Body language: [lang]" when `handleLangCycle` fires. |
| ARIA — pre overlay | Pass | Pass | `<pre data-testid="body-pre" aria-hidden="true">` correctly hides the syntax-highlight overlay from the accessibility tree. |
| ARIA — textarea | Pass | Pass | `<textarea aria-label="Request body" multiline>` provides an explicit label. No `role` override needed for native `<textarea>`. `spellcheck="false"` is set (appropriate for code). |
| Keyboard nav — radiogroup roving focus | Pass | Pass | Tab enters the radiogroup on the checked radio (tabindex=0). ArrowRight/ArrowLeft move focus and selection. Only one stop enters/exits the group, consistent with the ARIA radiogroup pattern. |
| Keyboard nav — focus order | Pass | Pass | Within the Body panel in Raw mode the tab order is: radiogroup (single stop) → lang-pill → textarea. In x-www-form-urlencoded mode: radiogroup → KV checkbox → KV key input → KV value input → KV description input. Logical, matches visual reading order. |
| Keyboard nav — focus visibility on radio | Pass | Pass | `.body-radio:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }` — matches the app-wide design system focus style. Confirmed present in the live stylesheet. |
| Keyboard nav — focus visibility on lang-pill | High | Fail | `.lang-pill` has **no** `:focus-visible` CSS rule. When focused, the element falls back to the macOS browser default (`rgb(229,151,0) auto 1px`). Computed contrast of that default ring against the button's background (`rgb(244,243,241)`) is **2.17:1**, which fails WCAG 2.2 SC 2.4.11 Focus Appearance (minimum 3:1). Every other interactive element in the app (`tabs`, `method button`, `send`, `save`, `kv-cell input`, `divider`) has an explicit `outline: 2px solid var(--accent)` rule. Fix: add `.lang-pill:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }` to `BodyEditor.css`. |
| Keyboard nav — focus visibility on code editor | Pass | Pass | `.code-editor-content:focus-within { outline: 2px solid var(--accent); outline-offset: 1px; }` applies when the textarea inside is focused. Provides a visible, design-consistent 2px accent outline on the editor container. |
| Color contrast — inactive radio text | Pass | Pass | Inactive radio label: `rgb(108,108,117)` on `rgb(251,250,249)` page background → **4.99:1** (threshold: 4.5:1 for 12.5px normal weight text). Passes WCAG AA. |
| Color contrast — active radio text | Pass | Pass | Active radio label: `rgb(24,24,27)` on `rgb(232,230,227)` → **14.22:1**. Passes. |
| Color contrast — lang-pill text | Pass | Pass | `rgb(108,108,117)` on `rgb(244,243,241)` → **4.69:1**. Passes WCAG AA (4.5:1 threshold for 11px text, which is normal size). |
| Alt text / image labels | Pass | Pass | No `<img>` elements in the BodyEditor scope. Decorative icons inside buttons are SVG or CSS; no missing `alt` attributes. |
| Target size — radio buttons | Medium | Fail | All six radio buttons measure **23×23px**, 1px below the WCAG 2.2 AA SC 2.5.8 minimum of 24×24px. The lang-pill button is **42×21px** (height fails). The 4px `gap` between items may satisfy the WCAG 2.5.8 "spacing exception" (24px diameter circle centred on each target must not overlap adjacent targets' circles), but the height of 23px makes the circle 24px → the top/bottom circles of adjacent rows could touch at the 4px gap. Fix: increase radio and lang-pill height to at minimum 24px (or 28px with padding to comfortably clear the exception). |
| Dynamic content / live regions | Medium | Fail | No `aria-live` regions anywhere in the BodyEditor. The lang-pill language cycle (noted above) and any future dynamic state changes (e.g. body type switching) are not announced. The `<footer role="status" aria-live="polite">` global status bar is available but not used for BodyEditor state changes. Fix: use the existing status bar or add a scoped `role="status"` region to announce language changes. |

### Responsive

Window resize (`Browser.getWindowForTarget`) is unavailable in this Electron DevTools session; pane width was simulated by constraining `.pane-split__pane--request` via inline style. The Electron app enforces `minWidth: 720` in its `BrowserWindow` config (`src/main/index.ts`). At the default sidebar width (260px), the request pane's effective minimum is ~460px. No viewport-based media queries exist in any stylesheet; all responsive behavior is passive `flex-wrap`.

| Breakpoint / Context | Severity | Status | Issues |
|----------------------|----------|--------|--------|
| 1440px (1205px pane — nominal) | Info | Pass | Single-row toolbar: radiogroup (578px) + lang-pill (42px) fit in 1205px with room to spare. No wrapping, no overflow, no horizontal scroll. |
| 1024px (~764px pane after sidebar) | Info | Pass | Single-row toolbar still fits. All radio labels fully visible. Lang-pill right-aligned. No issues. |
| 768px pane (simulated) | Info | Pass | Toolbar remains single-row (confirmed via layout measurement: toolbar height stays at 40px). All six radio options + lang-pill fit. No overflow. |
| ~620px pane (~880px window) — wrap threshold | Medium | Fail | At the point where radiogroup (578px) + lang-pill (42px) + gap can no longer fit in one row, the `.right` wrapper carrying the lang-pill drops to its own row via `flex-wrap: wrap`. The lang-pill is **visually orphaned** on a row of its own with no label or separator indicating what it controls. The spatial association between "Raw" mode and the lang-pill is broken. Fix: when the toolbar wraps, either (a) keep the lang-pill inline after the selected radio using a nested flex group, or (b) add a `min-width` floor on the toolbar container that prevents wrapping until a reasonable threshold. |
| 460px pane (720px window — Electron minimum) | Medium | Fail | Reproduced at the app's enforced minimum window width. Radiogroup wraps to 3 rows (row 1: None + Raw; row 2: x-www-form-urlencoded + Form data; row 3: Binary + GraphQL). Toolbar expands to 119px height. Lang-pill remains orphaned on a fourth visual row. The code editor height is further reduced because the toolbar now consumes ~79px more vertical space. No minimum height protection on the editor. The sidebar `minWidth` of 200px (from the resize handle `valuemin`) means at 720px the worst-case pane is 720−200=520px, still triggering the wrap. |
| Horizontal overflow — all widths | Info | Pass | `document.documentElement.scrollWidth === window.innerWidth` at 1470px — no horizontal scroll. The pane has `overflow: hidden` which clips content rather than extending the document width. No overflow issue at the measured viewport. |
| Text readability — narrow widths | Info | Pass | At 460px pane, radio button text labels remain fully readable (none truncate — the shortest labels "None", "Raw" shrink to their intrinsic width on their row). No `white-space: nowrap` truncation observed. |
| No viewport media queries | Info | Note | The BodyEditor has zero width-based `@media` breakpoints. All layout adaptation relies on `flex-wrap`. For a desktop-only Electron app this is acceptable, but the wrap threshold analysis above shows flex-wrap alone produces a disjointed layout at the enforced minimum window size. |
