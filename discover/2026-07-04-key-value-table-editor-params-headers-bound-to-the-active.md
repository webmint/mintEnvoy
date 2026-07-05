# Discovery: Key-value table editor (params + headers) bound to the active request tab's RequestSpec, with {{variable}} token highlighting/validation against the active environment; hand-rolled editable grid, build-vs-buy only on {{variable}} value-field autocomplete; pixel-fidelity to design/reference.html

**Date**: 2026-07-04
**Topic**: Key-value table editor (params + headers) bound to the active request tab's RequestSpec, with {{variable}} token highlighting/validation against the active environment; hand-rolled editable grid, build-vs-buy only on {{variable}} value-field autocomplete; pixel-fidelity to design/reference.html
**Verdict**: Worth pursuing

## Summary

A hand-rolled key-value grid editing the active tab's RequestSpec params[]/headers[] — enabled/key/value/description rows, an auto-promoting trailing empty row, hover-✕ delete, and {{variable}} highlighting with an unknown-flag against the active environment — built once and mounted twice (params + headers), to pixel-fidelity against design/styles.css. Internal search found NO existing implementation of this capability (genuinely greenfield), but the two things it binds to are already built and require zero adaptation: the Row shape (requestSpec.ts) and the tabsStore.updateActiveSpec write path (spec 004), giving an overall Good fit at Low effort. Prior art confirms the pattern is standard (Postman/Insomnia/Bruno) and that heavyweight table libraries (TanStack/Material) are the wrong tool for a 4-column, <50-row, token-styled grid — hand-roll it. The two dependencies the request assumed — the env store's validVars (T14) and a parent pane-tabs container — do NOT exist yet, but both are already de-risked in scope (a ∅-defaulting selector; an independently-mountable component), so neither blocks v1. Primary risk is fidelity drift and focus-management correctness (keyboard traversal, focus-never-lost on auto-promote/delete), both pinned as required CT scenarios rather than a coverage percentage.

## Prior Art

| Reference | Kind | Relevance | Source |
|---|---|---|---|
| Postman / Insomnia / Bruno key-value param+header editors | product | Canonical behavioural reference for the hand-rolled grid: enabled/key/value/description columns + trailing auto-promoting empty row. Confirms the pattern is standard and hand-rollable. | https://muhimasri.com/blogs/react-editable-table/ |
| TanStack Table / Material React Table / rsuite Editable Table | library | Heavyweight editable-grid libs. Overkill for a 4-column <50-row grid bound to existing store; fight the semantic-class + pixel-fidelity + no-cruft constraint. Evidence FOR hand-rolling the grid, not adopting a table lib. | https://tanstack.com/table/latest/docs/framework/react/examples/editable-data |
| Downshift useCombobox | library | Headless combobox hook, total styling control — candidate for the DEFERRED {{var}} value-field autocomplete (out of v1). Composes inside a Radix Popover. | https://www.downshift-js.com/use-combobox |
| React Aria useComboBox | library | Adobe headless combobox hook — alt candidate for deferred autocomplete. Adds a second headless dependency the repo doesn't have; disfavoured vs reusing adopted Radix. | https://react-spectrum.adobe.com/react-aria/useComboBox.html |
| radix-ui Popover — already adopted in-repo (Dropdown/Modal/Toast import radix-ui) | library | Repo already imports radix-ui in molecules/Dropdown.tsx, Modal.tsx, Toast.tsx. For the DEFERRED autocomplete, compose Radix Popover + a combobox hook rather than adding a new UI library — satisfies 'reuse 001 primitives, no new library'. Not a capability implementation; a reuse dependency. | https://www.radix-ui.com/primitives/docs/components/popover |

## Integration Surface

