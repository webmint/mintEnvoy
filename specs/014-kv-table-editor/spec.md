# Spec: kv-table-editor

**Date**: 2026-07-04
**Status**: Complete
**Design source**: html:design/reference.html
**Author**: Claude + User

## 1. Overview

Build KVTable, a hand-rolled controlled key-value grid that edits the active request tab's RequestSpec params[] and headers[] (both Row[] of {enabled,key,value,description}). A single reusable component is instanced twice — once bound to params, once to headers — via a 'params'|'headers' field prop. It renders an enabled checkbox, key/value/description mono cells, a hover-revealed delete affordance, and an auto-promoting trailing empty row, and highlights {{variable}} tokens in the key and value cells, flagging unknown ones against the active environment. It reads and writes exclusively through the existing tabsStore.updateActiveSpec action (no local copy), matches design/styles.css to pixel fidelity, and ships built + component-tested in isolation — it is NOT mounted into the running app (the parent pane-tabs container is a separate task). Autocomplete on the value field and any {{variable}} RESOLUTION are out of scope.

## 2. Current State

Greenfield for the request-editor UI. codebase-memory-mcp returns no KVTable, no editable-grid component, and no {{variable}} tokeniser anywhere in src/renderer (0 hits for validVars/envSlice/activeEnv/interpolat). The substrate KVTable consumes exists and is built: (1) the RequestSpec domain model — src/renderer/src/lib/requestSpec.ts:32 exports Row = {enabled:boolean,key:string,value:string,description:string} and RequestSpec.params/headers: Row[] (feature 004), a plain JSON-serializable shape; (2) the tabsStore write path — src/renderer/src/lib/tabsStore.ts exposes updateActiveSpec(patch: Partial<RequestSpec>) which shallow-merges with a strict-=== no-op guard (feature 009), the same seam RequestBar.tsx uses via per-field selectors; (3) design tokens at src/renderer/styles/tokens.css with authoritative resolved values in design/styles.css (.kv block, lines 951-1035) and the fidelity contract at design/design-fidelity-contract.md section 7 Key-Value editor; (4) the renderer test stack — Vitest (jsdom) + Playwright experimental-ct-react (Chromium), tests co-located under __tests__ split .test.tsx/.ct.tsx (feature 001); (5) the adopted radix-ui unified package. Feature 004 §6 explicitly deferred BOTH 'request-editing panels that bind to the active tab RequestSpec' and '{{...}} variable resolution' — this spec builds the former with DISPLAY-ONLY {{variable}} highlighting (never resolution). The env store (validVars, task T14) and the parent pane-tabs container do NOT exist yet.

## 3. Desired Behavior

