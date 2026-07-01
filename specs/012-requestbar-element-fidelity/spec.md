# Spec: requestbar-element-fidelity

**Date**: 2026-06-30
**Status**: Complete
**Design source**: html:design/reference.html
**Author**: Claude + User

## 1. Overview

Close the remaining visual-fidelity gap between the RequestBar organism (features 009/010, both Complete) and design/reference.html on five presentational props the 010 fidelity pass did not enumerate: the method-trigger font/colour/treatment, the method dropdown's OPEN PANEL styling, the URL input (a missing leading link icon, the wrong font, and a non-matching placeholder string), the Save button's hover state, and the Share button (rendered with a text label instead of icon-only). Each listed element is rebound to design/reference.html's resolved values (from design/styles.css + design-fidelity-contract.md) using existing tokens.css custom-properties and the project's own semantic class names — no new tokens, no design-export cruft, and ZERO behaviour change. The fix is localized to RequestBar.css/.tsx plus a bounded alignment of the shared Dropdown molecule's open panel.

## 2. Current State

RequestBar (src/renderer/src/components/organisms/RequestBar.tsx + sibling RequestBar.css) renders the [method ▾][URL][Send/Save/Share] bar wired to tabsStore (009/010, both Complete). Five presentational props still drift from design/reference.html. (1) The URL field is a bare input (src/renderer/src/components/organisms/RequestBar.tsx:285-292) with no leading icon and placeholder "Enter URL" (line 290) — the reference .url-bar (design/styles.css:772-795) is a flex container [leading icon + input, gap 6px] whose placeholder is "Enter URL or paste cURL command…". (2) Share renders an Icon plus a visible "Share" text node (src/renderer/src/components/organisms/RequestBar.tsx:339-342) — the reference shows it icon-only. (3) The method trigger uses cx('request-bar**method','method',method) (src/renderer/src/components/organisms/RequestBar.tsx:269); per docs/architecture.md its .request-bar .request-bar**method.method rule (specificity 0,3,0) carries an extra justify-content:center not present in reference .method-select (design/styles.css:749-770; mono / weight 700 / 11.5px / letter-spacing 0.04em / min-width 88px / padding 7px 10px 7px 12px / border --border / bg --bg-elev / --radius), and it deliberately omits `color` so the per-method colour falls through the [data-mstyle] cascade. (4) Save is a labelled .btn-ghost button whose hover treatment targets reference .btn-ghost:hover (design/styles.css:825-828: color --text, border-color --border-strong). (5) The shared Dropdown molecule's open panel — .dropdown-content (src/renderer/src/components/molecules/Dropdown.css:37-51) uses box-shadow var(--shadow-md) and .dropdown-item padding 0.375rem 0.625rem (6px 10px, Dropdown.css:85) with no inter-item gap — vs reference .dropdown (design/styles.css:1536-1566): box-shadow var(--shadow-lg), .dd-item padding 6px 8px, panel gap 1px (border-radius --radius-md, bg --bg-elev, hover bg --bg-hover already match). The "link" Icon already exists in atoms/icons.ts (icons.ts:72). Every required target value already exists as a token (--shadow-lg / --radius-md / --radius / --bg-elev / --bg-hover / --border / --border-strong / --font-mono / --text-muted) per design-fidelity-contract.md — no token additions. The Dropdown is a shared molecule (production consumers: RequestBar + dev-only PrimitivesDemo). Per the docs/architecture.md hazard, .request-bar**method.method must keep omitting `color`, and the seven (0,5,0) [data-mstyle='chip'] per-method counter-rules in RequestBar.css must stay in lockstep with METHODS in httpMethods.ts. The 010 fidelity CT (src/renderer/src/components/organisms/**tests\_\_/RequestBar.ct.tsx) uses computed-style EXACT-equality assertions + a thresholded screenshot diff over a tokens.css + data-mstyle='soft' fixture with the Radix two-step dismiss gate; Shell is the sole writer of data-mstyle.

## 3. Desired Behavior

