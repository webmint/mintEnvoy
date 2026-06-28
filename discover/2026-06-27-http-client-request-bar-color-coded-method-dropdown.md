# Discovery: HTTP client request bar: color-coded method dropdown, variable-highlighting URL input with unknown-var flagging against active env, and Send/Save/Share actions with keyboard shortcuts; reads/writes active tab RequestSpec

**Date**: 2026-06-27
**Topic**: HTTP client request bar: color-coded method dropdown, variable-highlighting URL input with unknown-var flagging against active env, and Send/Save/Share actions with keyboard shortcuts; reads/writes active tab RequestSpec
**Verdict**: Worth pursuing

## Summary

A RequestBar organism for the active request tab: a color-coded method dropdown (reusing the 001 Dropdown molecule + 005 .method/data-mstyle color tokens), a plain URL input bound to RequestSpec.url, and Send/Save/Share actions with ⌘↵/⌘S shortcuts. The feature is almost pure assembly of existing primitives — Dropdown, RequestSpec model, method-color tokens, and the Shell global-shortcut + per-field-selector patterns are all present and directly reusable, so overall fit is Good. The one real integration gap: the tab store exposes markClean (clear dirty) but NO action to edit the active tab's method/url and set dirty — that write mutator must be added, making effort Medium. Variable-token highlighting is explicitly out of scope (epic D); the URL field is a plain bound string. Recommended direction: add a single generic tabsStore spec-patch action and build RequestBar against it; primary risk is the store-write-path design and the §4 'TabBar is the sole subscriber' / §5.2 'requestSpec never imported by components' rules that constrain how RequestBar reads method/url.

## Prior Art

| Reference | Kind | Relevance | Source |
|---|---|---|---|
| tabsStore (active-tab state + markClean) | pattern | internal — holds active tab + RequestSpec; exposes read (tabs/activeTabId) + markClean, BUT no spec-edit/dirty-set action (gap) | internal:src/renderer/src/lib/tabsStore.ts |
| RequestSpec model (makeBlankRequest, method/url fields) | pattern | internal — RequestSpec type {method,url,name,params,headers,body,auth}; method+url are the fields this feature edits | internal:src/renderer/src/lib/requestSpec.ts |
| Dropdown molecule (Radix, open/onOpenChange) | pattern | internal — reuse for the method selector; no second overlay lib needed | internal:src/renderer/src/components/molecules/Dropdown.tsx |
| method-pill color tokens (.method.* via data-mstyle) | pattern | internal — per-method color classes already exist; consume via .method {METHOD} class, data-mstyle set on <html> by Shell | internal:src/renderer/styles/tokens.css |
| TabBar organism (per-field selectors + stable actions template) | pattern | internal — sibling organism showing the exact zustand subscribe/memoize pattern RequestBar should mirror; lives flat at organisms/ | internal:src/renderer/src/components/organisms/TabBar.tsx |
| Shell global-shortcut pattern (Effect 4: document keydown + preventDefault + getState) | pattern | internal — established global ⌘B shortcut pattern; reuse shape for ⌘↵ Send / ⌘S Save (preventDefault stops native save) | internal:src/renderer/src/components/organisms/shell/Shell.tsx |
| HTTP method color convention (GET green/POST orange/DELETE red) | pattern | industry-standard request-bar UX (Postman/Insomnia); already encoded in project tokens.css .method.* — no new work | https://github.com/postmanlabs/postman-app-support/issues/1337 |
| React global keyboard-shortcut pattern (useEffect+document keydown+preventDefault+metaKey+cleanup) | pattern | canonical ⌘Enter/⌘S handling; matches project Shell Effect 4; preventDefault stops native save | https://devtrium.com/posts/how-keyboard-shortcut |

## Integration Surface

