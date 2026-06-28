# Spec: request-bar

**Date**: 2026-06-28
**Status**: Complete
**Design source**: none
**Author**: Claude + User

## 1. Overview

Add a RequestBar organism for the active request tab: a color-coded HTTP-method dropdown (GET/POST/PUT/PATCH/DELETE/OPTIONS/HEAD), a plain URL text input bound to the active tab's RequestSpec.url, and Send/Save/Share actions with ⌘↵ (Send) and ⌘S (Save) shortcuts. The feature reuses the existing 001 Dropdown molecule + Icon atom, the 005 .method/[data-mstyle] color convention, and the 004 tabsStore/RequestSpec model — its only net-new primitive is a generic tabsStore spec-edit action (updateActiveSpec) and a single-source lib/httpMethods.ts. HTTP execution, the response, and {{variable}} highlighting (epic D) are explicitly out of scope.

## 2. Current State

The renderer is an atomic-design system (docs/architecture.md). The active request tab and its RequestSpec already exist but there is no editor for them. tabsStore (src/renderer/src/lib/tabsStore.ts:208-273) holds { tabs: Tab[]; activeTabId } with Tab={id,spec,dirty} and exposes openFromCollection/newBlank/close/selectActive/markClean — markClean(tabId) clears dirty but NO action edits a tab's spec.method/spec.url or sets dirty=true (the write path is absent). RequestSpec (src/renderer/src/lib/requestSpec.ts:68-83) types method as a plain string; no HttpMethod union or method-list constant exists anywhere (CBM-confirmed). The Dropdown molecule (src/renderer/src/components/molecules/Dropdown.tsx:204-282) is a controlled Radix wrapper ({open,onOpenChange,trigger,items,...}, trigger asChild). Per-method color classes (.method/.{METHOD}, plus --m-head/.method.HEAD) live in src/renderer/styles/tokens.css and resolve at runtime against [data-mstyle], which Shell sets on <html> (src/renderer/src/components/organisms/shell/Shell.tsx Effect 1, sole writer). Shell exposes a request-pane slot — <PaneSplit request={panes?.request} response={panes?.response}/> — and App.tsx currently mounts <Shell tabs={<TabBar />} /> with no panes prop (src/renderer/src/App.tsx:22; docs/architecture.md shows a stale no-prop <Shell/>). Organisms are flat (organisms/TabBar.tsx, organisms/Sidebar.tsx; only shell/ nested). The 005 method-pill, 002 Tabs, and Shell global ⌘B shortcut (Shell Effect 4: document keydown + e.preventDefault() + getState()) are the established patterns RequestBar mirrors. Test stack = Vitest + Testing Library (jsdom) + Playwright CT, co-located under __tests__/ split .test.tsx/.ct.tsx.

## 3. Desired Behavior

Deliver a flat organisms/RequestBar.tsx (+ sibling RequestBar.css) mounted into the Shell request pane by editing App.tsx to pass panes={{ request: <RequestBar onSend={...} /> }} on the existing <Shell tabs={<TabBar/>} /> element. Layout is [method ▾][URL][Send] (Postman/Insomnia pattern) plus Save and Share, matched visually to design/reference.html via semantic classes bound to tokens.css with zero inline styles. (1) Method selector: a controlled 001 Dropdown whose trigger is a button styled with the .method/.{METHOD} classes (no second overlay library); items are the 7 methods from a new single-source lib/httpMethods.ts (export const METHODS + export type HttpMethod = typeof METHODS[number]); requestSpec.method is re-pointed from string to HttpMethod (imported from httpMethods). Selecting a method writes it to the active tab. (2) URL field: a single-line plain text <input> bound reactively to the active tab's RequestSpec.url; long URLs scroll horizontally without reflowing the method pill or Send; no var-highlight editor (epic D). (3) Writes go through a NEW generic tabsStore action updateActiveSpec(patch: Partial<RequestSpec>) that shallow-merges the patch into the active tab's spec and sets dirty=true ONLY when a value actually changes (a no-op patch does not flip dirty); it resolves the active tab internally. (4) Send is disabled when the URL is empty-after-trim; otherwise it fires onSend (default no-op) with the active tab identity + current method+url — no HTTP. Save calls markClean(activeTabId) when the tab is dirty and is a no-op when not dirty. Share renders token-styled in its final slot but is wired to a disabled/no-op stub. (5) Keyboard: ⌘↵ routes to the same Send path (subject to the same trim guard) and ⌘S to the same Save path, both acting on the active tab globally regardless of focus, registered via a document keydown listener with e.preventDefault() (⌘S must not trigger native save) and cleaned up on unmount, mirroring Shell Effect 4. RequestBar subscribes to the active tab via per-field tabsStore selectors (mirroring TabBar); switching tabs swaps method+url with no cross-tab bleed. All code is renderer-only (@renderer alias, no Node/Electron). Behavior is gated by Vitest unit tests (updateActiveSpec dirty/no-op/per-tab isolation, trim guard, method-switch independence, markClean-on-Save) and Playwright CT (layout fidelity, disabled Send, ⌘↵/⌘S behavior, method-dropdown dismiss with the Radix two-step gate, per-tab isolation); typecheck + lint + build pass.

