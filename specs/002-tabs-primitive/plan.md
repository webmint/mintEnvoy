# Plan: tabs-primitive

**Date**: 2026-06-23
**Spec**: specs/002-tabs-primitive/spec.md
**Status**: Approved

## Specialist Consultation

**Invocations**:

- Phase 0 alternatives: yes — see research.md §Alternatives Compared (selection-only strip vs Radix `aria-controls` coupling; A vs B vs C). Seeded from the upstream discover plan-seeds (build-vs-buy + options A/B/C); only the unsettled `aria-controls` reconciliation was carried into the architect decision.
- Phase 1.3 architecture decisions: yes (mandatory)
- Specialists consulted (orchestrator-relayed on the architect's request, or directly): none beyond the architect — see Specialist Consultation table.

**Architect-authored sections** (transcribed verbatim from architect return):

- Layer Map: all rows
- Key Design Decisions: all rows
- Risk Assessment seeds: all rows
- Constitution Compliance flags: §2.1, §2.3, §3.1, §3.4, §6.3 (see Constitution Compliance)

| Specialist | Sub-question | Input summary | Verdict | Cites |
| --- | --- | --- | --- | --- |
| architect | Resolve selection-only vs Radix `aria-controls` coupling (A wrap+strip vs B hand-roll vs C share-root); author Layer Map / Key Design Decisions / Risk / Constitution rows | Pick B (hand-roll `role=tablist`): Radix `Tabs.Trigger` deterministically emits `aria-controls` to a sibling `Content`; with no Content (selection-only) it dangles → axe → fails AC-7. Hand-roll gives clean ARIA + decoupling; veneer still mirrors Dropdown. Flagged DEPARTURE from §6.3 "wrap Radix" precedent, accepted. No §6 escalations. | accepted | research.md §Alternatives Compared; spec.md AC-7, §6; constitution.md §6.3 |

## Summary

Build a single controlled, selection-only, horizontal-only `Tabs` primitive (`Tabs.tsx` + `Tabs.css`) under `src/renderer/src/components/molecules/`, registered in the dev-only PrimitivesDemo route and covered by Vitest + Playwright CT tests. The central design call — resolved by the mandatory architect consultation — is to **hand-roll the WAI-ARIA tablist** (`role="tablist"`/`role="tab"` + manual roving tabindex) rather than wrap Radix Tabs: Radix `Tabs.Trigger` deterministically emits `aria-controls` pointing at a sibling `Tabs.Content`, and with no Content mounted (the selection-only mandate) that attribute dangles and fails AC-7. The project veneer (flat descriptor-array API, `cx()` BEM classes, `import './Tabs.css'`, JSDoc, exported types) still mirrors the Dropdown precedent — only the accessibility engine diverges.

## Technical Context

**Architecture**: Renderer-only, presentation layer. Touches `components/molecules/` (the `Tabs` component + stylesheet) and `components/PrimitivesDemo.tsx`; reuses `lib/cx.ts`. No main/preload/IPC involvement; no network, no persistence.
**Error Handling**: No fallible operations in scope (pure render from props). The one defensive path is the render-no-selection guard (AC-10): an `activeId` that matches no enabled tab renders no `aria-selected` tab and auto-selects nothing — handled as the absence of a match, not an error.
**State Management**: Controlled-only. The caller owns `activeId` and updates it via `onChange(id)`; the component holds zero internal active state (no zustand store needed — this is a leaf presentation primitive, matching the Dropdown `open`/`onOpenChange` controlled precedent).

## Constitution Compliance

- §2.1 (no Node/electron in renderer): **compliant** — pure React + `cx`; the hand-rolled path removes even the Radix import. Asserted by AC-15.
- §2.3 (@renderer alias): **compliant** — import `cx` (and `Icon` if ever added) via `@renderer/...`, never deep relative paths.
- §3.1 (strict, no `any`, typed exports): **compliant** — export `TabDescriptor` + `TabsProps` with full JSDoc; no `any`. Asserted by AC-12.
- §3.4 (testing): **compliant (requires attention)** — Vitest `.test.tsx` + Playwright CT `.ct.tsx` under `__tests__/`. The hand-rolled engine raises the bar: coverage must include every keyboard/disabled/no-selection branch, not just click.
- §6.3 (search before building): **requires attention — accepted tradeoff** — the hand-rolled tablist does NOT reuse Radix's Tabs a11y engine, which §6.3 would otherwise favor. Accepted because reusing Radix here fails AC-7 (dangling `aria-controls`). §6.3 is satisfied at the veneer layer (reuses `cx`, the molecules wrapper shape, the Icon atom, the existing radix-ui dependency) and introduces no second accessibility library. This is the headline DEPARTURE.
- §6.6 (workflow / commits): **compliant** — Conventional Commits; WIP commits squash at /finalize.

## Implementation Approach

### Layer Map

| Layer | What | Files (existing or new) |
| --- | --- | --- |
| molecules | The `Tabs` primitive — hand-rolled `role="tablist"` strip rendering tab buttons from a flat descriptor array; controlled via `activeId`/`onChange`; selection-only (renders no panels); optional right-aligned `actions` slot | `src/renderer/src/components/molecules/Tabs.tsx` (new) |
| molecules (styles) | Sibling token-bound stylesheet; semantic BEM classes bound to `tokens.css`; no inline styles; `prefers-reduced-motion` guard | `src/renderer/src/components/molecules/Tabs.css` (new) |
| lib | Reused `cx()` className composer for BEM assembly (no change) | `src/renderer/src/lib/cx.ts` (reuse) |
| atoms | `Icon` atom available for a future per-tab leading icon; not required by the in-scope ACs (reuse only if added) | `src/renderer/src/components/atoms/Icon.tsx` (reuse, optional) |
| dev gallery | Register `Tabs` for manual visual fidelity check vs `design/reference.html` | `src/renderer/src/components/PrimitivesDemo.tsx` (edit) |
| tests | Vitest + Testing Library interaction tests; Playwright CT keyboard/focus tests | `src/renderer/src/components/molecules/__tests__/Tabs.test.tsx`, `src/renderer/src/components/molecules/__tests__/Tabs.ct.tsx` (new) |

### Key Design Decisions

| Decision | Chosen Approach | Why | Alternatives Rejected |
| --- | --- | --- | --- |
| a11y engine | Hand-roll `role="tablist"`/`role="tab"` buttons with manual roving tabindex + Arrow/Home/End/wrap + disabled-skip | **DEPARTURE: diverges from the Dropdown/Modal/Toast "wrap Radix" a11y precedent — justified because Radix `Tabs.Trigger` deterministically emits `aria-controls` to a sibling `Tabs.Content` (Context7-confirmed in research.md); with no Content mounted (selection-only, §6) that attribute dangles → axe violation → fails AC-7. Hand-rolling gives clean ARIA + full panel-decoupling (AC-7, §1). The veneer (flat array API, cx() BEM, import './Tabs.css', JSDoc, exported types) still mirrors Dropdown.** | A (wrap Radix + strip `aria-controls`): fights Radix internals, version-fragile post-render override, residual axe-violation risk vs AC-7. C (share one `Tabs.Root` with panels): consumers don't exist (§6 OOS), couples the primitive, breaks decoupled mandate. |
| controlled-only state | Caller owns `activeId`; component holds zero internal active state; `onChange(id)` emits the request | Matches §7 constraint + the 001 Dropdown/Modal controlled precedent (`open`/`onOpenChange`); consistent, not a departure | Uncontrolled / `defaultActiveId` self-managed mode — §6 OOS |
| keyboard activation | Automatic — Arrow/Home/End move selection immediately and fire `onChange` | AC-6; spec-locked behavior | Manual activation (move focus, activate on Enter/Space) — §6 OOS |
| badge type | `badge?: string \| number` | Spec-locked; keeps the descriptor a plain serializable shape; mirrors Dropdown's primitive-typed descriptor fields | `ReactNode` badge — §6 OOS |
| actions slot | Optional `actions?: React.ReactNode`, rendered right-aligned at strip end, outside the `tablist` element | AC-8; `React.ReactNode` slot consistent with Dropdown's `trigger` prop | Render-prop / render-slot actions option (discovery option C) — §6 OOS |
| render-no-selection guard | When `activeId` matches no enabled tab (no match / empty array / all-disabled), render no `aria-selected` tab and auto-select nothing; roving tabindex falls back to the first enabled tab as the single tab-stop | AC-10; selection-only means the component never auto-picks. Single-state guard, no status enum introduced | Auto-selecting the first enabled tab on no-match — contradicts AC-10 |

State-cardinality note: no discriminated union / enum / status field is introduced. `activeId` is a plain `string`; the "no active selection" case (AC-10) is the absence of a match, not a distinct declared state.

### Established-Convention Departures

| Departure | Established Pattern Left | Why Necessary |
| --- | --- | --- |
| Hand-rolled WAI-ARIA tablist (manual roving tabindex / Arrow-Home-End / disabled-skip / `aria-selected`) | Dropdown/Modal/Toast wrap a `radix-ui` namespace for their a11y engine ("buy the engine", constitution §6.3) | Radix `Tabs.Trigger` deterministically emits `aria-controls` to a sibling `Tabs.Content`; the selection-only strip mounts no Content (§6), so that attribute dangles → axe violation → fails AC-7. No first-class Radix "tablist without content" mode exists; stripping the attribute post-render is fragile and version-sensitive. Hand-rolling the small, APG-specified pattern is the only path that satisfies AC-7 while keeping the primitive decoupled. The component veneer still mirrors Dropdown — only the a11y engine diverges. |

### File Impact

| File | Action | What Changes |
| --- | --- | --- |
| src/renderer/src/components/molecules/Tabs.tsx | Create | The `Tabs` primitive: exported `TabDescriptor` + `TabsProps` types, hand-rolled `role="tablist"` render from `tabs[]`, controlled `activeId`/`onChange`, roving tabindex + Arrow/Home/End/wrap + disabled-skip, no-selection guard, optional right-aligned `actions` slot, JSDoc citing each AC (Dropdown precedent) |
| src/renderer/src/components/molecules/Tabs.css | Create | Semantic BEM classes bound to `tokens.css` custom properties; no inline styles; `@media (prefers-reduced-motion: reduce)` guard for any transition |
| src/renderer/src/components/PrimitivesDemo.tsx | Modify | Register a `Tabs` section rendering both the request-pane (6-tab) and response-pane (4-tab) sets for manual visual fidelity vs `design/reference.html` |
| src/renderer/src/components/molecules/__tests__/Tabs.test.tsx | Create | Vitest + Testing Library interaction tests: click→onChange-once (AC-5), arrow/Home/End wrap (AC-6), disabled-skip + no-onChange-on-disabled (AC-9), no-selection guard (AC-10), tablist/tab roles + aria-selected (AC-7) |
| src/renderer/src/components/molecules/__tests__/Tabs.ct.tsx | Create | Playwright CT real-browser focus/keyboard fidelity: roving tabindex single tab-stop, focus movement, keyboard activation; assert zero axe a11y violations (AC-7) |

### Documentation Impact

| Doc File | Action | What Changes |
| --- | --- | --- |
| docs/renderer/architecture.md (or docs/architecture.md §Renderer UI Primitives Layer) | Update | Add `Tabs` to the molecules sublayer inventory; note it hand-rolls its a11y engine (the documented exception to the "wrap Radix" rule) |
| docs/glossary.md | Update | Add a `Tabs` term (controlled selection-only tab-strip primitive) |

Docs are surgically updated by tech-writer at /finalize — listed here for traceability, not built during /implement.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Dangling `aria-controls` → axe violation → AC-7 fails (the core Radix-coupling tension) | High (under rejected Option A) | High | Resolved by the Option B decision — the hand-rolled tablist emits no `aria-controls`; assert zero axe a11y violations in the CT test against AC-7's roles / `aria-selected` / roving-tabindex |
| Larger interaction-test surface — reimplemented roving tabindex + Arrow/Home/End/wrap + disabled-skip must be covered (the `verify_cost=Med` discovery flagged) | Med | Med | Derive the test matrix directly from AC-5/6/9/10 (click-once, arrow-wrap, Home/End, disabled-skip, no-onChange-on-disabled, no-selection guard); split Vitest interaction vs Playwright CT focus/keyboard per the 001 pattern |
| Hand-rolled roving tabindex regresses focus management vs Radix's tested implementation | Med | Med | Follow the WAI-ARIA APG Tabs pattern exactly (single tab-stop; `tabindex=0` on active/first-enabled, `-1` elsewhere); cover with Playwright CT focus assertions |
| Visual drift from `design/reference.html` at request-pane (6-tab) and response-pane (4-tab) widths | Med | Low | Register in PrimitivesDemo; manual visual compare at both widths; overflow handling is explicitly §6 OOS (do not solve here) |

## Dependencies

- No new packages. radix-ui ^1.1.3 stays a dependency (used by Dropdown/Modal/Toast); the hand-rolled `Tabs` introduces no second accessibility library, so AC-3 (`grep -q '"radix-ui"' package.json` + no second a11y lib) is satisfied at the dependency level. Vitest + @testing-library/react + user-event + Playwright CT are already configured (feature 001). No new env vars or services.

## Supporting Documents

- [Research](research.md) — aria-controls coupling investigation + A/B/C alternatives (Context7-confirmed Radix behavior)