| Touchpoint | Module/file | Why touched |
|---|---|---|
| tabsStore active-tab spec write/read | src/renderer/src/lib/tabsStore.ts | read active tab method+url; REQUIRES a new store action to mutate spec.method/spec.url + set dirty (none exists; markClean clears only) — candidate for reuse-by-extension |
| RequestSpec model | src/renderer/src/lib/requestSpec.ts | method+url field types this feature binds to |
| Dropdown molecule | src/renderer/src/components/molecules/Dropdown.tsx | reuse for method selector |
| method-pill tokens | src/renderer/styles/tokens.css | consume existing .method.* color classes via data-mstyle |
| organism placement (flat) + request-pane mount | src/renderer/src/components/organisms | organisms are FLAT (TabBar.tsx/Sidebar.tsx, only shell/ nested) — RequestBar lands flat organisms/RequestBar.tsx, NOT organisms/request/; mounts into Shell panes.request slot, composed at App root |

## Fit Assessment

| Touchpoint | User expected | Reality (scan) | Effort | Blockers |
|---|---|---|---|---|
| tabsStore active-tab spec write/read | writes go through the existing dirty-flag + markClean path already in the store | store exposes read (tabs/activeTabId) + markClean (clear dirty) ONLY; NO action mutates spec.method/spec.url and NO action sets dirty=true — the edit/dirty-set write path does not exist and must be added | Medium | TabsState has no spec-edit/dirty-set mutator; a new store action (e.g. updateActiveSpec/setMethod+setUrl that patches the active tab spec and flips dirty=true) is required |
| organism placement (flat) + request-pane mount | RequestBar nested under organisms/request/ (domain home), same as TabBar; follow TabBar if it moved | organisms are FLAT (organisms/TabBar.tsx, organisms/Sidebar.tsx); only organisms/shell/ is nested; no organisms/request/ folder exists and TabBar never moved. RequestBar lands flat organisms/RequestBar.tsx matching siblings; mounts into the Shell panes.request slot composed at the App root | Low | none |
| Dropdown molecule | reuse existing 001 Radix Dropdown for method selector | molecules/Dropdown.tsx exports Dropdown/DropdownItem/DropdownLabel/DropdownSeparator, Radix-backed, controlled via open/onOpenChange — directly reusable | Low | none |
| method-pill tokens | consume 005 [data-mstyle] method-color convention | .method.* per-method classes live in tokens.css; data-mstyle is set on <html> by Shell Effect 1 from settingsStore — already wired, RequestBar just applies .method {METHOD} | Low | none |
| RequestSpec model | method+url are RequestSpec fields | RequestSpec = {method,url,name,params,headers,body,auth}; method+url top-level, confirmed via makeBlankRequest | Low | none |
| organism placement (flat) + request-pane mount | RequestBar nested under organisms/request/ (domain home), same as TabBar; follow TabBar if it moved | Constitution §2.2: single-domain components live in organisms/<domain>/ but the subfolder is created ONLY at >=2 components (TabBar/Sidebar are currently flat domain singletons, no organisms/request/ exists). So the belief is a DEFERRED decision, not wrong: if RequestBar makes a 'request' domain reach >=2 with TabBar, create organisms/request/ and move TabBar in; otherwise RequestBar lands flat as another singleton. The /plan stage owns this call. Either way it mounts into the Shell panes.request slot (composed at App root). | Low | placement is a /plan decision (flat singleton vs organisms/request/ at >=2-component trigger, which would relocate TabBar) |

**Overall fit**: Good
**Effort estimate**: Medium
**Rationale**: Almost pure assembly of existing primitives — Dropdown molecule, RequestSpec model, method-color tokens (data-mstyle), and the Shell global-shortcut + per-field-selector patterns all exist and are directly reusable. One real integration gap: the tab store has a clean-side API (markClean) but NO action to edit the active tab's spec.method/url and set dirty — that write mutator must be added (Medium). The user's placement belief (organisms/request/ domain nesting) is slightly off: organisms are flat, so RequestBar lands flat alongside TabBar and mounts into the Shell panes.request slot. No new runtime deps, no second overlay lib.

## Design Options

### Option A: Generic spec-patch store action
- **Shape**:
```
Add updateActiveSpec(patch: Partial<RequestSpec>) to tabsStore: shallow-merge the patch into the active tab's spec and set dirty=true in one action. RequestBar subscribes to active method+url via per-field selectors and calls updateActiveSpec({method}) / updateActiveSpec({url}); Save calls markClean; Send fires a send-intent callback.
```
- **Pros**:
  - single new mutator, minimal store surface
  - extensible to future fields (headers/body/params) with zero new actions
  - one dirty-set site keeps the dirty invariant centralized
  - matches the existing zustand action-only mutation pattern (§4)
