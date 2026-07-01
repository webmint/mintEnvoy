# Spec: working-tabs-state-machine

**Date**: 2026-06-24
**Status**: Complete
**Author**: Claude + User

## 1. Overview

Build the working-tabs state machine and the RequestSpec domain model for the mintEnvoy HTTP client as a renderer-only zustand slice (tabsStore) plus a TabBar strip that composes the existing Tabs primitive. The slice owns the open-request tabs, the lifecycle state machine (open-from-collection with id-then-url dedupe, new-blank, close with a never-zero invariant, select-active), a per-tab dirty flag with a markClean(tabId) action, and new-tab seed defaults; the TabBar renders/selects/closes tabs and mounts into Shell's existing tabs slot. T4 owns only the slice, the TabBar, and markClean — the sibling trigger sites (collection-list, http-engine, persistence, request editors) are out of scope.

## 2. Current State

Greenfield for tabs state and the request data model — no tabsStore, RequestSpec type, or TabBar exists in the renderer (codebase-memory-mcp returns no such symbols). The substrate T4 composes already exists: (1) the zustand store convention — module-level create<State>((set)=>...) single-instance stores with a Store suffix — established by src/renderer/src/lib/settingsStore.ts and src/renderer/src/lib/toastStore.ts (docs/architecture.md State Management; constitution §3.3); lib/ is a leaf layer that must not import components/. (2) The Tabs primitive at src/renderer/src/components/molecules/Tabs.tsx (feature 002) — controlled, selection-only, hand-rolled WAI-ARIA roving-tabindex; TabsProps = { tabs: TabDescriptor[]; activeId; onChange(id); actions?: ReactNode (rendered OUTSIDE role=tablist); className?; 'aria-label'? } and TabDescriptor = { id; label; badge?: string|number; disabled? } (Tabs.tsx:97-169). It has no per-tab close affordance today. (3) Shell's tabs slot — src/renderer/src/components/organisms/Shell.tsx renders <div className="shell__tabs">{tabs}</div> above PaneSplit when the optional tabs?: ReactNode prop is supplied (ShellProps Shell.tsx:110-140), currently fed only by a test fixture. (4) The renderer test stack — Vitest + @testing-library/react + user-event (jsdom) and Playwright CT — established by feature 001, with tests co-located under **tests**/ split .test.tsx / .ct.tsx. Styling is semantic class names bound to src/renderer/styles/tokens.css (mirrored by design/tokens.json) with a per-component sibling .css and no inline styles. design/reference.html is the visual reference (look only); its existing SEED wiring (design/reference.html:13485) seeds a new request's Accept header to application/json.

## 3. Desired Behavior

Deliver three renderer-only artifacts: a tabsStore slice, the RequestSpec domain model, and a TabBar that composes (and minimally extends) the Tabs primitive, wired into Shell's tabs slot. RequestSpec = { method, url, name, params: Row[], headers: Row[], body: { lang, type, text }, auth } where Row = { enabled: boolean; key: string; value: string; description: string } and auth is a discriminated union on a literal type field with exactly two members in scope: { type: 'none' } and { type: 'bearer'; token: string } (fully typed, narrowed via a type guard; no any). The tabsStore holds { tabs: Tab[]; activeTabId } where Tab = { id; spec: RequestSpec; dirty: boolean } and array order IS tab order. Lifecycle actions: openFromCollection dedupes by collection id first, then by exact verbatim (un-normalized) non-empty url, activating the existing tab on a hit and otherwise appending a new tab; newBlank appends a seeded tab; close removes a tab and, when the active tab is closed, selects the right neighbor (falling back to the left), and when the last tab is closed spawns a fresh seeded Untitled GET so the count is never zero; selectActive sets activeTabId. dirty is a first-class exposed selector; markClean(tabId) clears it; close is the SAME unconditional path for clean and dirty tabs (a dirty tab is dropped silently in T4 — no confirm) and the only close branch is the structural never-zero spawn. New-tab seed defaults: method=GET, empty url, empty name, empty body { lang:'', type:'', text:'' }, dirty=false, auth={ type:'bearer', token:'{{apiKey}}' } with the {{apiKey}} literal verbatim, and headers=[{ enabled:true, key:'Accept', value:'application/json', description:'' }] (Accept value reproduced from the existing prototype SEED at design/reference.html:13485) — auth is NOT mirrored into headers[]. The TabBar composes Tabs: each tab's label is name (if non-empty) else method + ' ' + url (only if url non-empty) else 'Untitled', rendered verbatim (no interpolation), CSS-ellipsis truncated; the dirty marker renders alongside the label via the primitive's badge slot; the '+' new-tab control rides the existing actions slot (no contract change). The Tabs primitive gains an opt-in per-tab close affordance: new optional closable / onClose props default-off so existing selection-only consumers are byte-identical; when closable, an X button renders as a sibling to the role=tab element (a tabIndex=-1 pointer target, NOT an extra roving stop) plus a Delete/Backspace keyboard close path on the focused tab; onClose is signal-only (emits close intent with the tab id, mutates no list — the store owns the lifecycle and the primitive's only post-close job is roving-focus integrity on the next render). All code is renderer-only (no node/electron imports, @renderer alias), styled via tokens-bound semantic classes with no inline styles and reduced-motion-gated animation. Slice behavior and the primitive extension are gated by Vitest + Testing Library tests (and Playwright CT for keyboard/focus); TabBar visual fidelity to design/reference.html is verified manually.