RequestBar and the shared Dropdown open panel shall match design/reference.html on the five enumerated props, verified by computed-style EXACT-equality in Playwright component tests plus a thresholded screenshot diff (per the 005/010 fidelity approach), with ZERO behaviour change. (1) URL input: restructure into a .url-bar flex container holding a leading aria-hidden link Icon plus the existing input, binding the reference treatment (border 1px --border, background --bg-elev, border-radius --radius, height 32px, padding 0 12px, gap 6px, font-family --font-mono; :focus-within accent border + a 0 0 0 3px accent-14% ring) while keeping the input mono at 12.5px; the input stays bound to RequestSpec.url via updateActiveSpec and the canSend trim guard reads the same value. (2) URL placeholder: exactly "Enter URL or paste cURL command…" — literal text only, with NO cURL parsing or any other behaviour. (3) Share: drop the visible "Share" text node so it renders icon-only; because the visible text previously supplied the accessible name, restore an accessible name (aria-label "Share") so the icon-only button stays named, and keep it the 009 disabled/no-op stub in its final slot. (4) Save: keep its visible "Save" label and bind the reference .btn-ghost rest + hover treatment (rest: color --text-muted, border-color --border, background --bg-elev; hover: color --text, border-color --border-strong). (5) Method trigger: present the reference .method-select treatment (font-family --font-mono, weight 700, font-size 11.5px, letter-spacing 0.04em, padding 7px 10px 7px 12px, min-width 88px, border 1px --border, background --bg-elev, border-radius --radius) and REMOVE the extra justify-content:center; the rule continues to omit `color` so the per-method colour falls through the .method/.{METHOD} cascade — RequestBar never writes data-mstyle, and the seven chip counter-rules stay in lockstep with METHODS. (6) Method dropdown open panel: rebind the shared .dropdown-content to box-shadow var(--shadow-lg), set the inter-item gap to 1px, and set .dropdown-item padding to 6px 8px — keeping border-radius --radius-md, background --bg-elev, and the existing data-highlighted hover background --bg-hover. The shared-panel rebind ripples to dev-only PrimitivesDemo + the visual-snapshot baselines (accepted in scope). All fidelity is rebuilt from semantic classes bound to tokens.css (values from design/styles.css), NEVER by importing design-export cruft (data-om-\*, \_\_OmT, inline styles, tweaks-panel). All 009/010 behaviour is untouched (RequestSpec read/write, onSend, ⌘Enter/⌘S, canSend trim guard, dirty/markClean, per-tab isolation, Shell as sole writer of data-mstyle, the Send ⌘↵ keycap, and Save's labelled state); existing unit + CT suites stay green with new computed-style fidelity CT added; typecheck + lint + build pass.

## 4. Affected Areas

| Area                               | Files                                                                                                                                                                                                   | Impact                                                                                                                                                                                                                                                                                                                        |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| RequestBar markup (presentational) | src/renderer/src/components/organisms/RequestBar.tsx                                                                                                                                                    | Modify — presentational only: wrap the URL input in a .url-bar flex container with a leading aria-hidden <Icon name=link>; set placeholder to the exact reference string; drop the Share visible text node (icon-only) and restore aria-label='Share'; keep the Save label. No logic change.                                  |
| RequestBar styles                  | src/renderer/src/components/organisms/RequestBar.css                                                                                                                                                    | Modify — bind reference values via existing tokens: .url-bar container treatment + focus ring; method-select treatment with the extra justify-content:center removed and color still unset; .btn-ghost Save rest+hover. All rules scoped under .request-bar; the seven chip counter-rules stay in lockstep with METHODS.      |
| Shared Dropdown panel              | src/renderer/src/components/molecules/Dropdown.css                                                                                                                                                      | Modify — rebind the open panel to reference values: .dropdown-content box-shadow var(--shadow-lg) + 1px inter-item gap; .dropdown-item padding 6px 8px. Bounded ripple to dev-only PrimitivesDemo + visual-snapshot baselines.                                                                                                |
| Fidelity + regression tests        | src/renderer/src/components/organisms/**tests**/RequestBar.ct.tsx, src/renderer/src/components/organisms/**tests**/RequestBar.test.tsx, src/renderer/src/components/molecules/**tests**/Dropdown.ct.tsx | Create/extend — add Playwright CT computed-style EXACT-equality assertions on the five enumerated props + a thresholded screenshot diff; reuse the tokens.css + data-mstyle=soft fixture scope and the Radix two-step dismiss gate; rebaseline the Dropdown panel visual snapshot; existing behaviour/unit suites stay green. |

## 5. Acceptance Criteria

Each AC must be testable and unambiguous. **Cover each category that applies. Mark non-applicable categories with "N/A — [reason]".**

### 5.1 Tooling / artifact presence and absence

- [x] **AC-1**: The RequestBar and Dropdown source shall contain no design-export cruft markers such as data-om attributes, \_\_OmT wrappers, or a tweaks-panel.
  > Verification: ! grep -REn 'data-om-|\_\_OmT|tweaks-panel' src/renderer/src/components/organisms/RequestBar.tsx src/renderer/src/components/molecules/Dropdown.tsx
- [x] **AC-2**: The renderer shall provide a link icon in the project icon set for reuse as the URL leading icon.
  > Verification: grep -q "link:" src/renderer/src/components/atoms/icons.ts

### 5.2 Behavior preservation

- [x] **AC-3**: WHEN the user operates any RequestBar control or keyboard shortcut, the RequestBar shall preserve the feature-009/010 behaviour unchanged including the updateActiveSpec write path, the onSend intent, the Cmd-Enter and Cmd-S shortcuts, markClean on Save, and the canSend empty-after-trim guard.
- [x] **AC-4**: WHILE the active tab changes, the RequestBar shall render the newly active tab method and url without leaking the previous tab values.
- [x] **AC-5**: The RequestBar shall keep Shell as the sole writer of the document data-mstyle attribute and shall never write it.
- [x] **AC-6**: WHILE Share is rendered, the RequestBar shall keep it a disabled no-op stub in its final slot.

### 5.3 Behavior change

- [x] **AC-7**: The RequestBar URL input placeholder shall be exactly "Enter URL or paste cURL command…" with no cURL parsing or any other behaviour.
- [x] **AC-8**: WHILE Share is rendered, the RequestBar shall present it icon-only with no visible text node and shall carry an accessible name of Share via aria-label.
- [x] **AC-9**: WHEN Save is hovered, the RequestBar shall present the reference btn-ghost hover treatment of color var(--text) and border-color var(--border-strong), keeping its visible Save text label and the rest treatment of color var(--text-muted), border-color var(--border), background var(--bg-elev).
- [x] **AC-10**: WHILE the method dropdown panel is open, the renderer shall present the reference panel treatment of box-shadow var(--shadow-lg), a 1px inter-item gap, and dropdown-item padding of 6px 8px, keeping border-radius var(--radius-md), background var(--bg-elev), and the existing highlighted hover background var(--bg-hover).
- [x] **AC-11**: WHEN the fidelity suite runs, the enumerated computed-style properties for the url-bar, method-select, Save hover, icon-only Share, and dropdown panel shall be asserted by exact equality in a real browser via Playwright component tests backed by a thresholded screenshot diff within an explicit anti-aliasing pixel-threshold.
- [x] **AC-12**: WHILE the URL field is rendered, the RequestBar shall present it as a url-bar flex container holding a leading aria-hidden link icon and the input bound to the active request url, with the reference border, elevated background, var(--radius) corner, fixed height, horizontal padding, inter-element gap, and mono font from design/styles css, plus an accent border and an accent ring on focus-within.
- [x] **AC-13**: WHILE the method trigger is rendered, the RequestBar shall present the reference method-select treatment of mono font at bold weight with the reference font-size, letter-spacing, padding, and min-width, var(--border) border, var(--bg-elev) background, and var(--radius) corner, with the extra justify-content center removed and color left unset so the per-method colour falls through the method class cascade.

### 5.4 CI / pipeline

N/A — No CI pipeline changes; tests run via existing npm scripts (vitest/playwright), not a new pipeline stage.

### 5.5 Hooks / gates

N/A — No new git hooks or commit gates; the project existing forge gates apply unchanged.

### 5.6 Documentation

- [x] **AC-14**: The touched RequestBar and Dropdown source shall document the url-bar restructure, the icon-only Share with restored aria-label, the method-trigger no-color and no-justify rule, and the shared Dropdown panel rebind in comments.

### 5.7 Hygiene

- [x] **AC-15**: The renderer source shall pass strict type-checking.
  > Verification: npm run typecheck:web
- [x] **AC-16**: The codebase shall pass ESLint without new errors.
  > Verification: npm run lint
- [x] **AC-17**: The project shall build cleanly.
  > Verification: npm run build
- [x] **AC-18**: The touched RequestBar source shall contain no inline style attributes outside comments.
  > Verification: ! grep -REn 'style=[{][{]' src/renderer/src/components/organisms/RequestBar.tsx | grep -vqE ':[[:space:]]_(\*|//|/[_])'
- [x] **AC-19**: The RequestBar and Dropdown unit and component test suites shall pass.
  > Verification: npx vitest run src/renderer/src/components/organisms/**tests**/RequestBar.test.tsx

## 6. Out of Scope

**Coverage rule (v3)**: For each Phase 1.5 finding, the finding either (a) becomes an AC in §5, (b) becomes a Constraint in §7, (c) is explicitly listed here as out of scope, OR (d) is in §9 Risks with documented mitigation. Unlanded finding = hard error — re-verify Phase 1.5 enumeration is complete before saving.

- NOT included: No tokens.css/tokens.json change — every reference value already exists as a token; restoring the un-gated tokens.css .method colour defaults (research hypothesis B, deferred by 010) is NOT in this feature. — F-spec-2
- NOT included: No behaviour change whatsoever — HTTP execution, the response view, RequestSpec read/write semantics, onSend, the Cmd-Enter/Cmd-S shortcuts, dirty/markClean, the canSend guard, and per-tab isolation are all excluded; this is presentational/CSS only.
- NOT included: No cURL behaviour — the URL placeholder mentions cURL as literal text only; no paste-to-import, parsing, or any other cURL handling is implemented.
- NOT included: The Send split-dropdown reference section is DEVIATE/OUT — not implemented in this feature.
- NOT included: No chrome outside the RequestBar and the method Dropdown open panel — Params/Auth/Headers/Body/Tests/Code sub-tabs, {{variable}} highlighting, the environment selector, the command palette, and the app header are untouched; no dark-theme-specific geometry; no repo-wide reformatting.

## 7. Technical Constraints

- Must follow: Only Shell writes documentElement data-mstyle (§4 Never / 009 AC-6)
- Must follow: Never use inline styles — class-based styling via cx() (§4 Never)
- Must follow: Prefer design tokens over literal values (§4 Prefer)
- Must follow: Search before building
- Must follow: Only Shell writes documentElement data-mstyle; the method per-verb colour stays on the .method/.{METHOD} class path and the RequestBar never writes data-mstyle.
- Must follow: Never use inline styles — class-based styling composed with cx(); all geometry and treatment edits land in RequestBar.css, Dropdown.css, and className/markup.
- Must follow: Prefer design tokens over literal values; bind shadow/radius/colour/padding to existing tokens (--shadow-lg, --radius-md, --radius, --bg-elev, --bg-hover, --border, --border-strong, --font-mono, --text-muted); raw px only where no token exists (item padding, panel gap).
- Must follow: Style exclusively via tokens-bound semantic class names; copy the reference VALUES from design/styles.css, never the export code; var(--token) asserts resolves-to-token; never reproduce design-export cruft (data-om-\*, \_\_OmT, inline styles, tweaks-panel).
- Must follow: Scope all RequestBar fidelity CSS under the .request-bar selector; the shared Dropdown panel rebind is the only intentionally cross-component change; keep the seven (0,5,0) [data-mstyle=chip] per-method counter-rules in lockstep with METHODS in httpMethods.ts.
- Must follow: Verify fidelity via computed-style EXACT equality in Playwright CT plus a thresholded screenshot diff; CT fixtures must import tokens.css, set data-mstyle on the host, apply the Radix two-step dismiss gate, baseline the no-reflow check with a non-empty URL, and cover mstyle variants beyond soft.
- Must follow: The change is renderer-only (no Node/Electron) and presentational; reuse the existing link Icon atom and the canonical .method/{METHOD} path; introduce no new tokens, no new colour mechanism, and no behaviour change (addresses research hypotheses A and C, not B).
- Must follow: This feature has design/reference.html, so /breakdown emits a design-manifest plus a static token-provenance check; every token binding must trace to a design/styles.css resolved value.
- Must not break: All feature-009/010 behaviour must not regress — onSend, the Cmd-Enter/Cmd-S shortcuts, the canSend empty-after-trim guard, dirty/markClean, updateActiveSpec, per-tab render isolation, Shell as sole writer of data-mstyle, the Send keycap, and the labelled Save state.

## 8. Open Questions

- **Q-1**: The exact screenshot-diff anti-aliasing pixel-threshold (Playwright toHaveScreenshot threshold + maxDiffPixelRatio) is deferred to /plan; the spec mandates an explicit threshold MUST be set (no eyeballing), mirroring the 010 Q-2 precedent.
- **Q-2**: Runtime-confirm via a design-auditor computed-style + screenshot diff that the method-trigger and Save-hover already meet the design/styles.css targets (010 may have fixed them) before locking those ACs to concrete values; residual drift, if any, is context-only, not a static value gap.
- **DP-data_flow_state-1** [no DP in category data_flow_state]: no relevant decision point for data_flow_state
- **DP-edge_cases-1** [no DP in category edge_cases]: no relevant decision point for edge_cases
- **DP-ui_ux_details-1** [no DP in category ui_ux_details]: no relevant decision point for ui_ux_details
- **DP-breaking_changes-1** [no DP in category breaking_changes]: no relevant decision point for breaking_changes
- **DP-tooling_configuration-1** [no DP in category tooling_configuration]: no relevant decision point for tooling_configuration

## 9. Risks

| Risk                                                                                                                                                                                                              | Likelihood | Impact | Mitigation                                                                                                                                                                                                                                 |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Behaviour paths untouched. Main risk is the shared Dropdown molecule ripple (PrimitivesDemo + visual snapshots) and CT fidelity needing the data-mstyle=soft context (005 fixture-scoping).                       | Med        | Med    | tbd via /plan                                                                                                                                                                                                                              |
| The shared Dropdown panel rebind (shadow/padding/gap) ripples to dev-only PrimitivesDemo and the visual-snapshot baselines, risking an unrelated dropdown regression or a snapshot failure.                       | Med        | Low    | Limit the edit to box-shadow + item padding + panel gap; rebaseline the Dropdown visual snapshot deliberately; the only other prod consumer (PrimitivesDemo) is dev-only and tree-shaken from production.                                  |
| The method-trigger CSS edit could reintroduce the white-on-white chip regression if the seven chip counter-rules drift from METHODS, or kill all per-method colours if a color declaration is accidentally added. | Med        | Med    | Keep color unset on .request-bar\_\_method.method; keep the seven (0,5,0) chip counter-rules in lockstep with METHODS; assert the per-method computed colour across mstyle variants (not just soft) in CT.                                 |
| Method-trigger and Save-hover may already match the reference from 010; locking ACs to assumed values without a runtime check could enshrine a wrong geometry/treatment.                                          | Low        | Med    | Confirm via a design-auditor runtime computed-style + screenshot diff vs design/reference.html before locking those ACs; residual drift, if any, is context-only, not a static value gap.                                                  |
| CT flakiness — the Radix dismiss arm-race, the keycap-mount no-reflow baseline confound, and jsdom inability to resolve computed/pseudo styles can produce intermittent false pass/fail.                          | Med        | Med    | Author fidelity asserts in real-browser Playwright CT; apply the two-step dismiss gate; baseline the no-reflow check with a non-empty URL; clear playwright/.cache + node_modules/.vite + dist when a build/test error names a clean file. |
| Dropping Share's visible text label without restoring an accessible name would break existing getByRole name queries for the Share button.                                                                        | Low        | Med    | Add aria-label Share when going icon-only; run the existing RequestBar CT + unit accessible-name queries as a regression gate.                                                                                                             |