| Touchpoint | Module/file | Why touched |
|---|---|---|
| RequestSpec tab store (updateActiveSpec) | src/renderer/src/lib/tabsStore.ts | Mutation path: read activeTab.spec.params/.headers via zustand selector; write via updateActiveSpec({params\|headers: nextRows}). New array ref defeats the ===​ no-op guard so dirty flips + re-render fires. No new store action needed. |
| RequestSpec Row shape | src/renderer/src/lib/requestSpec.ts | Existing Row = {enabled:boolean, key:string, value:string, description:string}; params: Row[] / headers: Row[]. Bind to this exact shape — do NOT invent a new one (user constraint confirmed by code). |
| Radix primitives (radix-ui, spec 001) | src/renderer/src/components/molecules/Dropdown.tsx | radix-ui already imported here + Modal.tsx + Toast.tsx. For DEFERRED autocomplete, compose Radix Popover — no new UI library. Not needed for v1 grid. |
| Design tokens (tokens.css) | src/renderer/styles/tokens.css | Semantic KV classes bind here; resolved values authoritative in design/styles.css. No kv-*.css exists yet — greenfield styling surface, no conflict. |
| Environment store validVars (T14) | (unverified) | unverified path — env store / envSlice does NOT exist in src/ (zero hits for validVars\|envSlice\|activeEnv). Read validVars via a thin selector defaulting to ∅; T6 tolerates absence. |
| Pane-tabs container (RequestSubTabs) | (unverified) | unverified path — no RequestSubTabs / pane-tab component in build (only top-level Tabs molecule + TabBar organism exist). Parent that would mount T6 is absent; T6 must be independently mountable. Generic molecules/Tabs.tsx is a reuse candidate for the future container. |

## Fit Assessment

| Touchpoint | User expected | Reality (scan) | Effort | Blockers |
|---|---|---|---|---|
| RequestSpec tab store (updateActiveSpec) | params/headers arrays already present in renderer tab state store — read/write existing shape | CONFIRMED. tabsStore (zustand, spec 004) exposes updateActiveSpec(patch: Partial<RequestSpec>). Belief matches reality exactly. Write path = updateActiveSpec({params\|headers: nextRows}) with a fresh array. No new action, no new shape. | Low | none |
| RequestSpec Row shape | bind to existing params/headers Row[]; do not invent new shape | CONFIRMED. Row interface exists verbatim in requestSpec.ts with the 4 fields. Zero adaptation needed. | Low | none |
| Radix primitives (radix-ui, spec 001) | reuse the Radix headless library adopted in 001 for {{var}} autocomplete; no new library | PARTIALLY CONFIRMED. radix-ui is adopted (DropdownMenu/Dialog/Toast). But no Combobox/Popover-combobox is built yet, and Radix has no first-class combobox primitive — the deferred autocomplete composes Popover + a combobox hook (Downshift/React-Aria) or Ariakit. Moot for v1 (autocomplete deferred). | Medium | Radix lacks a native combobox — deferred autocomplete needs Popover+hook composition, decided in the follow-up task |
| Design tokens (tokens.css) | pixel-fidelity via tokens.css bound to design/styles.css values | CONFIRMED. tokens.css exists at src/renderer/styles/tokens.css; design/styles.css is authoritative. Established semantic-class + tokens pattern across atoms/molecules (Icon/Tabs/Dropdown). KV classes are net-new, no collision. | Low | none |
| Environment store validVars (T14) | validVars from an env store to flag unknown {{var}} | MISFIT (tolerated by design). No env store exists (zero hits validVars\|envSlice\|activeEnv). Requirement already de-risked: read via thin selector defaulting to ∅, highlight always works, missing-flag activates only once T14 lands. NOT a hard prerequisite. | Low | env store T14 unbuilt — mitigated by empty-set-default selector, not a blocker for v1 |
| Pane-tabs container (RequestSubTabs) | parent Params/Headers pane mounts the component | MISFIT (tolerated by design). No pane-tabs container in build; RequestBar sits alone. T6 scoped as independently-mountable (CT with mock rows), so parent absence is not a blocker. Generic Tabs molecule available to build the container in a separate task. | Low | parent pane-tabs container unbuilt — mitigated by self-contained/isolation-testable design, separate task owns the shell |

**Overall fit**: Good
**Effort estimate**: Low
**Rationale**: Excellent fit. The core binding lands cleanly on existing, built infrastructure: the RequestSpec Row shape (requestSpec.ts) and the tabsStore.updateActiveSpec mutation path (spec 004) require zero adaptation — read a Row[] via selector, write a fresh array back through the existing action, and reactive re-render on external cURL-import mutation is a free consequence of the zustand subscription (no local copy). Styling drops onto the established semantic-class + tokens.css pattern; KV classes are net-new so there is no collision. The two dependencies the user's belief pointed at that do NOT yet exist — the env store's validVars (T14) and the parent pane-tabs container — are the only friction, and both are already de-risked in scope: validVars is read through a thin ∅-defaulting selector (highlight always works; missing-flag activates when T14 lands), and the component is built independently-mountable and isolation-testable so no parent is required. Neither absence blocks v1; effort is Low. The one genuinely deferred piece — {{var}} value-field autocomplete — is out of v1 and carries its own follow-up build-vs-buy once T14 provides data.