## 4. Affected Areas

| Area                     | Files                                                                                                                                                                                                                                         | Impact                                                                                                                                                                                                                                                                                                          |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| tabsStore slice          | src/renderer/src/lib/tabsStore.ts                                                                                                                                                                                                             | Create new — module-level zustand slice (tabs[], activeTabId) with lifecycle actions (openFromCollection id-then-url dedupe, newBlank, close never-zero + right-then-left neighbor, selectActive), per-tab dirty + markClean(tabId), and seed-default construction; mirrors settingsStore/toastStore convention |
| RequestSpec domain model | src/renderer/src/lib/requestSpec.ts                                                                                                                                                                                                           | Create new — RequestSpec + Row + Auth discriminated-union ({none}                                                                                                                                                                                                                                               | {bearer,token}) types, a type guard for auth narrowing, and a makeBlankRequest() seed factory (GET, empty url/name/body, Accept: application/json header, auth bearer {{apiKey}}); no auth->headers mirroring |
| TabBar organism          | src/renderer/src/components/organisms/TabBar.tsx, src/renderer/src/components/organisms/TabBar.css                                                                                                                                            | Create new — strip UI composing the Tabs primitive; maps tabsStore tabs to TabDescriptors (label precedence name->method+url->Untitled, dirty marker via badge slot, '+' via actions slot), wires selectActive/close/newBlank, styled via tokens-bound semantic classes                                         |
| Tabs primitive extension | src/renderer/src/components/molecules/Tabs.tsx, src/renderer/src/components/molecules/Tabs.css                                                                                                                                                | Modify — add opt-in closable/onClose props (default-off, backward-compatible): per-tab X as a sibling tabIndex=-1 button (not a roving stop) + Delete/Backspace close on the focused tab; onClose signal-only; preserve roving-focus integrity on close re-render                                               |
| Shell tabs-slot wiring   | src/renderer/src/components/organisms/Shell.tsx                                                                                                                                                                                               | Modify — mount the real <TabBar/> into the existing shell tabs slot (replacing the test fixture); no new layout plumbing                                                                                                                                                                                        |
| Slice + component tests  | src/renderer/src/lib/**tests**/tabsStore.test.ts, src/renderer/src/components/organisms/**tests**/TabBar.test.tsx, src/renderer/src/components/molecules/**tests**/Tabs.test.tsx, src/renderer/src/components/molecules/**tests**/Tabs.ct.tsx | Create new / extend — Vitest unit tests for every lifecycle action + dirty/markClean + invariants; TabBar render/select/close tests; closable=true a11y (axe, no interactive nested in role=tab) + closable=false byte-identical regression for the 002 path                                                    |
| PrimitivesDemo gallery   | src/renderer/src/components/PrimitivesDemo.tsx                                                                                                                                                                                                | Modify — register a closable Tabs variant (and/or TabBar) for dev-only manual visual fidelity check against design/reference.html                                                                                                                                                                               |

## 5. Acceptance Criteria

Each AC must be testable and unambiguous. **Cover each category that applies. Mark non-applicable categories with "N/A — [reason]".**

### 5.1 Tooling / artifact presence and absence