## 4. Affected Areas

| Area | Files | Impact |
|------|-------|--------|
| RequestBar organism | src/renderer/src/components/organisms/RequestBar.tsx, src/renderer/src/components/organisms/RequestBar.css | Create new — flat organism: method Dropdown trigger + URL input + Send/Save/Share; per-field tabsStore selectors; ⌘↵/⌘S document-keydown handlers; onSend prop; token-bound semantic classes, zero inline styles |
| HTTP method single-source module | src/renderer/src/lib/httpMethods.ts | Create new — export const METHODS (7 methods, display order) + export type HttpMethod = typeof METHODS[number]; lib-only, no component/store imports |
| RequestSpec model method type | src/renderer/src/lib/requestSpec.ts | Modify — re-point method from string to HttpMethod imported from httpMethods.ts (single source); makeBlankRequest GET seed stays valid |
| tabsStore spec-edit action | src/renderer/src/lib/tabsStore.ts | Modify — add updateActiveSpec(patch: Partial<RequestSpec>) action: shallow-merge into active tab spec, set dirty=true only on actual change, resolve active tab internally; existing actions unchanged |
| App root request-pane wiring | src/renderer/src/App.tsx | Modify — add panes={{ request: <RequestBar onSend={...} /> }} to the existing <Shell tabs={<TabBar/>} /> element; ToastProvider/Shell wiring otherwise unchanged |
| Constitution sole-subscriber rule | constitution.md | Modify — update §4 'TabBar.tsx is the sole subscriber' wording to admit RequestBar as the spec-edit subscriber of tabsStore (documentation-only; no behavior change to TabBar) |
| Unit + component tests | src/renderer/src/components/organisms/__tests__/RequestBar.test.tsx, src/renderer/src/components/organisms/__tests__/RequestBar.ct.tsx, src/renderer/src/lib/__tests__/tabsStore.test.ts | Create new / extend — RequestBar unit (trim guard, method-switch independence, Save dirty/no-op) + CT (layout fidelity, disabled Send, ⌘↵/⌘S, method-dropdown dismiss two-step gate, per-tab isolation); tabsStore.test.ts gains updateActiveSpec cases (dirty-on-change, no-op no-flip, per-tab isolation) |

## 5. Acceptance Criteria

Each AC must be testable and unambiguous. **Cover each category that applies. Mark non-applicable categories with "N/A — [reason]".**

### 5.1 Tooling / artifact presence and absence

- [x] **AC-1**: The renderer shall provide a RequestBar organism module with a sibling token-bound stylesheet under the organisms directory.
  > Verification: test -f src/renderer/src/components/organisms/RequestBar.tsx && test -f src/renderer/src/components/organisms/RequestBar.css
- [x] **AC-2**: The renderer shall provide an httpMethods module under the lib directory exporting the HTTP-method list and the HttpMethod type.
  > Verification: test -f src/renderer/src/lib/httpMethods.ts
- [x] **AC-3**: The build shall reuse the existing Radix and zustand dependencies without adding a new overlay or state-management library.
  > Verification: grep -q '"radix-ui"' package.json && grep -q '"zustand"' package.json

### 5.2 Behavior preservation

- [x] **AC-4**: WHILE the TabBar is rendered, the tabsStore shall expose its existing lifecycle actions (openFromCollection, newBlank, close, selectActive, markClean) with unchanged behavior.
- [x] **AC-5**: WHEN requestSpec.method is narrowed from string to the HttpMethod union, the makeBlankRequest GET seed and all existing spec assignments shall remain valid and continue to type-check.
- [x] **AC-6**: The renderer shall keep Shell as the sole writer of the document data-mstyle attribute.

### 5.3 Behavior change