Deliver one renderer-only component KVTable at src/renderer/src/components/organisms/KVTable.tsx with a sibling KVTable.css, plus a thin ∅-defaulting environment selector at src/renderer/src/lib/envVars.ts. KVTable takes a field prop of 'params' | 'headers'; it reads the active tab's Row[] for that field via a per-field tabsStore selector and, on every edit, computes a fresh Row[] and writes it back via tabsStore.updateActiveSpec({ [field]: nextRows }) — it holds NO local copy, so an external mutation of the array (import-from-cURL replacing params/headers) re-renders reactively without resurrecting stale edits. Rendering (Option A — controlled grid, derived virtual trailing row): a .kv-header label row, then one .kv-row per Row, then exactly one derived virtual trailing empty .kv-row.empty. Each row shows a real input type=checkbox (12px, accent-color var(--accent)) toggling Row.enabled (row gets .disabled at opacity 0.55 when unchecked); three .kv-cell mono inputs for key, value, description; and a hover-revealed 24px .kv-actions slot holding a real button delete control. Auto-promote: typing into the key OR value cell of the virtual trailing row appends a real Row and a new virtual trailing row spawns; toggling the checkbox or editing description alone on the otherwise-empty row does NOT promote. Delete removes that Row via updateActiveSpec; the virtual trailing row has no delete affordance and can never be removed. {{variable}} tokenising is DISPLAY-ONLY: key and value text is parsed for non-greedy shortest {{...}} tokens (trimmed inner text; empty {{}} and unclosed {{ are plain text; keys may contain unicode/dots/dashes, NOT constrained to word chars); each token renders as a .var span (color var(--accent)); a token whose trimmed name is absent from the active validVars set renders .var.missing (color var(--m-delete), line-through dotted) — but ONLY when validVars is non-empty; when validVars is ∅ (env store absent) every token is neutral .var and none are .missing. validVars comes from the new lib/envVars.ts selector, which returns ∅ until env store T14 lands. Keyboard: Tab/Shift-Tab traverse checkbox→key→value→description→next row; Enter in the trailing row's value or description commits and auto-promotes with focus landing in the new row's corresponding cell; focus is NEVER lost on auto-promote or delete (it moves to an adjacent row, never document body). Row type is obtained via a type-only import (import type { Row } from requestSpec) to honor §5.2. Styling is semantic classes bound to tokens.css (values from design/styles.css .kv block) with NO inline styles and none of the design-export cruft (data-om-*, __OmT, inline styles, tweaks-panel). The Row objects written stay plain and JSON-serializable. Paste: a single-line paste is inserted verbatim; a multi-line paste collapses newlines to spaces (no row explosion); a rapid/large paste into the trailing row spawns exactly ONE new trailing row. KVTable is verified by Playwright CT with mock Row[] and is NOT mounted into the app in this feature.

## 4. Affected Areas

| Area | Files | Impact |
|------|-------|--------|
| KVTable component | src/renderer/src/components/organisms/KVTable.tsx, src/renderer/src/components/organisms/KVTable.css | Create new — the controlled key-value grid (Option A) + its sibling token-bound stylesheet; takes a field:'params'|'headers' prop, instanced twice. |
| Variable tokeniser helper | src/renderer/src/lib/varTokens.ts | Create new — pure non-greedy {{...}} tokeniser (empty/unclosed = plain text; unicode/dot/dash keys) returning token spans for display-only highlighting; unit-testable in isolation. |
| Environment validVars selector | src/renderer/src/lib/envVars.ts | Create new — thin ∅-defaulting selector returning the active environment's validVars set; returns ∅ until env store T14 lands (stable seam). |
| KVTable + helper tests | src/renderer/src/components/organisms/__tests__/KVTable.ct.tsx, src/renderer/src/components/organisms/__tests__/KVTable.stories.tsx, src/renderer/src/lib/__tests__/varTokens.test.ts, src/renderer/src/lib/__tests__/envVars.test.ts | Create new — Playwright CT (mock Row[] fixtures) for grid behaviour + fidelity computed-style asserts; Vitest unit suites for the tokeniser edge rules and the ∅-default selector. |
| tabsStore (consumed, unchanged) | src/renderer/src/lib/tabsStore.ts | No change — KVTable reads active-tab Row[] via a per-field selector and writes via the existing updateActiveSpec action; no new store action added. |
| requestSpec (type-only import, unchanged) | src/renderer/src/lib/requestSpec.ts | No change — KVTable does a type-only import of Row (honors §5.2: requestSpec never value-imported by components). |
| Design tokens (consumed, unchanged) | src/renderer/styles/tokens.css | No change — KVTable.css binds semantic .kv classes to existing token custom properties; resolved fidelity values sourced from design/styles.css .kv block. |

## 5. Acceptance Criteria

Each AC must be testable and unambiguous. **Cover each category that applies. Mark non-applicable categories with "N/A — [reason]".**

### 5.1 Tooling / artifact presence and absence

- [x] **AC-1**: The KVTable component shall exist as a single-file component with a sibling token-bound stylesheet under the organisms directory.
  > Verification: test -f src/renderer/src/components/organisms/KVTable.tsx && test -f src/renderer/src/components/organisms/KVTable.css