- [x] **AC-1**: The renderer shall provide a tabsStore zustand slice module under the lib directory.
  > Verification: test -f src/renderer/src/lib/tabsStore.ts
- [x] **AC-2**: The renderer shall provide a RequestSpec domain-model module under the lib directory.
  > Verification: test -f src/renderer/src/lib/requestSpec.ts
- [x] **AC-3**: The renderer shall provide a TabBar component module with a sibling token-bound stylesheet under the organisms directory.
  > Verification: test -f src/renderer/src/components/organisms/TabBar.tsx && test -f src/renderer/src/components/organisms/TabBar.css
- [x] **AC-4**: The build shall reuse the existing zustand dependency without introducing a new state-management library.
  > Verification: grep -q '"zustand"' package.json

### 5.2 Behavior preservation

- [x] **AC-11**: WHILE the Tabs primitive is rendered without the closable option (its default), the primitive shall behave identically to its prior selection-only contract — no Delete/Backspace close handler, no extra close DOM node, and no additional roving tab stop.
- [x] **AC-12**: The Tabs primitive shall maintain exactly one roving tab stop per tab regardless of the closable option.

### 5.3 Behavior change

- [x] **AC-13**: WHEN openFromCollection is called with a request whose collection id matches an open tab, the tabsStore shall activate that existing tab and shall not append a new tab.
- [x] **AC-14**: WHEN openFromCollection is called and no open tab matches by collection id but an open tab has the same verbatim non-empty url, the tabsStore shall activate that existing tab and shall not append a new tab.
- [x] **AC-15**: IF a tab has an empty url, THEN the tabsStore shall not treat it as a url-dedupe match, so multiple empty-url tabs remain distinct.
- [x] **AC-16**: WHEN newBlank is invoked, the tabsStore shall append a tab seeded with method GET, empty url, empty name, empty body, dirty false, auth of type bearer with token literal {{apiKey}}, and a single enabled Accept header valued application/json, and shall not mirror auth into the headers array.
- [x] **AC-17**: WHEN the last remaining tab is closed, the tabsStore shall spawn a fresh seeded GET tab so the open-tab count is never zero.
- [x] **AC-18**: WHEN the active tab is closed and other tabs remain, the tabsStore shall set the active tab to the right neighbor, or to the left neighbor when the closed tab was the last in order.
- [x] **AC-19**: WHILE a tab is dirty, the tabsStore shall close it through the same unconditional path as a clean tab, discarding its spec without a confirmation prompt.
- [x] **AC-20**: WHEN markClean is called with an open tab id, the tabsStore shall set that tab's dirty flag to false and leave all other tabs unchanged.
- [x] **AC-21**: WHEN selectActive is called with an open tab id, the tabsStore shall set activeTabId to that id.
- [x] **AC-22**: WHERE the Tabs primitive is rendered with closable enabled, the primitive shall render a per-tab close control as a sibling to the role=tab element with tabIndex -1, and shall emit onClose with the tab id when that control is clicked or when Delete or Backspace is pressed on the focused tab.
- [x] **AC-23**: WHEN a focused tab is closed through the Tabs primitive, the primitive shall move roving focus to a neighboring tab on the next render without losing focus or leaving a dangling tabindex, and onClose shall mutate no tab list itself.
- [x] **AC-24**: WHEN the user activates a tab or its close control or the new-tab plus control in the TabBar, the TabBar shall route the gesture to the tabsStore as a select close or new-blank action respectively.
- [x] **AC-25**: WHILE a tab is rendered, the TabBar shall label it with the spec name when non-empty, otherwise the method followed by the url when the url is non-empty, otherwise the literal Untitled, rendered verbatim without interpolation.
- [x] **AC-26**: WHILE a tab is dirty, the TabBar shall render a dirty marker alongside the tab label without replacing the label text.
- [x] **AC-27**: WHEN the application shell renders, the Shell shall mount the TabBar into its tabs slot.

### 5.4 CI / pipeline

N/A — No CI pipeline changes in scope; tests run via existing npm scripts (vitest/playwright), not a new pipeline stage.

### 5.5 Hooks / gates

N/A — No new git hooks or commit gates introduced; the project's existing forge gates apply unchanged.

### 5.6 Documentation

