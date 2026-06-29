# Spec: request-bar-fidelity

**Date**: 2026-06-28
**Status**: Complete
**Design source**: html:design/reference.html
**Author**: Claude + User

## 1. Overview

Close the visual-fidelity gap between the RequestBar organism (feature 009) and design/reference.html's request bar, in BOTH the empty and filled states, with ZERO behaviour change. 009 shipped functionally correct but visually drifted: the bar is too cramped (uniform 24px geometry vs the reference's 32px), the URL input's radius + focus treatment are wrong, the method pill reads as a faint soft chip rather than the reference's bordered method-select with bold coloured text, the active Send lacks the solid-primary weight + ⌘↵ keycap, and Save/Share are bare undersized icons rather than laid-out labelled actions. 010 is a localised RequestBar.css restyle plus small presentational markup edits (visible Save/Share labels, an aria-hidden ⌘↵ keycap), binding to existing tokens.css custom-properties — no token additions, no logic change.

## 2. Current State

RequestBar (src/renderer/src/components/organisms/RequestBar.tsx:105-327 + sibling RequestBar.css) renders the [method ▾][URL][Send/Save/Share] bar wired to tabsStore via per-field selectors (009, Complete). RequestBar.css applies a uniform 24px geometry: .request-bar padding 5px 8px / gap 6px (RequestBar.css:48-57); all controls height 24px with border-radius var(--radius-sm) (5px); .request-bar__url focus sets border-color only, no ring (RequestBar.css:158-161); .request-bar__send is accent-fill weight 500, no shadow and no ⌘↵ element (RequestBar.css:222-246); Save/Share are icon-only buttons (RequestBar.tsx:283-323). The method trigger uses cx('request-bar__method','method',method) (RequestBar.tsx:256) so per-method colour resolves through tokens.css's [data-mstyle='soft'] .method.GET rules — Shell is the sole writer of data-mstyle (default 'soft', settingsStore.ts:65; Shell.tsx Effect 1), so the in-app pill IS coloured (009 AC-6). The reference target values live in design/styles.css: .reqbar gap 8px / padding 12px 16px (770-776), .url-bar height 32px / radius var(--radius) / focus ring box-shadow 0 0 0 3px accent14% (801-816), .btn-primary weight 600 + inset shadow (851-860), .method-select bordered 88px box with bold 11.5px plain-coloured method text (785-799) over un-gated .method.GET{color} (490-516), .kbd ⌘↵ keycap (245-254), .btn-ghost bordered actions (838-849). All radius/colour/shadow/font tokens the reference needs already exist in tokens.css. App.tsx:23 mounts <RequestBar /> (default no-op onSend). Research: research/2026-06-28-requestbar-009-visual-drift.md confirms the drift is token-APPLICATION local to RequestBar.css (not a token gap). The existing CT suite (RequestBar.ct.tsx) covers layout/behaviour but has NO computed-style fidelity assertions; its fixtures already import tokens.css + set data-mstyle='soft' + apply the Radix two-step dismiss gate (the 005 CT-fixture-scoping pattern).

## 3. Desired Behavior

RequestBar shall match design/reference.html's request bar in BOTH the empty and filled states, verified by tier (computed-style EXACT equality on enumerated props in Playwright CT + a thresholded screenshot diff, per the 005 precedent), with ZERO behaviour change. (1) Bar geometry: .request-bar adopts the reference padding/gap and a ~32px control height; controls bind border-radius to var(--radius) (7px) where the reference uses it. (2) URL input: matching radius and a focus treatment that adds the accent ring (box-shadow 0 0 0 3px of an accent-14% mix) alongside the accent border. (3) Method pill: presents the reference's bordered method-select treatment (border, elevated background, --radius, bold ~11.5px coloured method text) via a LOCAL .request-bar__method override of the inherited soft chip — keeping the per-method colour on the existing .method/.{METHOD} class path and NEVER writing data-mstyle (009 AC-6). (4) Send active state: solid-primary fill at weight 600 plus the reference inset-highlight shadow, plus a presentational aria-hidden <kbd> ⌘↵ keycap rendered ONLY in the enabled (canSend) state — display-only, registering no shortcut. (5) Save/Share: laid-out .btn-ghost-style buttons (bordered, ~32px) with VISIBLE 'Save'/'Share' text labels beside their icons; where the visible text supplies the accessible name, the now-redundant aria-label is dropped (no double-labelling); Share stays the 009 AC-19 disabled/no-op stub, labelled and in its final slot. (6) The empty-state Send greyed-disabled appearance is correct canSend-guard behaviour and is preserved, not restyled away. Fidelity is rebuilt with semantic classes bound to tokens.css (values from design/tokens.json), NEVER by importing design-export markup/cruft (data-om-*, __OmT, tweaks-panel). The new restyle is scoped under .request-bar so no other component regresses. All 009 behaviour is untouched (RequestSpec read/write, onSend, ⌘Enter/⌘S, dirty/markClean, canSend trim guard, per-tab isolation, Shell-sole-writer-of-data-mstyle); existing unit + CT tests stay green and new computed-style fidelity CT is added; typecheck + lint + build pass.

