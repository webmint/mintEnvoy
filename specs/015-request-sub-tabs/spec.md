# Spec: request-sub-tabs

**Date**: 2026-07-06
**Status**: Complete
**Design source**: html:design/reference.html
**Author**: Claude + User

## 1. Overview

RequestSubTabs is a per-request-tab container/switcher for the request pane: a horizontal strip of 6 fixed sub-tabs (Params, Auth, Headers, Body, Tests, Code) with RequestSpec-derived badges that switches which editor panel is visible below. It composes the existing Tabs molecule (002) for the switcher (a11y/keyboard/badge render), owns the 6 mounted tabpanels (mount-all + toggle-visibility to preserve panel state), and is backed by a new activeSubTab field + setActiveSubTab action on tabsStore. It implements no panel body itself — Params/Headers slots receive the existing KVTable (014); the other 4 slots show one shared empty-state until their panels land. This feature also mounts the composed request pane (RequestBar + RequestSubTabs) into the Shell, taking KVTable live through the Params/Headers slots. Visual fidelity to design/reference.html section 6 (Pane tabs) is mandatory.

## 2. Current State

The request pane currently renders only the RequestBar. App.tsx (src/renderer/src/App.tsx:6) composes the shell as Shell tabs={TabBar} panes={{ request: RequestBar }}; Shell (src/renderer/src/components/organisms/shell/Shell.tsx:110 ShellProps.panes) forwards panes to PaneSplit, whose request slot (src/renderer/src/components/organisms/shell/PaneSplit.tsx:49 PaneSplitProps.request?: ReactNode) renders its content without inspection. The Tabs molecule (src/renderer/src/components/molecules/Tabs.tsx:382; TabDescriptor at :135) is a hand-rolled WAI-ARIA, controlled (activeId + onChange), selection-only strip that never renders panels; TabDescriptor already supports badge (string|number), disabled, method, dirty, plus an optional right-aligned actions slot. TabBar (src/renderer/src/components/organisms/TabBar.tsx:112) is the canonical composition template: per-field tabsStore selectors -> useMemo(descriptors) -> Tabs activeId onChange className='tabbar' actions; Tabs.css carries a .tabbar-scoped override block. tabsStore (src/renderer/src/lib/tabsStore.ts) owns tabs: Tab[], activeTabId, and lifecycle actions (openFromCollection, newBlank, close, selectActive, markClean, updateActiveSpec — shallow-merge, no-op when unchanged so dirty never flips spuriously); the Tab record is {id, collectionRequestId, spec, dirty} (makeBlankTab at tabsStore.ts:138) with NO activeSubTab field today. requestSpec (src/renderer/src/lib/requestSpec.ts:70 RequestSpec; Auth union at :63; makeBlankRequest at :124) is a pure data module exposing method/url/params/headers/body/auth. KVTable (src/renderer/src/components/organisms/KVTable.tsx:26) is a self-subscribing organism: KVTable({ field: 'params'|'headers' }) reads the active tab's spec[field] from tabsStore directly and writes via updateActiveSpec; it is built + CT-tested but not yet mounted into the running app. Design tokens live in tokens.css; fidelity targets are pre-resolved in design/styles.css (.pane-tabs / .pane-tab / .badge) and design/design-fidelity-contract.md section 6.

## 3. Desired Behavior

Add a new RequestSubTabs organism at src/renderer/src/components/organisms/RequestSubTabs.tsx (+ sibling RequestSubTabs.css) that composes the Tabs molecule for a 6-sub-tab strip (Params, Auth, Headers, Body, Tests, Code — fixed order, all always visible and switchable, none disabled/hidden). The active sub-tab is per-request-tab state: add activeSubTab (enum 'params'|'auth'|'headers'|'body'|'tests'|'code', default 'params') to the Tab record and a setActiveSubTab(tabId, key) action to tabsStore. RequestSubTabs reads activeTabId + that tab's activeSubTab and renders Tabs activeId={activeSubTab} onChange={key => setActiveSubTab(activeTabId, key)} className='pane-tabs'; it never mutates the RequestSpec. Badges derive read-only from the active RequestSpec (params count, headers count, auth-set) and update reactively when the spec changes; a badge shows only where the spec carries a value (Body/Tests/Code typically none); counts above 99 display as 99+. All 6 tabpanels are mounted at once and hidden via CSS (display toggle), never unmounted, so panel state (KVTable focus/scroll/half-typed row, open inline edits) survives a sub-tab switch. Params and Headers panels are KVTable field='params' and KVTable field='headers'; the other 4 slots show ONE shared neutral empty-state (muted 'Panel not yet available' text via --text-muted) — the same empty-state for all four, not personalized. Each tabpanel carries role='tabpanel' with aria-controls/aria-labelledby linking it to its tab and aria-selected mirroring activeSubTab. RequestSubTabs reacts identically to its own click and to an external setActiveSubTab write. Invalid or absent activeSubTab reads back as 'params' (VALID_KEYS.includes(v) ? v : 'params'); with no active tab the strip renders a neutral empty region without crashing. Visual fidelity matches design/styles.css section 6 exactly in both light and dark themes. Finally, wire the composed request pane into the app: App.tsx replaces panes.request (RequestBar) with the composed pane (RequestBar + RequestSubTabs below it), taking KVTable live through the Params/Headers slots.