- [x] **AC-28**: The exported tabsStore actions, the RequestSpec, Row, and Auth types, the seed-default factory, and the new Tabs closable and onClose props shall carry documentation comments.
- [x] **AC-29**: The Tabs primitive contract extension shall be recorded in the feature-002 spec lineage as a contract change rather than a silent prop addition.

### 5.7 Hygiene

- [x] **AC-5**: The renderer source shall pass strict type-checking.
  > Verification: npm run typecheck:web
- [x] **AC-6**: The codebase shall pass ESLint without new errors.
  > Verification: npm run lint
- [x] **AC-7**: The project shall build cleanly.
  > Verification: npm run build
- [x] **AC-8**: The tabsStore slice unit suite shall pass.
  > Verification: npx vitest run src/renderer/src/lib/**tests**/tabsStore.test.ts
- [x] **AC-9**: The new tabsStore, requestSpec, and TabBar source shall contain no inline style attributes.
  > Verification: ! grep -REn 'style=[{][{]' src/renderer/src/lib/tabsStore.ts src/renderer/src/lib/requestSpec.ts src/renderer/src/components/organisms/TabBar.tsx | grep -vqE ':[[:space:]]_(\*|//|/[_])'
- [x] **AC-10**: The new renderer modules shall not import the electron or node built-in modules directly.
  > Verification: ! grep -REn "from '(electron|node:)" src/renderer/src/lib/tabsStore.ts src/renderer/src/lib/requestSpec.ts src/renderer/src/components/organisms/TabBar.tsx

## 6. Out of Scope

**Coverage rule (v3)**: For each Phase 1.5 finding, the finding either (a) becomes an AC in §5, (b) becomes a Constraint in §7, (c) is explicitly listed here as out of scope, OR (d) is in §9 Risks with documented mitigation. Unlanded finding = hard error — re-verify Phase 1.5 enumeration is complete before saving.

- NOT included: Request-editing panels — the params/headers/body/auth editors that bind to the active tab's RequestSpec (T4 ships the model + slice they will consume, not the editors). — F-2026-06-24-working-tabs-state-machine-request-data-model-requestspec-14
- NOT included: Real send and save — no http-engine wiring and no persistence; tabs state is in-memory only this release (markClean is exposed for those siblings to call, but the trigger sites are not built here). — F-claude-3
- NOT included: Variable interpolation / {{...}} template resolution — urls, tokens, and headers are stored and displayed verbatim; no resolution at any point in T4. — F-2026-06-24-working-tabs-state-machine-request-data-model-requestspec-14
- NOT included: Auth types beyond none and bearer — basic, apikey, digest, oauth2, awsv4, ntlm, inherit are deferred; the discriminated union is extensible but seeded with only {none} and {bearer,token}. — F-2026-06-24-working-tabs-state-machine-request-data-model-requestspec-14
- NOT included: Auth-to-wire-header derivation — auth is NOT mirrored into headers[]; computing an Authorization header from the auth field is a later concern. — F-2026-06-24-working-tabs-state-machine-request-data-model-requestspec-14
- NOT included: The sibling trigger sites that drive the slice — collection-list calling openFromCollection, http-engine calling markClean on a successful send, and persistence calling markClean on save; T4 owns only the slice, the TabBar, and the markClean action. — F-2026-06-24-working-tabs-state-machine-request-data-model-requestspec-13
- NOT included: Reproducing design/reference.html markup or its generated cruft (data-om-\*, \_\_OmT wrappers, inline styles, tweaks-panel); the reference is for look only, matched via tokens-bound semantic classes. — F-spec-4
- NOT included: Repo-wide reformatting or unrelated housekeeping commits on this feature branch — they pollute the /verify hygiene scope vs the breakdown baseline. — F-memory-2

## 7. Technical Constraints

