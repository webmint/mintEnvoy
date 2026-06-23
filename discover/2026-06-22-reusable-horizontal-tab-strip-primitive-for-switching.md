# Discovery: Reusable horizontal tab-strip primitive for switching panels within a pane — tabs array + active id, optional count/label badge per tab, optional right-aligned action cluster, emits change events

**Date**: 2026-06-22
**Topic**: Reusable horizontal tab-strip primitive for switching panels within a pane — tabs array + active id, optional count/label badge per tab, optional right-aligned action cluster, emits change events
**Verdict**: Worth pursuing

## Summary

A reusable, controlled, horizontal-only tab-strip primitive for switching panels within a pane (request authoring + response panes first; general-purpose after). The project already adopted radix-ui ^1.1.3 and wraps it in three controlled primitives (Dropdown/Modal/Toast) in src/renderer/src/components/molecules/, and Radix ships a Tabs namespace that supplies controlled value/onValueChange, roving tabindex, keyboard wrap (List loop), disabled-skip, and full WAI-ARIA — so fit is Good and effort Low with no new dependency. Recommended direction: a flat array-driven controlled API wrapping Radix Tabs, matching Dropdown's items-array precedent. Primary risk: Radix Tabs.Trigger emits aria-controls expecting a sibling Tabs.Content, which tensions the selection-only / panels-separate scope and must be resolved at plan time (share one Tabs.Root with consumer panels, or hand-roll the tablist).

## Prior Art

| Reference | Kind | Relevance | Source |
|---|---|---|---|
| Dropdown (Radix DropdownMenu wrapper) | pattern | internal — canonical controlled-primitive-wrapping-Radix pattern to extend for Tabs (cx + Icon + BEM + import './X.css') | internal:src/renderer/src/components/molecules/Dropdown.tsx |
| Toast (Radix Toast wrapper) | pattern | internal — same controlled Radix-namespace wrapper pattern; Provider/Viewport split, store-driven | internal:src/renderer/src/components/molecules/Toast.tsx |
| Modal (Radix Dialog wrapper) | pattern | internal — controlled Radix wrapper primitive; focus trap, prefers-reduced-motion gating precedent | internal:src/renderer/src/components/molecules/Modal.tsx |
| cx() class-name helper | pattern | internal — shared semantic-class composer used by every primitive; Tabs reuses it | internal:src/renderer/src/lib/cx.ts |
| PrimitivesDemo harness | pattern | internal — visual-verification route where each primitive is registered; success_criteria requires Tabs added here | internal:src/renderer/src/components/PrimitivesDemo.tsx |
| Radix Tabs (radix-ui Tabs namespace) | library | Controlled value/onValueChange, roving tabindex, Tabs.List loop=keyboard wrap, Trigger disabled-skip, activationMode auto/manual, horizontal default, full WAI-ARIA — covers nearly all gap behavior; already a dep (no new install). Caveat: Trigger sets aria-controls expecting a Tabs.Content. | https://www.radix-ui.com/primitives/docs/components/tabs |
| WAI-ARIA APG Tabs pattern | pattern | Authoritative spec for the hand-rolled path: role=tablist/tab, aria-selected, roving tabindex, arrow/Home/End, automatic-vs-manual activation guidance | https://www.w3.org/WAI/ARIA/apg/patterns/tabs/ |
| React Aria useTabList | library | Alternative headless tabs hook; would be a SECOND a11y lib alongside Radix — violates the 'no second library' guidance, recorded for completeness | https://react-spectrum.adobe.com/react-aria/Tabs.html |

## Integration Surface

| Touchpoint | Module/file | Why touched |
|---|---|---|
| molecules primitives dir | src/renderer/src/components/molecules | home of Dropdown/Modal/Toast; new Tabs.tsx + Tabs.css land here following the same wrapper pattern |
| cx helper | src/renderer/src/lib/cx.ts | semantic-class composer Tabs reuses for BEM class assembly |
| Icon atom | src/renderer/src/components/atoms/Icon.tsx | reused if a per-tab leading icon is ever added; consistent with Dropdown item icons |
| PrimitivesDemo route | src/renderer/src/components/PrimitivesDemo.tsx | Tabs registered here for manual visual fidelity check vs design/reference.html |
| radix-ui dependency | package.json | radix-ui ^1.1.3 already declared; Tabs namespace available with no new dependency |

## Fit Assessment