## 4. Affected Areas

| Area | Files | Impact |
|------|-------|--------|
| RequestBar styles (geometry + treatment) | src/renderer/src/components/organisms/RequestBar.css | Modify — restyle to reference fidelity using existing tokens: reference padding/gap + ~32px control height; bind --radius (7px) where reference uses it; add URL-input accent focus-ring box-shadow; Send solid-primary weight 600 + inset shadow + .kbd keycap styling; local .request-bar__method override presenting the bordered method-select treatment (no data-mstyle); .btn-ghost-style labelled Save/Share. All rules scoped under .request-bar. |
| RequestBar markup (presentational classNames + labels) | src/renderer/src/components/organisms/RequestBar.tsx | Modify — presentational only: add visible Save/Share text labels beside icons (drop now-redundant aria-label where visible text supplies the accessible name); add an aria-hidden kbd keycap inside Send rendered only in the enabled state; className/structure edits to match the reference. NO logic change — onSend, Cmd-Enter/Cmd-S, canSend, dirty/markClean, updateActiveSpec, per-tab selectors, data-mstyle invariant untouched. |
| RequestBar fidelity + regression tests | src/renderer/src/components/organisms/__tests__/RequestBar.ct.tsx, src/renderer/src/components/organisms/__tests__/RequestBar.stories.tsx, src/renderer/src/components/organisms/__tests__/RequestBar.test.tsx | Create/extend — add Playwright CT computed-style EXACT-equality fidelity assertions on enumerated .request-bar props (heights, radius, focus ring, method-select treatment, Send weight/shadow, labelled actions) + a thresholded screenshot diff; reuse the existing tokens.css + data-mstyle=soft fixture scope and Radix two-step dismiss gate; existing behaviour/layout CT + unit tests must stay green (accessible names Send/Save/Share/GET preserved). |

## 5. Acceptance Criteria

Each AC must be testable and unambiguous. **Cover each category that applies. Mark non-applicable categories with "N/A — [reason]".**

### 5.1 Tooling / artifact presence and absence

- [x] **AC-1**: The renderer shall provide the RequestBar organism module and its sibling stylesheet under the organisms directory.
  > Verification: test -f src/renderer/src/components/organisms/RequestBar.tsx && test -f src/renderer/src/components/organisms/RequestBar.css
- [x] **AC-2**: The RequestBar source shall contain no design-export cruft markers such as data-om attributes, __OmT wrappers, or a tweaks-panel.
  > Verification: ! grep -REn 'data-om-|__OmT|tweaks-panel' src/renderer/src/components/organisms/RequestBar.tsx

### 5.2 Behavior preservation

- [x] **AC-3**: The renderer shall keep Shell as the sole writer of the document data-mstyle attribute, with the RequestBar never writing it.
- [x] **AC-4**: WHILE the active tab changes, the RequestBar shall render the newly active tab's method and url without leaking the previous tab's values.
- [x] **AC-7**: WHEN the user operates any RequestBar control or keyboard shortcut, the RequestBar shall preserve the feature-009 behaviour unchanged including the updateActiveSpec write path, the onSend intent, markClean on Save, and the canSend empty-after-trim guard.

### 5.3 Behavior change

- [x] **AC-5**: WHILE the URL input is rendered it shall bind its border-radius to the var(--radius) token, and WHILE it is focused it shall present the reference accent focus treatment of an accent border plus an accent ring shadow.
- [x] **AC-6**: WHILE the method pill is rendered, the RequestBar shall present the reference bordered method-select treatment of a border, an elevated background, the var(--radius) token, and bold coloured method text via a local request-bar method override, keeping per-method colour on the global method classes.
- [x] **AC-8**: WHILE the RequestBar is rendered, the RequestBar shall apply the reference bar padding and gap and an approximately 32px control height from the design reference, asserted by computed-style equality in Playwright component tests.
- [x] **AC-9**: WHILE Send is enabled the RequestBar shall render Send as a solid-primary fill at the reference font weight with the reference inset-highlight shadow and a visible aria-hidden Cmd-Enter keycap.
- [x] **AC-10**: WHILE Send is disabled the RequestBar shall not render the Cmd-Enter keycap.
- [x] **AC-11**: WHILE Save and Share are rendered the RequestBar shall present them as laid-out bordered actions with visible text labels beside their icons and shall keep Share a disabled no-op stub in its final slot.
- [x] **AC-12**: The RequestBar fidelity styling shall be scoped under the request-bar selector so no other component is restyled.
- [x] **AC-13**: WHEN the fidelity suite runs the enumerated computed-style properties shall be asserted by exact equality in a real browser via Playwright component tests backed by a thresholded screenshot diff within an explicit anti-aliasing pixel-threshold.

