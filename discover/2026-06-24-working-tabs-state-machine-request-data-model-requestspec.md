# Discovery: Working-tabs state machine + request data model (RequestSpec) for an HTTP client, built as a zustand tabs slice with a TabBar strip UI

**Date**: 2026-06-24
**Topic**: Working-tabs state machine + request data model (RequestSpec) for an HTTP client, built as a zustand tabs slice with a TabBar strip UI
**Verdict**: Worth pursuing

## Summary

T4 builds the working-tabs state machine + RequestSpec request data model for the HTTP client as a renderer zustand slice (tabsStore) plus a TabBar strip. Prior-art is decisive: the slice convention (settingsStore/toastStore), the tab a11y primitive (molecules/Tabs.tsx), and the Shell 'tabs' mount slot all already exist internally, and Bruno's .bru/OpenCollection schema validates the RequestSpec shape (method/url/params/headers/body/auth with an extensible auth discriminated union seeded at none+bearer). Overall fit is Good and effort Low — the only net-new work is the GAP capabilities with no internal prior art (the RequestSpec domain model and the lifecycle/dirty state machine), and the one belief-vs-reality correction is favorable: the '+' new-tab control fits the Tabs primitive's existing actions? slot with no contract change, leaving only a per-tab close ✕ as a genuine (and narrow) primitive extension. Recommended direction: build a flat tab-array slice that composes the existing primitive and mirrors the existing store convention. Primary risk: the Tabs-primitive close-✕ extension must not break its roving-tabindex a11y, and the RequestSpec serialization shape must be pinned against the out-of-scope persistence task to avoid rework.

## Prior Art

| Reference | Kind | Relevance | Source |
|---|---|---|---|
| Tabs primitive (TabDescriptor/TabsProps) | pattern | internal — existing tab a11y/roving-tabindex + selection primitive (002); TabBar composes & extends it (close ✕, '+', dirty), does NOT re-roll | internal:src/renderer/src/components/molecules/Tabs.tsx |
| zustand store convention (settingsStore/toastStore) | pattern | internal — module-level create<State>((set)=>...), Store suffix (§3.3), renderer-only, selectors; tabsStore mirrors this exactly | internal:src/renderer/src/lib/settingsStore.ts |
| Shell organism 'tabs' slot | pattern | internal — existing mount point above PaneSplit where TabBar renders; no new layout plumbing needed | internal:src/renderer/src/components/organisms/Shell.tsx |
| Bruno .bru / OpenCollection request schema | product | GAP: RequestSpec shape — validates {method,url,headers,params(typed array),body{type,data},auth{type,...}}; auth types none/inherit/basic/bearer/apikey/digest/oauth2/awsv4/ntlm confirm the extensible discriminated-union with none+bearer as the minimal seed | https://docs.usebruno.com/bru-lang/tag-reference |
| Zustand slices pattern (official) | pattern | GAP: tab state machine — canonical single-slice shape (tabs[] + activeTab + actions); matches the project's existing module-level store convention | https://zustand.docs.pmnd.rs/learn/guides/slices-pattern |
| Redux→Zustand multi-tab editor case study | pattern | GAP: per-tab dirty/unsaved tracking — validates a tabs slice holding per-tab document state + dirty flag, markClean on save/send | https://engineering.synaptic.com/managing-state-in-a-multi-tabbed-application-our-journey-from-redux-to-zustand-6d3932544300 |

## Integration Surface

| Touchpoint | Module/file | Why touched |
|---|---|---|
| Tabs primitive (molecules/Tabs.tsx) | src/renderer/src/components/molecules/Tabs.tsx | existing capability — candidate for reuse over fresh build; TabBar composes it; its {id,label,badge?,disabled?} selection-only contract is EXTENDED (close ✕ sibling button, '+' control, dirty marker) — record extension in /specify |
| zustand store convention (lib/) | src/renderer/src/lib/settingsStore.ts | existing capability — new tabsStore.ts mirrors this slice convention; reuse over inventing a new state pattern |
| Shell 'tabs' slot | src/renderer/src/components/organisms/Shell.tsx | existing capability — TabBar mounts into the existing 'tabs' slot above PaneSplit; no new layout plumbing |

## Fit Assessment

