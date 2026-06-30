# Spec: tab-width-cap

**Date**: 2026-06-29
**Status**: Complete
**Design source**: html:design/reference.html
**Author**: Claude + User

## 1. Overview

Add the missing tab-cell width cap (max-width:220px) to the working-tabs TabBar so a tab holds a stable width and an overlong title ellipsis-truncates instead of stretching the tab and pushing the new-tab plus button and overflow actions. This completes the tab-strip fidelity from feature 005: that feature pinned the tab cell gap, padding, and border but omitted the cell max-width, and the current code caps the label rather than the cell (the cap sits on the label at max-width:200px in TabBar.css), diverging from design-fidelity-contract section 5, which places max-width:220px on the design tab cell. The change is pure CSS, tabbar-scoped, with zero behaviour change.

## 2. Current State

TabBar (src/renderer/src/components/organisms/TabBar.tsx:112) renders the working-tabs strip via the shared Tabs molecule (a Tabs element with className tabbar), mapping each store Tab through toDescriptor then deriveLabel (TabBar.tsx:53), which returns a plain string with no length cap. Per docs/architecture.md the tabbar visual contract spans two CSS files: Tabs.css carries the tabbar-scoped override block and TabBar.css carries the strip chrome. The per-tab cell is the tabbar tab-wrapper rule (Tabs.css:421); it sets a gap, a padding, and a right-border but no max-width, it does not shrink, and the tablist is content-width (the tabbar tab-list rule, Tabs.css:504), so each cell sizes to its content and grows with the title, pushing the actions rightward. A divergent cap sits on the label instead (the tabbar tab-label rule at max-width:200px, TabBar.css:88). The base tab-label rule (Tabs.css:196) already carries the nowrap, the overflow-hidden, and the text-overflow-ellipsis declarations, and the capped button (the tabbar tab rule, Tabs.css:493) is flex-filling with a zero min-width. The Playwright CT fidelity suite (Tabs.ct.tsx, established by feature 005) already asserts the tabbar tab-wrapper gap, padding, and border under the TabbarFidelityFixture, which mounts with tokens.css (playwright/index.tsx), TabBar.css, Shell.css, and a soft mstyle context; but no assertion pins the wrapper max-width, and no test pins the label cap.

## 3. Desired Behavior

The working-tabs tab cell shall hold a stable maximum width and truncate an overlong title with an ellipsis. Concretely, the tabbar tab-wrapper rule shall carry max-width:220px (the design tab-cell value from design-fidelity-contract section 5), and the divergent tabbar tab-label cap (max-width:200px in TabBar.css) shall be removed so the single cap lives on the cell, reusing the base tab-label ellipsis rule (Tabs.css:196). With the cell capped, an overlong title shall truncate with an ellipsis while the tab width stays at most 220px, with the plus button, the spacer, and the overflow chevron staying anchored. The change is tabbar-scoped (bare Tabs consumers unchanged) and CSS-only (no JS, markup, descriptor, or a11y change), with zero behaviour change to tab select, close, reorder, the dirty dot, the method chip, and active styling, and with the derived label text unchanged. The fidelity suite shall gain a computed-style assertion that the tabbar tab-wrapper max-width resolves to 220px, plus a no-growth test using a long-title fixture (the tab stays at most 220px, and its label shows an ellipsis). No tooltip and no min-width floor are added.

## 4. Affected Areas

| Area | Files | Impact |
|------|-------|--------|
| Tabs primitive styles (tabbar tab cell) | src/renderer/src/components/molecules/Tabs.css | Modify — add max-width:220px to the tabbar tab-wrapper rule (Tabs.css:421), the design tab cell; tabbar-scoped, with no change to the base Tabs rules. |
| TabBar styles (divergent label cap) | src/renderer/src/components/organisms/TabBar.css | Modify — remove the divergent tabbar tab-label cap (the max-width:200px rule, TabBar.css:88); the base tab-label rule (Tabs.css:196) already supplies the overflow, the ellipsis, and the nowrap, so the cap relocates to the cell without losing truncation. |
| Fidelity + behavior tests | src/renderer/src/components/molecules/__tests__/Tabs.ct.tsx, src/renderer/src/components/molecules/__tests__/Tabs.stories.tsx | Create/extend — add a computed-style assertion that the tabbar tab-wrapper max-width resolves to 220px to the existing wrapper-geometry block, and add a long-title fixture plus a no-growth test (the cell stays at most 220px, with the label showing an ellipsis). Reuse the existing TabbarFidelityFixture styling context (tokens.css, TabBar.css, Shell.css, soft mstyle). |

## 5. Acceptance Criteria

Each AC must be testable and unambiguous. **Cover each category that applies. Mark non-applicable categories with "N/A — [reason]".**

### 5.1 Tooling / artifact presence and absence

- [x] **AC-1**: The Tabs stylesheet shall cap the working-tabs tab-cell wrapper width at 220px.
  > Verification: grep -qE 'max-width:[[:space:]]*220px' src/renderer/src/components/molecules/Tabs.css
- [x] **AC-2**: The TabBar stylesheet shall not set a 200px width cap on the tab label.
  > Verification: ! grep -qE 'max-width:[[:space:]]*200px' src/renderer/src/components/organisms/TabBar.css

### 5.2 Behavior preservation

- [x] **AC-3**: WHILE the Tabs primitive is rendered without the tabbar class, the Tabs primitive shall leave the tab cell uncapped so bare Tabs consumers render unchanged.
- [x] **AC-4**: The TabBar shall keep tab select, close, reorder, the dirty dot, the method chip, and active-tab styling unchanged by the width cap.
- [x] **AC-5**: WHEN the TabBar derives a tab label, the TabBar shall leave deriveLabel and its text output unchanged, altering only how an overlong title is rendered.