- [x] **AC-2**: The renderer shall provide a pure variable-tokeniser module under the lib directory.
  > Verification: test -f src/renderer/src/lib/varTokens.ts
- [x] **AC-3**: The renderer shall provide an environment validVars selector module under the lib directory.
  > Verification: test -f src/renderer/src/lib/envVars.ts
- [x] **AC-4**: The build shall introduce no new table, combobox, or autocomplete runtime dependency.
  > Verification: ! grep -qE '(@tanstack/react-table|downshift|react-aria|@react-aria|ariakit|material-react-table|rsuite)' package.json

### 5.2 Behavior preservation

- [x] **AC-5**: WHILE KVTable is not mounted into the application shell this feature, the running application behavior shall remain unchanged.
- [x] **AC-6**: WHEN KVTable writes an edited array via updateActiveSpec with a fresh array reference, the tabsStore shall flip the active tab dirty flag through its existing no-op-guarded merge without modification to the store.
- [x] **AC-7**: The KVTable feature shall add no new tabsStore action and shall not modify the tabsStore or requestSpec modules.

### 5.3 Behavior change

- [x] **AC-8**: WHEN the user types text into the key or value cell of the trailing empty row, KVTable shall append a real row and render a fresh trailing empty row.
- [x] **AC-9**: The KVTable tokeniser shall match the shortest non-greedy delimited token and shall treat an empty token or an unclosed opener as plain text.
- [x] **AC-10**: The KVTable component shall be authored once and instanced twice through a field prop selecting params or headers.
- [x] **AC-11**: The KVTable component shall highlight variable tokens in the key and value cells only and not in the description cell.
- [x] **AC-12**: The KVTable component shall not resolve or substitute variable values and shall render all cell text verbatim.
- [x] **AC-13**: WHEN a row is deleted or the trailing empty row auto-promotes, KVTable shall keep focus on an adjacent cell and shall never move focus to the document body.
- [x] **AC-14**: The KVTable row enabled toggle shall be a real checkbox input and the row delete control shall be a real button element.
- [x] **AC-15**: WHEN the user edits any cell, the KVTable component shall write a new row array for the bound field through updateActiveSpec.
- [x] **AC-16**: WHILE a row enabled toggle is off, the KVTable component shall render that row with the disabled styling and an unchecked checkbox.
- [x] **AC-17**: WHEN the user toggles a row checkbox, the KVTable component shall flip that row enabled flag and write the change through updateActiveSpec.
- [x] **AC-18**: WHEN the user activates a real row delete control, the KVTable component shall remove that row through updateActiveSpec and move focus to an adjacent row.
- [x] **AC-19**: WHILE the active validVars set is non-empty, the KVTable component shall mark a variable token absent from validVars as a missing-variable token and a present one as a known token.
- [x] **AC-20**: WHILE the active validVars set is empty, the KVTable component shall render every variable token as a neutral token and mark none as missing.
- [x] **AC-21**: WHEN the bound array is replaced externally, the KVTable component shall re-render from the new array and shall not retain stale local edits.
- [x] **AC-22**: WHERE a variable token name contains dots dashes or unicode characters, the KVTable component shall compare its trimmed name verbatim against validVars without a word-character restriction.
- [x] **AC-23**: WHEN the user pastes multi-line text into a cell, the KVTable component shall collapse the newlines to spaces and shall not create additional rows.
- [x] **AC-24**: IF a rapid or large paste enters the trailing empty row, THEN the KVTable component shall spawn exactly one new trailing empty row.
- [x] **AC-25**: WHEN the user presses Tab within a row, the KVTable component shall move focus from checkbox to key to value to description and then onward to the next row.
- [x] **AC-26**: IF the user toggles the checkbox or edits the description of an otherwise-empty trailing row, THEN the KVTable component shall not promote that row to a real row.

### 5.4 CI / pipeline

N/A — No CI pipeline changes; tests run via existing npm scripts (vitest/playwright), not a new pipeline stage.

### 5.5 Hooks / gates