## Design Options

### Option A: Controlled grid, derived virtual trailing row, direct store writes
- **Shape**:
```
Zero component-local row state. Rows rendered = activeTab.spec.<field> (read via zustand selector) PLUS one synthetic virtual empty row at index length. Every edit computes a fresh Row[] and calls updateActiveSpec({<field>: nextRows}) immediately; first edit on the virtual row appends a real Row (auto-promote) so a new virtual trailing row appears. Delete = filter + updateActiveSpec. <field> is a 'params'|'headers' prop → one component, two mounts. {{var}} tokenised at render, compared to a validVars selector (∅-default).
```
- **Pros**:
  - Honors no-local-copy natively — external cURL-import mutation re-renders for free, no stale-edit race
  - Reuses the existing updateActiveSpec action — zero new store surface to test
  - Virtual trailing row makes never-zero + empty-row-not-deletable fall out by construction
  - Simplest to reason about; fewest moving parts
- **Cons**:
  - Every keystroke writes through the store (fires the ===​ no-op guard + a re-render); fine at <50 rows, not virtualization-scale
  - Cursor/focus must be managed carefully since the input is fully controlled by store-derived value
- **Complexity**: Low

### Option B: Local draft buffer, commit on blur/debounce
- **Shape**:
```
Component holds a local copy of the rows; edits mutate local state; changes are flushed to updateActiveSpec on blur or debounced. A reconciliation effect syncs the local buffer when the store array changes underneath.
```
- **Pros**:
  - Fewer store writes; typing never touches the store until commit
  - Cursor/focus trivially stable (input is locally controlled)
- **Cons**:
  - VIOLATES the no-local-copy constraint — the external cURL-import mutation race is exactly the failure this reintroduces (stale local edits resurrecting or clobbering an import)
  - Reconciliation effect is subtle and easy to get wrong (the classic controlled/uncontrolled sync bug)
  - More state, more tests, for a grid that does not need the write-batching
- **Complexity**: Med

### Option C: Granular row actions on tabsStore
- **Shape**:
```
Extend tabsStore with KV-specific actions — updateRow(field,index,patch), addRow(field), removeRow(field,index), toggleRow(field,index) — that own the array algebra + auto-promote. KVTable becomes a thin view calling these actions; the trailing-empty-row and never-zero logic lives in the store.
```
- **Pros**:
  - Row algebra is unit-testable at the store level, independent of the component
  - Component shrinks to pure presentation
- **Cons**:
  - Adds four new store actions + their tests for logic that Option A expresses as small pure array ops in the component — more surface for little gain
  - Couples generic tabsStore to KV-editor specifics (params/headers), leaking a component concern into the tab state machine
  - updateActiveSpec already covers the write; this is redundant machinery
- **Complexity**: Med

