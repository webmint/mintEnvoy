# Feature Review — specs/019-code-editor-toggle — 2026-07-22

**Feature**: specs/019-code-editor-toggle
**Scope**: assembled feature diff (all tasks together) — 29 files
**Finders invoked**: code-reviewer, architect, qa-reviewer, security-reviewer, performance-analyst
**Refuters invoked**: code-reviewer
**Source Root**: .
**Framework / Language**: Electron, React

## Confirmed — Top Priorities
Force-ranked across the confirmed findings. Fix these first.
(no confirmed findings)

## Confirmed Findings
(none)

## Summary
- Critical: 0 | High: 0 | Medium: 0 | Info: 0
- Confirmed: 0 | Contested: 0 | Dismissed: 1 | Uncertain: 0
- Finders skipped (not installed): none

## Dismissed / Worth a Glance
These findings were reviewed but not confirmed. Dismissed findings had no demonstrable emergent defect at feature scope; uncertain findings could not be resolved from the code alone. A reviewer may want to glance at them before closing the review.

### Dismissed
- [D-001] [Medium] src/renderer/src/components/organisms/BodyEditor.tsx:221 — An abstraction (CodeEditor's resetKey scroll-reset contract) that the assembling parent BYPASSES — the organism drives editing/preview reset itself but never wires the molecule's own resetKey reset for the same tab-switch event

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

Coverage: DEFECT — runtime conformance comparison ran against `design/reference.html` and the live app at `http://localhost:5173/`; one value drift detected on the MATCH element, plus a structural divergence advisory.

### Computed-style diff — `.code-editor` (data-ref: `.code-editor` / `[data-testid="body-code-editor"]`)

| Axis | Design (reference.html) | Implementation | Severity | Status |
|------|------------------------|----------------|----------|--------|
| `padding-right` | `0px` | `12px` | Medium | Mismatch |
| `padding-top` | `12px` | `12px` | — | Match |
| `padding-left` | `0px` | `0px` | — | Match |
| `padding-bottom` | `12px` | `12px` | — | Match |
| `display` | `grid` | `grid` | — | Match |
| `grid-template-columns` | `36px 1fr` | `36px 1fr` | — | Match |
| `overflow` | `visible` | `visible` | — | Match |
| `font-size` | `12.5px` | `12.5px` | — | Match |
| `line-height` | `20.625px` | `20.625px` | — | Match |
| `color` | `rgb(24, 24, 27)` | `rgb(24, 24, 27)` | — | Match |
| `font-family` (first token) | `"JetBrains Mono"` | `"JetBrains Mono"` | — | Match |
| `background-color` | `rgba(0,0,0,0)` | `rgba(0,0,0,0)` | — | Match |
| Gutter `color` | `rgb(110, 110, 119)` | `rgb(110, 110, 119)` | — | Match |
| Gutter `font-size` | `11.5px` | `11.5px` | — | Match |
| Gutter `padding-right` | `12px` | `12px` | — | Match |
| Content `overflow-x` | `visible` (pre direct child) | `hidden` (`.code-editor-content` wrapper) | Info | Structural |
| Focus ring color (`:focus-within`) | not in reference | `rgb(16, 185, 129)` (2px solid, −2px offset) | — | Added |

**Finding F-1 — `padding-right: 12px` vs design `0px` (Medium).**
The `.code-editor` grid container applies `padding: 12px 12px 12px 0` in production CSS (`CodeEditor.css` line 21). The design reference computes `padding-right: 0px`. The 12px right gutter is a deliberate addition (code comment: "Postman-parity — keeps content off the right edge under horizontal scroll") but it is not classified DEVIATE in the manifest, so it registers as a value drift against the MATCH disposition.

The visual effect: the editable/preview area is 12px narrower than the design reference (1157px vs 1174px of the content column), and the right edge of the textarea/pre sits 12px from the panel right wall rather than flush. No overflow or clipping occurs as a result.

**Sanity floor — overflow / clipping / font-loaded (both states).**

- Edit state: `code-editor` `overflow: visible`; `code-editor-content` `overflow: hidden` clips the textarea horizontally to the column boundary (1157px). The textarea itself is `overflow: auto` so long lines can scroll within that column. No unwanted clipping of content: the 12px right padding keeps the scroll surface off the edge. No regression introduced by the recent right-gutter fix.
- Preview state: same container geometry; `<pre>` inside `.code-editor-content` (overflow: hidden). Horizontal scrolling of long lines is handled by the pre's own `overflow: auto`. Content is not clipped at the reading start; the pre occupies the full column width.
- Focus ring (edit state confirmed visually): `outline: 2px solid rgb(16, 185, 129); outline-offset: -2px` on `.code-editor-content:focus-within`. The inset ring is fully visible on all four sides — no clipping past the pane boundary. Correct.
- Font loaded: `font-family` resolves to `"JetBrains Mono"` as first token in both states — consistent with the design spec. No system-fallback rendering.
- Click-to-edit area: `.code-editor[data-editing='false']` carries `cursor: text`; the full container is the click target. No overflow or clipping anomaly observed in preview state.

### Non-gating visual advisory

**A-1 — Structural wrapper addition (Info, not a defect).**
The reference `.code-editor` has `<pre>` as a direct child of the grid. The implementation inserts `.code-editor-content` as the second grid column, wrapping both `<pre>` (preview) and `<textarea>` (edit). This intermediate div is the conditional-mount mechanism required by the feature. Because the manifest does not declare MATCH at sub-element granularity, the wrapper is not a reportable MATCH violation; it is noted here for completeness.

**A-2 — `padding-right` drift is intentional but undeclared (Medium advisory).**
The 12px right gutter is well-commented in source and visually coherent (prevents content bleeding to the window edge). However, the manifest records no DEVIATE disposition for this axis, so it cannot be treated as pre-approved at audit time. The frontend-engineer should either (a) add a `deviate_reason` entry to `specs/019-code-editor-toggle/design-manifest.json` for the `padding-right` axis, or (b) confirm the reference was intentionally zero and the deviation is intentional — then mark it DEVIATE. This resolves the coverage gap without requiring a CSS change.

## Accessibility

### Accessibility

Chrome MCP available. Live audit run against the Electron app at `http://localhost:5173/` with Body sub-tab → raw radio selected (CodeEditor in preview mode, then toggled to edit mode for secondary checks).

#### Summary of feature elements audited

| Check | Severity | Status | Details |
|-------|----------|--------|---------|
| `body-edit-toggle` — accessible name | High | Pass | `<button type="button">` with `aria-label` that changes contextually: `"Switch to edit"` (preview mode) / `"Switch to preview"` (edit mode). Communicates the next action, which is an acceptable toggle pattern. |
| `body-edit-toggle` — `aria-pressed` missing | Medium | Fail | The toggle button has no `aria-pressed` attribute. WCAG APG toggle button pattern (ARIA 1.2) requires `aria-pressed="true/false"` to announce current state to AT users. The label-swap approach (`"Switch to edit"` / `"Switch to preview"`) conveys the action, not the current state; AT users hear the action but cannot query the *current* mode independently. Fix: add `aria-pressed={editing}` and standardize the label to a stable name (e.g. always `"Edit/preview toggle"`), letting `aria-pressed` carry the state. |
| `body-edit-toggle` — keyboard operability | High | Pass | `type="button"`, `tabIndex=0`, fully keyboard-operable. |
| `body-edit-toggle` — focus ring | High | Pass | `.body-edit-toggle:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px }` — token-bound, 2px solid, visible at focus. Confirmed live: computed `outline: rgb(16, 185, 129) solid 2px`. |
| `body-edit-toggle` — `onMouseDown` preventDefault | High | Pass | `onMouseDown` calls `e.preventDefault()` so clicking the button while the textarea is focused does not blur the textarea first; the toggle fires cleanly without a spurious blur→preview→edit double-transition. No a11y regression from this. |
| `body-edit-toggle` — color contrast | High | Pass | Text `rgb(108,108,117)` on button bg `rgb(244,243,241)` → 4.69:1. Passes WCAG AA 4.5:1 for normal text (11px/500-weight is below the large-text threshold). |
| `body-edit-toggle` — hidden when not in raw mode | High | Pass | `hidden={body.active !== 'raw'}` correctly removes the button from DOM and the accessibility tree when irrelevant. `.body-edit-toggle[hidden] { display: none }` re-overrides the class-level `display:flex`. |
| Preview `<pre role="button">` — role | High | Pass | Correct use: `<pre>` is not a native interactive element; `role="button"` is required. `tabIndex={0}` makes it keyboard-focusable. |
| Preview `<pre>` — accessible name | High | Pass | `aria-label="Request body preview — press Enter or Space to edit"` — descriptive, includes keyboard affordance instructions. |
| Preview `<pre>` — keyboard entry (Enter/Space) | High | Pass | `onKeyDown` handles `Enter` and `Space` → calls `onEditingChange(true)`. `e.preventDefault()` on Space prevents page scroll. Verified in source (`CodeEditor.tsx:179`). |
| Preview `<pre>` — focus ring | High | Pass | `pre:focus { outline: none }` is scoped correctly; `.code-editor-content:focus-within { outline: 2px solid var(--accent); outline-offset: -2px }` provides the visible ring on the container. Confirmed live: focus-within outline `rgb(16, 185, 129) solid 2px` activates when pre is focused. |
| Preview `<pre>` — `aria-pressed` | Info | Pass | No `aria-pressed` needed here; the pre is an action trigger (enter edit), not a two-state toggle. |
| `<textarea aria-label="Request body">` — label | High | Pass | Explicit `aria-label` present. No `<label for>` needed with explicit `aria-label`. |
| `<textarea>` — focus ring | High | Pass | `.code-editor-content:focus-within` outline covers the textarea as well (same container). |
| Whole-area click container — a11y confusion | Medium | Pass | The `.code-editor` `div` gains `onClick` only in preview mode (`onClick={editing ? undefined : handlePreviewClick}`). It carries no `role`, no `tabIndex` (effective tabIndex=-1), and no `aria-label` — so AT users see only the `<pre role="button">` as the named entry control. Mouse users clicking dead space below the text trigger `handlePreviewClick` via event bubbling, which is additive and does not bypass the AT-accessible path. The cursor changes to `text` in preview mode (`[data-editing="false"] { cursor: text }`), which signals edit affordance to sighted users. No a11y confusion introduced. |
| `.lang-pill` — accessible name | High | Pass | `aria-label="Raw body language: json"` — describes both the control purpose and current value. |
| `.lang-pill` — focus ring | Medium | Fail | No `:focus-visible` CSS rule defined for `.lang-pill` (only `.body-edit-toggle:focus-visible` is present in `BodyEditor.css`). The button falls back to the browser UA outline (`outline: auto 1px` in Chromium, orange/accent-based). This is inconsistent with every other interactive element in the feature and does not use the design token. Fix: add `.lang-pill:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px }` to `BodyEditor.css`. |
| `.body-radiogroup` — ARIA pattern | High | Pass | `role="radiogroup"` with `aria-label="Request body type"`. Each child `div` carries `role="radio"`, `aria-checked`, and correct roving-tabIndex (`0` on active, `-1` on inactive). Arrow-key navigation is implemented in `handleRadioKeyDown`. |
| `.body-radio` — focus ring | High | Pass | `.body-radio:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px }` — confirmed live. |
| `.body-radio` — color contrast (inactive) | High | Pass | `rgb(108,108,117)` on `rgb(251,250,249)` → 4.99:1. Passes AA. |
| `.body-radio` — color contrast (active) | High | Pass | `rgb(24,24,27)` on `rgb(232,230,227)` → 14.22:1. Passes AA. |
| Gutter (`aria-hidden`) | High | Pass | `aria-hidden="true"` correctly removes decorative line numbers from AT. |
| Semantic HTML — heading hierarchy | High | Pass | No headings in the editor region; the panel is an application control surface, not document content. No heading hierarchy defect. |
| Landmarks | High | Pass | `<main>` landmark present. Body editor is inside the main landmark. Status bar uses `role="status"`. |
| Tab/panel ARIA pattern | High | Pass | `role="tablist"` → `role="tab"` → `role="tabpanel"` (with `aria-labelledby` and `aria-controls`) implemented for both request sub-tabs and response sub-tabs. |
| Images without alt text | Critical | Pass | No `<img>` elements without `alt` or `aria-hidden`. |
| Form elements without labels | Critical | Pass | All `<textarea>` and `<input>` elements have explicit `aria-label`. |
| Buttons without accessible names | Critical | Pass | All `<button>` elements have accessible names via `aria-label` or visible text. |

#### Findings requiring attention

**F-A1 (Medium) — `body-edit-toggle` missing `aria-pressed`.**
Element: `BodyEditor.tsx:186` — `<button className="body-edit-toggle">`. The button is a two-state toggle (edit vs preview) and must carry `aria-pressed` per WCAG 4.1.2 (Name, Role, Value) and ARIA authoring practices for toggle buttons. Without it, screen readers announce only "Switch to edit" / "Switch to preview" without conveying the current mode as a queryable property. AT users relying on virtual-cursor inspection cannot determine the current state independently from the label.
Suggested fix: add `aria-pressed={editing}` to the button element. Standardize the label to a stable string (e.g. `"Edit/preview mode"`) so AT announces "Edit/preview mode, toggle button, pressed" (edit) or "not pressed" (preview), rather than the action-description pattern.

**F-A2 (Medium) — `.lang-pill` missing `:focus-visible` CSS rule.**
Element: `BodyEditor.css` — no `.lang-pill:focus-visible` rule. All sibling interactive elements (`.body-edit-toggle`, `.body-radio`, `.code-editor-content`) have explicit token-bound focus rings. The lang-pill's UA fallback ring is inconsistent with the design system and may be suppressed in some environments.
Suggested fix: add `.lang-pill:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px }` to `BodyEditor.css`, matching the sibling pattern.

---

### Responsive

This is a desktop Electron app with a documented minimum window width of 720px (per `constitution.md`). WCAG 2.5.5 AAA (44×44 px touch targets) does not apply to desktop-only controls; WCAG 2.5.8 AA (24×24 px minimum) applies. Breakpoints are tested at the design-system relevant widths.

| Breakpoint / Width | Severity | Status | Issues |
|--------------------|----------|--------|--------|
| 1440px (full desktop, current ~1470px) | Info | Pass | No horizontal overflow. Code editor fills pane with 12px right gutter. Toolbar single-row. `flex-wrap:wrap` has room to spare. |
| ~460px effective pane (720px min-window minus 260px sidebar) | Medium | Pass | Both `.body-toolbar` and `.body-radiogroup` have `flex-wrap: wrap` — radios wrap to a second row rather than clipping. Right section (`Edit` + `JSON` pill) wraps below the radios. No overflow detected in CSS. The 12px right gutter on `.code-editor` is outside the scroll layer, so it persists at all widths. |
| Touch targets — toggle button | Info | Info | `body-edit-toggle` computed size: 38×21 px. `lang-pill`: 48×21 px. `body-radio` (raw): 55×23 px. All are below the WCAG 2.5.5 AAA 44×44 px threshold, but this is a desktop Electron app — no mobile breakpoints are targeted. WCAG 2.5.8 AA (24×24 px) minimum: height 21px is 3px below the 24px floor. However, WCAG 2.5.8 includes an offset exception (the offset between adjacent targets can substitute); in a toolbar layout with 4px gap, the effective hit area may still meet the offset criterion. Flag as Info for the desktop desktop context; no immediate action required unless the app is ever ported to touch. |
| Code editor right gutter (12px) | Info | Pass | The 12px `padding-right` is on `.code-editor` (outside the scroll layers for `<pre>` and `<textarea>`), so horizontally-scrolled long lines never bleed to the pane edge. Confirmed `paddingRight: 12px` in computed style. |
| Horizontal overflow — document | Info | Pass | `document.documentElement.scrollWidth === clientWidth` — no document-level horizontal overflow at 1470px. |