- Must follow: Mirror the in-repo zustand convention exactly: a single module-level create<State>((set)=>...) instance, state mutated only through store actions, consumed via per-field selectors; tabsStore holds a flat { tabs: Tab[]; activeTabId } where array order IS tab order.
- Must follow: Style exclusively via tokens-bound semantic class names (color/bg/border/text vars, radius/font/shadow scales, per-method colors for any method marker); a per-component sibling .css; no inline styles; animations gated behind prefers-reduced-motion.
- Must follow: Author hygiene/AC verification commands behaviorally or with comment-line stripping so a grep does not self-match JSDoc/comments that quote the forbidden pattern (lesson from feature 002 AC-14).
- Must not break: The opt-in Tabs primitive extension must not break existing selection-only consumers: closable/onClose default-off, with a test proving the 002 path is byte-identical (no Delete handler, no extra DOM node, no extra tab stop).
- Must follow constitution §3.3: zustand store is camelCase + Store suffix → the slice MUST be named tabsStore (not TabsStore/TabSlice), aligning with settingsStore/toastStore.
- Must follow constitution §2.1: tabsStore, requestSpec, and TabBar are renderer-only — no Node or electron imports; outbound HTTP and persistence stay out of the renderer.
- Must follow constitution §2.3: Resolve renderer modules via the @renderer alias, not deep relative paths; lib/ (the store + model) must not import components/.
- Must follow constitution §3.1: Strict mode, no any: RequestSpec is fully typed and the auth field is an exhaustively-typed discriminated union narrowed via a type guard.
- Must follow constitution §3.2: Never swallow errors; handle both success and error paths (e.g. openFromCollection with a malformed/duplicate input, close on a missing id).
- Must follow constitution §3.4: Gate slice + primitive-extension behavior with Vitest + Testing Library (and Playwright CT for keyboard/focus), co-located under **tests**/ split .test.tsx/.ct.tsx — the test stack already established by feature 001.
- Must follow constitution §3.6: One responsibility per function; keep slice actions small (extract past ~40 lines); SOLID/DRY/KISS — favors the flat-array slice over a normalized map.
- Must follow constitution §6.3: Search before building: reuse the existing Tabs primitive, the Icon atom, cx(), and tokens.css; compose the primitive rather than re-rolling tab a11y; introduce no new runtime dependency.

## 8. Open Questions

- **Q-1**: Richer URL-dedupe normalization (single trailing-slash trim, scheme/host lowercasing) is deferred to a later task that operates on RESOLVED urls (T4 compares verbatim un-interpolated templates). Flag for that task: trailing-slash trim is lossy for non-root paths (/users != /users/) and must not collapse them blindly.
- **Q-2**: The RequestSpec serialization JSON shape is a cross-task contract with the out-of-scope persistence task; T4 should pin it (a shared contract test) to avoid rework when persistence lands. Resolved direction: keep RequestSpec a plain serializable object (no class instances/Symbols) so JSON.stringify(tab.spec) round-trips.
- **DP-breaking_changes-1** [no DP in category breaking_changes]: no relevant decision point for breaking_changes — the sole contract change is the opt-in Tabs primitive extension decided under DP-existing_behavior-1, backward-compatible by construction (closable/onClose default-off, test-verified byte-identical to the 002 selection-only path); no other downstream consumer breaks
- **DP-tooling_configuration-1** [no DP in category tooling_configuration]: no relevant decision point for tooling_configuration — the renderer test stack (Vitest + Testing Library + Playwright CT) is already established by feature 001; T4 adds no migration, build-config, or infra change; seed defaults are domain data, not tooling

## 9. Risks

| Risk                                                                                                                                                                       | Likelihood | Impact | Mitigation                                                                                                                                                                                                                                       |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| The per-tab close-X primitive extension breaks the existing roving-tabindex a11y (nested interactive element in role=tab, lost focus on close, or dangling aria-controls). | High       | High   | Spike the extension against the primitive's existing roving-tabindex tests BEFORE building TabBar; X is a sibling tabIndex=-1 button (not a roving stop); add a closable=false byte-identical regression test and an axe pass for closable=true. |
| The RequestSpec serialization shape drifts from the out-of-scope persistence task, forcing rework when persistence lands.                                                  | Med        | Med    | Pin the serialization JSON shape as a shared contract test now; keep RequestSpec a plain serializable object.                                                                                                                                    |
| A stale Vite/Playwright build cache makes a clean source file look broken (false RollupError naming a clean file), derailing diagnosis of the new slice/TabBar tests.      | Med        | Med    | When a build/test error names a clean file as the import source, clear the cache (playwright/.cache, node_modules/.vite, dist) and re-run BEFORE editing source or filing a bug.                                                                 |
| Repo-wide reformatting or housekeeping committed on the feature branch pollutes the /verify hygiene scope and produces false NEEDS-WORK artifacts.                         | Med        | Low    | Keep this branch's commits to the feature's src + test files; avoid prettier --write . and unrelated housekeeping.                                                                                                                               |