| Touchpoint | User expected | Reality (scan) | Effort | Blockers |
|---|---|---|---|---|
| molecules primitives dir | new tab-strip lives beside Dropdown/Modal/Toast and follows the same wrapper pattern | confirmed — molecules/ holds the three controlled Radix-wrapper primitives; Tabs.tsx + Tabs.css drop in cleanly with cx()+Icon+import './Tabs.css' | Low | none |
| radix-ui dependency | reuse whatever headless lib 001 adopted; do not add a second one | confirmed — radix-ui ^1.1.3 is adopted and exposes a Tabs namespace; no new dependency needed. BUT Radix Tabs.Trigger emits aria-controls expecting a sibling Tabs.Content; selection-only (panels separate) means either consumers share one Tabs.Root with their panels, or the strip hand-rolls role=tablist to stay panel-decoupled | Medium | Radix Tabs couples Trigger->Content via aria-controls; a standalone selection-only strip risks dangling aria-controls unless panels join the same Tabs.Root or the tablist is hand-rolled |
| PrimitivesDemo route | register Tabs in the demo for manual visual verification | confirmed — PrimitivesDemo.tsx already registers each primitive; success_criteria's manual visual check plugs in here | Low | none |
| cx helper | reuse cx() for semantic BEM classes | confirmed — cx() at src/renderer/src/lib/cx.ts is used by every primitive | Low | none |

**Overall fit**: Good
**Effort estimate**: Low
**Rationale**: Strong fit. The controlled-primitive-wrapping-Radix pattern is established three times in src/renderer/src/components/molecules/ and radix-ui (which ships a Tabs namespace) is already a dependency, so the user's 'reuse it, no second lib' belief is confirmed and the build is small. The single real wrinkle is design-time, not effort: Radix Tabs couples Trigger->Content via aria-controls, which tensions the selection-only/panels-separate scope — resolved by either sharing one Tabs.Root with consumer panels or hand-rolling the tablist. Either path stays within the existing pattern and needs no new dependency.

## Design Options

### Option A: Array-driven controlled strip
- **Shape**:
```
Flat props: <Tabs tabs={[{id,label,badge?,disabled?}]} activeId onChange actions?/>. One component renders the whole strip from the array; caller owns activeId and handles onChange(id). Mirrors Dropdown's items-array API.
```
- **Pros**:
  - Matches the API the user described (tabs array + active id)
  - Smallest consumer surface; one line to mount
  - Direct precedent in Dropdown items-array API
- **Cons**:
  - Less composable for one-off custom tab content
  - Badge limited to string|number unless widened
- **Complexity**: Low

### Option B: Compound components
- **Shape**:
```
Children API: <Tabs.Root activeId onChange><Tabs.List><Tabs.Tab id badge/>...</Tabs.List><Tabs.Actions/></Tabs.Root>. Composition mirrors Radix and Dropdown's children API; each tab is JSX.
```
- **Pros**:
  - Maximum composition flexibility (custom tab nodes, arbitrary actions)
  - Closest 1:1 to Radix Tabs structure
- **Cons**:
  - More verbose at every call site
  - More exported parts to document and test
  - Diverges from the simple array the user asked for
- **Complexity**: Med

### Option C: Array + slot nodes
- **Shape**:
```
Array-driven like option A, but badge accepts a ReactNode and actions is a render slot; tabs={[{id,label,badge?:ReactNode,disabled?}]} actions={<.../>}. Hybrid of A's ergonomics and B's flexibility.
```
- **Pros**:
  - Keeps the simple array call site
  - Allows rich badges / custom action clusters without compound parts
- **Cons**:
  - ReactNode badge complicates ARIA labelling and tests
  - Two ways to express simple cases invites inconsistency
- **Complexity**: Med

**Recommended option**: Array-driven controlled strip — It matches the API the user described (tabs array + active id + onChange) and extends the established controlled-primitive wrapper pattern at internal:src/renderer/src/components/molecules/Dropdown.tsx — those primitives implement the Radix-wrapper pattern but NOT tab-strip selection, which is the capability this option adds. Tradeoff accepted: badge stays string|number and one-off custom tab content is unsupported; if a richer badge is ever needed, widen to option C without breaking the array call site.

## Build vs Buy

| Build | Buy/Adopt |
|---|---|
| Hand-roll the strip: role=tablist + role=tab buttons, manual roving tabindex (arrows/Home/End with wrap), aria-selected, disabled-skip, onChange(id). Full panel-decoupling (no aria-controls coupling), but reimplements well-trodden a11y and carries the larger test surface. | Wrap radix-ui's Tabs namespace (Tabs.Root + Tabs.List + Tabs.Trigger) behind the flat array API. Inherits controlled value/onValueChange, roving tabindex, List loop (keyboard wrap), Trigger disabled-skip, activationMode, and WAI-ARIA for free; no new dependency. Must manage Trigger->Content aria-controls for the selection-only strip. |