## 4. Affected Areas

| Area | Files | Impact |
|------|-------|--------|
| RequestSubTabs component (new) | src/renderer/src/components/organisms/RequestSubTabs.tsx, src/renderer/src/components/organisms/RequestSubTabs.css | Create new — the container/switcher organism composing Tabs; owns the 6 mounted tabpanels + the shared empty-state; sibling CSS carries the .pane-tabs-scoped fidelity override |
| tabsStore + Tab record | src/renderer/src/lib/tabsStore.ts | Add a SubTabKey enum + activeSubTab field (default 'params') to the Tab record (makeBlankTab), and a setActiveSubTab(tabId,key) store action |
| App composition root | src/renderer/src/App.tsx | Replace panes.request (<RequestBar/>) with the composed request pane (RequestBar + RequestSubTabs); this takes KVTable live through the Params/Headers slots |
| Tabs molecule (reused, no change) | src/renderer/src/components/molecules/Tabs.tsx | Composed as-is via activeId/onChange/badge/actions API — no modification; consumed by RequestSubTabs |
| KVTable (mounted live) | src/renderer/src/components/organisms/KVTable.tsx | Mounted into the Params/Headers slots as <KVTable field='params'/> / field='headers'/>; no component change — it goes live through T5d |
| requestSpec (read-only badge source) | src/renderer/src/lib/requestSpec.ts | Read-only source for badge derivation (params/headers count, auth-set); no change |
| Design tokens | src/renderer/src/styles/tokens.css | Consumed by RequestSubTabs.css for the §6 pane-tab fidelity values (--text-muted/--text/--accent/--accent-soft/--bg-active/--border-faint); verify tokens present, no new token expected |
| Tests (new) | src/renderer/src/components/organisms/__tests__/RequestSubTabs.test.tsx, src/renderer/src/components/organisms/__tests__/RequestSubTabs.ct.tsx, src/renderer/src/lib/__tests__/tabsStore.test.ts | Create new — Vitest interaction + Playwright CT (switch/keyboard/per-tab-state/state-preservation/per-theme fidelity/a11y) and a tabsStore setActiveSubTab unit test |

## 5. Acceptance Criteria

Each AC must be testable and unambiguous. **Cover each category that applies. Mark non-applicable categories with "N/A — [reason]".**

### 5.1 Tooling / artifact presence and absence

- [x] **AC-1**: The renderer shall provide a RequestSubTabs container component module under the organisms directory.
  > Verification: test -f src/renderer/src/components/organisms/RequestSubTabs.tsx
- [x] **AC-2**: The RequestSubTabs component shall ship a sibling token-bound stylesheet.
  > Verification: test -f src/renderer/src/components/organisms/RequestSubTabs.css
- [x] **AC-3**: The build shall add no third-party tab library dependency.
  > Verification: ! grep -qE 'react-tabs|@radix-ui/react-tabs' package.json

### 5.2 Behavior preservation

- [x] **AC-4**: WHILE the new activeSubTab field is present on the Tab record, the existing tabsStore consumers TabBar and RequestBar shall continue to behave as before.
- [x] **AC-5**: The RequestSubTabs component shall compose the Tabs molecule through its existing public API without modifying the Tabs selection-only contract.

### 5.3 Behavior change