| Touchpoint | User expected | Reality (scan) | Effort | Blockers |
|---|---|---|---|---|
| Tabs primitive (molecules/Tabs.tsx) | Extend the primitive contract with per-tab close ✕, a '+' new-tab control, and a dirty marker | Primitive is controlled/selection-only (tabs[], activeId, onChange) and ALREADY exposes an actions? slot rendered OUTSIDE role=tablist (AC-8) — the '+' new-tab control fits there with NO contract change. Only per-tab close ✕ needs a real extension: a close button rendered as a SIBLING to the role=tab label (never nested) + an APG Delete-key path. Dirty marker can ride the existing badge? slot. Net: extension is narrower than the user assumed. | Low | per-tab close button must not nest inside role=tab (would break roving tabindex); needs APG Delete-key handler on the focused tab |
| zustand store convention (lib/) | New tabsStore.ts mirrors settingsStore.ts / toastStore.ts | Exact match: module-level create<State>((set)=>...), Store suffix (§3.3), renderer-only (no node/electron imports), selector usage. No new state pattern invented; tabsStore drops straight into the convention. | Low | none |
| Shell 'tabs' slot | TabBar mounts into Shell's existing tabs slot | Confirmed: Shell renders a 'tabs' slot above PaneSplit, currently fed only by a test fixture (ShellWithTabsFixture). Wiring the real TabBar is a slot fill — no new layout plumbing. | Low | none |

**Overall fit**: Good
**Effort estimate**: Low
**Rationale**: Fit is Good and effort Low. All three touchpoints already exist and match: the zustand slice drops straight into the settingsStore/toastStore convention, the TabBar mounts into Shell's existing 'tabs' slot, and the Tabs primitive is reused rather than re-rolled. The only real net-new work is the GAP capabilities with no internal prior art — the RequestSpec domain model and the tab state machine (lifecycle + dirty/markClean). The one belief-vs-reality correction is favorable: the user expected to extend the Tabs primitive with both a '+' control and per-tab close ✕, but the '+' fits the primitive's existing actions? slot (no contract change) — only the per-tab close ✕ (sibling-to-role=tab + APG Delete) is a genuine contract extension, which /specify must record explicitly.

## Design Options

### Option A: Flat tab array with embedded spec
- **Shape**:
```
state = { tabs: Tab[]; activeTabId: string } where Tab = { id; spec: RequestSpec; dirty }. Tab order IS the array order. Actions find-by-id over a small N; serialization = tabs.map(t => t.spec).
```
- **Pros**:
  - Simplest shape — mirrors settingsStore/toastStore minimalism (KISS)
  - Array order naturally encodes tab order; no separate order list to sync
  - Trivial (de)serialization to the persistence JSON shape
  - Close-neighbor selection is a simple index walk
- **Cons**:
  - O(n) find-by-id on markClean/updateActive (irrelevant for small N tab counts)
  - Index/id bookkeeping needed for close→select-neighbor
- **Complexity**: Low

### Option B: Normalized id-keyed map plus order list
- **Shape**:
```
state = { tabsById: Record<string,Tab>; order: string[]; activeTabId }. Lookups and updates are by id; order[] holds tab sequence separately.
```
- **Pros**:
  - O(1) lookup/update by id for markClean, updateActive, dedupe-by-id
  - Cleaner immutable per-tab updates
- **Cons**:
  - Two structures (order vs tabsById) must be kept in sync on every open/close
  - More boilerplate than the array for no real gain at small N
  - dedupe-by-url is still an O(n) scan
- **Complexity**: Med

### Option C: Spec registry with tab refs (decoupled)
- **Shape**:
```
RequestSpecs live in their own registry map; tabs hold only spec-id refs, so one spec could back multiple tabs/views.
```
- **Pros**:
  - Decouples spec lifetime from tab lifetime
  - Enables future multi-view of a single spec
- **Cons**:
  - Over-engineered for an in-memory single-window scope (YAGNI)
  - Extra indirection on every read/edit
  - No requirement in scope motivates the decoupling
- **Complexity**: High

**Recommended option**: Flat tab array with embedded spec — Extend the existing store convention rather than invent a new one: tabsStore mirrors internal:src/renderer/src/lib/settingsStore.ts (module-level create<State>, Store suffix, renderer-only) and the TabBar composes internal:src/renderer/src/components/molecules/Tabs.tsx instead of re-rolling tab a11y. The flat array is the KISS choice — at realistic tab counts the O(n) find-by-id is a non-issue, array order encodes tab order for free, and serialization to the persistence JSON shape is a trivial map. The normalized id-keyed map buys O(1) updates the scope does not need while adding an order/tabsById sync burden; the spec-registry option solves a multi-view problem no requirement raises (YAGNI). Acknowledged tradeoff: close→select-neighbor needs explicit index bookkeeping, and updateActive/markClean do an array find — both cheap and well-contained.

## Build vs Buy