### 5.3 Behavior change

- [x] **AC-6**: WHILE a tab is rendered in the TabBar, the tab-cell wrapper shall have a computed max-width of 220px.
- [x] **AC-7**: WHILE a tab title exceeds the capped cell width, the TabBar shall hold the tab at most 220px wide and truncate the title with an ellipsis rather than growing the cell.
- [x] **AC-8**: WHILE multiple long-titled tabs are open, the TabBar shall keep the new-tab plus button, the spacer, and the overflow chevron anchored rather than pushed by growing tabs.
- [x] **AC-9**: WHEN the fidelity suite runs, the suite shall assert the tab-cell max-width by exact computed-style equality to 220px in a real browser via Playwright component tests.

### 5.4 CI / pipeline

N/A — No CI pipeline changes; tests run via the existing npm scripts, not a new pipeline stage.

### 5.5 Hooks / gates

N/A — No new git hooks or commit gates; the project's existing forge gates apply unchanged.

### 5.6 Documentation

- [x] **AC-10**: The new tab-cell max-width rule shall carry a comment that cites design-fidelity-contract section 5, recording that the cap moved off the label onto the cell.

### 5.7 Hygiene

- [x] **AC-11**: The renderer source shall pass strict type-checking.
  > Verification: npm run typecheck:web
- [x] **AC-12**: The codebase shall pass ESLint without new errors.
  > Verification: npm run lint
- [x] **AC-13**: The project shall build cleanly.
  > Verification: npm run build

## 6. Out of Scope

**Coverage rule (v3)**: For each Phase 1.5 finding, the finding either (a) becomes an AC in §5, (b) becomes a Constraint in §7, (c) is explicitly listed here as out of scope, OR (d) is in §9 Risks with documented mitigation. Unlanded finding = hard error — re-verify Phase 1.5 enumeration is complete before saving.

- NOT included: A native title-attribute tooltip showing the full title on truncated tabs; this stays pure overflow rendering, and a discoverability tooltip is a possible later feature.
- NOT included: A min-width floor on tabs; tabs stay content-sized because the contract specifies a maximum only.
- NOT included: Functional tab overflow (tab measurement, a hidden-tab dropdown, scroll-into-view); the overflow chevron stays a static affordance, as before.
- NOT included: Changing deriveLabel or its label-derivation precedence (name then method+url then Untitled); that derived text stays byte-identical, and only overflow rendering changes.
- NOT included: The tabsStore lifecycle (open, dedupe, close never-zero, dirty, markClean); this feature touches only the tabbar tab-cell width CSS and its fidelity test.
- NOT included: Bare Tabs consumers and the request-pane section-tabs consumer; the cap is tabbar-scoped, so other consumers render unchanged.
- NOT included: Reproducing the design reference markup or its generated cruft (data-om attributes, wrapper nodes, inline styles, the tweaks panel); fidelity is matched via tokens-bound semantic classes, copying the values, not the code.

## 7. Technical Constraints

- Must follow: Design Fidelity: match the design-fidelity-contract tab-strip section so the cell carries max-width:220px and the label keeps nowrap, overflow-hidden, and ellipsis with no label cap; assert each token value as resolves-to-token, since the literal is the resolved value.
- Must follow: Style exclusively via tokens-bound semantic class names with no inline styles; keep the cap tabbar-scoped so bare Tabs consumers are not regressed, reusing the existing tabbar-scoping precedent.
- Must not break: Bare Tabs consumers and the selection-only non-closable path must not regress; deriveLabel and its label-derivation precedence and the tabsStore lifecycle stay unchanged, since this is presentation CSS only.
- Must follow constitution §3.6: Search before building and reuse: reuse the base tab-label ellipsis rule (Tabs.css:196) and add only the missing cell cap; write no new truncation CSS.
- Must follow constitution §6.1: Minimal changes: touch only the tabbar tab-cell width cap (the wrapper-rule add plus the label-rule removal) and its fidelity test; do not modify unrelated tab CSS.
- Must follow constitution §3.4: Testing: the cell max-width computed-style assertion must run in Playwright CT because jsdom cannot resolve computed layout; co-locate under the __tests__ folder as a .ct.tsx file, reusing the established fidelity suite.

## 8. Open Questions

- **DP-data_flow_state-1** [no DP in category data_flow_state]: no relevant decision point for data_flow_state
- **DP-breaking_changes-1** [no DP in category breaking_changes]: no relevant decision point for breaking_changes
- **DP-tooling_configuration-1** [no DP in category tooling_configuration]: no relevant decision point for tooling_configuration

## 9. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Removing the tabbar tab-label cap also drops its overflow, ellipsis, and nowrap declarations, but the base tab-label rule (Tabs.css:196) already provides them; if it did not, truncation would silently break. | Low | Low | Confirm the base ellipsis declarations are present before removal; keep the existing label flex and overflow CT assertions green; assert the ellipsis on the long-title fixture. |
| The new cell cap could clip the active accent pseudo-element or the overflow chevron if overflow interacts with the cap. | Low | Med | Rely on the existing overflow-visible rule on the tabbar container; keep the active-pseudo and screenshot CT assertions green; a runtime design-auditor pass confirms no clipping. |
| A short-title CT fixture would never trigger truncation, yielding a false pass on the no-growth assertion. | Med | Low | Add an explicit long-title fixture and assert both the cap and the rendered ellipsis, baselining the width CT with realistic content rather than empty-versus-filled. |
| A future method-chip width change could cause the title to truncate sooner inside the fixed cell. | Low | Low | Accepted; the cell cap is fixed and the label flexes, the chip width is bounded, and the earlier truncation is the intended overflow behaviour. |