### 5.4 CI / pipeline

N/A — No CI pipeline changes; tests run via existing npm scripts (vitest/playwright), not a new pipeline stage.

### 5.5 Hooks / gates

N/A — No new git hooks or commit gates; the project's existing forge gates apply unchanged.

### 5.6 Documentation

- [x] **AC-14**: The touched RequestBar source shall document the request-bar-scoped fidelity treatment, the local method-select override, and the aria-hidden Cmd-Enter keycap rationale in comments.

### 5.7 Hygiene

- [x] **AC-15**: The renderer source shall pass strict type-checking.
  > Verification: npm run typecheck:web
- [x] **AC-16**: The codebase shall pass ESLint without new errors.
  > Verification: npm run lint
- [x] **AC-17**: The project shall build cleanly.
  > Verification: npm run build
- [x] **AC-18**: The touched RequestBar source shall contain no inline style attributes outside comments.
  > Verification: ! grep -REn 'style=[{][{]' src/renderer/src/components/organisms/RequestBar.tsx | grep -vqE ':[[:space:]]*(\*|//|/[*])'
- [x] **AC-19**: The RequestBar unit and component test suites shall pass.
  > Verification: npx vitest run src/renderer/src/components/organisms/__tests__/RequestBar.test.tsx

## 6. Out of Scope

**Coverage rule (v3)**: For each Phase 1.5 finding, the finding either (a) becomes an AC in §5, (b) becomes a Constraint in §7, (c) is explicitly listed here as out of scope, OR (d) is in §9 Risks with documented mitigation. Unlanded finding = hard error — re-verify Phase 1.5 enumeration is complete before saving.

- NOT included: Restoring the un-gated tokens.css .method.GET..OPTIONS{color} default rules (Approach 2 / hypothesis B from the research) is NOT done in 010 — it is a design-system-wide change deferred to a separate follow-up; the in-app pill is already coloured via Shell's default data-mstyle='soft', so 010 needs no tokens.css change. — F-2026-06-28-requestbar-009-visual-drift-4
- NOT included: Any behaviour change whatsoever — HTTP execution, the response view, RequestSpec read/write semantics, the onSend intent, the Cmd-Enter/Cmd-S shortcuts, dirty/markClean, the canSend guard, per-tab isolation — is excluded; 010 is presentational/CSS only.
- NOT included: Chrome outside the 009 RequestBar scope — Params/Auth/Headers/Body/Tests/Code sub-tabs, {{variable}} highlighting, the environment selector, the command palette, and the app header bar — is not touched.
- NOT included: Reproducing design/reference.html markup or its generated export cruft (data-om-* attributes, __OmT wrappers, inline styles, tweaks-panel) — fidelity is rebuilt from semantic classes bound to tokens.css, never by copying the reference DOM.
- NOT included: Separate dark-theme fidelity work — dark rendering is driven by the existing light/dark token pairs in tokens.css; no theme-specific geometry or layout work is in scope.
- NOT included: Repo-wide reformatting or unrelated housekeeping on this feature branch — it pollutes the /verify hygiene scope vs the breakdown baseline (lesson carried from features 001/002/005).

## 7. Technical Constraints