N/A — No new git hooks or commit gates; the project's existing forge gates apply unchanged.

### 5.6 Documentation

- [x] **AC-27**: The exported KVTable props the varTokens tokeniser and the envVars selector shall each carry documentation comments.

### 5.7 Hygiene

- [x] **AC-28**: The renderer source shall pass strict web type-checking.
  > Verification: npm run typecheck:web
- [x] **AC-29**: The codebase shall pass ESLint without new errors.
  > Verification: npm run lint
- [x] **AC-30**: The project shall build cleanly.
  > Verification: npm run build
- [x] **AC-31**: The new KVTable source shall contain no inline style attributes.
  > Verification: ! grep -REn 'style=[{][{]' src/renderer/src/components/organisms/KVTable.tsx | grep -vqE ':[[:space:]]*(\*|//|/\*)'
- [x] **AC-32**: The new renderer modules shall not import electron or node built-in modules directly.
  > Verification: ! grep -REn "from '(electron|node:)" src/renderer/src/components/organisms/KVTable.tsx src/renderer/src/lib/varTokens.ts src/renderer/src/lib/envVars.ts
- [x] **AC-33**: The KVTable component and lib unit suites shall pass.
  > Verification: npx playwright test src/renderer/src/components/organisms/__tests__/KVTable.ct.tsx && npx vitest run src/renderer/src/lib/__tests__/varTokens.test.ts src/renderer/src/lib/__tests__/envVars.test.ts

## 6. Out of Scope

**Coverage rule (v3)**: For each Phase 1.5 finding, the finding either (a) becomes an AC in §5, (b) becomes a Constraint in §7, (c) is explicitly listed here as out of scope, OR (d) is in §9 Risks with documented mitigation. Unlanded finding = hard error — re-verify Phase 1.5 enumeration is complete before saving.

- NOT included: Variable RESOLUTION / {{...}} substitution — highlighting is display-only; resolving or substituting variable values stays out of scope (continues feature 004 §6 no-interpolation deferral).
- NOT included: Value-field {{variable}} autocomplete — deferred to its own post-T14 follow-up task that runs the Radix/Downshift/React-Aria build-vs-buy; v1 ships highlight + missing-flag only.
- NOT included: The environment model / validVars store (task T14) — consumed via the thin ∅-defaulting selector, NOT built here.
- NOT included: The parent pane-tabs container (RequestSubTabs / Params-Auth-Headers-Body-Tests-Code strip) — a separate task; KVTable ships independently-mountable and is NOT wired into the running app this feature.
- NOT included: Row reorder / drag handle and bulk enable-disable / select-all — no design surface in the reference; deferred.
- NOT included: Multi-line / expandable value cells, per-row content-type or file-upload values, value masking / secret-hiding, bulk multi-line paste-to-rows, and header/param NAME validation (wire-level validity is the http-engine T10 concern).
- NOT included: The import-from-cURL parse path itself — lives with RequestBar / command-palette; KVTable only renders + edits the arrays correctly when populated externally.

## 7. Technical Constraints