- [x] **AC-7**: WHEN the user selects a method from the RequestBar method dropdown, the RequestBar shall write that method to the active tab's RequestSpec through updateActiveSpec.
- [x] **AC-8**: WHEN the user edits the RequestBar URL input, the RequestBar shall write the new value to the active tab's RequestSpec url through updateActiveSpec.
- [x] **AC-9**: WHEN updateActiveSpec receives a patch that changes at least one value, the tabsStore shall shallow-merge the patch into the active tab's spec and set that tab dirty.
- [x] **AC-10**: IF updateActiveSpec receives a patch whose values equal the active tab's current spec, THEN the tabsStore shall not set the dirty flag.
- [x] **AC-11**: WHEN the active tab changes, the RequestBar shall render the newly active tab's method and url and shall not leak the previous tab's values.
- [x] **AC-12**: WHILE the URL is empty after trimming, the RequestBar shall render Send disabled and shall not emit a send intent.
- [x] **AC-13**: WHEN Send is activated with a URL that is non-empty after trimming, the RequestBar shall invoke onSend with the active tab identity and the current method and url, and shall not perform any HTTP request.
- [x] **AC-14**: WHILE the active tab is dirty and the user activates Save, the RequestBar shall call markClean for the active tab.
- [x] **AC-15**: IF Save is activated while the active tab is not dirty, THEN the RequestBar shall perform no write and no markClean.
- [x] **AC-16**: WHEN the user presses Cmd-Enter, the RequestBar shall route to the same Send path as the Send button under the same empty-url guard, acting on the active tab regardless of focus.
- [x] **AC-17**: WHEN the user presses Cmd-S, the RequestBar shall route to the Save path and shall call preventDefault so the native save action does not fire.
- [x] **AC-18**: WHEN the user changes the method, the RequestBar shall not modify the URL buffer or its caret position.
- [x] **AC-19**: WHILE Share is rendered, the RequestBar shall present it token-styled in its final action slot wired to a disabled no-op stub.
- [x] **AC-20**: WHILE a URL exceeds the input width, the RequestBar shall scroll it horizontally within the field without reflowing the method pill or Send.
- [x] **AC-21**: WHEN the application shell renders, the App shall mount the RequestBar into the Shell request-pane slot.
- [x] **AC-22**: The RequestBar shall source its method list and HttpMethod type from the lib httpMethods module, which requestSpec also references as its method type.

### 5.4 CI / pipeline

N/A — No CI pipeline changes; tests run via existing npm scripts (vitest/playwright), not a new pipeline stage.

### 5.5 Hooks / gates

N/A — No new git hooks or commit gates; the project's existing forge gates apply unchanged.

### 5.6 Documentation

- [x] **AC-23**: The exported RequestBar props, the updateActiveSpec action, and the METHODS constant and HttpMethod type shall carry documentation comments.
- [x] **AC-24**: The constitution section 4 sole-subscriber rule shall be updated to record RequestBar as the tabsStore spec-edit subscriber.

### 5.7 Hygiene

- [x] **AC-25**: The renderer source shall pass strict type-checking.
  > Verification: npm run typecheck:web
- [x] **AC-26**: The codebase shall pass ESLint without new errors.
  > Verification: npm run lint
- [x] **AC-27**: The project shall build cleanly.
  > Verification: npm run build
- [x] **AC-28**: The new RequestBar and lib source shall contain no inline style attributes.
  > Verification: ! grep -REn 'style=[{][{]' src/renderer/src/components/organisms/RequestBar.tsx | grep -vqE ':[[:space:]]*(\*|//|/[*])'
- [x] **AC-29**: The new renderer modules shall not import the electron or node built-in modules directly.
  > Verification: ! grep -REn "from '(electron|node:)" src/renderer/src/components/organisms/RequestBar.tsx src/renderer/src/lib/httpMethods.ts
- [x] **AC-30**: The RequestBar and tabsStore test suites shall pass.
  > Verification: npx vitest run src/renderer/src/components/organisms/__tests__/RequestBar.test.tsx src/renderer/src/lib/__tests__/tabsStore.test.ts

## 6. Out of Scope

**Coverage rule (v3)**: For each Phase 1.5 finding, the finding either (a) becomes an AC in §5, (b) becomes a Constraint in §7, (c) is explicitly listed here as out of scope, OR (d) is in §9 Risks with documented mitigation. Unlanded finding = hard error — re-verify Phase 1.5 enumeration is complete before saving.