- **Cons**:
  - patch is untyped-ish (Partial) — needs a guard to reject unknown keys
  - slightly less explicit than named field actions at call sites
- **Complexity**: Low

### Option B: Field-specific store actions
- **Shape**:
```
Add setActiveMethod(method) and setActiveUrl(url) to tabsStore; each writes its field into the active tab spec and sets dirty=true. RequestBar calls the matching action per control.
```
- **Pros**:
  - explicit, self-documenting call sites
  - each action is independently typed
- **Cons**:
  - store surface grows one action per editable field — does not scale to headers/body later
  - two dirty-set sites to keep consistent
  - more boilerplate for the same effect
- **Complexity**: Low

### Option C: Local draft + commit-on-action
- **Shape**:
```
RequestBar holds local method/url state and only writes to the store on blur/Send/Save (deferred commit), rather than writing on every keystroke.
```
- **Pros**:
  - fewer store writes per keystroke
- **Cons**:
  - breaks reactive dirty-on-edit — tab would not show dirty while typing
  - loses live per-tab sync; external/tab-switch changes can clobber the draft
  - contradicts the stated edge-case + success criteria (edit marks dirty immediately)
  - diverges from the established per-field-selector store pattern
- **Complexity**: High

**Recommended option**: Generic spec-patch store action — Extends the existing internal:src/renderer/src/lib/tabsStore.ts store — which currently covers active-tab read + markClean but NOT spec-edit/dirty-set — with one generic updateActiveSpec(patch) mutator. This is the minimal, KISS/DRY-aligned closure of the only real gap: it keeps all mutation behind a store action (§4), centralizes the dirty-set, scales to later request fields without new actions, and lets RequestBar stay a thin reactive consumer mirroring the TabBar selector pattern. Tradeoff accepted: a small key-allow-list guard on the patch to preserve type safety at the boundary.

## Build vs Buy

| Build | Buy/Adopt |
|---|---|
| Assemble RequestBar from existing internal primitives (Dropdown molecule, RequestSpec model, method-color tokens, Shell shortcut/selector patterns) plus one new tabsStore spec-patch action. No new runtime dependency. | Adopt an external request-bar / form component library or a generic dropdown+input kit. |

**Recommendation**: Build — Every building block already exists in-repo and the only missing piece is a ~10-line store action; an external lib would duplicate the Dropdown molecule, fight the zustand store pattern and tokens.css, and violate the no-second-overlay-lib constraint. Build is strictly cheaper and lower-risk.

## Derisk Plan

1. Spike the tabsStore write action (updateActiveSpec patch + dirty=true) with unit tests for dirty-flip-on-edit, per-tab isolation, and markClean-on-Save BEFORE building the UI
2. Confirm the App-root composition passes panes.request into Shell and how the active-tab context reaches RequestBar (mount point grounding)
3. Resolve placement at /plan: flat organisms/RequestBar.tsx vs organisms/request/ (>=2-component trigger that would relocate TabBar)
4. Resolve how RequestBar gets the method list + RequestSpec type WITHOUT a component->requestSpec import (re-export via tabsStore / type-only / constants module) per §5.2
5. CT-verify ⌘S preventDefault suppresses native save and ⌘↵/⌘S act on the active tab regardless of focus in the Electron renderer

## Constitution Constraints

