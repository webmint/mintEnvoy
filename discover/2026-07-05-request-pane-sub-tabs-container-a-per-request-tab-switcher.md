# Discovery: Request-pane sub-tabs container: a per-request-tab switcher strip (Params, Auth, Headers, Body, Tests, Code) with count/indicator badges derived from the active RequestSpec; renders the selected panel into a slot but implements no panel itself.

**Date**: 2026-07-05
**Topic**: Request-pane sub-tabs container: a per-request-tab switcher strip (Params, Auth, Headers, Body, Tests, Code) with count/indicator badges derived from the active RequestSpec; renders the selected panel into a slot but implements no panel itself.
**Verdict**: Worth pursuing

## Summary

T5d (RequestSubTabs) is a per-request-tab container/switcher rendering the 6 fixed sub-tabs (Params, Auth, Headers, Body, Tests, Code) with RequestSpec-derived badges, mounting one slotted panel at a time. Internal-prior-art search found the capability already exists in pieces: molecules/Tabs.tsx (002) is a strip-only controlled switcher with badge + full WAI-ARIA keyboard nav, KVTable (014) is the Params/Headers panel, and requestSpec (004) is the badge data source — so T5d is a thin composition organism, not a fresh build. Fit is Good and effort Low: the only net-new code is a per-tab activeSubTab enum field + setActiveSubTab action on tabsStore, a 6-slot mount-all container that toggles visibility (not unmount) to preserve KVTable edit state, and the tabpanel aria-wiring Tabs does not render. Primary risk is a lazy-mount regression silently breaking panel-state preservation — pinned by a focus-survives-switch CT. Recommended direction: build by composition with zero new dependencies.

## Prior Art