- Must follow: Reproduce design/reference.html via semantic classes bound to tokens.css; never use inline styles (constitution §4 Never Do) and never import the design-export cruft (data-om-* attrs, __OmT wrappers, inline styles, tweaks-panel). Take exact resolved values from design/styles.css (.kv block), NOT tokens.json (reference-only, can drift).
- Must follow: Pixel fidelity to design/styles.css .kv block (0px deviation; treat var(--token) as resolves-to-token, not literal hex), verified by computed-style CT assertions: grid-template-columns 22px 1fr 1fr 1fr 24px; .kv-header height 30px, font 10.5px uppercase letter-spacing 0.04em color var(--text-faint) weight 600; .kv-row min-height 32px border-bottom var(--border-faint) color var(--text); checkbox 12px accent-color var(--accent); .kv-cell padding 6px 10px mono font 12px; .kv-cell.value color var(--text-muted); .var color var(--accent); .var.missing color var(--m-delete) + line-through dotted; .kv-actions display none then flex on :hover; .kv-row.disabled opacity 0.55.
- Must not break: RequestSpec must stay a plain JSON-serializable object (feature 004 Q-2) — KVTable writes plain Row objects only (no class instances, Symbols, or functions on the data shape).
- Must follow constitution §2.2: requestSpec is a pure data module imported by tabsStore, never by components — KVTable obtains the Row type via a type-only import, never a value import.
- Must follow constitution §5.2: Domain invariant: requestSpec stays a pure data module (imported by tabsStore, never by components); KVTable must not value-import it.
- Must follow constitution §3.1: Strict mode, no implicit any — the tokeniser, Row[] transforms, and the params-or-headers field-prop union are fully typed; untyped boundaries narrow rather than cast.
- Must follow constitution §3.3: Naming: KVTable.tsx PascalCase one-per-file + sibling KVTable.css; the lib helpers varTokens/envVars are camelCase modules; tests co-located under __tests__ split .test.tsx/.ct.tsx.
- Must follow constitution §2.1: Renderer-only: no Node or electron imports in KVTable, varTokens, or envVars.
- Must follow constitution §2.3: Resolve cross-module imports via the @renderer alias, not deep relative paths; lib/ must not import components/.
- Must follow constitution §3.2: Boundary lookups degrade gracefully — the validVars selector returns ∅ (never throws) when the env store is absent, and KVTable renders neutral tokens rather than flagging everything missing.

## 8. Open Questions

- **Q-1**: The exact {{variable}} autocomplete combobox composition (reuse the adopted Radix Popover + which headless hook — Downshift useCombobox vs React-Aria useComboBox) is deferred to the post-T14 autocomplete follow-up task; it is data-starved until the env store lands and out of scope here.
- **DP-existing_behavior-1** [no DP in category existing_behavior]: no relevant decision point for existing_behavior
- **DP-ui_ux_details-1** [no DP in category ui_ux_details]: no relevant decision point for ui_ux_details
- **DP-breaking_changes-1** [no DP in category breaking_changes]: no relevant decision point for breaking_changes
- **DP-tooling_configuration-1** [no DP in category tooling_configuration]: no relevant decision point for tooling_configuration

## 9. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Fidelity drift (px, weight, color, letter-spacing) slips past static CSS-vs-styles.css review — the memory lesson is that only runtime getComputedStyle catches it. | Med | High | Add a computed-style CT assertion locking every pinned .kv value across states (default/disabled/hover/var/var-missing); run the runtime design-auditor against the live component; do NOT trust a green static pass. |
| Controlled-input focus/caret management: writing through the store on every keystroke re-renders and can jump the caret or drop focus on auto-promote or delete. | High | High | Spike Option A in isolation first; use stable React keys per row; pin 'focus never lost on auto-promote/delete' + Tab traversal order as required CT scenarios. |
| External-array mutation (import-from-cURL replacing params/headers while a cell is focused) resurrects stale edits or crashes the render. | Med | Med | Option A holds no local copy — derive rows from the store each render; add a CT that replaces the bound array mid-edit and asserts a clean reactive re-render. |
| The validVars ∅-default degradation mis-fires — every {{token}} rendered as missing on a project with no environment. | Med | Med | Explicit CT: validVars ∅ → all tokens neutral .var, zero .var.missing; the selector returns ∅ (never undefined/throw) when the env store is absent. |
| CT fidelity fixture omits the full styling context (tokens.css import, box-sizing, className scope), producing false pass/fail. | Med | Med | Reproduce the full styling context in the fixture (import tokens.css, scope box-sizing:border-box inline, wrap in the production className) per the CT-fixture-scoping memory lesson; do not global-import base.css. |
| Long CT runs stall an /implement subagent at the 600s watchdog. | Low | Med | Run npm run test:ct in the main thread (background bash), apply edits inline, then re-fan the no-tools review panel (implement-CT-watchdog memory lesson). |
