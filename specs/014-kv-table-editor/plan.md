# Plan: kv-table-editor

**Date**: 2026-07-04
**Spec**: specs/014-kv-table-editor/spec.md
**Status**: Approved

> **Grill-revision (cycle 1).** This plan replaces the prior draft after a `/grill` REVISE-PLAN disposition confirmed 2 plan-local defects (`specs/014-kv-table-editor/grill.md`). F1 (High): the field-prop-only KVTable called `envVars()` internally, and `envVars` is ∅ in v1, so `.var.missing` could never render → AC-19 + the mandated `.var.missing` fidelity CT were structurally unreachable. F2 (Med): a new single-component `organisms/request/` subfolder violated constitution §2.2's ≥2-components gate. This revision (1) adds a `validVars` injection-seam prop to KVTable and (2) flattens placement to `organisms/KVTable.tsx`. Everything else is unchanged from the grill-validated prior design.

## Specialist Consultation

**Invocations**:

- Phase 0 alternatives: no — N/A. State-ownership alternatives were settled in `/discover` (Option A) + the `/specify` decision points; no fresh 2+-alternative discovery required. No new external library.
- Phase 1.3 architecture decisions: yes (mandatory) — `architect` invoked in grill-revision mode; authored the updated Layer Map, Key Design Decision rows (d)/(f), File Impact, and Risk seeds (R11/R12) for the 2 deltas, and re-checked §2.2/§5.2/§6.
- Specialists consulted: `frontend-engineer` (prior run) — validated the caret/focus strategy; carried forward unchanged. No relay this run (both deltas are standard React/CT mechanics).

**Architect-authored sections** (transcribed verbatim from architect return):

- Layer Map: rows 1–8 (flat placement)
- Key Design Decisions: rows a–f (d + f updated for the `validVars` prop; a/b/c/e unchanged)
- Risk Assessment seeds: R7–R10 (prior) + R11–R12 (this revision)
- Constitution Compliance flags: §2.2 (now PASS — flat placement), §5.2/§2.2 sharp (unchanged), §4/AC-31, §2.1/AC-32

| Specialist | Sub-question | Input summary | Verdict | Cites |
| --- | --- | --- | --- | --- |
| architect | Integrate the `validVars` prop seam + flat placement into the plan tables; re-check §2.2/§5.2/§6 | Both deltas integrate cleanly; `validVars` is a defaulted optional prop (not a departure); flat `organisms/KVTable.tsx` is the exact §2.2 remediation; new risks R11 (CT must assert both injected + ∅-default paths) + R12 (prod omits prop until T14); no §6 reach | accepted | own-reasoning; constitution.md §2.2/§5.2; specs/014-kv-table-editor/grill.md |
| frontend-engineer | (prior run) Is the index-key + future-index virtual-row + imperative-refocus caret strategy sufficient (AC-8/13/18/21/25)? | SOUND-WITH-REFINEMENT — imperative refocus must use `useLayoutEffect` + a pending-focus ref; carried forward unchanged | modified | src/renderer/src/components/organisms/RequestBar.tsx; spec §5 AC-13/AC-18/AC-25 |

## Summary

Build KVTable as one renderer **organism** (flat `organisms/KVTable.tsx`) plus two pure **lib** leaves — `varTokens` (the `{{…}}` tokeniser) and `envVars` (the ∅-defaulting validVars selector). The component is fully controlled: it reads the active tab's `Row[]` for its bound field through a frozen-sentinel per-field `tabsStore` selector and writes a fresh `Row[]` back through the existing `updateActiveSpec` action, holding no local copy. KVTable's props are `{ field: 'params'|'headers'; validVars?: ReadonlySet<string> }` — `validVars` defaults to `envVars()` (production ∅) and is the injection seam that lets a CT render a non-empty set to lock the `.var` vs `.var.missing` computed styles (AC-19), while the omitted-prop path keeps AC-20 degradation testable. A render-time virtual trailing row drives auto-promote; index keys (virtual keyed at future index) preserve the caret natively, with `useLayoutEffect` + pending-focus refocus on the discrete delete/Enter events. No new store action, no new runtime dependency, no resolution/autocomplete. Built + CT-isolation-tested only; not mounted.

## Technical Context

**Architecture**: Renderer atomic-design system — KVTable is a flat organism at `organisms/KVTable.tsx` (matching Sidebar/TabBar/RequestBar); `varTokens` + `envVars` are leaf `lib/` modules. Consumes `tabsStore` (read via selector, write via `updateActiveSpec`) and the `Row` type (type-only) from `requestSpec`.
**Error Handling**: Boundary-lookup graceful degradation (§3.2) — `envVars` returns a frozen empty `ReadonlySet<string>` when the env store (T14) is absent; never throws, never returns undefined.
**State Management**: Single source of truth is `tabsStore`; KVTable is a controlled subscriber. Zero component-local row state → external array replacement (cURL import) re-renders cleanly. `validVars` is a read-only render input, never in the write path.