- Must follow: Only Shell.tsx writes documentElement data-mstyle (AC-6 / §4 Never)
- Must follow: Never use inline styles — class-based styling via cx() (§4 Never)
- Must follow: Prefer design tokens over literal style values (§4 Prefer)
- Must follow: Search before building
- Must follow: Style exclusively via tokens-bound semantic class names from tokens.css; no inline styles; bind radius/colour/shadow/font to existing custom-properties (--radius, --accent, --border, --bg-elev, --fs-*); raw px only where no token exists (spacing). Never reproduce design-export markup (data-om-*, __OmT, tweaks-panel).
- Must follow: The fix is localised to RequestBar.css plus presentational RequestBar.tsx className/label edits; every reference value maps to an existing token, so no tokens.css/tokens.json change is required. Reuse the canonical .method/.{METHOD} convention (methodChipClassName, src/renderer/src/components/molecules/Tabs.tsx:117); introduce no new method-colour mechanism and no new runtime dependency.
- Must follow: Scope all new fidelity CSS under the .request-bar selector (mirror the 005 .tabbar-scoping precedent) so the method pill and other .method consumers (TabBar) are not regressed; the method-pill treatment is a local override, never a data-mstyle write.
- Must follow: Verify fidelity via tiered checks per the 005 precedent — computed-style EXACT equality on the enumerated props in Playwright CT (a real browser; jsdom cannot resolve these) plus a thresholded screenshot diff with an explicit anti-aliasing pixel-threshold (no eyeballing). CT fixtures must import tokens.css, set data-mstyle on the host, and apply the Radix two-step dismiss gate.
- Must follow: Where a visible text label supplies a control's accessible name (Save/Share), drop the now-redundant aria-label to avoid double-labelling; the ⌘↵ keycap is decorative and aria-hidden so the Send button's accessible name stays 'Send'. Existing CT/unit accessible-name queries (Send/Save/Share/GET) must still resolve.
- Must not break: All feature-009 behaviour must not regress — RequestSpec read/write, updateActiveSpec, the onSend intent, the Cmd-Enter/Cmd-S shortcut paths, dirty/markClean, the canSend empty-after-trim guard, per-tab render isolation, and Shell as the sole writer of data-mstyle (009 AC-6). The empty-state greyed-disabled Send is correct and preserved, not restyled away.

## 8. Open Questions

- **Q-1**: Exact reference geometry values (control height ~32px, --radius 7px binding, bar padding/gap, focus-ring spread, Send weight/shadow) are pulled from design/styles.css and runtime-confirmed via design-auditor at /plan before the fidelity ACs lock to concrete numbers.
- **Q-2**: The exact screenshot-diff anti-aliasing pixel-threshold is deferred to /plan; the spec mandates an explicit threshold MUST be set (verification = computed-style equality + thresholded diff, not eyeballing), /plan fixes the concrete number (e.g. Playwright toHaveScreenshot threshold + maxDiffPixelRatio), mirroring 005 Q-2.
- **Q-3**: The deferred design-system follow-up — restoring the un-gated tokens.css .method.GET..OPTIONS{color} defaults so the pill colours in no-data-mstyle isolation (CT/stories) — is tracked separately (scope decision: localised-now, file-tokens-follow-up); it is NOT part of 010 and may be filed as its own /research or bug.
- **DP-breaking_changes-1** [no DP in category breaking_changes]: no relevant decision point for breaking_changes
- **DP-existing_behavior-1** [no DP in category existing_behavior]: no relevant decision point for existing_behavior
- **DP-data_flow_state-1** [no DP in category data_flow_state]: no relevant decision point for data_flow_state
- **DP-edge_cases-1** [no DP in category edge_cases]: no relevant decision point for edge_cases
- **DP-tooling_configuration-1** [no DP in category tooling_configuration]: no relevant decision point for tooling_configuration

## 9. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| CT fidelity flakiness: the Radix method-dropdown dismiss arm-race plus a missing data-mstyle/tokens.css context produce intermittent false pass/fail; and jsdom cannot resolve computed/pseudo styles, so a stale CT build cache can mask a clean source as broken. | Med | Med | Author fidelity asserts in Playwright CT (real browser); reuse the established fixture scope (import tokens.css + set data-mstyle='soft' on host) and the two-step dismiss gate; when a build/test error names a clean file, clear playwright/.cache, node_modules/.vite, dist and re-run before editing source (cache-clearing lesson logged 2026-06-24). |
| Locking RequestBar.css to assumed reference values without a runtime check could enshrine a wrong geometry/treatment value — the diagnosis is code-confirmed against design/styles.css but not yet runtime-verified against the rendered reference. | Low | Med | Confirm the exact reference geometry/treatment via a runtime design-auditor screenshot + computed-style diff against design/reference.html (filled state) during /plan or /implement before locking the values; fidelity ACs assert against the confirmed values. |
| Dropping a control's aria-label while adding a visible text label could break existing CT/unit getByRole name queries (Send/Save/Share/GET) if the visible text does not supply an equivalent accessible name. | Low | Med | Ensure the visible label text equals the prior accessible name before removing aria-label; keep the ⌘↵ keycap aria-hidden; run the existing RequestBar CT + unit suites as a regression gate. |
| The local .request-bar__method override must out-specify the tokens.css [data-mstyle='soft'] .method.GET colour rules; a specificity miss could drop the per-method colour or the method-select treatment. | Med | Low | Follow the 009 .request-bar__method.method (0,2,0) specificity precedent; colour stays from the .method.{METHOD} path; assert the computed method-text colour + border treatment in CT. |
