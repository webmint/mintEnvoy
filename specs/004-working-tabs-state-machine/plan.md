# Plan: working-tabs-state-machine

**Date**: 2026-06-24
**Spec**: specs/004-working-tabs-state-machine/spec.md
**Status**: Approved

## Specialist Consultation

**Invocations**:

- Phase 0 alternatives: no — N/A. No 2+ alternatives compared at /plan; the slice-shape alternatives (flat array vs normalized map vs spec registry) were already compared and settled in the `/discover` → `/specify` chain (Option A — flat tab array with embedded spec). No fresh discovery needed; no research signals detected (zustand + radix-ui already in stack).
- Phase 1.3 architecture decisions: yes (mandatory).
- Specialists consulted (orchestrator-relayed on the architect's request): frontend-engineer — see Specialist Consultation table.

**Architect-authored sections** (transcribed verbatim from architect return):

- Layer Map: rows 1-7
- Key Design Decisions: rows 1-7
- Risk Assessment seeds: rows 1-4 (Risk 1 mitigation refined post frontend-engineer relay)
- Constitution Compliance flags: §2.1, §2.3, §3.1, §3.3, §3.4, §3.6

| Specialist | Sub-question | Input summary | Verdict | Cites |
| --- | --- | --- | --- | --- |
| frontend-engineer | Minimal roving-focus restoration when the focused tab is removed under signal-only `onClose` | `useLayoutEffect` keyed `[activeId, tabs]` + a `lastFocusWasInListRef` capture-guard; restore `buttonRefs.get(activeId)?.focus()` only when guard true and not already focused; `tabIndex={0}` cannot dangle (re-derived each render); ✕ sibling invisible to roving logic | accepted | AC-11/AC-12/AC-23; Tabs.tsx roving engine (handleKeyDown ~:290, ref callback ~:373); docs/architecture.md "Tabs — hand-rolled WAI-ARIA tablist" |

## Summary

Build a renderer-only working-tabs feature as three layers: a plain-serializable `RequestSpec` domain model + seed factory (`lib/requestSpec.ts`), a flat-array `tabsStore` zustand slice owning the lifecycle state machine + per-tab dirty flag (`lib/tabsStore.ts`), and a `TabBar` organism that composes the existing Tabs primitive — extended with an opt-in, default-off `closable`/`onClose` contract — and mounts into Shell's existing `tabs` slot. No new runtime dependency; the design mirrors the established `settingsStore`/`toastStore` convention and reuses the 002 Tabs a11y engine rather than re-rolling it. No research.md (no signals).

## Technical Context

**Architecture**: Renderer process only (Electron three-process model — no main/preload changes). Touches the renderer's lib (model + state) leaf layer and the molecules + organisms component tiers. Dependency direction stays downward (organisms→molecules→atoms→lib); lib imports nothing from `components/`.
**Error Handling**: Thrown-exception model (constitution §3.2). Slice actions handle both paths — `close`/`markClean`/`selectActive` on an unknown id are no-ops (defensive guards), `openFromCollection` validates its input; no empty catches.
**State Management**: A single module-level zustand store (`create<TabsState>((set) => ...)`), one instance, mutated only through its actions; consumed via per-field selectors (`tabs`, `activeTabId`) + stable action references — never a whole-store read.

## Constitution Compliance

- §2.1 Process Boundaries (renderer-only): compliant — `tabsStore`/`requestSpec`/`TabBar` carry no Node/electron import; `crypto.randomUUID` is the browser global (not `node:crypto`). Gated by AC-10.
- §2.3 Module Organization (lib must not import `components/`): compliant — the one real tension is resolved by direction. The store exposes plain data + actions and imports no component; TabBar (organism) imports the store + the Tabs molecule (downward only), never a sibling organism. Resolved via `@renderer` alias.
- §3.1 Type Safety (no `any`): compliant — `Auth` is an exhaustive discriminated union on literal `type`, narrowed via an `isBearerAuth` guard. Gated by AC-5.
- §3.3 Naming: compliant — slice is `tabsStore` (camelCase + Store suffix); component `TabBar` PascalCase; files `tabsStore.ts` / `requestSpec.ts` / `TabBar.tsx`.
- §3.4 Testing: compliant — Vitest + Testing Library + Playwright CT, co-located `__tests__/` split `.test.tsx`/`.ct.tsx`; stack from feature 001, no new infra.
- §3.6 Function Length / KISS: compliant — slice actions kept <~40 lines (extract neighbor-selection + dedupe-match helpers); flat array chosen over a normalized map.

## Implementation Approach

### Layer Map

| Layer | What | Files (existing or new) |
| ----- | ---- | ----------------------- |
| lib (model) | `RequestSpec` + `Row` + `Auth` discriminated union (`{none}`\|`{bearer,token}`), `isBearerAuth` type guard, `makeBlankRequest()` seed factory (GET / empty url+name+body / Accept:application/json header / bearer `{{apiKey}}`); plain-serializable, no auth→headers mirroring | `src/renderer/src/lib/requestSpec.ts` (new) |
| lib (state) | `tabsStore` zustand slice `{ tabs: Tab[]; activeTabId }`; `Tab` carries a `collectionRequestId: string \| null`; actions `openFromCollection(input: OpenFromCollectionInput)` (two-leg dedupe: `collectionRequestId` first, then verbatim non-empty url), `newBlank`, `close` (never-zero + right-then-left neighbor for the active-tab branch; `activeTabId` UNCHANGED when a non-active tab closes), `selectActive`, `markClean`; tab-id via `crypto.randomUUID()` | `src/renderer/src/lib/tabsStore.ts` (new) |
| molecules | Tabs primitive extension — opt-in `closable`/`onClose` props (default-off); sibling `<button tabIndex={-1}>` ✕ per tab + Delete/Backspace close on focused tab; `onClose` signal-only; roving-focus restored on re-render | `src/renderer/src/components/molecules/Tabs.tsx`, `Tabs.css` (modify) |
| organisms | `TabBar` strip — maps `tabsStore.tabs`→`TabDescriptor[]` (label precedence name→method+url→`Untitled` verbatim; dirty marker via badge slot; `+` via actions slot); wires `selectActive`/`close`/`newBlank`; tokens-bound semantic classes | `src/renderer/src/components/organisms/TabBar.tsx`, `TabBar.css` (new) |
| organisms (wiring) | App injects `<Shell tabs={<TabBar />} />` at the composition root, replacing the test-fixture feeder. Shell stays slot-agnostic — it does NOT import TabBar (no organism→sibling-organism coupling, per Risk 2) | `src/renderer/src/App.tsx` (modify) — Shell.tsx itself is unchanged |
| support (demo) | Register a `closable` Tabs variant (and/or TabBar) in dev-only gallery for manual fidelity check vs `design/reference.html` | `src/renderer/src/components/PrimitivesDemo.tsx` (modify) |
| test | Slice unit suite (every lifecycle action + dirty/markClean + invariants + Q-2 serialization contract); TabBar render/select/close; Tabs `closable=true` a11y (axe) + `closable=false` byte-identical regression; CT for keyboard/focus | `src/renderer/src/lib/__tests__/tabsStore.test.ts`, `.../organisms/__tests__/TabBar.test.tsx`, `.../molecules/__tests__/Tabs.test.tsx`, `.../molecules/__tests__/Tabs.ct.tsx` (new/extend) |

### Key Design Decisions

| Decision | Chosen Approach | Why | Alternatives Rejected |
| -------- | --------------- | --- | --------------------- |
| Slice shape | Flat `{ tabs: Tab[]; activeTabId }`, array order IS tab order, spec embedded in Tab (Option A) | Pre-settled in /specify; mirrors `settingsStore`/`toastStore` convention (§7, §3.6 favors flat over normalized). Never-zero invariant means no empty state (AC-17), so no 0-tab branch | Normalized `{ byId, order }` map — KISS violation, no AC needs O(1) id lookup at this scale |
| Where close lives | Inside Tabs primitive as opt-in `closable`/`onClose`, default-off; ✕ is sibling `<button tabIndex={-1}>`, keyboard = Delete/Backspace on focused tab | **DEPARTURE** — the 002 contract was selection-only; gaining interactive close is a real contract change (record in 002 lineage per AC-29), backward-compatible by construction (default-off, byte-identical 002 path proven by AC-11/AC-12 regression). Exercises AC-22 | TabBar rolling its own ✕ outside the primitive — would duplicate roving-tabindex a11y the primitive owns (§6.3) |
| onClose contract | Signal-only: emits tab id on click/Delete/Backspace, mutates no list; store owns lifecycle; primitive's only post-close job is roving-focus integrity on next render | Keeps the primitive controlled + stateless (matches 002 `onChange`); store is sole owner of tab mutation (§4). Exercises AC-22/AC-23 | Primitive self-removing the tab — splits lifecycle ownership across primitive + store, breaks SSOT |
| Dirty-close policy | Silent unconditional drop; clean and dirty close through the SAME path; `dirty` stays an exposed selector; only close branch is the structural never-zero spawn | Pre-settled (§3, AC-19). One close path = §3.6 KISS; no confirm dialog in T4 (trigger sites that gate on dirty are §6 OOS) | Confirm-on-dirty-close — depends on a UX prompt §6 defers; over-solve |
| RequestSpec serializability (Q-2) | Plain object, no class/Symbol/function on the data shape; pin a contract test asserting `JSON.parse(JSON.stringify(spec))` deep-equals `spec` | Q-2 resolved direction; de-risks the OOS persistence task's cross-task contract now (Risk 2) at near-zero cost; actions live on the store wrapper, never on the data | Class-based RequestSpec with methods — breaks JSON round-trip, forces persistence rework |
| TabBar↔store wiring | Per-field selectors: subscribe to `tabs` and `activeTabId` separately; pull actions as stable references; no whole-store read | §4 "prefer zustand selectors"; avoids re-render on unrelated changes; matches 003 Shell pattern. Exercises AC-24–AC-27 | Whole-store `useTabsStore()` read — re-renders on any field change, violates selector-preference |
| Tab-id generation | `crypto.randomUUID()` at tab-create time (newBlank / openFromCollection append / never-zero spawn) | Browser global, no Node/electron import (§2.1 safe); collision-free; named in data-model.md. Greenfield convention, not a departure | Monotonic module-scope counter — survives slice but not HMR cleanly; UUID is simpler + stateless |

### Established-Convention Departures

| Departure | Established Pattern Left | Why Necessary |
| --------- | ----------------------- | ------------- |
| Tabs primitive gains opt-in interactive close (`closable`/`onClose`, ✕ + Delete/Backspace) | The 002 Tabs primitive is selection-only — it switches panels via `onChange(id)` and renders no per-tab interactive control beyond the tab button | The working-tabs feature requires closing tabs from the strip, and the close-focus restoration is roving-tabindex work the primitive already owns (§6.3 search-before-building — a TabBar-local ✕ would re-implement that a11y). Made safe by default-off opt-in: `closable=false` keeps the 002 path byte-identical (AC-11/AC-12 regression), so no existing consumer breaks. Recorded in the 002 spec lineage per AC-29, not a silent prop bump. |

### File Impact

| File | Action | What Changes |
| ---- | ------ | ------------ |
| src/renderer/src/lib/requestSpec.ts | Create | RequestSpec/Row/Auth types, `isBearerAuth` guard, `makeBlankRequest()` seed factory |
| src/renderer/src/lib/tabsStore.ts | Create | zustand slice `{ tabs, activeTabId }` + 5 actions + never-zero/neighbor/dedupe helpers |
| src/renderer/src/components/organisms/TabBar.tsx | Create | Strip composing Tabs; store→TabDescriptor mapping; label/dirty/`+` wiring |
| src/renderer/src/components/organisms/TabBar.css | Create | Tokens-bound semantic classes; reduced-motion-gated; no inline styles |
| src/renderer/src/components/molecules/Tabs.tsx | Modify | Opt-in `closable`/`onClose`; sibling `tabIndex={-1}` ✕; Delete/Backspace path; `useLayoutEffect` focus restoration |
| src/renderer/src/components/molecules/Tabs.css | Modify | Close-✕ styling + dirty-marker styling (token-bound) |
| src/renderer/src/App.tsx | Modify | Inject `<Shell tabs={<TabBar />} />` at the composition root (replacing the test-fixture feeder), satisfying AC-27 while keeping Shell slot-agnostic. Shell.tsx is NOT modified and does NOT import TabBar |
| src/renderer/src/components/PrimitivesDemo.tsx | Modify | Register a `closable` Tabs variant (and/or TabBar) for dev visual QA |
| src/renderer/src/lib/__tests__/tabsStore.test.ts | Create | Unit tests: every action + dirty/markClean + invariants + JSON round-trip contract; INCL. two-leg dedupe (collectionRequestId then url) and `activeTabId`-unchanged-on-non-active-close |
| src/renderer/src/components/organisms/__tests__/TabBar.test.tsx | Create | Render/select/close/new-blank + label precedence + dirty marker |
| src/renderer/src/components/molecules/__tests__/Tabs.test.tsx | Modify | `closable=true` behavior + `closable=false` byte-identical regression |
| src/renderer/src/components/molecules/__tests__/Tabs.ct.tsx | Modify | CT: Delete/Backspace close + roving-focus restoration + axe pass |

### Documentation Impact

| Doc File | Action | What Changes |
| -------- | ------ | ------------ |
| docs/renderer/index.md | Update | Add tabsStore + requestSpec to the lib/ tree; add TabBar to organisms/; note the Tabs closable extension |
| docs/architecture.md | Update | Extend the "Tabs — hand-rolled WAI-ARIA tablist" pattern note with the opt-in `closable`/`onClose` contract; add the tabsStore to the State Management list; record the RequestSpec serializability contract |
| docs/glossary.md | Update | Add RequestSpec, tabsStore, TabBar terms |

(Documentation is updated by `/finalize` via tech-writer, not in this feature's tasks — listed here for traceability.)

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
| ---- | ---------- | ------ | ---------- |
| Per-tab ✕ extension breaks 002 roving-tabindex a11y (nested interactive in role=tab, lost focus on close, dangling tabindex) | High | High | Spike against the existing roving-tabindex tests BEFORE TabBar; ✕ is sibling `tabIndex={-1}` (not a roving stop). Focus restoration: `useLayoutEffect` (NOT `useEffect`) keyed `[activeId, tabs]` + a `lastFocusWasInListRef` set via `onFocus`-capture on the tablist / cleared on `onBlur` when `relatedTarget` leaves the list — restore `buttonRefs.get(activeId)?.focus()` ONLY when the ref guard is true and `document.activeElement !== activeEl` (no mouse-user hijack; closes the focus-falls-to-`<body>` gap, AC-23). `tabIndex={0}` cannot dangle — `rovingTabStopIndex` re-derives from `(tabs, activeId)` every render. Implementer MUST NOT add ✕ to `buttonRefs`, give ✕ `role=tab`, or switch `handleKeyDown` to a DOM selector. Add `closable=false` byte-identical regression + `closable=true` axe pass. |
| Dependency-direction violation — store (lib) reaching into `components/`, or TabBar importing a sibling organism | Med | High | `tabsStore`/`requestSpec` import nothing from `components/` (leaf lib rule); TabBar imports only the Tabs molecule + lib (downward), never another organism; enforce via `@renderer` alias + code review |
| RequestSpec serialization shape drifts from the OOS persistence task | Med | Med | Pin the Q-2 contract test now (`JSON.parse(JSON.stringify(spec))` deep-equals `spec`); keep RequestSpec plain-serializable |
| Stale Vite/Playwright build cache makes a clean source file look broken (false RollupError) | Med | Med | When a build/test error names a clean file as import source, clear the cache (`playwright/.cache`, `node_modules/.vite`, `dist`) and re-run BEFORE editing source or filing a bug |
| Repo-wide reformatting/housekeeping on the feature branch pollutes the /verify hygiene scope | Med | Low | Keep this branch's commits to the feature's src + test files; avoid `prettier --write .` and unrelated housekeeping |

## Dependencies

None. No package to install (zustand + radix-ui already declared; `crypto.randomUUID` is a browser global). No service or environment variable. The renderer test stack (Vitest + Testing Library + Playwright CT) was established by feature 001.

## Supporting Documents

- [Data Model](data-model.md) — RequestSpec / Row / Auth / Tab / TabsState shapes + invariants
- Research: none — no research signals (zustand + radix-ui already in stack; all architectural choices pre-settled in the `/discover` → `/specify` chain)
- Contracts: none — no REST/GraphQL surface (renderer-only, in-memory)
