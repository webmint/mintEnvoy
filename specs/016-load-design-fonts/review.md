# Feature Review — specs/016-load-design-fonts — 2026-07-10

**Feature**: specs/016-load-design-fonts
**Scope**: assembled feature diff (all tasks together) — 30 files
**Finders invoked**: code-reviewer, architect, qa-reviewer, security-reviewer, performance-analyst
**Refuters invoked**: architect, code-reviewer
**Source Root**: .
**Framework / Language**: Electron, React

## Confirmed — Top Priorities
Force-ranked across the confirmed findings. Fix these first.
(no confirmed findings)

## Confirmed Findings
(none)

## Summary
- Critical: 0 | High: 0 | Medium: 0 | Info: 0
- Confirmed: 0 | Contested: 0 | Dismissed: 2 | Uncertain: 0
- Finders skipped (not installed): none

## Dismissed / Worth a Glance
These findings were reviewed but not confirmed. Dismissed findings had no demonstrable emergent defect at feature scope; uncertain findings could not be resolved from the code alone. A reviewer may want to glance at them before closing the review.

### Dismissed
- [D-001] [Medium] src/renderer/src/__tests__/font-load.ct.tsx:83 — Cross-task duplication — task 003 defines the form-control font-family reset in base.css; task 005 re-states it verbatim as an inline style string in the CT fixture
- [D-002] [Medium] src/renderer/src/__tests__/font-load.ct.tsx:83 — Cross-task blind spot — task 003 establishes a 4-element form-control reset; task 005's CT only asserts 1 of the 4 element types

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

Coverage verdict: CLEAN — Chrome MCP available; runtime fidelity comparison ran against the live Electron renderer at http://localhost:5173/.

---

### Scope

Design-manifest pairs (from `specs/016-load-design-fonts/design-manifest.json`):

| Anchor selector | Built selector used | Note |
|---|---|---|
| `body` | `#root` (id-matched; `data-testid="app-root"` absent from DOM) | font-stack root |
| `.method` | `.method` (class-matched; `data-testid="request-bar-method"` absent from DOM) | mono-font anchor |

No explicit MATCH/DEVIATE disposition field is present in the manifest; both pairs treated as MATCH for typography axes, consistent with feature intent.

---

### Font-not-loaded sanity check

`document.fonts.ready` awaited before all reads.

| Font family | Weight | Registered | Status | Pass |
|---|---|---|---|---|
| Inter | 400 | yes | loaded | yes |
| Inter | 500 | yes | loaded | yes |
| Inter | 600 | yes | loaded | yes |
| Inter | 700 | yes | loaded | yes |
| JetBrains Mono | 400 | yes | loaded | yes |
| JetBrains Mono | 600 | yes | unloaded (lazy) | yes — see advisory |
| JetBrains Mono | 700 | yes | loaded | yes |

All required weights are registered via `@font-face`. JBM 600 is in "unloaded" state because no currently visible content requests that weight (`[data-mstyle='dot']` uses `font-weight: 600` + `--font-mono`, but the dot variant is not in the visible viewport). `document.fonts.check('600 12px "JetBrains Mono"')` returns `false` for the same reason — this is expected lazy-loading, not a missing-file defect.

---

### Computed-style fidelity — token axes

Reference values from `design/styles.css` `:root` block.

| Axis | Design reference value | Implementation computed value | Status |
|---|---|---|---|
| `--font-sans` token | `"Inter", system-ui, -apple-system, sans-serif` | `'Inter', system-ui, -apple-system, sans-serif` | MATCH |
| `--font-mono` token | `"JetBrains Mono", "SF Mono", ui-monospace, Menlo, Consolas, monospace` | `'JetBrains Mono', 'SF Mono', ui-monospace, Menlo, Consolas, monospace` | MATCH |
| `body` computed `font-family` | Inter-first stack | `Inter, system-ui, -apple-system, sans-serif` | MATCH |
| `.method` computed `font-family` | JBM-first stack | `"JetBrains Mono", "SF Mono", ui-monospace, Menlo, Consolas, monospace` | MATCH |
| `.method` computed `font-weight` | `700` (base `.method` rule) | `700` | MATCH |
| `.method` computed `font-size` | `9.5px` (chip/soft mstyle) | `9.5px` | MATCH |
| `.titlebar` computed `font-family` | Inter-first stack (inherits `--font-sans`) | `Inter, system-ui, -apple-system, sans-serif` | MATCH |
| button computed `font-family` | Inter-first stack (inherits `--font-sans`) | `Inter, system-ui, -apple-system, sans-serif` | MATCH |

---

### Overflow / clipping check

| Element | scrollWidth | clientWidth | overflowX | Status |
|---|---|---|---|---|
| `.method` | 42px | 42px | visible | No clipping |