| Rule | Impact |
|---|---|
| §2.2 Domain placement (>=2-component trigger) | Governs where RequestBar lives: organisms/request/ only if the request domain reaches >=2 components (would also relocate TabBar); else flat organisms/RequestBar.tsx. No barrel/index files. @renderer alias, downward-only imports, no sibling-organism import. |
| §2.2 / §5.2 requestSpec is a pure data module — no component imports | RequestBar (a component) must NOT import requestSpec at runtime; the GET/POST/... method list + RequestSpec type must reach it another way (re-export via tabsStore, a type-only import, or a separate constants module). A naive import of method literals from requestSpec.ts violates this rule. |
| §4 Mutate state only through store actions; tabsStore owns tab lifecycle | RequestBar must write method/url ONLY via a tabsStore action — reinforcing the gap that no spec-edit/dirty-set action exists yet (one must be added). RequestBar also becomes a SECOND tabsStore subscriber, so the extracted rule 'TabBar.tsx is the sole subscriber' needs updating to reflect the spec-edit subscriber. |
| §4 Never use inline styles; prefer design tokens | All RequestBar styling via semantic classes in a sibling .css against tokens.css custom properties; zero inline styles; compose conditional classes with cx(); method color via .method {METHOD} (data-mstyle). |
| §3.4 Co-located tests + §3.3 PascalCase one-per-file | RequestBar.tsx + sibling RequestBar.css; tests under __tests__/ split .test.tsx (Vitest) and .ct.tsx (Playwright CT). |
| §2.1/§2.3 Renderer boundary | Renderer-only feature; no Node/Electron imports; cross-module via @renderer alias. Send fires an in-renderer intent callback only (no IPC/HTTP here). |

## Open uncertainties

[NEEDS CLARIFICATION: integration_points — user-supplied placement guess (confirm via Phase 2 fit-check): active request tab RequestSpec (method+url) already present in renderer tab store — request bar reads/writes it]

## Recommendation

**Action**: Proceed to /specify for the RequestBar feature, making the new tabsStore spec-edit/dirty-set action a first-class acceptance criterion (not an afterthought).
**Next**: Run /specify with the distilled topic below; spec the write-path action + placement + method-type reachability explicitly.

## Next step

Copy the block below into a new /specify session manually. No automated handoff — user controls when /specify runs.

~~~
/specify "RequestBar organism: color-coded method dropdown (reuse 001 Dropdown + 005 data-mstyle), plain URL input bound to RequestSpec.url, Send/Save/Share with ⌘↵/⌘S; add a tabsStore spec-edit+dirty action. No var-highlighting (epic D), no HTTP."

Discovery reference: discover/2026-06-27-http-client-request-bar-color-coded-method-dropdown.md
Key facts:
- Functional scope: RequestBar UI for the active request tab. (1) Method selector: dropdown over GET/POST/PUT/PATCH/DELETE/OPTIONS/HEAD, each method color-coded via the 005 method-pill [data-mstyle] convention; reuses the 001 Dropdown molecule. (2) URL field: plain text input bound to RequestSpec.url (no var-highlight editor — that is epic D). (3) Actions: Send (disabled when url empty; fires a send-intent callback, NO HTTP here), Save (writes via the 004 dirty-flag + markClean path), Share (rendered token-styled in final layout position but wired to disabled/no-op stub — real share deferred). (4) Keyboard: ⌘↵ = Send, ⌘S = Save. Reads/writes only method+url of the active tab RequestSpec; does not touch auth.
- Users: Single local developer/API-tester operating the mintEnvoy desktop renderer. Keyboard-driven (⌘↵ Send, ⌘S Save), mouse for method selection + Share. No multi-user, no auth/identity, no remote/collab surface.
- Success criteria: Layout [method ▾][URL][Send] matches Postman/Insomnia pattern + design reference visually; semantic classes bound to tokens.css, zero inline styles; Share button in final slot disabled/no-op. RequestSpec read: bar renders active tab method+url; tab switch swaps values with no cross-tab bleed. RequestSpec write: url edit + method change write back to active tab only; method pill uses 005 [data-mstyle]. Dirty integration: any method/url edit marks tab dirty via 004; Save (when dirty) persists + markClean clears flag; Save on non-dirty = no-op. Send: disabled when url empty-after-trim, else fires send-intent callback (no HTTP). Shortcuts: ⌘↵ Send + ⌘S Save act on active tab globally; Save respects dirty; trim guard applies to ⌘↵. Overflow: long url scrolls horizontally, method pill+Send do not reflow. Method selector reuses 001 Dropdown (no second overlay lib); icons use existing Icon atom. Tests green: unit (RequestSpec read/write, trim guard, dirty/markClean, method-switch independence) + CT (layout, disabled Send, shortcut behavior, per-tab isolation); typecheck+lint+build pass.
- Recommended option: Generic spec-patch store action
- Open uncertainties: 1 (see discovery doc §Open uncertainties)
~~~