**Recommendation**: Hybrid — Buy the accessibility engine (Radix Tabs, already a dependency), build the thin project veneer (the flat array wrapper + semantic classes) — exactly how Dropdown/Modal/Toast already treat Radix. This minimizes new a11y code and stays consistent with the codebase. The only design-time work is reconciling aria-controls with the panels-separate scope; pure hand-rolling is the fallback if that reconciliation proves awkward.

## Derisk Plan

1. Spike: render Radix Tabs.Root+List+Trigger as a selection-only strip WITHOUT Tabs.Content; run axe/a11y to check for dangling aria-controls and decide share-one-Root vs hand-rolled tablist
2. Contract test against both panes tab sets: click + arrows/Home/End wrap (List loop), disabled-skip, onChange(id) fires once, aria-selected/tablist roles correct, invalid/absent activeId renders no selection
3. Register in PrimitivesDemo.tsx and visually compare to design/reference.html at request-pane (6 tabs) and response-pane (4 tabs) widths

## Constitution Constraints

| Rule | Impact |
|---|---|
| §3.1 Type Safety (no any, strict) | Tab descriptor, props, and onChange must be fully typed; no any. Public Tabs/Tab types exported and strict-mode clean. |
| §2.3 / Never import Node or electron in renderer | Tabs is renderer-only; pure React + radix-ui + cx, no Node/electron imports — consistent with the other molecules. |
| §3.4 Testing Requirements | success_criteria's behavior/keyboard/ARIA gate is met with interaction tests mirroring the existing Dropdown/Toast __tests__ patterns. |
| §6.3 Search Before Building | Satisfied: reuses radix-ui (adopted), cx(), Icon atom, and the molecules wrapper pattern rather than introducing new machinery or a second a11y library. |
| Prefer @renderer alias | Imports use @renderer/* (cx, Icon) per the existing primitives, not deep relative paths. |

## Open uncertainties

[NEEDS CLARIFICATION: integration_points — user-supplied mechanism guess (confirm via Phase 2 fit-check): reuse whatever headless tabs library specs/001-ui-primitives adopted (Dropdown/Modal/Toast/Icon) rather than introducing a second; assumes 001 adopted a headless lib at all]

## Recommendation

**Action**: Run /specify for the Tabs primitive: flat array-driven controlled API (Array-driven controlled strip option) wrapping radix-ui Tabs, in src/renderer/src/components/molecules/, registered in PrimitivesDemo.
**Next**: Open the spec and resolve the aria-controls vs selection-only decision (share one Tabs.Root with panels, or hand-roll the tablist) as the first plan question.

## Next step

Copy the block below into a new /specify session manually. No automated handoff — user controls when /specify runs.

~~~
/specify "Controlled horizontal tab-strip primitive (Tabs) wrapping radix-ui Tabs behind a flat tabs-array + activeId + onChange API, for switching panels in the request and response panes."

Discovery reference: discover/2026-06-22-reusable-horizontal-tab-strip-primitive-for-switching.md
Key facts:
- Functional scope: Reusable, controlled, HORIZONTAL-only tab-strip primitive (no vertical variant): renders a row of tab buttons (label + optional badge + active state) from a tabs array, marks the activeId, emits onChange(id) on click or keyboard select, supports an optional right-aligned actions slot, implements roving-tabindex keyboard nav (arrows/Home/End with wrap) + WAI-ARIA tablist/tab semantics, skips disabled tabs. Selection only — does not render or own the panels it switches.
- Users: General-purpose reusable primitive for renderer developers: first consumers are the request authoring pane (Params/Auth/Headers/Body/Tests/Code) and the response pane (Body/Headers/Cookies/Test Results), but designed without coupling to those two call sites so any future pane/panel switching can use it. End user is the app user clicking/keyboarding tabs. No external API consumers.
- Success criteria: Behavior + keyboard nav + ARIA semantics gated by interaction tests (renders both panes' tab sets from a tabs array; click + arrows/Home/End switch active; WAI-ARIA tablist/tab/aria-selected correct; change event fires). Visual fidelity to design/reference.html verified manually via the PrimitivesDemo route.
- Recommended option: Array-driven controlled strip
- Open uncertainties: 1 (see discovery doc §Open uncertainties)
~~~