No horizontal overflow or text clipping detected on the method anchor element.

---

### Non-gating advisory

**`data-testid` anchors missing (Info):** Neither `data-testid="app-root"` nor `data-testid="request-bar-method"` exists in the live DOM. `document.querySelectorAll('[data-testid]')` returns an empty list — no testid attributes are present anywhere in the document. Runtime comparison fell back to `#root` and `.method` selectors successfully. If future tooling relies on testid-keyed lookup from the design-manifest `built_testid` field, those lookups will fail silently. The visual fidelity itself is not affected. Suggest the frontend-engineer add `data-testid` attributes to the root div and the method span if the manifest's `built_testid` fields are intended for CT harness targeting.

## Accessibility

Coverage: Chrome MCP connected — Electron renderer at http://localhost:5173/ (804×638 viewport). Runtime-assisted audit: computed styles and font-load states read live via `evaluate_script`.

**Feature-016 font-inheritance re-check (the specific remediation this run validates):**
All buttons (Titlebar workspace pill, icon buttons, env selector, account pill) now compute `"Inter", system-ui, -apple-system, sans-serif` — the previous Arial fallback is resolved by `button,input,select,textarea{font-family:inherit}` in `base.css`. The KVTable delete button (`✕`) also resolves Inter. KV cell inputs correctly resolve `"JetBrains Mono"…` (explicit `.kv-cell input { font-family: var(--font-mono) }` rule beats the inherit global). GET method button resolves JetBrains Mono 700 as intended. JetBrains Mono 600 shows `unloaded` in `document.fonts` — lazy-load, not a failure (no rendered text currently requests that weight).

### Accessibility

| Check | Severity | Status | Details |
|-------|----------|--------|---------|
| Semantic HTML — landmarks | High | Pass | `<header>` (banner), `<main>`, `<aside>` (complementary/sidebar), `<section aria-label="Notifications">` all present. No `<nav>` but `role="tablist"` on both tab groups is correct. |
| Semantic HTML — headings | Medium | Fail | Zero `<h1>`–`<h6>` elements in the document. Screen reader users cannot skim heading structure. Suggest adding a visually-hidden `<h1>` scoping the active request tab title. |
| ARIA — tab patterns (sub-tabs) | Info | Pass | Sub-tabs tablist has `aria-label="Request sub-tabs"`. Each sub-tab has `aria-selected`, `aria-controls="panel-*"`, and matching tabpanel `aria-labelledby`. Tabpanels are correct. |
| ARIA — tab patterns (working tabs / TabBar) | Medium | Fail | Working-tabs tablist (`aria-label="Open request tabs"`) omits `aria-controls` on each tab button — sub-tabs have it, working tabs do not. WCAG SC 4.1.2 requires the association. Suggest adding `aria-controls` pointing to the active request pane region. |
| ARIA — buttons | Info | Pass | All icon-only Titlebar buttons have accessible text via visible text or `aria-label`. Send button is correctly dual-marked `disabled` + `aria-disabled="true"`. |
| ARIA — SVG icons | Info | Pass | All 12 inline SVGs carry `aria-hidden`; none expose decorative content to the accessibility tree. |
| Form labels — URL input | Info | Pass | Request URL input has `aria-label="Request URL"`. |
| Form labels — KV table inputs | Critical | Fail | Key, Value, and Description `<input>` elements in every KVTable row have no `aria-label`, no `aria-labelledby`, and no associated `<label>` element. Placeholder text ("Key", "Value", "Description") is not an accessible name per WCAG SC 1.3.1 / 4.1.2. Affects both the new-row inputs and existing rows. Fix: add `aria-label` to each input (e.g. `aria-label="Key"`, `aria-label="Value"`, `aria-label="Description"`) or use `aria-labelledby` pointing to the column header cells. |
| Form labels — KV checkboxes | Pass | Pass | Row-enable checkboxes carry `aria-label="Toggle row N"` / `aria-label="Enable new row"`. |
| Keyboard nav — focus order | Info | Pass | Tab order follows visual document order (Titlebar → Tabs → RequestBar → SubTabs → KVTable). |
| Keyboard nav — focus visible (RequestBar) | Info | Pass | RequestBar method button, Send, Save, Share each have `2px solid var(--accent)` `:focus-visible` outline. URL bar shows `border-color: var(--accent)` + `box-shadow` on `:focus-within`. Dropdown items use `data-highlighted` background. Tabs and Divider have `:focus-visible` outlines. |
| Keyboard nav — focus visible (Titlebar buttons) | Critical | Fail | `.titlebar__workspace-pill`, `.titlebar__icon-btn` (sidebar toggle, command palette), `.titlebar__env-selector`, `.titlebar__account-pill` all define hover states but have **no** `:focus-visible` CSS rule. Keyboard-focused Titlebar buttons show no visible ring. Violates WCAG SC 2.4.7. Fix: add `&:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }` to each Titlebar button class (or a single `.titlebar :is(button,a):focus-visible` rule). |
| Keyboard nav — focus visible (KV inputs) | Critical | Fail | `.kv-cell input` sets `outline: none` with no parent `:focus-within` indicator. When a KV Key/Value/Description input receives keyboard focus there is no visible ring. Violates WCAG SC 2.4.7. Fix: add `.kv-cell:focus-within { outline: 2px solid var(--accent); outline-offset: -2px; }` or a row-level `:focus-within` border. |
| Keyboard nav — focus visible (KV delete button) | Critical | Fail | `.kv-actions button` (the `✕` delete button) has no `:focus-visible` rule. The button appears on row hover; when keyboard-focused it shows no indicator. Violates WCAG SC 2.4.7. Fix: add `.kv-actions button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }`. |
| Color contrast — Titlebar button text | Info | Pass | `rgb(108,108,117)` on `rgb(251,250,249)` = **4.99:1** (required 4.5:1, 12.5px/500). ✓ |
| Color contrast — Tab text (active and inactive) | Info | Pass | `rgb(24,24,27)` on `rgb(251,250,249)` = **16.99:1**. ✓ |
| Color contrast — Request URL input text | Info | Pass | `rgb(24,24,27)` on `rgb(255,255,255)` = **17.72:1**. ✓ |
| Color contrast — KV column headers | Info | Pass | `rgb(110,110,119)` (--text-faint) on `rgb(251,250,249)` = **4.84:1** at 10.5px/600. ✓ |
| Color contrast — Save button | Info | Pass | `rgb(108,108,117)` on `rgb(255,255,255)` = **5.20:1**. ✓ |
| Color contrast — Send button (disabled) | Info | Pass | 4.17:1 — disabled control; WCAG SC 1.4.3 exempts inactive UI components from the contrast requirement. ✓ |
| Color contrast — Method chip (soft mode, pre-existing) | Medium | Fail | GET method text `rgb(14,165,233)` (--m-get) against effective blended background ≈ `rgb(216,241,251)` (16 % alpha chip tint over white) ≈ **2.36:1** (required 4.5:1 at 9.5px bold). Same formula applies to all method colors (POST/PUT/PATCH/DELETE/OPTIONS) — all fail WCAG AA. Pre-existing design choice predating feature 016; not introduced by this feature. Suggest the design-system owner evaluate whether a darker text shade or fully-opaque chip bg could satisfy AA while preserving brand color hue. |
| Motion / animation — reduced-motion | Info | Pass | All animated components (Toast, Icon spin, RequestBar transitions, Dropdown, Tabs, TabBar, Divider handle) have `@media (prefers-reduced-motion: reduce)` rules disabling transitions. ✓ |
| Alt text — images | Info | Pass | No `<img>` elements in the rendered page. |

