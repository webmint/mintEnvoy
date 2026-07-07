# Plan: request-sub-tabs

**Date**: 2026-07-06
**Spec**: specs/015-request-sub-tabs/spec.md
**Status**: Approved

## Specialist Consultation

**Invocations**:

- Phase 0 alternatives: no — N/A (no 2+ alternatives compared; the mount strategy, no-new-dep, and per-tab-state approach were all settled in the spec/discover handoff — mechanical per §6 + §7)
- Phase 1.3 architecture decisions: yes (mandatory)
- Specialists consulted (orchestrator-relayed on the architect's request, or directly): see Specialist Consultation table

**Architect-authored sections** (transcribed verbatim from architect return):

- Layer Map: rows 1–8
- Key Design Decisions: rows D1–D10
- Risk Assessment seeds: rows 6–9 (R6–R9; rows 1–5 carried from spec §9)
- Constitution Compliance flags: §2.2 sibling-import (mitigated by slot injection), AC-14↔§4/AC-5 conflict (resolved Route B, see below)

| Specialist | Sub-question | Input summary | Verdict | Cites |
| --- | --- | --- | --- | --- |
| architect | Author the Layer Map / Key Design Decisions / Risk / Constitution tables; resolve whether §6 fidelity is achievable via scoped CSS with zero Tabs change | Full decision tables D1–D10; confirmed §6 fidelity achievable via `.pane-tabs`-scoped override (mirrors `.tabbar` precedent); surfaced AC-14↔AC-5/§4 ARIA-linkage conflict as D10 escalation | accepted | src/renderer/src/components/molecules/Tabs.css `.tabbar` block; design/styles.css:877-933 |
| design-auditor | Confirm §6 computed-style fidelity via `.pane-tabs` scoped CSS with no Tabs DOM change | Requested by architect; no response relayed — architect decided from the `.tabbar` scoped-override precedent | no-response | own-reasoning (Tabs.css `.tabbar` block) |
| frontend-engineer | Badge selector shape (count semantics + auth-badge glyph given the bearer seed) | Requested by architect; no response relayed — architect decided from KVTable's spec-ref selector pattern | no-response | own-reasoning (KVTable.tsx:36) |

## Summary

Build a new `RequestSubTabs` organism that composes the existing `Tabs` molecule (002) for a 6-fixed-sub-tab strip, owns 6 always-mounted tabpanels toggled by the `hidden` attribute (preserving KVTable state), and is backed by an additive per-tab `activeSubTab` field + `setActiveSubTab` action on `tabsStore`. Params/Headers slots receive the existing `KVTable` (014) injected from the App root; the other 4 share one neutral empty-state. §6 pane-tab visual fidelity is hit via a `.pane-tabs`-scoped CSS override of the Tabs DOM (zero molecule-contract change), asserted as computed styles in both themes. **Why no new research**: no signals — no new dependency (AC-3 forbids one), no new service, mount strategy + per-tab state pattern already established in the codebase (TabBar/KVTable).

## Technical Context

**Architecture**: Renderer atomic-design — new organism `RequestSubTabs` composes the `Tabs` molecule (downward-only, §2.2); mounts KVTable via slot props injected at the App composition root (never a sibling-organism import). Store change is leaf-level (tabsStore).
**Error Handling**: Defensive reads — `activeSubTab` normalized `VALID_KEYS.includes(v) ? v : 'params'`; `setActiveSubTab` validates key + no-ops on unknown `tabId` (mirrors existing store no-op convention); no active tab → neutral empty region, never throws.
**State Management**: zustand — additive `activeSubTab` field on the `Tab` record; the only write is via the `setActiveSubTab` action (§4 mutate-via-action-only). Badges are read-only derivations from the active spec ref.

## Constitution Compliance

- §2.1 renderer-only (no Node/Electron) — compliant (RequestSubTabs imports only React + @renderer; AC-23)
- §2.2 tier-flow downward-only — compliant **with attention**: RequestSubTabs (organism) must NOT import KVTable (organism). Panels injected as slot props from App.tsx root (D5/D7). A direct KVTable import would violate §2.2 AND AC-25.
- §2.3 @renderer alias — compliant
- §3.1 strict types, no `any` — compliant (AC-20); `SubTabKey` is a string-literal union
- §3.4 co-located tests (`.test.tsx` Vitest + `.ct.tsx` Playwright CT) — compliant (3 new test files)
- §3.5 doc comments on new exports — compliant (AC-19: RequestSubTabs, SubTabKey, setActiveSubTab documented)
- §3.6 search-before-build — compliant (composes Tabs/KVTable/tabsStore; no new generic util)
- §4 no inline styles / mutate-via-action-only — compliant (AC-22, AC-24; class-only CSS, setActiveSubTab)
- Design-token provenance gate (§7-6) — design/reference.html present → /breakdown emits design-manifest, /implement runs static token-provenance check
- **AC-14 ↔ §4/AC-5 conflict — RESOLVED (Route B, user-approved)**: the Tabs molecule renders tab buttons with no DOM `id` and deliberately no `aria-controls` (Tabs.tsx:370,544-573), so tabpanel↔tab ARIA linkage is impossible without touching Tabs. User approved a **minimal opt-in, byte-identical-when-off Tabs extension** (emit descriptor `id` as the button DOM `id` + optional `aria-controls`) — the same backward-compatible-extension framing used for `closable`/`onClose` (feature-004). Off-path stays byte-identical, so AC-5's selection-only contract is preserved; §4 row 4 "no change" is amended to "additive opt-in extension" (see File Impact).

## Implementation Approach

### Layer Map

| Layer | What | Files (existing or new) |
| ----- | ---- | ----------------------- |
| Composition root | Swap `panes.request` to composed pane: `RequestBar` above `RequestSubTabs`; inject `<KVTable field='params'/>` / `field='headers'/>` as panel slot props (org→org wiring stays at the root, §2.2). Pane is already `flex-column`, so a bare fragment lays out correctly. | src/renderer/src/App.tsx (Modify) |
| Organism (new) | RequestSubTabs: composes `Tabs` for the 6-sub-tab strip; self-subscribes `activeTabId` + active `spec` + normalized `activeSubTab`; derives 3 read-only badges; owns 6 always-mounted tabpanels (visibility-toggled) + one shared empty-state; wires tabpanel ARIA. | src/renderer/src/components/organisms/RequestSubTabs.tsx (Create) |
| Organism style (new) | `.pane-tabs`-scoped §6 fidelity overrides of the Tabs DOM (mirrors the `.tabbar` precedent) + panel/empty-state layout; root `flex:1;min-height:0`, panel body `flex:1;overflow:auto`. | src/renderer/src/components/organisms/RequestSubTabs.css (Create) |
| Molecule (additive opt-in extension) | Tabs: opt-in prop (e.g. `linkPanels`/`emitTabIds`) that, when set, emits the descriptor `id` as the button DOM `id` + `aria-controls`; OFF by default → byte-identical to current contract (AC-5 preserved). | src/renderer/src/components/molecules/Tabs.tsx (Modify — Route B) |
| Organism (reused, mounted live) | KVTable injected via slots; no change — goes live through the Params/Headers slots. | src/renderer/src/components/organisms/KVTable.tsx (no change) |
| lib (store) | tabsStore: add `SubTabKey` union + `activeSubTab` field (default `'params'`) on `Tab`/`makeBlankTab`; add `setActiveSubTab(tabId,key)` action (validate key, no-op on unknown id). | src/renderer/src/lib/tabsStore.ts (Modify) |
| lib (read-only) | requestSpec: badge-derivation source (`params`/`headers` rows, `auth` union); no change. | src/renderer/src/lib/requestSpec.ts (no change) |
| tokens (verify) | Confirm `--text-muted/--text/--accent/--accent-soft/--bg-active/--border-faint` present; no new token. | src/renderer/src/styles/tokens.css (verify-only) |
| tests (new) | Vitest interaction + Playwright CT + store unit. | .../organisms/__tests__/RequestSubTabs.test.tsx, RequestSubTabs.ct.tsx; lib/__tests__/tabsStore.test.ts (Create) |

### Key Design Decisions

| Decision | Chosen Approach | Why | Alternatives Rejected |
| -------- | --------------- | --- | --------------------- |
| **D1** Compose Tabs as-is | 6 `TabDescriptor`s (`id`=subtab key, `label`, `badge`); `<Tabs closable={false} activeId={activeSubTab} onChange={k=>setActiveSubTab(activeTabId,k)} className='pane-tabs'/>`; delegate Arrow/Home/End to Tabs. | Reuses molecule WAI-ARIA + roving-tabindex engine (§3.6); no fork. `closable=false` = selection-only path (AC-5, AC-6). | Forking Tabs / re-implementing keyboard — violates §3.6 + AC-5. |
| **D2** Per-tab `activeSubTab` state | Additive `SubTabKey` union + `activeSubTab` field (default `'params'`) on `Tab`, seeded in `makeBlankTab`; `setActiveSubTab(tabId,key)` action. | Extends the established additive-field + action-no-op store pattern; per-tab field guarantees A→B→A isolation (AC-8). | Shared/global active index (leaks across tabs, §9 risk 2); a separate store (fragments tab lifecycle). |
| **D3** Read-only badge derivation | One selector returns the active `spec` ref (mirrors KVTable's `rows` selector — avoids new-object-per-render over-render); `useMemo` derives `params`=`spec.params.length` (omit 0), `headers`=`spec.headers.length` (omit 0), each clamped `n>99?'99+':n`; `auth`=presence marker (e.g. `•`) when `spec.auth.type!=='none'`, else omit; Body/Tests/Code never badged. | Spec-ref selector re-fires only on `updateActiveSpec` replace → reactive without churn (AC-26, AC-15). Raw stored-row length = simplest "count" (KISS). Read-only → AC-24. | Object-returning selector (re-renders on every write); enabled-only counting (no AC backing); mirroring auth into a Headers row (spec forbids). |
| **D4** §6 fidelity via `.pane-tabs`-scoped CSS, zero-Tabs-DOM-change | Achievable, no molecule DOM change; AC-5 ∧ AC-27 both hold. Mirror the `.tabbar` block: scope `.tabs.pane-tabs`, `.pane-tabs .tabs__list`, `.pane-tabs .tabs__tab`, neutralize molecule active treatment + add `.pane-tabs .tabs__tab--active::after` underline (1.5px `--accent`), rebind `.pane-tabs .tabs__badge` to §6 `--bg-active`/`--accent-soft`. | Fidelity asserted as computed styles (not class equality), so re-styled `.tabs__badge` matches §6 `.pane-tab .badge` computed values. Same theme tokens on both sides → light/dark parity automatic. `.tabbar` precedent proves every move. | A Tabs-molecule DOM/class change (violates AC-5); screenshot baselines (drift-blind, §9 risk 3). |
| **D5** App.tsx composition | `request={<><RequestBar/><RequestSubTabs params={<KVTable field='params'/>} headers={<KVTable field='headers'/>} /></>}`. Panels injected from the root; RequestSubTabs imports NO organism. | `.pane-split__pane--request` is already `flex-column;min-height:0` → fragment stacks RequestBar over RequestSubTabs (`flex:1`) with no wrapper (minimal). Root injection keeps sibling wiring out of any organism (§2.2 + AC-11 + AC-25). | A `RequestPane` wrapper organism (imports sibling organisms → §2.2 violation); RequestSubTabs importing KVTable (§2.2 + AC-25 violation). |
| **D6** Mount-all + visibility toggle | Render all 6 tabpanels; hide inactive via the `hidden` attribute (`display:none` + drops from a11y tree). Same DOM node + React value state + `scrollTop` survive. Add a `useLayoutEffect` refocus-on-reshow to guarantee literal input-focus retention across a switch (see R6). | Never unmounting preserves KVTable value + scroll (§7, AC-9); `hidden` is the APG-correct hidden-tabpanel form. Refocus closes the `hidden`-blurs-focus gap. | Lazy/on-demand mount (§6 OOS + §9 risk 1 — remount loses state). |
| **D7** One shared neutral empty-state | RequestSubTabs renders ONE muted (`--text-muted`) "Panel not yet available" element for the 4 unbuilt slots (and as fallback when a panel prop is absent, AC-12); internal inline JSX, imports no `AuthPanel/BodyEditor/TestsPanel/CodePanel`. | Satisfies AC-12/AC-25; internal element is not a sibling-organism import. | Per-panel personalized empty-states (AC-12 says one shared); importing stub panels (AC-25). |
| **D8** Tabpanel ARIA owned by RequestSubTabs | Each panel: `role='tabpanel'` + stable `id={`panel-${key}`}` + `aria-labelledby={`tab-${key}`}` + `aria-controls` to its tab + `aria-selected` mirroring `activeSubTab`. The tab-side `id`/`aria-controls` come from D2/Route B's opt-in Tabs prop. | RequestSubTabs owns the panels → role + aria-selected trivially set; Route B supplies the tab DOM id needed for the linkage (AC-14 fully met). | (blocked-portion resolved by Route B, see D10). |
| **D9** Defensive reads | `activeSubTab` read normalized `VALID_KEYS.includes(v)?v:'params'`; `setActiveSubTab` validates key + no-ops on unknown `tabId`; no active tab → neutral empty region, no throw. | Mirrors the store's unknown-id no-op convention; guards persisted-garbage from later T23 restore (AC-16/AC-17). | Throwing on invalid key (AC-17 forbids); trusting the typed enum alone (runtime persisted values can violate it). |
| **D10** ARIA panel↔tab linkage | **RESOLVED — Route B (user-approved)**: a minimal opt-in, byte-identical-when-off Tabs extension emits the descriptor `id` as the button DOM `id` + optional `aria-controls`. | Only path that fully meets AC-14 while keeping AC-5's selection-only contract intact (off-path unchanged); precedented by `closable`/`onClose` (feature-004). | Route A (omit tab-linking attrs — fails AC-14 as written); runtime `setAttribute` on Tabs buttons from an effect (fragile DOM mutation outside React). |

### Established-Convention Departures

_No departures — every decision follows an existing codebase pattern. Route B's Tabs extension is itself the established "backward-compatible opt-in extension" pattern (closable/onClose, feature-004), not a departure._

### File Impact

| File | Action | What Changes |
| ---- | ------ | ------------ |
| src/renderer/src/components/organisms/RequestSubTabs.tsx | Create | The container/switcher organism: composes Tabs, owns 6 mounted tabpanels + shared empty-state, derives read-only badges, wires tabpanel ARIA, defensive reads (AC-1, AC-5, AC-6..AC-17, AC-26). |
| src/renderer/src/components/organisms/RequestSubTabs.css | Create | `.pane-tabs`-scoped §6 fidelity override of the Tabs DOM + panel/empty-state layout (AC-2, AC-27). |
| src/renderer/src/lib/tabsStore.ts | Modify | Add `SubTabKey` union + `activeSubTab` field (default `'params'`) on `Tab`/`makeBlankTab`; add `setActiveSubTab(tabId,key)` action (AC-7, AC-8, AC-16, AC-19). |
| src/renderer/src/components/molecules/Tabs.tsx | Modify (planning-discovered addition; §4 row 4 was "no change") | Route B: additive opt-in prop emitting descriptor `id` as button DOM `id` + optional `aria-controls`; OFF by default → byte-identical (AC-14, AC-5). |
| src/renderer/src/App.tsx | Modify | Replace `panes.request` (`<RequestBar/>`) with composed `<RequestBar/> + <RequestSubTabs params=… headers=…/>`; injects KVTable via slots (AC-18, AC-11). |
| src/renderer/src/components/organisms/KVTable.tsx | No change | Mounted live via slots; no component change. |
| src/renderer/src/lib/requestSpec.ts | No change | Read-only badge source. |
| src/renderer/src/styles/tokens.css | Verify-only | Confirm §6 tokens present; no new token. |
| src/renderer/src/components/organisms/__tests__/RequestSubTabs.test.tsx | Create | Vitest interaction (switch, badge, defensive reads, per-tab state). |
| src/renderer/src/components/organisms/__tests__/RequestSubTabs.ct.tsx | Create | Playwright CT: keyboard, focus-survives-switch, A→B→A per-tab state, per-theme computed-style fidelity, a11y. |
| src/renderer/src/lib/__tests__/tabsStore.test.ts | Create | Unit: `setActiveSubTab` sets per-tab key, validates, no-ops on unknown id; additive field does not break existing consumers. |

### Documentation Impact

| Doc File | Action | What Changes |
| -------- | ------ | ------------ |
| docs/renderer/components/index.md (or organisms concern doc) | Update | Add RequestSubTabs to the organisms roster + its compose-Tabs/own-panels role. |
| docs/renderer/lib/index.md (tabsStore concern) | Update | Note the additive `activeSubTab`/`SubTabKey`/`setActiveSubTab` on the tabs state machine. |

_Doc updates are surgical and handled by `/finalize`'s tech-writer pass; nothing beyond the two concern docs above is expected._

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
| ---- | ---------- | ------ | ---------- |
| (1) A lazy-mount regression silently breaks panel-state preservation (KVTable remounts on switch, losing focus/edits) | Med | High | The focus-survives-switch CT (focus a Params cell, switch to Headers and back, assert same DOM node keeps focus/value) is the go/no-go gate before wiring all 6 panels. |
| (2) A shared/global active-sub-tab index leaks across request tabs (per-tab state bug) | Med | Med | Dedicated A→B→A CT: A on Headers, B on Body, switch A→B→A, assert A's activeSubTab is still headers. |
| (3) Fidelity baselines drift (a sub-1% color change stays within screenshot tolerance and passes stale) | Med | Med | Assert resolved computed styles vs §6 values in both themes, reading the numbers from design/styles.css at CT-writing time (not screenshots). |
| (4) The additive Tab-record field breaks existing tabsStore consumers | Low | High | Type-check both configs and run the TabBar and RequestBar CTs after the store change. |
| (5) Mounting the composed pane into App.tsx + taking KVTable live introduces integration regressions in the running shell | Med | Med | Add a mount/smoke test for the composed request pane and run the full existing suite. |
| (R6 — NEW) `hidden`/`display:none` toggle drops literal DOM focus on hide (element made `display:none` blurs); value + scroll survive but the cell is no longer `document.activeElement` after switch-back | Med | Med | D6 adds a `useLayoutEffect` refocus-on-reshow (reuse the focus-restore pattern in Tabs.tsx); /breakdown must pin the AC-9 CT semantics to same DOM node + value + scroll + (via refocus) focus. |
| (R7 — NEW) Incomplete `.pane-tabs` neutralization — §6 parity needs badge-bg rebind, badge geometry reset, active box-shadow + accent-wash removal, `overflow:visible`, and the `::after` underline; missing any one leaves a computed-style drift | Med | Med | Enumerate EVERY §6 property (both themes) in the fidelity CT, read from styles.css at test-writing time. |
| (R8 — NEW) Auth badge shows on every fresh tab (bearer seed defaults `auth.type='bearer'` with a token) → reads as "auth configured" | High | Low | In-scope behavior is truthful to the seed; a "meaningful-auth" heuristic and changing the seed are both OOS (§6). Badge shows presence when `auth.type!=='none'`. |
| (R9 — RESOLVED) `aria-controls`/`aria-labelledby` cannot resolve without a tab DOM id (AC-14 vs AC-5/§4) | — | — | Resolved via Route B (opt-in Tabs extension), user-approved; see D10 + Constitution Compliance. |

## Dependencies

None. No package to install, no service to configure, no environment variable. AC-3 explicitly forbids a third-party tab library; the feature composes existing modules (Tabs, KVTable, tabsStore).

## Supporting Documents

- Research — none (no signals detected; planning cold from the spec + codebase).
- Data Model — none (additive `SubTabKey` union + one `activeSubTab` field + one action; covered inline in Layer Map / D2).
- Contracts — none (no REST/GraphQL contract; renderer-internal only).