**Recommended option**: Controlled grid, derived virtual trailing row, direct store writes — It is the only option that satisfies the no-local-copy + external-mutation-race requirements by construction rather than by careful reconciliation — the cURL-import race (Option B's fatal flaw) simply cannot occur because there is no local buffer to go stale. It reuses the existing updateActiveSpec write path (spec 004) with zero new store surface, where Option C adds four actions and leaks KV specifics into the generic tab store for no functional gain. The never-zero guard and the 'empty row has no delete affordance' rule fall out of the virtual trailing row for free. The only real cost — a store write per keystroke — is a non-issue at the confirmed <50-row scale (virtualization is explicitly out of scope). Focus management (the genuine risk) is addressed the same way in any option and is pinned as a required CT scenario.

## Build vs Buy

| Build | Buy/Adopt |
|---|---|
| Hand-roll the 4-column CSS-grid editor (grid-template 22px 1fr 1fr 1fr 24px) with semantic classes bound to tokens.css, real <input type=checkbox> + real <button> delete, a small non-greedy {{...}} tokeniser, and direct updateActiveSpec writes. Grid mechanics (rows, auto-promote, focus movement) are simple enough that a table library is net-negative. | For the GRID: adopt TanStack Table / Material React Table / rsuite editable table. Rejected — overkill for 4 columns/<50 rows, and their DOM/styling fights pixel-fidelity + the semantic-class/tokens.css + no-cruft constraints. For the DEFERRED autocomplete only (out of v1): buy a headless combobox hook (Downshift useCombobox or React-Aria useComboBox) composed inside the already-adopted Radix Popover — decided in its own post-T14 follow-up task, not now. |

**Recommendation**: Build — The v1 scope (grid + highlight + missing-flag) is pure Build: every 'buy' table library trades away the fidelity and no-cruft constraints that are mandatory here, for row-management convenience the grid does not need. The single legitimate buy question — the value-field autocomplete — is deferred out of v1 (data-starved until T14) and will run its own build-vs-buy then, leaning buy-a-hook + reuse-Radix-Popover to honor 'no new UI library'.

## Derisk Plan

1. Spike Option A in isolation (CT with mock Row[]): prove the edit→updateActiveSpec→re-render cycle AND that an external array replacement (simulated cURL import) re-renders with no stale local edits
2. Pre-extract the computed-style fidelity targets from design/styles.css (grid template, row height, mono cell font/size, header casing/padding/colour) and resolve every var(--token)→token BEFORE coding, so fidelity ACs are exact
3. Decide the Row-type import route that honors the §5.2 invariant (requestSpec imported by tabsStore, never by components) — type-only import vs a store type re-export — before writing any import
4. Land the thin validVars selector now (returns ∅ when the env store is absent) so T6 binds to a stable seam and never hard-depends on T14
5. Lock the {{...}} tokeniser edge rules with unit tests first: non-greedy nesting, empty {{}}/unclosed {{ = plain text, trimmed unicode/dot/dash keys, key vs value tokenised independently

## Constitution Constraints

| Rule | Impact |
|---|---|
| §3.2 Error Handling — boundary lookups degrade gracefully | Directly enables the design: the validVars lookup is a boundary read that must return a ∅ fallback (like resolveIcon's fallback entry) when the env store is absent — the ∅-defaulting selector IS this rule applied. Never throw / never flag-everything-missing on a project with no environment. |
| §5.2 Domain Invariant — requestSpec imported by tabsStore, never by components | Constrains how KVTable obtains the Row type. It must NOT import requestSpec.ts for values/logic; resolve the Row type via a type-only import or a store type re-export. A derisk item pins this decision before imports are written. |
| §4 Never Do — never use inline styles; Prefer design tokens over literal values | Forbids the Claude Design export's cruft (data-om-* attrs, __OmT wrappers, inline styles, tweaks-panel) from entering the build. All KV styling via semantic BEM-ish classes in a sibling .css bound to tokens.css custom properties; conditional classes via cx(). |
| §3.3 Naming Conventions | KVTable.tsx (PascalCase, one component per file) + sibling KVTable.css + co-located __tests__/KVTable.ct.tsx. The 'params'\|'headers' field prop keeps it one component, two mounts — not two files. |
| §3.1 Type Safety — strict mode, no any | The {{...}} tokeniser, Row[] transforms, and the field prop union ('params'\|'headers') are fully typed; untyped boundaries (validVars selector output) narrow rather than cast. |
| §3.6 Simplicity & Reuse — search before building | Justifies hand-rolling the grid over a table lib and reusing existing infrastructure (updateActiveSpec, tokens.css, adopted radix-ui) rather than adding new dependencies; the internal canonical-pattern search (0 hits) is this rule discharged. |

## Open uncertainties

[NEEDS CLARIFICATION: integration_points — user-supplied mechanism guess (confirm via Phase 2 fit-check): if specs/001-ui-primitives already adopted a headless combobox/autocomplete library, reuse it rather than adding another]

## Recommendation

**Action**: /specify the v1 KVTable: a hand-rolled controlled key-value grid (Option A) bound to RequestSpec params[]/headers[] via updateActiveSpec, {{var}} highlight + ∅-defaulting missing-flag, one component / two mounts, pixel-fidelity to design/styles.css — autocomplete and the pane-tabs container explicitly out of scope.
**Next**: Run /specify with the distilled topic to author the spec + acceptance criteria.

## Next step

Copy the block below into a new /specify session manually. No automated handoff — user controls when /specify runs.

~~~
/specify "Hand-rolled key-value grid editing the active tab's RequestSpec params/headers via updateActiveSpec: enabled/key/value/description rows, auto-promoting trailing row, hover-delete, {{var}} highlight + env missing-flag (∅-default), one component two mounts, pixel-fidelity to design/styles.css. No autocomplete, no pane-tabs container."

Discovery reference: discover/2026-07-04-key-value-table-editor-params-headers-bound-to-the-active.md
Key facts:
- Functional scope: Hand-rolled editable key-value grid, one component instanced twice (params + headers). Per row: enabled checkbox (12px accent; .disabled row → opacity 0.55), key / value / description as three mono cells (description = plain editable text, no extra behaviour). Trailing always-empty row (.kv-row.empty + placeholder) auto-promotes to real row on first edit. Row delete via trailing 24px .kv-actions slot hidden by default, revealed on .kv-row:hover. {{variable}} tokens highlighted in key+value cells (.kv-cell .var), unknown ones flagged (.var.missing) vs active environment. Cell-to-cell focus movement is internal grid mechanics. Grid template 22px 1fr 1fr 1fr 24px. (Deferred/excluded mechanics enumerated in non_goals.)
- Users: Single end-user: developer editing params/headers on active request tab via keyboard+mouse — no role tiers, no collab. Developer-as-consumer: one component authored once, two mount points (params pane, headers pane). Second data-writer to acknowledge: params[]/headers[] arrays are ALSO populated programmatically by the import-from-cURL path (paste-cURL in URL bar + 'Import from cURL' command-palette action) which parses cURL into RequestSpec directly. KVTable is NOT sole writer — it is an editor-view over shared state mutable externally, so it must read/write through the existing RequestSpec store and re-render reactively when the array changes underneath it, NOT own a local copy. The cURL parse/import path itself is OUT of scope (lives with RequestBar/command-palette); this component only renders + edits the arrays correctly including when populated externally.
- Success criteria: FIDELITY: rendered grid matches design/styles.css computed values (grid template 22px 1fr 1fr 1fr 24px, row height, mono cell font/size, header casing/padding/colour) verified as fidelity ACs (var→token, not literal hex). BEHAVIOUR: auto-promote on first edit; hover-✕ delete; checkbox flips enabled + .disabled opacity; {{var}} highlight; .var.missing when validVars non-empty and token absent; neutral .var when validVars ∅. BINDING: reads/writes existing Row[] through store; re-renders reactively on external mutation (cURL import); no local copy. REUSE: one component, two mounts; testable in isolation (CT mock rows). NO export cruft: semantic classes bound to tokens.css; no data-om-*, __OmT, inline styles, tweaks-panel. THREE HARD BARS: (1) Keyboard traversal (CORE UX, not a11y polish) — Tab/Shift-Tab across cells (checkbox→key→value→description→next row); Enter in last row's value/description commits + auto-promotes with focus landing in new row; focus NEVER lost on auto-promote or delete (moves to adjacent row, not <body>). (2) Semantic form elements (powers #1) — real <input type=checkbox> (accent-color, Space-toggle free); delete-✕ a real <button> (Enter/Space focusable), NOT div-onClick. (3) CT coverage as required SCENARIOS not a %-threshold — each a CT: auto-promote on first edit; hover-✕ delete + correct focus; checkbox→enabled flip + .disabled; {{var}} known=.var/unknown=.var.missing when validVars non-empty; degradation validVars ∅ → all {{var}} neutral .var, zero .missing (assert explicitly); external array mutation (simulated cURL import) → reactive re-render no local copy; both mounts (params+headers) independent; fidelity computed-style asserts (var→token). Line-% threshold is NOT a hard bar. SOFT (not a hard bar): full screen-reader ARIA-grid roles / row labels / aria-rowindex — over-engineering for a local few-devs tool with no SR users; semantic elements (#2) give baseline a11y.
- Recommended option: Controlled grid, derived virtual trailing row, direct store writes
- Open uncertainties: 1 (see discovery doc §Open uncertainties)
~~~