### Responsive

This is an Electron desktop application (`minWidth: 720` enforced by `BrowserWindow` configuration in `src/main/index.ts:11`). Standard web breakpoints (320 px, 768 px) and mobile/touch-target requirements do not apply. Audit scope is the usable desktop window range.

| Breakpoint / Condition | Severity | Status | Issues |
|------------------------|----------|--------|--------|
| 804 px (current runtime) | Info | Pass | No horizontal overflow (`scrollWidth === clientWidth`). All elements contained. Text legible — Inter at 12.5px base, JetBrains Mono at 12px in KV cells. |
| 720 px (Electron minimum, enforced) | Medium | Fail | Titlebar uses a `grid-template-columns: 1fr auto 1fr` layout with the cmdk bar fixed at 360 px. At 720 px each side column receives 180 px, down from ~258 px left / ~162 px right at 804 px. The left section (logo + workspace pill text "Friends & Family") currently measures 258 px — wider than the 180 px available at minimum width. `.titlebar__workspace-name` has no `overflow: hidden` or `text-overflow: ellipsis`. The workspace name will be clipped or push the sidebar-toggle button off-screen. Fix: add `overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: <value>` to `.titlebar__workspace-name`, or add `min-width: 0` to the left flex items so the flex container can shrink correctly. |
| 1024 px | Info | Pass | App scales well. No overflow. Content proportioned correctly. |
| 1440 px | Info | Pass | App scales well. No overflow. |
| Touch targets | Info | N/A | Electron desktop app — touch target requirements (44×44 pt iOS / 48×48 dp Android) do not apply. |
| Font reflow from 016 | Info | Pass | Switching from system-fallback (SF Pro on macOS) to self-hosted Inter causes minor per-glyph metric differences. No text reflow overflow detected at current 804 px viewport. The url-bar uses a flex shrink layout that accommodates the slight width change. |