| Reference | Kind | Relevance | Source |
|---|---|---|---|
| molecules/Tabs.tsx (002 tabs-primitive) | pattern | internal — existing tab/sub-tab switcher primitive: TabDescriptor already carries a badge field, roving tabindex, arrow/Home/End keyboard nav, underline active state, badge-fidelity CTs. This IS the switcher+badge capability; T5d composes it, does not rebuild it. | internal:src/renderer/src/components/molecules/Tabs.tsx |
| lib/tabsStore.ts | pattern | internal — per-tab state store; Tab record {id,collectionRequestId,spec,dirty} is where the new activeSubTab enum field lands (no such field today). setActiveSubTab action is added here. | internal:src/renderer/src/lib/tabsStore.ts |
| organisms/KVTable.tsx (014) | pattern | internal — the Params/Headers key-value editor panel that mounts into 2 of T5d's 6 slots; already built, passed in as a slot prop. | internal:src/renderer/src/components/organisms/KVTable.tsx |
| lib/requestSpec.ts (004) | pattern | internal — RequestSpec + Auth types; read-only badge data source (params/headers count, auth-set). Badge values derive from here. | internal:src/renderer/src/lib/requestSpec.ts |
| WAI-ARIA Authoring Practices — Tabs pattern | pattern | Canonical tablist/tab/tabpanel semantics: hide inactive tabpanels via hidden/CSS display:none (not unmount), aria-selected/controls/labelledby wiring. Matches T5d's mount-all + toggle-visibility + a11y-wiring plan; Tabs (002) already implements the roles/keyboard. | https://www.w3.org/WAI/ARIA/apg/patterns/tabs/ |
| react-tabs / Radix Tabs (forceMount / mountMode discussions) | library | Default tab libs UNMOUNT inactive panels (Radix discussion #855 requests opt-in forceMount; react-tabs forceRenderTabPanel). Default behavior would remount KVTable and lose in-progress edit state — evidence AGAINST adopting a tab lib and FOR the custom mount-all container. | https://github.com/radix-ui/primitives/discussions/855 |

## Integration Surface

| Touchpoint | Module/file | Why touched |
|---|---|---|
| molecules/Tabs.tsx | src/renderer/src/components/molecules/Tabs.tsx | existing switcher+badge primitive — candidate for reuse over fresh build; T5d composes it for the HOW (a11y/keyboard/badge render) |
| lib/tabsStore.ts | src/renderer/src/lib/tabsStore.ts | existing per-tab store — add activeSubTab enum field + setActiveSubTab action to the Tab record; T5d reads/writes here |
| organisms/KVTable.tsx | src/renderer/src/components/organisms/KVTable.tsx | existing Params/Headers panel — passed into 2 of 6 slots as a prop; T5d never imports it directly per structural non-goal |
| lib/requestSpec.ts | src/renderer/src/lib/requestSpec.ts | existing RequestSpec/Auth types — read-only badge data source |

## Fit Assessment

| Touchpoint | User expected | Reality (scan) | Effort | Blockers |
|---|---|---|---|---|
| molecules/Tabs.tsx | Reuse the 002 tab/sub-tab primitive (active state, keyboard nav, underline) by composition, not a new tab mechanism | Tabs is a strip-only, CONTROLLED primitive: renders role=tablist + role=tab buttons with roving tabindex + arrow/Home/End nav, emits onChange(id), caller owns activeId. TabDescriptor already supports badge/disabled/dirty. It renders NO tabpanels — T5d owns the 6 panels + aria-controls/labelledby wiring. JSDoc example literally uses id='params'. Exact match to the composition plan; controlled-only fits tabsStore-backed state with zero fork. | Low | none |
| lib/tabsStore.ts | activeSubTab enum field lives on the per-tab record, like the title field; add setActiveSubTab action | Tab record is {id, collectionRequestId, spec, dirty} — no activeSubTab field and no setActiveSubTab action today. Additive change: add one enum field (default 'params') + one action. No migration needed (no persistence yet, T23). | Low | none |
| organisms/KVTable.tsx | KVTable mounts into the Params/Headers slots, passed by parent | KVTable (014) exists as a standalone organism; passed into 2 of 6 slots as a prop. T5d never imports it directly (structural non-goal #8). Clean slot boundary. | Low | none |
| lib/requestSpec.ts | Badges derive read-only from the active RequestSpec (params/headers count, auth-set) | requestSpec.ts (004) exposes RequestSpec + Auth (isBearerAuth, params/headers arrays). Badge derivation is trivial read (spec.params?.length, auth kind). Defensive optional-chaining covers malformed-spec edge case. | Low | none |

**Overall fit**: Good
**Effort estimate**: Low
**Rationale**: T5d is a thin composition organism over already-built primitives. Tabs (002) supplies the switcher HOW (a11y/keyboard/badge render, controlled) with an exact-match API; KVTable (014) supplies the Params/Headers panels; requestSpec (004) supplies badge data; tabsStore holds per-tab state. The only net-new code is the wiring: an activeSubTab enum field + setActiveSubTab action on the Tab record, a 6-slot mount-all container that toggles visibility (not unmount) to preserve panel state, and aria-controls/labelledby tabpanel linkage Tabs does not render. Zero new deps, no fork of any primitive, no migration. Belief and reality align on every touchpoint.

## Design Options

### Option A: Store field on Tab record + mount-all container
- **Shape**:
```
activeSubTab: SubTabKey enum ('params'|'auth'|'headers'|'body'|'tests'|'code', default 'params') as one field on the Tab record in tabsStore, with a setActiveSubTab(tabId,key) action. RequestSubTabs (organism) composes Tabs (molecule) for the strip, and renders all 6 tabpanels mounted, toggling visibility via CSS; reads activeSubTab[activeTabId] as Tabs' controlled activeId.
```
- **Pros**:
  - Rides future persistence (T23) for free — field is on the persisted Tab record
  - Survives tab switches A->B->A by construction (state co-located with the request)
  - Reacts to external setActiveSubTab writes (open-on-specific-sub-tab flows) with no extra wiring
  - Single source of per-tab truth; matches the existing tab title/dirty field pattern
  - Zero new deps; composes Tabs/KVTable/requestSpec
- **Cons**:
  - Touches the shared Tab record type (additive, but a public-shape change)
  - Mount-all keeps all 6 panels in the DOM (acceptable: 2 KVTables + 4 empty)
- **Complexity**: Low

### Option B: Parallel sub-tab store keyed by tabId
- **Shape**:
```
A dedicated store holding Record<tabId, SubTabKey> separate from the Tab record; RequestSubTabs reads/writes it. Tab record stays untouched.
```
- **Pros**:
  - Does not modify the Tab record type
  - Isolates sub-tab concern in its own store
- **Cons**:
  - Two sources of per-tab truth — lifecycle must sync (clean up entries on tab close, or leak)
  - Does NOT ride T23 persistence for free — separate store needs its own persist path
  - External open-on-sub-tab flows must know about a second store
  - More moving parts for no functional gain over the field approach
- **Complexity**: Med

### Option C: Local component state keyed by tabId
- **Shape**:
```
RequestSubTabs holds useState<Record<tabId,SubTabKey>> internally; no store change at all.
```
- **Pros**:
  - Zero store/type changes
  - Simplest to write in isolation
- **Cons**:
  - Loses all sub-tab state on component unmount (pane collapse / remount)
  - No external driver — the users-dimension setActiveSubTab programmatic path (open-on-sub-tab) is impossible
  - No persistence path ever (T23 cannot restore it)
  - Violates the integration_points decision that state lives in tabsStore
- **Complexity**: Low

**Recommended option**: Store field on Tab record + mount-all container — Matches every scoped decision: state co-located on the Tab record in internal:src/renderer/src/lib/tabsStore.ts (rides T23 persistence + survives switches for free), reacts to the external setActiveSubTab driver the users dimension requires, and composes the existing internal:src/renderer/src/components/molecules/Tabs.tsx controlled switcher rather than rebuilding it — so the switcher/badge/keyboard capability is EXTENDED via composition, not fresh-built. The one capability none of the internal hits cover is the per-request-tab active-sub-tab selection + the 6-slot mount-all/toggle-visibility panel container with tabpanel aria-wiring — that is the genuine net-new code. Accepted tradeoff: an additive change to the shared Tab record type and all-6-panels mounted (2 KVTables + 4 empty, DOM cost acceptable). Rejected the parallel store (two truths + no free persistence) and local state (loses state on unmount, no external driver).

## Build vs Buy

| Build | Buy/Adopt |
|---|---|
| Compose molecules/Tabs.tsx (002) for the strip + a new organisms RequestSubTabs owning the 6 mounted tabpanels + an activeSubTab field/action on tabsStore. No new dependency. | Adopt a third-party tab library (react-tabs, Radix Tabs) for the switcher + panel management. |

**Recommendation**: Build — Buy is a net loss here: (1) default tab libs UNMOUNT inactive panels (Radix discussion #855 requests opt-in forceMount; react-tabs needs forceRenderTabPanel), which would remount KVTable on every switch and destroy in-progress edit state — the exact constraint T5d must protect; (2) a new runtime dependency directly violates the zero-new-deps constraint and signals Tabs was not reused; (3) the switcher + WAI-ARIA keyboard + badge capability already exists internally in Tabs (002). Building by composition is both cheaper and constitution-aligned (§3.6 reuse-before-build, §4 prefer composition).

## Derisk Plan

1. Spike the state-preservation CT first: focus a KVTable cell / type a partial row in Params, switch to Headers and back, assert the same DOM node keeps focus/value — this is the go/no-go proof that mount-all+toggle-visibility works before wiring all 6 panels
2. Confirm Tabs (002) controlled activeId + onChange + badge render cleanly drives 6 tabs with per-theme fidelity (assert computed styles vs contract §6 in BOTH light and data-theme=dark) before committing the strip
3. Re-read the §6 Pane tabs values from design/styles.css at CT-writing time (not the spec snapshot) to avoid a stale-baseline fidelity assertion
4. Confirm the additive Tab-record change (activeSubTab field + setActiveSubTab action) does not break existing tabsStore consumers (TabBar, RequestBar) — type-check + run their CTs

## Constitution Constraints

| Rule | Impact |
|---|---|
| §2.2 Renderer Tier Organization | RequestSubTabs is a single-domain organism composing the Tabs molecule — downward organism->molecule import is correct. Place as an organisms domain singleton (like TabBar); create organisms/<domain>/ subfolder only when the request-pane domain reaches >=2 components. |
| §4 Never mutate zustand state outside a store action | The activeSubTab write MUST be a tabsStore action (setActiveSubTab), not a direct state mutation from the component — enforces the store-field design and the external-driver path. |
| §4 Never use inline styles / Prefer design tokens (tokens.css) | Fidelity must be delivered via semantic class names composed with cx() bound to tokens.css — the exported cruft (inline styles, data-om-*, __OmT, tweaks-panel) is explicitly barred from the build; token provenance backs the fidelity ACs. |
| §2.2 Never write documentElement vars/attrs except Shell.tsx | T5d only READS theme tokens (resolved per data-theme set by Shell); it never sets data-theme itself — the per-theme fidelity contract binds T5d's resolved colors, not theme control. |
| §3.6 Search Before Building / Prefer composition | Composing Tabs (002) + KVTable (014) + requestSpec (004) instead of a new switcher/tab-lib satisfies reuse-before-build; a new runtime dep would violate it. |

## Open uncertainties

[NEEDS CLARIFICATION: integration_points — user-supplied placement guess (confirm via Phase 2 fit-check): reuse tab/sub-tab primitive from specs/002-tabs-primitive; sit inside request pane (PaneSplit) from specs/003-app-shell, below RequestBar from specs/009-request-bar]

## Recommendation

**Action**: Proceed to /specify for RequestSubTabs (T5d): build by composition — activeSubTab enum field + setActiveSubTab action on tabsStore, a new organisms RequestSubTabs composing molecules/Tabs.tsx, 6 mount-all tabpanels toggling visibility, badges read from RequestSpec, fidelity bound to tokens.css per contract §6 in both themes.
**Next**: Author the T5d spec with the AC set from success_criteria (per-tab-state CT, reactive badges, state-preservation CT, per-theme fidelity, a11y wiring, empty-slot-full-tab, negative RequestSpec-mutation AC, structural no-import AC).

## Next step

Copy the block below into a new /specify session manually. No automated handoff — user controls when /specify runs.

~~~
/specify "RequestSubTabs (T5d): a per-request-tab sub-tabs container/switcher composing Tabs (002) with RequestSpec-derived badges and 6 mount-all slotted panels, backed by an activeSubTab field on tabsStore; pixel-fidelity to reference.html contract section 6."

Discovery reference: discover/2026-07-05-request-pane-sub-tabs-container-a-per-request-tab-switcher.md
Key facts:
- Functional scope: Per-request-tab container/switcher rendering all 6 fixed sub-tabs (Params, Auth, Headers, Body, Tests, Code) in a strip from day one — visible, switchable, keyboard-nav, per contract §6; matches reference (unbuilt ones NOT hidden). Each sub-tab is ONE slot-condition: mounts the panel if provided, else a neutral empty-state (not four throwaway 'coming soon' components). Params/Headers slots receive KVTable (from 014); Auth/Body/Tests/Code slots empty until T8/T7/Tests/T9 land and pass their panel into the slot with zero T5d change. Badges are independent of panel existence: they read the active RequestSpec (params count, headers count, auth-set indicator) — data already carried by 004/014 — so e.g. Auth badge can show 'set' before AuthPanel exists. Net: 6 sub-tabs always visible; 2 slots wired (KVTable x2); 4 empty-state; panels self-insert later.
- Users: Human end-user (developer building/testing HTTP requests) is the SOLE interactive consumer — click/keyboard switch, read badges. Downstream panels (T7 Body/T8 Auth/T9 Code) + 003 shell are COMPOSITION consumers (supply slots / host T5d), not runtime drivers. BUT one programmatic driver in v1: the setActiveSubTab store action. active-sub-tab lives in tabsStore as a PUBLIC action, so selection can be driven programmatically, not only by a click in T5d. Realistic v1 caller: 'open request in tab' flows (collections-tree/history/command-palette, T18/T19/T20) may open a request on a specific sub-tab by writing setActiveSubTab directly. So T5d is NOT the sole writer of its own state — it's a VIEW over a store field that can change externally, and must REACT to external setActiveSubTab (strip + visible panel update) exactly as to its own click (same invariant as KVTable reacting to external RequestSpec mutation). Scope line: T5d IN for reacting to ANY activeSubTab change (own click OR external write); OUT for implementing the jump-flows themselves (live in T18/T19/T20). Explicitly OUT of v1: deep-links/URL-scheme sub-tab nav (no URL routing in local app); command-palette 'jump to Auth tab' action (future consumer, would just call setActiveSubTab — T5d reactivity ready but doesn't build it); any test-harness/automation API (local few-devs app, CTs drive component directly).
- Success criteria: (1) all 6 sub-tabs render + switch via click AND keyboard (arrows/Home/End), active state per-request-tab. Split out: 'survives A->B->A' gets own CT with explicit assert (two tabs, A on Headers, B on Body, switch A->B->A, assert A's activeSubTab==='headers') — catches per-tab-vs-global-state bug. (2) badges reflect live RequestSpec counts (params/headers/auth-set); hard AC = mutate RequestSpec (add a param) -> badge count updates REACTIVELY without a sub-tab switch (not read-once-on-mount). (3) CRITICAL: Params/Headers show KVTable, other 4 empty-state, switch preserves KVTable state proven by: focus a cell/type partial row in Params -> switch Headers -> back -> assert focus/input survived (same DOM node) — defends mount-all vs lazy-mount regression. (4) visual fidelity: computed-style CT vs contract §6 values, EXACT equality for discrete tokens (color/weight/radius = token-resolved exact, ±1px only for subpixel), in BOTH themes (assert under data-theme='dark' too); read §6 numbers from styles.css at CT-writing time not spec snapshot (staleness). (5) a11y: axe zero-violations on mounted T5d, PLUS CT axe can't catch: aria-selected tracks activeSubTab on switch, aria-controls/aria-labelledby point to real ids. (6) empty-slot sub-tabs are FULL tabs NOT disabled — assert all 6 reachable/focusable and unbuilt 4 render valid empty-state tabpanel (guards §6 fixed-6-set vs 'disable unbuilt' shortcut). (7) NEGATIVE AC: sub-tab interaction mutates RequestSpec zero times (spy updateActiveSpec; only write is setActiveSubTab). (8) STRUCTURAL AC: T5d imports no unbuilt panel component; slots are props (grep/lint assert) — lets T5d build now while T7/T8/T9 don't exist.
- Recommended option: Store field on Tab record + mount-all container
- Open uncertainties: 1 (see discovery doc §Open uncertainties)
~~~