- [x] **AC-6**: WHEN the user selects a sub-tab by click or by Arrow/Home/End keyboard navigation, the RequestSubTabs component shall make that sub-tab active and show its tabpanel while hiding the others.
- [x] **AC-7**: WHEN a sub-tab is activated, the RequestSubTabs component shall persist the selection only through the setActiveSubTab store action.
- [x] **AC-8**: WHILE two request tabs hold different active sub-tabs, the RequestSubTabs component shall restore each request tab's own active sub-tab when the user switches away and back.
- [x] **AC-9**: WHILE the user switches between sub-tabs, the RequestSubTabs component shall keep all 6 tabpanels mounted and toggle their visibility with CSS so panel state such as input focus, scroll position, and a half-typed row is preserved.
- [x] **AC-10**: WHEN setActiveSubTab is written externally rather than by a click inside RequestSubTabs, the RequestSubTabs component shall update the strip and the visible tabpanel identically to a local click.
- [x] **AC-11**: The Params and Headers sub-tabs shall render the KVTable bound to the respective RequestSpec field.
- [x] **AC-12**: WHILE a sub-tab has no panel supplied, the RequestSubTabs component shall render one shared neutral empty-state tabpanel using muted text so all 4 unbuilt sub-tabs share the same empty-state.
- [x] **AC-13**: The RequestSubTabs component shall render all 6 sub-tabs as reachable, focusable tabs with none disabled or hidden.
- [x] **AC-14**: WHILE mounted, the RequestSubTabs component shall give each tabpanel role tabpanel with aria-controls and aria-labelledby linking it to its tab and aria-selected mirroring the active sub-tab.
- [x] **AC-15**: WHEN a sub-tab badge count exceeds 99, the RequestSubTabs component shall display the badge as 99+.
- [x] **AC-16**: IF the stored active sub-tab value is absent or not a valid sub-tab key, THEN the RequestSubTabs component shall treat the active sub-tab as params.
- [x] **AC-17**: IF there is no active request tab, THEN the RequestSubTabs component shall render a neutral empty region without throwing.
- [x] **AC-18**: The App shall mount the composed request pane of RequestBar above RequestSubTabs into the request pane slot.
- [x] **AC-26**: WHEN the active RequestSpec changes its params headers or auth data, the RequestSubTabs component shall update the corresponding sub-tab badge reactively without a sub-tab switch.
- [x] **AC-27**: WHILE rendered under the light theme or the dark theme, the RequestSubTabs strip shall match the section 6 pane tab computed style targets for both themes.

### 5.4 CI / pipeline

N/A — No CI pipeline changes; tests run via existing npm scripts, not a new pipeline stage.

### 5.5 Hooks / gates

N/A — No new git hooks or commit gates introduced by this feature.

### 5.6 Documentation

- [x] **AC-19**: The exported RequestSubTabs component, the SubTabKey type, and the setActiveSubTab action shall carry documentation comments.

### 5.7 Hygiene

- [x] **AC-20**: The renderer source shall pass strict type-checking.
  > Verification: npm run typecheck:web
- [x] **AC-21**: The codebase shall pass ESLint without new errors.
  > Verification: npm run lint
- [x] **AC-22**: The RequestSubTabs source shall contain no inline style attributes.
  > Verification: ! grep -rEn 'style=[{][{]' src/renderer/src/components/organisms/RequestSubTabs.tsx
- [x] **AC-23**: The RequestSubTabs source shall not import the electron or node modules.
  > Verification: ! grep -rEn "from '(electron|node:)" src/renderer/src/components/organisms/RequestSubTabs.tsx
- [x] **AC-24**: The RequestSubTabs source shall not call updateActiveSpec, keeping sub-tab interaction free of any RequestSpec mutation.
  > Verification: ! grep -q updateActiveSpec src/renderer/src/components/organisms/RequestSubTabs.tsx
- [x] **AC-25**: The RequestSubTabs source shall import no unbuilt panel component, receiving all panels as slot props.
  > Verification: ! grep -rEn 'AuthPanel|BodyEditor|CodePanel|TestsPanel' src/renderer/src/components/organisms/RequestSubTabs.tsx

## 6. Out of Scope

**Coverage rule (v3)**: For each Phase 1.5 finding, the finding either (a) becomes an AC in §5, (b) becomes a Constraint in §7, (c) is explicitly listed here as out of scope, OR (d) is in §9 Risks with documented mitigation. Unlanded finding = hard error — re-verify Phase 1.5 enumeration is complete before saving.

