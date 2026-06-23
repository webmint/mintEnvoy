# Research: tabs-primitive

**Date**: 2026-06-23
**Signals detected**: Architectural decision with multiple valid approaches — how a *selection-only* tab-strip reconciles with Radix Tabs' `Trigger → Content` `aria-controls` coupling (flagged unresolved by the upstream discover handoff, "resolved at plan time"). radix-ui itself is already a project dependency, so it is NOT a signal; the decision is the design reconciliation, not the library adoption.

## Questions Investigated

1. Does Radix `Tabs.Trigger` require a matching `Tabs.Content`? → **Yes, by design.** Context7 (`/websites/radix-ui_primitives`, radix-ui Tabs docs): the anatomy is `Tabs.Root > Tabs.List > Tabs.Trigger` **+** `Tabs.Content`; `Trigger.value` is required and the Trigger "activates its associated content," rendering `aria-controls` that points at the `Content` with the matching `value`. With no `Tabs.Content` mounted (our selection-only strip), each Trigger's `aria-controls` references an id that is not in the DOM — axe flags this as a violation, which fails **AC-7** ("WAI-ARIA tablist/tab roles … correct"). This is the core design tension.
2. Do Radix defaults match the spec's decided behavior? → **Yes.** `Tabs.Root` defaults: `activationMode="automatic"` (matches the spec's automatic-activation decision) and `orientation="horizontal"` (matches horizontal-only). `Tabs.List` supplies arrow/Home/End keyboard nav + loop wrap; `Tabs.Trigger.disabled` supplies disabled-skip. So *if* Radix is used, keyboard + roving-tabindex behavior (AC-6) comes for free.
3. What is the established project pattern for a primitive like this? → **Thin Radix wrapper.** `Dropdown.tsx` (and Modal/Toast) wrap a `radix-ui` namespace behind a flat descriptor-array API: `import './X.css'`, `import { <Namespace> } from 'radix-ui'`, `cx()` for BEM classes, `Icon` atom, exported `*Descriptor` interface, JSDoc citing each AC. `Tabs` should mirror this shape regardless of the build-vs-buy outcome (the veneer is identical; only the a11y engine differs).

## Alternatives Compared

### Selection-only strip vs Radix Tabs `aria-controls` coupling (the decision deferred from discovery)

| Option | Pros | Cons | Verdict |
| --- | --- | --- | --- |
| A — Wrap Radix `Tabs.Root/List/Trigger`, suppress the dangling `aria-controls` | Inherits roving tabindex, List-loop wrap, disabled-skip, activationMode, tablist/tab roles for free; no new a11y code; consistent with Dropdown/Modal/Toast "buy the engine" | Fights Radix internals — `aria-controls` is set deterministically by Trigger and must be stripped/overridden post-render (fragile, version-sensitive); risk of residual axe violation; "no Content" is outside Radix's intended usage | **Architect to decide** (Phase 1.3) |
| B — Hand-roll `role="tablist"` + `role="tab"` buttons | Clean ARIA with zero dangling `aria-controls`; full panel-decoupling matching the selection-only scope; no Radix-internal fighting | Reimplements roving tabindex + arrow/Home/End/wrap + disabled-skip → larger interaction-test surface (the verify_cost=Med the discovery flagged); diverges from the "wrap Radix" precedent for the a11y layer (veneer still matches) | **Architect to decide** (Phase 1.3) |
| C — Share one `Tabs.Root` with consumer panels | Uses Radix exactly as intended; `aria-controls` resolves to real Content | Couples the primitive to its call sites; consumer panes do not exist yet (§6 OOS); breaks the decoupled-reusable mandate | **Rejected** — violates the spec's selection-only / decoupled scope (§1, §6) |

**Decision**: Deferred to the mandatory Phase 1.3 `architect` consultation — A vs B is a real tradeoff (inherited-a11y-with-fragile-override vs clean-ARIA-with-reimplemented-nav) that the architect owns. Upstream discovery recommended Hybrid (buy Radix) with hand-roll as the fallback "if aria-controls reconciliation proves awkward"; this research confirms the reconciliation is non-trivial (Radix has no first-class "tablist without content" mode), so the fallback is live, not theoretical.

## References

- Context7 `/websites/radix-ui_primitives` — Tabs anatomy, Trigger/Content/Root API, defaults (`activationMode="automatic"`, `orientation="horizontal"`), keyboard interactions. Source: https://www.radix-ui.com/primitives/docs/components/tabs
- WAI-ARIA APG Tabs pattern — https://www.w3.org/WAI/ARIA/apg/patterns/tabs/ (authoritative for the hand-rolled path: role=tablist/tab, aria-selected, roving tabindex, arrow/Home/End)
- Internal precedent: src/renderer/src/components/molecules/Dropdown.tsx (controlled descriptor-array Radix wrapper; JSDoc + cx + Icon + `import './Dropdown.css'`)
- Upstream discovery: discover/2026-06-22-reusable-horizontal-tab-strip-primitive-for-switching.md (§Build vs Buy, §Derisk Plan)
