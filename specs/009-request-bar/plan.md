# Plan: request-bar

**Date**: 2026-06-28
**Spec**: specs/009-request-bar/spec.md
**Status**: Approved

## Specialist Consultation

**Invocations**:
- Phase 0 alternatives: no — N/A (no 2+ alternatives compared; the store-action shape, method-list source, placement, and send-intent mechanism were all settled as /specify decision points, so there were no open alternatives to research).
- Phase 1.3 architecture decisions: yes (mandatory).
- Specialists consulted (orchestrator-relayed on the architect's request, or directly): none — the architect returned zero consultation requests; every decision mirrors an established codebase pattern (TabBar selectors, Shell Effect 4 keyboard registration, 005 method-pill, 001 Dropdown).

**Architect-authored sections** (transcribed verbatim from architect return):
- Layer Map: rows 1-7
- Key Design Decisions: rows 1-8
- Risk Assessment seeds: rows 1-5
- Constitution Compliance flags: §5.2, §4 sole-subscriber (amended via AC-24), §2.2 placement, §4 no-inline-styles, §4 store-actions-only, §2.3/§2.1 renderer boundary, §2.2 lib-leaf direction

| Specialist | Sub-question | Input summary | Verdict | Cites |
| --- | --- | --- | --- | --- |
| (none) | — | — | — | — |

## Summary

Add a flat `organisms/RequestBar.tsx` for the active request tab — a color-coded HTTP-method Dropdown (reusing the 001 Radix Dropdown molecule), a controlled plain URL input bound to the active tab's `RequestSpec.url`, and Send/Save/Share actions with ⌘↵/⌘S. The only net-new infrastructure is a single-source `lib/httpMethods.ts` (METHODS + HttpMethod, with `requestSpec.method` re-pointed to it) and a change-gated `tabsStore.updateActiveSpec(patch)` action; everything else reuses existing patterns. HTTP execution, the response, {{variable}} highlighting (epic D), persistence, real Share, and creating `organisms/request/` are out of scope.

## Technical Context

**Architecture**: renderer atomic-design — a new leaf `lib/` module (httpMethods), modifications to two existing leaf `lib/` modules (requestSpec type, tabsStore action), a new flat organism (RequestBar), and an App-root composition edit. Downward-only imports; `@renderer` alias; no Node/Electron.
**Error Handling**: boundary discipline — `updateActiveSpec` resolves the active tab internally and no-ops safely; the Send trim-guard predicate is the single guard for both the button and the keyboard path.
**State Management**: zustand `tabsStore` is the single owner; RequestBar reads via per-field selectors (mirroring TabBar) and writes only through `updateActiveSpec` / `markClean` (constitution §4).

## Constitution Compliance

- §5.2 (requestSpec is a pure data module, never imported by components): compliant — RequestBar reaches the method list/type via `lib/httpMethods`; `onSend` is typed with `HttpMethod` + primitives and `updateActiveSpec` is called with object literals, so RequestBar never imports `requestSpec`.
- §4 (mutate state only through store actions): compliant — every method/url write routes through `updateActiveSpec`; Save through `markClean`.
- §4 (sole-subscriber wording): requires attention — being formally amended via AC-24 (the single sanctioned departure; TabBar runtime behavior unchanged per AC-4).
- §4 (never inline styles): compliant — all styling via semantic classes bound to tokens.css (AC-28).
- §2.2 (flat-organism placement; `organisms/<domain>/` only at ≥2 components): compliant — RequestBar stays flat; `organisms/request/` is NOT created (§6 OOS).
- §2.2 (lib-leaf import direction): compliant — `httpMethods` imports nothing renderer-external; `requestSpec`→`httpMethods` is the only inbound edge (lib→lib, downward).
- §2.3 / §2.1 (renderer boundary): compliant — no Node/Electron imports in RequestBar or httpMethods (AC-29); cross-module via `@renderer`.
- §3.4 (testing): compliant — Vitest + Testing Library + Playwright CT, co-located under `__tests__/`.

## Implementation Approach

### Layer Map

| Layer | What | Files (existing or new) |
|-------|------|------------------------|
| lib — leaf data (new) | `METHODS` const (7 methods, display order) + `HttpMethod = typeof METHODS[number]`; imports nothing renderer-external | src/renderer/src/lib/httpMethods.ts |
| lib — domain data (modify) | re-point `RequestSpec.method` from `string` to `HttpMethod` imported from httpMethods; `makeBlankRequest` GET seed stays valid | src/renderer/src/lib/requestSpec.ts |
| lib — state store (modify) | add `updateActiveSpec(patch: Partial<RequestSpec>)`: resolve active tab internally, shallow-merge, set `dirty=true` only on actual change; existing lifecycle actions untouched | src/renderer/src/lib/tabsStore.ts |
| presentation — organism (new) | flat `RequestBar`: method Dropdown trigger + URL `<input>` + Send/Save/Share; per-field tabsStore selectors; `⌘↵`/`⌘S` document-keydown effect; `onSend` prop; token-bound semantic classes, zero inline styles | src/renderer/src/components/organisms/RequestBar.tsx, src/renderer/src/components/organisms/RequestBar.css |
| presentation — app composition (modify) | add `panes={{ request: <RequestBar onSend={…} /> }}` to the existing `<Shell tabs={<TabBar/>} />`; ToastProvider/Shell wiring otherwise unchanged | src/renderer/src/App.tsx |
| governance / docs (modify) | amend §4 sole-subscriber wording to admit RequestBar as the spec-edit subscriber (doc-only; no TabBar behavior change) | constitution.md |
| tests (new / extend) | RequestBar unit + CT; tabsStore `updateActiveSpec` cases | src/renderer/src/components/organisms/__tests__/RequestBar.test.tsx, src/renderer/src/components/organisms/__tests__/RequestBar.ct.tsx, src/renderer/src/lib/__tests__/tabsStore.test.ts |

### Key Design Decisions

| Decision | Chosen Approach | Why | Alternatives Rejected |
|----------|----------------|-----|----------------------|
| `onSend` payload shape | `onSend?: (intent: { tabId: string; method: HttpMethod; url: string }) => void`, default no-op; `HttpMethod` from httpMethods, all other fields primitives | Satisfies AC-13 (tab identity + method + url) WITHOUT importing `requestSpec` into a component — keeps §5.2 intact. Single path for Send click and ⌘↵. | Passing a `RequestSpec` object — forces a `requestSpec` import, violating §5.2. Passing only `(method,url)` — drops tab identity AC-13 requires. |
| URL input control model | Controlled `<input value={activeUrl} onChange={e ⇒ updateActiveSpec({ url: e.target.value })}>`; no remount key | Controlled binding swaps the displayed url on tab switch (AC-11) via the per-field selector; the url selector value is untouched on a method change, so React does not re-set the input value and caret/buffer are preserved (AC-18). Writes route through the store action (§4). | Uncontrolled + `defaultValue` — would not update on tab switch (AC-11). `key={activeTabId}` remount — needless churn; controlled binding already isolates per tab. |
| ⌘↵ / ⌘S registration | One `document` keydown effect handling both chords; reads live state via `tabsStore.getState()`; `e.preventDefault()` on ⌘S; cleanup on unmount | Mirrors Shell Effect 4 (document keydown + preventDefault + getState) — `getState()` avoids stale-closure capture so the handler acts on the current active tab regardless of focus (AC-16/AC-17). | React `onKeyDown` on a container — only fires when focus is inside RequestBar, failing "regardless of focus." Two separate effects — duplicate setup/teardown. |
| Send-enabled predicate | Single `canSend = url.trim() !== ''` derived once, consumed by the button `disabled`, the click handler, and the ⌘↵ handler | One predicate = one guard (DRY), so disabled state and the ⌘↵ path cannot diverge (AC-12/AC-13/AC-16 share trim semantics). | Computing the trim guard independently per call site — risks keyboard path and button drifting apart. |
| Method dropdown open-state | Local `useState` in RequestBar driving Dropdown's controlled `open`/`onOpenChange` | Dropdown (001) is a controlled-only Radix wrapper; local open-state is the contract. Reuses the existing molecule — no second overlay library (AC-3, §7). | Adding an uncontrolled/popover alternative — violates the reuse-Dropdown constraint and AC-3. |
| Active-state subscription | Per-field tabsStore selectors: `activeTabId`, active tab's `method`, `url`, `dirty` selected individually (mirror TabBar) | Selecting individual fields (not the whole `tabs` array) bounds re-renders to the values RequestBar shows, mitigating the §9 over-render risk; mirrors TabBar (§7). | Subscribing to the whole `tabs[]`/store object — re-renders on any unrelated tab mutation (§9 risk realized). |
| Method-pill trigger accessible name (Q-1) | Trigger button carries one accessible name (visible method text serves as the name; no redundant `aria-label`), mirroring 005's pill aria approach | Resolves Q-1: single announcement, not doubled, matching the 005 precedent. | A separate `aria-label` over visible text — double-announces the method (the 005 pitfall). |
| Constitution §4 amendment scope | Reword "TabBar.tsx is the sole subscriber" → TabBar owns lifecycle wiring; RequestBar is the spec-edit subscriber. Doc-only. | DEPARTURE: introduces a 2nd tabsStore subscriber where §4 currently names TabBar the sole subscriber — sanctioned by AC-24, which mandates this exact amendment; TabBar runtime behavior is unchanged (AC-4). | Leaving §4 as-is — leaves the constitution contradicting shipped code (AC-24 unmet). |

### Established-Convention Departures

| Departure | Established Pattern Left | Why Necessary |
|-----------|--------------------------|---------------|
| Constitution §4 reworded so RequestBar is a 2nd tabsStore subscriber (the spec-edit subscriber) | §4 currently states "TabBar.tsx is the sole subscriber" that wires tabsStore actions | A request bar that edits method+url must subscribe to and write the active tab's spec; the sole-subscriber wording predates this feature. AC-24 mandates the amendment; it is documentation-only and TabBar's runtime behavior is unchanged (AC-4). |

### File Impact

| File | Action | What Changes |
|------|--------|-------------|
| src/renderer/src/lib/httpMethods.ts | Create | `METHODS` const (GET/POST/PUT/PATCH/DELETE/OPTIONS/HEAD, display order) + `HttpMethod = typeof METHODS[number]`; pure const+type module |
| src/renderer/src/lib/requestSpec.ts | Modify | re-point `method: string` → `method: HttpMethod` (import from httpMethods); makeBlankRequest GET seed unchanged |
| src/renderer/src/lib/tabsStore.ts | Modify | add `updateActiveSpec(patch: Partial<RequestSpec>)` (resolve active tab, shallow-merge, dirty only on actual change); extend `TabsState` interface; existing actions untouched |
| src/renderer/src/components/organisms/RequestBar.tsx | Create | the organism — method Dropdown + URL input + Send/Save/Share + ⌘↵/⌘S effect + `onSend` prop; per-field selectors |
| src/renderer/src/components/organisms/RequestBar.css | Create | token-bound semantic classes for [method ▾][URL][Send/Save/Share] layout; horizontal URL scroll, no reflow |
| src/renderer/src/App.tsx | Modify | add `panes={{ request: <RequestBar onSend={…} /> }}` to the existing `<Shell tabs={<TabBar/>} />` |
| constitution.md | Modify | reword §4 sole-subscriber rule (AC-24) |
| src/renderer/src/components/organisms/__tests__/RequestBar.test.tsx | Create | unit: trim guard, method-switch independence, Save dirty/no-op, per-tab render isolation |
| src/renderer/src/components/organisms/__tests__/RequestBar.ct.tsx | Create | CT: layout, disabled Send, ⌘↵/⌘S, method-dropdown dismiss (two-step gate), per-tab isolation; fixtures import tokens.css + set data-mstyle |
| src/renderer/src/lib/__tests__/tabsStore.test.ts | Modify | add `updateActiveSpec` cases: dirty-on-change, no-op-no-flip, per-tab isolation |

### Documentation Impact

| Doc File | Action | What Changes |
|----------|--------|-------------|
| docs/renderer/index.md | Update | add RequestBar organism + httpMethods module to the renderer structure tree; note tabsStore gains updateActiveSpec |
| docs/architecture.md | Update | refresh the working-tabs pattern note (RequestBar is the spec-edit subscriber; updateActiveSpec) and correct the stale propless `<Shell/>` App-mount snippet to `<Shell tabs={<TabBar/>} panes={{request:…}} />` |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| RequestBar imports `requestSpec` to name the `RequestSpec` type, breaking §5.2 component-purity. | Med | Med | `onSend` typed with `HttpMethod` + primitives only; `updateActiveSpec` called with object literals (typed `Partial<RequestSpec>` on the store side). Lint/typecheck + a grep guard catch a stray import. |
| `httpMethods.ts` accidentally imports a store/component, breaking lib-leaf direction (§2.2). | Low | Med | Keep httpMethods a pure const+type module; `requestSpec`→`httpMethods` is the only inbound edge (lib→lib, downward). |
| `updateActiveSpec` over-dirties on a no-op patch, breaking the non-dirty Save no-op (AC-10/AC-15). | Med | Med | Set `dirty` only when a merged value actually differs; unit-test no-op-no-flip, change-flips, and per-tab isolation before UI wiring. |
| Narrowing `method` string→`HttpMethod` surfaces a hidden non-listed assignment elsewhere. | Low | Med | CBM-confirmed sole writer is `makeBlankRequest` (GET); lift the type into httpMethods and re-point in one change; typecheck/build gate (AC-5/AC-25/AC-27) catches strays. |
| CT flakiness from the Radix dismiss arm-race + missing `data-mstyle`/tokens context. | Med | Med | Apply the two-step dismiss gate (await animations + `setTimeout(0)` yield); CT fixtures import tokens.css and set `data-mstyle` on the host (005 CT lesson). |
| RequestBar over-renders as a 2nd tabsStore subscriber if it subscribes to the whole `tabs` array. | Med | Low | Per-field selectors for the active tab's method+url (mirror TabBar's memoized selector pattern). |
| Mount-point drift: docs/architecture.md shows a stale propless `<Shell/>` while App.tsx passes `tabs={<TabBar/>}`. | Low | Low | Plan §File Impact wires onto the verified App.tsx element; Documentation Impact refreshes the stale snippet at /finalize. |

## Dependencies

None — no packages to install, no services or environment variables. Radix (`radix-ui`) and zustand are already in the project; the Dropdown molecule, Icon atom, `cx()`, and tokens.css all exist.

## Supporting Documents

- No research.md — no Phase 0 signals (all libraries/patterns already in the stack; the open decisions were settled as /specify decision points).
- No data-model.md — reuses the existing `RequestSpec`; the only type change is re-pointing `method` to the new `HttpMethod` union (covered in Layer Map / File Impact).
- No contracts.md — renderer-only feature; no REST/GraphQL contract (Send fires an in-renderer `onSend` intent).