| Build | Buy/Adopt |
|---|---|
| Build the tabsStore slice + the RequestSpec domain model fresh, composing the existing internal Tabs primitive and the zustand dependency the project already ships. No new runtime dependency. | Adopt an external request-collection model/SDK (e.g. postman-collection, or Bruno's bru parser) to supply the RequestSpec shape and (de)serialization. |

**Recommendation**: Build — The buy path drags a heavyweight collection SDK in to model a handful of in-memory fields — a poor trade for an extensible discriminated-union we fully control, and it would couple the domain entity to a third-party schema. zustand is already a dependency and the Tabs primitive already exists, so the build path is mostly composition of internal assets; only the domain model + state machine are genuinely net-new. Bruno/OpenCollection inform the shape as a reference, not as a runtime dependency.

## Derisk Plan

1. Spike the Tabs-primitive close-✕ extension (close button as sibling to role=tab + APG Delete key) against the primitives existing roving-tabindex tests, confirming the contract extension is non-breaking BEFORE building the TabBar
2. Pin the RequestSpec serialization JSON shape as a shared contract test with the out-of-scope persistence task before implementing, to avoid rework when persistence lands
3. Establish the renderer test stack (Vitest + Testing Library per constitution §3.4 — no test infra exists yet) as part of this feature, since the success bar requires slice unit tests
4. Decide and fixture the url-dedupe normalization rule (trailing slash, case) and the dirty-tab-close behavior (warn/confirm vs silent-drop) during /specify

## Constitution Constraints

| Rule | Impact |
|---|---|
| §3.3 Naming Conventions | zustand store is camelCase + Store suffix → name it tabsStore (not TabsStore/TabSlice); aligns with settingsStore/toastStore for clean discovery |
| §2.1 / §2.3 Process Boundaries & Imports | tabsStore is renderer-only — no node/electron imports, resolve via @renderer alias, no cross-process imports; reinforces the scope rule that lib/ must not import components/ and the collection store must not be imported |
| §3.1 Type Safety | strict mode, no any → the auth discriminated union must be exhaustively typed and narrowed via type guards on ; RequestSpec is fully typed, enabling the extensible-union design without escape hatches |
| §3.4 Testing Requirements | no renderer test infra exists yet; the success bar (slice unit tests) makes this feature the one that must stand up Vitest + Testing Library — added setup scope to budget in /plan |
| §4 Patterns (Always Do, project-specific) | 'Shared renderer state lives in a zustand store' directly validates the slice approach over component-local state |

## Open uncertainties

[NEEDS CLARIFICATION: integration_points — user-supplied placement guess (confirm via Phase 2 fit-check): implement as a zustand tabs slice + TabBar strip UI, request-editing panels out of scope]

## Recommendation

**Action**: Run /specify for T4 — author the spec, explicitly recording the Tabs-primitive contract extension (per-tab close ✕ sibling button + APG Delete; '+' via the existing actions? slot) and the in-scope RequestSpec serialization shape as acceptance criteria
**Next**: Proceed to /specify with the flat-tab-array slice + composed-primitive direction

## Next step

Copy the block below into a new /specify session manually. No automated handoff — user controls when /specify runs.

~~~
/specify "T4 working-tabs state machine + RequestSpec model: a renderer zustand tabsStore (flat tab array, lifecycle + dirty/markClean, seed defaults) and a TabBar composing the existing Tabs primitive."

Discovery reference: discover/2026-06-24-working-tabs-state-machine-request-data-model-requestspec.md
Key facts:
- Functional scope: A zustand tabs slice owning the open-request tabs + the lifecycle state machine (open-from-collection with dedupe id-then-url, new-blank, close never-zero, select-active), a per-tab dirty flag + markClean(tabId) action, and new-tab seed defaults. The RequestSpec domain model: { method, url, name, params[], headers[], body:{lang,type,text}, auth } where each param/header row is { enabled, key, value, description } and auth is a discriminated union on type ({none}+{bearer,token} in scope). A TabBar strip UI composing the existing Tabs primitive (extended with close ✕, '+' new-tab, dirty marker) and wiring it to the slice. Out of scope: request-editing panels, real send/save, variable interpolation, other auth types, auth→wire-header derivation.
- Users: Two consumer classes. (1) End user: operates the TabBar — open/close/switch request tabs. (2) Sibling tasks consuming the zustand slice programmatically: collection-list opens tabs (open-from-collection), http-engine reads active RequestSpec + calls markClean on successful send, persistence calls markClean on save, request-editing panels bind to the active tab's RequestSpec. T4 owns only the slice + TabBar + the markClean action; the trigger sites live in those sibling tasks (out of scope).
- Success criteria: Slice unit-tested: every lifecycle action (open-from-collection dedupe id-then-url, new-blank, close never-zero, select-active) + dirty flag + markClean(tabId) covered; invariants asserted (never-zero tabs, dedupe, seed defaults = auth bearer {{apiKey}} verbatim + default Accept header, auth NOT mirrored into headers[]). TabBar renders/selects/closes AND visually matches design/reference.html (look/spacing/states) against design/tokens.json. typecheck + lint + build clean.
- Recommended option: Flat tab array with embedded spec
- Open uncertainties: 1 (see discovery doc §Open uncertainties)
~~~