## Constitution Compliance

- §2.2: PASS — flat `organisms/KVTable.tsx` creates no premature single-component domain folder (the exact §2.2 remediation for grill F2). A `request/` subfolder is deferred until a genuine ≥2nd request-domain component lands, at which point both move together.
- §2.2 / §5.2 (SHARP): `requestSpec` never value-imported — KVTable uses `import type { Row }` ONLY (grill CONFIRMED compliant: `import type` is compile-erased). `validVars: ReadonlySet<string>` is a built-in type, no import. **Requires attention** → guarded (Risk R8).
- §4 / AC-31: No inline styles — semantic `.kv*` classes bound to tokens.css. Compliant.
- §2.1 / AC-32: Renderer-only — no `electron`/`node:` imports. Compliant.
- §2.3: `@renderer` alias; lib leaves import nothing from `components/`. Compliant.
- §4 / AC-7: All writes through existing `updateActiveSpec`; no new store action. Compliant.
- §3.1: Strict, no `any` — tokeniser, `Row[]` transforms, the `'params'|'headers'` union, and the `ReadonlySet<string>` prop fully typed. Compliant.
- §3.3: `KVTable.tsx` PascalCase one-per-file + sibling `KVTable.css`; `varTokens`/`envVars` camelCase lib modules; tests co-located `__tests__` split `.test.tsx`/`.ct.tsx`. Compliant.

## Implementation Approach

### Layer Map

| Layer | What | Files (existing or new) |
| ----- | ---- | ----------------------- |
| organisms (flat) | KVTable — controlled key-value grid; props `{ field:'params'\|'headers'; validVars?: ReadonlySet<string> }` (`validVars` defaults to `envVars()`); per-field selector in, `updateActiveSpec` out; derives virtual trailing row; renders checkbox + 3 mono cells + hover-delete; calls varTokens for key/value highlight + applies the missing-flag from `validVars` | src/renderer/src/components/organisms/KVTable.tsx (new) |
| styles (component) | Token-bound `.kv*` semantic classes reproducing the design/styles.css `.kv` block (grid 22px 1fr 1fr 1fr 24px; header/row/cell/checkbox/var/disabled) — no inline styles | src/renderer/src/components/organisms/KVTable.css (new) |
| lib (leaf, pure) | varTokens — pure non-greedy `{{…}}` tokeniser; ordered plain/var segment list; empty/unclosed = plain text; unicode/dot/dash names; no renderer-external import | src/renderer/src/lib/varTokens.ts (new) |
| lib (leaf, boundary selector) | envVars — thin ∅-defaulting active-environment validVars selector; frozen empty `ReadonlySet<string>` until env store T14 lands; never throws/undefined; consumed as the KVTable `validVars` prop default | src/renderer/src/lib/envVars.ts (new) |
| lib (consumed, type-only) | `Row` type source — `import type { Row }` only, never a value import | src/renderer/src/lib/requestSpec.ts (unchanged) |
| lib (consumed, unchanged) | Active-tab `Row[]` read + write seam — existing `updateActiveSpec`; no new action | src/renderer/src/lib/tabsStore.ts (unchanged) |
| styles (consumed) | Existing design-token custom properties bound by KVTable.css | src/renderer/styles/tokens.css (unchanged) |
| tests (co-located) | Playwright CT (mock Row[] + fidelity computed-style asserts; injects a non-empty `validVars` AND asserts the ∅-default neutral path) + stories fixtures; Vitest unit suites for tokeniser edges + ∅-default selector | organisms/__tests__/KVTable.ct.tsx, organisms/__tests__/KVTable.stories.tsx, lib/__tests__/varTokens.test.ts, lib/__tests__/envVars.test.ts (new) |

### Key Design Decisions