- NOT included: HTTP execution and the response view — Send fires an in-renderer onSend intent only; the engine and response rendering are separate tasks. — F-spec-2
- NOT included: {{variable}} token highlighting, unknown-var flagging, and template interpolation — the URL is a plain bound string; this belongs to epic D (environment-model / variable-interpolation).
- NOT included: Request-editing panels (params / headers / body / auth editors) and request sub-tabs — RequestBar edits only method+url; auth is untouched.
- NOT included: Durable persistence to disk / collections — Save acts on the in-memory spec via markClean only; the persistence port is its own task.
- NOT included: Real Share behavior (copy-as-cURL / link / export) and URL parsing / validation / autocomplete / history — Share is a disabled no-op stub and the URL is a plain string.
- NOT included: Creating organisms/request/ or relocating TabBar — placement stays flat this task; the domain folder is created later when a 2nd request-domain organism crosses the >=2 trigger. — F-constitution-1

## 7. Technical Constraints

- Must follow: Mutate tabsStore state only through store actions; RequestBar writes method+url exclusively via the new updateActiveSpec action and becomes the spec-edit subscriber of tabsStore alongside TabBar.
- Must follow: Reuse the existing Dropdown molecule, Icon atom, cx(), and tokens.css; introduce no new runtime dependency and no second overlay library.
- Must follow: design/reference.html is a look/behavior reference only — never reproduce its markup or generated cruft (data-om-*, __OmT wrappers, inline styles, tweaks-panel); rebuild with semantic class names from each element's role.
- Must follow: Verify RequestBar visual fidelity via tiered checks — computed-style exact equality on enumerated props plus a thresholded screenshot diff in Playwright CT — per the 005 precedent; CT fixtures must import tokens.css, set data-mstyle on the host, and apply the Radix two-step dismiss gate.
- Must not break: The existing TabBar selection/close/new-blank behavior and the tabsStore lifecycle actions must remain unchanged; updateActiveSpec is additive.
- Must follow constitution §2.2: Renderer tier organization: RequestBar is a flat organism (downward-only imports, no sibling-organism import, @renderer alias, no barrel files); the organisms/<domain>/ subfolder is created only at >=2 single-domain components.
- Must follow constitution §5.2: requestSpec stays a pure data module — imported by tabsStore, never by components; RequestBar must reach the method list/type via lib/httpMethods, not via a requestSpec import.
- Must follow constitution §3.4: Gate behavior with Vitest + Testing Library (jsdom) and Playwright CT for focus/keyboard fidelity, co-located under __tests__/ split .test.tsx/.ct.tsx.
- Must follow constitution §2.3: Renderer modules import no Node/Electron APIs and resolve cross-module code via the @renderer alias.

## 8. Open Questions

- **Q-1**: The method-pill trigger's accessible-name handling (mirror 005's aria approach so the method is announced once, not doubled) is a /plan detail; the exact design-reference geometry (heights/padding) is pulled from design/reference.html at /plan.
- **DP-edge_cases-1** [no DP in category edge_cases]: no relevant decision point for edge_cases
- **DP-ui_ux_details-1** [no DP in category ui_ux_details]: no relevant decision point for ui_ux_details
- **DP-tooling_configuration-1** [no DP in category tooling_configuration]: no relevant decision point for tooling_configuration

## 9. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| updateActiveSpec over-dirties: flipping dirty on a no-op patch (same value) would break the non-dirty Save no-op contract. | Med | Med | Set dirty only when a value actually changes; unit-test both no-op-no-flip and change-flips, plus per-tab isolation, before wiring the UI. |
| Narrowing requestSpec.method string->HttpMethod surfaces a hidden non-listed method assignment elsewhere, breaking the build. | Low | Med | CBM-confirmed the only writer is makeBlankRequest seeding GET; the typecheck/build gate catches any stray assignment; lift the type into httpMethods and re-point in one change. |
| CT flakiness: the Radix dismiss arm-race and a missing data-mstyle/tokens context produce intermittent false pass/fail on the method-dropdown and fidelity tests. | Med | Med | Apply the two-step dismiss gate (await animations + yield setTimeout(0)); fixtures import tokens.css and set data-mstyle on the host per the 005 CT lesson. |
| Mount-point drift: docs/architecture.md shows a stale propless <Shell/> while App.tsx actually passes tabs={<TabBar/>}, risking a wrong wiring assumption. | Low | Low | Spec §2 uses the verified App.tsx wiring (add panes onto the existing <Shell tabs={<TabBar/>} /> element); refresh the architecture doc at /finalize. |
| RequestBar as a 2nd tabsStore subscriber over-renders if it subscribes to the whole tabs array instead of the active fields. | Med | Low | Use per-field selectors for the active tab's method+url (mirror TabBar's memoized selector pattern). |