- NOT included: Implementing the Auth, Body, Tests, or Code panel bodies — those are separate features; T5d only provides their slots + shared empty-state
- NOT included: Reorderable / closable / addable sub-tabs, overflow menus, and per-sub-tab context actions — the 6-tab set is fixed
- NOT included: Any RequestSpec mutation from sub-tab interaction — badges are read-only; the only write is setActiveSubTab
- NOT included: Persistence of activeSubTab across app restart — that is T23's job; T5d only puts the field on the Tab record
- NOT included: Lazy / on-demand / code-split panel mounting — decision is mount-all + toggle-visibility to preserve panel state — F-2026-07-05-request-pane-sub-tabs-container-a-per-request-tab-switcher-2
- NOT included: Sub-tab overflow / responsive collapse — the fixed 6 tabs shrink or scroll via the Tabs molecule's existing behavior; no responsive re-layout
- NOT included: Implementing the external open-on-specific-sub-tab jump-flows (collections-tree / history / command-palette, T18/T19/T20) — T5d only reacts to setActiveSubTab writes
- NOT included: Deep-links / URL-scheme sub-tab navigation, a command-palette 'jump to Auth tab' action, and any test-harness/automation API
- NOT included: Reproducing design/reference.html generated cruft (data-om-* attributes, __OmT wrappers, inline styles, tweaks-panel)

## 7. Technical Constraints

- Must follow: Introduce no new runtime dependency: compose the existing Tabs molecule, KVTable, and tabsStore rather than adding a tab library
- Must follow: Never mutate zustand state outside a store action: the activeSubTab write goes through the setActiveSubTab tabsStore action
- Must follow: Keep all 6 tabpanels mounted and toggle visibility via CSS; never unmount inactive panels, so KVTable edit state survives a sub-tab switch
- Must follow: Wire the tabpanel WAI-ARIA relationships: role tabpanel, aria-controls, aria-labelledby, and aria-selected mirroring activeSubTab; do not re-implement the tablist keyboard engine Tabs already provides
- Must follow: Author fidelity CTs by reading the section 6 pane-tab values from design/styles.css at test-writing time, and assert resolved computed styles (not screenshot pixels) so a sub-1-percent color change is caught
- Must follow: Visual fidelity is backed by the design-token provenance gate (design/reference.html present -> /breakdown design-manifest + /implement static token-provenance check)
- Must not break: The additive activeSubTab field on the Tab record must not break the existing tabsStore consumers TabBar and RequestBar
- Must follow constitution §2.2: renderer component tiers flow downward only: organisms to molecules to atoms; no sibling-tier or upward imports
- Must follow constitution §2.1: renderer depends only on browser/React APIs and preload-exposed window globals — never on Node, Electron, or main
- Must follow constitution §2.3: renderer imports cross-module code via the @renderer path alias rather than deep relative paths
- Must follow constitution §3.4: co-located tests under __tests__/ next to the code, split .test.tsx (Vitest) and .ct.tsx (Playwright CT)
- Must follow constitution §3.6: search the codebase for an existing utility/helper/component before writing anything generic

## 8. Open Questions

- **DP-existing_behavior-1** [no DP in category existing_behavior]: no relevant decision point for existing_behavior
- **DP-data_flow_state-1** [no DP in category data_flow_state]: no relevant decision point for data_flow_state
- **DP-edge_cases-1** [no DP in category edge_cases]: no relevant decision point for edge_cases
- **DP-breaking_changes-1** [no DP in category breaking_changes]: no relevant decision point for breaking_changes
- **DP-tooling_configuration-1** [no DP in category tooling_configuration]: no relevant decision point for tooling_configuration

## 9. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| A lazy-mount regression silently breaks panel-state preservation (KVTable remounts on switch, losing focus/edits) | Med | High | The focus-survives-switch CT (focus a Params cell, switch to Headers and back, assert same DOM node keeps focus/value) is the go/no-go gate before wiring all 6 panels |
| A shared/global active-sub-tab index leaks across request tabs (per-tab state bug) | Med | Med | Dedicated A->B->A CT: A on Headers, B on Body, switch A->B->A, assert A's activeSubTab is still headers |
| Fidelity baselines drift (a sub-1-percent color change stays within screenshot tolerance and passes stale) | Med | Med | Assert resolved computed styles vs section 6 values in both themes, reading the numbers from design/styles.css at CT-writing time |
| The additive Tab-record field breaks existing tabsStore consumers | Low | High | Type-check both configs and run the TabBar and RequestBar CTs after the store change |
| Mounting the composed pane into App.tsx and taking KVTable live introduces integration regressions in the running shell | Med | Med | Add a mount/smoke test for the composed request pane and run the full existing suite |