| Decision | Chosen Approach | Why | Alternatives Rejected |
| -------- | --------------- | --- | --------------------- |
| (a) State ownership | Controlled grid — derive rows from the store each render, write fresh `Row[]` via `updateActiveSpec`; NO local copy | Matches the RequestBar controlled-input precedent; external cURL array-replace re-renders cleanly (AC-21); satisfies "mutate only via store actions" without a new action (AC-7). In-scope: AC-6/AC-15/AC-21 | local-draft-buffer (resurrects stale edits → violates AC-21); store-row-actions (adds new tabsStore actions → violates AC-7) |
| (b) Trailing empty row | Derived VIRTUAL trailing row (render-time), not stored | Keeps `Row[]` free of a phantom row that would serialize into the wire spec; delete/promote become pure functions of data. In-scope: AC-8/AC-26 | stored empty row (pollutes the array; promote/delete bookkeeping bugs) |
| (c) Tokeniser placement | Separate pure `lib/varTokens.ts` module | Unit-testable in isolation (§3.6, AC-2/AC-9/AC-22); no React/DOM dependency; single responsibility | inline in KVTable (untestable in isolation → fails AC-2) |
| (d) One component / two mounts — **DEPARTURE** | Single KVTable.tsx with props `{ field:'params'\|'headers'; validVars?: ReadonlySet<string> }` (`validVars` defaults to `envVars()`); per-field selector `s => activeTab?.spec[field] ?? EMPTY_ROWS` returning a module-level frozen sentinel | DRY single authoring, two mounts (AC-10); the optional `validVars` prop is the F1 injection seam — a CT passes a non-empty set, production callers omit it and get the ∅-default. Adding a defaulted prop is standard React, NOT a departure. **DEPARTURE (unchanged)**: RequestBar selects primitives (`?? ''`); this selects an array, so the array fallback MUST be a hoisted frozen constant — a fresh `[]` per call breaks zustand `Object.is` and loops (R7) | one component per field (violates AC-10); inline `?? []` fallback (re-render loop) |
| (e) Caret / focus preservation — **DEPARTURE** | Stable numeric row keys `key={index}`; virtual trailing row keyed at its FUTURE index (`key={rows.length}`) so promotion reuses the same DOM node and native caret preservation holds mid-type; a per-cell ref registry drives IMPERATIVE focus via `useLayoutEffect` + a pending-focus ref ONLY on discrete delete (refocus adjacent) and Enter-commit (focus new row's cell) | Per-keystroke typing never reorders indices → same key → same node → React preserves caret natively. Refocus runs in `useLayoutEffect` (pre-paint), not `useEffect` — else a painted frame lands focus on `document.body` (AC-13 fail); Enter-commit needs a pending-focus `{rowIndex,column}` ref because the new row's node exists only after the post-write render. **DEPARTURE**: establishes the grid-caret convention. In-scope: AC-8/AC-13/AC-18/AC-25 | array-index keys with no future-index trick (promote remounts → caret jump); synthetic per-row uuid on Row (mutates the serializable shape → forbidden §2.2/§5.2); fully-imperative caret every keystroke (fragile) |
| (f) ∅-default validVars via defaulted prop | KVTable accepts `validVars?: ReadonlySet<string>` defaulting to `envVars()`; render `.var.missing` ONLY when `validVars.size > 0` AND name absent, else neutral `.var`. States: neutral `.var` exercised by AC-20 (∅-default); `.var.missing` exercised by AC-19 (CT injects a non-empty set) | Graceful boundary degrade (§3.2) — production omits the prop → `envVars()` frozen `EMPTY_SET` → the `size > 0` gate keeps every token neutral (AC-20 preserved); the prop lets a CT render a non-empty set to lock `.var` vs `.var.missing` computed styles (AC-19, spec §7 fidelity + §9.1). NOT a departure — defaulted optional prop is standard React. In-scope: AC-19/AC-20 | internal-only `envVars()` call with no prop (F1: `.var.missing` unreachable under CT → AC-19 + fidelity assertion untestable — the defect being fixed); returning undefined/null (null-checks); throwing (§3.2); fresh `new Set()` per call (identity loop) |

### Established-Convention Departures

| Departure | Established Pattern Left | Why Necessary |
| --------- | ----------------------- | ------------- |
| (d) Frozen-sentinel array selector | RequestBar's per-field selectors return primitives with a bare literal fallback (`?? ''`) | Selecting an **array** with a fresh `?? []` fallback returns a new reference each call → zustand `Object.is` mismatch → infinite re-render loop. The array fallback MUST be a module-level frozen constant. |
| (e) Grid-caret via index keys + `useLayoutEffect` refocus | No prior renderer component has dynamic add/remove rows with focus continuity (RequestBar is a single static input) | A dynamic controlled grid must preserve the caret across store-driven re-renders and keep focus off `document.body` on row removal — neither is solved in the codebase. Establishes the convention. |

### File Impact

| File | Action | What Changes |
| ---- | ------ | ------------ |
| src/renderer/src/components/organisms/KVTable.tsx | Create | The controlled grid organism (`{ field, validVars? }` props, selector-in/updateActiveSpec-out, virtual trailing row, index keys + layout-effect refocus, varTokens/envVars calls). |
| src/renderer/src/components/organisms/KVTable.css | Create | Semantic `.kv*` classes bound to tokens.css reproducing the design/styles.css `.kv` block. |
| src/renderer/src/lib/varTokens.ts | Create | Pure non-greedy `{{…}}` tokeniser returning ordered plain/var segments. |
| src/renderer/src/lib/envVars.ts | Create | ∅-defaulting validVars selector (frozen empty `ReadonlySet`); serves as the KVTable `validVars` prop default. |
| src/renderer/src/components/organisms/__tests__/KVTable.ct.tsx | Create | Playwright CT: grid behaviour + fidelity computed-style asserts; injects a non-empty `validVars` to exercise `.var` vs `.var.missing` (AC-19) AND omits it to assert the ∅-default all-neutral path (AC-20). |
| src/renderer/src/components/organisms/__tests__/KVTable.stories.tsx | Create | CT fixture components (full styling context: tokens.css import + border-box scope). |
| src/renderer/src/lib/__tests__/varTokens.test.ts | Create | Vitest unit suite for the tokeniser edge rules. |
| src/renderer/src/lib/__tests__/envVars.test.ts | Create | Vitest unit suite for the ∅-default selector. |

_Consumed unchanged (no rows above): src/renderer/src/lib/tabsStore.ts, src/renderer/src/lib/requestSpec.ts (type-only Row import), src/renderer/styles/tokens.css._ Planning-discovered addition (see R8): an ESLint `no-restricted-imports` guard blocking a runtime import of `requestSpec` from `components/` — carried as a risk mitigation, not a required file change; `/breakdown` decides whether it lands as a task.

### Documentation Impact

| Doc File | Action | What Changes |
| -------- | ------ | ------------ |
| docs/renderer/index.md | Update | Add KVTable to the flat `organisms/` concern tree and the two lib modules (varTokens, envVars). |

_Handled by tech-writer at `/finalize`; no doc edits during implementation._

## Risk Assessment

Spec §9 risks 1–6 remain in force (fidelity drift, controlled-input caret, external-mutation race, validVars ∅ mis-fire, CT fixture scoping, CT watchdog). The highest-severity two are restated with refinements, followed by the architect seeds (R7–R10 prior, R11–R12 from this revision).

| Risk | Likelihood | Impact | Mitigation |
| ---- | ---------- | ------ | ---------- |
| (spec §9.2, refined) Controlled-input caret jump or focus lost to `document.body` on re-render / delete / auto-promote | High | High | Index keys with the virtual row keyed at its future index; imperative refocus via `useLayoutEffect` + pending-focus ref on delete + Enter-commit ONLY; pin AC-13/AC-18/AC-25 as required CT scenarios. |
| (spec §9.1) Fidelity drift slips past static review | Med | High | Computed-style CT assertions locking every pinned `.kv` value across states (incl. the now-reachable `.var.missing` via injected `validVars`); runtime design-auditor; never trust a green static pass. |
| R7 — Array selector identity loop: `spec[field] ?? []` returns a fresh reference each call → zustand `Object.is` mismatch → infinite re-render loop | High | Med | Select the RAW stored array ref with a module-level frozen `EMPTY_ROWS` fallback; derive the virtual trailing row in the render body, NEVER inside the selector. |
| R8 — Type-only-import erosion (§2.2 sharp): a later value-import of a runtime member from `requestSpec` breaks the pure-data-module invariant | Med | High | Pin `import type { Row }`; add an ESLint `no-restricted-imports` guard so a value import of `requestSpec` from `components/` fails lint/build. |
| R9 — Paste double-promote: an `onPaste` (newline-collapse) plus the subsequent `onChange` each trigger a promote → two trailing rows (AC-24) | Med | Med | Make promote a pure function of the RESULTING rows, not of event count; collapse newlines before the single write. |
| R10 — Description-cell tokenise leak: a shared cell renderer accidentally tokenises the description cell (AC-11) | Low | Med | Gate the varTokens call by cell kind — key/value only; description renders verbatim. |
| R11 — Injection seam masks an AC-20 regression: a CT that only tests the injected non-empty `validVars` path never exercises the production ∅-default, so a broken `size > 0` gate (flag-everything) could ship green | Med | Med | The KVTable CT MUST assert BOTH paths: (1) non-empty `validVars` → `.var` vs `.var.missing` computed styles (AC-19); (2) prop omitted / `envVars()` ∅-default → every token neutral `.var`, zero `.var.missing` (AC-20). Pin both as required CT scenarios in `/breakdown`. |
| R12 — Default drift: a production caller passing an explicit `validVars` before env store T14 lands would render live missing-flags outside the ∅-default contract | Low | Low | KVTable's two production mounts (params/headers) MUST omit `validVars` in v1 so the `envVars()` default holds; `/breakdown` note — no caller supplies the prop until T14. |

## Dependencies

None new. Reuses installed `zustand`, `radix-ui` (not needed for v1 grid), React 19, and the Vitest + Playwright CT stack. No package to install, no service, no environment variable.

## Supporting Documents

- None. No deep-research signals (approach settled in `/discover` + `/specify`, grill-validated). No new/changed data entities (reuses the existing `Row` type). No API contracts.
